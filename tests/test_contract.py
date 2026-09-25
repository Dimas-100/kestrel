import datetime as dt

import pytest
from pydantic import ValidationError

from kestrel.contract import CONTRACT_VERSION, Snapshot, ValuePoint, merge

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


def minimal(**extra):
    return {"contract_version": "1", "generated_at": NOW.isoformat(), **extra}


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
