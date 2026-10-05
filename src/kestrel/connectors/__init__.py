"""Connectors turn a profile's sources into one Snapshot."""

from __future__ import annotations

from collections.abc import Callable, Hashable
from datetime import datetime
from pathlib import Path
from typing import Any

from ..contract import Snapshot, Source, merge
from ..profile import Profile, SourceCfg, parse_duration
from .base import DETAIL_LIMIT, Connector, ConnectorError, ConnectorUnavailable
from .command import DEFAULT_REFRESH
from .command import DEFAULT_TIMEOUT as COMMAND_TIMEOUT
from .demo import DemoConnector
from .fdc import FdcConnector
from .feed import TIMEOUT as FEED_TIMEOUT
from .feed import FeedConnector
from .rails import RailsConnector

__all__ = ["Connector", "ConnectorError", "ConnectorUnavailable", "build", "collect"]


def build(cfg: SourceCfg, profile: Profile) -> Connector:
    if cfg.kind == "demo":
        return DemoConnector(cfg.id, tz=profile.tz, seed=int(getattr(cfg, "seed", 340)))
    if cfg.kind == "fdc":
        path = getattr(cfg, "path", None)
        if not isinstance(path, str) or not path:
            raise ConnectorError("an fdc source needs a path to the warehouse, "
                                 'e.g. path = "../financial-data-collector/data/warehouse.db"')
        return FdcConnector(cfg.id, cfg.label or cfg.id, Path(path), categories=getattr(cfg, "categories", None),
                            benchmark=profile.benchmark)
    if cfg.kind == "feed":
        # the profile has already checked the shape: exactly one of url, path and command, the scheme, token_env,
        # cwd, timeout and refresh
        command = getattr(cfg, "command", None)
        if command is not None:
            cwd, refresh = getattr(cfg, "cwd", None), getattr(cfg, "refresh", None)
            return FeedConnector(cfg.id, cfg.label or cfg.id, command=list(command),
                                 cwd=Path(cwd) if cwd is not None else None,
                                 timeout=float(getattr(cfg, "timeout", COMMAND_TIMEOUT)),
                                 refresh=parse_duration(refresh) if refresh is not None else DEFAULT_REFRESH)
        path = getattr(cfg, "path", None)
        return FeedConnector(cfg.id, cfg.label or cfg.id, url=getattr(cfg, "url", None),
                             path=Path(path) if path is not None else None, token_env=getattr(cfg, "token_env", None),
                             timeout=float(getattr(cfg, "timeout", FEED_TIMEOUT)))
    if cfg.kind == "rails":
        path = getattr(cfg, "path", None)
        if not isinstance(path, str) or not path:
            raise ConnectorError('a rails source needs a path to its data folder (paper.json and runs.jsonl), '
                                 'e.g. path = "../trading-rails/data"')
        return RailsConnector(cfg.id, cfg.label or cfg.id, Path(path))
    raise ConnectorUnavailable(f"connector kind {cfg.kind!r} is not available in this version of kestrel")


def _with_staleness(sources: list[Source], cfg: SourceCfg, now: datetime) -> list[Source]:
    out = []
    for s in sources:
        old = s.last_success is not None and now - s.last_success > cfg.stale_delta
        out.append(s.model_copy(update={"status": "stale"}) if s.status == "ok" and old else s)
    return out


def _fit_note(detail: str, ignored: list[str]) -> str:
    """`detail` plus a note naming the ids `ignored` (five at most, then "and N more"), shrunk like
    `feed.problems()` until it fits `DETAIL_LIMIT`: fewer names, then no names at all, then — only if even a
    nameless note doesn't fit after `detail` — a shortened `detail` (with "…"), so the note always shows."""
    shown = min(5, len(ignored))
    while True:
        more = len(ignored) - shown
        if shown:
            note = f"ignored duplicate ids: {', '.join(ignored[:shown])}" + (f", and {more} more" if more else "")
        else:
            note = f"ignored {more} duplicate {'id' if more == 1 else 'ids'}"
        combined = " · ".join(text for text in (detail, note) if text)
        if len(combined) <= DETAIL_LIMIT or shown == 0:
            break
        shown -= 1
    if len(combined) <= DETAIL_LIMIT:
        return combined
    room = DETAIL_LIMIT - len(note) - len(" · ")
    short = detail[:room - 1] + "…" if room > 1 else ""
    return " · ".join(text for text in (short, note) if text)


