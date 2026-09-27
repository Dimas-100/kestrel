"""Connectors turn a profile's sources into one Snapshot."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..contract import Snapshot, Source, merge
from ..profile import Profile, SourceCfg
from .base import DETAIL_LIMIT, Connector, ConnectorError, ConnectorUnavailable
from .demo import DemoConnector
from .fdc import FdcConnector
from .feed import TIMEOUT as FEED_TIMEOUT
from .feed import FeedConnector

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
        # the profile has already checked the shape: exactly one of url and path, the scheme, token_env, timeout
        path = getattr(cfg, "path", None)
        return FeedConnector(cfg.id, cfg.label or cfg.id, url=getattr(cfg, "url", None),
                             path=Path(path) if path is not None else None, token_env=getattr(cfg, "token_env", None),
                             timeout=float(getattr(cfg, "timeout", FEED_TIMEOUT)))
    raise ConnectorUnavailable(f"connector kind {cfg.kind!r} is not available in this version of kestrel")


def _with_staleness(sources: list[Source], cfg: SourceCfg, now: datetime) -> list[Source]:
    out = []
    for s in sources:
        old = s.last_success is not None and now - s.last_success > cfg.stale_delta
        out.append(s.model_copy(update={"status": "stale"}) if s.status == "ok" and old else s)
    return out


def _noted(sources: list[Source], ignored: list[str]) -> list[Source]:
    """The part's first source row, its detail naming the ids it lost (at most five), then the rest unchanged."""
    if not sources:
        return sources
    names = ", ".join(ignored[:5]) + (f", and {len(ignored) - 5} more" if len(ignored) > 5 else "")
    first = sources[0]
    detail = " · ".join(text for text in (first.detail, f"ignored duplicate ids: {names}") if text)
    return [first.model_copy(update={"detail": detail}), *sources[1:]]


def _without_duplicates(parts: list[Snapshot]) -> list[Snapshot]:
    """When a later source uses an account, book or strategy id an earlier one already has, the earlier one's item
    stays and the later one's goes, with everything that hangs off it: an account's holdings and history; a book's
    history, positions, trades, trade charts and runs. Books keep pointing at the first strategy of their id."""
    seen_accounts: set[str] = set()
    seen_books: set[str] = set()
    seen_strategies: set[str] = set()
    out = []
    for part in parts:
        accounts = {a.id for a in part.accounts} & seen_accounts
        books = {b.id for b in part.books} & seen_books
        strategies = {s.id for s in part.strategies} & seen_strategies
        seen_accounts |= {a.id for a in part.accounts}
        seen_books |= {b.id for b in part.books}
        seen_strategies |= {s.id for s in part.strategies}
        if not (accounts or books or strategies):
            out.append(part)
            continue
        ignored = [*(a.id for a in part.accounts if a.id in accounts), *(b.id for b in part.books if b.id in books),
                   *(s.id for s in part.strategies if s.id in strategies)]
        out.append(part.model_copy(update={
            "accounts": [a for a in part.accounts if a.id not in accounts],
            "holdings": [h for h in part.holdings if h.account_id not in accounts],
            "account_history": [s for s in part.account_history if s.id not in accounts],
            "books": [b for b in part.books if b.id not in books],
            "book_history": [s for s in part.book_history if s.id not in books],
            "positions": [p for p in part.positions if p.book_id not in books],
            "trades": [t for t in part.trades if t.book_id not in books],
            "trade_charts": [c for c in part.trade_charts if c.book_id not in books],
            "runs": [r for r in part.runs if r.book_id not in books],
            "strategies": [s for s in part.strategies if s.id not in strategies],
            "sources": _noted(list(part.sources), list(dict.fromkeys(ignored))),  # an id named once, in order
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
