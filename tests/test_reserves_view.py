import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Account, Snapshot, Target, Transaction
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.reserves import moves_of, reserves_view

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
    assert v.summary == ("$9,900.00 in cash after recorded debts. Leaving aside moves between your own accounts, money "
                         "has left your cash at about $80.00 a day these 25 days: it would last about 4.1 months.")


def test_runway_is_none_without_rows_a_short_window_or_any_money_out():
    assert reserves_view(with_rows([], (), *CASH), Profile(), NOW).runway is None
    short = [row("checking", "2026-09-20", -100), row("checking", "2026-09-25", -100)]  # six days: too short to say
    assert reserves_view(with_rows(short, (), *CASH), Profile(), NOW).runway is None
    inflow = [row("checking", "2026-08-01", 100), row("checking", "2026-09-25", 100)]
    assert reserves_view(with_rows(inflow, (), *CASH), Profile(), NOW).runway is None
    v = reserves_view(with_rows(ROWS, (), *CASH), Profile(), NOW)
    assert (v.runway.aim, v.runway.low, v.runway.high) == (None, None, None)  # no runway target: no band
    assert reserves_view(with_rows([], (), *CASH), Profile(), NOW).summary == "$10,000.00 in cash after recorded debts."


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
        "$30,255.98 in cash after recorded debts. Leaving aside moves between your own accounts, money has left your "
        "cash at about $")


# ------------------------------------------------- estimates with their definitions (2026-10-08 reserves estimates)

def test_a_move_between_your_own_cash_accounts_is_left_out_of_the_pace_and_the_flows():
    rows = [row("checking", "2026-09-01", -1000), row("checking", "2026-09-25", -500),
            # checking -> savings the same day, and savings -> checking two days apart: total cash never moved
            row("checking", "2026-09-10", -400, "Withdrawal to Rainy Day Fund"),
            row("savings", "2026-09-10", 400, "Deposit from Checking"),
            row("savings", "2026-09-14", -250, "Online transfer to CHK 1234"),
            row("checking", "2026-09-16", 250, "Online transfer from SAV 5678")]
    v = reserves_view(with_rows(rows, (), *CASH), Profile(), NOW)
    r = v.runway
    # only the 1,500 that left for good counts: 60.00 a day over 25 days; 10,000 / 60 = 166 days -> months
    assert (r.days, r.daily_out, r.moved, r.moved_count) == (25, 60.0, 650.0, 2)
    assert (r.unit, r.months) == ("months", 5.5)
    sep = v.flows[-1]
    assert (sep.money_in, sep.money_out, sep.moved, sep.net) == (0.0, 1500.0, 650.0, -1500.0)


def test_a_move_needs_two_cash_accounts_the_same_amount_and_at_most_three_days():
    card = account("card", "debt", 100, rate_pct=20.0)
    t = "Online transfer"
    rows = [row("checking", "2026-09-01", -100), row("checking", "2026-09-25", -100),
            row("checking", "2026-09-05", -300, t), row("card", "2026-09-05", 300, t),  # a card payment left the cash
            row("checking", "2026-09-08", -200, t), row("savings", "2026-09-12", 200, t),  # four days apart
            row("checking", "2026-09-15", -75, t), row("savings", "2026-09-15", 75.01, t),  # a cent apart
            row("checking", "2026-09-18", -40, t), row("checking", "2026-09-18", 40, t),  # the same account
            # the same amount the same day, but a brokerage on one side and an account not on file on the other
            row("checking", "2026-09-21", -150, "BROKERAGE SVC LLC"),
            row("savings", "2026-09-21", 150, f"{t} from CHK 0001")]
    r = reserves_view(with_rows(rows, (), *CASH, card), Profile(), NOW).runway
    assert (r.moved, r.moved_count) == (0.0, 0)
    assert r.monthly_out == round((100 + 100 + 300 + 200 + 75 + 40 + 150) / 25 * 30.4375, 2)


def test_a_payment_to_yourself_pairs_with_the_deposit_that_names_you():
    rows = [row("checking", "2026-09-01", -100), row("checking", "2026-09-25", -100),
            Transaction(account_id="checking", date=dt.date(2026, 9, 12), amount=-190.0,
                        description="Zelle payment to Alex Rivera Conf# abc123"),
            Transaction(account_id="savings", date=dt.date(2026, 9, 12), amount=190.0, description="ALEX RIVERA",
                        counterparty="Alex Rivera"),
            # a category the feed gives is enough on both sides
            Transaction(account_id="savings", date=dt.date(2026, 9, 20), amount=-60.0, description="SAV 12",
                        category="Transfer"),
            Transaction(account_id="checking", date=dt.date(2026, 9, 21), amount=60.0, description="CHK 34",
                        category="transfer")]
    r = reserves_view(with_rows(rows, (), *CASH), Profile(), NOW).runway
    assert (r.moved, r.moved_count) == (250.0, 2)


def test_each_row_is_in_at_most_one_move_closest_date_then_the_same_bank_first():
    t = "Online transfer"
    third = account("other", "cash", 500)
    rows = [row("checking", "2026-09-01", -10), row("checking", "2026-09-25", -10),
            row("checking", "2026-09-10", -300, t), row("savings", "2026-09-12", 300, t),
            row("other", "2026-09-10", 300, t)]
    v = reserves_view(with_rows(rows, (), *CASH, third), Profile(), NOW)
    assert (v.runway.moved, v.runway.moved_count) == (300.0, 1)
    # the same-day 300 into "other" is the pair; the 300 into savings two days later is money in
    assert v.flows[-1].money_in == 300.0
    # two same-day candidates: the account at the same bank wins
    banked = (account("checking", "cash", 3000, institution="Bank A"),
              account("savings", "cash", 7000, institution="Bank A"),
              account("other", "cash", 500, institution="Bank B"))
    rows = [row("checking", "2026-09-01", -10), row("checking", "2026-09-25", -10),
            row("checking", "2026-09-10", -300, t), row("other", "2026-09-10", 300, t),
            row("savings", "2026-09-10", 300, t)]
    snapshot = with_rows(rows, (), *banked)
    assert [(o, i) for o, i in moves_of(snapshot.transactions, snapshot.accounts)] == [(2, 4)]


