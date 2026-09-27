import datetime as dt
import http.client
import json
import logging
import os
import ssl
import threading
import time

import pytest
from fastapi.testclient import TestClient
from feed_fixture import (
    MADE,
    FeedServer,
    RawServer,
    answer,
    chunk_size_trickle,
    chunked_cut_off,
    desk,
    feed_file,
    hang,
    hang_up,
    header_trickle,
    reset_midway,
    slow_head_then_body,
    tls_trickle,
    trailer_trickle,
    trickle,
)

from kestrel import __version__
from kestrel.cli import main
from kestrel.connectors import build, collect
from kestrel.connectors import feed as feed_module
from kestrel.connectors.base import ConnectorError
from kestrel.connectors.feed import MAX_BYTES, FeedConnector
from kestrel.contract import Snapshot
from kestrel.profile import Profile, SourceCfg, load_profile
from kestrel.server import create_app

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
TOKEN = "kst_9f8e7d6c5b4a3210"  # a made-up token


@pytest.fixture
def serve():
    servers = []

    def start(reply):
        server = FeedServer(reply)
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.close()


@pytest.fixture
def raw():
    servers = []

    def start(serve):
        server = RawServer(serve)
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.close()


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
    assert snap.sources[0].detail == "6 accounts · 5 books · 4 strategies · 136 trades"
    assert [a.id for a in snap.accounts] == ["roth", "brokerage", "trading", "savings", "checking", "card"]


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


@pytest.mark.parametrize("field,constant", [("positions", "NaN"), ("books", "Infinity"), ("books", "-Infinity")],
                         ids=["nan", "infinity", "-infinity"])
def test_nan_and_infinity_are_refused(tmp_path, field, constant):
    payload = desk()
    value = {"NaN": float("nan"), "Infinity": float("inf"), "-Infinity": float("-inf")}[constant]
    payload[field][0]["value" if field == "books" else "last_price"] = value
    path = tmp_path / "feed.json"
    path.write_text(json.dumps(payload), encoding="utf-8")  # json.dumps allows these by default; JSON itself doesn't
    assert refused(path) == f"the feed sent {constant}, which JSON doesn't allow"


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


def test_more_than_a_million_items_is_refused_before_any_is_checked(tmp_path):
    # pydantic collects every problem at once: 1.3 million empty books once took 7.5 GB to describe
    path = feed_file(tmp_path, desk(books=[{}] * 2_000_000))
    started = time.monotonic()
    assert refused(path) == "the feed sent more than 1,000,000 items"
    assert time.monotonic() - started < 5


def test_items_inside_items_count_toward_the_million(tmp_path):
    chart = {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08",
             "bars": [{"date": "2026-09-08", "open": 158.0, "high": 159.0, "low": 157.9, "close": 158.4}],
             "indicator": {"label": "RSI(2)", "values": [5.0] * 1_000_001}}
    assert refused(feed_file(tmp_path, desk(trade_charts=[chart]))) == "the feed sent more than 1,000,000 items"


def test_thousands_of_problems_are_counted_quickly(tmp_path):
    trade = {"bookId": "swing-real", "symbol": "PG", "opened": "2026-09-08", "closed": "2026-09-11",
             "entryPrice": 158.4, "exitPrice": 162.1, "quantity": 3, "pnl": 11.1, "returnPct": 2.34}  # camelCase
    path = feed_file(tmp_path, desk(trades=[trade] * 5000))
    started = time.monotonic()
    message = refused(path)
    assert time.monotonic() - started < 2
    assert message == ("trades.0.book_id: Field required; trades.0.entry_price: Field required; "
                       "trades.0.exit_price: Field required; and 19997 more")


