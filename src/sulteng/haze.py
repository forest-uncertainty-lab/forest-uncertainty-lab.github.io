"""The haze tab's data: measured air (NEA), model air (CAMS via Open-Meteo), wind back-trajectory
ensembles at three heights over recent fire detections, and the model's track record in Singapore.

Back-trajectories step against the hourly model wind at one pressure level, interpolated between the
1-degree grid points. They ignore vertical motion, turbulence and rain: a guide to where the air came
from, not a smoke model.
"""

from __future__ import annotations

import math
import urllib.parse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from sulteng.fetch import FetchError, get_json
from sulteng.indonesia import City, Indonesia

LEVELS = ("925", "850", "700")  # about 750 m, 1.5 km and 3 km
REGIONS = ("north", "south", "east", "west", "central")
NEA_URL = "https://api-open.data.gov.sg/v2/real-time/api"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WIND_URL = "https://api.open-meteo.com/v1/forecast"
M_PER_DEG = 111_320
POINTS_PER_REQUEST = 100
# Ensemble members: start 0, 1 or 2 hours earlier, each with the wind as given or 10% weaker turned
# 10 degrees one way, or 10% stronger turned the other way. Member 0 is the central path.
OFFSETS = (0, 1, 2)
PERTURBATIONS = ((1.0, 0.0), (0.9, -10.0), (1.1, 10.0))


@dataclass(frozen=True)
class WindField:
    times: np.ndarray  # hours since 1970-01-01 UTC
    lats: np.ndarray
    lons: np.ndarray
    u: dict  # level -> array (time, lat, lon), m/s towards the east
    v: dict  # level -> array (time, lat, lon), m/s towards the north


def _as_list(payload) -> list:
    return payload if isinstance(payload, list) else [payload]


def nea(pm25_days: list[dict], psi: dict) -> dict:
    """NEA's hourly PM2.5 by region (last 48 hours, regions without a reading left out) and the latest 24-hour PSI."""
    hourly = {}
    for payload in pm25_days:
        for item in payload["data"]["items"]:
            regions = {k: v for k, v in item["readings"]["pm25_one_hourly"].items() if v is not None}
            if regions:
                values = list(regions.values())
                hourly[item["timestamp"]] = {"time": item["timestamp"], "lo": min(values), "hi": max(values),
                                             "mean": round(sum(values) / len(values), 1), "regions": regions}
    latest = psi["data"]["items"][0]
    return {
        "pm25_hourly": sorted(hourly.values(), key=lambda h: h["time"])[-48:],
        "psi_time": latest["timestamp"],
        "psi_24h": latest["readings"]["psi_twenty_four_hourly"],
        "pm25_24h": latest["readings"]["pm25_twenty_four_hourly"],
    }


def cams(payloads, cities: Sequence[City]) -> dict:
    """Modelled PM2.5 per city, in the order the cities were requested. Times are GMT."""
    return {c.key: {"time": p["hourly"]["time"], "pm2_5": p["hourly"]["pm2_5"]} for c, p in zip(cities, _as_list(payloads))}


def wind_field(payloads: list[dict], lats: np.ndarray, lons: np.ndarray, levels=LEVELS) -> WindField:
    """Grid of u and v from Open-Meteo speed (m/s) and direction (degrees the wind comes from), lat-major points."""
    times = np.array(payloads[0]["hourly"]["time"], dtype="datetime64[h]").astype(np.int64).astype(float)
    u, v = {}, {}
    for lv in levels:
        speed = np.array([[np.nan if x is None else x for x in p["hourly"][f"wind_speed_{lv}hPa"]] for p in payloads], dtype=float).T
        direction = np.radians(np.array([[np.nan if x is None else x for x in p["hourly"][f"wind_direction_{lv}hPa"]]
                                         for p in payloads], dtype=float).T)
        shape = (len(times), len(lats), len(lons))
        u[lv] = (-speed * np.sin(direction)).reshape(shape)
        v[lv] = (-speed * np.cos(direction)).reshape(shape)
    return WindField(times=times, lats=np.asarray(lats, dtype=float), lons=np.asarray(lons, dtype=float), u=u, v=v)


