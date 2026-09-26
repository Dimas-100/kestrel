"""The Strategy pages, computed from one Snapshot: how does a strategy trade, and is it behaving the way its
backtest said it would?"""

from __future__ import annotations

import datetime as dt
import math
from statistics import fmean
from typing import Literal

from ..contract import Bar, Book, Expected, Indicator, Money, Snapshot, Step, Trade, TradeChart, ValuePoint, WatchItem
from ..metrics import expected_band, growth_index, max_drawdown_pct, sum_series
from ..profile import Profile
from .home import MIN_TRADES_FOR_VERDICT, View, _book_rows

BUCKET_LOW, BUCKETS = -10, 20  # 1-point buckets from -10% to +10%; returns beyond fold into the end buckets
FUNNEL_FROM = 3  # the expected band starts at the third trade
MONTH_DAYS = 365.25 / 12
SESSIONS = 40  # "Where the money works" looks at the last 40 sessions
RECENT = 8  # trades listed beside the anatomy chart
MONTHS = 12
YEAR_DAYS, EARLY_DAYS = 365, 90  # a yearly figure needs 90 days of history; under a year it is "early"

Verdict = Literal["in_band", "below", "above", "early", "none"]
Status = Literal["ok", "above", "below", "early", "none"]


class BookChip(View):
    id: str
    name: str
    money: Money
    status: str
    open: int  # open positions
    trades: int  # closed trades


class StrategyCard(View):
    id: str
    name: str
    summary: str
    books: list[BookChip]
    book: Money | None  # the money of the book the band describes: real when there is one
    trades: int
    per_trade_pct: float | None
    band_lo: float | None
    band_hi: float | None
    verdict: Verdict


class StrategiesView(View):
    strategies: list[StrategyCard]


class Bucket(View):
    low: int  # returns from `low` up to low + 1 percent; the end buckets also hold everything beyond them
    count: int
    share: float  # percent of the book's closed trades
    expected: float | None  # the backtest's share, when it reports a 20-bucket distribution


class ScoreRow(View):
    key: Literal["win_rate", "avg_trade", "avg_win", "avg_loss", "per_month"]
    label: str
    actual: float | None
    expected: float | None
    status: Status  # "above" / "below": outside the band for that measure; "early": under 10 closed trades


class OtherBook(View):
    id: str
    money: Money
    trades: int
    per_trade_pct: float | None
    win_rate: float | None


class Behaving(View):
    trades: int
    buckets: list[Bucket]
    scorecard: list[ScoreRow]
    review_at: int | None
    other: OtherBook | None


class FunnelLine(View):
    book_id: str
    money: Money
    values: list[float]  # the running mean after each closed trade, in close order


class Funnel(View):
    expected: float | None
    lines: list[FunnelLine]  # the primary book first
    lo: list[float | None]  # the expected 95% band after trade n (index n - 1); None before trade 3
    hi: list[float | None]


class Slots(View):
    book_id: str | None
    total: int | None  # the book's slots; None when it doesn't report them
    days: list[dt.date]  # the last 40 sessions
    used: list[int]  # slots in use each session
    avg_used: float | None
    working_pct: float | None  # the average in use as a share of the slots
    idle: int  # sessions with nothing in use
    watch: list[WatchItem]


class RecentTrade(View):
    key: str  # "book_id|symbol|opened": how the page picks a trade's chart
    symbol: str
    money: Money
    opened: dt.date
    closed: dt.date
    return_pct: float
    r_multiple: float | None
    exit_reason: str
    sessions: int  # sessions held: the weekdays after the open day, up to and including the close
    chart: bool


class AnatomyChart(View):
    key: str
    bars: list[Bar]
    indicator: Indicator | None
    stop: float | None
    entry: int  # index of the entry bar
    exit: int  # index of the exit bar
    entry_price: float
    exit_price: float


class Anatomy(View):
    recent: list[RecentTrade]  # the primary book's last 8 closed trades, newest first
    charts: list[AnatomyChart]  # for the recent trades that have one
    selected: str | None  # the newest charted trade


