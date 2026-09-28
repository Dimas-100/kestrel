import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Account, Goal, Holding, Series, Snapshot, Target, Thesis, ValuePoint
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.plan import _months_between, plan_view, target_attention, thesis_attention, thesis_rows

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
    assert row.gap_unit == "money"


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
    assert row.gap_unit is None


def test_negative_value_account_is_unknown():
    # a debit bigger than what is held (or any other reason a value could be negative): still not a real percentage
    t = Target(id="t", account_id="a", label="SPY", symbols=["SPY"], target=60, low=55, high=65)
    s = snap(accounts=[account("a", -500)], holdings=[holding("a", "SPY", 100)], targets=[t])
    row = plan_view(s, Profile(), NOW).accounts[0].rows[0]
    assert row.actual is None and row.status == "unknown" and row.gap_unit is None


def test_no_holdings_at_all_for_the_account_is_unknown_not_a_fake_zero_percent():
    # the account has a positive value but the snapshot has never reported ANY holding for it (a brand-new link,
    # or a source that only sends account totals) — 0% would claim knowledge kestrel doesn't have
    t = Target(id="t", account_id="a", label="SPY", symbols=["SPY"], target=60, low=55, high=65)
    s = snap(accounts=[account("a", 10437.29)], targets=[t])
    row = plan_view(s, Profile(), NOW).accounts[0].rows[0]
    assert row.actual is None and row.status == "unknown" and row.gap is None and row.gap_unit is None


def test_a_percent_target_with_no_symbols_and_no_actual_is_unknown_not_a_fake_zero_percent():
    # "Growth core" names nothing to sum and the feed sent no actual: there is no share to show, and no gap, and
    # nothing for Home's Needs you — not 0% "under the low end"
    t = Target(id="core", account_id="a", label="Growth core", symbols=[], low=50, high=70)
    s = snap(accounts=[account("a", 10437.29)], holdings=[holding("a", "VTI", 4218.66)], targets=[t])
    plan = plan_view(s, Profile(), NOW)
    row = plan.accounts[0].rows[0]
    assert (row.actual, row.status, row.gap, row.gap_unit, row.gap_text) == (None, "unknown", None, None, "")
    assert plan.counts.off_plan == 0 and target_attention(s) == []
    # the same target with the feed's own measure is judged as usual
    measured = t.model_copy(update={"actual": 44.6})
    row = plan_view(snap(accounts=[account("a", 10437.29)], targets=[measured]), Profile(), NOW).accounts[0].rows[0]
    assert (row.actual, row.status) == (44.6, "under")


def test_ratio_target_uses_feed_actual():
    t = Target(id="cover", label="Cash cover", unit="x", target=6, low=4, actual=7.5)
    s = snap(targets=[t])
    row = plan_view(s, Profile(), NOW).unscoped[0]
    assert row.unit == "x" and row.actual == 7.5 and row.status == "on" and row.gap_unit == "x"


def test_ratio_target_off_plan_gap_is_in_ratio_units():
    t = Target(id="cover", label="Cash cover", unit="x", target=6, low=4, actual=2.5)
    row = plan_view(snap(targets=[t]), Profile(), NOW).unscoped[0]
    assert row.status == "under" and row.gap == pytest.approx(1.5) and row.gap_unit == "x"


def test_status_and_gap_money():
    t = Target(id="t", account_id="a", label="SPY", symbols=["SPY"], target=60, low=55, high=65)
    s = snap(accounts=[account("a", 1000)], holdings=[holding("a", "SPY", 500)], targets=[t])  # 50%: under the low end
    row = plan_view(s, Profile(), NOW).accounts[0].rows[0]
    assert row.status == "under" and row.gap == pytest.approx(50.0) and row.gap_text == "under the low end"
    assert row.gap_unit == "money"
    # over: 700 of 1000 is 70%, above the 65 high end
    over = snap(accounts=[account("a", 1000)], holdings=[holding("a", "SPY", 700)], targets=[t])
    over_row = plan_view(over, Profile(), NOW).accounts[0].rows[0]
    assert over_row.status == "over" and over_row.gap == pytest.approx(-50.0)
    assert over_row.gap_text == "over the high end" and over_row.gap_unit == "money"


