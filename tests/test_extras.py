import json
from datetime import datetime, timezone

from shapely.geometry import box, mapping

from sulteng.extras import refresh_extras
from sulteng.fetch import FetchError
from sulteng.indonesia import load_indonesia

HEADER = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
NOW = datetime(2026, 3, 18, 6, 0, tzinfo=timezone.utc)


def minimal_root(tmp_path):
    names = [r.name for r in load_indonesia().regions]
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "data" / "public").mkdir(parents=True)
    (tmp_path / "data" / "boundaries").mkdir(parents=True)
    rows = "".join(f"-0.9,119.9,330,0.4,0.4,2026-03-{d},0530,N,VIIRS,n,2,290,5.0,D\n" for d in (15, 16, 17))
    (tmp_path / "data" / "raw" / "feed_N.csv").write_text(HEADER + rows)
    (tmp_path / "data" / "public" / "history_archive.json").write_text(json.dumps({
        "years": [2025], "provinces": names, "count": [[[0.0] * 52] for _ in names], "frp": [[[0] * 52] for _ in names],
        "filled_days": [[0] * 52], "missing_days": [[0] * 52], "ratio": {"2025": 1.0}}))
    (tmp_path / "data" / "public" / "masks.json").write_text(json.dumps({"cell_deg": 0.005, "static": [], "volcano": []}))
    (tmp_path / "data" / "boundaries" / "indonesia.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "Sulawesi Tengah", "island": "Sulawesi", "area_km2": 1.0},
         "geometry": mapping(box(119, -2, 121, 0))}]}))
    return tmp_path


def test_extras_record_a_haze_failure_and_still_write_history(tmp_path):
    root = minimal_root(tmp_path)

    def get(url, **_):
        raise FetchError("open-meteo down" if "open-meteo" in url else "nea down")

    status = refresh_extras(root, NOW, None, get=get)
    live = root / "data" / "live"
    page = json.loads((live / "history.json").read_text())
    assert page["years"] == [2025, 2026] and page["latest_day"] == "2026-03-17"
    assert status["history"]["backfill"] == "no key"
    assert len(status["haze"]["errors"]) == 3 and json.loads((live / "haze.json").read_text())["errors"]
    assert json.loads((live / "status_extra.json").read_text()) == status


def test_extras_isolate_an_unexpected_error(tmp_path):
    root = minimal_root(tmp_path)
    (root / "data" / "public" / "history_archive.json").write_text("{}")  # broken archive

    def get(url, **_):
        raise FetchError("offline")

    status = refresh_extras(root, NOW, None, get=get)
    assert status["history"]["status"] == "failed" and "KeyError" in status["history"]["error"]
    assert (root / "data" / "live" / "haze.json").exists()
