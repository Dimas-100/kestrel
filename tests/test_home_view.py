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
from kestrel.views.home import home_view, next_round, round_step

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def demo_home():
    return home_view(collect(DEMO_PROFILE, NOW), DEMO_PROFILE, NOW)


def test_net_worth_is_what_the_accounts_hold_less_what_is_owed(demo_home):
    owned = sum(a.value for a in demo_home.accounts if a.category != "debt")
    assert demo_home.net_worth.owed == 640.0  # the demo's card
    assert demo_home.net_worth.total == pytest.approx(owned - 640.0)
    assert demo_home.net_worth.points[-1].value == pytest.approx(demo_home.net_worth.total)


def test_net_worth_subtracts_debt():
    d = dt.date
    days = [d(2026, 9, 23), d(2026, 9, 24), d(2026, 9, 25)]
    accounts = [Account(id="lt", name="Index fund", category="long_term", value=700, as_of=NOW),
                Account(id="bank", name="Savings", category="cash", value=300, as_of=NOW),
                Account(id="card", name="Card", category="debt", value=200, limit=1000, as_of=NOW)]
    history = [Series(id="lt", points=[ValuePoint(date=day, value=v) for day, v in zip(days, (690, 695, 700))]),
               Series(id="bank", points=[ValuePoint(date=day, value=300) for day in days]),
               # 50 charged on the 24th (money out of the card), then paid down by 100 on the 25th (money in)
               Series(id="card", points=[ValuePoint(date=days[0], value=250), ValuePoint(date=days[1], value=300,
                                                                                          net_flow=-50),
                                         ValuePoint(date=days[2], value=200, net_flow=100)])]
    home = home_view(_tiny(accounts, history), Profile(), NOW)
    nw = home.net_worth
    assert (nw.total, nw.owed) == (800.0, 200.0)
    # the card counts against net worth, and its charge and payment are money moving, not the market
    assert [(p.value, p.net_flow) for p in nw.points] == [(740.0, 0.0), (695.0, -50.0), (800.0, 100.0)]
    assert [(s.category, s.value, s.share) for s in home.allocation] == [("long_term", 700.0, 70.0),
                                                                        ("cash", 300.0, 30.0)]
    assert sum(s.cells for s in home.allocation) == 100
    card = next(a for a in home.accounts if a.id == "card")
    assert (card.category, card.value, card.day_pct) == ("debt", 200.0, None)  # an owed balance has no day's return


def test_an_overpaid_card_adds_to_net_worth_and_no_debt_owes_nothing():
    credit = Account(id="card", name="Card", category="debt", value=-50, as_of=NOW)  # money owed to you
    held = Account(id="lt", name="Index fund", category="long_term", value=1000, as_of=NOW)
    nw = home_view(_tiny([held, credit], []), Profile(), NOW).net_worth
    assert (nw.total, nw.owed) == (1050.0, -50.0)
    assert home_view(_tiny([held], []), Profile(), NOW).net_worth.owed == 0.0


def _bank_feed_household():
    """A brokerage with history (a collector) next to a checking account and a card from a bank feed that reports
    only today's balance."""
    d = dt.date
    days = [d(2026, 9, 23), d(2026, 9, 24), d(2026, 9, 25)]
    brokerage = [ValuePoint(date=days[0], value=9812.37), ValuePoint(date=days[1], value=9904.15),
                 ValuePoint(date=days[2], value=10406.88, net_flow=500)]
    accounts = [Account(id="brokerage", name="Brokerage", category="long_term", value=10406.88, as_of=NOW),
                Account(id="checking", name="Checking", category="cash", value=4218.66, cash=4218.66, as_of=NOW),
                Account(id="card", name="Card", category="debt", value=1187.29, as_of=NOW)]
    return _tiny(accounts, [Series(id="brokerage", points=brokerage)])


