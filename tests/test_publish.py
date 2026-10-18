import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from sulteng.publish import feature_collection, point_feature, write_json


def test_write_json_converts_numpy_dates_and_missing(tmp_path):
    path = tmp_path / "x.json"
    write_json({
        "a": np.int64(3),
        "b": np.float64(1.234567),
        "c": [pd.NA, None, np.bool_(True)],
        "d": pd.Timestamp("2026-10-01T05:30:00Z"),
        "e": date(2026, 10, 1),
    }, path)
    assert json.loads(path.read_text()) == {
        "a": 3, "b": 1.2346, "c": [None, None, True], "d": "2026-10-01T05:30:00+00:00", "e": "2026-10-01",
    }


def test_write_json_rejects_nan_and_writes_nothing(tmp_path):
    with pytest.raises(ValueError, match="NaN"):
        write_json({"x": float("nan")}, tmp_path / "x.json")
    assert not (tmp_path / "x.json").exists()


def test_geojson_helpers():
    fc = feature_collection([point_feature(120.1, -1.2, {"k": 1})])
    assert fc["type"] == "FeatureCollection"
    assert fc["features"][0]["geometry"] == {"type": "Point", "coordinates": [120.1, -1.2]}
