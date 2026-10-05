import datetime as dt

import pytest
from fdc_fixture import household

from kestrel.connectors import collect
from kestrel.connectors.fdc import FdcConnector
from kestrel.contract import Account, Holding, Series, Snapshot, Transaction, ValuePoint
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.accounts import account_view, accounts_view, growth, window_start

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
d = dt.date


@pytest.fixture(scope="module")
def demo():
    return collect(DEMO_PROFILE, NOW)


def points(*rows):
    return [ValuePoint(date=day, value=value, net_flow=flow) for day, value, flow in rows]


def account(id_, value, cash=0.0, name=None):
    return Account(id=id_, name=name or id_.title(), category="long_term", value=value, cash=cash, as_of=NOW)


def test_windows_start_on_1_january_a_year_ago_and_at_the_first_point():
    history = points((d(2024, 3, 4), 10, 0), (d(2026, 9, 25), 12, 0))
    today = d(2026, 9, 25)
    assert [window_start(w, today, history) for w in ("ytd", "1y", "all")] == [
        d(2026, 1, 1), d(2025, 9, 25), d(2024, 3, 4)]


def test_growth_splits_the_change_into_what_you_put_in_and_what_the_market_added():
    history = points((d(2025, 12, 31), 1000, 0), (d(2026, 1, 5), 1600, 500), (d(2026, 3, 2), 1700, 0),
                     (d(2026, 9, 25), 1900, 100))
    g = growth(history, d(2026, 1, 1))  # starts from the value held on 1 January: 31 December's
    assert g is not None
    assert (g.start_date, g.start, g.deposits, g.market, g.end) == (d(2025, 12, 31), 1000, 600, 300, 1900)


def test_history_that_begins_after_the_window_starts_at_its_first_point_and_one_point_is_no_growth():
    history = points((d(2026, 3, 2), 500, 0), (d(2026, 6, 1), 700, 150), (d(2026, 9, 25), 640, -50))
    g = growth(history, d(2026, 1, 1))
    assert g is not None and (g.start_date, g.start, g.deposits, g.market) == (d(2026, 3, 2), 500, 100, 40)
    assert growth(history[:1], d(2026, 1, 1)) is None
    assert growth([], d(2026, 1, 1)) is None
    assert growth(history[:2], d(2026, 9, 1)) is None  # history that ended before the window holds one point of it


def test_the_list_puts_the_largest_account_first_with_its_share_its_day_and_its_year(demo):
    view = accounts_view(demo, DEMO_PROFILE, NOW)
    owned = sum(a.value for a in demo.accounts if a.category != "debt")
    assert (view.count, view.total) == (6, round(owned - 640.0, 2))  # net of the card
    assert [a.id for a in view.accounts] == ["roth", "brokerage", "savings", "trading", "checking", "card"]
    assert sum(a.share or 0 for a in view.accounts) == pytest.approx(100, abs=0.02)
    roth = view.accounts[0]
    assert (roth.institution, roth.account_type, roth.category) == ("Brokerage A", "Roth IRA", "long_term")
    history = list(next(s.points for s in demo.account_history if s.id == "roth"))
    assert roth.day_change == round(history[-1].value - history[-2].value - history[-1].net_flow, 2)
    assert roth.year_market == growth(history, d(2026, 1, 1)).market
    ytd = view.growth["ytd"]
    assert ytd is not None and ytd.end == view.total and ytd.start_date == d(2026, 1, 1)
    assert ytd.market == pytest.approx(sum(a.year_market or 0 for a in view.accounts), abs=0.05)


def test_holdings_add_up_by_symbol_with_one_row_for_all_the_cash(demo):
    rows = accounts_view(demo, DEMO_PROFILE, NOW).holdings
    assert len(rows) == 14  # 13 symbols and the cash
    assert [r.value for r in rows] == sorted((r.value for r in rows), reverse=True)
    spy = next(r for r in rows if r.symbol == "SPY")
    assert spy.accounts == ["Brokerage", "Roth IRA"] and spy.name == "S&P 500 index fund"
    assert spy.value == round(sum(h.value for h in demo.holdings if h.symbol == "SPY"), 2)
    cash = next(r for r in rows if r.cash)
    assert (cash.symbol, cash.name) == ("", "Cash")
    assert cash.value == round(sum(a.cash for a in demo.accounts), 2)
    assert cash.accounts == ["Brokerage", "Checking", "High-yield savings", "Roth IRA", "Trading account"]
    assert sum(r.share or 0 for r in rows) == pytest.approx(100, abs=0.05)


