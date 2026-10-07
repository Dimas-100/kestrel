"""The Strategy pages, computed from one Snapshot: what is running, how it is doing, what needs you, what the next
review needs — and, as before, how it trades and whether it is behaving the way its backtest said it would.

Spec: docs/specs/2026-10-07-strategies-attention-design.md (over 2026-09-26 phase 3a)."""

from __future__ import annotations

import datetime as dt
import math
from statistics import fmean
from typing import Literal
from urllib.parse import quote

from ..contract import (
    Backtest,
    Bar,
    Book,
    Criterion,
    Decision,
    Expected,
    Indicator,
    Money,
    Position,
    RuleVersion,
    Run,
    Snapshot,
    Step,
    Trade,
    TradeChart,
    ValuePoint,
    WatchItem,
)
from ..metrics import expected_band, growth_index, max_drawdown_pct, opening_on, sum_series
from ..profile import Profile
from ._base import View
from .books import Protection, protection_of, stop_attention, stop_flag
from .home import MIN_TRADES_FOR_VERDICT, Attention, _book_rows

BUCKET_LOW, BUCKETS = -10, 20  # 1-point buckets from -10% to +10%; returns beyond fold into the end buckets
FUNNEL_FROM = 3  # the expected band starts at the third trade
MONTH_DAYS = 365.25 / 12
SESSIONS = 40  # "Where the money works" looks at the last 40 sessions
RECENT = 8  # trades listed beside the anatomy chart
MONTHS = 12
YEAR_DAYS, EARLY_DAYS = 365, 90  # a yearly figure needs 90 days of history; under a year it is "early"
LIMITED_UNTIL = 30  # under this many closed trades a verdict is "limited evidence" (the plan judges over 30–50)
STALE_SESSIONS = 3  # marks older than this many sessions are called out
REVIEW_SOON_DAYS = 7  # a dated review within this many days is an attention item
CYCLE_SPAN_DAYS = 4  # a cycle's evening queue and morning placement sit at most this far apart (a long weekend)
CYCLE_ROWS = 60  # the most rows the page lists for one cycle
KINDS = ("signal", "queued", "blocked", "placed", "filled", "expired", "cancelled", "skipped", "error")

Verdict = Literal["in_band", "below", "above", "early", "none"]
Status = Literal["ok", "above", "below", "early", "none"]
Evidence = Literal["none", "early", "limited", "adequate"]
EVIDENCE_WORDS = {
    "none": "no closed trades yet",
    "early": "too early to judge",
    "limited": f"limited evidence; the plan judges the system over {LIMITED_UNTIL}–50",
    "adequate": "enough to read a pattern",
}


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
    evidence: Evidence  # how much the verdict rests on: the card words it with the sample
    # the primary book's closed trades at a glance, so a card that is too early to judge still says something
    win_rate: float | None  # percent of closed trades with a positive P&L
    avg_return_pct: float | None
    pnl: float  # realized, closed trades
    unrealized_pnl: float  # open positions at their last price
    last_closed: dt.date | None
    attention: int  # serious and warning items on this strategy's page
    review_text: str  # "12 of 20 trades · by 2 Nov" / "Decision review 30 Oct"


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
    n: int  # the closed trades the actual rests on (the wins alone for the average win, the losses for the loss)
    band_lo: float | None  # the band the status was judged against, in the row's own unit
    band_hi: float | None


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
    evidence: Evidence
    evidence_text: str  # "16 real trades so far — limited evidence; the plan judges the system over 30–50"


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
    # slots are not dollars: five small lots can fill every slot and a fraction of the money
    deployed: float | None  # open positions at their last price
    capital: float | None
    deployed_pct: float | None  # deployed as a share of capital
    note: str


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
    window: str  # the dates every live point is measured over ("13 Aug to 6 Oct"), or ""
    note: str  # why live points are missing, or ""


class Month(View):
    month: str  # "2026-09"
    book: float | None  # the primary book's return that month, in percent
    long_term: float | None  # the long-term accounts over the same dates as the book, when the book has any
    ahead: bool | None  # the book did better than the long-term accounts
    partial: bool  # the book covered only part of the month (it started inside it, or the month is still running)
    from_date: dt.date | None  # the dates the row measures: from the close before the first point to the last
    to_date: dt.date | None


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
    entry_by: Literal["system", "hand"] | None
    exit_by: Literal["system", "hand"] | None
    rules_version: str
    plan_followed: bool | None
    note: str


