import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Account, Snapshot
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
    assert v.spread.gap == pytest.approx(v.spread.yearly_earned - v.spread.yearly_cost)


def test_no_cash_or_debt_is_an_empty_view():
    v = reserves_view(snap(account("brokerage", "long_term", 1000.0)), Profile(), NOW)
    assert v.cash == [] and v.debts == [] and v.spread is None
    assert (v.totals.cash, v.totals.owed, v.totals.net, v.totals.utilization_pct) == (0.0, 0.0, 0.0, None)


def test_cash_and_debts_are_largest_first(demo_reserves):
    assert [c.value for c in demo_reserves.cash] == sorted((c.value for c in demo_reserves.cash), reverse=True)
    assert demo_reserves.debts[0].id == "card"


def test_demo_spread_sentence_figures(demo_reserves):
    assert demo_reserves.spread.owed_rate_pct == 24.9 and demo_reserves.spread.earned_rate_pct == 4.1
