import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Account, Goal, Holding, Series, Snapshot, Target, Thesis, ValuePoint
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.plan import PacePoint, _months_between, plan_view, target_attention, thesis_attention, thesis_rows

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
    assert row.overdue is True


def test_overdue_is_the_views_own_answer_a_far_date_or_a_reached_goal_is_not_overdue():
    goals = [Goal(id="far", label="Someday", target=1_000_000, account_id="a", by=d(9999, 12, 31)),
             Goal(id="done", label="Done late", target=4000, account_id="a", by=d(2025, 6, 30)),
             Goal(id="open", label="No date", target=9000, account_id="a")]
    rows = plan_view(snap(accounts=[account("a", 5127.44)], goals=goals), Profile(), NOW).goals
    assert [(r.id, r.overdue) for r in rows] == [("far", False), ("done", False), ("open", False)]


def test_a_goal_says_what_it_measures():
    goals = [Goal(id="v", label="Grow", target=9000, account_id="a"),
             Goal(id="dep", label="Save", target=9000, account_id="a", measure="deposits")]
    history = [Series(id="a", points=[ValuePoint(date=d(2026, 2, 3), value=5127.44, net_flow=312.18)])]
    rows = plan_view(snap(accounts=[account("a", 5127.44)], goals=goals, account_history=history), Profile(),
                     NOW).goals
    assert [r.measure for r in rows] == ["value", "deposits"]


def test_a_deposits_goal_over_an_account_with_no_history_is_unknown_not_zero():
    # the checking account comes from a bank feed with no history: what was deposited there can't be known
    savings = [ValuePoint(date=d(2026, 2, 3), value=5127.44, net_flow=312.18)]
    accounts = [account("savings", 5127.44, "cash"), account("checking", 2211.09, "cash")]
    g = Goal(id="dep", label="Save this year", target=6000, category="cash", measure="deposits", by=d(2026, 12, 31))
    row = plan_view(snap(accounts=accounts, goals=[g], account_history=[Series(id="savings", points=savings)]),
                    Profile(), NOW).goals[0]
    assert (row.current, row.progress_pct, row.monthly_needed, row.reached) == (None, None, None, False)
    assert row.unknown_reason == "no deposit history for Checking"
    # with every account's history in, it is known again: 312.18 of 6,000
    known = plan_view(snap(accounts=accounts[:1], goals=[g], account_history=[Series(id="savings", points=savings)]),
                      Profile(), NOW).goals[0]
    assert (known.current, known.unknown_reason) == (312.18, "")


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
    assert demo_plan.counts.off_plan == len(off_plan_ids) == 4
    assert demo_plan.counts.theses_alert == 1 and demo_plan.counts.theses_watch == 1
    # cross-check against Home's own Needs-you list, not just this view's internal count: the two must never
    # disagree, since Home computes its plan-related items from these same functions
    from kestrel.views.home import home_view

    snapshot = collect(DEMO_PROFILE, NOW)
    demo_home = home_view(snapshot, DEMO_PROFILE, NOW)
    plan_titles = {i.title for i in target_attention(snapshot)} | {i.title for i in thesis_attention(snapshot)}
    home_titles = {a.title for a in demo_home.attention}
    assert plan_titles and plan_titles <= home_titles


# ---------------------------------------------------------------- the summary and this month's actions (2026-10-05)

def test_summary_names_the_next_goal_and_what_needs_a_look():
    a = account("a", 1000)
    under = Target(id="under", account_id="a", label="A", symbols=["Y"], target=50, low=45, high=55)  # 10%: under
    goals = [Goal(id="far", label="Far", target=100000, account_id="a", by=d(2040, 1, 1)),
             Goal(id="near", label="Trip", target=2000, account_id="a", by=d(2027, 7, 25)),
             Goal(id="done", label="Done", target=500, account_id="a", by=d(2027, 1, 1))]
    theses = [Thesis(symbol="HD", health="alert", reasons=["Sales fell"]), Thesis(symbol="KO", health="watch")]
    v = plan_view(snap(accounts=[a], holdings=[holding("a", "Y", 100)], targets=[under], goals=goals, theses=theses),
                  Profile(), NOW)
    assert v.summary == ("2 goals ahead. The next is Trip, 50% there, by 25 Jul 2027. 1 target is outside its band "
                         "and needs a trade. 2 theses need a look.")


