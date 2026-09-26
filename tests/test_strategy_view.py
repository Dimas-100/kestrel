import datetime as dt
import math
from statistics import fmean

import pytest

from kestrel.connectors import collect
from kestrel.contract import Book, Expected, Position, Snapshot, Step, Strategy, Trade
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.home import home_view
from kestrel.views.strategy import buckets, strategies_view, strategy_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
D = dt.date
EXPECTED = Expected(win_rate=66, avg_trade_pct=0.84, avg_win_pct=2.45, avg_loss_pct=-2.28, trades_per_month=3.1,
                    sd_trade_pct=3.0)


@pytest.fixture(scope="module")
def demo():
    return collect(DEMO_PROFILE, NOW)


def book(id_, money="real", strategy="s", started=D(2026, 7, 27), slots=None):
    return Book(id=id_, name="Test", money=money, strategy_id=strategy, status="running", started=started, value=1000,
                slots_total=slots)


def trade(book_id, ret, opened, closed=None, symbol="HD"):
    return Trade(book_id=book_id, symbol=symbol, opened=opened, closed=closed or opened, entry_price=100,
                 exit_price=100 * (1 + ret / 100), quantity=1, pnl=ret, return_pct=ret)


def snap(books=(), trades=(), expected=EXPECTED, steps=(), positions=()):
    return Snapshot(generated_at=NOW, books=list(books), trades=list(trades), positions=list(positions),
                    strategies=[Strategy(id="s", name="Test strategy", steps=list(steps), sizing="One lot each.",
                                         expected=expected, review_at_trades=30)])


def test_the_list_has_a_card_per_strategy_with_its_books(demo):
    cards = {c.id: c for c in strategies_view(demo, DEMO_PROFILE, NOW).strategies}
    assert list(cards) == ["rsi2", "ibs", "leader", "verticals"]
    rsi2 = cards["rsi2"]
    assert [(b.money, b.status, b.open) for b in rsi2.books] == [("real", "running", 4), ("paper", "running", 5)]
    assert (rsi2.book, rsi2.trades, rsi2.verdict) == ("real", 34, "in_band")
    assert rsi2.band_lo is not None and rsi2.band_lo < rsi2.per_trade_pct < rsi2.band_hi
    assert (cards["leader"].book, cards["leader"].verdict) == ("paper", "below")
    assert (cards["ibs"].trades, cards["ibs"].verdict) == (7, "early")


def test_the_primary_book_follows_the_requested_money(demo):
    real = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real")
    paper = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "paper")
    assert (real.primary, real.book, real.toggle) == ("rsi2-real", "real", True)
    assert (paper.primary, paper.book, paper.toggle) == ("rsi2-paper", "paper", True)
    ibs = strategy_view(demo, DEMO_PROFILE, NOW, "ibs", "real")  # no real book: the paper one, and no toggle
    assert (ibs.primary, ibs.book, ibs.toggle) == ("ibs-paper", "paper", False)


def test_an_unknown_strategy_has_no_view(demo):
    assert strategy_view(demo, DEMO_PROFILE, NOW, "nope", "real") is None


def test_the_book_with_most_closed_trades_wins_and_a_tie_goes_to_the_first_listed():
    two = [trade("b", 1, D(2026, 9, 1)), trade("b", 2, D(2026, 9, 2))]
    view = strategy_view(snap([book("a"), book("b")], [trade("a", 1, D(2026, 9, 1)), *two]), Profile(), NOW, "s")
    assert view.primary == "b"
    tie = strategy_view(snap([book("a"), book("b")], [trade("a", 1, D(2026, 9, 1)), two[0]]), Profile(), NOW, "s")
    assert tie.primary == "a"


def test_how_it_trades_passes_the_steps_and_sizing_through(demo):
    view = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real")
    assert [s.label for s in view.steps] == ["Universe", "Entry", "Protect", "Exit"]
    assert view.steps[2].params == ["−8% stop", "GTC"]
    assert view.sizing == "Each position is the account value ÷ 6, at most 5 open."
    assert view.expected is not None and view.expected.cagr_pct == 23.4


