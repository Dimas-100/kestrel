"""A feed: one JSON document in the contract's own format (a Snapshot), read from a URL, a file or what a command
prints, checked, and handed on. This is how a system of your own (a trading desk) shows its books, strategies, trades
and runs; kestrel knows nothing else about it.

The connector only reads: one GET, or one file read, per snapshot, and nothing of those is cached (a feed is small and
its system is local). A command's output is reused for `refresh` (`command.cached_run`), since running a program is
slower than reading a file. The token, when there is one, goes in that GET's Authorization header and nowhere else:
never in a message, never in a log, never to a redirect or a proxy.
"""

from __future__ import annotations

import http.client
import json
import math
import os
import socket
import threading
import time
from datetime import date, datetime, timedelta
from functools import cache
from pathlib import Path
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin
from urllib.parse import urljoin, urlsplit, urlunsplit

from pydantic import BaseModel, TypeAdapter, ValidationError

from .. import __version__
from ..contract import Snapshot, Source, check_version
from .base import DETAIL_LIMIT, ConnectorError
from .command import DEFAULT_REFRESH, cached_run
from .command import DEFAULT_TIMEOUT as COMMAND_TIMEOUT

TIMEOUT = 5.0  # seconds, unless the profile says otherwise (1 to 60)
MAX_BYTES = 20 * 1024 * 1024  # 20 MB: far more than any feed needs, and a stop for one that never ends
CHUNK = 64 * 1024
CLOCK_DRIFT = timedelta(minutes=5)  # how far a feed's clock may run ahead of this one before its time is refused
SHOWN_PROBLEMS = 3
NOT_JSON = "the feed sent something that isn't JSON"
TOO_LARGE = "the feed sent a number too large to use"
MAX_ITEMS = 1_000_000  # list items in all, at any depth: far more than any feed needs
# the most list items pydantic sees in one call: it keeps every problem it finds until the call returns, so a whole
# payload of bad items at once could take gigabytes, and minutes to describe
BATCH = 2_000
EARLIEST, LATEST = date(1970, 1, 1), date(2200, 12, 31)  # the dates kestrel's pages can work with
LARGEST = 1e15  # the largest number, either way, that they can: sums, returns and charts stay finite
_PLAIN = {"include_url": False, "include_context": False, "include_input": False}  # an error's words and place only
_BAD = object()  # what a check returns for a part that didn't pass (None is a value a field can have)


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


class _TooBig(ConnectorError):
    """The body passed MAX_BYTES: a fact about the feed, whatever the clock says."""


def _read(response: http.client.HTTPResponse, deadline: float, still_sending: str) -> bytes:
    """The body, up to MAX_BYTES. The deadline is checked between reads; a read that blocks inside the chunked
    framing (a chunk-size or trailer line trickled a byte at a time) is ended by `_fetch`'s watchdog instead."""
    if response.length is not None and response.length > MAX_BYTES:  # http.client's own reading of Content-Length
        raise _TooBig("the feed sent more than 20 MB")
    chunks: list[bytes] = []
    size = 0
    try:
        while chunk := response.read1(CHUNK):
            size += len(chunk)
            if size > MAX_BYTES:
                raise _TooBig("the feed sent more than 20 MB")
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


def problems(found: list[str], total: int) -> str:
    """The first three problems `found` (as `field.path: message`), then how many more of the `total`; fewer than
    three when three wouldn't fit in a source row, so the count always shows."""
    shown = min(SHOWN_PROBLEMS, len(found))
    while True:
        more = total - shown
        text = "; ".join(found[:shown]) + (f"; and {more} more" if more else "")
        if len(text) <= DETAIL_LIMIT or shown <= 1:
            return text
        shown -= 1


def _reject_constant(constant: str) -> None:
    # json.loads accepts NaN, Infinity and -Infinity by default (they aren't valid JSON), and pydantic's floats
    # accept them too; kestrel's own JSON responses refuse NaN, so a feed that sent one would break a page instead
    # of showing a red row
    raise ConnectorError(f"the feed sent {constant}, which JSON doesn't allow")