def test_summary_when_everything_is_fine_or_undated():
    a = account("a", 1000)
    on = Target(id="on", account_id="a", label="B", symbols=["X"], target=10, low=5, high=15)  # 10%: on plan
    s = snap(accounts=[a], holdings=[holding("a", "X", 100)], targets=[on])
    assert plan_view(s, Profile(), NOW).summary == "No goals yet. Every target sits on plan."
    undated = Goal(id="floor", label="Floor", target=5000, account_id="a")
    s = snap(accounts=[a], holdings=[holding("a", "X", 100)], targets=[on], goals=[undated])
    assert plan_view(s, Profile(), NOW).summary == "1 goal ahead, none dated. Every target sits on plan."
    s = snap(accounts=[a], goals=[Goal(id="done", label="Done", target=500, account_id="a")])
    assert plan_view(s, Profile(), NOW).summary == "Every goal is reached."


def test_actions_say_what_to_do_this_month_warnings_first():
    a = account("a", 1000)  # named "A"
    under = Target(id="under", account_id="a", label="XLP", symbols=["Y"], target=20, low=18, high=22)  # 10%: $80 under
    over = Target(id="over", account_id="a", label="XLV", symbols=["X"], target=15, low=12, high=18)  # 20%: $20 over
    ratio = Target(id="ratio", label="Cash runway", unit="x", target=6, low=4, high=8, actual=3)  # 1.0x under
    goals = [Goal(id="late", label="Household", target=2000, account_id="a", by=d(2026, 1, 1)),  # overdue at 50%
             Goal(id="soon", label="Trip", target=2000, account_id="a", by=d(2027, 7, 25)),  # ten months: $100 a month
             Goal(id="far", label="Far", target=100000, account_id="a", by=d(2040, 1, 1)),  # nothing to do yet
             Goal(id="deposits", label="Savings this year", target=1200, account_id="a", measure="deposits",
                  by=d(2026, 12, 31))]
    theses = [Thesis(symbol="HD", health="alert", reasons=["Sales fell"]),
              Thesis(symbol="KO", health="watch", reasons=["Volume is soft"]), Thesis(symbol="PG", health="ok")]
    history = [Series(id="a", points=[ValuePoint(date=d(2026, 1, 15), value=700, net_flow=300),
                                      ValuePoint(date=TODAY, value=1000)])]
    s = snap(accounts=[a], holdings=[holding("a", "Y", 100), holding("a", "X", 200), holding("a", "Z", 700)],
             targets=[under, over, ratio], goals=goals, theses=theses, account_history=history)
    v = plan_view(s, Profile(), NOW)
    # ranked (spec 2026-10-08 §3): alert theses, overdue goals, trades by the size of the money gap; then the goal the
    # others sit inside, theses on watch, and last the goal already named inside another's action
    assert [(x.level, x.kind, x.title, x.detail, x.anchor) for x in v.actions] == [
        ("warning", "thesis", "Review HD: thesis on alert", "not held", "thesis-HD"),
        ("warning", "goal", "Household was due 1 Jan 2026", "$1,000.00 of $2,000.00", "goal-late"),
        ("warning", "target", "Add $80.00 to XLP in A", "10.0% held · aim 20.0% · band 18–22%", "target-under"),
        ("warning", "target", "Trim $20.00 from XLV in A", "20.0% held · aim 15.0% · band 12–18%", "target-over"),
        ("warning", "target", "Cash runway is 1.0x under its band", "3.0x actual · aim 6.0x · band 4–8x",
         "target-ratio"),
        ("note", "goal", "Put about $100.00 a month toward Trip", "to reach $2,000.00 by 25 Jul 2027 · 50% there",
         "goal-soon"),
        ("note", "thesis", "Look at KO: thesis on watch", "not held", "thesis-KO"),
        ("note", "goal", "Put about $300.00 a month in deposits toward Savings this year",
         "to reach $1,200.00 by 31 Dec 2026 · 25% there", "goal-deposits"),
    ]
    whys = [x.why for x in v.actions]
    assert whys[0] == "Sales fell." and whys[2] == "The plan brings it back with a trade."
    assert whys[5] == "Savings this year ($300.00 a month) is part of this, and alone covers it."
    assert whys[7] == "Counts toward Trip too: the two amounts overlap, they don't add up."


