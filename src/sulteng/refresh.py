"""One refresh run: download the feeds, update the store, write summaries and status."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd

from sulteng import coverage as cov
from sulteng import store
from sulteng.assign import assign
from sulteng.config import Params, Sensor
from sulteng.fetch import FetchError, download
from sulteng.firms import SchemaError, read_nrt
from sulteng.masks import Masks, categorize
from sulteng.publish import feature_collection, point_feature, write_json
from sulteng.summary import kept_months, local_today, previous_month, summarize

# The FIRMS API keeps ingesting passes for hours after they happen, so a backfill never claims
# coverage for the last day; the 7-day feeds cover that span.
API_SETTLED = timedelta(hours=24)


@dataclass(frozen=True)
class Paths:
    live: Path  # published live outputs and the rolling store
    raw: Path  # downloads; never published

    @property
    def store(self) -> Path:
        return self.live / "detections"


def run_refresh(
    params: Params,
    provinces: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    masks: Masks,
    paths: Paths,
    now_utc: datetime,
    *,
    map_key: str | None = None,
    fetch=download,
) -> dict:
    previous = _read_json(paths.live / "status.json")
    coverage = _read_json(paths.live / "coverage.json")
    attempt = now_utc.isoformat(timespec="seconds")

    frames: list[pd.DataFrame] = []
    sensors: dict[str, dict] = {}
    for sensor in params.sensors:
        got, errors, coverage = _collect(sensor, params, provinces, paths, now_utc, coverage, map_key, fetch)
        frames.extend(got)
        state = "ok" if got and not errors else ("partial" if got else "failed")
        last = attempt if got else previous.get("sensors", {}).get(sensor.code, {}).get("last_success")
        sensors[sensor.code] = {
            "name": sensor.name,
            "status": state,
            "rows": sum(len(f) for f in got),
            "errors": errors,
            "last_success": last,
        }
    backfill = {
        "enabled": bool(map_key),
        "note": None if map_key else "FIRMS_MAP_KEY not set: only the 7-day feeds were read",
    }

    if not frames:
        status = {"status": "update_failed", "last_attempt": attempt, "last_success": previous.get("last_success"),
                  "sensors": sensors, "backfill": backfill}
        write_json(status, paths.live / "status.json")
        return status

    offset = params.utc_offset_hours
    months = kept_months(now_utc, offset)
    new = assign(pd.concat(frames, ignore_index=True), provinces, districts)
    combined = store.combine(store.load(paths.store, months), new)
    combined = combined[combined["local_date"].str[:7].isin(months)]
    combined = categorize(combined, masks)[store.STORE_COLUMNS]
    store.save(paths.store, combined, months)

    first_kept = date.fromisoformat(f"{months[0]}-01")
    coverage = cov.prune(coverage, cov.day_bounds(first_kept, offset)[0])
    areas = dict(zip(provinces["name"], provinces["area_km2"].astype(float)))
    write_json(coverage, paths.live / "coverage.json")
    write_json(summarize(combined, coverage, params, areas, now_utc), paths.live / "now.json")
    write_json(focus_geojson(combined, params.focus_province), paths.live / "focus_detections.geojson")

    overall = "ok" if all(s["status"] == "ok" for s in sensors.values()) else "partial"
    status = {"status": overall, "last_attempt": attempt, "last_success": attempt,
              "sensors": sensors, "backfill": backfill}
    write_json(status, paths.live / "status.json")
    return status


def _collect(sensor: Sensor, params: Params, provinces, paths: Paths, now_utc: datetime, coverage: dict,
             map_key: str | None, fetch):
    """Frames for one sensor from its 7-day feed and, with a key, the API; plus errors and new coverage."""
    offset = params.utc_offset_hours
    got: list[pd.DataFrame] = []
    errors: list[str] = []
    dest = paths.raw / f"feed_{sensor.code}.csv"
    try:
        fetch(sensor.feed_url, dest)
        frame = read_nrt(dest, sensor=sensor.code, utc_offset_hours=offset)
    except (FetchError, SchemaError) as exc:
        errors.append(f"7-day feed: {exc}")
    else:
        got.append(frame)
        seen = cov.observed_interval(frame["acq_utc"])
        if seen:
            coverage = cov.add(coverage, sensor.code, *seen)

    if not map_key:
        return got, errors, coverage
    today = local_today(now_utc, offset)
    first, _ = previous_month(today)
    bbox = _bbox(provinces)
    requests = cov.backfill_requests(coverage, sensor.code, first, today - timedelta(days=1), offset,
                                     params.api_days_per_request)
    for start_day, days in requests:
        fields = {"source": sensor.api_source, "bbox": bbox, "days": days, "date": start_day.isoformat()}
        dest = paths.raw / f"api_{sensor.code}_{start_day.isoformat()}_{days}.csv"
        try:
            fetch(params.api_url.format(key=map_key, **fields), dest, label=params.api_url.format(key="***", **fields))
            frame = read_nrt(dest, sensor=sensor.code, utc_offset_hours=offset)
        except (FetchError, SchemaError) as exc:
            errors.append(f"API {start_day.isoformat()} +{days}d: {exc}")
            continue
        if frame.empty:  # an empty answer is not evidence of zero detections
            errors.append(f"API {start_day.isoformat()} +{days}d: no rows")
            continue
        got.append(frame)
        begin = datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc)
        end = min(begin + timedelta(days=days), now_utc - API_SETTLED)
        if end > begin:
            coverage = cov.add(coverage, sensor.code, begin, end)
    return got, errors, coverage


def _bbox(provinces: gpd.GeoDataFrame) -> str:
    west, south, east, north = provinces.total_bounds
    rounded = (math.floor(west * 100), math.floor(south * 100), math.ceil(east * 100), math.ceil(north * 100))
    return ",".join(f"{v / 100:.2f}" for v in rounded)


def focus_geojson(df: pd.DataFrame, focus: str) -> dict:
    rows = df[df["province"] == focus].sort_values(["acq_utc", "sensor"])
    return feature_collection([
        point_feature(r.longitude, r.latitude, {
            "sensor": r.sensor,
            "utc": r.acq_utc,
            "local_date": r.local_date,
            "confidence": r.confidence,
            "frp": None if pd.isna(r.frp) else r.frp,
            "category": r.category,
            "district": r.district if isinstance(r.district, str) else None,
        })
        for r in rows.itertuples(index=False)
    ])


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
