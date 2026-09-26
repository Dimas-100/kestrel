import datetime as dt
import os
import sqlite3
from zoneinfo import ZoneInfo

import pytest
from fdc_fixture import Warehouse, d, household

from kestrel.connectors import collect
from kestrel.connectors.base import ConnectorError
from kestrel.connectors.fdc import FdcConnector, category_of, connect, institution_text, slug, type_text
from kestrel.profile import BenchmarkCfg, Profile, SourceCfg, load_profile

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
NY = ZoneInfo("America/New_York")


def connector(path, **options):
    return FdcConnector("portfolio", "Portfolio", path, **options)


@pytest.fixture
def warehouse(tmp_path):
    return household(tmp_path)


def test_no_file_is_an_error_and_sqlite_never_creates_one(tmp_path):
    path = tmp_path / "data" / "warehouse.db"
    with pytest.raises(ConnectorError, match=r"^no warehouse at .*warehouse\.db$"):
        connector(path).snapshot(NOW)
    assert not path.parent.exists()


@pytest.mark.parametrize("gone", ["holdings_daily", "positions_latest"])
def test_a_missing_table_or_view_names_itself_and_the_fix(tmp_path, gone):
    path = Warehouse(tmp_path / "w.db", without=(gone,)).close()
    with pytest.raises(ConnectorError) as error:
        connector(path).snapshot(NOW)
    assert str(error.value) == f"this warehouse is missing {gone}: update financial-data-collector and run `fdc sync`"


def test_an_old_schema_version_is_refused(tmp_path):
    path = Warehouse(tmp_path / "w.db", version=2).close()
    with pytest.raises(ConnectorError) as error:
        connector(path).snapshot(NOW)
    assert str(error.value) == ("this warehouse is at schema version 2 and kestrel needs 3: "
                                "update financial-data-collector and run `fdc sync`")


def test_an_empty_file_or_another_kind_of_file_is_not_a_warehouse(tmp_path):
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    with pytest.raises(ConnectorError, match="empty.db is not a financial-data-collector warehouse"):
        connector(empty).snapshot(NOW)
    notes = tmp_path / "notes.db"
    notes.write_text("shopping list\n" * 200, encoding="utf-8")
    with pytest.raises(ConnectorError, match="^the warehouse couldn't be read: file is not a database$"):
        connector(notes).snapshot(NOW)


def test_the_connection_is_read_only_and_a_snapshot_leaves_the_file_untouched(warehouse):
    before = warehouse.read_bytes()
    with connect(warehouse) as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("INSERT INTO accounts (label, first_seen) VALUES ('Mallory', '2026-01-02')")
    connector(warehouse).snapshot(NOW)
    assert warehouse.read_bytes() == before
    assert os.listdir(warehouse.parent) == ["warehouse.db"]  # not even a journal left behind


def test_a_warehouse_locked_mid_sync_is_an_error_and_the_next_read_recovers(warehouse):
    writer = sqlite3.connect(warehouse)
    writer.execute("BEGIN EXCLUSIVE")  # a sync holding the whole file, as an older journal mode does
    try:
        with pytest.raises(ConnectorError, match="^the warehouse couldn't be read: database is locked$"):
            connector(warehouse, timeout=0.1).snapshot(NOW)
    finally:
        writer.rollback()
        writer.close()
    assert len(connector(warehouse).snapshot(NOW).accounts) == 5


def test_a_sync_in_progress_on_a_wal_warehouse_reads_the_last_committed_data(tmp_path):
    path = household(tmp_path, wal=True)  # the collector's own journal mode
    writer = sqlite3.connect(path)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("DELETE FROM accounts WHERE label = 'Alex Crypto'")
    try:
        assert len(connector(path, timeout=0.1).snapshot(NOW).accounts) == 5
    finally:
        writer.rollback()
        writer.close()


def test_a_folder_with_spaces_a_hash_and_a_percent_in_its_name_still_opens(tmp_path):
    folder = tmp_path / "Alex money #1 at 100%"
    folder.mkdir()
    assert len(connector(household(folder)).snapshot(NOW).accounts) == 5


def test_ids_are_slugs_of_labels_and_a_clash_gets_a_number(tmp_path):
    w = Warehouse(tmp_path / "w.db")
    for label in ["Alex Brokerage", "alex brokerage!", "Épargne · Alex", "★ ★ ★", "—", "Alex  Brokerage 2"]:
        w.account(label)
    accounts = connector(w.close()).snapshot(NOW).accounts
    assert [a.id for a in accounts] == [
        "alex-brokerage", "alex-brokerage-2", "epargne-alex", "account", "account-2", "alex-brokerage-2-2"]
    assert accounts[2].name == "Épargne · Alex"
    assert slug("Alex's 401(k)") == "alex-s-401-k"


