import datetime as dt
import json
from pathlib import Path

import pytest

from kestrel.connectors import collect
from kestrel.contract import Book, Position, Series, Snapshot, ValuePoint
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.books import book_rows, book_view, books_view
from kestrel.views.home import home_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def demo_snapshot():
    return collect(DEMO_PROFILE, NOW)


def test_books_view_real_first_then_paper_with_totals(demo_snapshot):
    v = books_view(demo_snapshot, DEMO_PROFILE, NOW)
    assert [r.money for r in v.rows] == ["real", "paper", "paper", "paper", "paper"]
    real_total = sum(b.value for b in demo_snapshot.books if b.money == "real")
    paper_total = sum(b.value for b in demo_snapshot.books if b.money == "paper")
    assert v.real_value == pytest.approx(real_total)
    assert v.paper_value == pytest.approx(paper_total)
    assert v.as_of == NOW


def test_spark_is_the_last_60_values_of_the_growth_since_the_book_started():
    days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(70)]
    points = [ValuePoint(date=d, value=100 + i) for i, d in enumerate(days)]
    book = Book(id="b", name="B", money="real", strategy_id="s", status="running", started=days[0],
                value=points[-1].value)
    snap = Snapshot(generated_at=NOW, books=[book], book_history=[Series(id="b", points=points)])
    v = books_view(snap, Profile(), NOW)
    row = v.rows[0]
    assert len(row.spark) == 60
    # percent since the first point, like the Book page's equity line: 110 and 169 on a start of 100
    assert (row.spark[0], row.spark[-1]) == (10.0, 69.0)
    assert row.spark[-1] == row.since_pct


def test_a_losing_book_funded_every_ten_days_has_a_spark_that_ends_below_its_start():
    days = [dt.date(2026, 6, 1) + dt.timedelta(days=i) for i in range(80)]
    points, value = [], 1000.0
    for i, day in enumerate(days):
        flow = 500.0 if i % 10 == 5 else 0.0
        value = round(value * 0.997 + flow, 2)  # losing 0.3% a day, topped up every ten days
        points.append(ValuePoint(date=day, value=value, net_flow=flow))
    assert points[-1].value > points[-60].value  # its balance rose: the deposits outran the losses
    book = Book(id="b", name="B", money="paper", strategy_id="s", status="running", started=days[0],
                value=points[-1].value)
    snap = Snapshot(generated_at=NOW, books=[book], book_history=[Series(id="b", points=points)])
    row = books_view(snap, Profile(), NOW).rows[0]
    assert row.since_pct < 0
    assert row.spark[-1] < row.spark[0]  # the deposits never read as gains
    assert row.spark[-1] == row.since_pct


def test_book_view_equity_and_drawdown_share_dates(demo_snapshot):
    v = book_view(demo_snapshot, DEMO_PROFILE, NOW, "rsi2-real")
    assert v.equity.dates == v.drawdown.dates
    assert len(v.equity.dates) > 2
    assert all(val <= 0 for val in v.drawdown.values)
    peak = float("-inf")
    for eq, dd in zip(v.equity.values, v.drawdown.values):
        if eq >= peak:
            assert dd == 0.0
        peak = max(peak, eq)


def test_book_scorecard_matches_home_verdict(demo_snapshot):
    home_row = next(r for r in book_rows(demo_snapshot) if r.id == "rsi2-real")
    v = book_view(demo_snapshot, DEMO_PROFILE, NOW, "rsi2-real")
    assert v.scorecard.verdict == home_row.verdict
    assert (v.scorecard.band_lo, v.scorecard.band_hi) == (home_row.band_lo, home_row.band_hi)
    assert v.scorecard.trades == home_row.trades
    assert v.scorecard.avg_trade_pct == home_row.per_trade_pct


