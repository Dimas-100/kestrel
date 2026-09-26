"""The Home page, computed from one Snapshot: how is all my money doing, and does anything need me?"""

from __future__ import annotations

import datetime as dt
from statistics import fmean
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel

from ..contract import Book, Snapshot, Source, ValuePoint
from ..metrics import expected_band, growth_index, largest_remainder, max_drawdown_pct, sum_series
from ..profile import Profile

CATEGORY_LABELS = {"long_term": "Long-term", "trading": "Trading", "cash": "Cash", "other": "Other"}
MIN_TRADES_FOR_VERDICT = 10  # fewer closed trades than this is "too early" to judge a book
MIN_YTD_POINTS = 5  # early January falls back to the past twelve months


class View(BaseModel):
    pass


class Delta(View):
    amount: float
    pct: float | None


class NetWorth(View):
    total: float
    today: Delta
    month: Delta
    year: Delta
    year_flows: float
    points: list[ValuePoint]  # the client draws the "starting value + deposits" line from net_flow


class Slice(View):
    category: str
    label: str
    value: float
    share: float
    cells: int  # of 100, for the waffle


class AccountRow(View):
    id: str
    name: str
    category: str
    value: float
    day_pct: float | None


class Line(View):
    key: Literal["trading", "long_term", "benchmark"]
    label: str
    return_pct: float
    max_drop_pct: float
    values: list[float | None]  # percent change since the window start, aligned with Comparison.dates


class Comparison(View):
    window: Literal["ytd", "12m"]
    start: dt.date  # the shared first day: later than the window's start when a line's history begins later
    dates: list[dt.date]
    lines: list[Line]
    gap_pts: float | None  # trading minus long-term, in percentage points
    shallower: bool | None  # trading's worst drop was smaller than long-term's
    real_trades: int
    review_at: int | None


class Attention(View):
    level: Literal["serious", "warning", "note"]
    title: str
    detail: str
    link: str


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


class TodayRun(View):
    time: dt.datetime
    label: str
    status: str
    detail: str


class PositionRow(View):
    book_id: str
    book: str
    symbol: str
    money: Literal["real", "paper"]
    quantity: float
    entry_price: float
    last_price: float
    stop_price: float | None
    room_pct: float | None  # distance from the last price down to the stop
    pnl: float
    note: str


class Summary(View):
    day_change: float
    gap_pts: float | None
    needs_you: int  # serious + warning items


class HomeView(View):
    as_of: dt.datetime
    summary: Summary
    net_worth: NetWorth
    allocation: list[Slice]
    accounts: list[AccountRow]
    comparison: Comparison
    attention: list[Attention]
    books: list[BookRow]
    today: list[TodayRun]
    positions: list[PositionRow]


def _delta(points: list[ValuePoint], since: dt.date) -> Delta:
    """Money change from the last point before `since` to the latest point (deposits included)."""
    if not points:
        return Delta(amount=0.0, pct=None)
    base = next((p.value for p in reversed(points) if p.date < since), points[0].value)
    amount = points[-1].value - base
    return Delta(amount=round(amount, 2), pct=round(amount / base * 100, 2) if base else None)


def _day_pct(points: list[ValuePoint]) -> float | None:
    if len(points) < 2 or points[-2].value <= 0:
        return None
    return round(((points[-1].value - points[-1].net_flow) / points[-2].value - 1) * 100, 2)