def test_gap_uses_the_exact_held_sum_not_a_rounded_percentage():
    # 10,862.49 of 67,890.81 is 15.99994...%: rounding that to 16.0 *before* computing the gap against low=18
    # gives 1,357.82; the correct gap, from the exact ratio, is 1,357.86
    t = Target(id="t", account_id="a", label="XLP", symbols=["XLP"], target=20, low=18, high=22)
    s = snap(accounts=[account("a", 67890.81)], holdings=[holding("a", "XLP", 10862.49)], targets=[t])
    row = plan_view(s, Profile(), NOW).accounts[0].rows[0]
    assert row.actual == 16.0  # rounded for display only
    assert row.status == "under"
    assert row.gap == pytest.approx(1357.86)  # NOT 1357.82


def test_a_percentage_just_under_the_edge_is_not_rounded_onto_the_band():
    # 549,960 of 1,000,000 is 54.996%: it rounds to 55.0 for display, exactly the low end, but it is truly
    # under it — the status (and the gap) must be decided before any rounding, or this reads as "on plan"
    t = Target(id="t", account_id="b", label="SPY", symbols=["SPY"], target=60, low=55, high=65)
    s = snap(accounts=[account("b", 1_000_000)], holdings=[holding("b", "SPY", 549960)], targets=[t])
    row = plan_view(s, Profile(), NOW).accounts[0].rows[0]
    assert row.actual == 55.0
    assert row.status == "under"
    assert row.gap == pytest.approx(40.0)


def test_holdings_exactly_at_the_band_edge_is_on_plan_not_a_float_glitch():
    # 570 of 1,000 is exactly 57%: computed as a float, 570 / 1000 * 100 can land on 56.99999999999999, which is
    # strictly < 57 — a raw comparison would misfire "under" (or, at a high edge, "over") for a value that landed
    # exactly on the line. The decision must be immune to that: both a low-edge and a high-edge target at the same
    # value must read "on", with a $0.00 gap.
    low_t = Target(id="lo", account_id="a", label="X", symbols=["X"], low=57, high=None)
    high_t = Target(id="hi", account_id="a", label="X", symbols=["X"], low=None, high=57)
    s = snap(accounts=[account("a", 1000)], holdings=[holding("a", "X", 570)], targets=[low_t, high_t])
    rows = {r.id: r for r in plan_view(s, Profile(), NOW).accounts[0].rows}
    assert rows["lo"].status == "on" and rows["lo"].gap == 0.0
    assert rows["hi"].status == "on" and rows["hi"].gap == 0.0


def test_a_wide_sweep_of_exact_band_edges_never_misfires_off_plan():
    # the reviewer's own sweep: every (value, edge) pair where held lands exactly on the edge, at cent precision,
    # over a range of edges and account sizes, must read "on" — this is the regression test for the 51 false
    # off-plan rows the float-equality bug produced
    false_off = []
    for value in (1000, 2000, 10000, 5000, 1234.5, 100):
        for edge in range(1, 100):
            held = round(edge * value / 100, 2)
            if abs(held - edge * value / 100) > 1e-9:
                continue  # a cent-rounding case, not an exact edge — out of scope for this sweep
            for t in (Target(id="lo", account_id="a", label="X", symbols=["X"], low=edge, high=None),
                     Target(id="hi", account_id="a", label="X", symbols=["X"], low=None, high=edge)):
                s = snap(accounts=[account("a", value)], holdings=[holding("a", "X", held)], targets=[t])
                row = plan_view(s, Profile(), NOW).accounts[0].rows[0]
                if row.status != "on":
                    false_off.append((value, edge, held, row.status, row.gap))
    assert false_off == []


def test_unscoped_percent_target_gap_is_percentage_points_only():
    # an unscoped target with a feed-sent actual: kestrel has no account value to turn the gap into money
    t = Target(id="t", label="Whole book", symbols=["SPY"], target=60, low=55, high=65, actual=40)
    row = plan_view(snap(targets=[t]), Profile(), NOW).unscoped[0]
    assert row.status == "under" and row.gap == pytest.approx(15.0) and row.gap_unit == "pts"  # points, not dollars


def test_zero_value_known_account_with_feed_actual_reports_points_not_money():
    # the bug this guards: a known account (it exists, just with a 0 value) grouped under `accounts[]` must not
    # let the UI infer "money" from that grouping alone — kestrel still can't turn points into dollars with a
    # zero denominator, so this must carry gap_unit "pts", not "money" (which rendered as a bogus "$55.00")
    t = Target(id="t3", account_id="z", label="VTI", symbols=["VTI"], target=60, low=55, high=65, actual=0)
    v = plan_view(snap(accounts=[account("z", 0)], targets=[t]), Profile(), NOW)
    row = v.accounts[0].rows[0]
    assert row.status == "under" and row.gap == pytest.approx(55.0) and row.gap_unit == "pts"