class WorthPoint(View):
    key: Literal["backtest", "book", "long_term", "benchmark"]
    label: str
    period: str  # "2006–2020" for a backtest, "12 months" or "5 years" for a history
    early: bool  # 90 to 364 days of history: annualized, but early
    return_pct: float  # yearly return
    drop_pct: float  # worst drop, as a positive magnitude


class Worth(View):
    points: list[WorthPoint]


class Month(View):
    month: str  # "2026-09"
    book: float | None  # the primary book's return that month, in percent
    long_term: float | None
    ahead: bool | None  # the book did better than the long-term accounts


class MonthFigure(View):
    month: str
    value: float


class Monthly(View):
    months: list[Month]  # the last 12 calendar months, oldest first
    ahead: int
    compared: int  # months with both figures
    best: MonthFigure | None
    worst: MonthFigure | None


class TradeRow(View):
    symbol: str
    money: Money
    opened: dt.date
    closed: dt.date
    days_held: int  # calendar days
    return_pct: float
    r_multiple: float | None
    pnl: float
    exit_reason: str


class StrategyView(View):
    id: str
    name: str
    summary: str
    books: list[BookChip]
    book: Money | None  # the primary book's money
    primary: str | None  # the primary book's id
    toggle: bool  # a real and a paper book: the page offers Real | Paper
    expected: Expected | None
    steps: list[Step]
    sizing: str
    behaving: Behaving
    funnel: Funnel
    slots: Slots
    anatomy: Anatomy
    worth: Worth
    monthly: Monthly
    trades: list[TradeRow]  # the primary book's closed trades, newest first


def closed_trades(snapshot: Snapshot, book_id: str) -> list[Trade]:
    """A book's closed trades in close order; ties by opened date, then symbol."""
    return sorted((t for t in snapshot.trades if t.book_id == book_id), key=lambda t: (t.closed, t.opened, t.symbol))


def _pick(books: list[Book], money: Money, counts: dict[str, int]) -> Book | None:
    """The book of that money with the most closed trades; a tie goes to the first listed."""
    return max((b for b in books if b.money == money), key=lambda b: counts[b.id], default=None)


def _primary(books: list[Book], want: Money, counts: dict[str, int]) -> tuple[Book | None, Book | None]:
    """The book the page focuses on (the other money's book when there is none of the one asked for), and the best
    book of the other money."""
    primary = _pick(books, want, counts) or _pick(books, "paper" if want == "real" else "real", counts)
    if primary is None:
        return None, None
    return primary, _pick(books, "paper" if primary.money == "real" else "real", counts)


def _chips(snapshot: Snapshot, books: list[Book], counts: dict[str, int]) -> list[BookChip]:
    return [BookChip(id=b.id, name=b.name, money=b.money, status=b.status, trades=counts[b.id],
                     open=sum(1 for p in snapshot.positions if p.book_id == b.id)) for b in books]


def buckets(returns: list[float], distribution: list[float]) -> list[Bucket]:
    counts = [0] * BUCKETS
    for r in returns:
        counts[min(BUCKETS - 1, max(0, math.floor(r) - BUCKET_LOW))] += 1
    n = len(returns)
    expected = distribution if len(distribution) == BUCKETS else None
    return [Bucket(low=BUCKET_LOW + i, count=c, share=round(c / n * 100, 2) if n else 0.0,
                   expected=expected[i] if expected else None) for i, c in enumerate(counts)]


def _within_half(expected: float) -> tuple[float, float]:
    """The ±50% range around an expected value, low end first (for a negative value too)."""
    a, b = expected * 0.5, expected * 1.5
    return min(a, b), max(a, b)


def _row(key, label, actual: float | None, expected: float | None, band: tuple[float, float] | None,
         n: int) -> ScoreRow:
    if expected is None:
        status: Status = "none"
    elif n < MIN_TRADES_FOR_VERDICT:
        status = "early"
    elif actual is None or band is None:
        status = "none"
    else:
        status = "below" if actual < band[0] else "above" if actual > band[1] else "ok"
    return ScoreRow(key=key, label=label, actual=actual, expected=expected, status=status)