def _wind(field: WindField, level: str, t_h: float, lat: float, lon: float) -> tuple[float, float] | None:
    ti = int(np.argmin(np.abs(field.times - t_h)))
    if abs(field.times[ti] - t_h) > 1:
        return None
    fy = (lat - field.lats[0]) / (field.lats[1] - field.lats[0])
    fx = (lon - field.lons[0]) / (field.lons[1] - field.lons[0])
    if not (0 <= fy <= len(field.lats) - 1 and 0 <= fx <= len(field.lons) - 1):
        return None
    y0, x0 = min(int(fy), len(field.lats) - 2), min(int(fx), len(field.lons) - 2)
    dy, dx = fy - y0, fx - x0

    def at(a: np.ndarray) -> float:
        return ((1 - dy) * (1 - dx) * a[ti, y0, x0] + (1 - dy) * dx * a[ti, y0, x0 + 1]
                + dy * (1 - dx) * a[ti, y0 + 1, x0] + dy * dx * a[ti, y0 + 1, x0 + 1])

    u, v = at(field.u[level]), at(field.v[level])
    return None if math.isnan(u) or math.isnan(v) else (u, v)


def _inside(field: WindField, lat: float, lon: float) -> bool:
    return field.lats.min() <= lat <= field.lats.max() and field.lons.min() <= lon <= field.lons.max()


def trajectory(field: WindField, level: str, lat: float, lon: float, start_h: float, hours: int = 48,
               speed: float = 1.0, turn_deg: float = 0.0) -> list[list[float]]:
    """[lon, lat, hours back] hourly, stepping against the wind; stops at the grid edge or a missing wind."""
    path = [[round(lon, 3), round(lat, 3), 0]]
    c, s = math.cos(math.radians(turn_deg)), math.sin(math.radians(turn_deg))
    for h in range(1, hours + 1):
        wind = _wind(field, level, start_h - (h - 0.5), lat, lon)
        if wind is None:
            break
        u, v = wind
        u, v = (u * c - v * s) * speed, (u * s + v * c) * speed
        new_lat = lat - v * 3600 / M_PER_DEG
        new_lon = lon - u * 3600 / (M_PER_DEG * math.cos(math.radians(new_lat)))
        if not _inside(field, new_lat, new_lon):
            break
        lat, lon = new_lat, new_lon
        path.append([round(lon, 3), round(lat, 3), h])
    return path


def ensemble(field: WindField, lat: float, lon: float, now_h: float) -> dict[str, list[list[list[float]]]]:
    """Nine paths per level; the first is the central one (latest hour, wind as given)."""
    return {lv: [trajectory(field, lv, lat, lon, now_h - offset, speed=sp, turn_deg=turn)
                 for offset in OFFSETS for sp, turn in PERTURBATIONS] for lv in LEVELS}


def _any_within(points: np.ndarray, fires: np.ndarray, km: float) -> bool:
    pad = km / 111.0 * 1.5
    lon0, lat0 = points.min(axis=0) - pad
    lon1, lat1 = points.max(axis=0) + pad
    near = fires[(fires[:, 0] >= lon0) & (fires[:, 0] <= lon1) & (fires[:, 1] >= lat0) & (fires[:, 1] <= lat1)]
    if not len(near):
        return False
    p, f = np.radians(points)[:, None, :], np.radians(near)[None, :, :]
    a = np.sin((f[..., 1] - p[..., 1]) / 2) ** 2 + np.cos(p[..., 1]) * np.cos(f[..., 1]) * np.sin((f[..., 0] - p[..., 0]) / 2) ** 2
    return bool((6371 * 2 * np.arcsin(np.sqrt(a)) <= km).any())


def share_near(paths: Sequence, fire_lonlat: np.ndarray, km: float = 50.0) -> float:
    """Share of paths with any point within `km` of a fire detection."""
    fires = np.asarray(fire_lonlat, dtype=float).reshape(-1, 2)
    if not len(paths):
        return 0.0
    hits = sum(_any_within(np.asarray(p, dtype=float)[:, :2], fires, km) for p in paths if len(fires))
    return hits / len(paths)


def binned_fires(df: pd.DataFrame, cell: float = 0.02) -> list[list[float]]:
    """[lon, lat, detections] per grid cell, at the cell centre."""
    if df.empty:
        return []
    ix = np.floor(df["longitude"].to_numpy(dtype=float) / cell).astype(np.int64)
    iy = np.floor(df["latitude"].to_numpy(dtype=float) / cell).astype(np.int64)
    counts = pd.Series(1, index=pd.MultiIndex.from_arrays([ix, iy])).groupby(level=[0, 1]).sum()
    return [[round((x + 0.5) * cell, 3), round((y + 0.5) * cell, 3), int(n)] for (x, y), n in counts.items()]