def test_dangling_account_id_groups_under_its_own_id_not_across_every_account():
    # a source never sent this account at all: the row must not fall into "unscoped" (which means "for every
    # account", by design) — it stays grouped by the id it names, marked as not a known account
    t = Target(id="t2", account_id="gone", label="VTI", symbols=["VTI"], target=60, low=55, high=65, actual=40)
    v = plan_view(snap(accounts=[account("a", 10000)], targets=[t]), Profile(), NOW)
    assert v.unscoped == []
    group = next(g for g in v.accounts if g.account_id == "gone")
    assert group.known is False and group.name == "gone"
    row = group.rows[0]
    assert row.status == "under" and row.gap == pytest.approx(15.0) and row.gap_unit == "pts"


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


def test_goal_missing_account_id_reports_unknown_not_a_fake_zero():
    g = Goal(id="g", label="Grow", target=100000, account_id="gone", by=d(2030, 12, 31))
    row = plan_view(snap(accounts=[account("a", 5000)], goals=[g]), Profile(), NOW).goals[0]
    assert row.current is None and row.progress_pct is None and row.monthly_needed is None
    assert row.missing_accounts == ["gone"]


def test_goal_missing_one_of_several_account_ids_reports_unknown():
    g = Goal(id="g", label="Two", target=10000, account_ids=["a", "gone"])
    row = plan_view(snap(accounts=[account("a", 5000)], goals=[g]), Profile(), NOW).goals[0]
    assert row.current is None and row.missing_accounts == ["gone"]


def test_goal_account_ids_signed_sum_a_debt_account_reduces_it():
    # 5,000 owned less 2,000 owed: the debt account never adds to the goal's progress
    g = Goal(id="g3", label="Two", target=10000, account_ids=["a", "card"])
    s = snap(accounts=[account("a", 5000), account("card", 2000, "debt")], goals=[g])
    row = plan_view(s, Profile(), NOW).goals[0]
    assert row.current == 3000.0


def test_goal_category_debt_current_is_negative_owed():
    g2 = Goal(id="g2", label="Card paid off", target=0, category="debt", by=d(2027, 6, 30))
    s = snap(accounts=[account("a", 5000), account("card", 2000, "debt")], goals=[g2])
    row = plan_view(s, Profile(), NOW).goals[0]
    assert row.current == -2000.0 and row.reached is False  # still owes 2,000: not paid off yet


def test_goal_single_account_id_on_a_debt_account_is_signed():
    g = Goal(id="g", label="Pay off the card", target=0, account_id="card")
    row = plan_view(snap(accounts=[account("card", 2000, "debt")], goals=[g]), Profile(), NOW).goals[0]
    assert row.current == -2000.0


def test_reached_goal_with_a_zero_target_shows_full_progress():
    # a debt payoff goal (target 0) that has been reached (the card is at 0) must show 100% progress, not 0% —
    # the target<=0 guard that avoids a division by zero must not also override an already-reached goal
    g = Goal(id="g6", label="Card paid off", target=0, category="debt")
    row = plan_view(snap(accounts=[account("card", 0.0, "debt")], goals=[g]), Profile(), NOW).goals[0]
    assert row.reached is True and row.progress_pct == 100.0


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


def test_deposits_goal_with_a_future_window_counts_months_from_the_window_start():
    # the goal's tracking year (2027) hasn't started: "months left" and the monthly pace must count from 1 Jan
    # 2027, not from today (2026-09-25) — that would give 15 months and $120/month instead of 12 and $150
    pts = [ValuePoint(date=d(2026, m, 1), value=1000, net_flow=150) for m in range(1, 10)]
    g = Goal(id="g", label="Save next year", target=1800, account_id="s", measure="deposits", by=d(2027, 12, 31))
    s = snap(accounts=[account("s", 1000, "cash")], goals=[g], account_history=[Series(id="s", points=pts)])
    row = plan_view(s, Profile(), NOW).goals[0]
    assert row.current == 0.0  # nothing counts yet: the tracking window opens 1 Jan 2027
    assert row.months_left == 12
    assert row.monthly_needed == pytest.approx(150.0)


def test_overdue_goal_not_reached_has_no_months_left_or_monthly_needed():
    g = Goal(id="g4", label="Overdue", target=10000, account_id="a", by=d(2025, 6, 30))
    row = plan_view(snap(accounts=[account("a", 5000)], goals=[g]), Profile(), NOW).goals[0]
    assert row.months_left is None and row.monthly_needed is None and row.reached is False


