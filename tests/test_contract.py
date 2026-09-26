import datetime as dt

import pytest
from pydantic import ValidationError

from kestrel.contract import CONTRACT_VERSION, Snapshot, ValuePoint, merge

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


def minimal(**extra):
    return {"contract_version": "1", "generated_at": NOW.isoformat(), **extra}


@pytest.mark.parametrize("link", ["https://evil.example", "//evil.example", "/\\evil.example", "javascript:x"])
def test_an_alert_link_must_stay_inside_the_app(link):
    with pytest.raises(ValidationError):
        Snapshot.model_validate(minimal(alerts=[{"level": "note", "title": "x", "link": link}]))


@pytest.mark.parametrize("link", ["", "/", "/books", "/strategies/rsi2?tab=trades"])
def test_an_internal_alert_link_is_kept(link):
    snap = Snapshot.model_validate(minimal(alerts=[{"level": "note", "title": "x", "link": link}]))
    assert snap.alerts[0].link == link


def test_a_minimal_snapshot_loads_with_empty_lists():
    snap = Snapshot.model_validate(minimal())
    assert snap.contract_version == CONTRACT_VERSION
    assert snap.accounts == [] and snap.benchmark is None


def test_an_unknown_major_version_is_refused_with_a_reason():
    with pytest.raises(ValidationError, match="unsupported contract version '2'"):
        Snapshot.model_validate(minimal(contract_version="2"))


def test_a_newer_minor_version_and_unknown_fields_still_load():
    snap = Snapshot.model_validate(minimal(contract_version="1.3", something_new={"x": 1}))
    assert snap.contract_version == "1.3"


def test_timestamps_must_carry_an_offset():
    with pytest.raises(ValidationError):
        Snapshot.model_validate({"generated_at": "2026-09-25T21:08:00"})


def test_a_full_account_and_series_round_trip_through_json():
    snap = Snapshot.model_validate(minimal(
        accounts=[{"id": "roth", "name": "Roth IRA", "category": "long_term", "value": 100.0,
                   "as_of": NOW.isoformat()}],
        account_history=[{"id": "roth", "points": [{"date": "2026-09-24", "value": 99.0},
                                                    {"date": "2026-09-25", "value": 100.0, "net_flow": 0.5}]}],
    ))
    again = Snapshot.model_validate_json(snap.model_dump_json())
    assert again == snap
    assert again.account_history[0].points[1] == ValuePoint(date=dt.date(2026, 9, 25), value=100.0, net_flow=0.5)


def test_an_account_type_is_optional_and_round_trips():
    base = {"id": "roth", "name": "Roth IRA", "category": "long_term", "value": 100.0, "as_of": NOW.isoformat()}
    snap = Snapshot.model_validate(minimal(accounts=[base, {**base, "id": "ira", "account_type": "Roth IRA"}]))
    assert [a.account_type for a in snap.accounts] == ["", "Roth IRA"]
    assert Snapshot.model_validate_json(snap.model_dump_json()) == snap


def test_a_holdings_day_is_optional_and_round_trips():
    base = {"account_id": "roth", "symbol": "SPY", "quantity": 2, "price": 600, "value": 1200}
    snap = Snapshot.model_validate(minimal(holdings=[base, {**base, "symbol": "AGG", "as_of": "2026-09-24"}]))
    assert [h.as_of for h in snap.holdings] == [None, dt.date(2026, 9, 24)]
    assert Snapshot.model_validate_json(snap.model_dump_json()) == snap


def test_an_unknown_category_is_refused():
    with pytest.raises(ValidationError):
        Snapshot.model_validate(minimal(accounts=[{"id": "x", "name": "X", "category": "crypto", "value": 1,
                                                   "as_of": NOW.isoformat()}]))


def test_merge_concatenates_lists_and_keeps_the_first_benchmark():
    bench = {"symbol": "SPY", "label": "S&P 500", "points": [{"date": "2026-09-25", "value": 600.0}]}
    a = Snapshot.model_validate(minimal(sources=[{"id": "a", "label": "A", "kind": "demo"}], benchmark=bench))
    b = Snapshot.model_validate(minimal(sources=[{"id": "b", "label": "B", "kind": "feed"}]))
    merged = merge([a, b], generated_at=NOW)
    assert [s.id for s in merged.sources] == ["a", "b"]
    assert merged.benchmark is not None and merged.benchmark.symbol == "SPY"
    assert merge([], generated_at=NOW).sources == []


CHART = {
    "book_id": "real", "symbol": "HD", "opened": "2026-09-14",
    "bars": [{"date": "2026-09-11", "open": 220.1, "high": 221.0, "low": 217.9, "close": 218.4},
             {"date": "2026-09-14", "open": 218.67, "high": 220.2, "low": 217.5, "close": 219.9}],
    "indicator": {"label": "RSI(2)", "values": [None, 6.5],
                  "lines": [{"value": 10, "label": "buy under 10"}, {"value": 70, "label": "sell over 70"}]},
    "stop": 201.18,
}
STRATEGY = {
    "id": "rsi2", "name": "Mean reversion",
    "expected": {"win_rate": 66, "avg_trade_pct": 0.84, "avg_win_pct": 2.45, "avg_loss_pct": -2.28,
                 "trades_per_month": 3.1, "sd_trade_pct": 3.0, "cagr_pct": 23.4, "max_drawdown_pct": -11.7},
    "watch": [{"symbol": "KO", "label": "RSI(2)", "value": 12.4}],
}


def test_trade_charts_and_the_new_strategy_fields_round_trip_through_json():
    snap = Snapshot.model_validate(minimal(trade_charts=[CHART], strategies=[STRATEGY]))
    again = Snapshot.model_validate_json(snap.model_dump_json())
    assert again == snap
    chart = again.trade_charts[0]
    assert chart.bars[1].open == 218.67 and chart.indicator is not None and chart.indicator.values == [None, 6.5]
    assert [line.label for line in chart.indicator.lines] == ["buy under 10", "sell over 70"]
    strategy = again.strategies[0]
    assert strategy.expected is not None and strategy.expected.cagr_pct == 23.4
    assert strategy.expected.max_drawdown_pct == -11.7
    assert strategy.watch[0].symbol == "KO" and strategy.watch[0].note == ""


def test_the_new_fields_are_optional():
    snap = Snapshot.model_validate(minimal(strategies=[{"id": "s", "name": "S", "expected": {
        "win_rate": 50, "avg_trade_pct": 0.1, "avg_win_pct": 1, "avg_loss_pct": -1, "trades_per_month": 2,
        "sd_trade_pct": 1}}]))
    assert snap.trade_charts == [] and snap.strategies[0].watch == []
    assert snap.strategies[0].expected is not None and snap.strategies[0].expected.cagr_pct is None
    bare = Snapshot.model_validate(minimal(trade_charts=[{**CHART, "indicator": None, "stop": None}]))
    assert bare.trade_charts[0].indicator is None and bare.trade_charts[0].stop is None


def test_a_chart_for_a_trade_that_does_not_exist_still_loads():
    # the Strategy page matches charts to trades and skips the rest; a stray chart is never a reason to drop a source
    snap = Snapshot.model_validate(minimal(trade_charts=[CHART]))
    assert snap.trades == [] and len(snap.trade_charts) == 1


def test_merge_keeps_every_sources_trade_charts():
    a = Snapshot.model_validate(minimal(trade_charts=[CHART]))
    b = Snapshot.model_validate(minimal(trade_charts=[{**CHART, "symbol": "LOW"}]))
    assert [c.symbol for c in merge([a, b], generated_at=NOW).trade_charts] == ["HD", "LOW"]
