"""The Backtests page, computed from one Snapshot: the research record."""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict

from ..contract import Backtest, Snapshot
from ..profile import Profile
from .home import View

ROWS_LIMIT = 200  # the page lists only the newest results; a real feed can carry thousands
# the best verdict for a window, lowest wins: a single pass outshines a pile of fails
_VERDICT_RANK = {"pass": 0, "pending": 1, "fail": 2, "refused": 3}


class Totals(View):
    results: int
    candidates: int  # distinct name, across every window
    families: int
    passes_by_window: dict[str, int]


class FamilyRow(View):
    family: str
    candidates: int  # distinct name, within this family
    best: Backtest | None
    verdicts: dict[str, str]  # window -> its best verdict seen for this family
    last_at: dt.datetime


class BacktestsView(View):
    as_of: dt.datetime
    totals: Totals
    windows: list[str]  # newest-used first, ties alphabetical
    families: list[FamilyRow]  # a pass first, then by last_at desc
    rows: list[Backtest]  # newest ROWS_LIMIT results


def _windows_order(backtests: list[Backtest]) -> list[str]:
    """Every window, ordered by its own most recent result: scanning the results newest first, this is the order
    each window is first seen. A tie (the same instant) breaks alphabetically."""
    latest: dict[str, dt.datetime] = {}
    for b in backtests:
        if b.window and (b.window not in latest or b.at > latest[b.window]):
            latest[b.window] = b.at
    return sorted(latest, key=lambda w: (-latest[w].timestamp(), w))


def _best(backtests: list[Backtest], rank: dict[str, int]) -> Backtest:
    """The furthest window (lowest `rank`) with a pass, ties broken by the higher t-stat; with no pass, the newest
    result of any verdict."""
    passes = [b for b in backtests if b.verdict == "pass"]
    if not passes:
        return max(backtests, key=lambda b: b.at)
    furthest = min(rank.get(b.window, len(rank)) for b in passes)
    at_furthest = [b for b in passes if rank.get(b.window, len(rank)) == furthest]
    return max(at_furthest, key=lambda b: b.t_stat if b.t_stat is not None else float("-inf"))


def _verdicts(backtests: list[Backtest]) -> dict[str, str]:
    best: dict[str, str] = {}
    for b in backtests:
        if not b.window:
            continue
        current = best.get(b.window)
        if current is None or _VERDICT_RANK[b.verdict] < _VERDICT_RANK[current]:
            best[b.window] = b.verdict
    return best


def backtests_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> BacktestsView:
    backtests = snapshot.backtests
    windows = _windows_order(backtests)
    rank = {w: i for i, w in enumerate(windows)}

    by_family: dict[str, list[Backtest]] = defaultdict(list)
    for b in backtests:
        by_family[b.family].append(b)

    ordered_families = sorted(
        by_family.items(),
        key=lambda kv: (not any(b.verdict == "pass" for b in kv[1]), -max(b.at for b in kv[1]).timestamp()),
    )
    families = [
        FamilyRow(family=family, candidates=len({b.name for b in group}), best=_best(group, rank),
                  verdicts=_verdicts(group), last_at=max(b.at for b in group))
        for family, group in ordered_families
    ]

    totals = Totals(
        results=len(backtests), candidates=len({b.name for b in backtests}), families=len(by_family),
        passes_by_window=dict(Counter(b.window for b in backtests if b.verdict == "pass")),
    )
    rows = sorted(backtests, key=lambda b: b.at, reverse=True)[:ROWS_LIMIT]
    return BacktestsView(as_of=now, totals=totals, windows=windows, families=families, rows=rows)
