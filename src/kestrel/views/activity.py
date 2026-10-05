"""The Activity page, computed from one Snapshot: what ran, what is due, and what failed."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from ..contract import Alert, Run, Snapshot
from ..profile import Profile, source_config
from ._base import View
from .home import age_text

PAST_DAYS = 7  # how far back "the past 7 days" reaches
LATE_FIRST = ("failed", "late")  # within a day, these statuses sort ahead of the rest
ALERT_ORDER = {"serious": 0, "warning": 1, "note": 2}
WEEK_DAYS = 7  # the week grid: this many days back, plus today
WORST = {"failed": 0, "late": 1, "due": 2, "paused": 3, "done": 4}  # a day's cell shows the worst of its runs


class RunRow(View):
    time: dt.datetime
    label: str
    book_id: str | None
    book_name: str | None
    status: Literal["done", "due", "late", "failed", "paused"]
    detail: str


class DayRuns(View):
    date: dt.date
    label: str  # "Today" | "Tomorrow" | a weekday date, e.g. "Fri 25 Sep"
    runs: list[RunRow]


class ActivitySource(View):
    id: str
    label: str
    kind: str
    status: Literal["ok", "stale", "error"]
    last_success: dt.datetime | None
    age_text: str | None
    stale_after: str | None  # None when no profile source configured this one (can't happen for a real profile)
    detail: str


class WeekCell(View):
    date: dt.date
    status: Literal["done", "due", "late", "failed", "paused"] | None  # None: the job had no run that day


class WeekRow(View):
    label: str  # the job
    cells: list[WeekCell]  # the eight days from a week ago to today


class ActivityView(View):
    as_of: dt.datetime
    summary: str  # the header's sentence: today's runs, the next one, the sources, the alerts
    next_run: RunRow | None  # the earliest run still due at or after now, today or later
    week: list[WeekRow]  # one row per job, in the order the jobs run through the day
    days: list[DayRuns]
    counts: dict[str, int]  # by run status, over the runs shown in `days`
    alerts: list[Alert]  # serious, warning, note
    sources: list[ActivitySource]


def _day_label(day: dt.date, today: dt.date) -> str:
    if day == today:
        return "Today"
    if day == today + dt.timedelta(days=1):
        return "Tomorrow"
    return f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"


def _ordered_days(by_date: dict[dt.date, list[Run]], today: dt.date) -> list[dt.date]:
    """Today first (when it has runs), then future days ascending, then the past 7 days descending."""
    future = sorted(d for d in by_date if d > today)
    past = sorted((d for d in by_date if d < today), reverse=True)
    return ([today] if today in by_date else []) + future + past


def _sorted_runs(runs: list[Run]) -> list[Run]:
    """Failed and late first, then by time."""
    return sorted(runs, key=lambda r: (0 if r.status in LATE_FIRST else 1, r.time))


def _stale_after(source_id: str, profile: Profile) -> str | None:
    """The `stale_after` of the profile source that produced this row (`profile.source_config`), or None when no
    entry matches at all (can't happen for a real profile: every source traces back to one)."""
    cfg = source_config(profile, source_id)
    return cfg.stale_after if cfg is not None else None


def _sources(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> list[ActivitySource]:
    return [
        ActivitySource(
            id=s.id, label=s.label, kind=s.kind, status=s.status, last_success=s.last_success,
            age_text=age_text(now - s.last_success) if s.last_success is not None else None,
            stale_after=_stale_after(s.id, profile), detail=s.detail,
        )
        for s in snapshot.sources
    ]


def _alerts(snapshot: Snapshot) -> list[Alert]:
    return sorted(snapshot.alerts, key=lambda a: ALERT_ORDER[a.level])


def week_rows(runs: list[Run], today: dt.date, tz) -> list[WeekRow]:
    """One row per job that ran in the eight days from a week ago to today, in the order the jobs run through the
    day (the earliest time of day each was seen); a cell per day, the worst status of that day's runs, None when
    the job didn't run. The day a run falls on is read in the profile's zone."""
    days = [today - dt.timedelta(days=WEEK_DAYS - i) for i in range(WEEK_DAYS + 1)]
    by_label: dict[str, dict[dt.date, str]] = {}
    first_seen: dict[str, dt.time] = {}
    for r in runs:
        local = r.time.astimezone(tz)
        day = local.date()
        if day < days[0] or day > today:
            continue
        cells = by_label.setdefault(r.label, {})
        current = cells.get(day)
        if current is None or WORST[r.status] < WORST[current]:
            cells[day] = r.status
        if r.label not in first_seen or local.time() < first_seen[r.label]:
            first_seen[r.label] = local.time()
    return [WeekRow(label=label, cells=[WeekCell(date=d, status=by_label[label].get(d)) for d in days])
            for label in sorted(by_label, key=lambda label: (first_seen[label], label))]


def _next_run(runs: list[Run], now: dt.datetime, book_names: dict[str, str]) -> RunRow | None:
    due = sorted((r for r in runs if r.status == "due" and r.time >= now), key=lambda r: r.time)
    if not due:
        return None
    r = due[0]
    return RunRow(time=r.time, label=r.label, book_id=r.book_id,
                  book_name=book_names.get(r.book_id, r.book_id) if r.book_id else None, status=r.status,
                  detail=r.detail)


def activity_summary(today_runs: list[Run], next_run: RunRow | None, sources: list[ActivitySource],
                     alerts: list[Alert], tz) -> str:
    """Today's runs, the next one, the sources and the alerts, each part left out when there is nothing to say."""
    parts = []
    if not today_runs:
        parts.append("No runs today.")
    else:
        bad = sum(1 for r in today_runs if r.status in LATE_FIRST)
        parts.append(f"{bad} run{'s' if bad != 1 else ''} failed or late today." if bad
                     else "Every run so far today is done.")
    if next_run is not None:
        parts.append(f"Next: {next_run.label} at {next_run.time.astimezone(tz).strftime('%H:%M')}.")
    if sources:
        bad = sum(1 for s in sources if s.status != "ok")
        parts.append(f"{bad} source{'s are' if bad != 1 else ' is'} stale or failing." if bad
                     else "Every source is fresh.")
    if alerts:
        parts.append(f"{len(alerts)} alert{'s' if len(alerts) != 1 else ''}.")
    return " ".join(parts)


def activity_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> ActivityView:
    tz = profile.tz
    today = now.astimezone(tz).date()
    cutoff = today - dt.timedelta(days=PAST_DAYS)
    by_date: dict[dt.date, list[Run]] = {}
    for r in snapshot.runs:
        day = r.time.astimezone(tz).date()
        if day < cutoff:
            continue
        by_date.setdefault(day, []).append(r)
    book_names = {b.id: b.name for b in snapshot.books}
    counts: dict[str, int] = {}
    days: list[DayRuns] = []
    for day in _ordered_days(by_date, today):
        rows = []
        for r in _sorted_runs(by_date[day]):
            counts[r.status] = counts.get(r.status, 0) + 1
            rows.append(RunRow(
                time=r.time, label=r.label, book_id=r.book_id,
                book_name=book_names.get(r.book_id, r.book_id) if r.book_id else None,
                status=r.status, detail=r.detail,
            ))
        days.append(DayRuns(date=day, label=_day_label(day, today), runs=rows))
    sources = _sources(snapshot, profile, now)
    alerts = _alerts(snapshot)
    next_run = _next_run(snapshot.runs, now, book_names)
    return ActivityView(as_of=now, summary=activity_summary(by_date.get(today, []), next_run, sources, alerts, tz),
                        next_run=next_run, week=week_rows(snapshot.runs, today, tz), days=days, counts=counts,
                        alerts=alerts, sources=sources)
