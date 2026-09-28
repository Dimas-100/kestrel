"""The Books list and one page per book, computed from one Snapshot: how is each book of money doing?

`BookRow`, `book_rows()` and `MIN_TRADES_FOR_VERDICT` used to live in `views/home.py`; they moved here so the Books
pages and Home share one verdict computation. `home.py` imports them back (`from .books import ...`), so this module
must never import from `.home` — that would be a circular import.
"""

from __future__ import annotations

import datetime as dt
import math
from statistics import fmean
from typing import Literal

from ..contract import Benchmark, Run, Snapshot, Trade, ValuePoint
from ..metrics import expected_band, growth_index, max_drawdown_pct
from ..profile import Profile
from ._base import View

MIN_TRADES_FOR_VERDICT = 10  # fewer closed trades than this is "too early" to judge a book
SPARK_POINTS = 60  # the Books list' sparkline


class BookRow(View):
    id: str
    name: str
    strategy: str
    money: Literal["real", "paper"]
    status: str
    value: float
    day_change: float | None
    since_pct: float | None
    started: dt.date
    trades: int
    per_trade_pct: float | None
    band_lo: float | None
    band_hi: float | None
    verdict: Literal["in_band", "below", "above", "early", "none"]
    slots_used: int
    slots_total: int | None
    next_run: dt.datetime | None


def book_rows(snapshot: Snapshot) -> list[BookRow]:
    history = {s.id: s.points for s in snapshot.book_history}
    strategies = {s.id: s for s in snapshot.strategies}
    rows = []
    for book in snapshot.books:
        points = list(history.get(book.id, []))
        returns = [t.return_pct for t in snapshot.trades if t.book_id == book.id]
        strategy = strategies.get(book.strategy_id)
        expected = strategy.expected if strategy else None
        per_trade_raw = fmean(returns) if returns else None
        per_trade = round(per_trade_raw, 3) if per_trade_raw is not None else None
        lo = hi = None
        if not returns or expected is None:
            verdict = "none"
        elif len(returns) < MIN_TRADES_FOR_VERDICT:
            verdict = "early"
        else:
            lo, hi = expected_band(expected.avg_trade_pct, expected.sd_trade_pct, len(returns))
            # compare the unrounded mean: a mean that rounds to the band edge must not read as "in_band" (the
            # scorecard on the strategy page compares the same unrounded mean, so the two pages never disagree)
            verdict = "below" if per_trade_raw < lo else "above" if per_trade_raw > hi else "in_band"
        rows.append(BookRow(
            id=book.id, name=book.name, strategy=strategy.name if strategy else book.strategy_id, money=book.money,
            status=book.status, value=book.value,
            day_change=round(points[-1].value - points[-2].value - points[-1].net_flow, 2) if len(points) > 1 else None,
            since_pct=round((growth_index(points)[-1] - 1) * 100, 2) if len(points) > 1 else None,
            started=book.started, trades=len(returns), per_trade_pct=per_trade,
            band_lo=round(lo, 3) if lo is not None else None, band_hi=round(hi, 3) if hi is not None else None,
            verdict=verdict, slots_used=sum(1 for p in snapshot.positions if p.book_id == book.id),
            slots_total=book.slots_total, next_run=book.next_run,
        ))
    return rows


class BooksRow(BookRow):
    spark: list[float]  # the last 60 values of the book's history, oldest first


class BooksView(View):
    as_of: dt.datetime
    real_value: float
    paper_value: float
    rows: list[BooksRow]  # every book, real first then paper


class EquitySeries(View):
    dates: list[dt.date]
    values: list[float]  # growth index (%) since the book's first point
    benchmark: list[float | None]  # the benchmark over the same dates, indexed from the same start day
    return_pct: float
    max_drop_pct: float


class DrawdownSeries(View):
    dates: list[dt.date]
    values: list[float]  # percent below the running peak, always <= 0


class Scorecard(View):
    trades: int
    win_rate: float | None
    avg_trade_pct: float | None
    avg_win_pct: float | None
    avg_loss_pct: float | None
    total_pnl: float
    best_pct: float | None
    worst_pct: float | None
    band_lo: float | None
    band_hi: float | None
    verdict: Literal["in_band", "below", "above", "early", "none"]


class BookPosition(View):
    symbol: str
    quantity: float
    entry_price: float
    last_price: float
    stop_price: float | None
    stop_resting: bool | None  # True: a stop rests but its level isn't reported (see contract.Position)
    room_pct: float | None  # distance from the last price down to the stop
    pnl: float
    pnl_pct: float | None
    opened: dt.date
    days: int
    flag: Literal["no_stop"] | None


class BookView(View):
    as_of: dt.datetime
    book: BooksRow
    strategy_id: str
    strategy_name: str
    account_id: str | None
    equity: EquitySeries
    drawdown: DrawdownSeries
    scorecard: Scorecard
    positions: list[BookPosition]
    trades: list[Trade]  # newest first
    runs: list[Run]  # this book's, next first then newest


def _spark(points: list[ValuePoint]) -> list[float]:
    return [p.value for p in points[-SPARK_POINTS:]]


def _books_rows(snapshot: Snapshot) -> list[BooksRow]:
    history = {s.id: s.points for s in snapshot.book_history}
    return [BooksRow(**row.model_dump(), spark=_spark(list(history.get(row.id, [])))) for row in book_rows(snapshot)]


