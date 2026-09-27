import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Event, Holding, Position, Snapshot
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.calendar import calendar_view

d = dt.date
NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def demo():
    return collect(DEMO_PROFILE, NOW)


def snap(events: list[Event], **kw) -> Snapshot:
    return Snapshot(generated_at=NOW, events=events, **kw)


def test_today_follows_the_profile_time_zone():
    # 02:00 UTC on Monday 28 Sep is still Sunday 27 Sep in America/New_York (EDT, UTC-4)
    now = dt.datetime(2026, 9, 28, 2, 0, tzinfo=dt.timezone.utc)
    view = calendar_view(snap([Event(date=d(2026, 9, 27), kind="earnings", title="Quarterly results")]),
                         Profile(), now)
    assert view.today == d(2026, 9, 27)
    assert len(view.upcoming) == 1 and view.upcoming[0].items[0].date == d(2026, 9, 27)
    assert view.recent == []  # today's own event is upcoming, not recent


def test_upcoming_events_group_into_monday_start_weeks_in_order():
    # Fri 25 Sep 2026 and Sat 26 Sep both fall in the week of Mon 21 Sep; Mon 5 Oct starts its own week
    events = [
        Event(date=d(2026, 9, 26), kind="earnings", title="A"),
        Event(date=d(2026, 9, 25), kind="filing", title="B"),
        Event(date=d(2026, 10, 5), kind="earnings", title="C"),
    ]
    view = calendar_view(snap(events), Profile(), NOW)
    assert [w.week_start for w in view.upcoming] == [d(2026, 9, 21), d(2026, 10, 5)]
    assert [e.title for e in view.upcoming[0].items] == ["B", "A"]  # date ascending within a week
    assert all(w.week_start.weekday() == 0 for w in view.upcoming)  # every group starts on a Monday


def test_recent_excludes_more_than_90_days_ago_and_any_future_date():
    today = NOW.astimezone(Profile().tz).date()
    events = [
        Event(date=today - dt.timedelta(days=90), kind="filing", title="in range"),
        Event(date=today - dt.timedelta(days=91), kind="filing", title="too old"),
        Event(date=today, kind="filing", title="today itself"),  # belongs to upcoming, never recent
        Event(date=today + dt.timedelta(days=1), kind="filing", title="future"),
    ]
    view = calendar_view(snap(events), Profile(), NOW)
    assert [e.title for e in view.recent] == ["in range"]


def test_recent_is_newest_first():
    today = NOW.astimezone(Profile().tz).date()
    events = [Event(date=today - dt.timedelta(days=10), kind="filing", title="older"),
              Event(date=today - dt.timedelta(days=1), kind="filing", title="newest")]
    view = calendar_view(snap(events), Profile(), NOW)
    assert [e.title for e in view.recent] == ["newest", "older"]


def test_held_flag_is_true_for_a_holding_or_an_open_position():
    today = NOW.astimezone(Profile().tz).date()
    events = [Event(date=today + dt.timedelta(days=1), symbol="AAPL", kind="earnings", title="Held via holding"),
              Event(date=today + dt.timedelta(days=1), symbol="MSFT", kind="earnings", title="Held via position"),
              Event(date=today + dt.timedelta(days=1), symbol="XOM", kind="earnings", title="Not held")]
    holdings = [Holding(account_id="a", symbol="AAPL", quantity=1, price=1, value=1)]
    positions = [Position(book_id="b", symbol="MSFT", quantity=1, entry_price=1, last_price=1, opened=today)]
    view = calendar_view(snap(events, holdings=holdings, positions=positions), Profile(), NOW)
    held = {e.title: e.held for w in view.upcoming for e in w.items}
    assert held == {"Held via holding": True, "Held via position": True, "Not held": False}


def test_counts_are_by_kind_over_every_event_shown():
    today = NOW.astimezone(Profile().tz).date()
    events = [
        Event(date=today + dt.timedelta(days=1), kind="earnings", title="e1"),
        Event(date=today + dt.timedelta(days=2), kind="earnings", title="e2"),
        Event(date=today - dt.timedelta(days=1), kind="filing", title="f1"),
        Event(date=today - dt.timedelta(days=1), kind="insider", title="i1"),
    ]
    view = calendar_view(snap(events), Profile(), NOW)
    assert view.counts == {"earnings": 2, "filing": 1, "insider": 1, "dividend": 0, "other": 0}


def test_no_events_is_empty():
    view = calendar_view(snap([]), Profile(), NOW)
    assert (view.upcoming, view.recent, view.counts) == ([], [], {"earnings": 0, "filing": 0, "insider": 0,
                                                                   "dividend": 0, "other": 0})


def test_demo_data_has_events_ahead_and_behind(demo):
    view = calendar_view(demo, DEMO_PROFILE, NOW)
    assert sum(len(w.items) for w in view.upcoming) > 0
    assert len(view.recent) > 0
    assert sum(view.counts.values()) == len(demo.events)