def _scorecard(trades: list[Trade], expected: Expected | None, book: Book | None, today: dt.date) -> list[ScoreRow]:
    returns = [t.return_pct for t in trades]
    n = len(returns)
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    months = max(1.0, (today - book.started).days / MONTH_DAYS) if book else 1.0
    win_rate = round(len(wins) / n * 100, 1) if n else None
    avg_trade = round(fmean(returns), 2) if n else None
    avg_win = round(fmean(wins), 2) if wins else None
    avg_loss = round(fmean(losses), 2) if losses else None
    per_month = round(n / months, 1) if n else None
    e = expected
    win_band = avg_band = None
    if e is not None and n:
        p = e.win_rate / 100
        half = 1.96 * math.sqrt(p * (1 - p) / n) * 100
        win_band = (e.win_rate - half, e.win_rate + half)
        avg_band = expected_band(e.avg_trade_pct, e.sd_trade_pct, n)
    return [
        _row("win_rate", "Win rate", win_rate, e.win_rate if e else None, win_band, n),
        _row("avg_trade", "Average per trade", avg_trade, e.avg_trade_pct if e else None, avg_band, n),
        _row("avg_win", "Average win", avg_win, e.avg_win_pct if e else None,
             _within_half(e.avg_win_pct) if e else None, n),
        _row("avg_loss", "Average loss", avg_loss, e.avg_loss_pct if e else None,
             _within_half(e.avg_loss_pct) if e else None, n),
        _row("per_month", "Trades per month", per_month, e.trades_per_month if e else None,
             _within_half(e.trades_per_month) if e else None, n),
    ]


def _other_book(book: Book | None, trades: list[Trade]) -> OtherBook | None:
    if book is None:
        return None
    returns = [t.return_pct for t in trades]
    return OtherBook(id=book.id, money=book.money, trades=len(returns),
                     per_trade_pct=round(fmean(returns), 2) if returns else None,
                     win_rate=round(sum(r > 0 for r in returns) / len(returns) * 100, 1) if returns else None)


def running_mean(trades: list[Trade]) -> list[float]:
    out: list[float] = []
    total = 0.0
    for n, t in enumerate(trades, 1):
        total += t.return_pct
        out.append(round(total / n, 3))
    return out


def _funnel(lines: list[FunnelLine], expected: Expected | None) -> Funnel:
    n = max((len(line.values) for line in lines), default=0)
    lo: list[float | None] = []
    hi: list[float | None] = []
    for k in range(1, n + 1):
        if expected is None or k < FUNNEL_FROM:
            lo.append(None)
            hi.append(None)
        else:
            low, high = expected_band(expected.avg_trade_pct, expected.sd_trade_pct, k)
            lo.append(round(low, 3))
            hi.append(round(high, 3))
    return Funnel(expected=expected.avg_trade_pct if expected else None, lines=lines, lo=lo, hi=hi)


def _weekdays_ending(end: dt.date, count: int) -> list[dt.date]:
    days: list[dt.date] = []
    day = end
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= dt.timedelta(days=1)
    return days[::-1]


def _history(snapshot: Snapshot, book_id: str) -> list[ValuePoint]:
    return list(next((s.points for s in snapshot.book_history if s.id == book_id), []))


def _slots(snapshot: Snapshot, book: Book | None, trades: list[Trade], watch: list[WatchItem],
           today: dt.date) -> Slots:
    if book is None or book.slots_total is None:
        return Slots(book_id=book.id if book else None, total=None, days=[], used=[], avg_used=None,
                     working_pct=None, idle=0, watch=watch)
    days = sorted({p.date for p in _history(snapshot, book.id)})[-SESSIONS:] or _weekdays_ending(today, SESSIONS)
    opened = [p.opened for p in snapshot.positions if p.book_id == book.id]
    used = [sum(1 for t in trades if t.opened <= d <= t.closed) + sum(1 for o in opened if o <= d) for d in days]
    avg = fmean(used)
    return Slots(book_id=book.id, total=book.slots_total, days=days, used=used, avg_used=round(avg, 1),
                 working_pct=round(avg / book.slots_total * 100, 1) if book.slots_total else None,
                 idle=sum(1 for u in used if u == 0), watch=watch)


def _key(book_id: str, symbol: str, opened: dt.date) -> str:
    return f"{book_id}|{symbol}|{opened.isoformat()}"


def _sessions_held(opened: dt.date, closed: dt.date) -> int:
    return sum(1 for i in range(1, (closed - opened).days + 1) if (opened + dt.timedelta(days=i)).weekday() < 5)


