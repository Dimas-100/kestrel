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
    assert flags == {"XLF": "no_stop", "AAPL": None}


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
