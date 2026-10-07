"""The Strategy page's later sections: where the money works, trade anatomy, is it worth it, month by month and
all trades."""

import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import (
    Account,
    Bar,
    Benchmark,
    Book,
    Expected,
    Position,
    Series,
    Snapshot,
    Strategy,
    Trade,
    TradeChart,
    ValuePoint,
    WatchItem,
)
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.strategy import strategy_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)  # a Friday
D = dt.date


@pytest.fixture(scope="module")
def demo():
    return collect(DEMO_PROFILE, NOW)


def book(slots=3, started=D(2025, 9, 1)):
    return Book(id="a", name="Test", money="real", strategy_id="s", status="running", started=started, value=1000,
                slots_total=slots)


def trade(opened, closed, ret=1.0, symbol="HD"):
    return Trade(book_id="a", symbol=symbol, opened=opened, closed=closed, entry_price=100,
                 exit_price=100 * (1 + ret / 100), quantity=1, pnl=ret, return_pct=ret)


def bars(days, price=100.0):
    return [Bar(date=d, open=price, high=price + 1, low=price - 1, close=price) for d in days]


def view(**parts):
    strategy = Strategy(id="s", name="Test", watch=parts.pop("watch", []), expected=parts.pop("expected", None))
    books = parts.pop("books", [book()])
    return strategy_view(Snapshot(generated_at=NOW, books=books, strategies=[strategy], **parts), Profile(), NOW, "s")


def week(start, n):
    return [start + dt.timedelta(days=i) for i in range(n)]


def test_slots_free_on_the_close_day_so_a_same_day_close_and_open_count_one():
    """2026-10-07 spec §3.7: HD closes Tuesday at the open and LOW fills in its slot that morning — one slot, not
    two; KO opens Thursday as LOW closes — one again. A trade that opens and closes the same day still counts."""
    days = week(D(2026, 9, 21), 5)  # Monday to Friday
    history = [Series(id="a", points=[ValuePoint(date=d, value=1000) for d in days])]
    trades = [trade(days[0], days[1]), trade(days[1], days[3], symbol="LOW"), trade(days[4], days[4], symbol="PG")]
    pos = Position(book_id="a", symbol="KO", quantity=1, entry_price=10, last_price=10, opened=days[3])
    slots = view(book_history=history, trades=trades, positions=[pos]).slots
    assert slots.days == days and slots.used == [1, 1, 1, 1, 2]
    assert (slots.total, slots.avg_used, slots.working_pct, slots.idle) == (3, 1.2, 40.0, 0)
    assert slots.note.startswith("Slots are not dollars")


def test_two_slices_of_one_fill_hold_one_slot_and_an_open_remainder_keeps_it():
    """A partially filled exit leaves two closed trades and an open position with the same symbol and open day: the
    lot held one slot all along, and still does."""
    days = week(D(2026, 9, 21), 5)
    history = [Series(id="a", points=[ValuePoint(date=d, value=1000) for d in days])]
    trades = [trade(days[0], days[2]), trade(days[0], days[3])]  # both HD, both opened Monday
    pos = Position(book_id="a", symbol="HD", quantity=1, entry_price=10, last_price=12, opened=days[0])
    slots = view(book_history=history, trades=trades, positions=[pos]).slots
    assert slots.used == [1, 1, 1, 1, 1]


def test_slots_say_how_much_money_is_deployed_against_the_books_capital():
    days = week(D(2026, 9, 21), 5)
    history = [Series(id="a", points=[ValuePoint(date=d, value=1000) for d in days])]
    pos = [Position(book_id="a", symbol="HD", quantity=2, entry_price=100, last_price=110, opened=days[0]),
           Position(book_id="a", symbol="KO", quantity=3, entry_price=50, last_price=40, opened=days[1])]
    b = Book(id="a", name="Test", money="real", strategy_id="s", status="running", started=days[0], value=340,
             slots_total=5, capital=1000.0, capital_basis="the account")
    slots = view(books=[b], book_history=history, positions=pos).slots
    assert (slots.used[-1], slots.working_pct) == (2, 36.0)  # two of five slots (1.8 on average) ...
    assert (slots.deployed, slots.capital, slots.deployed_pct) == (340.0, 1000.0, 34.0)  # ... a third of the money


def test_slots_fall_back_to_weekdays_without_history_and_count_idle_sessions():
    slots = view().slots
    assert len(slots.days) == 40 and slots.days[-1] == D(2026, 9, 25)
    assert all(d.weekday() < 5 for d in slots.days)
    assert set(slots.used) == {0} and slots.idle == 40 and slots.working_pct == 0.0


def test_a_book_without_slots_says_so_and_still_lists_the_watch():
    watch = [WatchItem(symbol="KO", label="RSI(2)", value=12.4)]
    slots = view(books=[book(slots=None)], watch=watch).slots
    assert slots.total is None and slots.days == [] and slots.avg_used is None
    assert [w.symbol for w in slots.watch] == ["KO"]