def test_one_account_weighs_each_holding_and_leaves_an_unknown_cost_out_of_the_gain(demo):
    view = account_view(demo, DEMO_PROFILE, NOW, "brokerage")
    assert view is not None and (view.name, view.as_of) == ("Brokerage", d(2026, 9, 25))
    assert [h.symbol for h in view.holdings] == ["SPY", "XLK", "COST", "HD", "XLE", "KO", "XLI"]
    assert sum(h.weight or 0 for h in view.holdings) + (view.cash_weight or 0) == pytest.approx(100, abs=0.05)
    ko = next(h for h in view.holdings if h.symbol == "KO")
    assert (ko.cost_basis, ko.gain, ko.gain_pct) == (None, None, None)
    xle = next(h for h in view.holdings if h.symbol == "XLE")
    assert xle.gain is not None and xle.gain < 0 and xle.gain_pct == round(xle.gain / xle.cost_basis * 100, 2)
    known = [h for h in view.holdings if h.cost_basis is not None]
    assert view.totals.unknown_cost == 1
    assert view.totals.gain == round(sum(h.value - h.cost_basis for h in known), 2)
    assert view.totals.value == round(sum(h.value for h in view.holdings) + view.cash, 2) == view.value


def test_the_last_eight_days_money_moved_newest_first():
    history = points(*[(d(2026, month, 1), 1000 + month, 50 if month % 2 else -25) for month in range(1, 10)],
                     (d(2026, 9, 25), 1100, 0))
    snap = Snapshot(generated_at=NOW, accounts=[account("roth", 1100)], account_history=[Series(id="roth",
                                                                                               points=history)])
    flows = account_view(snap, Profile(), NOW, "roth").flows
    assert [(f.date.month, f.amount) for f in flows] == [
        (9, 50), (8, -25), (7, 50), (6, -25), (5, 50), (4, -25), (3, 50), (2, -25)]


def test_money_moved_that_no_transaction_records_yet_says_how_much_of_it_is_unposted():
    history = [ValuePoint(date=d(2026, 9, 23), value=1000), ValuePoint(date=d(2026, 9, 24), value=1150, net_flow=150,
                                                                      unexplained=100)]
    snap = Snapshot(generated_at=NOW, accounts=[account("trading", 1150)],
                    account_history=[Series(id="trading", points=history)])
    (flow,) = account_view(snap, Profile(), NOW, "trading").flows
    assert (flow.date.day, flow.amount, flow.unexplained) == (24, 150, 100)   # 50 recorded, 100 not yet


def test_a_margin_debit_weighs_against_the_holdings_and_a_debit_bigger_than_the_holdings_has_no_weights():
    held = [Holding(account_id="margin", symbol="AAPL", quantity=4, price=250, value=1000, cost_basis=900)]
    snap = Snapshot(generated_at=NOW, accounts=[account("margin", 800, cash=-200)], holdings=held)
    view = account_view(snap, Profile(), NOW, "margin")
    assert (view.holdings[0].weight, view.cash, view.cash_weight) == (125.0, -200.0, -25.0)
    listed = accounts_view(snap, Profile(), NOW).holdings
    assert [(r.name, r.value, r.share) for r in listed] == [("", 1000.0, 125.0), ("Cash", -200.0, -25.0)]
    deep = snap.model_copy(update={"accounts": [account("margin", -100, cash=-1100)]})
    view = account_view(deep, Profile(), NOW, "margin")
    assert (view.holdings[0].weight, view.cash_weight) == (None, None)


