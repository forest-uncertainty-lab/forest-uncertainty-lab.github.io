import json
import math
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sulteng.fetch import FetchError
from sulteng.haze import (
    LEVELS, WindField, binned_fires, build_haze, cams, ensemble, nea, track, trajectory, upwind_fires, wind_field,
)
from sulteng.indonesia import load_indonesia

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 22, 6, 0, tzinfo=timezone.utc)
NOW_H = NOW.timestamp() / 3600


def fixture(name):
    return json.loads((FIX / name).read_text())


def uniform_field(u=-10.0, v=0.0, hours=72, lats=(-2.0, -1.0, 0.0, 1.0, 2.0), lons=(100.0, 101.0, 102.0, 103.0, 104.0)):
    times = NOW_H - hours + np.arange(hours + 1)
    shape = (len(times), len(lats), len(lons))
    return WindField(times=times, lats=np.asarray(lats), lons=np.asarray(lons),
                     u={lv: np.full(shape, u) for lv in LEVELS}, v={lv: np.full(shape, v) for lv in LEVELS})


def test_nea_band_ignores_missing_regions():
    out = nea([fixture("nea_pm25.json")], fixture("nea_psi.json"))
    times = [h["time"] for h in out["pm25_hourly"]]
    assert times == sorted(times) and len(times) == 3
    middle = out["pm25_hourly"][1]
    assert "west" not in middle["regions"] and middle["lo"] == min(middle["regions"].values())
    assert set(out["psi_24h"]) == {"north", "south", "east", "west", "central"} and out["psi_time"].endswith("+08:00")


def test_cams_maps_payloads_to_cities_in_order():
    cities = load_indonesia().cities
    out = cams(fixture("openmeteo_air.json"), [cities[0], cities[7]])
    assert list(out) == ["singapore", "palangka-raya"] and len(out["singapore"]["time"]) == 48
    assert len(out["palangka-raya"]["pm2_5"]) == 48


def test_wind_field_turns_speed_and_direction_into_components():
    payload = {"hourly": {"time": ["2026-10-22T05:00", "2026-10-22T06:00"], **{f"wind_speed_{lv}hPa": [10.0, None] for lv in LEVELS},
                          **{f"wind_direction_{lv}hPa": [90.0, 90.0] for lv in LEVELS}}}
    f = wind_field([payload], np.array([0.0]), np.array([100.0]))
    assert f.u["850"][0, 0, 0] == pytest.approx(-10.0) and abs(f.v["850"][0, 0, 0]) < 1e-9  # from the east: blowing west
    assert np.isnan(f.u["850"][1, 0, 0]) and f.times[1] - f.times[0] == 1


def test_trajectory_constant_wind_moves_expected_distance():
    path = trajectory(uniform_field(), "850", 0.0, 101.0, NOW_H, hours=2)
    assert [p[2] for p in path] == [0, 1, 2]
    assert path[-1][0] == pytest.approx(101.0 + 2 * 3600 * 10 / 111_320, abs=1e-3) and path[-1][1] == pytest.approx(0.0)


def test_trajectory_stops_at_missing_wind():
    f = uniform_field()
    f.u["850"][-3:] = np.nan  # the last three hours have no wind
    assert len(trajectory(f, "850", 0.0, 101.0, NOW_H, hours=10)) == 1


def test_trajectory_stops_at_the_grid_edge():
    path = trajectory(uniform_field(), "850", 0.0, 103.5, NOW_H, hours=48)
    assert path[-1][0] <= 104.0 and len(path) < 49


def test_ensemble_has_nine_members_per_level_with_central_first():
    ens = ensemble(uniform_field(), 0.0, 101.0, NOW_H)
    assert set(ens) == set(LEVELS) and all(len(members) == 9 for members in ens.values())
    assert ens["850"][0] == trajectory(uniform_field(), "850", 0.0, 101.0, NOW_H)
    assert ens["850"][1] != ens["850"][0]


def test_upwind_fires_skip_the_city_and_count_detections():
    fires = np.array([[101.0, 0.05, 7], [104.0, 0.0, 3]])  # [lon, lat, detections]: one at the city, one upwind
    at_city_only = [[101.0, 0.0, 0], [101.3, 0.0, 1], [101.6, 0.0, 2], [102.0, 0.0, 3]]
    upwind = [[101.0, 0.0, 0], [102.0, 0.0, 2], [103.0, 0.0, 4], [103.9, 0.1, 6]]
    out = upwind_fires([at_city_only, upwind], fires, km=50, skip_hours=3)
    assert out == {"share": 0.5, "median": 1.5, "max": 3}
    assert upwind_fires([upwind], np.empty((0, 3)))["share"] == 0.0


