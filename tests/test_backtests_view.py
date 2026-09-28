import datetime as dt
import random
import time

import pytest

from kestrel.connectors import collect
from kestrel.contract import Backtest, Snapshot
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.backtests import ROWS_LIMIT, backtests_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def demo():
    return collect(DEMO_PROFILE, NOW)


def at(days_ago: float) -> dt.datetime:
    return NOW - dt.timedelta(days=days_ago)


def bt(id_, name, family, window, verdict, days_ago, **kw) -> Backtest:
    return Backtest(id=id_, name=name, family=family, window=window, verdict=verdict, at=at(days_ago), **kw)


def snap(backtests: list[Backtest]) -> Snapshot:
    return Snapshot(generated_at=NOW, backtests=backtests)


def test_totals_count_results_distinct_candidates_families_and_passes_by_window():
    data = [
        bt("d1a", "Dip A", "Dip", "develop", "pass", 10),
        bt("d1b", "Dip A", "Dip", "confirm", "pass", 5),  # same candidate name, another window
        bt("d2", "Dip B", "Dip", "develop", "fail", 12),
        bt("g1", "Gap A", "Gap", "develop", "pass", 20),
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    assert view.totals.results == 4
    assert view.totals.candidates == 3  # "Dip A", "Dip B", "Gap A" -- a candidate counts once across its windows
    assert view.totals.families == 2
    assert view.totals.passes_by_window == {"develop": 2, "confirm": 1}


def test_windows_follow_the_research_pipeline_order_not_recency():
    data = [
        bt("a", "A", "F", "confirm", "pass", 1),  # confirm's newest result is 1 day ago (more recent)...
        bt("b", "B", "F", "develop", "pass", 200),  # ...but develop still comes first: it is earlier in the pipeline
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    assert view.windows == ["develop", "confirm"]


def test_windows_outside_the_pipeline_sort_after_it_alphabetically():
    data = [
        bt("a", "A", "F", "confirm", "pass", 1),
        bt("b", "B", "F", "develop", "pass", 2),
        bt("c", "C", "F", "zzz-custom", "pass", 3),
        bt("d", "D", "F", "aaa-custom", "pass", 4),
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    assert view.windows == ["develop", "confirm", "aaa-custom", "zzz-custom"]


def test_windows_only_lists_windows_present_in_the_data():
    # "holdout" and "live" are pipeline stages, but nothing in this data used them
    data = [bt("a", "A", "F", "confirm", "pass", 1), bt("b", "B", "F", "develop", "fail", 2)]
    view = backtests_view(snap(data), Profile(), NOW)
    assert view.windows == ["develop", "confirm"]


def test_best_favors_the_furthest_pipeline_stage_over_a_more_recent_earlier_stage():
    # the controller's disagreement case: confirm passed long ago, develop is the recently active window
    data = [
        bt("c1", "A", "F", "confirm", "pass", 200, t_stat=2.0),
        bt("d1", "B", "F", "develop", "fail", 1),
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    assert view.windows == ["develop", "confirm"]
    family = next(f for f in view.families if f.family == "F")
    assert family.best is not None and family.best.id == "c1"  # confirm is further along than develop, despite age


def test_best_is_the_furthest_window_with_a_pass_ties_broken_by_higher_t_stat():
    data = [
        bt("d1", "A", "F", "develop", "pass", 30, t_stat=4.0),
        bt("c1", "A", "F", "confirm", "pass", 5, t_stat=2.1),   # confirm is the newer, furthest-along window
        bt("c2", "B", "F", "confirm", "pass", 6, t_stat=3.5),   # a second confirm pass, higher t wins the tie
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    family = next(f for f in view.families if f.family == "F")
    assert family.best is not None and family.best.id == "c2"


def test_best_falls_back_to_the_newest_result_when_nothing_passed():
    data = [
        bt("d1", "A", "F", "develop", "fail", 10),
        bt("d2", "B", "F", "develop", "fail", 3),  # the newest of the two
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    family = next(f for f in view.families if f.family == "F")
    assert family.best is not None and family.best.id == "d2"


def test_best_ranks_a_window_the_pipeline_doesnt_name_below_every_stage_it_does():
    # "zzz-custom" sorts after "develop" as a column, but that says nothing about how far along it is: a develop pass
    # is the best result even though the custom one is newer and has the higher t
    data = [
        bt("dev", "A", "F", "develop", "pass", 30, t_stat=2.14),
        bt("custom", "B", "F", "zzz-custom", "pass", 2, t_stat=5.87),
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    assert view.windows == ["develop", "zzz-custom"]
    assert view.families[0].best.id == "dev"
    # with no pipeline pass at all, the custom pass is still the best there is
    only = backtests_view(snap([bt("custom", "B", "F", "zzz-custom", "pass", 2, t_stat=5.87),
                                bt("dev", "A", "F", "develop", "fail", 1)]), Profile(), NOW)
    assert only.families[0].best.id == "custom"


def test_passes_by_window_follow_the_pipeline_order():
    data = [
        bt("c1", "A", "F", "confirm", "pass", 1), bt("x1", "B", "F", "aaa-custom", "pass", 2),
        bt("d1", "C", "F", "develop", "pass", 3), bt("c2", "D", "G", "confirm", "pass", 4),
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    assert list(view.totals.passes_by_window.items()) == [("develop", 1), ("confirm", 2), ("aaa-custom", 1)]


def test_verdict_per_window_is_the_best_seen_pass_then_pending_then_fail_then_refused():
    data = [
        bt("a", "A", "F", "develop", "fail", 10),
        bt("b", "B", "F", "develop", "refused", 9),
        bt("c", "C", "F", "develop", "pending", 8),
        bt("d", "D", "F", "confirm", "fail", 7),
        bt("e", "E", "F", "confirm", "refused", 6),
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    family = next(f for f in view.families if f.family == "F")
    assert family.verdicts == {"develop": "pending", "confirm": "fail"}


def test_families_with_a_pass_come_first_then_by_last_at_descending():
    data = [
        bt("a", "A", "Old fail", "develop", "fail", 100),
        bt("b", "B", "New fail", "develop", "fail", 1),
        bt("c", "C", "Old pass", "develop", "pass", 50),
        bt("d", "D", "New pass", "develop", "pass", 2),
    ]
    view = backtests_view(snap(data), Profile(), NOW)
    assert [f.family for f in view.families] == ["New pass", "Old pass", "New fail", "Old fail"]


def test_rows_are_the_newest_200_even_with_5000_inputs_and_it_stays_fast():
    rng = random.Random(1)
    data = [bt(f"id-{i}", f"Name {i}", f"Family {i % 40}", rng.choice(["develop", "confirm"]),
              rng.choice(["pass", "fail", "refused", "pending"]), rng.uniform(0, 900))
            for i in range(5000)]
    start = time.perf_counter()
    view = backtests_view(snap(data), Profile(), NOW)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0
    assert len(view.rows) == ROWS_LIMIT
    assert view.rows == sorted(data, key=lambda b: b.at, reverse=True)[:ROWS_LIMIT]
    assert view.totals.results == 5000


def test_no_backtests_is_empty():
    view = backtests_view(snap([]), Profile(), NOW)
    assert (view.totals.results, view.totals.candidates, view.totals.families) == (0, 0, 0)
    assert (view.windows, view.families, view.rows, view.totals.passes_by_window) == ([], [], [], {})


def test_demo_data_has_families_and_a_bounded_row_list(demo):
    view = backtests_view(demo, DEMO_PROFILE, NOW)
    assert view.totals.results == len(demo.backtests)
    assert view.totals.families == len({b.family for b in demo.backtests})
    assert len(view.rows) == min(len(demo.backtests), ROWS_LIMIT)
    assert view.rows == sorted(view.rows, key=lambda b: b.at, reverse=True)
    for family in view.families:
        assert family.best is not None
