"""A feed: one JSON document in the contract's own format (a Snapshot), read from a URL or a file, checked, and
handed on. This is how a system of your own (a trading desk) shows its books, strategies, trades and runs; kestrel
knows nothing else about it.

The connector only reads: one GET, or one file read, per snapshot, and nothing is cached (a feed is small and its
system is local). The token, when there is one, goes in that GET's Authorization header and nowhere else: never in a
message, never in a log, never to a redirect or a proxy.
"""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from pydantic import ValidationError

from ..contract import Snapshot, Source
from .base import DETAIL_LIMIT, ConnectorError

TIMEOUT = 5.0  # seconds, unless the profile says otherwise (1 to 60)
MAX_BYTES = 20 * 1024 * 1024  # 20 MB: far more than any feed needs, and a stop for one that never ends
CHUNK = 64 * 1024
CLOCK_DRIFT = timedelta(minutes=5)  # how far a feed's clock may run ahead of this one before its time is refused
SHOWN_PROBLEMS = 3
NOT_JSON = "the feed sent something that isn't JSON"


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _span(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return _count(minutes, "minute", "minutes")
    hours = minutes // 60
    return _count(hours, "hour", "hours") if hours < 48 else _count(hours // 24, "day", "days")


def read_file(path: Path) -> bytes:
    if not path.is_file():
        raise ConnectorError(f"no feed file at {path}")
    try:
        with path.open("rb") as f:
            body = f.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ConnectorError(f"the feed file at {path} couldn't be read ({exc.strerror or exc})") from None
    if len(body) > MAX_BYTES:
        raise ConnectorError("the feed file is more than 20 MB")
    return body


def _opener() -> urllib.request.OpenerDirector:
    """HTTP and HTTPS and nothing more: no proxy (the token goes to the configured host only), no redirect handler
    (a redirect comes back as an error), no cookie jar."""
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(),
                    urllib.request.HTTPDefaultErrorHandler(), urllib.request.HTTPErrorProcessor(),
                    urllib.request.UnknownHandler()):
        opener.add_handler(handler)
    return opener


def _shown(url: str) -> str:
    """A URL fit to show a person: no user name or password and no query, either of which could carry a secret."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc.rpartition("@")[2], parts.path, "", ""))


def _read(response: http.client.HTTPResponse, deadline: float, timeout: float) -> bytes:
    """The body, up to MAX_BYTES and within the deadline. `read1` makes at most one read on the socket, so a feed
    that sends a byte at a time can't outlast the timeout (the socket's own timeout is per read)."""
    length = response.headers.get("Content-Length", "")
    if length.isdigit() and int(length) > MAX_BYTES:
        raise ConnectorError("the feed sent more than 20 MB")
    chunks: list[bytes] = []
    size = 0
    try:
        while chunk := response.read1(CHUNK):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ConnectorError("the feed sent more than 20 MB")
            if time.monotonic() > deadline:
                raise ConnectorError(f"the feed was still sending after {timeout:g} s")
            chunks.append(chunk)
    except TimeoutError:
        raise ConnectorError(f"the feed was still sending after {timeout:g} s") from None
    return b"".join(chunks)


def _why(reason: object) -> str:
    return reason.strerror if isinstance(reason, OSError) and reason.strerror else str(reason)


def problems(exc: ValidationError) -> str:
    """The first three problems as `field.path: message`, then how many more; fewer than three when three wouldn't
    fit in a source row, so the count always shows."""
    found = [f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" if e["loc"] else e["msg"]
             for e in exc.errors()]
    shown = min(SHOWN_PROBLEMS, len(found))
    while True:
        more = len(found) - shown
        text = "; ".join(found[:shown]) + (f"; and {more} more" if more else "")
        if len(text) <= DETAIL_LIMIT or shown <= 1:
            return text
        shown -= 1


def parse(body: bytes) -> Snapshot:
    """The body as a Snapshot, or a ConnectorError that says what is wrong with it."""
    try:
        text = body.decode("utf-8-sig")  # -sig: a byte-order mark is fine
    except UnicodeDecodeError:
        raise ConnectorError(f"{NOT_JSON} (it isn't UTF-8 text)") from None
    if text.lstrip().startswith("<"):
        raise ConnectorError(f"{NOT_JSON}: a web page (a sign-in page, or the wrong address?)")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"{NOT_JSON} (line {exc.lineno}, column {exc.colno}: {exc.msg})") from None
    except RecursionError:
        raise ConnectorError(f"{NOT_JSON} (it is nested too deeply to read)") from None
    if isinstance(payload, dict) and "contract_version" not in payload:
        # the contract defaults a missing version to 1; a feed must say it, so a future one can't pass for this one
        raise ConnectorError('the feed doesn\'t say which contract it speaks: add "contract_version": "1"')
    try:
        return Snapshot.model_validate(payload)
    except ValidationError as exc:
        for e in exc.errors():
            if e["loc"] == ("contract_version",) and e["type"] == "value_error":
                raise ConnectorError(str(e["ctx"]["error"])) from None  # the contract's own words
        raise ConnectorError(problems(exc)) from None


def keep(snapshot: Snapshot, source_id: str, label: str, now: datetime) -> Snapshot:
    """What kestrel keeps of a payload: every list and the benchmark, with the payload's own sources replaced by one
    row for this feed, whose last success is when the payload was made."""
    made = snapshot.generated_at
    if made - now > CLOCK_DRIFT:
        raise ConnectorError(f"the feed's generated_at is {_span(made - now)} ahead of this computer's clock: "
                             "check the clock and time zone where the feed is made")
    counts = [_count(len(snapshot.books), "book", "books"), _count(len(snapshot.strategies), "strategy", "strategies"),
              _count(len(snapshot.trades), "trade", "trades")]
    if snapshot.accounts:
        counts.insert(0, _count(len(snapshot.accounts), "account", "accounts"))
    source = Source(id=source_id, label=label, kind="feed", last_success=min(made, now), status="ok",
                    detail=" · ".join(counts))
    return snapshot.model_copy(update={"sources": [source]})


class FeedConnector:
    """Reads one feed: `url` (one GET) or `path` (one file). `token_env` names the environment variable that holds a
    bearer token for the url; it is read each time, so the token lives in no object."""

    def __init__(self, source_id: str, label: str, *, url: str | None = None, path: Path | None = None,
                 token_env: str | None = None, timeout: float = TIMEOUT) -> None:
        self.source_id = source_id
        self.label = label
        self.url = url
        self.path = path
        self.token_env = token_env
        self.timeout = timeout

    def snapshot(self, now: datetime) -> Snapshot:
        body = self._fetch(self.url) if self.url is not None else read_file(self.path)
        return keep(parse(body), self.source_id, self.label, now)

    def _token(self) -> str | None:
        if self.token_env is None:
            return None
        token = os.environ.get(self.token_env, "").strip()
        if not token:
            raise ConnectorError(f"set {self.token_env} in the environment (token_env)")
        if not all("!" <= c <= "~" for c in token):
            # http.client would refuse it with the token in its message; visible ASCII is what a bearer token is
            raise ConnectorError(f"the token in {self.token_env} has a character a header can't carry "
                                 "(a space or a line break?)")
        return token

    def _fetch(self, url: str) -> bytes:
        token = self._token()
        request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        if token:
            # unredirected: were a redirect ever followed, the token would stay behind
            request.add_unredirected_header("Authorization", f"Bearer {token}")
        deadline = time.monotonic() + self.timeout
        no_answer = f"the feed didn't answer within {self.timeout:g} s"
        try:
            with _opener().open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ConnectorError(f"the feed answered {response.status}")
                return _read(response, deadline, self.timeout)
        except urllib.error.HTTPError as exc:  # any answer outside 2xx, a redirect included
            location = exc.headers.get("Location")
            exc.close()
            if 300 <= exc.code < 400 and location:
                raise ConnectorError(f"the feed redirected to {_shown(urljoin(url, location))}; kestrel doesn't "
                                     "follow redirects (set url to the feed's own address)") from None
            raise ConnectorError(f"the feed answered {exc.code}") from None
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise ConnectorError(no_answer) from None
            raise ConnectorError(f"the feed couldn't be reached ({_why(exc.reason)})") from None
        except TimeoutError:
            raise ConnectorError(no_answer) from None
        except (http.client.HTTPException, OSError) as exc:
            raise ConnectorError(f"the feed couldn't be read ({exc})") from None