def _anatomy_chart(chart: TradeChart, trade: Trade) -> AnatomyChart | None:
    dates = [b.date for b in chart.bars]
    if trade.opened not in dates:
        return None  # a chart that doesn't show the entry can't explain the trade
    entry = dates.index(trade.opened)
    exit_ = max(i for i, d in enumerate(dates) if d <= trade.closed)
    return AnatomyChart(key=_key(trade.book_id, trade.symbol, trade.opened), bars=list(chart.bars),
                        indicator=chart.indicator, stop=chart.stop, entry=entry, exit=exit_,
                        entry_price=trade.entry_price, exit_price=trade.exit_price)


def _anatomy(snapshot: Snapshot, book: Book | None, trades: list[Trade]) -> Anatomy:
    if book is None:
        return Anatomy(recent=[], charts=[], selected=None)
    by_key = {(c.book_id, c.symbol, c.opened): c for c in snapshot.trade_charts}
    recent: list[RecentTrade] = []
    charts: list[AnatomyChart] = []
    for t in trades[-RECENT:][::-1]:
        found = by_key.get((t.book_id, t.symbol, t.opened))
        chart = _anatomy_chart(found, t) if found else None
        if chart:
            charts.append(chart)
        recent.append(RecentTrade(key=_key(t.book_id, t.symbol, t.opened), symbol=t.symbol, money=book.money,
                                  opened=t.opened, closed=t.closed, return_pct=t.return_pct, r_multiple=t.r_multiple,
                                  exit_reason=t.exit_reason, sessions=_sessions_held(t.opened, t.closed),
                                  chart=chart is not None))
    return Anatomy(recent=recent, charts=charts, selected=charts[0].key if charts else None)


def _period(days: int) -> str:
    months = round(days / MONTH_DAYS)
    if months >= 24:
        return f"{round(days / 365.25)} years"
    return f"{months} month" if months == 1 else f"{months} months"


def yearly(points: list[ValuePoint]) -> tuple[float, float, int] | None:
    """(yearly return %, worst drop % as a positive magnitude, days spanned), or None under 90 days of history."""
    if len(points) < 2:
        return None
    days = (points[-1].date - points[0].date).days
    index = growth_index(points)
    if days < EARLY_DAYS or index[-1] <= 0:
        return None
    return (index[-1] ** (365 / days) - 1) * 100, -max_drawdown_pct(index), days


def _long_term(snapshot: Snapshot) -> list[ValuePoint]:
    history = {s.id: s.points for s in snapshot.account_history}
    return sum_series([history[a.id] for a in snapshot.accounts if a.category == "long_term" and a.id in history])


def _worth(snapshot: Snapshot, profile: Profile, book: Book | None, expected: Expected | None) -> Worth:
    points: list[WorthPoint] = []
    if expected is not None and expected.cagr_pct is not None and expected.max_drawdown_pct is not None:
        points.append(WorthPoint(key="backtest", label="Backtest", period=expected.window, early=False,
                                 return_pct=expected.cagr_pct, drop_pct=abs(expected.max_drawdown_pct)))
    bench = snapshot.benchmark
    lines = [
        ("book", f"{book.money.capitalize()} book" if book else "", _history(snapshot, book.id) if book else []),
        ("long_term", "Long-term accounts", _long_term(snapshot)),
        ("benchmark", bench.label if bench else profile.benchmark.label, list(bench.points) if bench else []),
    ]
    for key, label, history in lines:
        figure = yearly(history)
        if figure is not None:
            ret, drop, days = figure
            points.append(WorthPoint(key=key, label=label, period=_period(days), early=days < YEAR_DAYS,
                                     return_pct=round(ret, 2), drop_pct=round(drop, 2)))
    return Worth(points=points)


def monthly_returns(points: list[ValuePoint]) -> dict[str, float]:
    """Each month's return in percent: its last growth-index value over the month before's (the first month runs
    from the first point)."""
    ends: dict[str, float] = {}
    for p, value in zip(points, growth_index(points)):
        ends[p.date.strftime("%Y-%m")] = value
    out: dict[str, float] = {}
    base = 1.0
    for month in sorted(ends):
        out[month] = round((ends[month] / base - 1) * 100, 2) if base > 0 else 0.0
        base = ends[month]
    return out