def test_a_closed_account_at_zero_sits_last_and_a_household_of_zeros_has_no_shares():
    snap = Snapshot(generated_at=NOW, accounts=[account("old-401k", 0.0, name="Old 401(k)"), account("roth", 500)])
    view = accounts_view(snap, Profile(), NOW)
    assert [(a.id, a.share, a.day_change, a.year_market) for a in view.accounts] == [
        ("roth", 100.0, None, None), ("old-401k", 0.0, None, None)]
    closed = account_view(snap, Profile(), NOW, "old-401k")
    assert closed is not None and (closed.holdings, closed.cash_weight, closed.flows) == ([], None, [])
    assert closed.totals.model_dump() == {"value": 0.0, "cost_basis": None, "gain": None, "gain_pct": None,
                                          "unknown_cost": 0}
    zeros = accounts_view(Snapshot(generated_at=NOW, accounts=[account("old-401k", 0.0)]), Profile(), NOW)
    assert [a.share for a in zeros.accounts] == [None] and zeros.holdings == []


def test_debt_account_has_no_market_growth():
    lt = points((d(2026, 9, 23), 1000, 0), (d(2026, 9, 24), 1010, 0), (d(2026, 9, 25), 1020, 0))
    # 60 charged on the 24th, 100 paid in on the 25th: the owed balance moves against its flows
    owed = points((d(2026, 9, 23), 300, 0), (d(2026, 9, 24), 360, -60), (d(2026, 9, 25), 260, 100))
    card = Account(id="card", name="Card", category="debt", value=260, limit=2000, rate_pct=24.9, cash=-5, as_of=NOW)
    snap = Snapshot(generated_at=NOW, accounts=[account("lt", 1020, cash=20), card],
                    account_history=[Series(id="lt", points=lt), Series(id="card", points=owed)])
    view = accounts_view(snap, Profile(), NOW)
    row = next(a for a in view.accounts if a.id == "card")
    # the row shows what is owed; none of it is a share of what is held, a day's gain or market growth
    assert (row.category, row.value, row.share, row.day_change, row.day_pct, row.year_market) == (
        "debt", 260.0, None, None, None, None)
    assert next(a for a in view.accounts if a.id == "lt").share == 100.0
    # every account together is net of what is owed; the charge and the payment are money moving, not the market
    assert view.total == 760.0
    ytd = view.growth["ytd"]
    assert ytd is not None and (ytd.start, ytd.deposits, ytd.market, ytd.end) == (700.0, 40.0, 20.0, 760.0)
    assert [r.name for r in view.holdings if r.cash] == ["Cash"] and view.holdings[-1].value == 20.0
    one = account_view(snap, Profile(), NOW, "card")
    assert one is not None and (one.category, one.value) == ("debt", 260.0)
    assert one.growth == {"ytd": None, "1y": None, "all": None}
    assert [f.amount for f in one.flows] == [100.0, -60.0]  # what went in and out stays listed


def test_an_account_without_history_counts_at_todays_balance_and_adds_no_market_growth():
    # a brokerage from a collector, a checking account and a card from a bank feed with no history
    brokerage = points((d(2026, 9, 23), 9812.37, 0), (d(2026, 9, 24), 9904.15, 0), (d(2026, 9, 25), 10406.88, 500))
    checking = Account(id="checking", name="Checking", category="cash", value=4218.66, cash=4218.66, as_of=NOW)
    card = Account(id="card", name="Card", category="debt", value=1187.29, as_of=NOW)
    snap = Snapshot(generated_at=NOW, accounts=[account("brokerage", 10406.88), checking, card],
                    account_history=[Series(id="brokerage", points=brokerage)])
    view = accounts_view(snap, Profile(), NOW)
    assert view.total == 13438.25
    everything = view.growth["all"]
    assert everything is not None and everything.end == view.total  # the header and "Now" agree
    # the flat accounts are in the start and the end alike: the market's share is the brokerage's alone
    assert (everything.start, everything.deposits, everything.market) == (12843.74, 500.0, 94.51)
    assert growth(brokerage, d(2026, 9, 23)).market == 94.51
    assert view.no_history == 2


def test_no_accounts_is_an_empty_page_and_an_unknown_account_is_none():
    view = accounts_view(Snapshot(generated_at=NOW), Profile(), NOW)
    assert (view.count, view.total, view.accounts, view.holdings) == (0, 0, [], [])
    assert view.growth == {"ytd": None, "1y": None, "all": None}
    assert account_view(Snapshot(generated_at=NOW), Profile(), NOW, "roth") is None


