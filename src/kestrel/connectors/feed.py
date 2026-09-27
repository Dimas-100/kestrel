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
import socket
import threading
import time
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


def _reject_constant(constant: str) -> None:
    # json.loads accepts NaN, Infinity and -Infinity by default (they aren't valid JSON), and pydantic's floats
    # accept them too; kestrel's own JSON responses refuse NaN, so a feed that sent one would break a page instead
    # of showing a red row
    raise ConnectorError(f"the feed sent {constant}, which JSON doesn't allow")


def parse(body: bytes) -> Snapshot:
    """The body as a Snapshot, or a ConnectorError that says what is wrong with it."""
    try:
        text = body.decode("utf-8-sig")  # -sig: a byte-order mark is fine
    except UnicodeDecodeError:
        raise ConnectorError(f"{NOT_JSON} (it isn't UTF-8 text)") from None
    if text.lstrip().startswith("<"):
        raise ConnectorError(f"{NOT_JSON}: a web page (a sign-in page, or the wrong address?)")
    try:
        payload = json.loads(text, parse_constant=_reject_constant)
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
        # http.client, not urllib: it never follows a redirect (so the token can never follow one either) and never
        # reads HTTP_PROXY/HTTPS_PROXY from the environment (so a feed on another host must be reachable directly)
        token = self._token()
        parts = urlsplit(url)
        target = urlunsplit(("", "", parts.path or "/", parts.query, ""))
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        connection_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        connection = connection_cls(parts.hostname, parts.port, timeout=self.timeout)
        no_answer = f"the feed didn't answer within {self.timeout:g} s"
        timed_out = False
        # set once the headers are in (or the attempt has already failed), so the watchdog thread below stands down
        done = threading.Event()

        def _watch() -> None:
            # the watchdog: a peer that trickles bytes without ever finishing its headers keeps resetting the
            # socket's own per-read timeout, so that alone can't be trusted to end this. Shutting the socket down
            # unblocks whatever call is waiting on it.
            nonlocal timed_out
            if done.wait(self.timeout):
                return  # stood down before the timeout: nothing to do
            timed_out = True
            sock = connection.sock
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

        try:
            connection.connect()  # the host's address is resolved here, before the watchdog can act
        except TimeoutError:
            connection.close()
            raise ConnectorError(no_answer) from None
        except OSError as exc:
            connection.close()
            raise ConnectorError(f"the feed couldn't be reached ({_why(exc)})") from None

        watchdog = threading.Thread(target=_watch, daemon=True)
        watchdog.start()
        try:
            try:
                connection.request("GET", target, headers=headers)
                response = connection.getresponse()
            except TimeoutError:
                raise ConnectorError(no_answer) from None
            except (http.client.HTTPException, OSError) as exc:
                raise ConnectorError(no_answer if timed_out else f"the feed couldn't be read ({exc})") from None
            finally:
                done.set()  # the headers are in (or the call above raised); the body has its own deadline below
            if timed_out:
                # the watchdog cut the connection while the headers were still coming in; whatever getresponse()
                # pieced together from what was left isn't a real answer
                raise ConnectorError(no_answer)
            if response.status != 200:
                if 300 <= response.status < 400:
                    location = response.getheader("Location")
                    if location:
                        raise ConnectorError(f"the feed redirected to {_shown(urljoin(url, location))}; kestrel "
                                             "doesn't follow redirects (set url to the feed's own address)")
                raise ConnectorError(f"the feed answered {response.status}")
            deadline = time.monotonic() + self.timeout
            return _read(response, deadline, self.timeout)
        finally:
            done.set()
            connection.close()
