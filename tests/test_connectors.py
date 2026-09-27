"""collect() and ids that two sources share: the first source in the profile keeps its item."""

import datetime as dt
import re

from feed_fixture import MADE, desk, feed_file

from kestrel.cli import main
from kestrel.connectors import collect
from kestrel.connectors.base import DETAIL_LIMIT
from kestrel.profile import DEMO_PROFILE, Profile, SourceCfg
from kestrel.views.home import home_view
from kestrel.views.strategy import strategy_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
DAY = {"date": "2026-09-25", "value": 100.0}


def with_account(payload: dict) -> dict:
    """The desk's payload plus a brokerage account with one holding and a day of history."""
    return {**payload,
            "accounts": [{"id": "brokerage", "name": "Brokerage", "category": "long_term", "value": 5000.0,
                          "as_of": "2026-09-25T20:00:00+00:00"}],
            "holdings": [{"account_id": "brokerage", "symbol": "VTI", "quantity": 10, "price": 300.0,
                          "value": 3000.0}],
            "account_history": [{"id": "brokerage", "points": [{"date": "2026-09-25", "value": 5000.0}]}]}


def household() -> dict:
    """A second fictional source that reuses the desk's account, book and strategy ids, and has its own too."""
    return desk(
        accounts=[{"id": "brokerage", "name": "Joint brokerage", "category": "long_term", "value": 9999.0,
                   "as_of": "2026-09-25T20:00:00+00:00"},
                  {"id": "hsa", "name": "HSA", "category": "long_term", "value": 1200.0,
                   "as_of": "2026-09-25T20:00:00+00:00"}],
        holdings=[{"account_id": "brokerage", "symbol": "BND", "quantity": 1, "price": 72.0, "value": 72.0},
                  {"account_id": "hsa", "symbol": "VXUS", "quantity": 2, "price": 70.0, "value": 140.0}],
        account_history=[{"id": "brokerage", "points": [DAY]}, {"id": "hsa", "points": [DAY]}],
        books=[{"id": "swing-real", "name": "Other swing", "money": "real", "strategy_id": "swing",
                "status": "paused", "started": "2025-01-02", "value": 1.0},
               {"id": "ibs-paper", "name": "IBS (paper)", "money": "paper", "strategy_id": "ibs",
                "status": "running", "started": "2026-02-02", "value": 3200.0}],
        book_history=[{"id": "swing-real", "points": [DAY]}, {"id": "ibs-paper", "points": [DAY]}],
        positions=[{"book_id": "swing-real", "symbol": "XOM", "quantity": 1, "entry_price": 110.0,
                    "last_price": 111.0, "opened": "2026-09-23"}],
        trades=[{"book_id": "swing-real", "symbol": "CVX", "opened": "2026-09-01", "closed": "2026-09-02",
                 "entry_price": 150.0, "exit_price": 151.0, "quantity": 1, "pnl": 1.0, "return_pct": 0.67},
                {"book_id": "ibs-paper", "symbol": "SPY", "opened": "2026-09-21", "closed": "2026-09-22",
                 "entry_price": 650.0, "exit_price": 653.0, "quantity": 2, "pnl": 6.0, "return_pct": 0.46}],
        trade_charts=[{"book_id": "swing-real", "symbol": "CVX", "opened": "2026-09-01",
                       "bars": [{"date": "2026-09-01", "open": 150.0, "high": 151.5, "low": 149.2, "close": 150.4}]}],
        strategies=[{"id": "swing", "name": "Someone else's swing"}, {"id": "ibs", "name": "Weak close"}],
        runs=[{"time": "2026-09-25T13:31:00+00:00", "label": "Other morning", "book_id": "swing-real",
               "status": "done"},
              {"time": "2026-09-25T19:56:00+00:00", "label": "Close entries", "book_id": "ibs-paper",
               "status": "done"},
              {"time": "2026-09-25T23:00:00+00:00", "label": "Backup", "status": "due"}],
        alerts=[{"level": "note", "title": "IBS book opened a trade"}],
    )


