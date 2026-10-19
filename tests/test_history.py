from datetime import date

import pandas as pd

from conftest import make_detections
from sulteng.history import field_changes, longest_gap, province_years, raw_profile

HEADER = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight,type\n"


def test_longest_gap_counts_days_without_any_detection():
    seen = [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 6)]
    assert longest_gap(seen, date(2020, 1, 1), date(2020, 1, 10)) == (4, date(2020, 1, 7))
    assert longest_gap([date(2020, 1, d) for d in range(1, 11)], date(2020, 1, 1), date(2020, 1, 10)) == (0, None)


def test_raw_profile_reports_fields_months_and_gaps(tmp_path):
    path = tmp_path / "viirs-snpp_2020_Indonesia.csv"
    path.write_text(HEADER
                    + "-1.5,120.2,330,0.4,0.4,2020-01-05,0530,N,VIIRS,n,2,290,3.1,D,0\n"
                    + "-1.6,120.3,331,0.4,0.4,2020-01-05,1730,N,VIIRS,h,2,291,9.0,N,2\n"
                    + "-1.7,120.4,332,0.4,0.4,2020-03-01,0530,N,VIIRS,l,2,292,1.0,D,0\n")
    p = raw_profile(path, 2020)
    assert p["rows"] == 3
    assert p["columns"] == HEADER.strip().split(",")
    assert p["values"]["type"] == {"0": 2, "2": 1}
    assert p["values"]["confidence"] == {"h": 1, "l": 1, "n": 1}
    assert p["rows_per_month"]["2020-02"] == 0 and p["rows_per_month"]["2020-03"] == 1
    assert p["empty_months"] == [f"2020-{m:02d}" for m in [2] + list(range(4, 13))]
    assert p["days_without_rows"] == 366 - 2
    assert p["longest_gap"] == (305, "2020-03-02")  # 2 March to 31 December


def test_field_changes_name_what_differs_from_the_year_before():
    a = {"columns": ["x", "type"], "values": {"type": {"0": 5}, "version": {"2": 5}}}
    b = {"columns": ["x", "type", "extra"], "values": {"type": {"0": 3, "3": 1}, "version": {"2": 4}}}
    notes = field_changes({2019: a, 2020: b})
    assert notes == ["2020: new column(s) extra", "2020: type gains value(s) 3"]


def test_province_years_counts_by_wita_year_with_zero_rows_and_land_rates():
    det = make_detections([
        (-1.5, 120.2, "2023-06-01 05:30", 0),
        (-1.5, 120.2, "2023-12-31 17:30", 0),  # 2024-01-01 WITA
        (-1.5, 120.2, "2024-06-01 05:30", 0),
    ]).assign(province="Alfa", category=["other", "other", "static_suspect"])
    provinces = pd.DataFrame({"name": ["Alfa", "Beta"], "island": ["Sulawesi", "Kalimantan"],
                              "area_km2": [2000.0, 500.0]})
    out = province_years(det, provinces, (2023, 2024)).set_index(["province", "year"])
    assert out.loc[("Alfa", 2023), "all"] == 1 and out.loc[("Alfa", 2024), "all"] == 2
    assert out.loc[("Alfa", 2024), "static_suspect"] == 1 and out.loc[("Alfa", 2024), "other"] == 1
    assert out.loc[("Alfa", 2024), "other_per_1000_km2"] == 0.5
    assert out.loc[("Beta", 2023), "all"] == 0 and out.loc[("Beta", 2023), "other_per_1000_km2"] == 0.0
    assert out.loc[("Beta", 2023), "island"] == "Kalimantan"
