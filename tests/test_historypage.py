from datetime import date, datetime, timedelta, timezone

import pytest

from sulteng.historypage import build_history_page
from sulteng.indonesia import Indonesia, Region

IND = Indonesia(
    regions=(Region("A", "Alfa", "Alpha", "Sumatra", "Sumatera"), Region("B", "Beta", "Beta", "Kalimantan", "Kalimantan")),
    cities=(), archive_first=2023, archive_last=2025, area_bbox="0,0,1,1", map_bbox=(0, 0, 1, 1),
)


def archive(weekly_alfa=1.0, weekly_beta=2.0, years=(2023, 2024, 2025)):
    return {
        "years": list(years), "provinces": ["Alfa", "Beta"],
        "count": [[[weekly_alfa] * 52 for _ in years], [[weekly_beta] * 52 for _ in years]],
        "frp": [[[10 * weekly_alfa] * 52 for _ in years], [[10 * weekly_beta] * 52 for _ in years]],
        "filled_days": [[0] * 52 for _ in years], "missing_days": [[0] * 52 for _ in years],
        "ratio": {str(y): 1.0 for y in years},
    }


def daily_store(first: date, last: date, per_day=1, sensor="N", province="Alfa", skip=()):
    rows, fetched = [], {}
    day = first
    while day <= last:
        iso = day.isoformat()
        if iso in skip:
            fetched[iso] = "empty-NRT"
        else:
            rows.append([sensor, province, iso, iso, per_day, 10.0 * per_day])
            fetched[iso] = "SP"
        day += timedelta(days=1)
    return {"rows": rows, "fetched": {sensor: fetched}}


NOW = datetime(2026, 3, 18, 6, 0, tzinfo=timezone.utc)  # 14:00 on 18 March in UTC+8: day 77, week 10


def page(store, now=NOW, arc=None):
    return build_history_page(arc or archive(), store, IND, now)


def row(p, key):
    return [r["key"] for r in p["rows"]].index(key)


def test_rows_sum_provinces_into_islands_and_indonesia():
    p = page(daily_store(date(2026, 1, 1), date(2026, 3, 17)))
    assert [r["key"] for r in p["rows"]] == ["total", "isl:Sumatra", "prov:Alfa", "isl:Kalimantan", "prov:Beta"]
    assert p["rows"][2]["en"] == "Alpha" and p["rows"][2]["id"] == "Alfa" and p["rows"][1]["id"] == "Sumatera"
    y = p["years"].index(2025)
    assert p["count"][0][y][0] == 3 and p["count"][1][y][0] == 1 and p["frp"][4][y][0] == 20


def test_future_weeks_are_null_and_running_week_is_nowcast():
    p = page(daily_store(date(2026, 1, 1), date(2026, 3, 17)))
    y = p["years"].index(2026)
    assert p["years"][-1] == 2026 and p["latest_day"] == "2026-03-17"
    assert p["running"] == {"year": 2026, "week": 10, "days_seen": 6, "days_in_week": 7}
    alfa = row(p, "prov:Alfa")
    assert p["count"][alfa][y][9] == 7 and p["count"][alfa][y][10] == 6 and p["count"][alfa][y][11] is None
    lo, mid, hi = p["nowcast"]["count"][alfa]
    assert lo <= 7 <= hi and mid == pytest.approx(7, abs=1)


def test_days_never_fetched_are_missing_not_zero():
    p = page(daily_store(date(2026, 3, 11), date(2026, 3, 17)))  # only the last week is known (no key)
    y = p["years"].index(2026)
    assert p["count"][row(p, "prov:Alfa")][y][0] is None and p["missing_days"][y][0] == 7
    assert p["count"][row(p, "prov:Alfa")][y][9] is not None


def test_gap_day_in_current_year_is_filled_from_noaa20():
    store = daily_store(date(2026, 1, 1), date(2026, 3, 17), skip={"2026-03-04"})
    store["rows"].append(["N20", "Alfa", "2026-03-04", "2026-03-04", 2, 20.0])
    store["fetched"]["N20"] = {"2026-03-04": "SP"}
    p = page(store)
    y, week = p["years"].index(2026), (date(2026, 3, 4).timetuple().tm_yday - 1) // 7
    assert p["count"][row(p, "prov:Alfa")][y][week] == pytest.approx(6 + 2 * 1.0)  # fallback ratio 1.0 from 2025
    assert p["filled_days"][y][week] == 1 and p["missing_days"][y][week] == 0


def test_unusual_uses_the_same_weeks_each_year():
    p = page(daily_store(date(2026, 1, 1), date(2026, 3, 17), per_day=2), arc=archive(weekly_alfa=7.0))  # 14 a week against 7
    u = p["unusual"]["count"][row(p, "prov:Alfa")]
    assert u["to_date"] == 140 and u["usual"] == 70 and u["rank"] == 1
    assert u["ratio"][0] < 2 < u["ratio"][2]
    assert p["unusual"]["frp"][row(p, "prov:Alfa")]["ratio"] == [2.0, 2.0, 2.0]
    out = p["outlook"]["count"][row(p, "prov:Alfa")]
    assert out["year_end"] == pytest.approx([728, 728, 728]) and out["analogs"] == 3  # 140 + 2 x 7 x 42


def test_year_after_archive_stays_in_store_and_page():
    store = daily_store(date(2026, 1, 1), date(2027, 1, 2))
    p = page(store, now=datetime(2027, 1, 3, 6, 0, tzinfo=timezone.utc))
    assert p["years"][-2:] == [2026, 2027]
    y = p["years"].index(2026)
    assert all(v is not None for v in p["count"][row(p, "prov:Alfa")][y])
    assert p["running"]["year"] == 2027 and p["running"]["week"] == 0 and p["running"]["days_seen"] == 2
    assert p["nowcast"]["count"][row(p, "prov:Alfa")] is not None


def test_incomplete_completed_weeks_do_not_produce_ratio_rank_or_outlook():
    p = page(daily_store(date(2026, 3, 11), date(2026, 3, 17)))
    alfa = row(p, 'prov:Alfa')
    u = p['unusual']['count'][alfa]
    assert u['to_date'] == 1  # One known day precedes the running week.
    assert u['ratio'] is None and u['rank'] is None and u['p_above_max'] is None
    assert u['incomplete'] is True
    assert p['outlook']['count'][alfa] is None


def test_running_week_estimates_missing_elapsed_days_as_well_as_future_days():
    p = page(daily_store(date(2026, 1, 1), date(2026, 3, 17), per_day=100, skip={'2026-03-12', '2026-03-13'}))
    alfa = row(p, 'prov:Alfa')
    assert p['running']['days_seen'] == 4
    assert p['nowcast']['count'][alfa][1] == pytest.approx(700, abs=10)


def test_frp_nowcast_preserves_units_and_fractional_power():
    store = daily_store(date(2026, 1, 1), date(2026, 3, 17))
    for entry in store['rows']:
        entry[-1] = .1
    p = page(store)
    assert p['nowcast']['frp'][row(p, 'prov:Alfa')] == pytest.approx([.7, .7, .7])


def test_historical_partial_weeks_are_excluded_from_the_baseline():
    arc = archive(weekly_alfa=7)
    arc['missing_days'][1][9] = 1
    arc['count'][0][1][9] = 999
    p = page(daily_store(date(2026, 1, 1), date(2026, 3, 17), per_day=2), arc=arc)
    stats = p['unusual']['count'][row(p, 'prov:Alfa')]
    assert stats['years'] == 3 and stats['rank'] == 1 and stats['usual'] == 70
