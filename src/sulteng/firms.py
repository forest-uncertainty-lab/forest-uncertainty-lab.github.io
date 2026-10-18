"""Read FIRMS VIIRS CSVs (yearly archive and near-real-time) into one schema."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUMNS = [
    "sensor", "latitude", "longitude", "acq_date", "acq_time", "acq_utc",
    "local_date", "confidence", "frp", "daynight", "type",
]
_REQUIRED = ("latitude", "longitude", "acq_date", "acq_time", "confidence", "frp", "daynight")
_CONFIDENCE = {"l": "l", "n": "n", "h": "h", "low": "l", "nominal": "n", "high": "h"}


class SchemaError(ValueError):
    """The file is not a FIRMS VIIRS CSV in the expected format."""


def read_archive(path, *, utc_offset_hours: int, sensor: str = "N") -> pd.DataFrame:
    return _read(Path(path), sensor, utc_offset_hours, require_type=True)


def read_nrt(path, *, sensor: str, utc_offset_hours: int) -> pd.DataFrame:
    return _read(Path(path), sensor, utc_offset_hours, require_type=False)


def local_dates(acq_utc: pd.Series, utc_offset_hours: int) -> pd.Series:
    return (acq_utc + pd.Timedelta(hours=utc_offset_hours)).dt.strftime("%Y-%m-%d")


def _read(path: Path, sensor: str, offset: int, require_type: bool) -> pd.DataFrame:
    try:
        raw = pd.read_csv(path, dtype={"acq_date": str, "acq_time": str, "confidence": str})
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise SchemaError(f"{path.name}: not a FIRMS CSV ({exc})") from exc
    required = _REQUIRED + (("type",) if require_type else ())
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise SchemaError(f"{path.name}: missing column(s) {', '.join(missing)}")

    hhmm = raw["acq_time"].astype(str).str.strip().str.zfill(4)
    try:
        acq_utc = pd.to_datetime(
            raw["acq_date"].astype(str).str.strip() + " " + hhmm, format="%Y-%m-%d %H%M", utc=True
        )
        latitude = raw["latitude"].astype(float)
        longitude = raw["longitude"].astype(float)
        frp = raw["frp"].astype(float)
        if "type" in raw.columns:
            kind = raw["type"].astype("Int64")
        else:
            kind = pd.Series(pd.NA, index=raw.index, dtype="Int64")
    except (ValueError, TypeError) as exc:
        raise SchemaError(f"{path.name}: bad value ({exc})") from exc
    if acq_utc.isna().any():
        raise SchemaError(f"{path.name}: rows without acquisition date or time")

    confidence = raw["confidence"].astype(str).str.strip().str.lower().map(_CONFIDENCE)
    if confidence.isna().any():
        bad = sorted(set(raw.loc[confidence.isna(), "confidence"].astype(str)))
        raise SchemaError(f"{path.name}: unexpected confidence values {bad}")

    out = pd.DataFrame({
        "sensor": pd.Series(sensor, index=raw.index, dtype=object),
        "latitude": latitude,
        "longitude": longitude,
        "acq_date": acq_utc.dt.strftime("%Y-%m-%d"),
        "acq_time": hhmm,
        "acq_utc": acq_utc,
        "local_date": local_dates(acq_utc, offset),
        "confidence": confidence,
        "frp": frp,
        "daynight": raw["daynight"].astype(str),
        "type": kind,
    })
    return out[COLUMNS]
