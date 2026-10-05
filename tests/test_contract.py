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


# the six blocks and the debt category added in phase 5; every name and number here is made up
TARGET = {"id": "roth-vti", "account_id": "roth", "label": "VTI", "symbols": ["VTI"], "target": 60.0, "low": 55.0,
          "high": 65.0, "note": "the core"}
THESIS = {"symbol": "KO", "name": "Coca-Cola", "health": "watch", "reasons": ["volume soft two quarters"],
          "conviction": "medium", "opened": "2025-03-03", "last_reviewed": "2026-09-01",
          "wrong_if": ["pricing power fades"], "account_ids": ["brokerage"]}
EVENT = {"date": "2026-10-21", "symbol": "KO", "kind": "earnings", "title": "Third-quarter results",
         "detail": "before the open", "url": "https://example.com/ko/q3"}
GOAL = {"id": "house", "label": "House deposit", "target": 60000.0, "category": "cash", "by": "2028-06-01",
        "note": "twenty percent down"}
EXPOSURE = {"symbol": "MSFT", "name": "Microsoft", "value": 4210.5, "direct": 1500.0, "sector": "Technology"}
BACKTEST = {"id": "dip-a1", "name": "Dip buy, sell the bounce", "family": "dip", "window": "confirm",
            "verdict": "pass", "at": "2026-09-10T22:00:00+00:00", "strategy_id": "swing", "trades": 212,
            "avg_trade_pct": 0.41, "t_stat": 2.61, "calmar": 1.2, "max_drawdown_pct": -9.4, "note": "a made-up run"}
NEW_BLOCKS = {"targets": TARGET, "theses": THESIS, "events": EVENT, "goals": GOAL, "exposures": EXPOSURE,
              "backtests": BACKTEST}


def test_new_blocks_default_empty():
    # a v1 document written before these blocks existed still loads, with each of them empty
    account = {"id": "roth", "name": "Roth IRA", "category": "long_term", "value": 100.0, "as_of": NOW.isoformat()}
    snap = Snapshot.model_validate(minimal(accounts=[account]))
    assert [getattr(snap, name) for name in NEW_BLOCKS] == [[]] * 6
    assert snap.accounts[0].rate_pct is None and snap.accounts[0].limit is None


def test_every_new_block_round_trips_through_json():
    snap = Snapshot.model_validate(minimal(**{name: [item] for name, item in NEW_BLOCKS.items()}))
    assert Snapshot.model_validate_json(snap.model_dump_json()) == snap
    assert snap.targets[0].unit == "%" and snap.targets[0].actual is None
    assert snap.theses[0].status == "active" and snap.theses[0].last_reviewed == dt.date(2026, 9, 1)
    assert snap.events[0].date == dt.date(2026, 10, 21) and snap.goals[0].by == dt.date(2028, 6, 1)
    assert snap.exposures[0].direct == 1500.0 and snap.backtests[0].t_stat == 2.61
    bare = Snapshot.model_validate(minimal(
        theses=[{"symbol": "PG"}], events=[{"date": "2026-10-01", "kind": "other", "title": "Investor day"}],
        goals=[{"id": "all", "label": "Net worth", "target": 100000}],
        exposures=[{"symbol": "AAPL", "value": 10.0}],
        backtests=[{"id": "b", "name": "B", "verdict": "pending", "at": NOW.isoformat()}]))
    assert bare.theses[0].health == "none" and bare.theses[0].opened is None
    assert bare.events[0].symbol == "" and bare.events[0].url == ""
    assert bare.goals[0].account_id is None and bare.goals[0].category is None
    assert bare.exposures[0].direct == 0.0 and bare.backtests[0].trades is None


def test_debt_category_and_rates_round_trip():
    card = {"id": "card", "name": "Rewards card", "category": "debt", "value": 640.0, "rate_pct": 24.9,
            "limit": 5000.0, "as_of": NOW.isoformat()}
    savings = {"id": "savings", "name": "High-yield savings", "category": "cash", "value": 8000.0, "rate_pct": 4.1,
               "as_of": NOW.isoformat()}
    snap = Snapshot.model_validate(minimal(accounts=[card, savings], goals=[{**GOAL, "category": "debt"}]))
    assert [(a.category, a.rate_pct, a.limit) for a in snap.accounts] == [("debt", 24.9, 5000.0), ("cash", 4.1, None)]
    assert snap.goals[0].category == "debt"
    assert Snapshot.model_validate_json(snap.model_dump_json()) == snap


def test_target_needs_an_aim():
    aimless = {key: value for key, value in TARGET.items() if key not in ("target", "low", "high")}
    with pytest.raises(ValidationError, match="target, low or high"):
        Snapshot.model_validate(minimal(targets=[aimless]))
    for only in ("target", "low", "high"):  # any one of the three is an aim
        snap = Snapshot.model_validate(minimal(targets=[{**aimless, only: 50.0}]))
        assert getattr(snap.targets[0], only) == 50.0


def test_ratio_target_needs_actual():
    ratio = {"id": "cover", "label": "Cash cover", "unit": "x", "low": 6.0}
    with pytest.raises(ValidationError, match="actual"):
        Snapshot.model_validate(minimal(targets=[ratio]))
    snap = Snapshot.model_validate(minimal(targets=[{**ratio, "actual": 7.5}]))
    assert snap.targets[0].unit == "x" and snap.targets[0].actual == 7.5 and snap.targets[0].account_id is None
    with pytest.raises(ValidationError):
        Snapshot.model_validate(minimal(targets=[{**ratio, "unit": "$", "actual": 7.5}]))


