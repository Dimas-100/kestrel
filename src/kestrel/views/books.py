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
from urllib.parse import quote

from ..contract import Benchmark, Book, Position, Run, Snapshot, Strategy, Trade, ValuePoint
from ..metrics import expected_band, growth_index, max_drawdown_pct, opening_on
from ..profile import Profile
from ._base import View

MIN_TRADES_FOR_VERDICT = 10  # fewer closed trades than this is "too early" to judge a book
SPARK_POINTS = 60  # the Books list' sparkline
STALE_SESSIONS = 3  # marks older than this many sessions are called out

Protection = Literal["stop", "signal", ""]
# no_stop: a stop is expected and the source says there is none; unknown_stop: a stop is expected (or the strategy
# doesn't say) and none is on record; signal_exit: the strategy exits on a signal, a resting stop is not expected
StopFlag = Literal["no_stop", "unknown_stop", "signal_exit"] | None


class Attention(View):
    level: Literal["serious", "warning", "note"]
    title: str
    detail: str
    link: str


def protection_of(strategy: Strategy | None) -> Protection:
    """How a strategy protects a lot: what it says, else "stop" when its rule has a Protect step, else unknown."""
    if strategy is None:
        return ""
    if strategy.protection:
        return strategy.protection
    return "stop" if any(s.label.lower() == "protect" and s.kind == "step" for s in strategy.steps) else ""


def stop_flag(p: Position, protection: Protection) -> StopFlag:
    """The one word about a lot's stop. A reported stop (a level, or a resting one) is never flagged; a source
    that says there is NO stop is flagged as missing; a lot with nothing on record is "not on record" — unless the
    strategy exits on a signal, in which case no stop is expected."""
    if p.stop_price is not None or p.stop_resting is True:
        return None
    if p.stop_resting is False:
        return "no_stop"
    return "signal_exit" if protection == "signal" else "unknown_stop"


def stop_attention(book: Book, p: Position, flag: StopFlag) -> Attention | None:
    """Home's and the strategy page's item for a real lot's stop: serious when the source says there is none,
    a warning when nothing is on record; never for paper, never for a signal-exit strategy."""
    if book.money != "real" or flag is None or flag == "signal_exit":
        return None
    link = f"/books/{quote(book.id, safe='')}"
    if flag == "no_stop":
        return Attention(level="serious", title=f"{p.symbol} has no resting stop",
                         detail=f"{book.name} · real — the source reports no protective stop", link=link)
    return Attention(level="warning", title=f"{p.symbol}'s stop isn't on record",
                     detail=f"{book.name} · real — no protective stop reported; it may rest unreported", link=link)


def last_session(now: dt.datetime, tz: dt.tzinfo) -> dt.date:
    """The last weekday whose close has passed (16:00 local), as a stand-in for the last trading session."""
    local = now.astimezone(tz)
    day = local.date()
    if day.weekday() >= 5 or local.time() < dt.time(16, 0):
        day -= dt.timedelta(days=1)
    while day.weekday() >= 5:
        day -= dt.timedelta(days=1)
    return day


def sessions_old(prices_as_of: dt.date, session: dt.date) -> int:
    """Weekdays after `prices_as_of` up to and including `session` (0 when the marks are from it)."""
    n, day = 0, prices_as_of
    while day < session:
        day += dt.timedelta(days=1)
        n += day.weekday() < 5
    return n


def freshness(book: Book, session: dt.date) -> str:
    """"fresh", "oldest mark 2 sessions old", or "not reported" — judged by the book's oldest position mark."""
    if book.prices_as_of is None:
        return "not reported"
    old = sessions_old(book.prices_as_of, session)
    return "fresh" if old == 0 else f"oldest mark {old} session{'s' if old != 1 else ''} old"


class BookRow(View):
    id: str
    name: str
    strategy: str
    money: Literal["real", "paper"]
    status: str
    value: float  # what the source calls the book's value (a paper book's equity; a real sleeve's open lots)
    # the two figures every book can be compared on: what it holds at the last price, and the money it works with
    invested: float  # open positions at their last price
    equity: float | None  # the book's capital when the source sends one, else its value; None when neither
    capital_basis: str  # what `equity` and the return are measured against, in the source's words
    unrealized_pnl: float
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
    prices_as_of: dt.date | None
    protection: Protection


