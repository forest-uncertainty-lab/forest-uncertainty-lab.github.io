import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import PROVINCES
from sulteng.boundaries import load_districts, load_provinces
from sulteng.config import load_params
from sulteng.fetch import FetchError, ManifestEntry
from sulteng.masks import Masks
from sulteng.refresh import Paths, run_refresh

NOW = datetime(2026, 10, 18, 4, 0, tzinfo=timezone.utc)
HEADER = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight\n"
ROW_ALFA = "-1.5,120.25,340,0.4,0.4,2026-10-17,0530,N,nominal,2.0NRT,290,5.0,D\n"
ROW_SEA = "-1.5,117.0,340,0.4,0.4,2026-10-17,0530,N,nominal,2.0NRT,290,5.0,D\n"
NO_CELLS = pd.MultiIndex.from_arrays([np.array([], dtype=np.int64)] * 2, names=["iy", "ix"])
PARAMS = replace(load_params(), provinces=PROVINCES, focus_province="Alfa")


class FakeFetch:
    def __init__(self, body_for, last_modified="2026-10-18T03:00:00+00:00"):
        self.body_for, self.last_modified, self.calls = body_for, last_modified, []

    def __call__(self, url, dest, label=None):
        self.calls.append((url, label))
        body = self.body_for(url)
        if isinstance(body, Exception):
            raise body
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_text(body)
        return ManifestEntry(url=label or url, file=Path(dest).name, bytes=len(body), sha256="x",
                             retrieved_at=NOW.isoformat(), last_modified=self.last_modified)


@pytest.fixture
def run(tmp_path, boundary_files):
    adm1, adm2 = boundary_files
    provinces = load_provinces(adm1, PROVINCES)
    districts = load_districts(adm2, provinces)
    paths = Paths(live=tmp_path / "live", raw=tmp_path / "raw")

    def go(fetch, now=NOW, map_key=None):
        return run_refresh(PARAMS, provinces, districts, Masks(0.005, NO_CELLS, NO_CELLS), paths, now,
                           map_key=map_key, fetch=fetch)

    go.paths = paths
    return go


def read(run, name):
    return json.loads((run.paths.live / name).read_text())


def test_all_feeds_ok(run):
    status = run(FakeFetch(lambda url: HEADER + ROW_ALFA + ROW_SEA))
    assert status["status"] == "ok"
    assert set(status["sensors"]) == {"N", "N20", "N21"}
    alfa = read(run, "now.json")["windows"]["24h"]["provinces"][0]
    assert alfa["name"] == "Alfa" and alfa["counts"]["all"] == 3  # one detection per sensor
    assert len(read(run, "focus_detections.geojson")["features"]) == 3
    assert (run.paths.live / "detections" / "2026-10.csv").exists()
    assert (run.paths.live / "detections" / "2026-09.csv").exists()


def test_repeated_runs_do_not_duplicate(run):
    fetch = FakeFetch(lambda url: HEADER + ROW_ALFA)
    run(fetch)
    run(fetch)
    assert read(run, "now.json")["windows"]["24h"]["provinces"][0]["counts"]["all"] == 3


def test_one_sensor_failing_is_partial(run):
    failing = PARAMS.sensors[1].feed_url
    status = run(FakeFetch(lambda url: FetchError("down") if url == failing else HEADER + ROW_ALFA))
    assert status["status"] == "partial"
    assert status["sensors"]["N20"]["status"] == "failed"
    assert read(run, "coverage.json").get("N20", []) == []


def test_html_pages_everywhere_is_update_failed(run):
    run(FakeFetch(lambda url: HEADER + ROW_ALFA))
    before = (run.paths.live / "now.json").read_text()
    later = datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc)
    status = run(FakeFetch(lambda url: "<html><body>Maintenance</body></html>"), now=later)
    assert status["status"] == "update_failed"
    assert status["last_attempt"] == later.isoformat(timespec="seconds")
    assert status["last_success"] == NOW.isoformat(timespec="seconds")
    assert (run.paths.live / "now.json").read_text() == before
    assert read(run, "status.json")["status"] == "update_failed"


def test_empty_feeds_are_ok_with_zero(run):
    status = run(FakeFetch(lambda url: HEADER))
    assert status["status"] == "ok"
    assert read(run, "now.json")["windows"]["24h"]["provinces"][0]["counts"]["all"] == 0


def test_backfill_requests_and_key_redaction(run):
    def body(url):
        if "/api/" in url:
            return FetchError("HTTP 500") if "VIIRS_NOAA21_NRT" in url else HEADER
        return HEADER + ROW_ALFA

    fetch = FakeFetch(body)
    status = run(fetch, map_key="SECRET123")
    api_calls = [(url, label) for url, label in fetch.calls if "/api/" in url]
    assert api_calls
    assert all("SECRET123" in url and "SECRET123" not in label and "***" in label for url, label in api_calls)
    assert all(int(url.split("/")[-2]) <= PARAMS.api_days_per_request for url, _ in api_calls)
    assert "SECRET123" not in json.dumps(status)
    assert "SECRET123" not in (run.paths.live / "status.json").read_text()
    assert status["sensors"]["N21"]["status"] == "partial"
    assert status["sensors"]["N"]["status"] == "ok"


def test_no_key_means_no_api_calls(run):
    fetch = FakeFetch(lambda url: HEADER)
    status = run(fetch)
    assert not [url for url, _ in fetch.calls if "/api/" in url]
    assert status["backfill"]["enabled"] is False


def test_feed_coverage_follows_the_data_not_the_file_time(run):
    # The file is stamped 18 Oct 03:00Z, but it still holds a pass from 10 Oct 05:30Z (13:30 WITA).
    old_row = "-1.5,120.25,340,0.4,0.4,2026-10-10,0530,N,nominal,2.0NRT,290,5.0,D\n"
    run(FakeFetch(lambda url: HEADER + old_row + ROW_ALFA))
    coverage = read(run, "coverage.json")
    assert coverage["N"] == [["2026-10-10T05:30:00+00:00", "2026-10-17T05:30:00+00:00"]]
    day = next(d for d in read(run, "now.json")["daily"] if d["date"] == "2026-10-10")
    assert day["coverage"] == "partial"
    assert day["counts"]["other"] == 3  # one detection per sensor, shown rather than hidden


def test_empty_feeds_claim_no_coverage(run):
    run(FakeFetch(lambda url: HEADER))
    assert all(spans == [] for spans in read(run, "coverage.json").values())
    window = read(run, "now.json")["windows"]["24h"]
    assert window["coverage"]["missing"] == window["coverage"]["days"]
