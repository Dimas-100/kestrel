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

from .. import __version__
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


def _read(response: http.client.HTTPResponse, deadline: float, still_sending: str) -> bytes:
    """The body, up to MAX_BYTES. The deadline is checked between reads; a read that blocks inside the chunked
    framing (a chunk-size or trailer line trickled a byte at a time) is ended by `_fetch`'s watchdog instead."""
    if response.length is not None and response.length > MAX_BYTES:  # http.client's own reading of Content-Length
        raise ConnectorError("the feed sent more than 20 MB")
    chunks: list[bytes] = []
    size = 0
    try:
        while chunk := response.read1(CHUNK):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ConnectorError("the feed sent more than 20 MB")
            if time.monotonic() > deadline:
                raise ConnectorError(still_sending)
            chunks.append(chunk)
    except TimeoutError:
        raise ConnectorError(still_sending) from None
    except (http.client.HTTPException, OSError) as exc:
        # the class name only: an exception's text can quote what the feed sent
        raise ConnectorError(f"the feed couldn't be read ({type(exc).__name__})") from None
    if response.length:  # what Content-Length promised and never came
        raise ConnectorError("the feed stopped partway")
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
        headers = {"Accept": "application/json", "User-Agent": f"kestrel/{__version__}"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        connection_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        connection = connection_cls(parts.hostname, parts.port, timeout=self.timeout)
        no_answer = f"the feed didn't answer within {self.timeout:g} s"
        still_sending = f"the feed was still sending after {self.timeout:g} s"
        deadline = time.monotonic() + self.timeout  # one deadline for the whole answer: connecting, headers, body
        timed_out = False
        done = threading.Event()  # set once the whole answer is in, or the attempt has failed

        def _watch() -> None:
            # the watchdog: a peer that trickles bytes (in its headers, or in a chunked body's framing) keeps
            # resetting the socket's own per-read timeout, so that alone can't be trusted to end this. Shutting the
            # socket down unblocks whatever call is waiting on it.
            nonlocal timed_out
            if done.wait(max(0.0, deadline - time.monotonic())):
                return  # stood down before the deadline: nothing to do
            timed_out = True  # before the socket is read: a connect that finishes now still sees this
            sock = connection.sock  # None while connecting: the connect has its own timeout, and is checked after
            if sock is not None:
                try:
                    # the plain socket's shutdown, even under TLS: SSLSocket.shutdown also drops the TLS state,
                    # which a read in progress on the other thread may be about to use
                    socket.socket.shutdown(sock, socket.SHUT_RDWR)
                except OSError:
                    pass

        watchdog = threading.Thread(target=_watch, daemon=True)
        watchdog.start()
        try:
            try:
                connection.connect()  # looking up the host's address happens in here, and nothing can cut it short
            except OSError as exc:
                late = timed_out or isinstance(exc, TimeoutError)
                raise ConnectorError(no_answer if late else f"the feed couldn't be reached ({_why(exc)})") from None
            if timed_out:
                raise ConnectorError(no_answer)
            try:
                connection.request("GET", target, headers=headers)
                response = connection.getresponse()
            except TimeoutError:
                raise ConnectorError(no_answer) from None
            except (http.client.HTTPException, OSError) as exc:
                raise ConnectorError(no_answer if timed_out else f"the feed couldn't be read ({exc})") from None
            if timed_out:
                # the watchdog cut the connection while the headers were still coming in; whatever getresponse()
                # pieced together from what was left isn't a real answer
                raise ConnectorError(no_answer)
            if response.status != 200:
                if 300 <= response.status < 400:
                    location = response.getheader("Location")
                    if location:
                        try:
                            where = f" to {_shown(urljoin(url, location))}"
                        except ValueError:  # an address urllib can't read: don't repeat it, or why
                            where = ""
                        raise ConnectorError(f"the feed redirected{where}; kestrel doesn't follow redirects "
                                             "(set url to the feed's own address)")
                raise ConnectorError(f"the feed answered {response.status}")
            try:
                body = _read(response, deadline, still_sending)
            except ConnectorError:
                if timed_out:  # whatever went wrong, it went wrong because the watchdog cut the connection
                    raise ConnectorError(still_sending) from None
                raise
            if timed_out:  # the watchdog ended a read that would otherwise have gone on: what came isn't the answer
                raise ConnectorError(still_sending)
            return body
        finally:
            done.set()
            watchdog.join()  # it has stood down, or is finishing a shutdown: never close under it
            connection.close()
