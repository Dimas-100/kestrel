"""The Strategy pages, computed from one Snapshot: how does a strategy trade, and is it behaving the way its
backtest said it would?"""

from __future__ import annotations

import datetime as dt
import math
from statistics import fmean
from typing import Literal

from ..contract import Book, Expected, Money, Snapshot, Step, Trade
from ..metrics import expected_band
from ..profile import Profile
from .home import MIN_TRADES_FOR_VERDICT, View, _book_rows

BUCKET_LOW, BUCKETS = -10, 20  # 1-point buckets from -10% to +10%; returns beyond fold into the end buckets
FUNNEL_FROM = 3  # the expected band starts at the third trade
MONTH_DAYS = 365.25 / 12

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
    )