def age_text(delta: dt.timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{hours // 24} days"


def _window(points: list[ValuePoint], start: dt.date) -> list[ValuePoint]:
    return [p for p in points if p.date >= start]


def _from(points: list[ValuePoint], start: dt.date) -> list[ValuePoint]:
    """The points after `start`, opening on `start` with the value held then (the last point on or before it)."""
    before = [p for p in points if p.date <= start]
    after = [p for p in points if p.date > start]
    return [ValuePoint(date=start, value=before[-1].value), *after] if before else after


def _line(key, label, points: list[ValuePoint], dates: list[dt.date]) -> Line | None:
    if len(points) < 2:
        return None
    index = growth_index(points)
    by_date = {p.date: i for p, i in zip(points, index)}
    values: list[float | None] = []
    last: float | None = None
    for day in dates:
        last = by_date.get(day, last)
        values.append(None if last is None else round((last - 1) * 100, 3))
    return Line(key=key, label=label, return_pct=round((index[-1] - 1) * 100, 2),
                max_drop_pct=round(max_drawdown_pct(index), 2), values=values)


def _comparison(snapshot: Snapshot, profile: Profile, today: dt.date, real_books: list[Book]) -> Comparison:
    history = {s.id: s.points for s in snapshot.account_history}
    book_history = {s.id: s.points for s in snapshot.book_history}
    trading = sum_series([book_history[b.id] for b in real_books if b.id in book_history])
    long_term = sum_series([history[a.id] for a in snapshot.accounts if a.category == "long_term" and a.id in history])
    bench = list(snapshot.benchmark.points) if snapshot.benchmark else []
    start, window = dt.date(today.year, 1, 1), "ytd"
    # a series needs two points to be a line: a real book on its first day must not move the window or the start
    drawable = lambda points: len(points) >= 2  # noqa: E731
    if len(_window(trading if drawable(trading) else long_term, start)) < MIN_YTD_POINTS:
        start, window = today - dt.timedelta(days=365), "12m"
    trading, long_term, bench = _window(trading, start), _window(long_term, start), _window(bench, start)
    firsts = [s[0].date for s in (trading, long_term, bench) if drawable(s)]
    if firsts:
        # every line is measured from the same day: the latest first date, so a book opened in July is not
        # set against an index fund's whole year
        start = max(firsts)
        trading, long_term, bench = _from(trading, start), _from(long_term, start), _from(bench, start)
    dates = sorted({p.date for p in next((s for s in (trading, long_term, bench) if drawable(s)), [])})
    lines = [
        line for line in (
            _line("trading", "Trading", trading, dates),
            _line("long_term", "Long-term", long_term, dates),
            _line("benchmark", snapshot.benchmark.label if snapshot.benchmark else profile.benchmark.label, bench,
                  dates),
        ) if line is not None
    ]
    by_key = {line.key: line for line in lines}
    t, lt = by_key.get("trading"), by_key.get("long_term")
    real_ids = {b.id for b in real_books}
    review = [s.review_at_trades for s in snapshot.strategies
              if s.review_at_trades and s.id in {b.strategy_id for b in real_books}]
    return Comparison(
        window=window, start=start, dates=dates, lines=lines,
        gap_pts=round(t.return_pct - lt.return_pct, 2) if t and lt else None,
        shallower=(t.max_drop_pct > lt.max_drop_pct) if t and lt else None,
        real_trades=sum(1 for tr in snapshot.trades if tr.book_id in real_ids),
        review_at=min(review) if review else None,
    )


def _book_rows(snapshot: Snapshot) -> list[BookRow]:
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
            # scorecard on the strategy page compares the same unrounded mean, so the two never disagree)
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


def _source_attention(source: Source, now: dt.datetime, tz: dt.tzinfo) -> Attention | None:
    if source.status == "error":
        return Attention(level="warning", title=f"{source.label} couldn't be read", detail=source.detail,
                         link="/settings")
    if source.status == "stale" and source.last_success is not None:
        when = source.last_success.astimezone(tz).strftime("%a %H:%M")
        age = age_text(now - source.last_success)
        return Attention(level="warning", title=f"{source.label} hasn't synced in {age}",
                         detail=f"{source.kind} · last success {when}", link="/settings")
    return None


def _attention(snapshot: Snapshot, rows: list[BookRow], strategies_review: dict[str, int | None],
               now: dt.datetime, tz: dt.tzinfo) -> list[Attention]:
    books = {b.id: b for b in snapshot.books}
    items: list[Attention] = []
    for p in snapshot.positions:
        book = books.get(p.book_id)
        if book is not None and book.money == "real" and p.stop_price is None:
            items.append(Attention(level="serious", title=f"{p.symbol} has no resting stop",
                                   detail=f"{book.name} · real — no protective stop on record", link="/books"))
    for source in snapshot.sources:
        item = _source_attention(source, now, tz)
        if item:
            items.append(item)
    for row in rows:
        if row.verdict == "below":
            review = strategies_review.get(row.id)
            detail = f"{row.trades} of {review} {row.money} trades · reviewed at {review}" if review else \
                f"{row.trades} {row.money} trades"
            # the strategy's own page; its id is escaped so an odd id can't bend the link into another path
            items.append(Attention(level="note", title=f"{row.name} is below its expected band", detail=detail,
                                   link=f"/strategies/{quote(books[row.id].strategy_id, safe='')}"))
    items.extend(Attention(level=a.level, title=a.title, detail=a.detail, link=a.link) for a in snapshot.alerts)
    order = {"serious": 0, "warning": 1, "note": 2}
    return sorted(items, key=lambda a: order[a.level])


def home_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> HomeView:
    tz = profile.tz
    today = now.astimezone(tz).date()
    history = {s.id: s.points for s in snapshot.account_history}
    net = sum_series([history[a.id] for a in snapshot.accounts if a.id in history])
    total = round(sum(a.value for a in snapshot.accounts), 2)
    net_worth = NetWorth(
        total=total,
        today=_delta(net, today), month=_delta(net, today.replace(day=1)), year=_delta(net, dt.date(today.year, 1, 1)),
        year_flows=round(sum(p.net_flow for p in net[1:] if p.date >= dt.date(today.year, 1, 1)), 2),
        points=net,
    )
    order = ["long_term", "trading", "cash", "other"]
    values = {c: sum(a.value for a in snapshot.accounts if a.category == c) for c in order}
    present = [c for c in order if values[c] > 0]
    cells = largest_remainder([values[c] for c in present])
    allocation = [
        Slice(category=c, label=CATEGORY_LABELS[c], value=round(values[c], 2),
              share=round(values[c] / total * 100, 2) if total else 0.0, cells=n)
        for c, n in zip(present, cells)
    ]
    accounts = [AccountRow(id=a.id, name=a.name, category=a.category, value=a.value,
                           day_pct=_day_pct(list(history.get(a.id, [])))) for a in snapshot.accounts]
    real_books = [b for b in snapshot.books if b.money == "real"]
    comparison = _comparison(snapshot, profile, today, real_books)
    rows = _book_rows(snapshot)
    review_by_book = {b.id: next((s.review_at_trades for s in snapshot.strategies if s.id == b.strategy_id), None)
                      for b in snapshot.books}
    attention = _attention(snapshot, rows, review_by_book, now, tz)
    books = {b.id: b for b in snapshot.books}
    positions = [
        PositionRow(
            book_id=p.book_id, book=books[p.book_id].name if p.book_id in books else p.book_id, symbol=p.symbol,
            money=books[p.book_id].money if p.book_id in books else "paper", quantity=p.quantity,
            entry_price=p.entry_price, last_price=p.last_price, stop_price=p.stop_price,
            room_pct=round((p.last_price - p.stop_price) / p.last_price * 100, 2)
            if p.stop_price is not None and p.last_price > 0 else None,
            pnl=round((p.last_price - p.entry_price) * p.quantity, 2), note=p.note,
        )
        for p in snapshot.positions
    ]
    positions.sort(key=lambda r: (r.money != "real", r.room_pct is not None, r.symbol))
    runs = sorted((r for r in snapshot.runs if r.time.astimezone(tz).date() == today), key=lambda r: r.time)
    return HomeView(
        as_of=now,
        summary=Summary(day_change=net_worth.today.amount, gap_pts=comparison.gap_pts,
                        needs_you=sum(1 for a in attention if a.level in ("serious", "warning"))),
        net_worth=net_worth, allocation=allocation, accounts=accounts, comparison=comparison, attention=attention,
        books=rows, today=[TodayRun(time=r.time, label=r.label, status=r.status, detail=r.detail) for r in runs],
        positions=positions,
    )