def _noted(sources: list[Source], ignored: list[str]) -> list[Source]:
    """The part's first source row, its detail naming the ids it lost, fitted to the row (`_fit_note`), then the
    rest unchanged."""
    if not sources:
        return sources
    first = sources[0]
    return [first.model_copy(update={"detail": _fit_note(first.detail, ignored)}), *sources[1:]]


# Blocks nothing else hangs off, each with the key two items of the same thing share, and whether a dropped item's
# key is named in the source's note: an event has no id of its own, so a duplicate event goes without a mention.
_LONE_BLOCKS: tuple[tuple[str, Callable[[Any], Hashable], bool], ...] = (
    ("targets", lambda target: target.id, True),
    ("theses", lambda thesis: thesis.symbol, True),
    ("events", lambda event: (event.date, event.kind, event.symbol, event.title), False),
    ("goals", lambda goal: goal.id, True),
    ("exposures", lambda exposure: exposure.symbol, True),
    ("backtests", lambda backtest: backtest.id, True),
)


def _dedupe_within(part: Snapshot) -> tuple[Snapshot, list[str]]:
    """Two accounts, books or strategies of the same id within this one source: keep the first, drop the later
    item itself. Its dependents (positions, trades, holdings, …) are keyed by that same id, so they stay — they end
    up attached to the one that's kept. Two histories of the same id: the first stays, the later goes (a history
    isn't an item of its own, so it isn't named in the note). Two targets, goals or backtests of the same id, theses
    or exposures of the same symbol, or events of the same date, kind, symbol and title: the first stays
    (`_LONE_BLOCKS`; nothing hangs off them)."""

    def first_only(items: list, key: Callable[[Any], Hashable] = lambda item: item.id) -> tuple[list, list]:
        seen: set[Hashable] = set()
        kept: list = []
        dupes: list = []
        for item in items:
            k = key(item)
            if k in seen:
                dupes.append(k)
            else:
                seen.add(k)
                kept.append(item)
        return kept, dupes

    accounts, dup_accounts = first_only(part.accounts)
    books, dup_books = first_only(part.books)
    strategies, dup_strategies = first_only(part.strategies)
    account_history, dup_account_history = first_only(part.account_history)
    book_history, dup_book_history = first_only(part.book_history)
    lone = {name: first_only(getattr(part, name), key) for name, key, _ in _LONE_BLOCKS}
    dupes = [*dup_accounts, *dup_books, *dup_strategies,
             *(k for name, _, named in _LONE_BLOCKS if named for k in lone[name][1])]
    if not (dupes or dup_account_history or dup_book_history or any(dropped for _, dropped in lone.values())):
        return part, []
    return part.model_copy(update={"accounts": accounts, "books": books, "strategies": strategies,
                                   "account_history": account_history, "book_history": book_history,
                                   **{name: kept for name, (kept, _) in lone.items()}}), dupes