def profile_of(*paths) -> Profile:
    return Profile(sources=[SourceCfg(id=path.stem, kind="feed", label=path.stem.title(), path=str(path))
                            for path in paths])


def test_a_later_sources_duplicate_ids_are_dropped_with_everything_that_hangs_off_them(tmp_path):
    first = feed_file(tmp_path, with_account(desk()), "desk.json")
    later = feed_file(tmp_path, household(), "household.json")
    snap = collect(profile_of(first, later), NOW)
    assert [(a.id, a.name) for a in snap.accounts] == [("brokerage", "Brokerage"), ("hsa", "HSA")]
    assert [h.symbol for h in snap.holdings] == ["VTI", "VXUS"]
    assert [(s.id, s.points[0].value) for s in snap.account_history] == [("brokerage", 5000.0), ("hsa", 100.0)]
    assert [(b.id, b.name) for b in snap.books] == [("swing-real", "Swing"), ("swing-paper", "Swing (paper)"),
                                                   ("ibs-paper", "IBS (paper)")]
    assert [(s.id, s.points[-1].value) for s in snap.book_history] == [("swing-real", 2150.0), ("ibs-paper", 100.0)]
    assert [p.symbol for p in snap.positions] == ["KO"]
    assert [t.symbol for t in snap.trades] == ["PG", "JNJ", "SPY"]
    assert snap.trade_charts == []
    assert [(s.id, s.name) for s in snap.strategies] == [("swing", "Swing pullbacks"), ("ibs", "Weak close")]
    assert [r.label for r in snap.runs] == ["Evening run", "Close entries", "Backup"]  # a run with no book stays
    assert [a.title for a in snap.alerts] == ["KO is near its stop", "IBS book opened a trade"]
    assert {s.id: s.detail for s in snap.sources} == {
        "desk": "1 account · 2 books · 1 strategy · 2 trades",
        "household": "2 accounts · 2 books · 2 strategies · 2 trades · ignored duplicate ids: brokerage, swing-real, "
                     "swing",
    }


def test_profile_order_decides_which_source_is_first(tmp_path):
    desk_path = feed_file(tmp_path, with_account(desk()), "desk.json")
    household_path = feed_file(tmp_path, household(), "household.json")
    snap = collect(profile_of(household_path, desk_path), NOW)
    assert [(a.id, a.name) for a in snap.accounts] == [("brokerage", "Joint brokerage"), ("hsa", "HSA")]
    assert [h.symbol for h in snap.holdings] == ["BND", "VXUS"]
    assert [(b.id, b.name) for b in snap.books] == [("swing-real", "Other swing"), ("ibs-paper", "IBS (paper)"),
                                                   ("swing-paper", "Swing (paper)")]
    assert [p.symbol for p in snap.positions] == ["XOM"]
    assert [t.symbol for t in snap.trades] == ["CVX", "SPY", "JNJ"]
    assert [c.symbol for c in snap.trade_charts] == ["CVX"]
    assert [r.label for r in snap.runs] == ["Other morning", "Close entries", "Backup"]
    assert [s.name for s in snap.strategies] == ["Someone else's swing", "Weak close"]
    assert {s.id: s.detail for s in snap.sources}["desk"] == (
        "1 account · 2 books · 1 strategy · 2 trades · ignored duplicate ids: brokerage, swing-real, swing")


