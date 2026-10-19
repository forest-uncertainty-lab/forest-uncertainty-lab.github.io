"""Rolling store of detections: one CSV per WITA month."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

DETECTION_COLUMNS = [
    "sensor", "latitude", "longitude", "acq_date", "acq_time", "acq_utc", "local_date",
    "confidence", "frp", "daynight", "province", "district",
]
STORE_COLUMNS = DETECTION_COLUMNS + ["category"]  # category is recomputed from the masks on every refresh
KEY = ["sensor", "latitude", "longitude", "acq_date", "acq_time"]
_TEXT = ["sensor", "acq_date", "acq_time", "local_date", "confidence", "daynight", "province", "district", "category"]


def empty() -> pd.DataFrame:
    df = pd.DataFrame({c: pd.Series(dtype=object) for c in STORE_COLUMNS})
    df["acq_utc"] = pd.to_datetime(df["acq_utc"], utc=True)
    return df


def load(store_dir: Path | str, months) -> pd.DataFrame:
    frames = []
    for month in months:
        path = Path(store_dir) / f"{month}.csv"
        if path.exists():
            frames.append(pd.read_csv(path, dtype={c: str for c in _TEXT}))
    if not frames:
        return empty()
    df = pd.concat(frames, ignore_index=True)
    df["acq_utc"] = pd.to_datetime(df["acq_utc"], utc=True)
    return df[STORE_COLUMNS]


def combine(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Union of both frames' detection columns, without category. When a detection is in both,
    the row from `new` wins."""
    frames = [f[DETECTION_COLUMNS] for f in (existing, new) if not f.empty]
    if not frames:
        return empty()[DETECTION_COLUMNS]
    both = pd.concat(frames, ignore_index=True)
    return both.drop_duplicates(subset=KEY, keep="last").reset_index(drop=True)


def save(store_dir: Path | str, df: pd.DataFrame, months) -> None:
    """Write one CSV per month in `months`; delete CSVs of any other month."""
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    month_of = df["local_date"].str[:7]
    for month in months:
        part = df[month_of == month].sort_values(["acq_utc", "sensor", "latitude", "longitude"])
        path = store_dir / f"{month}.csv"
        tmp = path.with_name(path.name + ".part")
        part[STORE_COLUMNS].to_csv(tmp, index=False)
        os.replace(tmp, path)
    keep = set(months)
    for path in store_dir.glob("*.csv"):
        if path.stem not in keep:
            path.unlink()