def _without_duplicates(parts: list[Snapshot]) -> list[Snapshot]:
    """When a later source uses an account, book or strategy id an earlier one already has, the earlier one's item
    stays and the later one's goes, with everything that hangs off it: an account's holdings, transactions and
    history; a book's
    history, positions, trades, trade charts and runs. Books keep pointing at the first strategy of their id. A
    history whose id an earlier source's history already has goes too, even without an item of that id, so every
    page reads the same one. A target, thesis, event, goal, exposure or backtest whose key an earlier source already
    has goes on its own (`_LONE_BLOCKS`). Two items or histories of the same id within one source (`_dedupe_within`)
    are resolved first."""
    seen_accounts: set[str] = set()
    seen_books: set[str] = set()
    seen_strategies: set[str] = set()
    seen_account_history: set[str] = set()
    seen_book_history: set[str] = set()
    seen_lone: dict[str, set] = {name: set() for name, _, _ in _LONE_BLOCKS}
    out = []
    for part in parts:
        part, within = _dedupe_within(part)
        accounts = {a.id for a in part.accounts} & seen_accounts
        books = {b.id for b in part.books} & seen_books
        strategies = {s.id for s in part.strategies} & seen_strategies
        account_history = {s.id for s in part.account_history} & seen_account_history
        book_history = {s.id for s in part.book_history} & seen_book_history
        seen_accounts |= {a.id for a in part.accounts}
        seen_books |= {b.id for b in part.books}
        seen_strategies |= {s.id for s in part.strategies}
        seen_account_history |= {s.id for s in part.account_history}
        seen_book_history |= {s.id for s in part.book_history}
        lone = {name: {key(item) for item in getattr(part, name)} & seen_lone[name] for name, key, _ in _LONE_BLOCKS}
        for name, key, _ in _LONE_BLOCKS:
            seen_lone[name] |= {key(item) for item in getattr(part, name)}
        if not (accounts or books or strategies or within or account_history or book_history or any(lone.values())):
            out.append(part)
            continue
        ignored = [*(a.id for a in part.accounts if a.id in accounts), *(b.id for b in part.books if b.id in books),
                   *(s.id for s in part.strategies if s.id in strategies),
                   *(key(item) for name, key, named in _LONE_BLOCKS if named
                     for item in getattr(part, name) if key(item) in lone[name]),
                   *within]
        out.append(part.model_copy(update={
            "accounts": [a for a in part.accounts if a.id not in accounts],
            "holdings": [h for h in part.holdings if h.account_id not in accounts],
            "transactions": [t for t in part.transactions if t.account_id not in accounts],
            "account_history": [s for s in part.account_history if s.id not in accounts | account_history],
            "books": [b for b in part.books if b.id not in books],
            "book_history": [s for s in part.book_history if s.id not in books | book_history],
            "positions": [p for p in part.positions if p.book_id not in books],
            "trades": [t for t in part.trades if t.book_id not in books],
            "trade_charts": [c for c in part.trade_charts if c.book_id not in books],
            "runs": [r for r in part.runs if r.book_id not in books],
            "strategies": [s for s in part.strategies if s.id not in strategies],
            **{name: [item for item in getattr(part, name) if key(item) not in lone[name]]
               for name, key, _ in _LONE_BLOCKS},
            # an id named once, in order; a history alone (no item dropped) isn't noted
            "sources": _noted(list(part.sources), list(dict.fromkeys(ignored))) if ignored else part.sources,
        }))
    return out


def collect(profile: Profile, now: datetime) -> Snapshot:
    """Ask every source for its snapshot. One broken source shows as an error; it never takes the page down. When
    two sources use the same id, the one earlier in the profile wins (`_without_duplicates`)."""
    parts: list[Snapshot] = []
    failed: list[Source] = []
    for cfg in profile.sources:
        try:
            part = build(cfg, profile).snapshot(now)
        except Exception as exc:  # noqa: BLE001 - any connector failure becomes a visible source error
            failed.append(Source(id=cfg.id, label=cfg.label or cfg.id, kind=cfg.kind, status="error",
                                 detail=str(exc)[:DETAIL_LIMIT]))
            continue
        parts.append(part.model_copy(update={"sources": _with_staleness(list(part.sources), cfg, now)}))
    snapshot = merge(_without_duplicates(parts), generated_at=now)
    return snapshot.model_copy(update={"sources": [*snapshot.sources, *failed]})