def track(store: dict, nea_hourly: list[dict], cams_sg: dict, now_utc: datetime, days: int = 30) -> tuple[dict, dict | None]:
    """Pair NEA's hourly mean with the model value for Singapore; keep 30 days; report once a day is in."""
    pairs = dict(store.get("pairs", {}))
    model = dict(zip(cams_sg["time"], cams_sg["pm2_5"]))
    for h in nea_hourly:
        t = datetime.fromisoformat(h["time"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00")
        m = model.get(t)
        if m and h.get("mean") is not None:
            pairs[t] = [h["mean"], m]
    cutoff = (now_utc - timedelta(days=days)).strftime("%Y-%m-%dT%H:00")
    pairs = {t: v for t, v in sorted(pairs.items()) if t >= cutoff}
    if len(pairs) < 24:
        return {"pairs": pairs}, None
    ratios = [a / b for a, b in pairs.values()]
    return {"pairs": pairs}, {"hours": len(pairs), "ratio": tuple(float(q) for q in np.percentile(ratios, (10, 50, 90)))}


def _url(base: str, params: dict) -> str:
    return f"{base}?{urllib.parse.urlencode(params)}"


def build_haze(ind: Indonesia, fires: pd.DataFrame, now_utc: datetime, track_store: dict, *, get=get_json) -> tuple[dict, dict]:
    """The haze snapshot. A source that fails is recorded in `errors`; the others still come through."""
    errors: list[str] = []
    sgt = (now_utc + timedelta(hours=8)).date()
    nea_out = None
    try:
        pm = [get(_url(f"{NEA_URL}/pm25", {"date": d.isoformat()})) for d in (sgt - timedelta(days=1), sgt)]
        nea_out = nea(pm, get(f"{NEA_URL}/psi"))
    except (FetchError, KeyError, IndexError, TypeError) as exc:
        errors.append(f"NEA: {exc}")
    cams_out = {}
    try:
        cams_out = cams(get(_url(AIR_URL, {
            "latitude": ",".join(str(c.lat) for c in ind.cities), "longitude": ",".join(str(c.lon) for c in ind.cities),
            "hourly": "pm2_5", "past_days": 2, "forecast_days": 3, "timezone": "GMT"})), ind.cities)
    except (FetchError, KeyError, TypeError) as exc:
        errors.append(f"CAMS: {exc}")

    west, south, east, north = ind.map_bbox
    lats, lons = np.arange(south, north + 0.5, 1.0), np.arange(west, east + 0.5, 1.0)
    points = [(la, lo) for la in lats for lo in lons]
    hourly = ",".join(f"wind_speed_{lv}hPa,wind_direction_{lv}hPa" for lv in LEVELS)
    trajectories, share = {}, {}
    try:
        payloads = []
        for i in range(0, len(points), POINTS_PER_REQUEST):
            chunk = points[i:i + POINTS_PER_REQUEST]
            payloads += _as_list(get(_url(WIND_URL, {
                "latitude": ",".join(f"{la:g}" for la, _ in chunk), "longitude": ",".join(f"{lo:g}" for _, lo in chunk),
                "hourly": hourly, "past_days": 2, "forecast_days": 1, "wind_speed_unit": "ms", "timezone": "GMT"})))
        field = wind_field(payloads, lats, lons)
        now_h = math.floor(now_utc.timestamp() / 3600)
        fire_ll = fires[["longitude", "latitude"]].to_numpy(dtype=float) if len(fires) else np.empty((0, 2))
        for c in ind.cities:
            ens = ensemble(field, c.lat, c.lon, now_h)
            trajectories[c.key] = ens
            share[c.key] = {lv: round(share_near(members, fire_ll), 3) for lv, members in ens.items()}
    except (FetchError, KeyError, ValueError, TypeError) as exc:
        errors.append(f"winds: {exc}")

    stats = None
    if nea_out and "singapore" in cams_out:
        track_store, stats = track(track_store, nea_out["pm25_hourly"], cams_out["singapore"], now_utc)
    latest = pd.to_datetime(fires["acq_utc"], utc=True).max() if len(fires) else None
    return {
        "generated_at": now_utc.isoformat(timespec="seconds"),
        "cities": [{"key": c.key, "name": c.name, "lat": c.lat, "lon": c.lon, "tz": c.tz, "utc_offset": c.utc_offset,
                    "country": c.country} for c in ind.cities],
        "map_bbox": list(ind.map_bbox),
        "nea": nea_out,
        "cams": cams_out,
        "trajectories": trajectories,
        "share_near": share,
        "fires": {"cell": 0.02, "points": binned_fires(fires), "count": int(len(fires)),
                  "latest_utc": None if latest is None or pd.isna(latest) else latest.isoformat()},
        "track": None if stats is None else {"hours": stats["hours"], "ratio": [round(q, 3) for q in stats["ratio"]]},
        "errors": errors,
    }, track_store