def books_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> BooksView:
    rows = _books_rows(snapshot)
    ordered = sorted(rows, key=lambda r: r.money != "real")  # real first; a stable sort keeps each group's order
    return BooksView(
        as_of=now, real_value=round(sum(r.value for r in rows if r.money == "real"), 2),
        paper_value=round(sum(r.value for r in rows if r.money == "paper"), 2), rows=ordered,
    )


def _from(points: list[ValuePoint], start: dt.date) -> list[ValuePoint]:
    """The points from `start` on, opening on `start` with the value held then (the last point on or before it)."""
    before = [p for p in points if p.date <= start]
    after = [p for p in points if p.date > start]
    return [ValuePoint(date=start, value=before[-1].value), *after] if before else after


def _equity(history: list[ValuePoint], benchmark: Benchmark | None) -> EquitySeries:
    if len(history) < 2:
        return EquitySeries(dates=[], values=[], benchmark=[], return_pct=0.0, max_drop_pct=0.0)
    idx = growth_index(history)
    dates = [p.date for p in history]
    bench_values: list[float | None] = [None] * len(dates)
    if benchmark is not None:
        aligned = _from(list(benchmark.points), dates[0])
        if len(aligned) >= 2:
            bench_idx = growth_index(aligned)
            by_date = {p.date: i for p, i in zip(aligned, bench_idx)}
            last: float | None = None
            bench_values = []
            for d in dates:
                last = by_date.get(d, last)
                bench_values.append(None if last is None else round((last - 1) * 100, 3))
    return EquitySeries(dates=dates, values=[round((v - 1) * 100, 3) for v in idx], benchmark=bench_values,
                        return_pct=round((idx[-1] - 1) * 100, 2), max_drop_pct=round(max_drawdown_pct(idx), 2))


def _drawdown(history: list[ValuePoint]) -> DrawdownSeries:
    if len(history) < 2:
        return DrawdownSeries(dates=[], values=[])
    idx = growth_index(history)
    peak = -math.inf
    values = []
    for v in idx:
        peak = max(peak, v)
        values.append(round((v / peak - 1) * 100, 3) if peak > 0 else 0.0)
    return DrawdownSeries(dates=[p.date for p in history], values=values)


def _scorecard(snapshot: Snapshot, book_id: str, row: BookRow) -> Scorecard:
    trades = [t for t in snapshot.trades if t.book_id == book_id]
    returns = [t.return_pct for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    n = len(returns)
    return Scorecard(
        trades=n, win_rate=round(len(wins) / n * 100, 1) if n else None,
        avg_trade_pct=row.per_trade_pct, avg_win_pct=round(fmean(wins), 2) if wins else None,
        avg_loss_pct=round(fmean(losses), 2) if losses else None,
        total_pnl=round(sum(t.pnl for t in trades), 2),
        best_pct=round(max(returns), 2) if returns else None, worst_pct=round(min(returns), 2) if returns else None,
        band_lo=row.band_lo, band_hi=row.band_hi, verdict=row.verdict,
    )


def _positions(snapshot: Snapshot, book_id: str, today: dt.date) -> list[BookPosition]:
    out = []
    for p in snapshot.positions:
        if p.book_id != book_id:
            continue
        room = round((p.last_price - p.stop_price) / p.last_price * 100, 2) \
            if p.stop_price is not None and p.last_price > 0 else None
        out.append(BookPosition(
            symbol=p.symbol, quantity=p.quantity, entry_price=p.entry_price, last_price=p.last_price,
            stop_price=p.stop_price, stop_resting=p.stop_resting, room_pct=room,
            pnl=round((p.last_price - p.entry_price) * p.quantity, 2),
            pnl_pct=round((p.last_price - p.entry_price) / p.entry_price * 100, 2) if p.entry_price else None,
            opened=p.opened, days=(today - p.opened).days,
            flag="no_stop" if p.stop_price is None and p.stop_resting is not True else None,
        ))
    return out


def _book_trades(snapshot: Snapshot, book_id: str) -> list[Trade]:
    mine = [t for t in snapshot.trades if t.book_id == book_id]
    return sorted(mine, key=lambda t: (t.closed, t.opened, t.symbol), reverse=True)


def _book_runs(snapshot: Snapshot, book_id: str, now: dt.datetime) -> list[Run]:
    mine = [r for r in snapshot.runs if r.book_id == book_id]
    future = sorted((r for r in mine if r.time > now), key=lambda r: r.time)
    past = sorted((r for r in mine if r.time <= now), key=lambda r: r.time, reverse=True)
    return [*future, *past]


def book_view(snapshot: Snapshot, profile: Profile, now: dt.datetime, book_id: str) -> BookView | None:
    """One book, or None when there is no book with that id."""
    book = next((b for b in snapshot.books if b.id == book_id), None)
    if book is None:
        return None
    row = next(r for r in _books_rows(snapshot) if r.id == book_id)
    strategy = next((s for s in snapshot.strategies if s.id == book.strategy_id), None)
    history = list(next((s.points for s in snapshot.book_history if s.id == book_id), []))
    today = now.astimezone(profile.tz).date()
    return BookView(
        as_of=now, book=row, strategy_id=book.strategy_id,
        strategy_name=strategy.name if strategy else book.strategy_id, account_id=book.account_id,
        equity=_equity(history, snapshot.benchmark), drawdown=_drawdown(history),
        scorecard=_scorecard(snapshot, book_id, row), positions=_positions(snapshot, book_id, today),
        trades=_book_trades(snapshot, book_id), runs=_book_runs(snapshot, book_id, now),
    )