def test_a_points_gap_action_names_the_points_and_the_account():
    zero = account("z", 0)
    t = Target(id="t", account_id="z", label="VTI", symbols=["VTI"], target=60, low=55, high=65, actual=0)
    v = plan_view(snap(accounts=[zero], targets=[t]), Profile(), NOW)
    assert [(x.level, x.title) for x in v.actions] == [("warning", "VTI is 55.0 pts under its band in Z")]


def test_nothing_to_do_is_an_empty_list_and_the_demo_has_actions():
    a = account("a", 1000)
    on = Target(id="on", account_id="a", label="B", symbols=["X"], target=10, low=5, high=15)
    s = snap(accounts=[a], holdings=[holding("a", "X", 100)], targets=[on], theses=[Thesis(symbol="PG", health="ok")])
    assert plan_view(s, Profile(), NOW).actions == []


def test_the_demo_plan_has_a_summary_and_actions(demo_plan):
    assert demo_plan.summary.startswith(
        "6 goals ahead. The next is Save into savings this year, 75% there, by 31 Dec 2026. 4 targets are outside "
        "their bands; 2 need a trade.")
    assert [x.level for x in demo_plan.actions][:3] == ["warning", "warning", "warning"]
    assert any(t.startswith("Put about") for t in (x.title for x in demo_plan.actions))


# ---------------------------------------------------------------- the record of what was passed (2026-10-05 milestones)

def test_a_goal_knows_the_day_its_scope_first_met_the_target_and_a_deposits_goal_has_none():
    history = [Series(id="a", points=[ValuePoint(date=d(2026, 8, 1), value=400),
                                      ValuePoint(date=d(2026, 8, 15), value=520),
                                      ValuePoint(date=d(2026, 9, 1), value=480), ValuePoint(date=TODAY, value=600)])]
    goals = [Goal(id="g", label="Trip", target=500, account_id="a"),
             Goal(id="dep", label="Save", target=100, account_id="a", measure="deposits", by=d(2026, 12, 31)),
             Goal(id="far", label="Far", target=5000, account_id="a")]
    v = plan_view(snap(accounts=[account("a", 600)], goals=goals, account_history=history), Profile(), NOW)
    rows = {g.id: g for g in v.goals}
    assert (rows["g"].reached, rows["g"].reached_on) == (True, d(2026, 8, 15))  # the first day it met 500
    assert rows["dep"].reached_on is None and rows["far"].reached_on is None
    assert plan_view(snap(accounts=[account("a", 600)], goals=[goals[0]]), Profile(), NOW).goals[0].reached_on is None


def test_the_passed_list_holds_round_numbers_and_reached_goals_newest_first():
    pts = [ValuePoint(date=d(2026, 6, 1), value=9400), ValuePoint(date=d(2026, 7, 1), value=10200),
           ValuePoint(date=d(2026, 8, 1), value=9900), ValuePoint(date=d(2026, 9, 1), value=10600),
           ValuePoint(date=TODAY, value=15200)]
    goals = [Goal(id="g", label="Trip", target=10000, account_id="a")]
    v = plan_view(snap(accounts=[account("a", 15200)], goals=goals, account_history=[Series(id="a", points=pts)]),
                  Profile(), NOW)
    assert [(m.date, m.label, m.kind) for m in v.passed] == [
        (TODAY, "$15,000", "round"), (d(2026, 7, 1), "$10,000", "round"), (d(2026, 7, 1), "Trip", "goal")]
    assert plan_view(snap(accounts=[account("a", 100)]), Profile(), NOW).passed == []



