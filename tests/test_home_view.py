import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import (
    Account,
    Benchmark,
    Book,
    Position,
    Series,
    Snapshot,
    Source,
    Strategy,
    Trade,
    ValuePoint,
)
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.home import home_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def demo_home():
    return home_view(collect(DEMO_PROFILE, NOW), DEMO_PROFILE, NOW)


def test_net_worth_is_the_sum_of_accounts(demo_home):
    assert demo_home.net_worth.total == pytest.approx(sum(a.value for a in demo_home.accounts))
    assert demo_home.net_worth.points[-1].value == pytest.approx(demo_home.net_worth.total)


def test_allocation_fills_exactly_one_hundred_cells(demo_home):
    assert sum(s.cells for s in demo_home.allocation) == 100
    assert [s.category for s in demo_home.allocation] == ["long_term", "trading", "cash"]


def test_the_comparison_is_year_to_date_with_three_aligned_lines(demo_home):
    c = demo_home.comparison
    assert c.window == "ytd" and c.dates[0] >= dt.date(2026, 1, 1)
    assert [line.key for line in c.lines] == ["trading", "long_term", "benchmark"]
    assert all(len(line.values) == len(c.dates) for line in c.lines)
    assert c.lines[0].values[0] == 0.0
    assert c.gap_pts == pytest.approx(c.lines[0].return_pct - c.lines[1].return_pct, abs=0.01)
    assert c.real_trades == 34 and c.review_at == 50


def test_attention_is_ordered_serious_warning_note(demo_home):
    levels = [a.level for a in demo_home.attention]
    assert levels == sorted(levels, key=["serious", "warning", "note"].index)
    titles = [a.title for a in demo_home.attention]
    assert "MSFT has no resting stop" in titles
    assert any("Savings" in t for t in titles)
    assert demo_home.summary.needs_you == 2


def test_book_verdicts(demo_home):
    verdicts = {b.id: b.verdict for b in demo_home.books}
    assert verdicts["rsi2-real"] == "in_band"
    assert verdicts["ibs-paper"] == "early"  # 7 trades is too few to judge
    assert verdicts["leader-paper"] == "below"


def test_positions_list_real_money_first_and_an_unprotected_one_first_of_all(demo_home):
    first = demo_home.positions[0]
    assert (first.symbol, first.money, first.room_pct) == ("MSFT", "real", None)
    assert all(p.money == "real" for p in demo_home.positions[:4])


def test_today_holds_only_today(demo_home):
    assert [r.label for r in demo_home.today][:2] == ["Opening leader · paper", "Morning run"]


def _tiny(accounts, history, books=(), book_history=(), trades=(), positions=(), strategies=(), sources=()):
    return Snapshot(generated_at=NOW, accounts=list(accounts), account_history=list(history), books=list(books),
                    book_history=list(book_history), trades=list(trades), positions=list(positions),
                    strategies=list(strategies), sources=list(sources))


def test_an_empty_snapshot_still_renders():
    home = home_view(_tiny([], []), Profile(), NOW)
    assert home.net_worth.total == 0 and home.allocation == [] and home.comparison.lines == []
    assert home.comparison.gap_pts is None and home.books == [] and home.attention == []


def test_early_january_falls_back_to_twelve_months():
    days = [dt.date(2025, 12, 30) - dt.timedelta(days=i) for i in range(30)][::-1] + [dt.date(2026, 1, 2)]
    points = [ValuePoint(date=d, value=100 + i) for i, d in enumerate(days)]
    acct = Account(id="a", name="A", category="long_term", value=points[-1].value, as_of=NOW)
    home = home_view(_tiny([acct], [Series(id="a", points=points)]), Profile(), NOW.replace(month=1, day=2))
    assert home.comparison.window == "12m"
    assert len(home.comparison.dates) == len(days)


def test_every_comparison_line_starts_on_the_same_day():
    """A long-term account held all year (+10%) and a real book opened on 1 July (+4%) are compared from 1 July."""
    d = dt.date
    lt = [ValuePoint(date=day, value=v) for day, v in [
        (d(2026, 1, 1), 100), (d(2026, 4, 1), 102), (d(2026, 7, 1), 105), (d(2026, 8, 3), 106), (d(2026, 9, 1), 108),
        (d(2026, 9, 25), 110)]]
    book = [ValuePoint(date=day, value=v) for day, v in [
        (d(2026, 7, 1), 1000), (d(2026, 7, 15), 1010), (d(2026, 8, 3), 1020), (d(2026, 9, 1), 1030),
        (d(2026, 9, 25), 1040)]]
    # the benchmark has no close on 1 July itself: it starts from the last close before it
    spx = [ValuePoint(date=day, value=v) for day, v in [
        (d(2026, 1, 2), 500), (d(2026, 6, 30), 525), (d(2026, 7, 2), 530), (d(2026, 9, 25), 550)]]
    snapshot = Snapshot(
        generated_at=NOW,
        accounts=[Account(id="lt", name="Index fund", category="long_term", value=110, as_of=NOW)],
        account_history=[Series(id="lt", points=lt)],
        books=[Book(id="real", name="Real", money="real", strategy_id="s", status="running", started=d(2026, 7, 1),
                    value=1040)],
        book_history=[Series(id="real", points=book)],
        benchmark=Benchmark(symbol="SPY", label="S&P 500", points=spx),
    )
    c = home_view(snapshot, Profile(), NOW).comparison
    assert c.window == "ytd" and c.start == d(2026, 7, 1) and c.dates[0] == d(2026, 7, 1)
    assert [line.key for line in c.lines] == ["trading", "long_term", "benchmark"]
    assert [line.values[0] for line in c.lines] == [0.0, 0.0, 0.0]
    returns = {line.key: line.return_pct for line in c.lines}
    assert returns == {"trading": 4.0, "long_term": pytest.approx(4.76), "benchmark": pytest.approx(4.76)}
    assert c.gap_pts == pytest.approx(-0.76)  # 4.0 - 4.76 over the shared period, not 4.0 - 10.0


