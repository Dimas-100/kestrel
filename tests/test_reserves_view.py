import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Account, Snapshot, Target, Transaction
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.reserves import reserves_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


def account(id_, category, value, *, rate_pct=None, limit=None, name=None, institution=""):
    return Account(id=id_, name=name or id_.title(), institution=institution, category=category, value=value,
                  as_of=NOW, rate_pct=rate_pct, limit=limit)


def snap(*accounts):
    return Snapshot(generated_at=NOW, accounts=list(accounts))


@pytest.fixture(scope="module")
def demo_reserves():
    return reserves_view(collect(DEMO_PROFILE, NOW), DEMO_PROFILE, NOW)


def test_totals_and_utilization():
    s = snap(
        account("savings", "cash", 8000, rate_pct=4.1), account("checking", "cash", 2000),
        account("card_a", "debt", 500, rate_pct=20.0, limit=2000), account("card_b", "debt", 300, limit=1000),
    )
    v = reserves_view(s, Profile(), NOW)
    assert (v.totals.cash, v.totals.owed, v.totals.net) == (10000.0, 800.0, 9200.0)
    # utilization is over every line WITH a limit: (500 + 300) / (2000 + 1000)
    assert v.totals.utilization_pct == pytest.approx(26.67, abs=0.01)
    card_a = next(d for d in v.debts if d.id == "card_a")
    assert card_a.utilization_pct == 25.0


def test_a_debt_with_no_limit_is_left_out_of_utilization():
    s = snap(account("card", "debt", 100, rate_pct=20.0))  # no limit at all
    v = reserves_view(s, Profile(), NOW)
    assert v.debts[0].utilization_pct is None and v.totals.utilization_pct is None


def test_a_zero_balance_debt_does_not_set_the_owed_rate():
    s = snap(
        account("paid_off", "debt", 0.0, rate_pct=29.9), account("card", "debt", 400.0, rate_pct=19.9),
        account("savings", "cash", 1000.0, rate_pct=3.0),
    )
    v = reserves_view(s, Profile(), NOW)
    assert v.spread is not None and v.spread.owed_rate_pct == 19.9  # not the paid-off card's higher rate


def test_a_credit_balance_shows_below_zero_and_is_never_negative_utilization():
    s = snap(account("card", "debt", -50.0, limit=1000.0))  # paid past zero: owed to the owner
    v = reserves_view(s, Profile(), NOW)
    assert v.debts[0].owed == -50.0 and v.debts[0].utilization_pct == 0.0
    # totals.owed is a SIGNED sum (only utilization clamps at 0): a lone credit balance must read the same
    # negative number Home's net worth does, or the two pages disagree about what is owed
    assert v.totals.owed == -50.0


def test_totals_owed_is_a_signed_sum_a_credit_balance_offsets_real_debt():
    # non-round values: a card owing 1042.37, a credit balance of 87.65 "owed" to the owner
    s = snap(account("card", "debt", 1042.37), account("refund", "debt", -87.65),
            account("savings", "cash", 3210.19))
    v = reserves_view(s, Profile(), NOW)
    assert v.totals.owed == pytest.approx(1042.37 - 87.65)  # signed sum, not each line clamped at 0 first
    assert v.totals.net == pytest.approx(3210.19 - (1042.37 - 87.65))


def test_spread_is_none_without_a_rated_debt_balance():
    assert reserves_view(snap(account("savings", "cash", 1000.0, rate_pct=4.0)), Profile(), NOW).spread is None
    assert reserves_view(snap(account("card", "debt", 100.0, rate_pct=20.0)), Profile(), NOW).spread is None  # no cash
    unrated = snap(account("card", "debt", 100.0), account("savings", "cash", 1000.0, rate_pct=4.0))
    assert reserves_view(unrated, Profile(), NOW).spread is None  # the debt has no rate to compare


def test_spread_sums_each_lines_own_balance_at_its_own_rate():
    s = snap(
        account("card_a", "debt", 1000.0, rate_pct=20.0), account("card_b", "debt", 500.0, rate_pct=10.0),
        account("savings", "cash", 2000.0, rate_pct=4.0), account("checking", "cash", 1000.0, rate_pct=1.0),
    )
    v = reserves_view(s, Profile(), NOW)
    assert v.spread.owed_rate_pct == 20.0 and v.spread.earned_rate_pct == 4.0
    assert v.spread.yearly_cost == pytest.approx(1000 * 0.20 + 500 * 0.10)
    assert v.spread.yearly_earned == pytest.approx(2000 * 0.04 + 1000 * 0.01)
    assert not hasattr(v.spread, "gap")  # a year's cost and a year's earnings are shown apart, never netted