def _finite(text: str) -> float:
    # json turns a number too large for a float, such as 1e999, into inf without ever asking parse_constant
    value = float(text)
    if not math.isfinite(value):
        raise ConnectorError(TOO_LARGE)
    return value


def _inside(nodes: list, cap: int) -> int:
    """How many list items `nodes` hold, at any depth (a list's items, their lists' items, and so on). The count
    stops as soon as it passes `cap`, so it never walks much more than `cap` items."""
    total, stack = 0, [node for node in nodes if isinstance(node, (list, dict))]
    pop, push = stack.pop, stack.append
    while stack:
        node = pop()
        if isinstance(node, list):
            total += len(node)
            if total > cap:
                break
            children = node
        else:
            children = node.values()
        for child in children:
            if isinstance(child, (list, dict)):
                push(child)
    return total


def _unwrap(tp: Any) -> Any:
    """X for `X | None`; any other type as it is."""
    if get_origin(tp) in (Union, UnionType):
        rest = [arg for arg in get_args(tp) if arg is not NoneType]
        if len(rest) == 1:
            return rest[0]
    return tp


@cache
def _deep(tp: Any) -> bool:
    """Whether a value of `tp` can hold a list (it is a list, or a model with one inside): such a value is checked
    in parts."""
    if get_origin(tp) is list:
        return True
    model = _unwrap(tp)
    return (isinstance(model, type) and issubclass(model, BaseModel)
            and any(_deep(field.annotation) for field in model.model_fields.values()))


@cache
def _adapter(tp: Any) -> TypeAdapter:
    return TypeAdapter(tp)


class _Problems:
    """What is wrong with a payload: the first few problems as `field.path: message`, in the order pydantic would
    list them, and how many there are in all."""

    def __init__(self) -> None:
        self.found: list[str] = []
        self.total = 0

    def add(self, errors: list, path: tuple, offset: int = 0) -> None:
        """`errors` from a check of the part at `path`; `offset` is where a batch of list items began."""
        self.total += len(errors)
        for e in errors[:SHOWN_PROBLEMS - len(self.found)]:
            loc = e["loc"]
            if offset and loc and isinstance(loc[0], int):
                loc = (loc[0] + offset, *loc[1:])  # the item's place in the whole list, not in its batch
            where = ".".join(str(part) for part in (*path, *loc))
            self.found.append(f"{where}: {e['msg']}" if where else e["msg"])

    def add_error(self, exc: ValidationError, path: tuple, offset: int = 0) -> None:
        if len(self.found) < SHOWN_PROBLEMS:
            self.add(exc.errors(**_PLAIN), path, offset)  # one check's errors: at most BATCH items' worth
        else:
            self.total += exc.error_count()  # only the count: nothing more will be shown


def _validate(tp: Any, value: Any, path: tuple, found: _Problems, offset: int = 0) -> Any:
    try:
        return _adapter(tp).validate_python(value)
    except ValidationError as exc:
        found.add_error(exc, path, offset)
        return _BAD


def _check(tp: Any, value: Any, path: tuple, found: _Problems) -> Any:
    """`value` checked as `tp` without pydantic ever seeing more than BATCH list items at once; the checked value,
    or _BAD with the problems in `found`."""
    if get_origin(tp) is list:
        return _check_list(get_args(tp)[0], value, path, found)
    model = _unwrap(tp)
    if isinstance(value, dict) and _deep(model):
        return _check_model(model, value, path, found)
    return _validate(tp, value, path, found)  # None, or not even a dict: one quick check