def test_months_between_is_monotonic_across_a_month_boundary():
    # the reviewer's own repro: with `by` fixed at 2027-06-15, walking `start` across 2026-09-29 -> 09-30 -> 10-01
    # -> 10-02 must never go up then back down (8, 8, 9, 8 was the bug — the 1st of a month got a free "+1" bonus
    # that the 2nd did not, even though less time had passed by the 2nd)
    by = d(2027, 6, 15)
    days = [d(2026, 9, 29), d(2026, 9, 30), d(2026, 10, 1), d(2026, 10, 2)]
    assert [_months_between(day, by) for day in days] == [8, 8, 8, 8]


def test_months_between_never_increases_as_the_start_date_advances():
    # a broader sweep across several month boundaries (including a short February and a year boundary), one day at
    # a time: months_left must be non-increasing as "today" moves forward, whatever `by` is
    for by in (d(2027, 6, 15), d(2027, 2, 28), d(2030, 12, 31), d(2027, 6, 30)):
        start = d(2026, 9, 20)
        previous = _months_between(start, by)
        for _ in range(45):  # walks well past a month boundary either way
            start += dt.timedelta(days=1)
            current = _months_between(start, by)
            assert current <= previous, (by, start, previous, current)
            previous = current


def test_months_between_still_counts_a_full_calendar_year_as_twelve():
    # 1 January to 31 December of the same year: the monotonic rule must still give 12, not 11
    assert _months_between(d(2027, 1, 1), d(2027, 12, 31)) == 12


def test_months_between_is_none_when_by_is_the_last_representable_date():
    # date.max (9999-12-31), a common "no real deadline" placeholder: `by + 1 day` would overflow
    assert _months_between(TODAY, d(9999, 12, 31)) is None


def test_a_goal_with_by_at_the_date_ceiling_keeps_progress_but_has_no_monthly_pace():
    # the bug this guards: /api/plan crashed (OverflowError) on a goal whose `by` is 9999-12-31
    g = Goal(id="g5", label="Someday", target=2000, account_id="a", by=d(9999, 12, 31))
    row = plan_view(snap(accounts=[account("a", 1000)], goals=[g]), Profile(), NOW).goals[0]
    assert row.current == 1000.0 and row.progress_pct == 50.0 and row.reached is False
    assert row.months_left is None and row.monthly_needed is None


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


def test_thesis_held_in_names_the_accounts_it_is_actually_held_in_not_the_declared_ones():
    # the feed's own account_ids can go stale (a holding moved, the thesis wasn't updated); "held in" must reflect
    # reality
    thesis = Thesis(symbol="X", health="ok", account_ids=["declared"])
    s = snap(accounts=[account("declared", 100), account("real", 200)], holdings=[holding("real", "X", 50)],
            theses=[thesis])
    row = thesis_rows(s, TODAY)[0]
    assert row.held is True and row.account_names == ["Real"]


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
    assert [(i.level, i.title, i.detail, i.link) for i in theses] == [
        ("warning", "X: thesis needs a look", "margins fell", "/plan"),
        ("note", "Y: thesis needs a look", "volume soft", "/plan")]


def test_target_attention_names_the_account_id_when_no_source_sent_it():
    t = Target(id="t2", account_id="gone", label="VTI", symbols=["VTI"], target=60, low=55, high=65, actual=40)
    items = target_attention(snap(targets=[t]))
    assert items[0].title == "VTI is under plan in gone"


def test_demo_plan_matches_demo_home_off_plan_targets(demo_plan):
    off_plan_ids = {r.id for a in demo_plan.accounts for r in a.rows if r.status in ("over", "under")}
    off_plan_ids |= {r.id for r in demo_plan.unscoped if r.status in ("over", "under")}
    assert demo_plan.counts.off_plan == len(off_plan_ids) == 2
    assert demo_plan.counts.theses_alert == 1 and demo_plan.counts.theses_watch == 1
    # cross-check against Home's own Needs-you list, not just this view's internal count: the two must never
    # disagree, since Home computes its plan-related items from these same functions
    from kestrel.views.home import home_view

    snapshot = collect(DEMO_PROFILE, NOW)
    demo_home = home_view(snapshot, DEMO_PROFILE, NOW)
    plan_titles = {i.title for i in target_attention(snapshot)} | {i.title for i in thesis_attention(snapshot)}
    home_titles = {a.title for a in demo_home.attention}
    assert plan_titles and plan_titles <= home_titles
