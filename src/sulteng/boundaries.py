"""Province and district polygons for the 11 study provinces."""

from __future__ import annotations

import geopandas as gpd
import shapely

from sulteng.config import Province

EQUAL_AREA_CRS = "EPSG:6933"
WGS84 = "EPSG:4326"


def load_provinces(path, provinces: tuple[Province, ...]) -> gpd.GeoDataFrame:
    """The study provinces with Indonesian names, island and land area (km²), in config order."""
    gdf = gpd.read_file(path)
    if "shapeName" not in gdf.columns:
        raise ValueError(f"{path}: no shapeName column")
    by_source = {p.source_name: p for p in provinces}
    missing = sorted(set(by_source) - set(gdf["shapeName"]))
    if missing:
        raise ValueError(f"{path}: provinces not found: {', '.join(missing)}")
    gdf = gdf[gdf["shapeName"].isin(by_source)].to_crs(WGS84)
    gdf = gdf.dissolve(by="shapeName", as_index=False)
    out = gpd.GeoDataFrame(
        {
            "name": [by_source[s].name for s in gdf["shapeName"]],
            "island": [by_source[s].island for s in gdf["shapeName"]],
        },
        geometry=gdf.geometry.to_numpy(),
        crs=WGS84,
    )
    out["area_km2"] = out.to_crs(EQUAL_AREA_CRS).area / 1e6
    order = {p.name: i for i, p in enumerate(provinces)}
    return out.sort_values("name", key=lambda s: s.map(order)).reset_index(drop=True)


def load_districts(path, provinces: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Districts whose representative point lies in a study province, tagged with that province."""
    gdf = gpd.read_file(path)
    if "shapeName" not in gdf.columns:
        raise ValueError(f"{path}: no shapeName column")
    gdf = gdf[["shapeName", "geometry"]].rename(columns={"shapeName": "district"}).to_crs(WGS84)
    gdf = gdf.reset_index(drop=True)
    points = gpd.GeoDataFrame(geometry=gdf.representative_point(), crs=WGS84)
    hit = gpd.sjoin(points, provinces[["name", "geometry"]], predicate="within", how="inner")
    hit = hit[~hit.index.duplicated(keep="first")]
    out = gdf.loc[hit.index].assign(province=hit["name"].to_numpy())
    return out[["district", "province", "geometry"]].reset_index(drop=True)


def simplified(gdf: gpd.GeoDataFrame, tolerance: float, grid: float) -> gpd.GeoDataFrame:
    """Copy with simplified geometry snapped to a coordinate grid (keeps polygons valid)."""
    out = gdf.copy()
    geoms = out.geometry.simplify(tolerance, preserve_topology=True).to_numpy()
    out["geometry"] = shapely.set_precision(geoms, grid)
    return out
