import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Account, Goal, Holding, Series, Snapshot, Target, Thesis, ValuePoint
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.plan import plan_view, target_attention, thesis_attention, thesis_rows

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
TODAY = dt.date(2026, 9, 25)
d = dt.date


def account(id_, value, category="long_term"):
    return Account(id=id_, name=id_.title(), category=category, value=value, as_of=NOW)


def holding(account_id, symbol, value):
    return Holding(account_id=account_id, symbol=symbol, name=symbol, quantity=1, price=value, value=value)


def snap(accounts=(), holdings=(), targets=(), theses=(), goals=(), account_history=()):
    return Snapshot(generated_at=NOW, accounts=list(accounts), holdings=list(holdings), targets=list(targets),
                    theses=list(theses), goals=list(goals), account_history=list(account_history))


@pytest.fixture(scope="module")
def demo_plan():
    return plan_view(collect(DEMO_PROFILE, NOW), DEMO_PROFILE, NOW)


def test_percent_actual_from_holdings():
    t = Target(id="t", account_id="a", label="SPY", symbols=["SPY"], target=60, low=55, high=65)
    s = snap(accounts=[account("a", 1000)], holdings=[holding("a", "SPY", 600)], targets=[t])
    row = plan_view(s, Profile(), NOW).accounts[0].rows[0]
    assert row.actual == 60.0 and row.status == "on" and row.gap == 0.0 and row.gap_text == "on plan"


def test_sleeve_sums_its_symbols():
    t = Target(id="t", account_id="a", label="Two", symbols=["A", "B"], low=15, high=25)
    s = snap(accounts=[account("a", 1000)],
             holdings=[holding("a", "A", 100), holding("a", "B", 100), holding("a", "C", 400)], targets=[t])
    row = plan_view(s, Profile(), NOW).accounts[0].rows[0]
    assert row.actual == 20.0 and row.status == "on"


def test_zero_value_account_is_unknown():
    t = Target(id="t", account_id="a", label="SPY", symbols=["SPY"], target=60, low=55, high=65)
    s = snap(accounts=[account("a", 0)], targets=[t])
    v = plan_view(s, Profile(), NOW)
    assert v.unscoped == []  # the account is known, so the row still lives under it, not in unscoped
    row = v.accounts[0].rows[0]
    assert row.actual is None and row.status == "unknown" and row.gap is None and row.gap_text == ""


def test_ratio_target_uses_feed_actual():
    t = Target(id="cover", label="Cash cover", unit="x", target=6, low=4, actual=7.5)
    s = snap(targets=[t])
    row = plan_view(s, Profile(), NOW).unscoped[0]
    assert row.unit == "x" and row.actual == 7.5 and row.status == "on"


def test_status_and_gap_money():
    t = Target(id="t", account_id="a", label="SPY", symbols=["SPY"], target=60, low=55, high=65)
    s = snap(accounts=[account("a", 1000)], holdings=[holding("a", "SPY", 500)], targets=[t])  # 50%: under the low end
    row = plan_view(s, Profile(), NOW).accounts[0].rows[0]
    assert row.status == "under" and row.gap == pytest.approx(50.0) and row.gap_text == "under the low end"
    # over: 700 of 1000 is 70%, above the 65 high end
    over = snap(accounts=[account("a", 1000)], holdings=[holding("a", "SPY", 700)], targets=[t])
    over_row = plan_view(over, Profile(), NOW).accounts[0].rows[0]
    assert over_row.status == "over" and over_row.gap == pytest.approx(-50.0)
    assert over_row.gap_text == "over the high end"


def test_unscoped_percent_target_gap_is_percentage_points_only():
    # an unscoped target with a feed-sent actual: kestrel has no account value to turn the gap into money
    t = Target(id="t", label="Whole book", symbols=["SPY"], target=60, low=55, high=65, actual=40)
    row = plan_view(snap(targets=[t]), Profile(), NOW).unscoped[0]
    assert row.status == "under" and row.gap == pytest.approx(15.0)  # points, not dollars


def test_off_plan_first():
    a = account("a", 1000)
    on = Target(id="on", account_id="a", label="B", symbols=["X"], target=10, low=5, high=15)  # 10%: on plan
    under = Target(id="under", account_id="a", label="A", symbols=["Y"], target=50, low=45, high=55)  # 10%: under
    s = snap(accounts=[a], holdings=[holding("a", "X", 100), holding("a", "Y", 100)], targets=[on, under])
    rows = plan_view(s, Profile(), NOW).accounts[0].rows
    # "A" sorts before "B" by label, but off-plan rows come first regardless of label
    assert [r.id for r in rows] == ["under", "on"]


def test_goal_progress_and_monthly_needed():
    g = Goal(id="g", label="Trip", target=2000, account_id="a", by=d(2027, 7, 25))
    s = snap(accounts=[account("a", 1000)], goals=[g])
    row = plan_view(s, Profile(), NOW).goals[0]
    assert row.current == 1000.0 and row.months_left == 10 and row.monthly_needed == pytest.approx(100.0)
    assert row.reached is False and row.progress_pct == 50.0