class ReviewProgress(View):
    label: str
    trades: int  # closed trades counted toward it (since `counted_since`)
    at_trades: int | None
    counted_since: dt.date | None
    by: dt.date | None
    days_left: int | None
    due: bool
    last_at: dt.date | None
    last_note: str
    criteria: list[Criterion]
    doc: str
    text: str  # one line: "12 of 20 trades · by 2 Nov"


class Rules(View):
    version: str
    effective: dt.date | None
    history: list[RuleVersion]  # oldest first
    steps: list[Step]  # the flow
    gates: list[Step]  # limits and circuit breakers
    sizing: str


class Performance(View):
    book_id: str | None
    money: Money | None
    realized_pnl: float  # closed trades
    unrealized_pnl: float  # open positions at their last price
    total_pnl: float
    capital: float | None  # what the figures are measured against
    capital_basis: str  # what that is, in words
    deployed: float  # open positions at their last price
    deployed_pct: float | None
    positions: int
    stops_covered: int | None  # real books: positions with a stop on record; None for paper
    stops_total: int | None
    protection: Protection  # "stop": a resting stop is expected on every lot; "signal": exits on a signal; "": not said
    return_pct: float | None  # deposit-adjusted, since the history starts
    drawdown_now_pct: float | None  # below the running peak now (<= 0)
    drawdown_worst_pct: float | None  # the worst fall from a peak (<= 0)
    since: dt.date | None
    days: int | None
    unavailable: list[str]  # a sentence per figure that can't be shown, and why


class CycleRun(View):
    label: str
    status: str
    time: dt.datetime
    detail: str


class CycleCount(View):
    kind: str
    count: int


class Cycle(View):
    book_id: str | None
    session: dt.date | None  # the day the cycle ended on
    rows: list[Decision]  # in time order
    counts: list[CycleCount]  # per kind, in the cycle's order, only kinds present
    runs: list[CycleRun]  # the book's latest run per label, then the next due
    prices_as_of: dt.date | None
    freshness: str  # "fresh", "2 sessions old", "not reported"
    reported: bool  # the source sends this book's decisions


class AdherenceRow(View):
    version: str
    effective: dt.date | None
    summary: str
    trades: int
    system_entries: int
    hand_entries: int
    system_exits: int
    hand_exits: int
    followed: int
    broken: int
    unscored: int
    system_run: bool  # under this version a hand entry or exit is a deviation


class Deviation(View):
    symbol: str
    opened: dt.date
    closed: dt.date
    rules_version: str
    what: str  # "Hand exit", "Scored off-plan: sold ahead of a print"


class Adherence(View):
    rows: list[AdherenceRow]  # oldest version first
    deviations: list[Deviation]  # newest first
    note: str
    reported: bool  # the source says who placed its trades


class Research(View):
    expected: Expected | None
    backtests: list[Backtest]  # this strategy's, newest first


class StrategyView(View):
    id: str
    name: str
    summary: str
    books: list[BookChip]
    book: Money | None  # the primary book's money
    primary: str | None  # the primary book's id
    toggle: bool  # a real and a paper book: the page offers Real | Paper
    expected: Expected | None
    steps: list[Step]  # the flow steps, as before (gates are in `rules`)
    sizing: str
    attention: list[Attention]
    review: ReviewProgress | None
    rules: Rules
    performance: Performance
    cycle: Cycle
    adherence: Adherence
    research: Research
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


def evidence(n: int) -> Evidence:
    if n == 0:
        return "none"
    if n < MIN_TRADES_FOR_VERDICT:
        return "early"
    return "limited" if n < LIMITED_UNTIL else "adequate"


def evidence_text(n: int, money: Money | None) -> str:
    word = EVIDENCE_WORDS[evidence(n)]
    if n == 0:
        return word[0].upper() + word[1:]
    return f"{n} {money or 'closed'} trade{'s' if n != 1 else ''} so far — {word}"


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
         n: int, compare: float | None = None, count: int | None = None) -> ScoreRow:
    """`compare` is the unrounded value to test against the band, when it differs from the rounded `actual` shown
    in the row — a value that rounds to the edge must not read as inside it (Home compares the same unrounded
    mean, so the two pages never disagree at the edge)."""
    value = actual if compare is None else compare
    if expected is None:
        status: Status = "none"
    elif n < MIN_TRADES_FOR_VERDICT:
        status = "early"
    elif value is None or band is None:
        status = "none"
    else:
        status = "below" if value < band[0] else "above" if value > band[1] else "ok"
    return ScoreRow(key=key, label=label, actual=actual, expected=expected, status=status,
                    n=n if count is None else count,
                    band_lo=round(band[0], 2) if band and expected is not None else None,
                    band_hi=round(band[1], 2) if band and expected is not None else None)