def test_target_low_above_high_is_refused():
    with pytest.raises(ValidationError, match="low"):
        Snapshot.model_validate(minimal(targets=[{**TARGET, "low": 70.0, "high": 65.0}]))
    snap = Snapshot.model_validate(minimal(targets=[{**TARGET, "low": 60.0, "high": 60.0}]))  # a point band is fine
    assert snap.targets[0].low == snap.targets[0].high == 60.0


@pytest.mark.parametrize("url,ok", [
    ("", True),
    ("https://example.com/a", True),
    ("http://x", False),
    ("javascript:alert(1)", False),
    ("https://a b", False),
])
def test_event_url_must_be_https(url, ok):
    payload = minimal(events=[{**EVENT, "url": url}])
    if ok:
        assert Snapshot.model_validate(payload).events[0].url == url
    else:
        with pytest.raises(ValidationError):
            Snapshot.model_validate(payload)


def test_backtest_verdicts():
    for verdict in ("pass", "fail", "refused", "pending"):
        assert Snapshot.model_validate(minimal(backtests=[{**BACKTEST, "verdict": verdict}])).backtests[0].verdict == \
            verdict
    with pytest.raises(ValidationError):
        Snapshot.model_validate(minimal(backtests=[{**BACKTEST, "verdict": "maybe"}]))
    with pytest.raises(ValidationError):  # like every timestamp, `at` carries an offset
        Snapshot.model_validate(minimal(backtests=[{**BACKTEST, "at": "2026-09-10T22:00:00"}]))


def test_goal_account_ids_and_measure_round_trip():
    snap = Snapshot.model_validate(minimal(
        goals=[{**GOAL, "category": None, "account_ids": ["roth", "brokerage"], "measure": "deposits"}]))
    assert snap.goals[0].account_ids == ["roth", "brokerage"] and snap.goals[0].measure == "deposits"
    assert Snapshot.model_validate_json(snap.model_dump_json()) == snap
    bare = Snapshot.model_validate(minimal(goals=[GOAL])).goals[0]
    assert bare.account_ids == [] and bare.measure == "value"  # unchanged by default


@pytest.mark.parametrize("extra", [
    {"account_id": "roth", "account_ids": ["brokerage"], "category": None},
    {"account_id": "roth", "category": "cash", "account_ids": []},
    {"account_ids": ["roth", "brokerage"], "category": "cash"},
])
def test_goal_scope_is_at_most_one_of_account_accounts_or_category(extra):
    with pytest.raises(ValidationError, match="pick only one"):
        Snapshot.model_validate(minimal(goals=[{**GOAL, **extra}]))


def test_merge_keeps_every_new_block():
    a = Snapshot.model_validate(minimal(**{name: [item] for name, item in NEW_BLOCKS.items()}))
    b = Snapshot.model_validate(minimal(
        targets=[{**TARGET, "id": "roth-bnd", "label": "BND", "symbols": ["BND"]}], theses=[{**THESIS, "symbol": "PG"}],
        events=[{**EVENT, "symbol": "PG"}], goals=[{**GOAL, "id": "car"}], exposures=[{**EXPOSURE, "symbol": "AAPL"}],
        backtests=[{**BACKTEST, "id": "dip-a2"}]))
    merged = merge([a, b], generated_at=NOW)
    assert [t.id for t in merged.targets] == ["roth-vti", "roth-bnd"]
    assert [t.symbol for t in merged.theses] == ["KO", "PG"]
    assert [e.symbol for e in merged.events] == ["KO", "PG"]
    assert [g.id for g in merged.goals] == ["house", "car"]
    assert [e.symbol for e in merged.exposures] == ["MSFT", "AAPL"]
    assert [b.id for b in merged.backtests] == ["dip-a1", "dip-a2"]


TRANSACTION = {"account_id": "checking", "date": "2026-09-24", "amount": -42.17, "description": "GROCERY MART",
               "counterparty": "Grocery Mart", "category": "groceries"}


def test_transactions_default_empty_round_trip_and_merge():
    account = {"id": "checking", "name": "Checking", "category": "cash", "value": 800.0, "as_of": NOW.isoformat()}
    assert Snapshot.model_validate(minimal(accounts=[account])).transactions == []
    snap = Snapshot.model_validate(minimal(accounts=[account], transactions=[TRANSACTION]))
    assert Snapshot.model_validate_json(snap.model_dump_json()) == snap
    t = snap.transactions[0]
    assert (t.account_id, t.date, t.amount, t.description) == ("checking", dt.date(2026, 9, 24), -42.17, "GROCERY MART")
    bare = Snapshot.model_validate(minimal(transactions=[
        {"account_id": "card", "date": "2026-09-20", "amount": 200.0, "description": "PAYMENT"}]))
    assert bare.transactions[0].counterparty == "" and bare.transactions[0].category == ""
    merged = merge([snap, bare], generated_at=NOW)
    assert [t.account_id for t in merged.transactions] == ["checking", "card"]