def _check_list(item: Any, value: Any, path: tuple, found: _Problems) -> Any:
    """A list, in batches of at most BATCH items (counting what each item holds); an item bigger than that on its
    own is checked in parts."""
    if not isinstance(value, list):
        return _validate(list[item], value, path, found)
    deep = _deep(item)
    out: list = []
    bad = False
    batch: list = []
    start = weight = 0

    def flush() -> None:
        nonlocal bad, batch, weight
        if batch:
            checked = _validate(list[item], batch, path, found, offset=start)
            if checked is _BAD:
                bad = True
            else:
                out.extend(checked)
        batch, weight = [], 0

    for i, element in enumerate(value):
        size = 1 + _inside([element], BATCH) if deep else 1
        if weight + size > BATCH:
            flush()
        if size > BATCH:
            checked = _check(item, element, (*path, i), found)
            if checked is _BAD:
                bad = True
            else:
                out.append(checked)
            continue
        if not batch:
            start = i
        batch.append(element)
        weight += size
    flush()
    return _BAD if bad else out


def _check_model(model: type[BaseModel], value: dict, path: tuple, found: _Problems) -> Any:
    """A model in parts: each field that can hold a list on its own, the rest at once; the problems in the model's
    field order, as pydantic would list them."""
    fields = model.model_fields
    parts = [name for name, field in fields.items() if name in value and _deep(field.annotation)]
    left_out = {(name,) for name in parts}
    rest = {key: v for key, v in value.items() if key not in parts}
    errors: list = []
    try:
        _adapter(model).validate_python(rest)
    except ValidationError as exc:
        # these fields hold no lists, so there are few of these; a part left out reads as missing here, and is
        # checked on its own below
        errors = [e for e in exc.errors(**_PLAIN) if not (e["type"] == "missing" and e["loc"] in left_out)]
    before = found.total
    found.add([e for e in errors if not e["loc"]], path)
    checked = {}
    for name, field in fields.items():
        found.add([e for e in errors if e["loc"][:1] == (name,)], path)
        if name in parts:
            checked[name] = _check(field.annotation, value[name], (*path, name), found)
    if found.total > before:
        return _BAD
    return _validate(model, {**rest, **checked}, path, found)  # the parts are models by now: not checked again


def _unusable(node: BaseModel | list, path: tuple = ()) -> str | None:
    """The first date or number in `node` that kestrel's pages can't work with, as the problem to show, or None: a
    date outside 1970–2200 (Go's zero time, 0001-01-01, is the usual one), a number bigger than LARGEST either way,
    or NaN (pydantic reads the string "NaN" as one). Models and lists are walked in field order."""
    # a validated model keeps its fields in __dict__, in field order; exact types first, as a feed can hold a lot
    items = node.__dict__.items() if isinstance(node, BaseModel) else enumerate(node)
    for key, value in items:
        kind = type(value)
        if kind is float or kind is int:  # not bool: its type is bool
            if not -LARGEST <= value <= LARGEST:
                where = ".".join(str(part) for part in (*path, key))
                return f"{where} isn't a number" if value != value else f"{where} is too large"
        elif kind is str or value is None:
            continue
        elif isinstance(value, date):
            day = value.date() if isinstance(value, datetime) else value
            if not EARLIEST <= day <= LATEST:
                where = ".".join(str(part) for part in (*path, key))
                return f"{where} is {day.isoformat()}, outside 1970–2200"
        elif isinstance(value, BaseModel | list):
            problem = _unusable(value, (*path, key))
            if problem:
                return problem
    return None