def test_the_demo_slots_and_watch_list(demo):
    rsi2 = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real").slots
    assert (rsi2.book_id, rsi2.total, len(rsi2.days), rsi2.days[-1]) == ("rsi2-real", 5, 40, D(2026, 9, 25))
    assert rsi2.used[-1] == 4  # the four open positions
    assert [w.symbol for w in rsi2.watch] == ["KO", "ABT", "UNP"]
    assert strategy_view(demo, DEMO_PROFILE, NOW, "ibs", "real").slots.watch == []


def test_anatomy_lists_the_last_eight_trades_newest_first_and_selects_the_newest_chart(demo):
    a = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real").anatomy
    assert len(a.recent) == 8 and all(r.chart for r in a.recent)
    closes = [r.closed for r in a.recent]
    assert closes == sorted(closes, reverse=True)
    assert a.selected == a.recent[0].key and len(a.charts) == 8
    chart = next(c for c in a.charts if c.key == a.selected)
    assert chart.bars[chart.entry].open == chart.entry_price and chart.entry < chart.exit
    assert chart.indicator is not None and chart.stop == pytest.approx(chart.entry_price * 0.92, abs=0.01)


def test_a_chart_that_matches_no_trade_misses_the_open_day_or_has_a_backwards_trade_is_ignored():
    days = week(D(2026, 9, 14), 12)
    a = trade(days[1], days[3], symbol="HD")
    b = trade(days[4], days[6], symbol="LOW")
    c = trade(days[7], days[9], symbol="KO")
    d = trade(days[11], days[10], symbol="PG")  # closes before it opens: a source's bug, not a crash
    charts = [
        TradeChart(book_id="a", symbol="HD", opened=days[1], bars=bars(days)),
        TradeChart(book_id="a", symbol="LOW", opened=days[4], bars=bars(days[5:])),  # the open day is missing
        TradeChart(book_id="a", symbol="MRK", opened=days[2], bars=bars(days)),  # no such trade
        TradeChart(book_id="a", symbol="PG", opened=days[11], bars=bars(days[11:])),
    ]
    anatomy = view(trades=[a, b, c, d], trade_charts=charts).anatomy
    assert [(r.symbol, r.chart) for r in anatomy.recent] == [
        ("PG", False), ("KO", False), ("LOW", False), ("HD", True)]
    assert [ch.key for ch in anatomy.charts] == [anatomy.selected] == ["a|HD|2026-09-15"]


def test_sessions_held_count_weekdays_after_the_open_and_days_held_count_the_calendar():
    t = trade(D(2026, 9, 18), D(2026, 9, 22))  # Friday to Tuesday
    same_day = trade(D(2026, 9, 23), D(2026, 9, 23), symbol="KO")
    v = view(trades=[t, same_day])
    assert [(r.symbol, r.sessions) for r in v.anatomy.recent] == [("KO", 0), ("HD", 2)]
    assert [(r.symbol, r.days_held) for r in v.trades] == [("KO", 0), ("HD", 4)]


def line(start, days, end_value, drop_at=None):
    """A value series from 100 to `end_value` over `days` calendar days, with an optional 10% dip."""
    points = [ValuePoint(date=start, value=100.0)]
    for i in range(1, days + 1):
        value = 100 + (end_value - 100) * i / days
        points.append(ValuePoint(date=start + dt.timedelta(days=i), value=value * (0.9 if i == drop_at else 1)))
    return points


def test_worth_annualizes_a_year_or_more_marks_a_shorter_history_early_and_skips_under_ninety_days():
    year = view(book_history=[Series(id="a", points=line(D(2025, 9, 25), 365, 110))]).worth.points
    assert [(p.key, p.label, p.early, p.period) for p in year] == [("book", "Real book", False, "12 months")]
    assert year[0].return_pct == pytest.approx(10.0) and str(year[0].drop_pct) == "0.0"  # never "-0.0"
    half = view(book_history=[Series(id="a", points=line(D(2026, 3, 1), 200, 105, drop_at=50))]).worth.points
    assert half[0].early and half[0].period == "7 months"
    assert half[0].return_pct == pytest.approx((1.05 ** (365 / 200) - 1) * 100, abs=0.01)
    assert half[0].drop_pct == pytest.approx(10.0, abs=0.05)  # the one-day 10% dip, net of that day's drift
    assert view(book_history=[Series(id="a", points=line(D(2026, 8, 1), 60, 104))]).worth.points == []


