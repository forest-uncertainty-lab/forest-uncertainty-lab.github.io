"""The years after the archive: Suomi NPP and NOAA-20 detections per province and day, kept up to date.

Each refresh replaces the days the 7-day feeds cover, then backfills the rest of the year through the
FIRMS area API: standard (SP) data where FIRMS has it, near-real-time (NRT) after that. NOAA-20 is
fetched only for days Suomi NPP missed, to fill those gaps. A day re-fetched later from SP replaces
its NRT or feed version, so the store converges on the data the archive years use.

Store: {"rows": [[sensor, province, local_date, utc_date, count, frp], ...],
        "fetched": {sensor: {utc_date: "SP" | "NRT" | "feed" | "empty-SP" | "empty-NRT" | "empty-feed"}}}
"""

from __future__ import annotations

import csv
import io
from collections.abc import Collection
from datetime import date, datetime, timedelta
from pathlib import Path

import geopandas as gpd
import pandas as pd

from sulteng.config import Params
from sulteng.fetch import FetchError, download
from sulteng.firehistory import keep_fires
from sulteng.firms import SchemaError, read_nrt
from sulteng.indonesia import Indonesia
from sulteng.masks import Masks

OFFSET = 8  # fire weeks are counted in UTC+8 for the whole country
MAX_DAYS = 5  # the FIRMS area API returns at most five days per request
API_PREFIX = {"N": "VIIRS_SNPP", "N20": "VIIRS_NOAA20"}


def first_day(ind: Indonesia, now_utc: datetime) -> date:
    """The first day the archive does not hold."""
    return date(ind.archive_last + 1, 1, 1)


def ingest(store: dict, sensor: str, kept: pd.DataFrame, utc_days: Collection[str], source: str,
           raw_days: Collection[str]) -> dict:
    """Replace `sensor`'s rows on `utc_days` with `kept`, and record where each day came from."""
    days = set(utc_days)
    rows = [r for r in store.get("rows", []) if not (r[0] == sensor and r[3] in days)]
    part = kept[kept["acq_date"].isin(days)] if len(kept) else kept
    if len(part):
        grouped = part.groupby(["province", "local_date", "acq_date"]).agg(count=("frp", "size"), frp=("frp", "sum"))
        rows += [[sensor, p, local, utc, int(r["count"]), round(float(r["frp"]), 1)]
                 for (p, local, utc), r in grouped.iterrows()]
    rows.sort(key=lambda r: (r[3], r[0], r[1], r[2]))
    fetched = {s: dict(v) for s, v in store.get("fetched", {}).items()}
    raw = set(raw_days)
    fetched.setdefault(sensor, {}).update({d: source if d in raw else f"empty-{source}" for d in days})
    return {"rows": rows, "fetched": fetched}


def feed_days(raw: pd.DataFrame) -> list[str]:
    """UTC days of a 7-day feed, without the first one, which the feed covers only in part."""
    return sorted(raw["acq_date"].unique())[1:]


def _source(day: date, sp_last: date | None, nrt_first: date | None) -> str | None:
    if sp_last is not None and day <= sp_last:
        return "SP"
    if nrt_first is not None and day >= nrt_first:
        return "NRT"
    return None


def _needed(state: str | None, source: str | None) -> bool:
    if source is None:
        return False
    if state is None:
        return True
    return source == "SP" and state in ("NRT", "feed", "empty-NRT", "empty-feed")