# ---------------------------------------------------------------- accurate to the plan (2026-10-08)

def _policy_snap(rebalance):
    a = account("a", 1000)
    under = Target(id="under", account_id="a", label="XLP", symbols=["Y"], target=20, low=18, high=22,
                   rebalance=rebalance)  # 10%: $80 under
    over = Target(id="over", account_id="a", label="XLV", symbols=["X"], target=15, low=12, high=18,
                  rebalance=rebalance)  # 20%: $20 over
    return snap(accounts=[a], holdings=[holding("a", "Y", 100), holding("a", "X", 200), holding("a", "Z", 700)],
                targets=[under, over])


def test_the_status_is_the_plain_fact_whatever_the_policy():
    for rebalance in ("trades", "contributions", "hold"):
        rows = {r.id: r for r in plan_view(_policy_snap(rebalance), Profile(), NOW).accounts[0].rows}
        assert (rows["under"].status, rows["over"].status) == ("under", "over")
        assert rows["under"].rebalance == rebalance


def test_new_money_only_never_says_trim():
    v = plan_view(_policy_snap("contributions"), Profile(), NOW)
    assert [(x.level, x.title, x.why, x.detail) for x in v.actions] == [
        ("note", "Steer new money to XLP in A",
         "The plan rebalances with new money only, so the next deposits go here.",
         "10.0% held · aim 20.0% · band 18–22% · $80.00 to its low end"),
        ("note", "Send no new money to XLV in A",
         "It sits over its band and comes down as new money goes elsewhere: no sale.", "XLV 20.0% (band 12–18%)"),
    ]
    assert not any(x.title.startswith(("Trim", "Add")) for x in v.actions)
    assert v.counts.off_plan == 2 and v.counts.need_trade == 0
    assert "2 targets are outside their bands; none needs a trade." in v.summary


def test_held_and_diluted_is_a_revisit_not_a_buy():
    v = plan_view(_policy_snap("hold"), Profile(), NOW)
    assert [(x.level, x.title) for x in v.actions] == [
        ("note", "Revisit XLP in A: under its band"), ("note", "Send no new money to XLV in A")]
    assert v.actions[0].why == "Held and diluted by plan: under its band is a decision to revisit, not a buy."


def test_home_hears_about_a_target_only_when_it_needs_something():
    trades = {(i.level, i.title) for i in target_attention(_policy_snap("trades"))}
    assert trades == {("warning", "XLP is under plan in A"), ("warning", "XLV is over plan in A")}
    steer = target_attention(_policy_snap("contributions"))
    assert [(i.level, i.title, i.detail) for i in steer] == [
        ("note", "XLP is under plan in A", "under the low end · steer new money here")]
    hold = target_attention(_policy_snap("hold"))
    assert [(i.level, i.detail) for i in hold] == [("note", "under the low end · a decision to revisit, not a buy")]


def test_the_dilute_note_names_every_holding_over_its_band_in_one_account():
    a = account("a", 1000)
    targets = [Target(id=i, account_id="a", label=i.upper(), symbols=[i.upper()], target=10, low=5, high=15,
                      rebalance="contributions") for i in ("p", "q", "r")]
    holdings = [holding("a", "P", 300), holding("a", "Q", 300), holding("a", "R", 100), holding("a", "Z", 300)]
    v = plan_view(snap(accounts=[a], holdings=holdings, targets=targets), Profile(), NOW)
    assert [x.title for x in v.actions] == ["Send no new money to P or Q in A"]
    assert v.actions[0].why.startswith("Each sits over its band")