def test_a_paper_position_without_a_stop_is_not_an_alarm():
    book = Book(id="p", name="Paper", money="paper", strategy_id="s", status="running", started=dt.date(2026, 1, 1),
                value=1000)
    pos = Position(book_id="p", symbol="XLF", quantity=1, entry_price=50, last_price=51, opened=dt.date(2026, 9, 25))
    home = home_view(_tiny([], [], books=[book], positions=[pos]), Profile(), NOW)
    assert home.attention == []


def test_an_error_source_becomes_a_warning():
    src = Source(id="desk", label="Trading desk", kind="feed", status="error", detail="timed out")
    home = home_view(_tiny([], [], sources=[src]), Profile(), NOW)
    assert [(a.level, a.title) for a in home.attention] == [("warning", "Trading desk couldn't be read")]


def test_a_book_without_history_or_trades_has_no_numbers_but_still_shows():
    book = Book(id="b", name="New", money="real", strategy_id="s", status="running", started=dt.date(2026, 9, 25),
                value=500, slots_total=3)
    strat = Strategy(id="s", name="New strategy")
    trade = Trade(book_id="b", symbol="HD", opened=dt.date(2026, 9, 24), closed=dt.date(2026, 9, 25),
                  entry_price=10, exit_price=11, quantity=1, pnl=1, return_pct=10)
    home = home_view(_tiny([], [], books=[book], strategies=[strat], trades=[trade]), Profile(), NOW)
    row = home.books[0]
    assert row.day_change is None and row.since_pct is None
    assert row.verdict == "none"  # no expectation to compare with
    assert row.slots_used == 0 and row.slots_total == 3


def test_a_real_book_on_its_first_day_does_not_empty_the_comparison():
    """A book with a single point can't be drawn yet; it must not move the shared start or the window."""
    d = dt.date
    lt = [ValuePoint(date=d(2026, 1, 2) + dt.timedelta(days=i), value=100 + i) for i in range(260)]
    spx = [ValuePoint(date=p.date, value=500 + p.value) for p in lt]
    first_day = [ValuePoint(date=d(2026, 9, 25), value=2000)]
    snapshot = Snapshot(
        generated_at=NOW,
        accounts=[Account(id="lt", name="Index fund", category="long_term", value=lt[-1].value, as_of=NOW)],
        account_history=[Series(id="lt", points=lt)],
        books=[Book(id="new", name="New", money="real", strategy_id="s", status="running", started=d(2026, 9, 25),
                    value=2000)],
        book_history=[Series(id="new", points=first_day)],
        benchmark=Benchmark(symbol="SPY", label="S&P 500", points=spx),
    )
    c = home_view(snapshot, Profile(), NOW).comparison
    assert c.window == "ytd" and c.start == d(2026, 1, 2) and len(c.dates) > 200
    assert [line.key for line in c.lines] == ["long_term", "benchmark"]
    assert c.gap_pts is None


def test_a_book_below_its_band_links_to_its_strategy(demo_home):
    below = next(a for a in demo_home.attention if a.title == "Opening leader is below its expected band")
    assert below.link == "/strategies/leader"


def test_until_a_real_book_has_a_history_the_trading_accounts_are_the_trading_line():
    d = dt.date
    days = [d(2026, 1, 2), d(2026, 3, 2), d(2026, 5, 1), d(2026, 7, 1), d(2026, 9, 1), d(2026, 9, 25)]
    trading = [ValuePoint(date=day, value=1000 + 20 * i) for i, day in enumerate(days)]  # +10%
    lt = [ValuePoint(date=day, value=100 + i) for i, day in enumerate(days)]  # +5%
    accounts = [Account(id="desk", name="Trading", category="trading", value=1100, as_of=NOW),
                Account(id="lt", name="Index fund", category="long_term", value=105, as_of=NOW)]
    history = [Series(id="desk", points=trading), Series(id="lt", points=lt)]
    book = Book(id="real", name="Real", money="real", strategy_id="s", status="running", started=d(2026, 9, 24),
                value=2100)

    def lines(book_points):
        snapshot = Snapshot(generated_at=NOW, accounts=accounts, account_history=history,
                            books=[book] if book_points else [], book_history=[Series(id="real", points=book_points)])
        comparison = home_view(snapshot, Profile(), NOW).comparison
        return {line.key: (line.label, line.return_pct) for line in comparison.lines}

    assert lines([]) == {"trading": ("Trading", 10.0), "long_term": ("Long-term", 5.0)}
    first_day = [ValuePoint(date=d(2026, 9, 25), value=2000)]
    assert lines(first_day)["trading"] == ("Trading", 10.0)  # one point is not a history yet
    two_days = [ValuePoint(date=d(2026, 9, 24), value=2000), ValuePoint(date=d(2026, 9, 25), value=2100)]
    assert lines(two_days)["trading"] == ("Trading", 5.0)