def test_paying_the_dearest_debt_from_cash_saves_the_rate_difference_on_what_moves():
    s = snap(
        account("card_a", "debt", 1286.73, rate_pct=27.49, name="Card A"),
        account("card_b", "debt", 422.18, rate_pct=18.9, name="Card B"),
        account("savings", "cash", 3417.52, rate_pct=4.35), account("checking", "cash", 812.40),
    )
    v = reserves_view(s, Profile(), NOW)
    # a year of each, apart: 1,286.73 x 27.49% + 422.18 x 18.9% owed; 3,417.52 x 4.35% earned
    assert (v.spread.yearly_cost, v.spread.yearly_earned) == (433.51, 148.66)
    # the dearest debt is all covered by the 4,229.92 of cash: 1,286.73 x (27.49 - 4.35)%
    assert (v.spread.owed_name, v.spread.pay_down, v.spread.pay_down_saves) == ("Card A", 1286.73, 297.75)


def test_paying_down_moves_no_more_than_the_cash_there_is():
    s = snap(account("card", "debt", 1286.73, rate_pct=27.49, name="Card"),
             account("savings", "cash", 612.08, rate_pct=3.9))
    v = reserves_view(s, Profile(), NOW)
    assert (v.spread.pay_down, v.spread.pay_down_saves) == (612.08, 144.39)  # 612.08 x (27.49 - 3.9)%


def test_no_pay_down_when_cash_earns_more_than_the_debt_costs_or_there_is_no_cash():
    cheap = reserves_view(snap(account("loan", "debt", 5000.0, rate_pct=3.5),
                               account("savings", "cash", 2500.0, rate_pct=4.35)), Profile(), NOW)
    assert cheap.spread is not None and (cheap.spread.pay_down, cheap.spread.pay_down_saves) == (None, None)
    overdrawn = reserves_view(snap(account("card", "debt", 900.0, rate_pct=24.0),
                                   account("savings", "cash", 0.0, rate_pct=4.0),
                                   account("checking", "cash", -35.17)), Profile(), NOW)
    assert overdrawn.spread is not None and (overdrawn.spread.pay_down, overdrawn.spread.pay_down_saves) == (None, None)


def test_no_cash_or_debt_is_an_empty_view():
    v = reserves_view(snap(account("brokerage", "long_term", 1000.0)), Profile(), NOW)
    assert v.cash == [] and v.debts == [] and v.spread is None
    assert (v.totals.cash, v.totals.owed, v.totals.net, v.totals.utilization_pct) == (0.0, 0.0, 0.0, None)


def test_cash_and_debts_are_largest_first(demo_reserves):
    assert [c.value for c in demo_reserves.cash] == sorted((c.value for c in demo_reserves.cash), reverse=True)
    assert demo_reserves.debts[0].id == "card"


def test_demo_spread_sentence_figures(demo_reserves):
    assert demo_reserves.spread.owed_rate_pct == 24.9 and demo_reserves.spread.earned_rate_pct == 4.1


def test_reserves_fills_from_the_collector_alone(tmp_path):
    from fdc_fixture import Warehouse, d

    from kestrel.connectors.fdc import FdcConnector

    w = Warehouse(tmp_path / "bank.db")
    card = w.account("Example Bank Visa", "example_bank", "credit_card", flows="balance", rate_pct=24.9,
                     credit_limit=5000.0, origin="simplefin")
    savings = w.account("Example Bank Savings", "example_bank", "savings", flows="balance", rate_pct=4.1,
                        origin="simplefin")
    w.day(card, d(24), {}, cash=-640.0)
    w.snapshot(card, d(24), [], cash=-640.0, available=0.0)
    w.day(savings, d(24), {}, cash=24243.44)
    w.snapshot(savings, d(24), [], cash=24243.44)
    w.run("derive", "ok", "2026-09-24T22:00:00Z")
    snapshot = FdcConnector("bank", "Bank", w.close()).snapshot(NOW)
    view = reserves_view(snapshot, DEMO_PROFILE, NOW)
    debt = {line.name: line for line in view.debts}
    assert debt["Example Bank Visa"].owed == 640.0 and debt["Example Bank Visa"].limit == 5000.0
    assert debt["Example Bank Visa"].utilization_pct == 12.8 and debt["Example Bank Visa"].rate_pct == 24.9
    assert {line.name: line.rate_pct for line in view.cash} == {"Example Bank Savings": 4.1}


