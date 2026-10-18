"""Group points that lie close together."""

from __future__ import annotations

import geopandas as gpd
import numpy as np


def group_nearby(lat, lon, radius_deg: float) -> np.ndarray:
    """One integer label per point. Points within about 2 × radius_deg of each other, chained, share a label."""
    points = gpd.GeoSeries(gpd.points_from_xy(np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)))
    if points.empty:
        return np.array([], dtype=np.int64)
    blobs = gpd.GeoSeries([points.buffer(radius_deg, quad_segs=4).union_all()])
    blobs = blobs.explode(index_parts=False).reset_index(drop=True)
    joined = gpd.sjoin(
        gpd.GeoDataFrame(geometry=points), gpd.GeoDataFrame(geometry=blobs), predicate="intersects", how="left"
    )
    joined = joined[~joined.index.duplicated(keep="first")]
    return joined["index_right"].to_numpy(dtype=np.int64)
