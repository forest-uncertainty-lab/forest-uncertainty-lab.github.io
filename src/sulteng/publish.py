"""Write JSON and GeoJSON outputs safely."""

from __future__ import annotations

import datetime as dt
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd


def to_public(obj):
    """Plain JSON types; floats rounded to 4 places; NaN and infinity are errors."""
    if isinstance(obj, dict):
        return {str(k): to_public(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_public(v) for v in obj]
    if obj is None or obj is pd.NA or obj is pd.NaT:
        return None
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        value = float(obj)
        if not math.isfinite(value):
            raise ValueError("NaN or infinity in public output")
        return round(value, 4)
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    return obj


def write_json(obj, path: Path | str) -> None:
    path = Path(path)
    text = json.dumps(to_public(obj), ensure_ascii=False, separators=(",", ":"))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def point_feature(lon: float, lat: float, properties: dict) -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": properties}


def feature_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}
