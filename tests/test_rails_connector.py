import datetime as dt
import json
import shutil
from pathlib import Path

import pytest

from kestrel.connectors import build, collect
from kestrel.connectors.base import ConnectorError
from kestrel.connectors.rails import LOG_TAIL_LIMIT, RailsConnector
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


def test_closed_trades_are_matched_fifo_including_a_partial_close_and_two_buys_averaged(fixture_snapshot):
    by_symbol = {t.symbol: t for t in fixture_snapshot.trades}
    assert set(by_symbol) == {"ACME", "ZETA"}  # ORPHAN's sell matches no buy at all: skipped, not invented
    assert all(t.book_id == "rails-paper" for t in fixture_snapshot.trades)

    # a partial close: 3 of a 10-share lot bought at 25.00, sold at 27.50
    acme = by_symbol["ACME"]
    assert (acme.entry_price, acme.exit_price, acme.quantity) == (25.0, 27.5, 3)
    assert (acme.opened, acme.closed) == (dt.date(2026, 9, 18), dt.date(2026, 9, 20))
    assert acme.pnl == pytest.approx(7.5) and acme.return_pct == pytest.approx(10.0)  # (27.50-25.00)*3 / 75.00

    # two buys (4 @ 10.00, 6 @ 20.00) fully closed by one sell of 10 @ 25.00: entry is their weighted average
    zeta = by_symbol["ZETA"]
    assert zeta.entry_price == pytest.approx(16.0) and zeta.exit_price == 25.0 and zeta.quantity == 10
    assert (zeta.opened, zeta.closed) == (dt.date(2026, 9, 15), dt.date(2026, 9, 17))
    assert zeta.pnl == pytest.approx(90.0) and zeta.return_pct == pytest.approx(56.25)  # (250-160) / 160 * 100


def test_a_future_fill_with_commission_nets_it_out_of_pnl(tmp_path):
    # today's real fills never carry a commission (paper.py charges CostModel.commission but never persists it per
    # fill); a future format that does should still be read correctly
    state = {
        "cash": 0.0, "positions": {}, "open_orders": {}, "as_of": "2026-09-20",
        "fills": [
            {"client_order_id": "b1", "symbol": "FUT", "side": "BUY", "quantity": 10, "price": 10.0,
             "ts": "2026-09-18T00:00:00+00:00", "commission": 1.0},
            {"client_order_id": "s1", "symbol": "FUT", "side": "SELL", "quantity": 10, "price": 12.0,
             "ts": "2026-09-19T00:00:00+00:00", "commission": 1.0},
        ],
    }
    (tmp_path / "paper.json").write_text(json.dumps(state), encoding="utf-8")
    trade, = connector(tmp_path).snapshot(NOW).trades
    # proceeds 120.00 - cost 100.00 - both commissions (1.00 + 1.00) = 18.00
    assert trade.pnl == pytest.approx(18.0)


def test_the_run_log_is_read_only_from_its_tail_once_it_grows_past_the_cap(tmp_path, monkeypatch):
    shutil.copy(FIXTURES / "paper.json", tmp_path / "paper.json")
    path = tmp_path / "runs.jsonl"

    def row(ts: str, symbol: str, pad: int = 400) -> str:
        return json.dumps({"ts": ts, "symbol": symbol, "step": "signal", "status": "ok", "detail": "x" * pad,
                           "order": None, "extra": None})

    lines = [row("2000-01-01T00:00:00+00:00", "SENTINEL-OLD")]
    while sum(len(line) + 1 for line in lines) < LOG_TAIL_LIMIT + 100_000:
        lines.append(row("2010-06-01T00:00:00+00:00", "PAD"))
    lines.append(row("2026-09-24T00:00:00+00:00", "RECENT", pad=0))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert path.stat().st_size > LOG_TAIL_LIMIT

    read_sizes: list[int] = []
    real_open = Path.open

    def spy_open(self, *args, **kwargs):
        handle = real_open(self, *args, **kwargs)
        if self == path:
            original_read = handle.read

            def counted(*a, **k):
                data = original_read(*a, **k)
                read_sizes.append(len(data))
                return data
            handle.read = counted
        return handle

    monkeypatch.setattr(Path, "open", spy_open)
    snap = connector(tmp_path).snapshot(NOW)
    years = {r.time.year for r in snap.runs}
    assert 2000 not in years and 2026 in years  # the sentinel — the file's very first row — never entered the tail
    assert read_sizes and max(read_sizes) <= LOG_TAIL_LIMIT + 4096  # bounded near the cap, nowhere near the file


def test_a_non_utf8_run_log_is_a_readable_error(tmp_path):
    shutil.copy(FIXTURES / "paper.json", tmp_path / "paper.json")
    (tmp_path / "runs.jsonl").write_bytes(b"\xff\xfe\x00\x00not utf-8")
    with pytest.raises(ConnectorError, match="runs.jsonl.*isn't UTF-8 text"):
        connector(tmp_path).snapshot(NOW)


def test_an_unreadable_run_log_is_a_readable_error(tmp_path):
    shutil.copy(FIXTURES / "paper.json", tmp_path / "paper.json")
    (tmp_path / "runs.jsonl").write_text('{"ts": "2026-09-20T00:00:00+00:00"}\n', encoding="utf-8")

    class Locked(type(tmp_path)):
        def stat(self, *args, **kwargs):
            if self.name == "runs.jsonl":
                raise PermissionError(13, "Permission denied")
            return super().stat(*args, **kwargs)

    with pytest.raises(ConnectorError, match="runs.jsonl couldn't be read"):
        connector(Locked(tmp_path)).snapshot(NOW)


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
