import numpy as np
import pandas as pd

from conftest import make_detections
from sulteng.config import MaskParams
from sulteng.masks import Masks, build_masks, categorize, masks_from_json, masks_to_json, static_sites

MP = MaskParams(archive_years=(2023, 2024, 2025), cell_deg=0.005, min_calendar_months=7, min_years=2,
                archive_min_last_modified="2025-06-01")
NO_CELLS = pd.MultiIndex.from_arrays([np.array([], dtype=np.int64)] * 2, names=["iy", "ix"])
YEAR_ROUND = [f"2023-{m:02d}" for m in range(1, 6)] + [f"2024-{m:02d}" for m in range(6, 10)]


def monthly(lat, lon, year_months, kind=0):
    return [(lat, lon, f"{ym}-15 05:30", kind) for ym in year_months]


def test_year_round_source_is_static():
    archive = make_detections(monthly(-1.5012, 120.2512, YEAR_ROUND))
    out = categorize(archive, build_masks(archive, MP))
    assert (out["category"] == "static_suspect").all()


def test_dry_season_fires_are_not_static():
    yms = [f"{y}-{m:02d}" for y in (2023, 2024, 2025) for m in (7, 8, 9, 10)]
    archive = make_detections(monthly(-1.5012, 120.2512, yms))
    out = categorize(archive, build_masks(archive, MP))
    assert (out["category"] == "other").all()


def test_neighbouring_cells_pool_across_the_equator():
    rows = [((0.001 if i % 2 else -0.001), 120.0012, f"{ym}-15 05:30", 0) for i, ym in enumerate(YEAR_ROUND)]
    archive = make_detections(rows)
    out = categorize(archive, build_masks(archive, MP))
    assert (out["category"] == "static_suspect").all()


def test_type_flags_and_precedence():
    det = make_detections([
        (-1.5, 120.25, "2023-08-01 05:30", 1),
        (-1.5, 120.35, "2023-08-01 05:30", 2),
        (-1.5, 120.45, "2023-08-01 05:30", 0),
        (-1.5, 120.55, "2023-08-01 05:30", None),
    ])
    masks = Masks(cell_deg=0.005, static=NO_CELLS, volcano=NO_CELLS)
    assert list(categorize(det, masks)["category"]) == ["volcano", "static_suspect", "other", "other"]


def test_near_real_time_points_take_flags_from_archive_masks():
    archive = make_detections([(-1.5, 120.25, "2023-08-01 05:30", 1), (-1.5, 120.35, "2023-08-01 05:30", 2)])
    masks = build_masks(archive, MP)
    recent = make_detections([
        (-1.5003, 120.2502, "2026-10-01 05:30", None),
        (-1.5003, 120.3502, "2026-10-01 05:30", None),
        (-1.9000, 120.9000, "2026-10-01 05:30", None),
    ]).drop(columns="type")
    assert list(categorize(recent, masks)["category"]) == ["volcano", "static_suspect", "other"]


def test_masks_json_round_trip():
    archive = make_detections([(-1.5, 120.25, "2023-08-01 05:30", 1), (-1.5, 120.35, "2023-08-01 05:30", 2)])
    masks = build_masks(archive, MP)
    back = masks_from_json(masks_to_json(masks, {"note": "x"}))
    assert back.cell_deg == masks.cell_deg
    assert set(back.static) == set(masks.static)
    assert set(back.volcano) == set(masks.volcano)
    assert len(back.volcano) == 9  # the cell and its 8 neighbours


def test_static_sites_group_nearby_detections():
    det = make_detections([
        (-1.5000, 120.2500, "2023-08-01 05:30", 2),
        (-1.5010, 120.2510, "2023-09-01 05:30", 2),
        (-1.5020, 120.2490, "2024-01-01 05:30", 2),
        (-1.9000, 120.9000, "2023-08-01 05:30", 2),
    ]).assign(province="Alfa", district=["A1", "A1", "A1", "A2"])
    sites = static_sites(categorize(det, Masks(0.005, NO_CELLS, NO_CELLS)), 0.005)
    assert list(sites["detections"]) == [3, 1]
    assert list(sites["site_id"]) == ["S001", "S002"]
    assert list(sites["district"]) == ["A1", "A2"]
    assert sites.loc[0, "calendar_months"] == 3 and sites.loc[0, "years"] == 2
    assert sites.loc[0, "type2_share"] == 1.0
