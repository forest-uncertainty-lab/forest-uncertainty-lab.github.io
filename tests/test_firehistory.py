from datetime import date

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from conftest import make_detections
from sulteng.firehistory import gap_days, keep_fires, local_week, ratio, unmasked, weekly, with_gap_fill
from sulteng.masks import Masks, cell_index

NO_CELLS = pd.MultiIndex.from_arrays([np.array([], dtype=np.int64)] * 2, names=["iy", "ix"])
PROVINCES = gpd.GeoDataFrame({"name": ["Alfa", "Beta"]}, geometry=[box(120, -2, 121, -1), box(121, -2, 122, -1)], crs="EPSG:4326")


def test_local_week_crosses_midnight_and_caps_week_52():
    det = make_detections([
        (-1.5, 120.5, "2023-12-31 17:30", 0),  # 2024-01-01 in UTC+8
        (-1.5, 120.5, "2024-12-30 17:30", 0),  # 2024-12-31, day 366
        (-1.5, 120.5, "2024-01-08 05:30", 0),  # day 8: second week
    ])
    year, week = local_week(det["local_date"])
    assert year.tolist() == [2024, 2024, 2024] and week.tolist() == [0, 51, 1]


def test_gap_days_lists_utc_days_without_rows():
    assert gap_days(["2024-01-01", "2024-01-03"], date(2024, 1, 1), date(2024, 1, 4)) == ["2024-01-02", "2024-01-04"]


def test_ratio_needs_30_shared_days():
    days = pd.date_range("2024-01-01", periods=40).strftime("%Y-%m-%d")
    snpp, n20 = pd.Series(98.0, index=days), pd.Series(100.0, index=days)
    assert ratio(snpp, n20) == pytest.approx(0.98)
    assert ratio(snpp.iloc[:29], n20.iloc[:29]) is None


def test_gap_fill_weights_noaa20_rows_on_gap_days_only():
    snpp = make_detections([(-1.5, 120.5, "2024-07-10 05:30", 0)])
    n20 = make_detections([(-1.5, 120.5, "2024-07-11 05:30", None), (-1.5, 120.6, "2024-07-12 05:30", None)], sensor="N20")
    out = with_gap_fill(snpp, n20, ["2024-07-11"], 0.98)
    assert out["weight"].tolist() == [1.0, 0.98] and out["filled"].tolist() == [False, True]
    assert out["acq_date"].tolist() == ["2024-07-10", "2024-07-11"]


def test_gap_fill_leaves_double_gaps_missing():
    snpp = make_detections([(-1.5, 120.5, "2024-07-10 05:30", 0)])
    n20 = make_detections([(-1.5, 120.5, "2024-07-12 05:30", None)], sensor="N20")
    assert len(with_gap_fill(snpp, n20, ["2024-07-11"], 0.98)) == 1
    assert len(with_gap_fill(snpp, n20, ["2024-07-12"], None)) == 1


def test_keep_fires_drops_masked_typed_and_outside():
    det = make_detections([
        (-1.5012, 120.5012, "2024-08-01 05:30", 0),  # masked cell
        (-1.6, 120.6, "2024-08-01 05:30", 2),  # FIRMS static type
        (-1.5, 125.0, "2024-08-01 05:30", 0),  # outside every province
        (-1.7, 121.5, "2024-08-01 05:30", 0),  # kept, in Beta
        (-1.8, 120.2, "2024-08-01 05:30", None),  # kept, no type (near-real-time), in Alfa
    ])
    masked = cell_index(det.iloc[[0]], 0.005)
    out = keep_fires(det, PROVINCES, Masks(0.005, masked, NO_CELLS))
    assert out["province"].tolist() == ["Beta", "Alfa"]


def test_unmasked_keeps_rows_outside_provinces():
    det = make_detections([(-1.5, 125.0, "2024-08-01 05:30", 0), (-1.6, 120.6, "2024-08-01 05:30", 1)])
    assert len(unmasked(det, Masks(0.005, NO_CELLS, NO_CELLS))) == 1


def test_weekly_sums_weights_and_counts_filled_days():
    det = make_detections([
        (-1.5, 120.5, "2024-07-10 05:30", 0),
        (-1.5, 120.5, "2024-07-11 05:30", None),
        (-1.7, 121.5, "2024-12-31 05:30", 0),
    ]).assign(province=["Alfa", "Alfa", "Beta"], weight=[1.0, 0.98, 1.0], filled=[False, True, False], frp=[5.0, 10.0, 2.0])
    out = weekly(det, 2024, ["Alfa", "Beta"])
    w = (pd.Timestamp("2024-07-10").dayofyear - 1) // 7
    assert out["count"][0][w] == pytest.approx(1.98) and out["count"][1][51] == 1
    assert out["frp"][0][w] == pytest.approx(5 + 9.8)
    assert out["filled_days"][w] == 1 and sum(out["filled_days"]) == 1
    assert len(out["count"][0]) == 52


def test_a_filled_day_counts_once_even_across_two_local_weeks():
    # UTC 2024-01-07 runs from 08:00 on the 7th (week 0) to 08:00 on the 8th (week 1) in UTC+8.
    det = make_detections([(-1.5, 120.5, "2024-01-07 05:30", None), (-1.5, 120.5, "2024-01-07 17:30", None)])
    det = det.assign(province="Alfa", weight=0.98, filled=True)
    out = weekly(det, 2024, ["Alfa"])
    assert out["count"][0][0] == pytest.approx(0.98) and out["count"][0][1] == pytest.approx(0.98)
    assert out["filled_days"].tolist()[:2] == [1, 0]