def test_worth_adds_the_backtest_long_term_accounts_and_benchmark_when_they_exist():
    expected = Expected(win_rate=60, avg_trade_pct=1, avg_win_pct=2, avg_loss_pct=-1, trades_per_month=2,
                        sd_trade_pct=2, window="2006–2020", cagr_pct=23.4, max_drawdown_pct=-11.7)
    lt = line(D(2021, 9, 25), 1826, 160)
    accounts = [Account(id="ira", name="IRA", category="long_term", value=160, as_of=NOW)]
    mine = line(D(2025, 9, 25), 365, 110)  # the book: its last 12 months
    worth = view(books=[book()], book_history=[Series(id="a", points=mine)], expected=expected, accounts=accounts,
                 account_history=[Series(id="ira", points=lt)],
                 benchmark=Benchmark(symbol="SPY", label="S&P 500", points=lt)).worth
    # the long-term accounts and the benchmark are measured over the book's own window, so the dates match
    assert [(p.key, p.label, p.period) for p in worth.points] == [
        ("backtest", "Backtest", "2006–2020"), ("book", "Real book", "12 months"),
        ("long_term", "Long-term accounts", "12 months"), ("benchmark", "S&P 500", "12 months")]
    assert (worth.points[0].return_pct, worth.points[0].drop_pct) == (23.4, 11.7)
    assert worth.window == "since 25 Sep" and worth.note == ""
    lt_year = 160 / 148 - 1  # a straight line from 100 to 160 over 5 years: its last year grows 148 → 160
    assert worth.points[2].return_pct == pytest.approx(lt_year * 100, abs=0.2)


def test_worth_without_book_history_shows_the_backtest_alone_and_says_why():
    expected = Expected(win_rate=60, avg_trade_pct=1, avg_win_pct=2, avg_loss_pct=-1, trades_per_month=2,
                        sd_trade_pct=2, window="2006–2020", cagr_pct=23.4, max_drawdown_pct=-11.7)
    lt = line(D(2021, 9, 25), 1826, 160)
    accounts = [Account(id="ira", name="IRA", category="long_term", value=160, as_of=NOW)]
    worth = view(expected=expected, accounts=accounts, account_history=[Series(id="ira", points=lt)],
                 benchmark=Benchmark(symbol="SPY", label="S&P 500", points=lt)).worth
    assert [p.key for p in worth.points] == ["backtest"]
    assert worth.note == "The real book sends no value history, so there is nothing to measure yet."
    short = view(book_history=[Series(id="a", points=line(D(2026, 8, 1), 60, 104))]).worth
    assert short.points == [] and short.note == "The real book has 60 days of value history; a yearly figure needs 90."
    assert view(books=[]).worth.note == "No book trades this strategy yet."


def test_the_demo_worth_points(demo):
    points = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real").worth.points
    assert [p.key for p in points] == ["backtest", "book", "long_term", "benchmark"]
    assert (points[1].label, points[1].period, points[1].early) == ("Real book", "12 months", False)
    assert all(p.drop_pct >= 0 for p in points)


def test_monthly_returns_chain_month_ends_over_the_last_twelve_months():
    book_points = [ValuePoint(date=d, value=v) for d, v in [
        (D(2026, 7, 15), 100), (D(2026, 7, 31), 110), (D(2026, 8, 31), 121), (D(2026, 9, 25), 108.9)]]
    lt_points = [ValuePoint(date=d, value=v) for d, v in [
        (D(2026, 7, 15), 100), (D(2026, 7, 31), 101), (D(2026, 8, 31), 102.01), (D(2026, 9, 25), 103.03)]]
    accounts = [Account(id="ira", name="IRA", category="long_term", value=103.03, as_of=NOW)]
    m = view(book_history=[Series(id="a", points=book_points)], accounts=accounts,
             account_history=[Series(id="ira", points=lt_points)]).monthly
    assert [x.month for x in m.months] == [f"2025-{k}" for k in ("10", "11", "12")] + [
        f"2026-{k:02d}" for k in range(1, 10)]
    tail = [(x.month, x.book, x.long_term, x.ahead) for x in m.months[-3:]]
    assert tail == [("2026-07", 10.0, 1.0, True), ("2026-08", 10.0, 1.0, True), ("2026-09", -10.0, 1.0, False)]
    assert m.months[0].book is None and m.months[0].ahead is None
    assert (m.ahead, m.compared) == (2, 3)
    assert (m.best.month, m.best.value, m.worst.month, m.worst.value) == ("2026-07", 10.0, "2026-09", -10.0)


def test_the_demo_monthly_grid(demo):
    m = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real").monthly
    assert (m.months[0].month, m.months[-1].month, m.compared) == ("2025-10", "2026-09", 12)
    assert m.ahead == sum(1 for x in m.months if x.ahead)
    assert m.best.value == max(x.book for x in m.months)


def test_all_trades_are_the_primary_books_newest_first(demo):
    trades = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "paper").trades
    assert len(trades) == 71 and {t.money for t in trades} == {"paper"}
    assert trades[0].closed >= trades[-1].closed
    assert trades[0].days_held == (trades[0].closed - trades[0].opened).days


def test_a_book_with_no_trades_leaves_those_sections_empty():
    v = view()
    assert (v.anatomy.recent, v.anatomy.charts, v.anatomy.selected, v.trades) == ([], [], None, [])
    assert v.monthly.compared == 0 and v.monthly.best is None
