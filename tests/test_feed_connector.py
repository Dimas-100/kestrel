import datetime as dt
import json
import os

import pytest
from feed_fixture import MADE, desk, feed_file

from kestrel.cli import main
from kestrel.connectors.base import ConnectorError
from kestrel.connectors.feed import MAX_BYTES, FeedConnector
from kestrel.contract import Snapshot

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


def from_file(path):
    return FeedConnector("desk", "Trading desk", path=path).snapshot(NOW)


def refused(path) -> str:
    with pytest.raises(ConnectorError) as error:
        from_file(path)
    return str(error.value)


def test_a_valid_payload_from_a_file_keeps_every_list_and_the_benchmark_and_only_reads(tmp_path):
    path = feed_file(tmp_path)
    before = path.read_bytes()
    snap = from_file(path)
    expected = Snapshot.model_validate(desk())
    assert snap.model_dump(exclude={"sources"}) == expected.model_dump(exclude={"sources"})
    assert snap.benchmark is not None and snap.benchmark.symbol == "SPY"
    assert path.read_bytes() == before and os.listdir(tmp_path) == ["feed.json"]


def test_the_payloads_sources_are_replaced_by_one_row_for_the_feed(tmp_path):
    snap = from_file(feed_file(tmp_path))
    assert [s.model_dump() for s in snap.sources] == [{
        "id": "desk", "label": "Trading desk", "kind": "feed", "last_success": dt.datetime.fromisoformat(MADE),
        "status": "ok", "detail": "2 books · 1 strategy · 2 trades",
    }]


def test_alerts_pass_through_and_can_only_link_inside_kestrel(tmp_path):
    snap = from_file(feed_file(tmp_path))
    assert [(a.level, a.title, a.link) for a in snap.alerts] == [
        ("warning", "KO is near its stop", "/strategies/swing")]
    outside = desk(alerts=[{"level": "serious", "title": "Sign in again", "link": "https://desk.example.com/login"}])
    assert refused(feed_file(tmp_path, outside)).startswith("alerts.0.link: String should match pattern")


def test_kestrel_demo_prints_a_payload_a_feed_can_read(tmp_path, capsysbinary):
    main(["demo", "--now", NOW.isoformat()])
    path = tmp_path / "demo.json"
    path.write_bytes(capsysbinary.readouterr().out)
    snap = from_file(path)
    assert snap.sources[0].detail == "4 accounts · 5 books · 4 strategies · 136 trades"
    assert [a.id for a in snap.accounts] == ["roth", "brokerage", "trading", "savings"]


def test_a_byte_order_mark_is_fine(tmp_path):
    path = tmp_path / "feed.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(desk()).encode("utf-8"))
    assert len(from_file(path).books) == 2


def test_a_missing_file_is_named(tmp_path):
    assert refused(tmp_path / "nope.json") == f"no feed file at {tmp_path / 'nope.json'}"
    assert refused(tmp_path) == f"no feed file at {tmp_path}"  # a folder is not a feed file


def test_a_file_over_20_mb_is_refused_and_20_mb_exactly_is_read(tmp_path):
    body = json.dumps(desk()).encode("utf-8")
    path = tmp_path / "feed.json"
    path.write_bytes(body + b" " * (MAX_BYTES - len(body)))
    assert len(from_file(path).books) == 2
    path.write_bytes(body + b" " * (MAX_BYTES - len(body) + 1))
    assert refused(path) == "the feed file is more than 20 MB"


@pytest.mark.parametrize("body,why", [
    (b"", "(line 1, column 1: Expecting value)"),
    (b"{'books': []}", "(line 1, column 2: Expecting property name enclosed in double quotes)"),
    ('{"note": "café"}'.encode("latin-1"), "(it isn't UTF-8 text)"),
    (b"[" * 100_000, "(it is nested too deeply to read)"),
], ids=["empty", "single quotes", "latin-1", "nested"])
def test_something_that_isnt_json_is_refused(tmp_path, body, why):
    path = tmp_path / "feed.json"
    path.write_bytes(body)
    assert refused(path) == f"the feed sent something that isn't JSON {why}"


def test_a_web_page_such_as_a_sign_in_page_is_named(tmp_path):
    path = tmp_path / "feed.json"
    path.write_bytes(b"\n  <!DOCTYPE html>\n<html><head><title>Sign in</title></head><body><form></form></body></html>")
    assert refused(path) == ("the feed sent something that isn't JSON: "
                             "a web page (a sign-in page, or the wrong address?)")


@pytest.mark.parametrize("version", ["2", "2.0", "0"])
def test_another_major_version_is_refused_with_the_contracts_own_message(tmp_path, version):
    message = refused(feed_file(tmp_path, desk(contract_version=version, books="not even a list")))
    assert message == f"unsupported contract version {version!r}; this kestrel reads major version 1"


def test_a_newer_minor_version_loads_and_a_payload_must_say_its_version(tmp_path):
    assert len(from_file(feed_file(tmp_path, desk(contract_version="1.4", extra_field={"a": 1}))).books) == 2
    payload = desk()
    del payload["contract_version"]
    assert refused(feed_file(tmp_path, payload)) == (
        "the feed doesn't say which contract it speaks: add \"contract_version\": \"1\"")


def test_a_validation_error_lists_the_first_three_problems_then_how_many_more(tmp_path):
    payload = desk()
    payload["books"][0]["money"] = "cash"
    payload["books"][1]["value"] = "lots"
    del payload["trades"][0]["pnl"]
    payload["trades"][1]["closed"] = "soon"
    payload["runs"][0]["status"] = "maybe"
    assert refused(feed_file(tmp_path, payload)) == (
        "books.0.money: Input should be 'real' or 'paper'; "
        "books.1.value: Input should be a valid number, unable to parse string as a number; "
        "trades.0.pnl: Field required; and 2 more")


def test_problems_too_long_for_a_source_row_are_fewer_but_still_counted(tmp_path):
    chart = {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08", "stop": "x",
             "bars": [{"date": "2026-09-08", "open": "x", "high": 159.0, "low": 157.9, "close": 158.4}]}
    payload = desk(trade_charts=[chart])
    payload["runs"][0]["status"] = "maybe"
    message = refused(feed_file(tmp_path, payload))
    assert message == (
        "trade_charts.0.bars.0.open: Input should be a valid number, unable to parse string as a number; "
        "trade_charts.0.stop: Input should be a valid number, unable to parse string as a number; and 1 more")
    assert len(message) <= 200  # what a source row keeps of an error


def test_not_a_json_object_is_a_problem_of_the_whole_payload(tmp_path):
    assert refused(feed_file(tmp_path, [desk()])) == "Input should be a valid dictionary or instance of Snapshot"


def test_a_payload_from_the_future_is_refused_beyond_five_minutes_of_clock_drift(tmp_path):
    drift = from_file(feed_file(tmp_path, desk(generated_at="2026-09-25T21:12:00+00:00")))
    assert drift.sources[0].last_success == NOW  # four minutes ahead: this computer's clock is the one shown
    ahead = desk(generated_at="2026-09-25T21:08:00-04:00")  # a local time given the wrong offset: 4 hours ahead
    assert refused(feed_file(tmp_path, ahead)) == (
        "the feed's generated_at is 4 hours ahead of this computer's clock: "
        "check the clock and time zone where the feed is made")