def test_buckets_are_one_point_wide_and_fold_the_ends():
    distribution = [float(i) for i in range(20)]
    out = buckets([-12, -9.5, -0.2, 0, 2.5, 9.99, 10, 15], distribution)
    assert [b.low for b in out] == list(range(-10, 10))
    counts = {b.low: b.count for b in out if b.count}
    assert counts == {-10: 2, -1: 1, 0: 1, 2: 1, 9: 3}
    assert out[0].share == 25.0 and out[19].expected == 19.0
    assert all(b.expected is None for b in buckets([1.0], [1.0, 2.0]))  # a distribution that isn't 20 buckets


def test_the_scorecard_and_the_other_book_on_demo_data(demo):
    view = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real")
    b = view.behaving
    real = [t.return_pct for t in demo.trades if t.book_id == "rsi2-real"]
    assert b.trades == 34 and sum(x.count for x in b.buckets) == 34 and b.review_at == 50
    rows = {r.key: r for r in b.scorecard}
    assert list(rows) == ["win_rate", "avg_trade", "avg_win", "avg_loss", "per_month"]
    assert [r.label for r in b.scorecard] == ["Win rate", "Average per trade", "Average win", "Average loss",
                                              "Trades per month"]
    assert rows["win_rate"].actual == round(sum(r > 0 for r in real) / 34 * 100, 1)
    assert rows["avg_trade"].actual == pytest.approx(fmean(real), abs=0.005)
    assert rows["avg_trade"].expected == 0.84 and rows["avg_trade"].status == "ok"
    assert all(r.status in {"ok", "above", "below"} for r in b.scorecard)
    paper = [t.return_pct for t in demo.trades if t.book_id == "rsi2-paper"]
    assert (b.other.money, b.other.trades) == ("paper", 71)
    assert b.other.per_trade_pct == pytest.approx(fmean(paper), abs=0.005)


def test_a_measure_outside_its_band_is_flagged_in_the_direction_it_is_off():
    trades = [trade("a", 1.0, D(2026, 8, 3) + dt.timedelta(days=i)) for i in range(20)]
    rows = {r.key: r for r in strategy_view(snap([book("a")], trades), Profile(), NOW, "s").behaving.scorecard}
    assert rows["win_rate"].status == "above"  # 100% against 66% ± 20.8 pts
    assert rows["avg_trade"].status == "ok"  # +1.0% inside 0.84 ± 1.31
    assert rows["avg_win"].status == "below"  # +1.0% under half of +2.45%
    assert (rows["avg_loss"].actual, rows["avg_loss"].status) == (None, "none")  # no losses to average
    assert rows["per_month"].status == "above"  # 20 trades in two months against 3.1 a month


def test_a_backtest_win_rate_outside_0_to_100_does_not_raise():
    trades = [trade("a", 1.0, D(2026, 9, 1) + dt.timedelta(days=i)) for i in range(12)]
    bad = Expected(win_rate=120, avg_trade_pct=0.84, avg_win_pct=2.45, avg_loss_pct=-2.28, trades_per_month=3.1,
                   sd_trade_pct=3.0)
    view = strategy_view(snap([book("a")], trades, expected=bad), Profile(), NOW, "s")
    assert view.behaving.scorecard[0].key == "win_rate"