def test_the_demo_left_in_next_to_a_feed_of_the_same_data_counts_once(tmp_path, capsysbinary):
    main(["demo", "--now", NOW.isoformat()])
    path = tmp_path / "copy.json"
    path.write_bytes(capsysbinary.readouterr().out)
    demo = collect(DEMO_PROFILE, NOW)
    feed = SourceCfg(id="copy", kind="feed", label="Copy", path=str(path))
    snap = collect(Profile(sources=[*DEMO_PROFILE.sources, feed]), NOW)
    for field in ("accounts", "holdings", "account_history", "books", "book_history", "positions", "trades",
                  "trade_charts", "strategies"):
        assert getattr(snap, field) == getattr(demo, field), field
    assert len(snap.runs) == len(demo.runs) + 2  # the two runs that belong to no book
    assert snap.sources[-1].detail == ("4 accounts · 5 books · 4 strategies · 136 trades · ignored duplicate ids: "
                                       "roth, brokerage, trading, savings, rsi2-real, and 8 more")
    reversed_order = collect(Profile(sources=[feed, *DEMO_PROFILE.sources]), NOW)
    assert [(s.id, s.detail) for s in reversed_order.sources][:2] == [
        ("copy", "4 accounts · 5 books · 4 strategies · 136 trades"),
        ("demo-portfolio", "ignored duplicate ids: roth, brokerage, trading, savings, rsi2-real, and 8 more"),
    ]  # the note goes on the later source's first row


def test_the_duplicate_note_shrinks_to_fit_the_row(tmp_path):
    # ten 35-char strategy ids: even five names plus "and N more" doesn't fit next to the source's own detail
    ids = [f"strategy-{i:02d}-{'x' * 23}" for i in range(10)]
    assert len(ids[0]) == 35
    payload = desk(books=[], book_history=[], positions=[], trades=[], trade_charts=[], runs=[],
                   strategies=[{"id": sid, "name": f"Strategy {i}"} for i, sid in enumerate(ids)])
    first = feed_file(tmp_path, payload, "first.json")
    later = feed_file(tmp_path, payload, "later.json")
    snap = collect(profile_of(first, later), NOW)
    detail = snap.sources[1].detail
    assert len(detail) <= DETAIL_LIMIT
    assert re.search(r"ignored duplicate ids: .*, and \d+ more$", detail)
    assert len(snap.strategies) == 10  # the first source's strategies win; none of the later source's survive


def test_duplicate_ids_within_one_source_keep_the_first_and_are_noted(tmp_path):
    payload = desk(books=[
        {"id": "x", "name": "First x", "money": "real", "strategy_id": "swing", "status": "running",
         "started": "2026-01-01", "value": 100.0},
        {"id": "x", "name": "Second x", "money": "paper", "strategy_id": "swing", "status": "running",
         "started": "2026-01-02", "value": 200.0},
    ])
    snap = collect(profile_of(feed_file(tmp_path, payload)), NOW)
    assert [(b.id, b.name) for b in snap.books] == [("x", "First x")]
    assert "ignored duplicate ids: x" in snap.sources[0].detail


def test_two_histories_of_one_id_keep_the_first_on_every_page(tmp_path):
    first = {"id": "swing-real", "points": [{"date": "2026-09-24", "value": 2131.4},
                                            {"date": "2026-09-25", "value": 2150.0}]}
    second = {"id": "swing-real", "points": [{"date": "2026-09-17", "value": 900.0},
                                             {"date": "2026-09-18", "value": 1000.0}]}
    within = profile_of(feed_file(tmp_path, desk(book_history=[first, second]), "within.json"))
    # across sources: the later one has no book of that id to drop, only a second history for it
    later = desk(books=[], positions=[], trades=[], runs=[], alerts=[], strategies=[], book_history=[second])
    across = profile_of(feed_file(tmp_path, desk(book_history=[first]), "desk.json"),
                        feed_file(tmp_path, later, "later.json"))
    for profile in (within, across):
        snap = collect(profile, NOW)
        home = home_view(snap, profile, NOW)
        strategy = strategy_view(snap, profile, NOW, "swing", "real")
        seen = ({row.id: row.day_change for row in home.books}["swing-real"],
                [d.isoformat() for d in strategy.slots.days])
        assert seen == (18.6, ["2026-09-24", "2026-09-25"]), profile.sources[-1].id


