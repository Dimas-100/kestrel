import datetime as dt
import shutil
from pathlib import Path

import pytest

from kestrel.connectors import build, collect
from kestrel.connectors.base import ConnectorError
from kestrel.connectors.rails import RailsConnector
from kestrel.contract import ValuePoint
from kestrel.profile import Profile, SourceCfg

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures" / "rails"


def connector(folder: Path) -> RailsConnector:
    return RailsConnector("rails", "Paper (trading-rails)", folder)


def test_a_missing_folder_is_a_readable_error(tmp_path):
    with pytest.raises(ConnectorError, match="no trading-rails data at"):
        connector(tmp_path / "nope").snapshot(NOW)


def test_a_missing_paper_json_is_a_readable_error(tmp_path):
    with pytest.raises(ConnectorError, match="no paper.json in"):
        connector(tmp_path).snapshot(NOW)


def test_torn_paper_json_is_a_readable_error(tmp_path):
    (tmp_path / "paper.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ConnectorError, match="isn't valid JSON"):
        connector(tmp_path).snapshot(NOW)


def test_a_paper_json_that_is_not_an_object_is_a_readable_error(tmp_path):
    (tmp_path / "paper.json").write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ConnectorError, match="isn't a paper account"):
        connector(tmp_path).snapshot(NOW)


@pytest.fixture
def fixture_snapshot():
    return connector(FIXTURES).snapshot(NOW)


def test_the_book_is_one_paper_book_priced_from_the_latest_known_price(fixture_snapshot):
    assert [b.id for b in fixture_snapshot.books] == ["rails-paper"]
    book = fixture_snapshot.books[0]
    assert (book.name, book.money, book.strategy_id) == ("Paper (trading-rails)", "paper", "rails")
    assert book.started == dt.date(2026, 9, 20)  # the first run's date, not the state's as_of (09-21)
    # cash 8000 + ACME 10 @ 27.50 (its latest fill) + GLOBEX 5 @ 40.00 (its only fill) + INITCO 3 @ 100.00 (avg cost:
    # it has no fill at all)
    assert book.value == pytest.approx(8000.0 + 275.0 + 200.0 + 300.0)


def test_positions_carry_their_latest_fill_price_opened_date_and_any_resting_stop(fixture_snapshot):
    by_symbol = {p.symbol: p for p in fixture_snapshot.positions}
    assert set(by_symbol) == {"ACME", "GLOBEX", "INITCO"}
    acme = by_symbol["ACME"]
    assert (acme.quantity, acme.entry_price, acme.last_price, acme.stop_price) == (10, 25.0, 27.5, 22.5)
    assert acme.opened == dt.date(2026, 9, 18)  # its earliest BUY fill
    globex = by_symbol["GLOBEX"]
    assert (globex.last_price, globex.stop_price) == (40.0, None)
    initco = by_symbol["INITCO"]
    assert initco.last_price == 100.0  # no fill at all: falls back to its average cost
    assert initco.opened == dt.date(2026, 9, 20)  # no BUY fill either: falls back to the book's started date


def test_a_strategy_stub_is_named_from_the_run_log_or_rails_when_it_names_none(fixture_snapshot):
    assert [s.id for s in fixture_snapshot.strategies] == ["rails"]
    strategy = fixture_snapshot.strategies[0]
    assert (strategy.name, strategy.summary) == ("trading-rails", "From trading-rails")


def test_a_run_is_done_or_failed_when_one_of_its_steps_errored(fixture_snapshot):
    runs = fixture_snapshot.runs
    assert [(r.time.date(), r.status) for r in runs] == [
        (dt.date(2026, 9, 20), "done"), (dt.date(2026, 9, 21), "failed")]
    assert all(r.book_id == "rails-paper" for r in runs)
    assert runs[1].detail == "ConnectionError: broker unreachable"  # the failing step's own message
    # a torn last line in the fixture (a crash mid-write) never becomes a third run
    assert len(runs) == 2


def test_the_source_row_reports_the_newest_runs_time(fixture_snapshot):
    source = fixture_snapshot.sources[0]
    assert (source.kind, source.status) == ("rails", "ok")
    assert source.last_success == dt.datetime(2026, 9, 21, 9, 5, tzinfo=dt.timezone.utc)


def test_book_history_picks_up_an_equity_point_when_a_run_row_reports_one(fixture_snapshot):
    # today's real runner never sends one; the fixture's first row does, to prove the hook works when a future one does
    history = {s.id: s.points for s in fixture_snapshot.book_history}
    assert history["rails-paper"] == [ValuePoint(date=dt.date(2026, 9, 20), value=8770.5)]


def test_a_missing_run_log_falls_back_to_the_state_files_as_of_date(tmp_path):
    shutil.copy(FIXTURES / "paper.json", tmp_path / "paper.json")
    snap = connector(tmp_path).snapshot(NOW)
    assert snap.books[0].started == dt.date(2026, 9, 21)  # the state's own as_of: there is no run log to ask instead
    assert snap.runs == []
    assert snap.sources[0].last_success is None and snap.sources[0].status == "stale"


def test_an_empty_state_still_produces_a_valid_book(tmp_path):
    (tmp_path / "paper.json").write_text("{}", encoding="utf-8")
    snap = connector(tmp_path).snapshot(NOW)
    assert snap.books[0].value == 0.0
    assert snap.positions == []


def test_build_wires_the_rails_kind_and_a_missing_path_is_a_readable_error():
    cfg = SourceCfg(id="rails", kind="rails", label="Paper (trading-rails)", path=str(FIXTURES))
    made = build(cfg, Profile(sources=[cfg]))
    assert isinstance(made, RailsConnector) and made.folder == FIXTURES
    with pytest.raises(ConnectorError, match="needs a path"):
        build(SourceCfg(id="rails", kind="rails"), Profile())


def test_a_rails_source_with_no_path_shows_as_a_source_error_not_a_profile_problem():
    # `kestrel check` reads a profile problem and a source error very differently (exit 2 before anything is read,
    # vs. exit 1 with the rest of the page still working) — a missing path is the connector's business, like fdc's
    profile = Profile(sources=[SourceCfg(id="rails", kind="rails")])
    snap = collect(profile, NOW)
    assert snap.sources[0].status == "error" and "needs a path" in snap.sources[0].detail
