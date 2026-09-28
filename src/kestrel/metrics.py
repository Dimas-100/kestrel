"""Pure money math shared by every view. No I/O, no clock."""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Sequence

from .contract import ValuePoint


def growth_index(points: Sequence[ValuePoint]) -> list[float]:
    """Time-weighted growth index starting at 1.0.

    Each step is the day's change net of that day's deposits and withdrawals, so adding money never
    looks like performance. A deposit can be on the books before the balance shows it; when taking it
    would leave a negative starting value, it waits for the next point instead of turning the line over.
    """
    if not points:
        return []
    index = [1.0]
    waiting = 0.0
    for prev, cur in zip(points, points[1:]):
        flow = cur.net_flow + waiting
        waiting = flow if prev.value > 0 and cur.value - flow < 0 else 0.0
        step = (cur.value - flow + waiting) / prev.value if prev.value > 0 else 1.0
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


def opening_on(points: Sequence[ValuePoint], start: dt.date) -> list[ValuePoint]:
    """The points after `start`, opening on `start` with the value held then (the last point on or before it), so
    lines that begin on different days can be measured from one. A series that begins after `start` is returned as
    it is: nothing was held on `start`."""
    before = [p for p in points if p.date <= start]
    after = [p for p in points if p.date > start]
    return [ValuePoint(date=start, value=before[-1].value), *after] if before else after


def rsi(closes: Sequence[float], period: int = 2) -> list[float | None]:
    """Wilder's relative strength index, aligned with `closes`: None until `period` changes have been seen."""
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    changes = [b - a for a, b in zip(closes, closes[1:])]
    gain = sum(max(c, 0.0) for c in changes[:period]) / period
    loss = sum(max(-c, 0.0) for c in changes[:period]) / period

    def value() -> float:
        if gain == 0 and loss == 0:
            return 50.0
        return 100.0 if loss == 0 else 100.0 - 100.0 / (1.0 + gain / loss)

    out[period] = value()
    for i in range(period, len(changes)):
        gain = (gain * (period - 1) + max(changes[i], 0.0)) / period
        loss = (loss * (period - 1) + max(-changes[i], 0.0)) / period
        out[i + 1] = value()
    return out