def parse(body: bytes) -> Snapshot:
    """The body as a Snapshot, or a ConnectorError that says what is wrong with it."""
    try:
        text = body.decode("utf-8-sig")  # -sig: a byte-order mark is fine
    except UnicodeDecodeError:
        raise ConnectorError(f"{NOT_JSON} (it isn't UTF-8 text)") from None
    if text.lstrip().startswith("<"):
        raise ConnectorError(f"{NOT_JSON}: a web page (a sign-in page, or the wrong address?)")
    try:
        payload = json.loads(text, parse_constant=_reject_constant, parse_float=_finite)
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"{NOT_JSON} (line {exc.lineno}, column {exc.colno}: {exc.msg})") from None
    except RecursionError:
        raise ConnectorError(f"{NOT_JSON} (it is nested too deeply to read)") from None
    except ValueError:  # an integer longer than Python reads (4,300 digits)
        raise ConnectorError(TOO_LARGE) from None
    if isinstance(payload, dict):
        if _inside([payload.get(name) for name in Snapshot.model_fields], MAX_ITEMS) > MAX_ITEMS:
            raise ConnectorError(f"the feed sent more than {MAX_ITEMS:,} items")
        if "contract_version" not in payload:
            # the contract defaults a missing version to 1; a feed must say it, so a future one can't pass for this
            raise ConnectorError('the feed doesn\'t say which contract it speaks: add "contract_version": "1"')
        if isinstance(payload["contract_version"], str):  # anything else is a problem the check below names
            try:
                check_version(payload["contract_version"])
            except ValueError as exc:
                raise ConnectorError(str(exc)) from None  # the contract's own words
    found = _Problems()
    snapshot = _check(Snapshot, payload, (), found)
    if snapshot is _BAD:
        raise ConnectorError(problems(found.found, found.total))
    # the payload's own sources are left out: keep() replaces them, and a Go system that has never succeeded
    # writes Go's zero time as their last success
    problem = _unusable(snapshot.model_copy(update={"sources": []}))
    if problem:
        raise ConnectorError(problem)
    return snapshot


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
    """Reads one feed: `url` (one GET), `path` (one file) or `command` (a program's output, one run reused for
    `refresh`, run in `cwd`). `token_env` names the environment variable that holds a bearer token for the url; it is
    read each time, so the token lives in no object. `timeout` defaults to 5 s, or 30 s for a command."""

    def __init__(self, source_id: str, label: str, *, url: str | None = None, path: Path | None = None,
                 command: list[str] | None = None, cwd: Path | None = None, token_env: str | None = None,
                 timeout: float | None = None, refresh: timedelta = DEFAULT_REFRESH) -> None:
        self.source_id = source_id
        self.label = label
        self.url = url
        self.path = path
        self.command = command
        self.cwd = cwd
        self.token_env = token_env
        self.timeout = timeout if timeout is not None else COMMAND_TIMEOUT if command is not None else TIMEOUT
        self.refresh = refresh

    def snapshot(self, now: datetime) -> Snapshot:
        if self.command is not None:
            body = cached_run((self.source_id, tuple(self.command)), self.command, cwd=self.cwd,
                              timeout=self.timeout, refresh=self.refresh)
        elif self.url is not None:
            body = self._fetch(self.url)
        else:
            body = read_file(self.path)
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

        def late() -> bool:
            # past the deadline, whatever failed failed for lack of time, even before the watchdog wakes (on a
            # coarse clock it can wake a tick late) and even when the error isn't a TimeoutError (a TLS handshake
            # that runs out of time can end with SSLWantReadError)
            return timed_out or time.monotonic() >= deadline

        watchdog = threading.Thread(target=_watch, daemon=True)
        watchdog.start()
        try:
            try:
                connection.connect()  # looking up the host's address happens in here, and nothing can cut it short
            except OSError as exc:
                timeout = late() or isinstance(exc, TimeoutError)
                raise ConnectorError(no_answer if timeout else f"the feed couldn't be reached ({_why(exc)})") from None
            if late():
                raise ConnectorError(no_answer)
            try:
                connection.request("GET", target, headers=headers)
                response = connection.getresponse()
            except TimeoutError:
                raise ConnectorError(no_answer) from None
            except (http.client.HTTPException, OSError) as exc:
                raise ConnectorError(no_answer if late() else f"the feed couldn't be read ({exc})") from None
            if late():
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
            except _TooBig:
                raise
            except ConnectorError:
                if late():  # whatever went wrong, it went wrong because the time ran out
                    raise ConnectorError(still_sending) from None
                raise
            if late():  # the watchdog ended a read that would otherwise have gone on: what came isn't the answer
                raise ConnectorError(still_sending)
            return body
        finally:
            done.set()
            watchdog.join()  # it has stood down, or is finishing a shutdown: never close under it
            connection.close()