def test_names_institutions_and_types_read_the_way_a_person_writes_them(warehouse):
    accounts = connector(warehouse).snapshot(NOW).accounts
    assert [(a.id, a.institution, a.account_type) for a in accounts] == [
        ("alex-roth-ira", "Fidelity", "Roth IRA"), ("alex-brokerage", "Fidelity", "Brokerage"),
        ("alex-trading", "Webull", "Brokerage"), ("alex-crypto", "Coinbase", "Crypto"),
        ("alex-old-401k", "Fidelity", "401(k)")]
    assert [institution_text(c) for c in ["unknown", "charles_schwab"]] == ["", "Charles Schwab"]
    assert [type_text(c) for c in ["traditional_ira", "sep_ira", "joint_tenants", "other"]] == [
        "Traditional IRA", "SEP IRA", "Joint Tenants", "Other"]


def test_categories_come_from_the_type_unless_the_profile_names_the_account(warehouse):
    by_type = connector(warehouse).snapshot(NOW)
    assert {a.id: a.category for a in by_type.accounts} == {
        "alex-roth-ira": "long_term", "alex-brokerage": "long_term", "alex-trading": "long_term",
        "alex-crypto": "other", "alex-old-401k": "long_term"}
    assert [category_of(t) for t in ["hsa", "checking", "money_market", "crypto", "joint"]] == [
        "long_term", "cash", "cash", "other", "other"]
    mapped = connector(warehouse, categories={
        "alex-trading": "trading", "Alex Crypto": "cash", "alex-crypto": "trading", "brokerage-9": "cash",
    }).snapshot(NOW)
    categories = {a.id: a.category for a in mapped.accounts}
    assert (categories["alex-trading"], categories["alex-crypto"]) == ("trading", "trading")  # an id outranks a label
    assert mapped.sources[0].detail.endswith("no account matches categories 'brokerage-9'")


def test_value_and_cash_come_from_the_latest_snapshot_at_the_us_close(warehouse):
    accounts = {a.id: a for a in connector(warehouse).snapshot(NOW).accounts}
    assert (accounts["alex-brokerage"].value, accounts["alex-brokerage"].cash) == (4500.0, 500.0)
    assert (accounts["alex-trading"].value, accounts["alex-trading"].cash) == (550.0, -200.0)  # a margin debit
    assert accounts["alex-brokerage"].as_of == dt.datetime(2026, 9, 25, 16, 0, tzinfo=NY)
    assert accounts["alex-old-401k"].value == 0.0


def test_last_success_is_the_latest_good_derive_run(tmp_path, warehouse):
    source = connector(warehouse).snapshot(NOW).sources[0]
    assert (source.id, source.label, source.kind, source.status) == ("portfolio", "Portfolio", "fdc", "ok")
    assert source.last_success == dt.datetime(2026, 9, 25, 12, 5, tzinfo=dt.timezone.utc)
    w = Warehouse(tmp_path / "other.db")
    w.run("prices", "ok", "2026-09-24T08:00:00")  # no offset: UTC
    w.run("derive", "error", "2026-09-25T08:00:00Z")
    assert connector(w.close()).snapshot(NOW).sources[0].last_success == dt.datetime(2026, 9, 24, 8,
                                                                                     tzinfo=dt.timezone.utc)
    never = connector(Warehouse(tmp_path / "never.db").close()).snapshot(NOW).sources[0]
    assert (never.last_success, never.status) == (None, "stale")


def test_the_newer_of_the_snapshot_and_the_history_sets_the_value_and_a_tie_goes_to_the_snapshot(warehouse):
    accounts = {a.id: a for a in connector(warehouse).snapshot(NOW).accounts}
    roth = accounts["alex-roth-ira"]  # a snapshot on Thu 24, history to Fri 25
    assert (roth.value, roth.cash, roth.as_of) == (8700.0, 150.0, dt.datetime(2026, 9, 25, 16, 0, tzinfo=NY))
    assert (accounts["alex-brokerage"].value, accounts["alex-brokerage"].cash) == (4500.0, 500.0)  # both on Fri 25
    assert (accounts["alex-crypto"].value, accounts["alex-crypto"].cash) == (320.0, 0.0)  # history only


def test_history_adds_holdings_and_cash_by_day_and_files_each_flow_under_a_history_day(warehouse):
    history = {s.id: s.points for s in connector(warehouse).snapshot(NOW).account_history}
    assert list(history) == ["alex-roth-ira", "alex-brokerage", "alex-crypto"]  # a snapshot-only account has none
    roth = history["alex-roth-ira"]
    assert [(p.date.day, p.value) for p in roth] == [
        (16, 7950.0), (17, 8000.0), (18, 8050.0), (21, 8600.0), (22, 8420.0), (23, 8330.0), (24, 8650.0), (25, 8700.0)]
    # Tue 15 lands on the first point and Saturday's deposit on Monday; a withdrawal is always out; a reversed
    # contribution counts against; a transfer keeps its sign; dividends are growth; Sat 26 is after the last point
    assert [p.net_flow for p in roth] == [100.0, 0.0, 0.0, 500.0, -200.0, -100.0, 300.0, -50.0]
    assert [p.value for p in history["alex-crypto"]] == [300.0, 310.0, 320.0]


