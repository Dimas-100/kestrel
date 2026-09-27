"""The Calendar page, computed from one Snapshot: company events ahead and behind."""

from __future__ import annotations

import datetime as dt
from collections import Counter

from ..contract import Event, Snapshot
from ..profile import Profile
from .home import View

RECENT_DAYS = 90  # how far back "recent" looks
KINDS = ("earnings", "filing", "insider", "dividend", "other")


class EventRow(View):
    date: dt.date
    symbol: str
    kind: str
    title: str
    detail: str
    url: str
    held: bool  # the symbol sits in a holding or an open position


class WeekGroup(View):
    week_start: dt.date  # the Monday the week starts on
    items: list[EventRow]


class CalendarView(View):
    as_of: dt.datetime
    today: dt.date
    upcoming: list[WeekGroup]  # date ascending, grouped by week
    recent: list[EventRow]  # the last RECENT_DAYS days, newest first
    counts: dict[str, int]  # by kind, over every event shown above


def _week_start(day: dt.date) -> dt.date:
    return day - dt.timedelta(days=day.weekday())


def _row(event: Event, held: set[str]) -> EventRow:
    return EventRow(date=event.date, symbol=event.symbol, kind=event.kind, title=event.title, detail=event.detail,
                    url=event.url, held=bool(event.symbol) and event.symbol in held)


def calendar_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> CalendarView:
    today = now.astimezone(profile.tz).date()
    held = {h.symbol for h in snapshot.holdings} | {p.symbol for p in snapshot.positions}

    ahead = sorted((e for e in snapshot.events if e.date >= today), key=lambda e: (e.date, e.symbol, e.title))
    weeks: dict[dt.date, list[EventRow]] = {}
    for e in ahead:
        weeks.setdefault(_week_start(e.date), []).append(_row(e, held))
    upcoming = [WeekGroup(week_start=ws, items=weeks[ws]) for ws in sorted(weeks)]

    since = today - dt.timedelta(days=RECENT_DAYS)
    behind = sorted((e for e in snapshot.events if since <= e.date < today),
                    key=lambda e: (e.date, e.symbol, e.title), reverse=True)
    recent = [_row(e, held) for e in behind]

    counts = Counter(e.kind for e in (*ahead, *behind))
    return CalendarView(as_of=now, today=today, upcoming=upcoming, recent=recent,
                        counts={kind: counts[kind] for kind in KINDS})