def test_a_huge_list_inside_one_item_is_counted_quickly_too(tmp_path):
    # a million problems inside one chart: checking the chart whole once took seconds and gigabytes
    chart = {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08", "bars": [{}] * 200_000}
    path = feed_file(tmp_path, desk(trade_charts=[chart]))
    started = time.monotonic()
    message = refused(path)
    assert time.monotonic() - started < 2
    assert message == ("trade_charts.0.bars.0.date: Field required; trade_charts.0.bars.0.open: Field required; "
                       "trade_charts.0.bars.0.high: Field required; and 999997 more")


def test_a_long_history_loads_whole_and_its_problems_keep_their_places(tmp_path):
    points = [{"date": (dt.date(2006, 1, 2) + dt.timedelta(days=i)).isoformat(), "value": 100.0 + i}
              for i in range(5000)]
    payload = desk(book_history=[{"id": "swing-real", "points": points}])
    assert from_file(feed_file(tmp_path, payload)).book_history == Snapshot.model_validate(payload).book_history
    points[4321]["value"] = "x"
    payload["book_history"].append({"points": []})
    assert refused(feed_file(tmp_path, payload)) == (
        "book_history.0.points.4321.value: Input should be a valid number, unable to parse string as a number; "
        "book_history.1.id: Field required")
    bars = [{"date": "2026-09-08", "open": 158.0, "high": 159.0, "low": 157.9, "close": 158.4}] * 3000
    chart = {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08", "stop": "x",
             "bars": [*bars[:2500], {**bars[0], "open": "x"}, *bars[2501:]]}
    assert refused(feed_file(tmp_path, desk(trade_charts=[chart]))) == (
        "trade_charts.0.bars.2500.open: Input should be a valid number, unable to parse string as a number; "
        "trade_charts.0.stop: Input should be a valid number, unable to parse string as a number")


def test_the_demo_payload_loads_exactly_as_the_contract_reads_it(tmp_path, capsysbinary):
    main(["demo", "--now", NOW.isoformat()])
    body = capsysbinary.readouterr().out
    path = tmp_path / "demo.json"
    path.write_bytes(body)
    expected = Snapshot.model_validate_json(body)
    assert from_file(path).model_dump(exclude={"sources"}) == expected.model_dump(exclude={"sources"})


def raw_desk(field: str | None, key: str, raw: str) -> str:
    """The desk's payload, plus an account with two days of history, as JSON text with `raw` written as-is for
    `key` of the first item in `field` (or of the payload itself)."""
    payload = desk(accounts=[{"id": "desk-cash", "name": "Desk cash", "category": "trading", "value": 5000.0,
                              "as_of": "2026-09-25T20:00:00+00:00"}],
                   account_history=[{"id": "desk-cash", "points": [{"date": "2026-09-24", "value": 4900.0},
                                                                   {"date": "2026-09-25", "value": 5000.0}]}])
    (payload if field is None else payload[field][0])[key] = "__RAW__"
    return json.dumps(payload).replace('"__RAW__"', raw)


@pytest.mark.parametrize("field,key,raw,message", [
    ("runs", "time", '"0001-01-01T00:00:00Z"', "runs.0.time is 0001-01-01, outside 1970–2200"),
    (None, "generated_at", '"0001-01-01T00:00:00Z"', "generated_at is 0001-01-01, outside 1970–2200"),
    ("trades", "closed", '"9999-12-31"', "trades.0.closed is 9999-12-31, outside 1970–2200"),
    ("accounts", "value", "1e999", "the feed sent a number too large to use"),
    ("accounts", "value", "1e300", "accounts.0.value is too large"),
    ("accounts", "value", '"-inf"', "accounts.0.value is too large"),  # pydantic reads these strings as floats
    ("accounts", "value", '"NaN"', "accounts.0.value isn't a number"),
    ("books", "slots_total", "1" + "0" * 400, "books.0.slots_total is too large"),
    ("books", "value", "1" * 5000, "the feed sent a number too large to use"),
], ids=["Go's zero time in a run", "Go's zero time as generated_at", "the year 9999", "1e999", "1e300",
        "the string -inf", "the string NaN", "a 401-digit integer", "a 5000-digit integer"])
def test_a_date_or_number_the_pages_cant_use_is_refused_and_every_page_still_answers(tmp_path, field, key, raw,
                                                                                      message):
    path = tmp_path / "feed.json"
    path.write_text(raw_desk(field, key, raw), encoding="utf-8")
    profile = Profile(sources=[SourceCfg(id="demo", kind="demo", label="Demo data"),
                               SourceCfg(id="desk", kind="feed", label="Trading desk", path=str(path))])
    client = TestClient(create_app(profile, clock=lambda: NOW, web_dist=None), base_url="http://127.0.0.1",
                        raise_server_exceptions=False)
    codes = {page: client.get(page).status_code for page in ("/api/home", "/api/strategies", "/api/strategies/swing")}
    row = next(s for s in client.get("/api/shell").json()["sources"] if s["id"] == "desk")
    assert (row["status"], row["detail"]) == ("error", message)
    assert codes == {"/api/home": 200, "/api/strategies": 200, "/api/strategies/swing": 404}  # no desk, no swing


def test_the_payloads_own_sources_are_not_checked_since_they_are_replaced(tmp_path):
    # a Go system's source that has never succeeded says so with Go's zero time; kestrel drops that row anyway
    never = {"id": "desk-broker", "label": "Broker link", "kind": "api", "last_success": "0001-01-01T00:00:00Z"}
    assert len(from_file(feed_file(tmp_path, desk(sources=[never]))).books) == 2


def test_a_payload_from_the_future_is_refused_beyond_five_minutes_of_clock_drift(tmp_path):
    drift = from_file(feed_file(tmp_path, desk(generated_at="2026-09-25T21:12:00+00:00")))
    assert drift.sources[0].last_success == NOW  # four minutes ahead: this computer's clock is the one shown
    ahead = desk(generated_at="2026-09-25T21:08:00-04:00")  # a local time given the wrong offset: 4 hours ahead
    assert refused(feed_file(tmp_path, ahead)) == (
        "the feed's generated_at is 4 hours ahead of this computer's clock: "
        "check the clock and time zone where the feed is made")


def over_http(url, **options):
    return FeedConnector("desk", "Trading desk", url=url, **options).snapshot(NOW)


def refused_over_http(url, **options) -> str:
    with pytest.raises(ConnectorError) as error:
        over_http(url, **options)
    return str(error.value)


def test_a_valid_payload_over_http_is_one_plain_get_and_matches_the_file(tmp_path, serve):
    server = serve(answer(desk()))
    snap = over_http(server.url + "/api/feed")
    assert snap.model_dump() == from_file(feed_file(tmp_path)).model_dump()
    [request] = server.requests
    assert (request["method"], request["path"], request["accept"]) == ("GET", "/api/feed", "application/json")
    assert "authorization" not in request and "cookie" not in request


def test_the_token_goes_in_a_bearer_header_when_token_env_is_set(serve, monkeypatch):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", f"  {TOKEN}\n")  # the spaces and newline a .env line can leave
    server = serve(answer(desk()))
    over_http(server.url, token_env="KESTREL_TEST_TOKEN")
    assert server.requests[0]["authorization"] == f"Bearer {TOKEN}"


def test_a_missing_or_empty_token_variable_is_an_error_that_names_it(serve, monkeypatch):
    server = serve(answer(desk()))
    monkeypatch.delenv("KESTREL_TEST_TOKEN", raising=False)
    assert refused_over_http(server.url, token_env="KESTREL_TEST_TOKEN") == (
        "set KESTREL_TEST_TOKEN in the environment (token_env)")
    monkeypatch.setenv("KESTREL_TEST_TOKEN", "   ")
    assert refused_over_http(server.url, token_env="KESTREL_TEST_TOKEN") == (
        "set KESTREL_TEST_TOKEN in the environment (token_env)")
    assert server.requests == []  # nothing is sent without it


def test_a_token_a_header_cant_carry_is_refused_without_showing_it(serve, monkeypatch):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", f"{TOKEN}\r\nX-Extra: 1")
    server = serve(answer(desk()))
    message = refused_over_http(server.url, token_env="KESTREL_TEST_TOKEN")
    assert message == ("the token in KESTREL_TEST_TOKEN has a character a header can't carry "
                       "(a space or a line break?)")
    assert server.requests == []


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_a_redirect_is_refused_and_the_token_never_follows_it(serve, monkeypatch, code):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", TOKEN)
    elsewhere = serve(answer(desk()))
    server = serve(answer(b"", status=code, headers={"Location": f"{elsewhere.url}/login?session=a1b2c3"}))
    message = refused_over_http(server.url + "/api/feed", token_env="KESTREL_TEST_TOKEN")
    assert message == (f"the feed redirected to {elsewhere.url}/login; "
                       "kestrel doesn't follow redirects (set url to the feed's own address)")
    assert elsewhere.requests == []


def test_a_redirect_to_a_path_is_named_in_full(serve):
    server = serve(answer(b"", status=302, headers={"Location": "/sign-in"}))
    assert refused_over_http(server.url + "/api/feed").startswith(f"the feed redirected to {server.url}/sign-in; ")


@pytest.mark.parametrize("code", [503, 404, 401, 204])
def test_a_status_other_than_200_is_an_error(serve, code):
    server = serve(answer(b"" if code == 204 else b'{"error": "no"}', status=code))
    assert refused_over_http(server.url) == f"the feed answered {code}"


def test_a_feed_that_doesnt_answer_in_time_is_cut_off(serve):
    server = serve(hang)
    started = time.monotonic()
    assert refused_over_http(server.url, timeout=0.3) == "the feed didn't answer within 0.3 s"
    assert time.monotonic() - started < 2


def test_a_slow_trickle_is_cut_off_at_the_timeout(serve):
    server = serve(trickle)
    started = time.monotonic()
    assert refused_over_http(server.url, timeout=0.5) == "the feed was still sending after 0.5 s"
    assert time.monotonic() - started < 1.5  # timeout + 1 s: the whole answer is bounded, not just cut off eventually


def test_a_feed_that_trickles_its_headers_forever_is_cut_off(serve):
    # a status line and one header, then a byte every 20 ms, the terminating blank line never sent: this used to
    # defeat the timeout entirely (a 0.2 s timeout still blocked after 4 s) because nothing but a per-socket-read
    # timeout guarded the header phase, and a trickle resets that every time
    server = serve(header_trickle)
    started = time.monotonic()
    assert refused_over_http(server.url, timeout=0.3) == "the feed didn't answer within 0.3 s"
    assert time.monotonic() - started < 1.5


def cut_off(url, timeout=1):
    """How a fetch ended (its error, or None when it didn't fail) and how long it took, in seconds."""
    started = time.monotonic()
    try:
        over_http(url, timeout=timeout)
    except ConnectorError as error:
        return str(error), time.monotonic() - started
    return None, time.monotonic() - started


@pytest.mark.parametrize("reply", [chunk_size_trickle, trailer_trickle, slow_head_then_body],
                         ids=["chunk-size line", "trailer lines", "slow head then slow body"])
def test_one_timeout_covers_the_whole_answer_chunked_or_not(serve, reply):
    # a chunk-size line or trailer lines trickled a byte at a time used to block inside one read of the body for as
    # long as the feed kept it up; headers and body each had their own timeout, so together they could take ~3x
    message, took = cut_off(serve(reply).url)
    assert took < 2.5, (message, took)
    assert message == "the feed was still sending after 1 s"


def test_a_tls_handshake_that_trickles_is_cut_off(raw):
    server = raw(tls_trickle)
    message, took = cut_off(f"https://127.0.0.1:{server.port}/api/feed")
    assert took < 2.5, (message, took)
    assert message == "the feed didn't answer within 1 s"


def test_an_error_after_the_deadline_is_the_timeout_even_before_the_watchdog_wakes(monkeypatch):
    # CPython's TLS handshake can end at its own deadline with SSLWantReadError rather than TimeoutError, and the
    # watchdog thread can wake a timer tick after the deadline (Windows' clock is coarse): seen as a flake of the
    # test above. Here the watchdog wakes half a second late, on purpose.
    class LateEvent(threading.Event):
        def wait(self, timeout=None):
            return super().wait(None if timeout is None else timeout + 0.5)

    def connect(self):
        time.sleep(0.35)
        raise ssl.SSLWantReadError(2, "The operation did not complete (read) (_ssl.c:1006)")

    monkeypatch.setattr(threading, "Event", LateEvent)
    monkeypatch.setattr(http.client.HTTPConnection, "connect", connect)
    assert refused_over_http("http://127.0.0.1:9/api/feed", timeout=0.3) == "the feed didn't answer within 0.3 s"


@pytest.mark.parametrize("reply,message", [
    (chunked_cut_off, "the feed couldn't be read (IncompleteRead)"),
    (reset_midway, "the feed couldn't be read (ConnectionResetError)"),
    (answer(b'{"contract_version": "1"', headers={"Content-Length": "1000"}, length=False), "the feed stopped partway"),
], ids=["chunked, cut off", "reset", "shorter than its Content-Length"])
def test_a_body_that_breaks_off_is_named_plainly(serve, reply, message):
    assert refused_over_http(serve(reply).url) == message


def test_a_content_length_that_isnt_a_number_is_no_length(serve):
    # "²".isdigit() is True, and int("²") raises: the answer is read to its end instead
    server = serve(answer(desk(), headers={"Content-Type": "application/json", "Content-Length": "²"}, length=False))
    assert len(over_http(server.url).books) == 2


def test_a_redirect_to_a_malformed_address_is_refused_without_repeating_it(serve):
    server = serve(answer(b"", status=302, headers={"Location": "http://[::1/login?session=a1b2c3"}))
    assert refused_over_http(server.url) == (
        "the feed redirected; kestrel doesn't follow redirects (set url to the feed's own address)")


def test_the_request_says_it_comes_from_kestrel(serve):
    server = serve(answer(desk()))
    over_http(server.url)
    assert server.requests[0]["user-agent"] == f"kestrel/{__version__}"


def test_more_than_20_mb_in_one_line_is_refused_whether_or_not_the_feed_says_so_up_front(serve):
    head = f'{{"contract_version": "1", "generated_at": "{MADE}", "note": "'.encode("utf-8")
    exactly = head + b"z" * (MAX_BYTES - len(head) - 2) + b'"}'
    assert len(over_http(serve(answer(exactly, length=False)).url).books) == 0
    one_line = exactly[:-2] + b'z"}'  # one byte over, no newline anywhere, no Content-Length
    assert refused_over_http(serve(answer(one_line, length=False)).url) == "the feed sent more than 20 MB"
    declared = serve(answer(b"{}", headers={"Content-Length": str(MAX_BYTES + 1)}, length=False))
    assert refused_over_http(declared.url) == "the feed sent more than 20 MB"


def test_the_20_mb_message_wins_over_still_sending_when_the_deadline_has_also_passed(serve, monkeypatch):
    # a race: the body is too big AND the deadline has already passed by the time _read raises. The size message
    # must win -- the operator should shrink the feed, not raise the timeout. _fetch used to get this backwards by
    # rewriting every ConnectorError out of _read into "still sending" once late() was true. Content-Length alone
    # trips the size check in _read with no monotonic call inside it, so the flip below (set only once the real
    # _read has finished) is the only thing that makes the deadline look passed -- deterministic, no real race.
    real_read = feed_module._read
    real_monotonic = time.monotonic
    late_now = threading.Event()

    def fake_monotonic():
        return real_monotonic() + 1e9 if late_now.is_set() else real_monotonic()

    def wrapped_read(response, deadline, still_sending):
        try:
            return real_read(response, deadline, still_sending)
        finally:
            late_now.set()

    monkeypatch.setattr(feed_module.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(feed_module, "_read", wrapped_read)
    server = serve(answer(b"{}", headers={"Content-Length": str(MAX_BYTES + 1)}, length=False))
    assert refused_over_http(server.url) == "the feed sent more than 20 MB"


def test_a_sign_in_page_over_http_is_named(serve):
    page = b"<!doctype html><html><body><h1>Sign in</h1></body></html>"
    server = serve(answer(page, headers={"Content-Type": "text/html"}))
    assert refused_over_http(server.url) == ("the feed sent something that isn't JSON: "
                                             "a web page (a sign-in page, or the wrong address?)")


def test_a_feed_that_hangs_up_without_answering_is_an_error(serve):
    server = serve(hang_up)
    assert refused_over_http(server.url) == (
        "the feed couldn't be read (Remote end closed connection without response)")


def test_no_proxy_is_used_so_the_token_goes_only_to_the_feed(serve, monkeypatch):
    proxy = serve(answer(desk(books=[])))
    for name in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.setenv(name, proxy.url)
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("KESTREL_TEST_TOKEN", TOKEN)
    server = serve(answer(desk()))
    assert len(over_http(server.url, token_env="KESTREL_TEST_TOKEN").books) == 2
    assert proxy.requests == [] and len(server.requests) == 1


def test_the_token_never_shows_in_an_error_or_a_log(serve, monkeypatch, caplog, capsys):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", TOKEN)
    caplog.set_level(logging.DEBUG)
    replies = [answer(b"", status=503), answer(b"", status=302, headers={"Location": "/login"}),
               answer(b"<html></html>"), hang_up, answer(desk(contract_version="2")), answer(desk(books=[{}]))]
    messages = [refused_over_http(serve(reply).url, token_env="KESTREL_TEST_TOKEN") for reply in replies]
    out, err = capsys.readouterr()
    assert len(messages) == 6 and not [m for m in messages if TOKEN in m]
    assert TOKEN not in caplog.text and TOKEN not in out + err


def test_a_feed_url_in_a_profile_is_read_through_collect_with_its_options(serve, monkeypatch):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", TOKEN)
    server = serve(answer(desk()))
    profile = Profile(sources=[SourceCfg(id="desk", kind="feed", label="Trading desk", url=server.url,
                                         token_env="KESTREL_TEST_TOKEN", timeout=30, stale_after="15m")])
    assert build(profile.sources[0], profile).timeout == 30.0
    assert build(SourceCfg(id="desk", kind="feed", url=server.url), profile).timeout == 5.0
    snap = collect(profile, NOW)
    assert [(s.id, s.label, s.kind, s.status, s.detail) for s in snap.sources] == [
        ("desk", "Trading desk", "feed", "ok", "2 books · 1 strategy · 2 trades")]
    later = collect(profile, NOW + dt.timedelta(minutes=20))  # the payload is 23 minutes old by then
    assert later.sources[0].status == "stale"
    assert server.requests[0]["authorization"] == f"Bearer {TOKEN}"


def test_a_feed_file_is_found_from_the_profiles_folder_and_a_broken_feed_is_a_red_row(tmp_path, monkeypatch):
    (tmp_path / "desk").mkdir()
    feed_file(tmp_path / "desk")
    (tmp_path / "kestrel").mkdir()
    (tmp_path / "kestrel" / "profile.toml").write_text(
        '[[sources]]\nid = "demo"\nkind = "demo"\n'
        '[[sources]]\nid = "desk"\nkind = "feed"\nlabel = "Trading desk"\npath = "../desk/feed.json"\n'
        '[[sources]]\nid = "night"\nkind = "feed"\nlabel = "Night desk"\nurl = "http://127.0.0.1:9/feed"\n'
        'token_env = "KESTREL_NIGHT_TOKEN"\n', encoding="utf-8")
    monkeypatch.delenv("KESTREL_NIGHT_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path / "desk")  # anywhere but the profile's folder
    profile, _ = load_profile(tmp_path / "kestrel" / "profile.toml")
    snap = collect(profile, NOW)
    rows = {s.id: (s.status, s.detail) for s in snap.sources}
    assert rows["desk"] == ("ok", "2 books · 1 strategy · 2 trades")
    assert rows["night"] == ("error", "set KESTREL_NIGHT_TOKEN in the environment (token_env)")
    assert len(snap.accounts) == 6 and len(snap.books) == 7  # the demo's and the desk's
