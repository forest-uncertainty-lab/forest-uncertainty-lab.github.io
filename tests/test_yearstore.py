from datetime import date, datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from conftest import make_detections
from sulteng.config import load_params
from sulteng.fetch import ManifestEntry
from sulteng.indonesia import load_indonesia
from sulteng.masks import Masks
from sulteng.yearstore import feed_days, ingest, plan_backfill, update_year

HEADER = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
NO_CELLS = pd.MultiIndex.from_arrays([np.array([], dtype=np.int64)] * 2, names=["iy", "ix"])
MASKS = Masks(0.005, NO_CELLS, NO_CELLS)
PROVINCES = gpd.GeoDataFrame({"name": ["Alfa"]}, geometry=[box(120, -2, 121, -1)], crs="EPSG:4326")
NOW = datetime(2026, 7, 20, 6, 0, tzinfo=timezone.utc)
AVAILABILITY = ("data_id,min_date,max_date\nVIIRS_SNPP_SP,2012-01-20,2026-06-30\nVIIRS_SNPP_NRT,2026-07-01,2026-07-20\n"
                "VIIRS_NOAA20_SP,2018-04-01,2026-06-30\nVIIRS_NOAA20_NRT,2026-07-01,2026-07-20\n")


def row(day, time="0530", lat=-1.5, lon=120.5):
    return f"{lat},{lon},330,0.4,0.4,{day},{time},N,VIIRS,n,2,290,5.0,D\n"


def kept(rows, sensor="N"):
    det = make_detections(rows, sensor=sensor).drop(columns="type")
    return det.assign(province="Alfa")


def test_ingest_replaces_only_the_given_days():
    store = {"rows": [["N", "Alfa", "2026-07-01", "2026-07-01", 3, 15.0], ["N", "Alfa", "2026-07-02", "2026-07-02", 4, 20.0]],
             "fetched": {"N": {"2026-07-01": "SP", "2026-07-02": "SP"}}}
    new = kept([(-1.5, 120.5, "2026-07-02 05:30", None)])
    out = ingest(store, "N", new, ["2026-07-02"], "NRT", raw_days={"2026-07-02"})
    assert out["rows"] == [["N", "Alfa", "2026-07-01", "2026-07-01", 3, 15.0], ["N", "Alfa", "2026-07-02", "2026-07-02", 1, 5.0]]
    assert out["fetched"]["N"] == {"2026-07-01": "SP", "2026-07-02": "NRT"}


def test_ingest_marks_days_without_raw_rows_empty():
    out = ingest({}, "N", kept([]), ["2026-07-03"], "NRT", raw_days=set())
    assert out["fetched"]["N"]["2026-07-03"] == "empty-NRT" and out["rows"] == []


def test_feed_days_drop_the_partial_first_day():
    raw = make_detections([(-1.5, 120.5, f"2026-07-{d:02d} 05:30", None) for d in (13, 14, 15, 15)])
    assert feed_days(raw) == ["2026-07-14", "2026-07-15"]


def test_plan_prefers_sp_and_refetches_nrt_days_sp_now_covers():
    store = {"fetched": {"N": {"2026-06-29": "NRT", "2026-06-30": "SP", "2026-07-01": "feed"}}}
    plan = plan_backfill(store, date(2026, 6, 27), date(2026, 7, 2), {"N": (date(2026, 6, 30), date(2026, 7, 1)), "N20": (None, None)})
    assert plan == [("N", "SP", date(2026, 6, 27), 3), ("N", "NRT", date(2026, 7, 2), 1)]


def test_plan_asks_noaa20_only_for_suomi_gap_days():
    store = {"fetched": {"N": {"2026-07-10": "NRT", "2026-07-11": "empty-NRT", "2026-07-12": "empty-NRT"}}}
    plan = plan_backfill(store, date(2026, 7, 10), date(2026, 7, 12), {"N": (date(2026, 6, 30), date(2026, 7, 1)),
                                                                        "N20": (date(2026, 6, 30), date(2026, 7, 1))})
    assert plan == [("N20", "NRT", date(2026, 7, 11), 2)]


def test_plan_caps_requests_per_run():
    plan = plan_backfill({}, date(2026, 1, 1), date(2026, 6, 30), {"N": (date(2026, 6, 30), None), "N20": (None, None)}, max_requests=4)
    assert len(plan) == 4 and plan[0] == ("N", "SP", date(2026, 1, 1), 5) and plan[3][2] == date(2026, 1, 16)


class FakeFetch:
    """Writes CSV text chosen from the request label (the key is masked there)."""

    def __init__(self, answer):
        self.answer, self.labels = answer, []

    def __call__(self, url, dest, *, label=None, **_):
        self.labels.append(label)
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_text(self.answer(label))
        return ManifestEntry(url=label, file=Path(dest).name, bytes=1, sha256="x", retrieved_at="t", last_modified=None)


def run_update(tmp_path, store, fetch, map_key="KEY"):
    return update_year(store, load_params(), load_indonesia(), PROVINCES, MASKS, tmp_path, NOW, map_key=map_key, fetch=fetch)


def test_empty_api_day_is_a_gap_not_refetched(tmp_path, monkeypatch):
    monkeypatch.setattr("sulteng.yearstore.first_day", lambda ind, now: date(2026, 7, 11))
    (tmp_path / "feed_N.csv").write_text(HEADER + row("2026-07-16") + row("2026-07-17") + row("2026-07-20"))

    def answer(label):
        if "data_availability" in label:
            return AVAILABILITY
        return HEADER + ("" if "2026-07-11" in label else row("2026-07-13"))

    fetch = FakeFetch(answer)
    store, status = run_update(tmp_path, {}, fetch)
    assert store["fetched"]["N"]["2026-07-11"] == "empty-NRT"
    assert all("***" in label and "KEY" not in label for label in fetch.labels)
    again = FakeFetch(answer)
    run_update(tmp_path, store, again)
    assert not any("VIIRS_SNPP_NRT" in label and "2026-07-11" in label for label in again.labels)
    assert status["backfill"] == "ok" and status["requests"] >= 1


def test_update_year_without_key_reads_feeds_only(tmp_path):
    (tmp_path / "feed_N.csv").write_text(HEADER + row("2026-07-18") + row("2026-07-19") + row("2026-07-19", lon=130.0))
    fetch = FakeFetch(lambda label: "")
    store, status = run_update(tmp_path, {}, fetch, map_key=None)
    assert fetch.labels == [] and status["backfill"] == "no key"
    assert store["rows"] == [["N", "Alfa", "2026-07-19", "2026-07-19", 1, 5.0]]  # 18th is the partial first feed day
    assert store["fetched"]["N"] == {"2026-07-19": "feed"}