def book_rows(snapshot: Snapshot) -> list[BookRow]:
    history = {s.id: s.points for s in snapshot.book_history}
    strategies = {s.id: s for s in snapshot.strategies}
    rows = []
    for book in snapshot.books:
        points = list(history.get(book.id, []))
        returns = [t.return_pct for t in snapshot.trades if t.book_id == book.id]
        strategy = strategies.get(book.strategy_id)
        expected = strategy.expected if strategy else None
        positions = [p for p in snapshot.positions if p.book_id == book.id]
        invested = round(sum(p.quantity * p.last_price for p in positions), 2)
        unrealized = round(sum((p.last_price - p.entry_price) * p.quantity for p in positions), 2)
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
            status=book.status, value=book.value, invested=invested,
            equity=book.capital if book.capital is not None else book.value,
            capital_basis=book.capital_basis or ("the book's own value" if book.capital is None else ""),
            unrealized_pnl=unrealized, prices_as_of=book.prices_as_of, protection=protection_of(strategy),
            day_change=round(points[-1].value - points[-2].value - points[-1].net_flow, 2) if len(points) > 1 else None,
            since_pct=round((growth_index(points)[-1] - 1) * 100, 2) if len(points) > 1 else None,
            started=book.started, trades=len(returns), per_trade_pct=per_trade,
            band_lo=round(lo, 3) if lo is not None else None, band_hi=round(hi, 3) if hi is not None else None,
            verdict=verdict, slots_used=sum(1 for p in snapshot.positions if p.book_id == book.id),
            slots_total=book.slots_total, next_run=book.next_run,
        ))
    return rows


class BooksRow(BookRow):
    # the last 60 values of the book's growth since it started, in percent (the equity line's measure, so a deposit
    # never reads as a gain), oldest first; the last is `since_pct`
    spark: list[float]


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
    benchmark_label: str
    # the first day the benchmark is drawn from: the book's first day, or later when the benchmark's own history
    # starts after it (it is then indexed from that later day, and the panel says so); None with no benchmark line
    benchmark_from: dt.date | None


class DrawdownSeries(View):
    dates: list[dt.date]
    values: list[float]  # percent below the running peak, always <= 0


class Scorecard(View):
    trades: int
    win_rate: float | None
    avg_trade_pct: float | None
    avg_win_pct: float | None
    avg_loss_pct: float | None
    total_pnl: float  # realized: the closed trades
    unrealized_pnl: float  # the open positions at their last price
    combined_pnl: float  # realized + unrealized
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
    flag: StopFlag
    note: str  # the source's own note on the lot: a fallback price, a stale mark, a stop placed


class BookView(View):
    as_of: dt.datetime
    book: BooksRow
    strategy_id: str
    strategy_name: str
    account_id: str | None
    attention: list[Attention]  # what needs you on this book: stops, its alerts, late runs, stale marks
    notes: list[str]  # the distinct notes the source put on its positions (a fallback price, a stale mark)
    freshness: str  # "fresh", "oldest mark 2 sessions old", "not reported"
    equity: EquitySeries
    drawdown: DrawdownSeries
    scorecard: Scorecard
    positions: list[BookPosition]
    trades: list[Trade]  # newest first
    runs: list[Run]  # this book's, next first then newest


def _spark(points: list[ValuePoint]) -> list[float]:
    if len(points) < 2:
        return []
    # rounded as since_pct is, so the line ends on the figure in the "since start" column
    return [round((v - 1) * 100, 2) for v in growth_index(points)[-SPARK_POINTS:]]


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