def test_binned_fires_counts_per_cell():
    df = pd.DataFrame({"longitude": [101.001, 101.009, 101.031], "latitude": [0.001, 0.009, 0.001]})
    assert sorted(binned_fires(df, cell=0.02)) == [[101.01, 0.01, 2], [101.03, 0.01, 1]]


def test_track_keeps_30_days_and_reports_after_24_hours():
    hourly = [{"time": f"2026-10-21T{h:02d}:00:00+08:00", "mean": 20.0} for h in range(24)]
    model = {"time": [f"2026-10-20T{h:02d}:00" for h in range(16, 24)] + [f"2026-10-21T{h:02d}:00" for h in range(16)],
             "pm2_5": [10.0] * 24}
    store, stats = track({"pairs": {"2026-09-01T00:00": [1.0, 1.0]}}, hourly, model, NOW)
    assert "2026-09-01T00:00" not in store["pairs"] and len(store["pairs"]) == 24
    assert stats == {"hours": 24, "ratio": (2.0, 2.0, 2.0)}
    assert track({}, hourly[:5], model, NOW)[1] is None


def fake_get(fail=()):
    air = fixture("openmeteo_air.json")

    def get(url, **_):
        if any(f in url for f in fail):
            raise FetchError("down")
        if "data.gov.sg" in url:
            return fixture("nea_psi.json") if url.endswith("/psi") else fixture("nea_pm25.json")
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        n = len(q["latitude"][0].split(","))
        if "air-quality" in url:
            return [air[i % 2] for i in range(n)]
        hours = [f"2026-10-{d}T{h:02d}:00" for d in (20, 21, 22) for h in range(24)]
        point = {"hourly": {"time": hours, **{f"wind_speed_{lv}hPa": [5.0] * 72 for lv in LEVELS},
                            **{f"wind_direction_{lv}hPa": [45.0] * 72 for lv in LEVELS}}}
        return [point] * n

    return get


def test_build_haze_with_fake_get():
    fires = pd.DataFrame({"longitude": [104.5], "latitude": [1.5], "acq_utc": [pd.Timestamp("2026-10-22T03:00Z")]})
    out, store = build_haze(load_indonesia(), fires, NOW, {}, get=fake_get(), sleep=lambda s: None)
    assert [c["key"] for c in out["cities"]][0] == "singapore" and len(out["cities"]) == 9
    assert set(out["trajectories"]["palu"]) == set(LEVELS) and len(out["trajectories"]["palu"]["850"]) == 9
    assert set(out["upwind"]["singapore"]["850"]) == {"share", "median", "max"}
    assert out["nea"]["psi_24h"] and out["cams"]["palu"]["pm2_5"]
    assert out["fires"]["count"] == 1 and out["generated_at"] == "2026-10-22T06:00:00+00:00" and out["errors"] == []


def test_build_haze_records_a_failed_source_and_keeps_the_rest():
    out, _ = build_haze(load_indonesia(), pd.DataFrame(columns=["longitude", "latitude", "acq_utc"]), NOW, {},
                        get=fake_get(fail=("air-quality",)), sleep=lambda s: None)
    assert out["cams"] == {} and out["nea"] is not None and out["trajectories"]
    assert any("CAMS" in e for e in out["errors"])


def test_build_haze_paces_wind_requests_under_the_minute_limit():
    pauses, calls = [], []
    get = fake_get()

    def counting_get(url, **kw):
        calls.append(url)
        return get(url, **kw)

    build_haze(load_indonesia(), pd.DataFrame(columns=["longitude", "latitude", "acq_utc"]), NOW, {}, get=counting_get,
               sleep=pauses.append)
    assert sum(u.startswith("https://api.open-meteo.com/") for u in calls) == 10  # 940 points, 100 per request
    assert pauses == [61]  # one pause after the first 500 points


def test_build_haze_counts_only_fires_inside_the_map():
    fires = pd.DataFrame({"longitude": [104.5, 90.0], "latitude": [1.5, 15.0],
                          "acq_utc": [pd.Timestamp("2026-10-22T03:00Z")] * 2})
    out, _ = build_haze(load_indonesia(), fires, NOW, {}, get=fake_get(), sleep=lambda s: None)
    assert out["fires"]["count"] == 1 and len(out["fires"]["points"]) == 1