def test_coverage_reads_in_whole_days_rounded_down_under_sixty_days():
    small = (account("checking", "cash", 845.0),)
    rows = [row("checking", "2026-09-01", -2000), row("checking", "2026-09-30", -2500)]  # 150.00 a day over 30 days
    v = reserves_view(with_rows(rows, (), *small), Profile(), dt.datetime(2026, 10, 1, 12, tzinfo=dt.timezone.utc))
    r = v.runway
    assert (r.daily_out, r.days_cover, r.unit) == (150.0, 5, "days")  # 845 / 150 = 5.63: never overstated
    assert v.summary == ("$845.00 in cash after recorded debts. Leaving aside moves between your own accounts, money "
                         "has left your cash at about $150.00 a day these 30 days: it would last about 5 days.")


def test_overdrawn_cash_covers_no_days_and_reads_as_debts_over_cash():
    rows = [row("checking", "2026-09-01", -1000), row("checking", "2026-09-25", -500)]
    v = reserves_view(with_rows(rows, (), account("checking", "cash", -20.0), account("card", "debt", 500.0)),
                      Profile(), NOW)
    assert (v.runway.days_cover, v.runway.months, v.runway.unit) == (0, 0.0, "days")
    assert v.summary.startswith("Recorded debts are $520.00 more than your cash. ")
    assert v.summary.endswith("it would not last a day.")


def test_partial_months_carry_the_days_they_cover():
    rows = [row("checking", "2026-07-10", -100), row("checking", "2026-08-15", 2000),
            row("checking", "2026-08-20", -700), row("checking", "2026-09-03", -300)]
    v = reserves_view(with_rows(rows, (), *CASH), Profile(), NOW)  # NOW is 25 Sep in the default zone too
    got = [(f.month, f.start, f.end, f.days, f.partial) for f in v.flows]
    assert got == [("2026-07", dt.date(2026, 7, 10), dt.date(2026, 7, 31), 22, True),
                   ("2026-08", dt.date(2026, 8, 1), dt.date(2026, 8, 31), 31, False),
                   ("2026-09", dt.date(2026, 9, 1), dt.date(2026, 9, 25), 25, True)]
    assert [f.net for f in v.flows] == [-100.0, 1300.0, -300.0]


def test_rates_on_record_cover_only_the_lines_that_carry_one():
    s = snap(account("store", "debt", 540.0, limit=1200.0, name="Store card"),
             account("charge", "debt", 310.5, name="Charge card"),
             account("visa", "debt", 260.0, rate_pct=22.0, limit=2000.0, name="Visa"),
             account("paid", "debt", -10.0, name="Paid card"),  # a credit balance owes nothing and needs no rate
             account("checking", "cash", 912.4), account("savings", "cash", 15.6, rate_pct=2.5))
    v = reserves_view(s, Profile(), NOW)
    rates = v.rates
    assert (rates.owed, rates.rated_owed, rates.rated_owed_pct) == (1110.5, 260.0, 23.41)
    assert rates.unrated == ["Store card", "Charge card"]  # largest balance first
    assert (rates.cash, rates.rated_cash) == (928.0, 15.6)
    assert (v.totals.debt_count, v.totals.limited_count, v.totals.cash_count) == (4, 2, 2)


def test_no_rates_block_without_anything_owed_or_any_cash():
    assert reserves_view(snap(account("brokerage", "long_term", 1000.0)), Profile(), NOW).rates is None
    paid = reserves_view(snap(account("card", "debt", 0.0, rate_pct=20.0)), Profile(), NOW).rates
    assert paid is not None and (paid.owed, paid.rated_owed_pct) == (0.0, None)


def test_balances_and_bank_rows_over_a_week_old_are_named():
    old = dt.datetime(2026, 9, 10, 12, tzinfo=dt.timezone.utc)
    s = Snapshot(generated_at=NOW, accounts=[
        account("checking", "cash", 3000),
        Account(id="manual", name="Manual savings", category="cash", value=500, as_of=old),
        Account(id="card", name="Card", category="debt", value=100, as_of=NOW - dt.timedelta(days=7))],
        transactions=[row("checking", "2026-08-01", -100), row("checking", "2026-09-15", -100)])
    v = reserves_view(s, Profile(), NOW)
    assert v.totals.stale == ["Manual savings"]  # seven days is still fresh; fifteen is not
    assert (v.totals.oldest_as_of, v.totals.newest_as_of) == (dt.date(2026, 9, 10), dt.date(2026, 9, 25))
    assert (v.runway.through, v.runway.stale) == (dt.date(2026, 9, 15), True)  # no bank rows for ten days
    assert v.today == dt.date(2026, 9, 25)


def test_the_demo_leaves_its_savings_transfers_out_and_ends_on_a_month_to_date(demo_reserves):
    r = demo_reserves.runway
    assert r.moved > 0 and r.moved_count >= 3  # Alex's monthly transfer into savings
    assert (r.stale, r.unit) == (False, "months")
    assert demo_reserves.flows[-1].partial and demo_reserves.flows[-1].end == dt.date(2026, 9, 25)
    assert demo_reserves.rates.rated_owed_pct == 100.0 and demo_reserves.totals.stale == []