def _equity(history: list[ValuePoint], benchmark: Benchmark | None, label: str) -> EquitySeries:
    if len(history) < 2:
        return EquitySeries(dates=[], values=[], benchmark=[], return_pct=0.0, max_drop_pct=0.0,
                            benchmark_label=label, benchmark_from=None)
    idx = growth_index(history)
    dates = [p.date for p in history]
    bench_values: list[float | None] = [None] * len(dates)
    bench_from = None
    if benchmark is not None:
        # the benchmark's points in date order (a source may send them unsorted), opened on the book's first day;
        # a benchmark whose history starts later is indexed from its own first day inside the window, and says so
        aligned = [p for p in opening_on(sorted(benchmark.points, key=lambda p: p.date), dates[0])
                   if p.date <= dates[-1]]
        if len(aligned) >= 2:
            bench_idx = growth_index(aligned)
            by_date = {p.date: i for p, i in zip(aligned, bench_idx)}
            bench_from = aligned[0].date
            last: float | None = None
            bench_values = []
            for d in dates:
                last = by_date.get(d, last)
                bench_values.append(None if last is None else round((last - 1) * 100, 3))
    return EquitySeries(dates=dates, values=[round((v - 1) * 100, 3) for v in idx], benchmark=bench_values,
                        return_pct=round((idx[-1] - 1) * 100, 2), max_drop_pct=round(max_drawdown_pct(idx), 2),
                        benchmark_label=label, benchmark_from=bench_from)


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
    realized = round(sum(t.pnl for t in trades), 2)
    return Scorecard(
        trades=n, win_rate=round(len(wins) / n * 100, 1) if n else None,
        avg_trade_pct=row.per_trade_pct, avg_win_pct=round(fmean(wins), 2) if wins else None,
        avg_loss_pct=round(fmean(losses), 2) if losses else None,
        total_pnl=realized, unrealized_pnl=row.unrealized_pnl, combined_pnl=round(realized + row.unrealized_pnl, 2),
        best_pct=round(max(returns), 2) if returns else None, worst_pct=round(min(returns), 2) if returns else None,
        band_lo=row.band_lo, band_hi=row.band_hi, verdict=row.verdict,
    )


def _positions(snapshot: Snapshot, book_id: str, today: dt.date, protection: Protection = "") -> list[BookPosition]:
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
            opened=p.opened, days=(today - p.opened).days, flag=stop_flag(p, protection), note=p.note,
        ))
    return out


def _book_attention(snapshot: Snapshot, book: Book, strategy: Strategy | None, protection: Protection,
                    now: dt.datetime, tz: dt.tzinfo) -> list[Attention]:
    """What needs you on this book: its lots' stops, the snapshot's alerts that point at it or its strategy, its
    late or failed runs, and marks older than STALE_SESSIONS."""
    items: list[Attention] = []
    page = f"/books/{quote(book.id, safe='')}"
    strategy_page = f"/strategies/{quote(book.strategy_id, safe='')}"
    for p in snapshot.positions:
        if p.book_id == book.id:
            item = stop_attention(book, p, stop_flag(p, protection))
            if item:
                items.append(item)
    for a in snapshot.alerts:
        if a.link in (page, strategy_page):
            items.append(Attention(level=a.level, title=a.title, detail=a.detail, link=a.link))
    for r in snapshot.runs:
        if r.book_id == book.id and r.status in ("late", "failed"):
            when = r.time.astimezone(tz).strftime("%a %H:%M")
            items.append(Attention(level="warning", title=f"{r.label} {r.status} {when}", detail=r.detail,
                                   link="/activity"))
    session = last_session(now, tz)
    has_positions = any(p.book_id == book.id for p in snapshot.positions)
    if book.prices_as_of is not None and has_positions and sessions_old(book.prices_as_of, session) > STALE_SESSIONS:
        items.append(Attention(level="warning", title=f"Marks are from {book.prices_as_of.isoformat()}",
                               detail=f"{sessions_old(book.prices_as_of, session)} sessions old · the P&L and the "
                               "room to each stop rest on them", link=page))
    order = {"serious": 0, "warning": 1, "note": 2}
    return sorted(items, key=lambda a: order[a.level])


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
    protection = protection_of(strategy)
    label = snapshot.benchmark.label if snapshot.benchmark else profile.benchmark.label
    notes = sorted({p.note for p in snapshot.positions if p.book_id == book_id and p.note})
    return BookView(
        as_of=now, book=row, strategy_id=book.strategy_id,
        strategy_name=strategy.name if strategy else book.strategy_id, account_id=book.account_id,
        attention=_book_attention(snapshot, book, strategy, protection, now, profile.tz), notes=notes,
        freshness=freshness(book, last_session(now, profile.tz)),
        equity=_equity(history, snapshot.benchmark, label), drawdown=_drawdown(history),
        scorecard=_scorecard(snapshot, book_id, row), positions=_positions(snapshot, book_id, today, protection),
        trades=_book_trades(snapshot, book_id), runs=_book_runs(snapshot, book_id, now),
    )