def _last_months(today: dt.date) -> list[str]:
    year, month = today.year, today.month
    out = []
    for _ in range(MONTHS):
        out.append(f"{year:04d}-{month:02d}")
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return out[::-1]


def _monthly(snapshot: Snapshot, book: Book | None, today: dt.date) -> Monthly:
    mine = monthly_returns(_history(snapshot, book.id)) if book else {}
    theirs = monthly_returns(_long_term(snapshot))
    months = []
    for m in _last_months(today):
        a, b = mine.get(m), theirs.get(m)
        months.append(Month(month=m, book=a, long_term=b, ahead=a > b if a is not None and b is not None else None))
    shown = [MonthFigure(month=m.month, value=m.book) for m in months if m.book is not None]
    return Monthly(months=months, ahead=sum(1 for m in months if m.ahead),
                   compared=sum(1 for m in months if m.ahead is not None),
                   best=max(shown, key=lambda f: f.value, default=None),
                   worst=min(shown, key=lambda f: f.value, default=None))


def strategies_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> StrategiesView:
    rows = {r.id: r for r in _book_rows(snapshot)}
    counts = {b.id: rows[b.id].trades for b in snapshot.books}
    cards = []
    for s in snapshot.strategies:
        books = [b for b in snapshot.books if b.strategy_id == s.id]
        primary, _ = _primary(books, "real", counts)
        row = rows[primary.id] if primary else None
        cards.append(StrategyCard(
            id=s.id, name=s.name, summary=s.summary, books=_chips(snapshot, books, counts),
            book=primary.money if primary else None, trades=row.trades if row else 0,
            per_trade_pct=row.per_trade_pct if row else None, band_lo=row.band_lo if row else None,
            band_hi=row.band_hi if row else None, verdict=row.verdict if row else "none",
        ))
    return StrategiesView(strategies=cards)


def strategy_view(snapshot: Snapshot, profile: Profile, now: dt.datetime, strategy_id: str,
                  book: Money = "real") -> StrategyView | None:
    """One strategy, focused on its `book` money (the other money's book when it has none). None when unknown."""
    strategy = next((s for s in snapshot.strategies if s.id == strategy_id), None)
    if strategy is None:
        return None
    today = now.astimezone(profile.tz).date()
    books = [b for b in snapshot.books if b.strategy_id == strategy.id]
    closed = {b.id: closed_trades(snapshot, b.id) for b in books}
    counts = {b_id: len(trades) for b_id, trades in closed.items()}
    primary, other = _primary(books, book, counts)
    mine = closed[primary.id] if primary else []
    expected = strategy.expected
    lines = [FunnelLine(book_id=b.id, money=b.money, values=running_mean(closed[b.id]))
             for b in (primary, other) if b is not None and closed[b.id]]
    return StrategyView(
        id=strategy.id, name=strategy.name, summary=strategy.summary, books=_chips(snapshot, books, counts),
        book=primary.money if primary else None, primary=primary.id if primary else None,
        toggle={b.money for b in books} == {"real", "paper"}, expected=expected, steps=list(strategy.steps),
        sizing=strategy.sizing,
        behaving=Behaving(
            trades=len(mine), buckets=buckets([t.return_pct for t in mine], expected.distribution if expected else []),
            scorecard=_scorecard(mine, expected, primary, today), review_at=strategy.review_at_trades,
            other=_other_book(other, closed[other.id] if other else []),
        ),
        funnel=_funnel(lines, expected),
        slots=_slots(snapshot, primary, mine, list(strategy.watch), today),
        anatomy=_anatomy(snapshot, primary, mine),
        worth=_worth(snapshot, profile, primary, expected),
        monthly=_monthly(snapshot, primary, today),
        trades=[TradeRow(symbol=t.symbol, money=primary.money, opened=t.opened, closed=t.closed,
                         days_held=(t.closed - t.opened).days, return_pct=t.return_pct, r_multiple=t.r_multiple,
                         pnl=t.pnl, exit_reason=t.exit_reason) for t in mine[::-1]] if primary else [],
    )