def test_a_sleeve_and_its_members_nest_and_are_never_summed():
    a = account("a", 1000)
    sleeve = Target(id="core", account_id="a", label="Growth core", symbols=["M", "N", "O"], low=45, high=50,
                    rebalance="hold")
    m = Target(id="m", account_id="a", label="M", symbols=["M"], target=22, low=16.5, high=27.5)
    n = Target(id="n", account_id="a", label="N", symbols=["N"], target=12, low=9, high=15)
    s_ = Target(id="s", account_id="a", label="S", symbols=["S"], target=15, low=11, high=19)
    holdings = [holding("a", "M", 180), holding("a", "N", 140), holding("a", "O", 90), holding("a", "S", 320),
                holding("a", "Z", 270)]
    rows = {r.id: r for r in plan_view(snap(accounts=[a], holdings=holdings, targets=[sleeve, m, n, s_]),
                                       Profile(), NOW).accounts[0].rows}
    assert (rows["m"].parent, rows["n"].parent, rows["s"].parent, rows["core"].parent) == ("core", "core", None, None)
    # each share is its own: the sleeve's 41% and the members' 18% and 14% are never stacked into one bar
    assert (rows["core"].actual, rows["m"].actual, rows["s"].actual) == (41.0, 18.0, 32.0)


def test_the_untargeted_share_counts_each_symbol_once_and_includes_cash():
    a = account("a", 1000)
    sleeve = Target(id="two", account_id="a", label="Two", symbols=["A", "B"], low=15, high=25)
    member = Target(id="a1", account_id="a", label="A", symbols=["A"], target=10, low=5, high=15)
    holdings = [holding("a", "A", 100), holding("a", "B", 100), holding("a", "C", 400)]  # $400 of cash besides
    v = plan_view(snap(accounts=[a], holdings=holdings, targets=[sleeve, member]), Profile(), NOW)
    assert v.accounts[0].untargeted_pct == 80.0
    lone = Target(id="t", account_id="b", label="X", symbols=["X"], target=5)
    nothing = plan_view(snap(accounts=[account("b", 1000)], targets=[lone]), Profile(), NOW)
    assert nothing.accounts[0].untargeted_pct is None  # no holdings reported: unknown, never a fake 100%


def test_a_target_kestrel_cannot_measure_is_never_called_on_plan():
    a = account("a", 1000)
    on = Target(id="on", account_id="a", label="B", symbols=["X"], target=10, low=5, high=15)
    blind = Target(id="blind", account_id="a", label="Core", symbols=[], low=50, high=70)
    gone = Target(id="gone", account_id="missing", label="VTI", symbols=["VTI"], target=60, low=55, high=65)
    hold = [holding("a", "X", 100)]
    v = plan_view(snap(accounts=[a], holdings=hold, targets=[on, blind]), Profile(), NOW)
    assert v.counts.unknown == 1
    assert v.summary == "No goals yet. 1 of 2 targets on plan; 1 can't be measured yet."
    v = plan_view(snap(targets=[gone]), Profile(), NOW)
    assert v.summary == "No goals yet. No target can be measured yet."
    off = Target(id="off", account_id="a", label="C", symbols=["X"], target=50, low=45, high=55)
    v = plan_view(snap(accounts=[a], holdings=hold, targets=[off, blind]), Profile(), NOW)
    assert v.summary == ("No goals yet. 1 target is outside its band and needs a trade. 1 target can't be measured "
                         "yet.")