def test_position_without_stop_is_flagged():
    book = Book(id="b", name="B", money="paper", strategy_id="s", status="running", started=dt.date(2026, 9, 1),
                value=1000)
    no_stop = Position(book_id="b", symbol="XLF", quantity=1, entry_price=50, last_price=51,
                        opened=dt.date(2026, 9, 20))
    has_stop = Position(book_id="b", symbol="AAPL", quantity=1, entry_price=100, last_price=101, stop_price=90,
                        opened=dt.date(2026, 9, 20))
    snap = Snapshot(generated_at=NOW, books=[book], positions=[no_stop, has_stop])
    v = book_view(snap, Profile(), NOW, "b")
    flags = {p.symbol: p.flag for p in v.positions}
    # no strategy says how lots are protected: a lot with nothing on record is "not on record", not "missing"
    assert flags == {"XLF": "unknown_stop", "AAPL": None}


def _stop_cases(protection: str, money: str = "real"):
    """Three lots under one strategy: the source says there is NO stop (False), says nothing (None), and reports a
    resting one (True)."""
    from kestrel.contract import Step, Strategy
    protect = [Step(label="Protect", title="A stop rests", text="8% under")] if protection == "" else []
    strategy = Strategy(id="s", name="S", protection=protection, steps=protect)  # type: ignore[arg-type]
    book = Book(id="b", name="B", money=money, strategy_id="s", status="running", started=dt.date(2026, 9, 1),  # type: ignore[arg-type]
                value=1000)
    lots = [Position(book_id="b", symbol=sym, quantity=1, entry_price=50, last_price=51, stop_resting=resting,
                     opened=dt.date(2026, 9, 20)) for sym, resting in (("NONE", False), ("UNKN", None), ("REST", True))]
    return Snapshot(generated_at=NOW, books=[book], positions=lots, strategies=[strategy])


def test_a_stop_strategy_tells_a_missing_stop_from_one_not_on_record():
    v = book_view(_stop_cases("stop"), Profile(), NOW, "b")
    assert {p.symbol: p.flag for p in v.positions} == {"NONE": "no_stop", "UNKN": "unknown_stop", "REST": None}
    titles = [(a.level, a.title) for a in v.attention]
    assert titles == [("serious", "NONE has no resting stop"), ("warning", "UNKN's stop isn't on record")]


def test_a_signal_exit_strategy_expects_no_resting_stop():
    """IBS exits on its own signal: a lot without a stop is how it works, never a red flag — only a source that says
    there is NO stop is still reported as such."""
    v = book_view(_stop_cases("signal", money="paper"), Profile(), NOW, "b")
    assert {p.symbol: p.flag for p in v.positions} == {"NONE": "no_stop", "UNKN": "signal_exit", "REST": None}
    assert v.attention == []          # paper: never an alarm
    assert book_view(_stop_cases("signal"), Profile(), NOW, "b").attention[0].title == "NONE has no resting stop"


def test_a_protect_step_reads_as_a_stop_strategy():
    """A strategy that says nothing about protection but whose rule has a Protect step expects a stop."""
    v = book_view(_stop_cases(""), Profile(), NOW, "b")
    assert {p.symbol: p.flag for p in v.positions} == {"NONE": "no_stop", "UNKN": "unknown_stop", "REST": None}


def test_the_scorecard_shows_realized_unrealized_and_combined(demo_snapshot):
    v = book_view(demo_snapshot, Profile(), NOW, "rsi2-real")
    s = v.scorecard
    assert s.unrealized_pnl == round(sum(p.pnl for p in v.positions), 2)
    assert s.combined_pnl == round(s.total_pnl + s.unrealized_pnl, 2)
    assert v.book.unrealized_pnl == s.unrealized_pnl


def test_every_book_has_comparable_equity_and_invested_figures(demo_snapshot):
    rows = {r.id: r for r in books_view(demo_snapshot, Profile(), NOW).rows}
    real, ibs = rows["rsi2-real"], rows["ibs-paper"]
    assert real.equity == real.value and real.capital_basis.startswith("The trading account's value")
    assert real.invested == round(sum(p.quantity * p.last_price for p in demo_snapshot.positions
                                      if p.book_id == "rsi2-real"), 2)
    assert ibs.equity == 3200.0 and ibs.invested > 0 and ibs.protection == "signal" and real.protection == "stop"
    leader = rows["leader-paper"]
    assert leader.equity == leader.value and leader.capital_basis == "the book's own value"