def test_holdings_come_from_each_accounts_latest_snapshot(warehouse):
    snap = connector(warehouse).snapshot(NOW)
    assert [(h.account_id, h.symbol, h.name, h.quantity, h.price, h.value, h.cost_basis) for h in snap.holdings] == [
        ("alex-roth-ira", "SPY", "S&P 500 index fund", 10.0, 600.0, 6000.0, 5000.0),
        ("alex-roth-ira", "AGG", "Bond index fund", 20.0, 100.0, 2000.0, 2100.0),
        ("alex-brokerage", "SPY", "S&P 500 index fund", 5.0, 600.0, 3000.0, 2500.0),
        ("alex-brokerage", "MSFT", "Microsoft", 2.0, 500.0, 1000.0, None),  # no price: its value over its quantity
        ("alex-trading", "AAPL", "Apple", 3.0, 250.0, 750.0, 700.0),
    ]  # and Walt Disney had no market value, so it is left out and counted


def test_the_benchmark_comes_from_the_warehouses_prices_over_the_accounts_history(warehouse):
    snap = connector(warehouse, benchmark=BenchmarkCfg(symbol="SPY", label="S&P 500")).snapshot(NOW)
    assert snap.benchmark is not None and (snap.benchmark.symbol, snap.benchmark.label) == ("SPY", "S&P 500")
    assert [(p.date.day, p.value) for p in snap.benchmark.points][:2] == [(16, 595.0), (17, 597.0)]
    assert snap.benchmark.points[-1].value == 603.0
    other = connector(warehouse, benchmark=BenchmarkCfg(symbol="QQQ", label="Nasdaq 100")).snapshot(NOW)
    assert other.benchmark is None
    assert other.sources[0].detail == ("5 accounts · 5 holdings · prices to 25 Sep · 1 holding left out "
                                       "(no market value) · no QQQ prices in the warehouse")


def test_a_closed_account_at_zero_with_no_holdings_is_still_listed(warehouse):
    snap = connector(warehouse).snapshot(NOW)
    old = next(a for a in snap.accounts if a.id == "alex-old-401k")
    assert (old.value, old.cash, old.as_of.date()) == (0.0, 0.0, d(21))
    assert [h for h in snap.holdings if h.account_id == old.id] == []
    assert old.id not in {s.id for s in snap.account_history}


def test_a_margin_debit_is_negative_cash_and_the_value_nets_it(warehouse):
    snap = connector(warehouse).snapshot(NOW)
    trading = next(a for a in snap.accounts if a.id == "alex-trading")
    held = sum(h.value for h in snap.holdings if h.account_id == trading.id)
    assert (held, trading.cash, trading.value) == (750.0, -200.0, 550.0)


def test_an_empty_warehouse_is_a_source_with_nothing_in_it_yet(tmp_path):
    snap = connector(Warehouse(tmp_path / "w.db").close(), benchmark=BenchmarkCfg()).snapshot(NOW)
    assert (snap.accounts, snap.holdings, snap.account_history, snap.benchmark) == ([], [], [], None)
    assert snap.sources[0].detail == "0 accounts · 0 holdings · no prices yet · no SPY prices in the warehouse"


def test_a_profile_reads_its_warehouse_relative_to_its_own_folder(tmp_path, monkeypatch):
    (tmp_path / "collector").mkdir()
    household(tmp_path / "collector")
    (tmp_path / "kestrel").mkdir()
    (tmp_path / "kestrel" / "profile.toml").write_text(
        '[[sources]]\nid = "portfolio"\nkind = "fdc"\nlabel = "Portfolio"\npath = "../collector/warehouse.db"\n'
        '[sources.categories]\n"Alex Trading" = "trading"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path / "collector")  # anywhere but the profile's folder
    profile, _ = load_profile(tmp_path / "kestrel" / "profile.toml")
    snap = collect(profile, NOW)
    assert [(s.label, s.kind, s.status) for s in snap.sources] == [("Portfolio", "fdc", "ok")]
    assert {a.id: a.category for a in snap.accounts}["alex-trading"] == "trading"
    assert snap.benchmark is not None and snap.benchmark.label == "S&P 500"


def test_a_broken_source_is_a_red_row_and_the_rest_still_arrives(tmp_path):
    profile = Profile(sources=[
        SourceCfg(id="demo", kind="demo"),
        SourceCfg(id="portfolio", kind="fdc", label="Portfolio", path=str(tmp_path / "nope.db")),
        SourceCfg(id="unset", kind="fdc"),
    ])
    snap = collect(profile, NOW)
    errors = {s.id: s.detail for s in snap.sources if s.status == "error"}
    assert errors["portfolio"] == f"no warehouse at {tmp_path / 'nope.db'}"
    assert errors["unset"].startswith("an fdc source needs a path to the warehouse")
    assert len(snap.accounts) == 4  # the demo still arrived