def plan_backfill(store: dict, first: date, last: date, availability: dict[str, tuple[date | None, date | None]],
                  *, max_requests: int = 30) -> list[tuple[str, str, date, int]]:
    """(sensor, source, first day, days) requests: Suomi NPP days missing or now covered by SP, and NOAA-20
    on the days Suomi NPP came back empty. At most `max_requests`, oldest first."""
    fetched = store.get("fetched", {})
    plan: list[tuple[str, str, date, int]] = []
    for sensor in ("N", "N20"):
        sp_last, nrt_first = availability.get(sensor, (None, None))
        own = fetched.get(sensor, {})
        day = first
        while day <= last:
            iso = day.isoformat()
            wanted = sensor == "N" or fetched.get("N", {}).get(iso, "").startswith("empty")
            source = _source(day, sp_last, nrt_first)
            if wanted and _needed(own.get(iso), source):
                prev = plan[-1] if plan else None
                if prev and prev[:2] == (sensor, source) and prev[2] + timedelta(days=prev[3]) == day and prev[3] < MAX_DAYS:
                    plan[-1] = (sensor, source, prev[2], prev[3] + 1)
                else:
                    plan.append((sensor, source, day, 1))
            day += timedelta(days=1)
    return plan[:max_requests]


def _availability(text: str) -> dict[str, tuple[date | None, date | None]]:
    ranges = {r["data_id"]: r for r in csv.DictReader(io.StringIO(text))}

    def bound(data_id: str, field: str) -> date | None:
        return date.fromisoformat(ranges[data_id][field]) if data_id in ranges else None

    return {sensor: (bound(f"{prefix}_SP", "max_date"), bound(f"{prefix}_NRT", "min_date"))
            for sensor, prefix in API_PREFIX.items()}


def update_year(store: dict, params: Params, ind: Indonesia, provinces: gpd.GeoDataFrame, masks: Masks,
                raw_dir: Path | str, now_utc: datetime, *, map_key: str | None, fetch=download) -> tuple[dict, dict]:
    """Bring the store up to date from the feeds in `raw_dir` and, with a key, the FIRMS API."""
    raw_dir = Path(raw_dir)
    first, last = first_day(ind, now_utc), now_utc.date()
    start = first.isoformat()
    store = {"rows": [r for r in store.get("rows", []) if r[3] >= start],
             "fetched": {s: {d: v for d, v in days.items() if d >= start} for s, days in store.get("fetched", {}).items()}}
    for code in API_PREFIX:
        path = raw_dir / f"feed_{code}.csv"
        if not path.exists():
            continue
        raw = read_nrt(path, sensor=code, utc_offset_hours=OFFSET)
        days = [d for d in feed_days(raw) if start <= d <= last.isoformat()]
        kept = keep_fires(raw[raw["acq_date"].isin(days)], provinces, masks)
        store = ingest(store, code, kept, days, "feed", set(raw["acq_date"]))
    if not map_key:
        return store, {"backfill": "no key", "requests": 0, "errors": []}

    work = raw_dir / "year"
    try:
        fetch(params.availability_url.format(key=map_key), work / "availability.csv",
              label=params.availability_url.format(key="***"))
        availability = _availability((work / "availability.csv").read_text(encoding="utf-8"))
    except (FetchError, KeyError, ValueError) as exc:
        return store, {"backfill": "partial", "requests": 0, "errors": [f"availability: {exc}"]}
    errors, done = [], 0
    for sensor, source, begin, days in plan_backfill(store, first, last, availability):
        fields = {"source": f"{API_PREFIX[sensor]}_{source}", "bbox": ind.area_bbox, "days": days, "date": begin.isoformat()}
        dest = work / f"{sensor}_{source}_{begin.isoformat()}_{days}.csv"
        try:
            fetch(params.api_url.format(key=map_key, **fields), dest, label=params.api_url.format(key="***", **fields))
            raw = read_nrt(dest, sensor=sensor, utc_offset_hours=OFFSET)
        except (FetchError, SchemaError) as exc:
            errors.append(f"{sensor} {source} {begin.isoformat()} +{days}d: {exc}")
            continue
        done += 1
        span = [(begin + timedelta(days=i)).isoformat() for i in range(days)]
        store = ingest(store, sensor, keep_fires(raw, provinces, masks), span, source, set(raw["acq_date"]))
    return store, {"backfill": "partial" if errors else "ok", "requests": done, "errors": errors}
