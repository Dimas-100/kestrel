import datetime as dt

from kestrel.contract import Alert, Run, Snapshot, Source
from kestrel.profile import Profile, SourceCfg
from kestrel.views.activity import activity_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)  # a Friday, in UTC (the default profile's tz)
TODAY = dt.date(2026, 9, 25)


def _run(days_from_today: int, hour: int, status: str, label: str = "run", book_id: str | None = None) -> Run:
    when = dt.datetime.combine(TODAY + dt.timedelta(days=days_from_today), dt.time(hour, 0), tzinfo=dt.timezone.utc)
    return Run(time=when, label=label, book_id=book_id, status=status, detail="")


def test_days_are_today_then_future_ascending_then_past_descending():
    runs = [_run(2, 9, "due"), _run(0, 9, "done"), _run(-1, 9, "done"), _run(1, 9, "due"), _run(-3, 9, "done")]
    snap = Snapshot(generated_at=NOW, runs=runs)
    v = activity_view(snap, Profile(), NOW)
    assert [d.date for d in v.days] == [TODAY, TODAY + dt.timedelta(days=1), TODAY + dt.timedelta(days=2),
                                        TODAY - dt.timedelta(days=1), TODAY - dt.timedelta(days=3)]
    assert [d.label for d in v.days][:2] == ["Today", "Tomorrow"]
    assert v.days[2].label == "Sun 27 Sep"
    assert v.days[3].label == "Thu 24 Sep"


def test_runs_older_than_seven_days_are_dropped():
    snap = Snapshot(generated_at=NOW, runs=[_run(-7, 9, "done"), _run(-8, 9, "done")])
    v = activity_view(snap, Profile(), NOW)
    assert [d.date for d in v.days] == [TODAY - dt.timedelta(days=7)]


def test_failed_and_late_run_first_within_a_day():
    runs = [_run(0, 9, "done", label="a"), _run(0, 10, "failed", label="b"), _run(0, 8, "late", label="c")]
    snap = Snapshot(generated_at=NOW, runs=runs)
    v = activity_view(snap, Profile(), NOW)
    assert [r.label for r in v.days[0].runs] == ["c", "b", "a"]


def test_counts_by_status():
    runs = [_run(0, 9, "done"), _run(0, 10, "done"), _run(0, 11, "failed"), _run(-8, 9, "done")]  # the last is dropped
    snap = Snapshot(generated_at=NOW, runs=runs)
    v = activity_view(snap, Profile(), NOW)
    assert v.counts == {"done": 2, "failed": 1}


def test_a_run_names_its_book():
    from kestrel.contract import Book

    book = Book(id="b", name="Mean reversion", money="real", strategy_id="s", status="running",
                started=dt.date(2026, 1, 1), value=1000)
    snap = Snapshot(generated_at=NOW, books=[book], runs=[_run(0, 9, "done", book_id="b")])
    v = activity_view(snap, Profile(), NOW)
    row = v.days[0].runs[0]
    assert (row.book_id, row.book_name) == ("b", "Mean reversion")
    # a run with no book at all names none
    snap2 = Snapshot(generated_at=NOW, runs=[_run(0, 9, "done")])
    assert activity_view(snap2, Profile(), NOW).days[0].runs[0].book_name is None


def test_sources_carry_stale_after_from_the_profile():
    profile = Profile(sources=[SourceCfg(id="desk", kind="rails", stale_after="15m")])
    src = Source(id="desk", label="Trading desk", kind="feed", last_success=NOW - dt.timedelta(minutes=5))
    v = activity_view(Snapshot(generated_at=NOW, sources=[src]), profile, NOW)
    assert v.sources[0].stale_after == "15m"
    assert v.sources[0].age_text == "5 minutes"


def test_a_sub_source_matches_its_profile_entry_by_prefix():
    """A connector may report several source rows under one profile entry (the demo does); each still carries that
    entry's stale_after."""
    profile = Profile(sources=[SourceCfg(id="demo", kind="demo", stale_after="36h")])
    src = Source(id="demo-portfolio", label="Portfolio", kind="data collector", last_success=NOW)
    v = activity_view(Snapshot(generated_at=NOW, sources=[src]), profile, NOW)
    assert v.sources[0].stale_after == "36h"


def test_a_source_that_never_synced_has_no_age():
    src = Source(id="desk", label="Trading desk", kind="feed", status="error", last_success=None, detail="boom")
    v = activity_view(Snapshot(generated_at=NOW, sources=[src]), Profile(), NOW)
    assert v.sources[0].age_text is None and v.sources[0].detail == "boom"


def test_alerts_sorted_by_level():
    alerts = [Alert(level="note", title="n"), Alert(level="serious", title="s"), Alert(level="warning", title="w")]
    v = activity_view(Snapshot(generated_at=NOW, alerts=alerts), Profile(), NOW)
    assert [a.level for a in v.alerts] == ["serious", "warning", "note"]


def test_an_empty_snapshot_still_renders():
    v = activity_view(Snapshot(generated_at=NOW), Profile(), NOW)
    assert v.days == [] and v.counts == {} and v.alerts == [] and v.sources == []


def test_age_text_reused_from_home():
    # sanity check only: activity.py imports Home's age_text rather than re-implementing it
    from kestrel.views.activity import age_text as activity_age_text
    from kestrel.views.home import age_text as home_age_text
    assert activity_age_text is home_age_text
