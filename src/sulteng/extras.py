"""The refresh steps behind Haze, Explained: the fire history of the current year and the haze snapshot.

Each step records its own outcome in data/live/status_extra.json; a failure in one never stops the
other, or the Sulawesi Tengah refresh that runs before them.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import geopandas as gpd
import pandas as pd

from sulteng.config import load_params
from sulteng.fetch import download, get_json
from sulteng.firehistory import unmasked
from sulteng.firms import SchemaError, read_nrt
from sulteng.haze import build_haze
from sulteng.historypage import build_history_page
from sulteng.indonesia import load_indonesia
from sulteng.masks import masks_from_json
from sulteng.publish import read_json, write_json
from sulteng.yearstore import OFFSET, update_year

FEEDS = ("N", "N20", "N21")
FIRE_HOURS = 48  # detections drawn under the wind paths


def _failed(exc: Exception) -> dict:
    return {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}


def refresh_extras(root: Path, now_utc: datetime, map_key: str | None, *, get=get_json, fetch=download) -> dict:
    root = Path(root)
    live, raw, public = root / "data" / "live", root / "data" / "raw", root / "data" / "public"
    params, ind = load_params(), load_indonesia()
    masks = masks_from_json(json.loads((public / "masks.json").read_text(encoding="utf-8")))
    status: dict = {}

    try:
        provinces = gpd.read_file(root / "data" / "boundaries" / "indonesia.geojson")
        store, history = update_year(read_json(live / "history_current.json"), params, ind, provinces, masks, raw, now_utc,
                                     map_key=map_key, fetch=fetch)
        write_json(store, live / "history_current.json")
        page = build_history_page(json.loads((public / "history_archive.json").read_text(encoding="utf-8")), store, ind, now_utc)
        write_json(page, live / "history.json")
        status["history"] = {"status": "ok", **history, "latest_day": page["latest_day"]}
    except Exception as exc:  # recorded, never fatal: the haze step and the published site go on
        status["history"] = _failed(exc)

    try:
        haze, track = build_haze(ind, _recent_fires(raw, masks, now_utc), now_utc, read_json(live / "haze_track.json"), get=get)
        write_json(haze, live / "haze.json")
        write_json(track, live / "haze_track.json")
        status["haze"] = {"status": "partial" if haze["errors"] else "ok", "errors": haze["errors"]}
    except Exception as exc:
        status["haze"] = _failed(exc)

    write_json(status, live / "status_extra.json")
    return status


def _recent_fires(raw: Path, masks, now_utc: datetime) -> pd.DataFrame:
    """Detections from the three 7-day feeds in the last 48 hours, volcanoes and static sources left out."""
    frames = []
    for code in FEEDS:
        path = raw / f"feed_{code}.csv"
        if path.exists():
            try:
                frames.append(read_nrt(path, sensor=code, utc_offset_hours=OFFSET))
            except SchemaError:
                continue
    if not frames:
        return pd.DataFrame(columns=["longitude", "latitude", "acq_utc"])
    df = pd.concat(frames, ignore_index=True)
    df = df[df["acq_utc"] > pd.Timestamp(now_utc - timedelta(hours=FIRE_HOURS))]
    return unmasked(df, masks)[["longitude", "latitude", "acq_utc"]]