def test_a_goal_knows_the_goals_it_is_part_of():
    accounts = [account("roth", 600), account("brok", 400)]
    goals = [Goal(id="household", label="Household", target=5000, account_ids=["roth", "brok"]),
             Goal(id="retire", label="Retire", target=9000, account_id="roth"),
             Goal(id="roth-dep", label="Roth deposits", target=700, account_id="roth", measure="deposits",
                  by=d(2026, 12, 31)),
             Goal(id="other", label="Other", target=900, account_id="roth"),
             Goal(id="done", label="Done", target=100, account_ids=["roth", "brok"])]
    history = [Series(id="roth", points=[ValuePoint(date=d(2026, 1, 2), value=100, net_flow=100),
                                         ValuePoint(date=TODAY, value=600)])]
    rows = {g.id: g for g in plan_view(snap(accounts=accounts, goals=goals, account_history=history),
                                       Profile(), NOW).goals}
    # deposits raise the value of every goal over the same or more accounts; a reached goal moves no more
    assert rows["roth-dep"].part_of == ["household", "retire", "other"]
    # a value goal sits inside a strictly larger scope only: two milestones of one number are never part of each other
    assert rows["retire"].part_of == ["household"] and rows["other"].part_of == ["household"]
    assert rows["household"].part_of == []


def test_the_goal_others_sit_inside_says_how_much_of_its_monthly_they_are():
    accounts = [account("roth", 6000), account("brok", 4000)]
    goals = [Goal(id="household", label="Household $20k", target=20000, account_ids=["roth", "brok"],
                  by=d(2026, 12, 31)),
             Goal(id="roth-dep", label="Roth deposits", target=3000, account_id="roth", measure="deposits",
                  by=d(2026, 12, 31)),
             Goal(id="brok-dep", label="Brokerage deposits", target=1500, account_id="brok", measure="deposits",
                  by=d(2026, 12, 31))]
    history = [Series(id=i, points=[ValuePoint(date=d(2026, 1, 2), value=v, net_flow=0),
                                    ValuePoint(date=TODAY, value=v)]) for i, v in (("roth", 6000), ("brok", 4000))]
    v = plan_view(snap(accounts=accounts, goals=goals, account_history=history), Profile(), NOW)
    assert [x.title for x in v.actions] == [
        "Put about $3,333.33 a month toward Household $20k",
        "Put about $500.00 a month in deposits toward Brokerage deposits",
        "Put about $1,000.00 a month in deposits toward Roth deposits"]
    assert v.actions[0].why == ("Brokerage deposits ($500.00 a month) and Roth deposits ($1,000.00 a month) are part "
                                "of this, not on top of it: $1,500.00 of the $3,333.33.")
    assert v.actions[1].why == "Counts toward Household $20k too: the two amounts overlap, they don't add up."


def test_a_lone_goal_names_the_other_goals_it_also_moves():
    accounts = [account("s", 1000)]
    goals = [Goal(id="dep", label="Save", target=1800, account_id="s", measure="deposits", by=d(2026, 12, 31)),
             Goal(id="cash", label="A year in cash", target=40000, account_id="s", by=d(2030, 1, 1))]
    history = [Series(id="s", points=[ValuePoint(date=d(2026, 1, 2), value=100, net_flow=1350),
                                      ValuePoint(date=TODAY, value=1000)])]
    v = plan_view(snap(accounts=accounts, goals=goals, account_history=history), Profile(), NOW)
    assert v.actions[0].why == ("Deposits since 1 January count; this spreads the rest evenly to 31 Dec 2026. "
                                "It also moves A year in cash.")


def _daily(start, days, value, step=1):
    return [ValuePoint(date=start + dt.timedelta(days=i), value=value) for i in range(0, days, step)]


def test_a_deposits_goal_has_a_pace_when_its_history_covers_the_year():
    pts = _daily(d(2026, 1, 1), 268, 1000, step=7)  # weekly, from 1 January
    pts[4] = pts[4].model_copy(update={"net_flow": 900.0})
    goal = Goal(id="dep", label="Save", target=1800, account_id="a", measure="deposits", by=d(2026, 12, 31))
    row = plan_view(snap(accounts=[account("a", 1000)], goals=[goal], account_history=[Series(id="a", points=pts)]),
                    Profile(), NOW).goals[0]
    assert row.pace is not None and row.pace_note == ""
    assert row.pace.start == d(2026, 1, 1) and row.pace.start_value == 0.0
    assert row.pace.points[0].value == 0.0 and row.pace.points[-1] == PacePoint(date=TODAY, value=900.0)
    # the straight line from 0 on 1 January to $1,800 on 31 December, read on 25 September (267 of 364 days)
    assert row.pace.required_now == round(1800 * 267 / 364, 2)
    assert row.pace.ahead == round(900 - 1800 * 267 / 364, 2)