def _scorecard(trades: list[Trade], expected: Expected | None, book: Book | None, today: dt.date) -> list[ScoreRow]:
    returns = [t.return_pct for t in trades]
    n = len(returns)
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    months = max(1.0, (today - book.started).days / MONTH_DAYS) if book else 1.0
    win_rate = round(len(wins) / n * 100, 1) if n else None
    avg_trade_raw = fmean(returns) if n else None
    avg_trade = round(avg_trade_raw, 2) if avg_trade_raw is not None else None
    avg_win = round(fmean(wins), 2) if wins else None
    avg_loss = round(fmean(losses), 2) if losses else None
    per_month = round(n / months, 1) if n else None
    e = expected
    win_band = avg_band = None
    if e is not None and n:
        p = min(1.0, max(0.0, e.win_rate / 100))  # a backtest's win_rate can arrive outside 0..100
        half = 1.96 * math.sqrt(p * (1 - p) / n) * 100
        win_band = (e.win_rate - half, e.win_rate + half)
        avg_band = expected_band(e.avg_trade_pct, e.sd_trade_pct, n)
    return [
        _row("win_rate", "Win rate", win_rate, e.win_rate if e else None, win_band, n),
        _row("avg_trade", "Average per trade", avg_trade, e.avg_trade_pct if e else None, avg_band, n,
             compare=avg_trade_raw),
        _row("avg_win", "Average win", avg_win, e.avg_win_pct if e else None,
             _within_half(e.avg_win_pct) if e else None, n, count=len(wins)),
        _row("avg_loss", "Average loss", avg_loss, e.avg_loss_pct if e else None,
             _within_half(e.avg_loss_pct) if e else None, n, count=len(losses)),
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


def _deployed(positions: list[Position]) -> float:
    return round(sum(p.quantity * p.last_price for p in positions), 2)


def slots_used(trades: list[Trade], positions: list[Position], days: list[dt.date]) -> list[int]:
    """Slots in use on each day. A lot is one (symbol, opened) — several closed slices of one fill count once; it
    holds a slot from its open day up to, but not including, its close day (on the close day the slot is the
    next lot's), and on the close day itself only when it opened and closed that day; an open position holds one
    from its open day on."""
    lots: dict[tuple[str, dt.date], dt.date | None] = {}
    for t in trades:
        key = (t.symbol, t.opened)
        lots[key] = max(lots[key], t.closed) if lots.get(key) else t.closed
    for p in positions:
        lots[(p.symbol, p.opened)] = None  # still open: outlives any closed slice of the same lot
    used = []
    for d in days:
        n = 0
        for (_, opened), closed in lots.items():
            if closed is None:
                n += opened <= d
            else:
                n += opened <= d < closed or opened == closed == d
        used.append(n)
    return used


def _slots(snapshot: Snapshot, book: Book | None, trades: list[Trade], positions: list[Position],
           watch: list[WatchItem], today: dt.date) -> Slots:
    deployed = _deployed(positions) if book else None
    capital = book.capital if book else None
    deployed_pct = round(deployed / capital * 100, 1) if deployed is not None and capital else None
    note = ""
    if book is not None and book.slots_total:
        note = ("Slots are not dollars: a lot is sized by its own rule, so every slot can be in use with only part "
                "of the money at work.")
    if book is None or book.slots_total is None:
        return Slots(book_id=book.id if book else None, total=None, days=[], used=[], avg_used=None,
                     working_pct=None, idle=0, watch=watch, deployed=deployed, capital=capital,
                     deployed_pct=deployed_pct, note=note)
    days = sorted({p.date for p in _history(snapshot, book.id)})[-SESSIONS:] or _weekdays_ending(today, SESSIONS)
    used = slots_used(trades, positions, days)
    avg = fmean(used)
    return Slots(book_id=book.id, total=book.slots_total, days=days, used=used, avg_used=round(avg, 1),
                 working_pct=round(avg / book.slots_total * 100, 1) if book.slots_total else None,
                 idle=sum(1 for u in used if u == 0), watch=watch, deployed=deployed, capital=capital,
                 deployed_pct=deployed_pct, note=note)


def _key(book_id: str, symbol: str, opened: dt.date) -> str:
    return f"{book_id}|{symbol}|{opened.isoformat()}"


def _sessions_held(opened: dt.date, closed: dt.date) -> int:
    return sum(1 for i in range(1, (closed - opened).days + 1) if (opened + dt.timedelta(days=i)).weekday() < 5)


def _anatomy_chart(chart: TradeChart, trade: Trade) -> AnatomyChart | None:
    dates = [b.date for b in chart.bars]
    if trade.opened not in dates or trade.closed < trade.opened:
        return None  # a chart that doesn't show the entry, or a trade that closes before it opens, can't be drawn
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
    return (index[-1] ** (365 / days) - 1) * 100, abs(max_drawdown_pct(index)), days


def _long_term(snapshot: Snapshot) -> list[ValuePoint]:
    history = {s.id: s.points for s in snapshot.account_history}
    return sum_series([history[a.id] for a in snapshot.accounts if a.category == "long_term" and a.id in history])


def _day_label(day: dt.date) -> str:
    return f"{day.day} {day.strftime('%b')}"


def _worth(snapshot: Snapshot, profile: Profile, book: Book | None, expected: Expected | None) -> Worth:
    """The backtest's point, and — only over the primary book's own window, so the dates match — the book, the
    long-term accounts and the benchmark. Without 90 days of book history the live points are left out and the
    note says so."""
    points: list[WorthPoint] = []
    if expected is not None and expected.cagr_pct is not None and expected.max_drawdown_pct is not None:
        points.append(WorthPoint(key="backtest", label="Backtest", period=expected.window, early=False,
                                 return_pct=expected.cagr_pct, drop_pct=abs(expected.max_drawdown_pct)))
    history = _history(snapshot, book.id) if book else []
    figure = yearly(history)
    if book is None:
        return Worth(points=points, window="", note="No book trades this strategy yet.")
    if figure is None:
        days = (history[-1].date - history[0].date).days if len(history) > 1 else 0
        note = (f"The {book.money} book has {days} days of value history; a yearly figure needs {EARLY_DAYS}."
                if history else f"The {book.money} book sends no value history, so there is nothing to measure yet.")
        return Worth(points=points, window="", note=note)
    start, end = history[0].date, history[-1].date
    bench = snapshot.benchmark
    lines = [
        ("book", f"{book.money.capitalize()} book", history),
        ("long_term", "Long-term accounts", _clip(_long_term(snapshot), start, end)),
        ("benchmark", bench.label if bench else profile.benchmark.label,
         _clip(list(bench.points), start, end) if bench else []),
    ]
    for key, label, line in lines:
        measured = yearly(line)
        if measured is not None:
            ret, drop, days = measured
            points.append(WorthPoint(key=key, label=label, period=_period(days), early=days < YEAR_DAYS,
                                     return_pct=round(ret, 2), drop_pct=round(drop, 2)))
    return Worth(points=points, window=f"{_day_label(start)} to {_day_label(end)}", note="")


def _clip(points: list[ValuePoint], start: dt.date, end: dt.date) -> list[ValuePoint]:
    """A series over exactly [start, end]: opening on `start` with the value held then, ending at the last point on
    or before `end` -- so two series measured together share both endpoints."""
    return [p for p in opening_on(points, start) if p.date <= end]


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


def monthly_spans(points: list[ValuePoint]) -> dict[str, tuple[dt.date, dt.date, dt.date]]:
    """For each month a series covers: (the base date — the last point of the month before, or the first point —,
    the last point of the month, the first point of the month)."""
    out: dict[str, tuple[dt.date, dt.date, dt.date]] = {}
    last: dt.date | None = None
    for p in points:
        month = p.date.strftime("%Y-%m")
        if month not in out:
            out[month] = (last or p.date, p.date, p.date)
        else:
            base, _, first = out[month]
            out[month] = (base, p.date, first)
        last = p.date
    return out


def _index_at(points: list[ValuePoint], index: list[float], day: dt.date) -> float | None:
    """The growth index at the last point on or before `day`."""
    value = None
    for p, v in zip(points, index):
        if p.date > day:
            break
        value = v
    return value


def _last_months(today: dt.date) -> list[str]:
    year, month = today.year, today.month
    out = []
    for _ in range(MONTHS):
        out.append(f"{year:04d}-{month:02d}")
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return out[::-1]


def _first_weekday(month: str) -> dt.date:
    day = dt.date(int(month[:4]), int(month[5:]), 1)
    while day.weekday() >= 5:
        day += dt.timedelta(days=1)
    return day


def _monthly(snapshot: Snapshot, book: Book | None, today: dt.date) -> Monthly:
    """The book's months against the long-term accounts over the SAME dates: a book that started on the 14th is
    compared with the long-term accounts from the 14th, and the row says it is partial."""
    history = _history(snapshot, book.id) if book else []
    mine = monthly_returns(history)
    spans = monthly_spans(history)
    theirs_points = _long_term(snapshot)
    theirs_index = growth_index(theirs_points)
    theirs_full = monthly_returns(theirs_points)
    months = []
    for m in _last_months(today):
        a = mine.get(m)
        partial = m == today.strftime("%Y-%m")
        b = theirs_full.get(m)
        from_date = to_date = None
        if a is not None:
            base, end, first = spans[m]
            from_date, to_date = base, end
            partial = partial or (history[0].date >= first and first > _first_weekday(m))
            start_value, end_value = _index_at(theirs_points, theirs_index, base), _index_at(theirs_points,
                                                                                               theirs_index, end)
            b = round((end_value / start_value - 1) * 100, 2) if start_value and end_value is not None else None
        months.append(Month(month=m, book=a, long_term=b, ahead=a > b if a is not None and b is not None else None,
                            partial=partial, from_date=from_date, to_date=to_date))
    shown = [MonthFigure(month=m.month, value=m.book) for m in months if m.book is not None]
    return Monthly(months=months, ahead=sum(1 for m in months if m.ahead),
                   compared=sum(1 for m in months if m.ahead is not None),
                   best=max(shown, key=lambda f: f.value, default=None),
                   worst=min(shown, key=lambda f: f.value, default=None))


# ---------------------------------------------------------------- the new sections (2026-10-07)

def _review(strategy, trades: list[Trade], today: dt.date) -> ReviewProgress | None:
    r = strategy.review
    if r is None:
        if strategy.review_at_trades is None:
            return None
        r_label, at, since, by, last_at, last_note, criteria, doc = (
            "Strategy review", strategy.review_at_trades, None, None, None, "", [], "")
    else:
        r_label, at, since, by, last_at, last_note, criteria, doc = (
            r.label or "Review", r.at_trades, r.counted_since, r.by, r.last_at, r.last_note, list(r.criteria), r.doc)
    n = sum(1 for t in trades if since is None or t.closed >= since)
    days_left = (by - today).days if by else None
    due = (at is not None and n >= at) or (days_left is not None and days_left <= 0)
    parts = []
    if at is not None:
        parts.append(f"{n} of {at} trades")
    if by is not None:
        parts.append(f"by {_day_label(by)}")
    text = " · ".join(parts) if parts else r_label
    if due:
        text += " · due"
    return ReviewProgress(label=r_label, trades=n, at_trades=at, counted_since=since, by=by, days_left=days_left,
                          due=due, last_at=last_at, last_note=last_note, criteria=criteria, doc=doc, text=text)


def _rules(strategy) -> Rules:
    history = sorted(strategy.rules_history, key=lambda r: r.effective)
    return Rules(version=strategy.rules_version, effective=strategy.rules_effective, history=history,
                 steps=[s for s in strategy.steps if s.kind == "step"],
                 gates=[s for s in strategy.steps if s.kind == "gate"], sizing=strategy.sizing)


def _performance(snapshot: Snapshot, book: Book | None, trades: list[Trade], positions: list[Position],
                 protection: Protection = "") -> Performance:
    if book is None:
        return Performance(book_id=None, money=None, realized_pnl=0.0, unrealized_pnl=0.0, total_pnl=0.0,
                           capital=None, capital_basis="", deployed=0.0, deployed_pct=None, positions=0,
                           stops_covered=None, stops_total=None, protection="", return_pct=None, drawdown_now_pct=None,
                           drawdown_worst_pct=None, since=None, days=None,
                           unavailable=["No book trades this strategy yet."])
    realized = round(sum(t.pnl for t in trades), 2)
    unrealized = round(sum((p.last_price - p.entry_price) * p.quantity for p in positions), 2)
    deployed = _deployed(positions)
    unavailable: list[str] = []
    capital, basis = book.capital, book.capital_basis
    if capital is None:
        cost = round(sum(p.entry_price * p.quantity for p in positions), 2)
        if cost > 0:
            capital, basis = cost, "The cost of its open positions: the book sends no capital figure"
        else:
            unavailable.append("The book sends no capital figure, so deployed money has nothing to be measured "
                               "against.")
    history = _history(snapshot, book.id)
    return_pct = now_dd = worst_dd = None
    since = days = None
    if len(history) >= 2:
        idx = growth_index(history)
        peak = max(idx)
        return_pct = round((idx[-1] - 1) * 100, 2)
        now_dd = round((idx[-1] / peak - 1) * 100, 2) if peak > 0 else None
        worst_dd = round(max_drawdown_pct(idx), 2)
        since, days = history[0].date, (history[-1].date - history[0].date).days
    else:
        unavailable.append(f"The {book.money} book sends no value history, so its drawdown and its return since "
                           "the start can't be measured; the P&L above is what the trades and positions add up to.")
    stops_covered = stops_total = None
    if book.money == "real":
        stops_total = len(positions)
        stops_covered = sum(1 for p in positions if p.stop_price is not None or p.stop_resting is True)
    return Performance(book_id=book.id, money=book.money, realized_pnl=realized, unrealized_pnl=unrealized,
                       total_pnl=round(realized + unrealized, 2), capital=capital, capital_basis=basis,
                       deployed=deployed, deployed_pct=round(deployed / capital * 100, 1) if capital else None,
                       positions=len(positions), stops_covered=stops_covered, stops_total=stops_total,
                       protection=protection,
                       return_pct=return_pct, drawdown_now_pct=now_dd, drawdown_worst_pct=worst_dd, since=since,
                       days=days, unavailable=unavailable)


def _last_session(now: dt.datetime, tz: dt.tzinfo) -> dt.date:
    """The last weekday whose close has passed (16:00 local), as a stand-in for the last trading session."""
    local = now.astimezone(tz)
    day = local.date()
    if day.weekday() >= 5 or local.time() < dt.time(16, 0):
        day -= dt.timedelta(days=1)
    while day.weekday() >= 5:
        day -= dt.timedelta(days=1)
    return day


def sessions_old(prices_as_of: dt.date, last_session: dt.date) -> int:
    """Weekdays after `prices_as_of` up to and including `last_session` (0 when the marks are from it)."""
    n, day = 0, prices_as_of
    while day < last_session:
        day += dt.timedelta(days=1)
        n += day.weekday() < 5
    return n


def _freshness(book: Book | None, last_session: dt.date) -> str:
    """How old the book's marks are, judged by its OLDEST position mark (`prices_as_of` is the date every position
    can be trusted to; a stale one names its own date in its note)."""
    if book is None or book.prices_as_of is None:
        return "not reported"
    old = sessions_old(book.prices_as_of, last_session)
    return "fresh" if old == 0 else f"oldest mark {old} session{'s' if old != 1 else ''} old"


def _cycle(snapshot: Snapshot, book: Book | None, now: dt.datetime, tz: dt.tzinfo) -> Cycle:
    last_session = _last_session(now, tz)
    if book is None:
        return Cycle(book_id=None, session=None, rows=[], counts=[], runs=[], prices_as_of=None,
                     freshness="not reported", reported=False)
    mine = sorted((d for d in snapshot.decisions if d.book_id == book.id), key=lambda d: d.time)
    rows: list[Decision] = []
    session = None
    if mine:
        day = lambda d: d.time.astimezone(tz).date()  # noqa: E731
        session = day(mine[-1])
        earlier = [day(d) for d in mine if d.kind in ("signal", "queued") and day(d) < session]
        start = session
        if earlier and (session - earlier[-1]).days <= CYCLE_SPAN_DAYS:
            start = earlier[-1]
        rows = [d for d in mine if start <= day(d) <= session][-CYCLE_ROWS:]
    counts = [CycleCount(kind=k, count=sum(1 for d in rows if d.kind == k)) for k in KINDS
              if any(d.kind == k for d in rows)]
    runs: list[CycleRun] = []
    own = [r for r in snapshot.runs if r.book_id == book.id]
    latest: dict[str, Run] = {}
    for r in sorted((r for r in own if r.status in ("done", "failed", "late", "paused")), key=lambda r: r.time):
        latest[r.label] = r
    runs = [CycleRun(label=r.label, status=r.status, time=r.time, detail=r.detail)
            for r in sorted(latest.values(), key=lambda r: r.time, reverse=True)]
    due = sorted((r for r in own if r.status == "due"), key=lambda r: r.time)
    if due:
        runs.append(CycleRun(label=due[0].label, status="due", time=due[0].time, detail=due[0].detail))
    return Cycle(book_id=book.id, session=session, rows=rows, counts=counts, runs=runs,
                 prices_as_of=book.prices_as_of, freshness=_freshness(book, last_session), reported=bool(mine))


def version_for(history: list[RuleVersion], opened: dt.date) -> RuleVersion | None:
    """The rules in force on a day: the latest version effective on or before it."""
    return next((r for r in sorted(history, key=lambda r: r.effective, reverse=True) if r.effective <= opened), None)


BEFORE_RULES = "before written rules"


def _adherence(strategy, trades: list[Trade]) -> Adherence:
    history = sorted(strategy.rules_history, key=lambda r: r.effective)
    reported = any(t.entry_by is not None for t in trades)
    any_system = any(t.entry_by == "system" for t in trades)
    groups: dict[str, list[Trade]] = {}
    for t in trades:
        v = version_for(history, t.opened)
        groups.setdefault(v.version if v else BEFORE_RULES, []).append(t)
    rows: list[AdherenceRow] = []
    deviations: list[Deviation] = []
    versions = [(BEFORE_RULES, None, "")] if BEFORE_RULES in groups else []
    versions += [(r.version, r.effective, r.summary) for r in history]
    for i, (version, effective, summary) in enumerate(versions):
        mine = groups.get(version, [])
        if not mine and effective is None:
            continue
        known = next((r.placed_by for r in history if r.version == version), "")
        if known:
            system_run = known == "system"
        else:   # the source doesn't say: every written version after the first is system-run, when the book has
            # system entries at all
            system_run = any_system and effective is not None and version != history[0].version
        rows.append(AdherenceRow(
            version=version, effective=effective, summary=summary, trades=len(mine),
            system_entries=sum(t.entry_by == "system" for t in mine),
            hand_entries=sum(t.entry_by == "hand" for t in mine),
            system_exits=sum(t.exit_by == "system" for t in mine), hand_exits=sum(t.exit_by == "hand" for t in mine),
            followed=sum(t.plan_followed is True for t in mine), broken=sum(t.plan_followed is False for t in mine),
            unscored=sum(t.plan_followed is None for t in mine), system_run=system_run))
        for t in mine:
            what = []
            if system_run and t.entry_by == "hand":
                what.append("Hand entry")
            if system_run and t.exit_by == "hand":
                what.append("Hand exit")
            if t.plan_followed is False:
                what.append(f"Scored off-plan: {t.note}" if t.note else "Scored off-plan")
            if what:
                deviations.append(Deviation(symbol=t.symbol, opened=t.opened, closed=t.closed, rules_version=version,
                                            what=" · ".join(what)))
    deviations.sort(key=lambda d: (d.closed, d.opened, d.symbol), reverse=True)
    note = ("Each trade is judged against the rules in force when it was entered. Before the system placed the "
            "entries, a hand entry was how the rules were run; after that, a hand entry or exit is a deviation. "
            "A scored verdict is the desk's own, never recomputed here.") if reported else \
        "This source doesn't say who placed its trades, so adherence can't be judged."
    return Adherence(rows=rows, deviations=deviations, note=note, reported=reported)


def _research(snapshot: Snapshot, strategy) -> Research:
    mine = sorted((b for b in snapshot.backtests if b.strategy_id == strategy.id), key=lambda b: b.at, reverse=True)
    return Research(expected=strategy.expected, backtests=mine)


def _attention(snapshot: Snapshot, strategy, books: list[Book], primary: Book | None, trades: list[Trade],
               review: ReviewProgress | None, now: dt.datetime, tz: dt.tzinfo) -> list[Attention]:
    page = f"/strategies/{quote(strategy.id, safe='')}"
    ids = {b.id for b in books}
    items: list[Attention] = []
    protection = protection_of(strategy)
    for b in books:
        for p in snapshot.positions:
            if p.book_id == b.id:
                item = stop_attention(b, p, stop_flag(p, protection))
                if item:
                    items.append(item)
    for a in snapshot.alerts:
        if a.link == page or any(a.link == f"/books/{quote(b_id, safe='')}" for b_id in ids):
            items.append(Attention(level=a.level, title=a.title, detail=a.detail, link=a.link))
    for r in snapshot.runs:
        if r.book_id in ids and r.status in ("late", "failed"):
            when = r.time.astimezone(tz).strftime("%a %H:%M")
            items.append(Attention(level="warning", title=f"{r.label} {r.status} {when}", detail=r.detail,
                                   link="/activity"))
    last_session = _last_session(now, tz)
    for b in books:
        has_positions = any(p.book_id == b.id for p in snapshot.positions)
        if b.prices_as_of is not None and has_positions and sessions_old(b.prices_as_of, last_session) > STALE_SESSIONS:
            items.append(Attention(level="warning", title=f"{b.name}'s marks are from {_day_label(b.prices_as_of)}",
                                   detail=f"{sessions_old(b.prices_as_of, last_session)} sessions old · "
                                   "the P&L and stops below rest on them", link=page))
    if review is not None:
        if review.due:
            items.append(Attention(level="note", title=f"{review.label} is due", detail=review.text, link=page))
        elif review.days_left is not None and review.days_left <= REVIEW_SOON_DAYS:
            items.append(Attention(level="note", title=f"{review.label} in {review.days_left} days",
                                   detail=review.text, link=page))
    for b in books:
        if b.status != "running":
            items.append(Attention(level="note", title=f"{b.name} ({b.money}) is {b.status}", detail="", link=page))
    if primary is not None and len(trades) < LIMITED_UNTIL:
        items.append(Attention(level="note", title=evidence_text(len(trades), primary.money),
                               detail="Verdicts on this page rest on a small sample", link=page))
    order = {"serious": 0, "warning": 1, "note": 2}
    return sorted(items, key=lambda a: order[a.level])


def strategies_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> StrategiesView:
    rows = {r.id: r for r in _book_rows(snapshot)}
    counts = {b.id: rows[b.id].trades for b in snapshot.books}
    today = now.astimezone(profile.tz).date()
    cards = []
    for s in snapshot.strategies:
        books = [b for b in snapshot.books if b.strategy_id == s.id]
        primary, _ = _primary(books, "real", counts)
        row = rows[primary.id] if primary else None
        mine = closed_trades(snapshot, primary.id) if primary else []
        positions = [p for p in snapshot.positions if primary and p.book_id == primary.id]
        review = _review(s, mine, today)
        attention = _attention(snapshot, s, books, primary, mine, review, now, profile.tz)
        cards.append(StrategyCard(
            id=s.id, name=s.name, summary=s.summary, books=_chips(snapshot, books, counts),
            book=primary.money if primary else None, trades=row.trades if row else 0,
            per_trade_pct=row.per_trade_pct if row else None, band_lo=row.band_lo if row else None,
            band_hi=row.band_hi if row else None, verdict=row.verdict if row else "none",
            evidence=evidence(len(mine)),
            win_rate=round(100 * sum(t.pnl > 0 for t in mine) / len(mine), 1) if mine else None,
            avg_return_pct=round(sum(t.return_pct for t in mine) / len(mine), 3) if mine else None,
            pnl=round(sum(t.pnl for t in mine), 2),
            unrealized_pnl=round(sum((p.last_price - p.entry_price) * p.quantity for p in positions), 2),
            last_closed=mine[-1].closed if mine else None,
            attention=sum(1 for a in attention if a.level != "note"),
            review_text=review.text if review else "",
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
    positions = [p for p in snapshot.positions if primary and p.book_id == primary.id]
    expected = strategy.expected
    lines = [FunnelLine(book_id=b.id, money=b.money, values=running_mean(closed[b.id]))
             for b in (primary, other) if b is not None and closed[b.id]]
    review = _review(strategy, mine, today)
    return StrategyView(
        id=strategy.id, name=strategy.name, summary=strategy.summary, books=_chips(snapshot, books, counts),
        book=primary.money if primary else None, primary=primary.id if primary else None,
        toggle={b.money for b in books} == {"real", "paper"}, expected=expected,
        steps=[s for s in strategy.steps if s.kind == "step"], sizing=strategy.sizing,
        attention=_attention(snapshot, strategy, books, primary, mine, review, now, profile.tz),
        review=review, rules=_rules(strategy),
        performance=_performance(snapshot, primary, mine, positions, protection_of(strategy)),
        cycle=_cycle(snapshot, primary, now, profile.tz),
        adherence=_adherence(strategy, mine),
        research=_research(snapshot, strategy),
        behaving=Behaving(
            trades=len(mine), buckets=buckets([t.return_pct for t in mine], expected.distribution if expected else []),
            scorecard=_scorecard(mine, expected, primary, today),
            review_at=review.at_trades if review else None,
            other=_other_book(other, closed[other.id] if other else []),
            evidence=evidence(len(mine)), evidence_text=evidence_text(len(mine), primary.money if primary else None),
        ),
        funnel=_funnel(lines, expected),
        slots=_slots(snapshot, primary, mine, positions, list(strategy.watch), today),
        anatomy=_anatomy(snapshot, primary, mine),
        worth=_worth(snapshot, profile, primary, expected),
        monthly=_monthly(snapshot, primary, today),
        trades=[TradeRow(symbol=t.symbol, money=primary.money, opened=t.opened, closed=t.closed,
                         days_held=(t.closed - t.opened).days, return_pct=t.return_pct, r_multiple=t.r_multiple,
                         pnl=t.pnl, exit_reason=t.exit_reason, entry_by=t.entry_by, exit_by=t.exit_by,
                         rules_version=t.rules_version, plan_followed=t.plan_followed, note=t.note)
                for t in mine[::-1]] if primary else [],
    )