def test_an_account_without_history_joins_net_worth_flat_at_todays_balance():
    nw = home_view(_bank_feed_household(), Profile(), NOW).net_worth
    # 10,406.88 + 4,218.66 - 1,187.29: the hero and the chart's last point are one figure
    assert nw.total == 13438.25
    assert nw.points[-1].value == nw.total
    # checking and the card sit at today's balance on every date (3,031.37 together), with no flows of their own
    assert [(p.value, p.net_flow) for p in nw.points] == [(12843.74, 0.0), (12935.52, 0.0), (13438.25, 500.0)]
    assert nw.no_history == 2
    # a flat line moves nothing: the day's change is the brokerage's alone, 502.73 of it
    assert nw.today.amount == 502.73
    assert nw.year_flows == 500.0


def test_every_account_with_history_leaves_no_count():
    lt = Account(id="lt", name="Index fund", category="long_term", value=512.34, as_of=NOW)
    history = [Series(id="lt", points=[ValuePoint(date=dt.date(2026, 9, 24), value=500.11),
                                       ValuePoint(date=dt.date(2026, 9, 25), value=512.34)])]
    assert home_view(_tiny([lt], history), Profile(), NOW).net_worth.no_history == 0


def test_a_change_of_a_net_worth_below_zero_has_no_percent():
    # what is owed (2,000, no history) outweighs what is held: a percent of a negative base would read backwards
    lt = Account(id="lt", name="Index fund", category="long_term", value=512.34, as_of=NOW)
    card = Account(id="card", name="Card", category="debt", value=2000, as_of=NOW)
    history = [Series(id="lt", points=[ValuePoint(date=dt.date(2026, 9, 24), value=500.11),
                                       ValuePoint(date=dt.date(2026, 9, 25), value=512.34)])]
    nw = home_view(_tiny([lt, card], history), Profile(), NOW).net_worth
    assert nw.total == nw.points[-1].value == -1487.66
    assert (nw.today.amount, nw.today.pct) == (12.23, None)


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
    assert c.real_trades == 34 and c.review_at == 20


def test_attention_is_ordered_serious_warning_note(demo_home):
    levels = [a.level for a in demo_home.attention]
    assert levels == sorted(levels, key=["serious", "warning", "note"].index)
    titles = [a.title for a in demo_home.attention]
    # MSFT's stop rests but isn't reported (stop_resting=True): no false "no resting stop" alarm
    assert "MSFT has no resting stop" not in titles
    assert any("Savings" in t for t in titles)
    # an off-plan target and an alert thesis are warnings; a watch thesis is a note (Plan owns their arithmetic)
    assert "XLV is over plan in Roth IRA" in titles and "XLP is under plan in Roth IRA" in titles
    assert "HD: thesis needs a look" in titles and "XLE: thesis needs a look" in titles
    by_title = {a.title: a.level for a in demo_home.attention}
    assert (by_title["HD: thesis needs a look"], by_title["XLE: thesis needs a look"]) == ("warning", "note")
    link = next(a.link for a in demo_home.attention if a.title == "XLV is over plan in Roth IRA")
    assert link == "/plan"
    assert demo_home.summary.needs_you == 4


def test_stale_source_warning_stays_in_the_top_three(demo_home):
    # source and book items are worked out before the plan's target/thesis items are appended, so a widening set
    # of off-plan targets or theses can never bump a stale-source warning further down the list than it already was
    top3 = demo_home.attention[:3]
    assert any("Savings" in a.title and a.level == "warning" for a in top3)


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


def test_a_real_position_with_no_stop_links_to_its_own_book():
    book = Book(id="swing/real", name="Swing", money="real", strategy_id="s", status="running",
                started=dt.date(2026, 1, 1), value=1000)
    pos = Position(book_id="swing/real", symbol="KLAC", quantity=1, entry_price=512.4, last_price=518.07,
                   opened=dt.date(2026, 9, 24))
    item, = home_view(_tiny([], [], books=[book], positions=[pos]), Profile(), NOW).attention
    # nothing on record is a warning; only a source that says there is NO stop is serious
    assert (item.level, item.title) == ("warning", "KLAC's stop isn't on record")
    assert item.link == "/books/swing%2Freal"  # the book's own page, its id escaped so it stays one path segment
    none = Position(book_id="swing/real", symbol="KLAC", quantity=1, entry_price=512.4, last_price=518.07,
                    stop_resting=False, opened=dt.date(2026, 9, 24))
    item, = home_view(_tiny([], [], books=[book], positions=[none]), Profile(), NOW).attention
    assert (item.level, item.title) == ("serious", "KLAC has no resting stop")
    assert home_view(_tiny([], [], books=[book], positions=[none]), Profile(), NOW).positions[0].flag == "no_stop"


