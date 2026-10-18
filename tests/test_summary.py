from datetime import date, datetime, timezone

from conftest import make_detections
from sulteng import coverage as cov
from sulteng.config import load_params
from sulteng.summary import daily_series, kept_months, summarize, windows

PARAMS = load_params()
AREAS = {p.name: 1000.0 for p in PARAMS.provinces}
NOW = datetime(2026, 10, 18, 4, 0, tzinfo=timezone.utc)  # 12:00 WITA


def full_coverage(start, end):
    c = {}
    for sensor in PARAMS.sensors:
        c = cov.add(c, sensor.code, start, end)
    return c


def frame(specs):
    """specs: (province, district, 'YYYY-MM-DD HH:MM' UTC, category)."""
    det = make_detections([(-1.0, 120.0, utc, None) for _, _, utc, _ in specs]).drop(columns="type")
    return det.assign(
        province=[p for p, *_ in specs], district=[d for _, d, *_ in specs], category=[c for *_, c in specs]
    )


def test_kept_months_rollover_and_january():
    assert kept_months(NOW, 8) == ["2026-09", "2026-10"]
    assert kept_months(datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc), 8) == ["2026-10", "2026-11"]
    assert kept_months(datetime(2027, 1, 3, tzinfo=timezone.utc), 8) == ["2026-12", "2027-01"]
    # 17:00 UTC on 31 Dec is already 1 Jan in WITA
    assert kept_months(datetime(2026, 12, 31, 17, 0, tzinfo=timezone.utc), 8) == ["2026-12", "2027-01"]


def test_window_bounds_and_labels():
    w = windows(NOW, 8)
    assert (w["this_month"]["start"], w["this_month"]["end"]) == (date(2026, 10, 1), date(2026, 10, 18))
    assert (w["last_month"]["start"], w["last_month"]["end"]) == (date(2026, 9, 1), date(2026, 9, 30))
    assert w["24h"]["start"] == datetime(2026, 10, 17, 4, 0, tzinfo=timezone.utc)
    assert w["last_month"]["label"] == "September 2026"


def test_counts_per_window_province_and_district():
    df = frame([
        ("Sulawesi Tengah", "Morowali", "2026-10-18 02:00", "static_suspect"),
        ("Sulawesi Tengah", "Poso", "2026-10-17 05:00", "other"),
        ("Sulawesi Tengah", "Poso", "2026-10-05 05:00", "other"),
        ("Sulawesi Tengah", "Banggai", "2026-09-10 05:00", "other"),
        ("Kalimantan Tengah", "Kotawaringin Timur", "2026-09-10 05:00", "other"),
    ])
    s = summarize(df, full_coverage(datetime(2026, 8, 31, tzinfo=timezone.utc), NOW), PARAMS, AREAS, NOW)

    def focus(key):
        return next(p for p in s["windows"][key]["provinces"] if p["name"] == "Sulawesi Tengah")

    assert focus("24h")["counts"]["all"] == 2
    assert focus("24h")["counts"]["static_suspect"] == 1
    assert focus("this_month")["counts"]["other"] == 2
    assert focus("this_month")["per_1000_km2"] == {"all": 3.0, "other": 2.0}
    assert focus("last_month")["counts"]["all"] == 1
    kalteng = next(p for p in s["windows"]["last_month"]["provinces"] if p["name"] == "Kalimantan Tengah")
    assert kalteng["counts"]["other"] == 1
    assert [d["district"] for d in s["windows"]["this_month"]["focus_districts"]] == ["Poso", "Morowali"]
    assert s["windows"]["last_month"]["coverage"] == {"days": 30, "complete": 30, "partial": 0, "missing": 0}
    assert s["windows"]["this_month"]["coverage"]["partial"] == 1  # today


def test_window_with_no_coverage_reports_missing_days():
    s = summarize(frame([]), {}, PARAMS, AREAS, NOW)
    assert s["windows"]["last_month"]["coverage"] == {"days": 30, "complete": 0, "partial": 0, "missing": 30}


def test_daily_series_null_for_missing_and_zero_for_complete():
    c = full_coverage(datetime(2026, 9, 30, 16, 0, tzinfo=timezone.utc), NOW)  # from WITA 1 Oct
    df = frame([("Sulawesi Tengah", "Poso", "2026-10-05 05:00", "other")])
    days = {d["date"]: d for d in daily_series(df, c, PARAMS, NOW)}
    assert len(days) == 30 + 18
    assert days["2026-09-15"] == {"date": "2026-09-15", "coverage": "missing", "counts": None}
    assert days["2026-10-04"]["counts"] == {"volcano": 0, "static_suspect": 0, "other": 0}
    assert days["2026-10-05"]["counts"]["other"] == 1
    assert days["2026-10-18"]["coverage"] == "partial"
