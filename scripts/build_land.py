"""Coastlines for the haze map: Natural Earth 1:50m countries, clipped to the map box and simplified.

Writes data/public/land.json as a list of rings ([[lon, lat], ...]). Run once; the output is committed.
"""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import box

from sulteng.config import ROOT
from sulteng.indonesia import load_indonesia
from sulteng.publish import write_json

SOURCE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_admin_0_countries.geojson"


def main() -> None:
    land = gpd.read_file(SOURCE).clip(box(*load_indonesia().map_bbox)).explode(index_parts=False)
    land = land[land.to_crs(6933).area > 2e7]  # islands under 20 km² do not show at this scale
    rings = [[[round(x, 2), round(y, 2)] for x, y in poly.exterior.simplify(0.03).coords] for poly in land.geometry]
    write_json({"source": "Natural Earth 1:50m admin 0 countries v5.1.2", "rings": rings}, ROOT / "data" / "public" / "land.json")
    print(f"wrote {len(rings)} rings")


if __name__ == "__main__":
    main()