def test_a_paper_position_without_a_stop_is_not_an_alarm():
    book = Book(id="p", name="Paper", money="paper", strategy_id="s", status="running", started=dt.date(2026, 1, 1),
                value=1000)
    pos = Position(book_id="p", symbol="XLF", quantity=1, entry_price=50, last_price=51, opened=dt.date(2026, 9, 25))
    home = home_view(_tiny([], [], books=[book], positions=[pos]), Profile(), NOW)
    assert home.attention == []


def test_a_real_position_whose_stop_rests_but_isnt_reported_is_not_an_alarm():
    # a trading desk that manages its own stops but doesn't report their level: stop_resting=True says a stop is
    # there, so kestrel must not shout "no resting stop" on a lot that is in fact protected
    book = Book(id="b", name="Real", money="real", strategy_id="s", status="running", started=dt.date(2026, 1, 1),
                value=1000)
    pos = Position(book_id="b", symbol="MSFT", quantity=1, entry_price=50, last_price=51, stop_resting=True,
                   opened=dt.date(2026, 9, 25))
    home = home_view(_tiny([], [], books=[book], positions=[pos]), Profile(), NOW)
    assert home.attention == []
    row = home.positions[0]
    assert (row.stop_price, row.stop_resting, row.room_pct) == (None, True, None)


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


def test_net_worth_says_what_is_owned_before_what_is_owed(demo_home):
    nw = demo_home.net_worth
    assert nw.owned == pytest.approx(nw.total + nw.owed)
    assert nw.owned == pytest.approx(sum(a.value for a in demo_home.accounts if a.category != "debt"))
    held = Account(id="a", name="A", category="long_term", value=1000, as_of=NOW)
    card = Account(id="card", name="Card", category="debt", value=200, as_of=NOW)
    nw = home_view(_tiny([held, card], []), Profile(), NOW).net_worth
    assert (nw.owned, nw.owed, nw.total) == (1000.0, 200.0, 800.0)


# ---------------------------------------------------------------- the next round number (2026-10-05 milestones)

def test_the_step_is_half_the_power_of_ten_below_and_the_next_round_number_follows():
    assert [round_step(v) for v in (14215.01, 168278.24, 1421.0, 9800.0, 52300.0, 0.0, -5.0)] == [
        5000.0, 50000.0, 500.0, 500.0, 5000.0, 500.0, 500.0]
    assert [next_round(v) for v in (14215.01, 168278.24, 1421.0, 9800.0, 15000.0)] == [
        15000.0, 200000.0, 1500.0, 10000.0, 20000.0]  # exactly on one: the next is the one after


def test_net_worth_names_the_next_round_number_and_a_crossing_today():
    a = Account(id="a", name="A", category="long_term", value=14215.01, as_of=NOW)
    before = [ValuePoint(date=dt.date(2026, 9, 24), value=14800.0),
              ValuePoint(date=dt.date(2026, 9, 25), value=14215.01)]
    nw = home_view(_tiny([a], [Series(id="a", points=before)]), Profile(), NOW).net_worth
    assert (nw.next_round, nw.to_go, nw.passed_today) == (15000.0, 784.99, None)
    crossed = [ValuePoint(date=dt.date(2026, 9, 24), value=14900.0),
               ValuePoint(date=dt.date(2026, 9, 25), value=15100.0)]
    b = Account(id="a", name="A", category="long_term", value=15100.0, as_of=NOW)
    nw = home_view(_tiny([b], [Series(id="a", points=crossed)]), Profile(), NOW).net_worth
    assert (nw.next_round, nw.passed_today) == (20000.0, 15000.0)
    above = [ValuePoint(date=dt.date(2026, 9, 24), value=15050.0), ValuePoint(date=dt.date(2026, 9, 25), value=15100.0)]
    assert home_view(_tiny([b], [Series(id="a", points=above)]), Profile(), NOW).net_worth.passed_today is None
    assert home_view(_tiny([b], []), Profile(), NOW).net_worth.passed_today is None  # no day before to cross from

