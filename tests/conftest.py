import json
from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import box, mapping

from sulteng.config import Province

PROVINCES = (
    Province(source_name="Alpha", name="Alfa", island="Sulawesi"),
    Province(source_name="Beta", name="Beta", island="Kalimantan"),
)


def make_detections(rows, sensor="N", offset=8):
    """rows: (lat, lon, 'YYYY-MM-DD HH:MM' UTC, FIRMS type or None)."""
    df = pd.DataFrame(rows, columns=["latitude", "longitude", "utc", "type"])
    acq_utc = pd.to_datetime(df["utc"], utc=True)
    return pd.DataFrame({
        "sensor": sensor,
        "latitude": df["latitude"].astype(float),
        "longitude": df["longitude"].astype(float),
        "acq_date": acq_utc.dt.strftime("%Y-%m-%d"),
        "acq_time": acq_utc.dt.strftime("%H%M"),
        "acq_utc": acq_utc,
        "local_date": (acq_utc + pd.Timedelta(hours=offset)).dt.strftime("%Y-%m-%d"),
        "confidence": "n",
        "frp": 5.0,
        "daynight": "D",
        "type": df["type"].astype("Int64"),
    })


def write_boxes(path: Path, features) -> Path:
    collection = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"shapeName": name}, "geometry": mapping(box(*bounds))}
            for name, bounds in features
        ],
    }
    path.write_text(json.dumps(collection))
    return path


@pytest.fixture
def boundary_files(tmp_path):
    adm1 = write_boxes(tmp_path / "adm1.geojson", [
        ("Alpha", (120.0, -2.0, 121.0, -1.0)),
        ("Beta", (114.0, -2.0, 115.0, -1.0)),
        ("Gamma", (100.0, -2.0, 101.0, -1.0)),
    ])
    adm2 = write_boxes(tmp_path / "adm2.geojson", [
        ("Distrik A1", (120.0, -2.0, 120.5, -1.0)),
        ("Distrik A2", (120.5, -2.0, 121.0, -1.0)),
        ("Distrik B1", (114.0, -2.0, 115.0, -1.0)),
        ("Distrik G1", (100.0, -2.0, 101.0, -1.0)),
    ])
    return adm1, adm2
