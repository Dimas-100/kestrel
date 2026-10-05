import datetime as dt

from kestrel.contract import Alert, Run, Snapshot, Source
from kestrel.profile import Profile, SourceCfg
from kestrel.views.activity import activity_view, week_rows

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


def test_an_exact_id_match_wins_over_a_shorter_prefix_whatever_the_profile_order():
    """desk-2 is its own configured source, not a sub-source of desk; the exact match must win regardless of which
    cfg the profile lists first (a prefix match on "desk" must never pre-empt the exact "desk-2" entry)."""
    desk = SourceCfg(id="desk", kind="rails", stale_after="15m")
    desk2 = SourceCfg(id="desk-2", kind="rails", stale_after="5m")
    src = Source(id="desk-2", label="Desk 2", kind="feed", last_success=NOW)
    for sources in ([desk, desk2], [desk2, desk]):
        profile = Profile(sources=sources)
        v = activity_view(Snapshot(generated_at=NOW, sources=[src]), profile, NOW)
        assert v.sources[0].stale_after == "5m", sources

    # a genuine sub-source of "desk" (no "desk-2" configured) still falls back to the prefix match
    only_desk = Profile(sources=[desk])
    extra = Source(id="desk-extra", label="Desk extra", kind="feed", last_success=NOW)
    v = activity_view(Snapshot(generated_at=NOW, sources=[extra]), only_desk, NOW)
    assert v.sources[0].stale_after == "15m"


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


# ---------------------------------------------------------------- the sentence, the next run and the week (2026-10-05)

UTC = Profile(app={"timezone": "UTC"})  # the default profile keeps New York; these sentences print times


def _at(days_from_today: int, hour: int, minute: int, status: str, label: str) -> Run:
    when = dt.datetime.combine(TODAY + dt.timedelta(days=days_from_today), dt.time(hour, minute),
                               tzinfo=dt.timezone.utc)
    return Run(time=when, label=label, status=status, detail="")


def test_summary_names_todays_runs_the_next_one_the_sources_and_the_alerts():
    runs = [_at(0, 9, 31, "done", "Morning run"), _at(0, 15, 45, "failed", "Retry"), _at(0, 23, 0, "due", "Backup"),
            _at(0, 17, 30, "late", "Evening suite"), _at(1, 9, 31, "due", "Morning run")]
    sources = [Source(id="desk", label="Desk", kind="feed", status="ok", last_success=NOW),
               Source(id="bank", label="Bank", kind="feed", status="stale", last_success=NOW)]
    alerts = [Alert(level="warning", title="KO is near its stop")]
    v = activity_view(Snapshot(generated_at=NOW, runs=runs, sources=sources, alerts=alerts), UTC, NOW)
    assert v.summary == "2 runs failed or late today. Next: Backup at 23:00. 1 source is stale or failing. 1 alert."
    assert (v.next_run.label, v.next_run.time.hour) == ("Backup", 23)
    fine = activity_view(Snapshot(generated_at=NOW, runs=[_at(0, 9, 31, "done", "Morning run")],
                                  sources=[sources[0]]), UTC, NOW)
    assert fine.summary == "Every run so far today is done. Every source is fresh."
    assert fine.next_run is None
    assert activity_view(Snapshot(generated_at=NOW), UTC, NOW).summary == "No runs today."


def test_the_next_run_is_the_earliest_still_due_at_or_after_now_today_or_later():
    runs = [_at(0, 9, 0, "due", "Missed"),  # before now (21:08): not next, it is late or stale
            _at(1, 9, 31, "due", "Tomorrow morning"), _at(0, 23, 0, "due", "Backup"), _at(0, 22, 0, "paused", "Off")]
    v = activity_view(Snapshot(generated_at=NOW, runs=runs), UTC, NOW)
    assert (v.next_run.label, v.next_run.time.hour) == ("Backup", 23)
    assert "Next: Backup at 23:00." in v.summary


def test_week_rows_one_per_job_in_the_order_they_run_with_blanks_and_the_worst_of_a_day():
    runs = [_at(-6, 17, 30, "done", "Evening suite"), _at(-6, 9, 31, "done", "Morning run"),
            _at(-3, 9, 31, "failed", "Morning run"), _at(-3, 9, 40, "done", "Morning run"),  # worst of the day: failed
            _at(-1, 9, 31, "late", "Morning run"), _at(0, 9, 31, "done", "Morning run"),
            _at(1, 9, 31, "due", "Morning run")]  # tomorrow: not in the week
    v = activity_view(Snapshot(generated_at=NOW, runs=runs), UTC, NOW)
    assert [r.label for r in v.week] == ["Morning run", "Evening suite"]
    morning = v.week[0]
    assert [c.date for c in morning.cells] == [TODAY - dt.timedelta(days=7 - i) for i in range(8)]
    assert [c.status for c in morning.cells] == [None, "done", None, None, "failed", None, "late", "done"]
    assert [c.status for c in v.week[1].cells] == [None, "done", None, None, None, None, None, None]
    assert week_rows([], TODAY, dt.timezone.utc) == []


def test_the_week_uses_the_profiles_zone_for_the_day_a_run_falls_on():
    ny = Profile(app={"timezone": "America/New_York"})
    late_utc = Run(time=dt.datetime(2026, 9, 25, 2, 30, tzinfo=dt.timezone.utc), label="Night", status="done",
                   detail="")
    v = activity_view(Snapshot(generated_at=NOW, runs=[late_utc]), ny, NOW)  # 22:30 on the 24th in New York
    cells = {c.date: c.status for c in v.week[0].cells}
    assert cells[dt.date(2026, 9, 24)] == "done" and cells[dt.date(2026, 9, 25)] is None


def test_the_streak_counts_weekdays_in_a_row_where_every_job_ran_and_none_failed():
    # Fri 18 .. Fri 25 Sep (today, a Friday); the week grid holds a week back plus today
    def day(n, status="done", label="Morning run"):
        return _at(-n, 9, 31, status, label)
    runs = [day(7), day(4), day(3), day(2), day(1), day(0)]  # Mon 21 .. Fri 25 and Fri 18: the weekend 19/20 is free
    v = activity_view(Snapshot(generated_at=NOW, runs=runs), UTC, NOW)
    assert v.streak_days == 6
    failed = runs + [day(2, "failed", "Evening run"), day(1, "done", "Evening run"), day(0, "done", "Evening run")]
    assert activity_view(Snapshot(generated_at=NOW, runs=failed), UTC, NOW).streak_days == 2  # Thu 24, Fri 25
    assert activity_view(Snapshot(generated_at=NOW), UTC, NOW).streak_days == 0

