import datetime as dt
import os
import sqlite3
from zoneinfo import ZoneInfo

import pytest
from fdc_fixture import Warehouse, household

from kestrel.connectors.base import ConnectorError
from kestrel.connectors.fdc import FdcConnector, category_of, connect, institution_text, slug, type_text

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