def test_goal_reached_caps_progress():
    g = Goal(id="g", label="Trip", target=500, account_id="a", by=d(2027, 1, 1))
    s = snap(accounts=[account("a", 1000)], goals=[g])
    row = plan_view(s, Profile(), NOW).goals[0]
    assert row.progress_pct == 100.0 and row.reached is True and row.monthly_needed is None


def test_goal_account_ids_sums_scoped_accounts():
    g = Goal(id="g", label="Two accounts", target=1000, account_ids=["a", "b"])
    s = snap(accounts=[account("a", 300), account("b", 400), account("c", 999)], goals=[g])
    row = plan_view(s, Profile(), NOW).goals[0]
    assert row.current == 700.0 and "A" in row.scope_text and "B" in row.scope_text


def test_goal_deposits_measure_sums_net_flow_since_year_start():
    points = [ValuePoint(date=d(2026, 1, 5), value=1100, net_flow=100),
             ValuePoint(date=d(2026, 6, 1), value=1300, net_flow=200),
             ValuePoint(date=TODAY, value=1300, net_flow=0)]
    g = Goal(id="g", label="This year's deposits", target=1000, account_id="a", measure="deposits")
    s = snap(accounts=[account("a", 1300)], goals=[g], account_history=[Series(id="a", points=points)])
    row = plan_view(s, Profile(), NOW).goals[0]
    assert row.current == 300.0 and row.progress_pct == 30.0


def test_goal_deposits_measure_uses_the_by_dates_year():
    # an overdue goal: its window starts on 1 January of `by`'s year, not this year, so a deposit made back then
    # still counts toward it today
    points = [ValuePoint(date=d(2024, 12, 1), value=100, net_flow=100),  # before the goal's year: excluded
             ValuePoint(date=d(2025, 3, 1), value=250, net_flow=150),   # the goal's (past) year: counted
             ValuePoint(date=TODAY, value=400, net_flow=150)]           # this year, through now: also counted
    g = Goal(id="g", label="Overdue", target=1000, account_id="a", measure="deposits", by=d(2025, 6, 30))
    s = snap(accounts=[account("a", 400)], goals=[g], account_history=[Series(id="a", points=points)])
    row = plan_view(s, Profile(), NOW).goals[0]
    assert row.current == 300.0


def test_theses_sorted_by_health_and_held_flag():
    theses = [
        Thesis(symbol="A", health="ok"),
        Thesis(symbol="B", health="alert"),
        Thesis(symbol="C", health="watch", account_ids=["h"]),
        Thesis(symbol="D", health="watch"),
    ]
    s = snap(accounts=[account("h", 100)], holdings=[holding("h", "C", 50)], theses=theses)
    rows = thesis_rows(s, TODAY)
    # alert first, then watch (held before not-held, since C is held and D isn't), then ok
    assert [r.symbol for r in rows] == ["B", "C", "D", "A"]
    assert rows[1].held is True and rows[1].held_value == 50.0 and rows[2].held is False


def test_no_source_is_empty():
    v = plan_view(snap(), Profile(), NOW)
    assert v.accounts == [] and v.unscoped == [] and v.theses == [] and v.goals == []
    assert v.counts.off_plan == 0 and v.counts.theses_alert == 0 and v.counts.theses_watch == 0


def test_attention_lists_off_plan_targets_and_alert_theses():
    t_over = Target(id="over", account_id="a", label="SPY", symbols=["SPY"], target=60, low=55, high=65)
    s = snap(accounts=[account("a", 1000)], holdings=[holding("a", "SPY", 900)], targets=[t_over],
            theses=[Thesis(symbol="X", health="alert", reasons=["margins fell"]),
                    Thesis(symbol="Y", health="watch", reasons=["volume soft"]), Thesis(symbol="Z", health="ok")])
    targets = target_attention(s)
    assert len(targets) == 1
    assert targets[0].level == "warning" and targets[0].title == "SPY is over plan in A" and targets[0].link == "/plan"
    theses = thesis_attention(s)
    assert [(i.level, i.title, i.detail) for i in theses] == [
        ("warning", "X: thesis needs a look", "margins fell"), ("note", "Y: thesis needs a look", "volume soft")]


def test_demo_plan_matches_demo_home_off_plan_targets(demo_plan):
    off_plan_ids = {r.id for a in demo_plan.accounts for r in a.rows if r.status in ("over", "under")}
    off_plan_ids |= {r.id for r in demo_plan.unscoped if r.status in ("over", "under")}
    assert demo_plan.counts.off_plan == len(off_plan_ids) == 2
    assert demo_plan.counts.theses_alert == 1 and demo_plan.counts.theses_watch == 1
