import datetime as dt

import pytest

from kestrel.contract import ValuePoint
from kestrel.metrics import expected_band, growth_index, largest_remainder, max_drawdown_pct, rsi, sum_series


def vp(day, value, flow=0.0):
    return ValuePoint(date=dt.date(2026, 9, day), value=value, net_flow=flow)


def test_growth_index_ignores_deposits():
    # 100 -> 110 of which 10 was a deposit: no performance at all
    assert growth_index([vp(1, 100), vp(2, 110, 10)]) == [1.0, 1.0]


def test_growth_index_chains_daily_returns():
    index = growth_index([vp(1, 100), vp(2, 110), vp(3, 99)])
    assert index == pytest.approx([1.0, 1.1, 0.99])


def test_growth_index_survives_a_zero_balance_and_empty_input():
    assert growth_index([]) == []
    assert growth_index([vp(1, 0), vp(2, 50, 50)]) == [1.0, 1.0]


def test_max_drawdown_is_the_worst_fall_from_a_peak():
    assert max_drawdown_pct([1.0, 1.2, 0.9, 1.3, 1.17]) == pytest.approx(-25.0)
    assert max_drawdown_pct([1.0, 1.1, 1.2]) == 0.0


def test_expected_band_narrows_with_more_trades():
    lo4, hi4 = expected_band(0.84, 3.0, 4)
    lo100, hi100 = expected_band(0.84, 3.0, 100)
    assert (lo4, hi4) == pytest.approx((0.84 - 2.94, 0.84 + 2.94))
    assert hi100 - lo100 < hi4 - lo4
    with pytest.raises(ValueError):
        expected_band(0.84, 3.0, 0)


def test_largest_remainder_always_totals_exactly():
    assert largest_remainder([71.53, 12.40, 16.07]) == [72, 12, 16]
    assert sum(largest_remainder([1, 1, 1])) == 100
    assert largest_remainder([0, 0]) == [0, 0]


def test_sum_series_carries_forward_a_missing_day():
    a = [vp(1, 100), vp(2, 101), vp(3, 102)]
    b = [vp(1, 50), vp(3, 55)]  # no point on the 2nd
    assert [p.value for p in sum_series([a, b])] == [150, 151, 157]


def test_sum_series_counts_a_late_account_as_a_deposit_not_growth():
    a = [vp(1, 100), vp(2, 100)]
    late = [vp(2, 40)]
    total = sum_series([a, late])
    assert total[1].value == 140 and total[1].net_flow == 40
    assert growth_index(total) == [1.0, 1.0]


def test_rsi_is_wilders_and_aligned_with_the_closes():
    assert rsi([10, 11, 10, 12]) == pytest.approx([None, None, 50.0, 83.333], abs=0.001)
    assert rsi([1, 2, 3]) == [None, None, 100.0]  # no losses at all
    assert rsi([3, 2, 1]) == [None, None, 0.0]
    assert rsi([5, 5, 5]) == [None, None, 50.0]  # no movement is neither overbought nor oversold
    assert rsi([1, 2]) == [None, None]
