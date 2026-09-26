"""Pure money math shared by every view. No I/O, no clock."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .contract import ValuePoint


def growth_index(points: Sequence[ValuePoint]) -> list[float]:
    """Time-weighted growth index starting at 1.0.

    Each step is the day's change net of that day's deposits and withdrawals, so adding money never
    looks like performance.
    """
    if not points:
        return []
    index = [1.0]
    for prev, cur in zip(points, points[1:]):
        step = (cur.value - cur.net_flow) / prev.value if prev.value > 0 else 1.0
        index.append(index[-1] * step)
    return index


def max_drawdown_pct(index: Sequence[float]) -> float:
    """Worst fall from a running peak, as a negative percent (0.0 when it never fell)."""
    peak = -math.inf
    worst = 0.0
    for value in index:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1.0)
    return worst * 100.0


def expected_band(avg: float, sd: float, n: int) -> tuple[float, float]:
    """95% range for the average of n trades: avg ± 1.96·sd/√n."""
    if n <= 0:
        raise ValueError("n must be positive")
    half = 1.96 * sd / math.sqrt(n)
    return avg - half, avg + half


def largest_remainder(shares: Sequence[float], total: int = 100) -> list[int]:
    """Round shares to whole units that add up to exactly `total` (for the 100-cell waffle)."""
    whole = sum(shares)
    if whole <= 0:
        return [0] * len(shares)
    raw = [s / whole * total for s in shares]
    floors = [math.floor(r) for r in raw]
    left = total - sum(floors)
    by_remainder = sorted(range(len(raw)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in by_remainder[:left]:
        floors[i] += 1
    return floors


def sum_series(series: Sequence[Sequence[ValuePoint]]) -> list[ValuePoint]:
    """Add value series by date.

    A series with no point on a date contributes its last known value. A series that appears after the
    first date brings its opening value in as a flow, so a newly linked account is not counted as growth.
    """
    dates = sorted({p.date for s in series for p in s})
    by_date = [{p.date: p for p in s} for s in series]
    last: list[float | None] = [None] * len(series)
    out: list[ValuePoint] = []
    for n, day in enumerate(dates):
        total = 0.0
        flow = 0.0
        for i, points in enumerate(by_date):
            point = points.get(day)
            if point is not None:
                if last[i] is None and n > 0:
                    flow += point.value
                else:
                    flow += point.net_flow
                last[i] = point.value
            if last[i] is not None:
                total += last[i]
        out.append(ValuePoint(date=day, value=round(total, 2), net_flow=round(flow, 2)))
    return out
