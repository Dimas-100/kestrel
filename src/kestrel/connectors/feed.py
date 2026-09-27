"""A feed: one JSON document in the contract's own format (a Snapshot), read from a file, checked, and handed on.
This is how a system of your own (a trading desk) shows its books, strategies, trades and runs; kestrel knows
nothing else about it.

The connector only reads, once per snapshot, and caches nothing: a feed is small and its system is local.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import ValidationError

from ..contract import Snapshot, Source
from .base import DETAIL_LIMIT, ConnectorError

MAX_BYTES = 20 * 1024 * 1024  # 20 MB: far more than any feed needs, and a stop for one that never ends
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
    """Reads one feed file."""

    def __init__(self, source_id: str, label: str, *, path: Path) -> None:
        self.source_id = source_id
        self.label = label
        self.path = path

    def snapshot(self, now: datetime) -> Snapshot:
        return keep(parse(read_file(self.path)), self.source_id, self.label, now)
