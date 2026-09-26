import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Account, Book, Position, Series, Snapshot, Source, Strategy, Trade, ValuePoint
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
