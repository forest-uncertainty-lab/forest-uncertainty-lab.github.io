import pytest

from sulteng.stats import analog_outlook, jeffreys_vs_history, nowcast


def test_jeffreys_interval_narrows_with_count():
    small, big = jeffreys_vs_history(20, [10] * 13), jeffreys_vs_history(2000, [1000] * 13)
    assert small["ratio"][0] < 1.6 and small["ratio"][2] > 2.5  # Gamma(20.5): about 1.50 to 2.65
    assert big["ratio"][0] > 1.9 and big["ratio"][2] < 2.1
    assert small["ratio"][2] - small["ratio"][0] > big["ratio"][2] - big["ratio"][0]


def test_jeffreys_probability_above_record():
    r = jeffreys_vs_history(120, [10, 20, 100])
    assert 0.9 < r["p_above_max"] < 1
    assert r["rank"] == 1 and r["years"] == 4


def test_jeffreys_rank_counts_years_above():
    assert jeffreys_vs_history(50, [10, 60, 70, 40])["rank"] == 3


def test_zero_history_gives_no_ratio():
    r = jeffreys_vs_history(5, [0, 0, 0])
    assert r["ratio"] is None and r["p_above_max"] > 0.99


def test_nowcast_brackets_a_steady_rate():
    q = nowcast(30, [10] * 14, 4)
    assert q[0] <= 70 <= q[2]
    assert q[1] == pytest.approx(70, abs=5)


def test_nowcast_widens_when_recent_days_vary():
    steady, jumpy = nowcast(0, [10] * 14, 5), nowcast(0, [0, 20] * 7, 5)
    assert jumpy[2] - jumpy[0] > steady[2] - steady[0]


def test_nowcast_without_recent_days_is_none_and_full_week_is_exact():
    assert nowcast(5, [], 3) is None
    assert nowcast(42, [9] * 14, 0) == (42, 42, 42)


def test_nowcast_is_reproducible():
    assert nowcast(3, [1, 5, 9, 2], 4) == nowcast(3, [1, 5, 9, 2], 4)


def test_analog_outlook_is_exact_on_proportional_history():
    past = [[1] * 52, [2] * 52, [3] * 52]  # every year has the same shape
    out = analog_outlook(10 * 2, past, 10)  # this year: 2 a week for 10 weeks
    assert out["year_end"] == pytest.approx((104, 104, 104))
    assert out["weekly"][0] == pytest.approx((2, 2, 2)) and len(out["weekly"]) == 42
    assert out["p_record"] == 0 and out["analogs"] == 3


def test_analog_outlook_reports_record_share():
    past = [[1] * 52, [0] * 10 + [5] * 42]  # second year: quiet start, big finish
    out = analog_outlook(10, past, 10)  # this year: 1 a week so far, like the first year
    assert out["analogs"] == 1 and out["year_end"] == pytest.approx((52, 52, 52))
    assert out["p_record"] == 0  # 52 does not beat the second year's 210


def test_analog_outlook_skips_years_without_detections_so_far():
    assert analog_outlook(5, [[0] * 52, [0] * 52], 10) is None
