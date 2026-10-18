"""Counts per time window, province and district, ready for the site."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from sulteng.config import Params
from sulteng.coverage import day_status
from sulteng.masks import CATEGORIES

MONTHS_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def local_today(now_utc: datetime, utc_offset_hours: int) -> date:
    return (now_utc + timedelta(hours=utc_offset_hours)).date()


def previous_month(day: date) -> tuple[date, date]:
    last = day.replace(day=1) - timedelta(days=1)
    return last.replace(day=1), last


def kept_months(now_utc: datetime, utc_offset_hours: int) -> list[str]:
    today = local_today(now_utc, utc_offset_hours)
    first, _ = previous_month(today)
    return [first.strftime("%Y-%m"), today.strftime("%Y-%m")]


def windows(now_utc: datetime, utc_offset_hours: int) -> dict[str, dict]:
    today = local_today(now_utc, utc_offset_hours)
    prev_first, prev_last = previous_month(today)
    offset = timedelta(hours=utc_offset_hours)

    def by_time(label, hours):
        start = now_utc - timedelta(hours=hours)
        return {"label": label, "kind": "utc", "start": start, "end": now_utc,
                "first_day": (start + offset).date(), "last_day": today}

    def by_day(label, first, last):
        return {"label": label, "kind": "local", "start": first, "end": last, "first_day": first, "last_day": last}

    return {
        "24h": by_time("24 jam terakhir", 24),
        "7d": by_time("7 hari terakhir", 24 * 7),
        "this_month": by_day(f"{MONTHS_ID[today.month - 1]} {today.year} (sampai hari ini)", today.replace(day=1), today),
        "last_month": by_day(f"{MONTHS_ID[prev_first.month - 1]} {prev_first.year}", prev_first, prev_last),
    }


def select(df: pd.DataFrame, window: dict) -> pd.DataFrame:
    if window["kind"] == "utc":
        return df[(df["acq_utc"] > window["start"]) & (df["acq_utc"] <= window["end"])]
    local = df["local_date"]
    return df[(local >= window["start"].isoformat()) & (local <= window["end"].isoformat())]


def counts(frame: pd.DataFrame) -> dict:
    cats = frame["category"].value_counts()
    conf = frame["confidence"].value_counts()
    return {
        "all": int(len(frame)),
        **{c: int(cats.get(c, 0)) for c in CATEGORIES},
        "confidence": {k: int(conf.get(k, 0)) for k in ("l", "n", "h")},
        "sensors": {str(k): int(v) for k, v in frame["sensor"].value_counts().items()},
    }


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def summarize(df: pd.DataFrame, coverage: dict, params: Params, areas: dict[str, float], now_utc: datetime) -> dict:
    offset = params.utc_offset_hours
    sensors = [s.code for s in params.sensors]
    focus = params.focus_province
    out = {}
    for key, w in windows(now_utc, offset).items():
        chosen = select(df, w)
        status = [day_status(coverage, sensors, d, offset) for d in _days(w["first_day"], w["last_day"])]
        provinces = []
        for p in params.provinces:
            c = counts(chosen[chosen["province"] == p.name])
            area = float(areas[p.name])
            provinces.append({
                "name": p.name,
                "island": p.island,
                "area_km2": area,
                "counts": c,
                "per_1000_km2": {"all": c["all"] / area * 1000, "other": c["other"] / area * 1000},
            })
        in_focus = chosen[chosen["province"] == focus]
        districts = [{"district": d, "counts": counts(g)} for d, g in in_focus.groupby("district")]
        districts.sort(key=lambda r: (-r["counts"]["other"], -r["counts"]["all"], r["district"]))
        out[key] = {
            "label": w["label"],
            "start": w["start"],
            "end": w["end"],
            "coverage": {"days": len(status), **{s: status.count(s) for s in ("complete", "partial", "missing")}},
            "provinces": provinces,
            "focus_districts": districts,
        }
    return {
        "generated_at": now_utc.isoformat(timespec="seconds"),
        "utc_offset_hours": offset,
        "focus": focus,
        "sensors": [{"code": s.code, "name": s.name} for s in params.sensors],
        "windows": out,
        "daily": daily_series(df, coverage, params, now_utc),
    }


def daily_series(df: pd.DataFrame, coverage: dict, params: Params, now_utc: datetime) -> list[dict]:
    """Focus-province counts per WITA day for last month and this month; None where no data exists."""
    offset = params.utc_offset_hours
    sensors = [s.code for s in params.sensors]
    today = local_today(now_utc, offset)
    first, _ = previous_month(today)
    focus = df[df["province"] == params.focus_province]
    per_day = focus.groupby(["local_date", "category"]).size()
    rows = []
    for d in _days(first, today):
        state = day_status(coverage, sensors, d, offset)
        key = d.isoformat()
        values = None if state == "missing" else {c: int(per_day.get((key, c), 0)) for c in CATEGORIES}
        rows.append({"date": key, "coverage": state, "counts": values})
    return rows