def plan_only(**blocks) -> dict:
    """A feed with only the plan and research blocks: no books, strategies or trades of its own to collide."""
    return desk(books=[], book_history=[], positions=[], trades=[], strategies=[], runs=[], alerts=[], **blocks)


TARGET = {"id": "roth-vti", "label": "VTI", "symbols": ["VTI"], "target": 60.0}
THESIS = {"symbol": "KO", "health": "ok"}
EVENT = {"date": "2026-10-21", "symbol": "KO", "kind": "earnings", "title": "Third-quarter results"}
GOAL = {"id": "house", "label": "House deposit", "target": 60000.0}
EXPOSURE = {"symbol": "MSFT", "value": 900.0}
BACKTEST = {"id": "dip-a1", "name": "Dip buy", "verdict": "pass", "at": MADE}
FIRST = plan_only(targets=[TARGET], theses=[THESIS], events=[EVENT], goals=[GOAL], exposures=[EXPOSURE],
                  backtests=[BACKTEST])


def seen(snap) -> dict:
    return {"targets": [(t.id, t.target) for t in snap.targets], "theses": [(t.symbol, t.health) for t in snap.theses],
            "events": [(e.kind, e.detail) for e in snap.events], "goals": [(g.id, g.target) for g in snap.goals],
            "exposures": [(e.symbol, e.value) for e in snap.exposures],
            "backtests": [(b.id, b.verdict) for b in snap.backtests]}


def test_duplicate_new_block_ids_first_source_wins(tmp_path):
    later = plan_only(
        targets=[{**TARGET, "target": 70.0}, {**TARGET, "id": "roth-bnd", "label": "BND", "symbols": ["BND"]}],
        theses=[{**THESIS, "health": "alert"}, {"symbol": "PG"}],
        # the same (date, kind, symbol, title) is the same event whatever its detail; another kind is another event
        events=[{**EVENT, "detail": "after the close"}, {**EVENT, "kind": "dividend"}],
        goals=[{**GOAL, "target": 1.0}], exposures=[{**EXPOSURE, "value": 1.0}],
        backtests=[{**BACKTEST, "verdict": "fail"}])
    snap = collect(profile_of(feed_file(tmp_path, FIRST, "desk.json"), feed_file(tmp_path, later, "notebook.json")),
                   NOW)
    assert seen(snap) == {
        "targets": [("roth-vti", 60.0), ("roth-bnd", 60.0)], "theses": [("KO", "ok"), ("PG", "none")],
        "events": [("earnings", ""), ("dividend", "")], "goals": [("house", 60000.0)],
        "exposures": [("MSFT", 900.0)], "backtests": [("dip-a1", "pass")],
    }
    # the target id and the thesis symbol are named, and the goal, exposure and backtest too; an event has no id
    assert {s.id: s.detail for s in snap.sources} == {
        "desk": "0 books · 0 strategies · 0 trades",
        "notebook": "0 books · 0 strategies · 0 trades · ignored duplicate ids: roth-vti, KO, house, MSFT, dip-a1",
    }


def test_duplicate_new_block_items_within_one_source_keep_the_first(tmp_path):
    payload = plan_only(targets=[TARGET, {**TARGET, "target": 70.0}], theses=[THESIS, {**THESIS, "health": "alert"}],
                        events=[EVENT, {**EVENT, "detail": "after the close"}], goals=[GOAL, {**GOAL, "target": 1.0}],
                        exposures=[EXPOSURE, {**EXPOSURE, "value": 1.0}],
                        backtests=[BACKTEST, {**BACKTEST, "verdict": "fail"}])
    snap = collect(profile_of(feed_file(tmp_path, payload)), NOW)
    assert seen(snap) == seen(collect(profile_of(feed_file(tmp_path, FIRST, "first.json")), NOW))
    assert snap.sources[0].detail == ("0 books · 0 strategies · 0 trades · ignored duplicate ids: roth-vti, KO, house, "
                                      "MSFT, dip-a1")