# ---------------------------------------------------------------- runway, flows, shares and the sentence (2026-10-05)

def row(account_id, day, amount, description="x"):
    return Transaction(account_id=account_id, date=dt.date.fromisoformat(day), amount=amount, description=description)


def with_rows(rows, targets=(), *accounts):
    return Snapshot(generated_at=NOW, accounts=list(accounts), transactions=list(rows), targets=list(targets))


CASH = (account("checking", "cash", 3000), account("savings", "cash", 7000, rate_pct=4.0))
RUNWAY_TARGET = Target(id="runway", label="Cash runway", unit="x", target=6, low=4, high=8, actual=5.0)
ROWS = [row("checking", "2026-09-01", -1000), row("checking", "2026-09-10", 2000), row("checking", "2026-09-20", -500),
        row("checking", "2026-09-25", -500), row("card", "2026-09-12", -80)]  # the card's charge is not cash leaving


def test_runway_from_the_pace_money_left_the_cash_accounts_with_the_band_from_a_runway_target():
    v = reserves_view(with_rows(ROWS, [RUNWAY_TARGET], *CASH, account("card", "debt", 100, rate_pct=20.0)), Profile(),
                      NOW)
    r = v.runway
    # 2,000 out over 25 days (1 to 25 Sep, inclusive) -> 2,435.00 a month; 10,000 of cash lasts 4.1 months
    assert (r.days, r.since, r.monthly_out, r.months) == (25, dt.date(2026, 9, 1), 2435.0, 4.1)
    assert (r.aim, r.low, r.high) == (6.0, 4.0, 8.0)
    assert v.summary == ("$9,900.00 in cash after debts. At the pace money has left your cash these 25 days, it would "
                         "last about 4.1 months.")


def test_runway_is_none_without_rows_a_short_window_or_any_money_out():
    assert reserves_view(with_rows([], (), *CASH), Profile(), NOW).runway is None
    short = [row("checking", "2026-09-20", -100), row("checking", "2026-09-25", -100)]  # six days: too short to say
    assert reserves_view(with_rows(short, (), *CASH), Profile(), NOW).runway is None
    inflow = [row("checking", "2026-08-01", 100), row("checking", "2026-09-25", 100)]
    assert reserves_view(with_rows(inflow, (), *CASH), Profile(), NOW).runway is None
    v = reserves_view(with_rows(ROWS, (), *CASH), Profile(), NOW)
    assert (v.runway.aim, v.runway.low, v.runway.high) == (None, None, None)  # no runway target: no band
    assert reserves_view(with_rows([], (), *CASH), Profile(), NOW).summary == "$10,000.00 in cash after debts."


def test_flows_count_each_month_in_and_out_over_the_cash_accounts_only():
    rows = [row("checking", "2026-08-05", 2000), row("checking", "2026-08-20", -700), row("savings", "2026-08-20", 150),
            row("checking", "2026-09-10", 2000), row("checking", "2026-09-12", -300), row("card", "2026-09-12", -80)]
    v = reserves_view(with_rows(rows, (), *CASH, account("card", "debt", 100)), Profile(), NOW)
    assert [(f.month, f.money_in, f.money_out) for f in v.flows] == [("2026-08", 2150.0, 700.0),
                                                                        ("2026-09", 2000.0, 300.0)]


def test_cash_shares_and_a_debts_yearly_cost():
    v = reserves_view(snap(*CASH, account("card", "debt", 500, rate_pct=20.0, limit=2000),
                           account("loan", "debt", 1000), account("paid", "debt", -50, rate_pct=20.0)), Profile(), NOW)
    assert [(c.id, c.share_pct) for c in v.cash] == [("savings", 70.0), ("checking", 30.0)]
    assert {d.id: d.yearly_cost for d in v.debts} == {"card": 100.0, "loan": None, "paid": None}


def test_the_demo_has_a_runway_with_its_band_and_three_months_of_flows(demo_reserves):
    r = demo_reserves.runway
    assert r is not None and r.months > 0 and r.days >= 80
    assert (r.aim, r.low, r.high) == (6.0, 4.0, None)  # the demo's Cash runway target has no high end
    assert len(demo_reserves.flows) >= 3
    assert all(f.money_in >= 0 and f.money_out >= 0 for f in demo_reserves.flows)
    assert demo_reserves.summary.startswith(
        "$30,255.98 in cash after debts. At the pace money has left your cash these")

