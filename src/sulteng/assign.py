"""Attach province and district to detections inside the study provinces."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from sulteng.boundaries import EQUAL_AREA_CRS, WGS84


def assign(detections: pd.DataFrame, provinces: gpd.GeoDataFrame, districts: gpd.GeoDataFrame) -> pd.DataFrame:
    """Rows inside a study province, with `province` and `district` added; all other rows are dropped.

    The district is the one containing the point, or the nearest district of the same province
    (coastal points can fall just outside simplified district polygons).
    """
    det = detections.reset_index(drop=True)
    empty = det.iloc[0:0].assign(province=pd.Series(dtype=object), district=pd.Series(dtype=object))
    if det.empty:
        return empty
    points = gpd.GeoDataFrame(det, geometry=gpd.points_from_xy(det["longitude"], det["latitude"]), crs=WGS84)
    inside = gpd.sjoin(points, provinces[["name", "geometry"]], predicate="within", how="inner")
    inside = inside[~inside.index.duplicated(keep="first")]
    if inside.empty:
        return empty
    inside = inside.drop(columns="index_right").rename(columns={"name": "province"})

    parts = []
    for province, group in inside.groupby("province", sort=False):
        candidates = districts.loc[districts["province"] == province, ["district", "geometry"]]
        if candidates.empty:
            parts.append(pd.DataFrame(group.drop(columns="geometry")).assign(district=None))
            continue
        nearest = gpd.sjoin_nearest(group.to_crs(EQUAL_AREA_CRS), candidates.to_crs(EQUAL_AREA_CRS), how="left")
        nearest = nearest[~nearest.index.duplicated(keep="first")]
        parts.append(pd.DataFrame(nearest.drop(columns=["geometry", "index_right"])))
    return pd.concat(parts).sort_index()