def test_a_mean_just_outside_the_band_is_not_hidden_by_rounding():
    """The scorecard rounds the mean to 2dp and Home's book row to 3dp; a mean that sits just past the band edge
    must not round back inside it in either place (they'd then disagree with each other at the edge)."""
    n = 10
    sd = math.sqrt(n) / 1.96  # half = 1.96 * sd / sqrt(n) == 1.0, so with avg 0 the band is (-1.0, 1.0)
    edge = Expected(win_rate=50, avg_trade_pct=0.0, avg_win_pct=1.0, avg_loss_pct=-1.0, trades_per_month=1.0,
                    sd_trade_pct=sd)
    trades = [trade("a", 1.0004, D(2026, 9, 1) + dt.timedelta(days=i)) for i in range(n)]
    snapshot = snap([book("a")], trades, expected=edge)
    scorecard = strategy_view(snapshot, Profile(), NOW, "s").behaving.scorecard
    row = {r.key: r for r in scorecard}["avg_trade"]
    assert row.status == "above"  # 1.0004 rounds to 1.00 at 2dp — must not read as "ok"
    verdict = home_view(snapshot, Profile(), NOW).books[0].verdict
    assert verdict == "above"  # 1.0004 rounds to 1.000 at 3dp — must not read as "in_band"


def test_fewer_than_ten_closed_trades_is_too_early_to_judge():
    trades = [trade("a", -9.0, D(2026, 9, i)) for i in range(1, 6)]
    rows = strategy_view(snap([book("a")], trades), Profile(), NOW, "s").behaving.scorecard
    assert {r.status for r in rows} == {"early"}


def test_without_a_backtest_the_actual_figures_stand_alone():
    trades = [trade("a", 1.0 + i, D(2026, 9, 1) + dt.timedelta(days=i)) for i in range(12)]
    view = strategy_view(snap([book("a")], trades, expected=None), Profile(), NOW, "s")
    assert {r.status for r in view.behaving.scorecard} == {"none"}
    assert all(r.expected is None for r in view.behaving.scorecard)
    assert view.behaving.scorecard[0].actual == 100.0
    assert all(b.expected is None for b in view.behaving.buckets)
    assert view.funnel.expected is None and set(view.funnel.lo) == {None}


def test_the_running_mean_follows_close_order_and_the_band_narrows_from_trade_three():
    trades = [
        trade("a", 4.0, D(2026, 9, 1), D(2026, 9, 4), "LOW"),
        trade("a", 2.0, D(2026, 9, 1), D(2026, 9, 2), "HD"),
        trade("a", -3.0, D(2026, 8, 31), D(2026, 9, 4), "KO"),  # same close as LOW, opened earlier: first
        trade("a", 1.0, D(2026, 9, 7), D(2026, 9, 8), "HD"),
    ]
    funnel = strategy_view(snap([book("a")], trades), Profile(), NOW, "s").funnel
    assert funnel.lines[0].values == pytest.approx([2.0, -0.5, 1.0, 1.0])
    assert funnel.lo[:2] == [None, None] and funnel.hi[:2] == [None, None]
    assert funnel.lo[2] == pytest.approx(0.84 - 1.96 * 3 / 3 ** 0.5, abs=0.001)
    assert funnel.hi[3] - funnel.lo[3] < funnel.hi[2] - funnel.lo[2]


def test_the_demo_funnel_has_the_primary_book_first(demo):
    funnel = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "paper").funnel
    assert [(line.money, len(line.values)) for line in funnel.lines] == [("paper", 71), ("real", 34)]
    assert len(funnel.lo) == len(funnel.hi) == 71 and funnel.expected == 0.84


def test_a_strategy_with_no_books_still_describes_itself():
    view = strategy_view(snap(steps=[Step(label="Entry", title="Buy", text="On a signal")]), Profile(), NOW, "s")
    assert (view.primary, view.book, view.toggle, view.books) == (None, None, False, [])
    assert [s.title for s in view.steps] == ["Buy"] and view.sizing == "One lot each."
    assert view.behaving.trades == 0 and view.behaving.other is None
    assert view.funnel.lines == [] and view.funnel.lo == []


def test_open_positions_are_counted_on_the_chips():
    pos = Position(book_id="a", symbol="HD", quantity=1, entry_price=10, last_price=11, opened=D(2026, 9, 24))
    view = strategy_view(snap([book("a")], positions=[pos]), Profile(), NOW, "s")
    assert [(b.id, b.open, b.trades) for b in view.books] == [("a", 1, 0)]
