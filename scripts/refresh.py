"""Refresh near-real-time detections from the FIRMS feeds, then the fire history and the haze snapshot. Run every few hours.

Reads FIRMS_MAP_KEY from the environment when set, to backfill days the 7-day feeds no longer cover.
Always exits 0 when the run itself completes: status.json records whether the data was updated.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import geopandas as gpd

from sulteng.config import ROOT, load_params
from sulteng.extras import refresh_extras
from sulteng.masks import masks_from_json
from sulteng.refresh import Paths, run_refresh


def main() -> None:
    params = load_params()
    provinces = gpd.read_file(ROOT / "data" / "boundaries" / "provinces.geojson")
    districts = gpd.read_file(ROOT / "data" / "boundaries" / "districts.geojson")
    masks = masks_from_json(json.loads((ROOT / "data" / "public" / "masks.json").read_text(encoding="utf-8")))
    now = datetime.now(timezone.utc)
    map_key = os.environ.get("FIRMS_MAP_KEY") or None
    status = run_refresh(
        params, provinces, districts, masks,
        Paths(live=ROOT / "data" / "live", raw=ROOT / "data" / "raw"),
        now,
        map_key=map_key,
    )
    print(json.dumps(status, ensure_ascii=False, indent=1))
    print(json.dumps(refresh_extras(ROOT, now, map_key), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