def test_the_book_page_carries_its_freshness_notes_and_attention(demo_snapshot):
    v = book_view(demo_snapshot, Profile(), NOW, "ibs-paper")
    assert v.freshness == "fresh" and v.notes == ["Exits on strength"]
    assert v.positions[0].note == "Exits on strength" and v.positions[0].flag == "signal_exit"
    stale = demo_snapshot.model_copy(update={"books": [
        b.model_copy(update={"prices_as_of": dt.date(2026, 9, 15)}) if b.id == "ibs-paper" else b
        for b in demo_snapshot.books]})
    v = book_view(stale, Profile(), NOW, "ibs-paper")
    assert v.freshness == "oldest mark 8 sessions old"
    assert [a.title for a in v.attention] == ["Marks are from 2026-09-15"]


def test_a_benchmark_that_starts_after_the_book_is_indexed_from_its_own_first_day():
    from kestrel.contract import Benchmark, Series
    days = [dt.date(2026, 9, 1) + dt.timedelta(days=i) for i in range(10)]
    book = Book(id="b", name="B", money="paper", strategy_id="s", status="running", started=days[0], value=1000)
    history = [ValuePoint(date=d, value=1000 + i * 10) for i, d in enumerate(days)]
    late = [ValuePoint(date=d, value=100 + i) for i, d in enumerate(days) if i >= 4]
    snap = Snapshot(generated_at=NOW, books=[book], book_history=[Series(id="b", points=history)],
                    benchmark=Benchmark(symbol="SPY", label="S&P 500", points=late[::-1]))   # unsorted on purpose
    e = book_view(snap, Profile(), NOW, "b").equity
    assert (e.benchmark_label, e.benchmark_from) == ("S&P 500", days[4])
    assert e.benchmark[:4] == [None] * 4 and e.benchmark[4] == 0.0
    assert e.benchmark[-1] == pytest.approx(5 / 104 * 100, abs=0.01)   # 104 -> 109 from its own first day
    none = Snapshot(generated_at=NOW, books=[book], book_history=[Series(id="b", points=history)])
    e = book_view(none, Profile(), NOW, "b").equity
    assert e.benchmark == [None] * 10 and e.benchmark_from is None and e.benchmark_label == "S&P 500"


def test_a_stop_that_rests_but_isnt_reported_is_not_flagged():
    book = Book(id="b", name="B", money="real", strategy_id="s", status="running", started=dt.date(2026, 9, 1),
                value=1000)
    resting = Position(book_id="b", symbol="MSFT", quantity=1, entry_price=50, last_price=51, stop_resting=True,
                       opened=dt.date(2026, 9, 20))
    snap = Snapshot(generated_at=NOW, books=[book], positions=[resting])
    row = book_view(snap, Profile(), NOW, "b").positions[0]
    assert (row.flag, row.stop_price, row.stop_resting, row.room_pct) == (None, None, True, None)


def test_unknown_book_404(demo_snapshot):
    assert book_view(demo_snapshot, DEMO_PROFILE, NOW, "nope") is None


def test_home_unchanged_after_the_move(demo_snapshot):
    fixture = ROOT / "web" / "src" / "test" / "fixtures" / "home.json"
    expected = json.loads(fixture.read_text(encoding="utf-8"))
    view = home_view(demo_snapshot, DEMO_PROFILE, NOW)
    assert json.loads(view.model_dump_json()) == expected


def test_an_empty_snapshot_still_renders():
    empty = Snapshot(generated_at=NOW)
    v = books_view(empty, Profile(), NOW)
    assert v.rows == [] and v.real_value == 0.0 and v.paper_value == 0.0
    assert book_view(empty, Profile(), NOW, "nope") is None