def test_on_collector_data_the_total_the_growth_and_each_accounts_value_agree(tmp_path):
    snap = FdcConnector("portfolio", "Portfolio", household(tmp_path)).snapshot(NOW)
    view = accounts_view(snap, Profile(), NOW)
    everything = [view.growth["all"], view.growth["ytd"]]
    assert view.total == 14070.0 and [g.end if g else None for g in everything] == [14070.0, 14070.0]
    for a in snap.accounts:
        one = account_view(snap, Profile(), NOW, a.id)
        assert one is not None and one.value == one.points[-1].value
        assert {w: g.end for w, g in one.growth.items() if g} == {w: one.value for w, g in one.growth.items() if g}
    brokerage = account_view(snap, Profile(), NOW, "alex-brokerage")
    assert brokerage.growth["all"].end == brokerage.value == 4500.0  # the snapshot outranks the replayed 4,450


def test_one_account_says_which_day_its_holdings_are_from(tmp_path, demo):
    snap = FdcConnector("portfolio", "Portfolio", household(tmp_path)).snapshot(NOW)
    days = {a.id: account_view(snap, Profile(), NOW, a.id) for a in snap.accounts}
    assert {i: (v.as_of, v.holdings_as_of) for i, v in days.items()} == {
        "alex-roth-ira": (d(2026, 9, 25), d(2026, 9, 24)),  # a newer replayed day than the broker's snapshot
        "alex-brokerage": (d(2026, 9, 25), d(2026, 9, 25)), "alex-trading": (d(2026, 9, 25), d(2026, 9, 25)),
        "alex-crypto": (d(2026, 9, 25), None), "alex-old-401k": (d(2026, 9, 21), None)}  # nothing held: no day
    assert account_view(demo, DEMO_PROFILE, NOW, "roth").holdings_as_of is None  # the demo doesn't say


def test_transactions_newest_first_with_the_totals_in_and_out_and_none_without_any(demo):
    rows = [Transaction(account_id="checking", date=d(2026, 9, 24), amount=-42.17, description="GROCERY MART",
                        counterparty="Grocery Mart", category="groceries"),
            Transaction(account_id="checking", date=d(2026, 9, 25), amount=1500.0, description="PAYROLL ACME"),
            Transaction(account_id="checking", date=d(2026, 9, 24), amount=-10.0, description="COFFEE BAR"),
            Transaction(account_id="card", date=d(2026, 9, 20), amount=200.0, description="PAYMENT")]
    snap = Snapshot(generated_at=NOW, accounts=[account("checking", 800), account("card", 50)], transactions=rows)
    t = account_view(snap, Profile(), NOW, "checking").transactions
    assert [(r.date.day, r.amount, r.description) for r in t.rows] == [
        (25, 1500.0, "PAYROLL ACME"), (24, -42.17, "GROCERY MART"), (24, -10.0, "COFFEE BAR")]
    assert (t.rows[1].counterparty, t.rows[1].category, t.rows[0].counterparty) == ("Grocery Mart", "groceries", "")
    assert (t.count, t.since, t.money_in, t.money_out) == (3, d(2026, 9, 24), 1500.0, 52.17)
    assert account_view(snap, Profile(), NOW, "card").transactions.money_out == 0.0
    assert account_view(Snapshot(generated_at=NOW, accounts=[account("roth", 1)]), Profile(), NOW,
                        "roth").transactions is None
    # the demo: its bank accounts have rows, its brokerage accounts don't
    assert account_view(demo, DEMO_PROFILE, NOW, "checking").transactions.count > 20
    assert account_view(demo, DEMO_PROFILE, NOW, "roth").transactions is None


def test_the_list_says_what_is_owned_and_what_is_owed_beside_the_net(demo):
    v = accounts_view(demo, DEMO_PROFILE, NOW)
    assert v.owned == pytest.approx(v.total + v.owed)
    assert v.owed == 640.0  # the demo's card
    snap = Snapshot(generated_at=NOW, accounts=[account("a", 1000), Account(id="card", name="Card", category="debt",
                                                                                 value=200, as_of=NOW)])
    v = accounts_view(snap, Profile(), NOW)
    assert (v.owned, v.owed, v.total) == (1000.0, 200.0, 800.0)