def test_a_long_pace_is_thinned_and_keeps_its_last_point():
    goal = Goal(id="v", label="Grow", target=5000, account_id="a", by=d(2027, 12, 31))
    pts = _daily(d(2026, 1, 1), 268, 1000)
    row = plan_view(snap(accounts=[account("a", 1000)], goals=[goal], account_history=[Series(id="a", points=pts)]),
                    Profile(), NOW).goals[0]
    assert row.pace is not None and len(row.pace.points) <= 61
    assert row.pace.points[-1].date == TODAY and row.pace.start_value == 1000.0


def test_no_pace_when_an_account_s_history_starts_late_or_the_goal_needs_none():
    late = Series(id="b", points=_daily(d(2026, 6, 3), 115, 500))
    early = Series(id="a", points=_daily(d(2026, 1, 1), 268, 1000))
    goal = Goal(id="both", label="Both", target=5000, account_ids=["a", "b"], by=d(2026, 12, 31))
    row = plan_view(snap(accounts=[account("a", 1000), account("b", 500)], goals=[goal],
                         account_history=[early, late]), Profile(), NOW).goals[0]
    assert row.pace is None and row.pace_note == "no pace yet: history for B starts 3 Jun 2026"
    undated = Goal(id="u", label="U", target=5000, account_id="a")
    row = plan_view(snap(accounts=[account("a", 1000)], goals=[undated], account_history=[early]),
                    Profile(), NOW).goals[0]
    assert row.pace is None and row.pace_note == ""
    few = Series(id="a", points=_daily(d(2026, 1, 1), 268, 1000, step=60))
    one = Goal(id="one", label="One", target=5000, account_id="a", by=d(2026, 12, 31))
    row = plan_view(snap(accounts=[account("a", 1000)], goals=[one], account_history=[few]), Profile(), NOW).goals[0]
    assert row.pace is None and row.pace_note == "no pace yet: too little history since 1 January"


def test_a_value_goal_decades_out_gets_no_straight_line_pace():
    goal = Goal(id="retire", label="Retire", target=1_000_000, account_id="a", by=d(2064, 5, 7))
    pts = _daily(d(2026, 1, 1), 268, 1000)
    row = plan_view(snap(accounts=[account("a", 1000)], goals=[goal], account_history=[Series(id="a", points=pts)]),
                    Profile(), NOW).goals[0]
    assert row.pace is None and row.pace_note.startswith("no pace: too far out")


def test_several_theses_on_watch_are_one_note_naming_each_reason():
    theses = [Thesis(symbol="A", health="watch", reasons=["Margins fell."]), Thesis(symbol="B", health="watch")]
    v = plan_view(snap(theses=theses), Profile(), NOW)
    assert [(x.title, x.why, x.anchor) for x in v.actions] == [
        ("Look at 2 theses on watch: A and B", "A — Margins fell; B.", "theses")]


def test_the_demo_ranks_trades_first_and_steers_its_brokerage_with_new_money(demo_plan):
    titles = [x.title for x in demo_plan.actions]
    assert titles[:3] == ["Review HD: thesis on alert", "Trim $2,036.71 from XLV in Roth IRA",
                          "Add $1,357.86 to XLP in Roth IRA"]
    assert "Steer new money to XLI in Brokerage" in titles and "Send no new money to COST in Brokerage" in titles
    assert not any(t.startswith(("Trim", "Add")) and "Brokerage" in t for t in titles)
    brokerage = next(a for a in demo_plan.accounts if a.account_id == "brokerage")
    assert {r.id: r.parent for r in brokerage.rows}["brokerage-cost"] == "brokerage-stocks"
