import numpy as np
import pandas as pd

from conftest import make_detections
from sulteng.config import MaskParams
from sulteng.masks import (
    SITE_ID_COLUMNS, Masks, build_masks, categorize, masks_from_json, masks_to_json, read_site_ids,
    site_ids_from_features, static_sites, within_years, write_site_ids,
)

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


def test_recurrence_counts_wita_months():
    # Night passes at 17:30 UTC on a month's last day fall on the 1st of the next month in WITA.
    day = [(-1.5012, 120.2512, f"2023-{m:02d}-15 05:30", 0) for m in (1, 2, 3, 4)]
    night = [(-1.5012, 120.2512, t, 0) for t in ("2023-04-30 17:30", "2024-05-31 17:30", "2024-06-30 17:30")]
    archive = make_detections(day + night)  # WITA months 1-7 over 2023-2024; UTC months only 1-6
    out = categorize(archive, build_masks(archive, MP))
    assert (out["category"] == "static_suspect").all()


def test_static_site_months_and_years_are_wita():
    det = make_detections([
        (-1.5000, 120.2500, "2023-08-01 05:30", 2),
        (-1.5010, 120.2510, "2023-12-31 17:30", 2),  # 2024-01-01 01:30 WITA
    ]).assign(province="Alfa", district="A1")
    sites, _ = static_sites(categorize(det, Masks(0.005, NO_CELLS, NO_CELLS)), 0.005)
    assert sites.loc[0, "calendar_months"] == 2 and sites.loc[0, "years"] == 2
    assert sites.loc[0, "last_date"] == "2024-01-01"


def test_archive_is_cut_to_whole_wita_years():
    det = make_detections([
        (-1.5, 120.25, "2023-01-01 05:30", 0),
        (-1.5, 120.25, "2025-12-31 05:30", 0),
        (-1.5, 120.25, "2025-12-31 17:30", 0),  # 2026-01-01 WITA: outside a 2023-2025 archive
    ])
    assert list(within_years(det, (2023, 2024, 2025))["local_date"]) == ["2023-01-01", "2025-12-31"]


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
    sites, ids = static_sites(categorize(det, Masks(0.005, NO_CELLS, NO_CELLS)), 0.005)
    assert list(sites["detections"]) == [3, 1]
    assert list(sites["site_id"]) == ["S001", "S002"]
    assert list(ids["site_id"]) == ["S001", "S002"] and set(ids["status"]) == {"active"}
    assert list(sites["district"]) == ["A1", "A2"]
    assert sites.loc[0, "calendar_months"] == 3 and sites.loc[0, "years"] == 2
    assert sites.loc[0, "type2_share"] == 1.0


# Two places for the site ID tests: A has three flagged detections, B one.
A = (-1.5000, 120.2500)
B = (-1.9000, 120.9000)


def two_sites():
    det = make_detections([
        (*A, "2023-08-01 05:30", 2),
        (-1.5010, 120.2510, "2023-09-01 05:30", 2),
        (-1.5020, 120.2490, "2024-01-01 05:30", 2),
        (*B, "2023-08-01 05:30", 2),
    ]).assign(province="Alfa", district="A1")
    return categorize(det, Masks(0.005, NO_CELLS, NO_CELLS))


def register(*rows):
    return pd.DataFrame(rows, columns=SITE_ID_COLUMNS)


def ids_by_place(sites):
    return {(round(r.latitude, 1), round(r.longitude, 1)): r.site_id for r in sites.itertuples()}


def test_site_ids_stay_with_their_place():
    known = register(("S001", *B, "active", ""), ("S002", *A, "active", ""))
    sites, ids = static_sites(two_sites(), 0.005, known)
    assert list(sites["detections"]) == [3, 1]  # still largest first
    assert ids_by_place(sites) == {(-1.5, 120.2): "S002", (-1.9, 120.9): "S001"}
    assert list(ids["status"]) == ["active", "active"]


def test_an_id_with_no_detections_nearby_is_retired_and_never_reused():
    # S002 sits just beyond the grouping distance (2 × 0.005°) from B; S001 just inside it from A.
    known = register(("S001", A[0], A[1] + 0.009, "active", ""), ("S002", B[0], B[1] + 0.011, "active", ""))
    sites, ids = static_sites(two_sites(), 0.005, known)
    assert ids_by_place(sites) == {(-1.5, 120.2): "S001", (-1.9, 120.9): "S003"}
    assert list(ids["site_id"]) == ["S001", "S002", "S003"]
    assert list(ids["status"]) == ["active", "gone", "active"]
    assert ids.loc[2, ["latitude", "longitude"]].tolist() == list(B)


def test_merged_sites_keep_the_lowest_id():
    known = register(("S004", *A, "active", ""), ("S002", -1.5020, 120.2490, "active", ""), ("S003", *B, "active", ""))
    sites, ids = static_sites(two_sites(), 0.005, known)
    assert ids_by_place(sites) == {(-1.5, 120.2): "S002", (-1.9, 120.9): "S003"}
    assert ids.set_index("site_id")[["status", "merged_into"]].to_dict("index") == {
        "S002": {"status": "active", "merged_into": ""},
        "S003": {"status": "active", "merged_into": ""},
        "S004": {"status": "merged", "merged_into": "S002"},
    }


def test_a_retired_id_returns_with_its_place():
    known = register(("S001", *B, "active", ""), ("S002", *A, "gone", ""))
    sites, ids = static_sites(two_sites(), 0.005, known)
    assert ids_by_place(sites) == {(-1.5, 120.2): "S002", (-1.9, 120.9): "S001"}
    assert list(ids["status"]) == ["active", "active"]


def test_site_ids_seed_from_published_sites():
    features = [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [122.1639, -2.8505]},
         "properties": {"site_id": "S002", "detections": 3333}},
    ]
    assert site_ids_from_features(features).to_dict("records") == [
        {"site_id": "S002", "latitude": -2.8505, "longitude": 122.1639, "status": "active", "merged_into": ""},
    ]


def test_site_id_register_round_trips_through_csv(tmp_path):
    known = register(("S001", -1.5, 120.25, "active", ""), ("S002", -1.9, 120.9, "merged", "S001"))
    write_site_ids(known, tmp_path / "ids.csv")
    pd.testing.assert_frame_equal(read_site_ids(tmp_path / "ids.csv"), known)


def test_site_without_district_reads_none_not_nan():
    det = make_detections([
        (-1.5000, 120.2500, "2023-08-01 05:30", 2),
        (-1.9000, 120.9000, "2023-08-01 05:30", 2),
    ]).assign(province="Alfa", district=["A1", None])
    sites, _ = static_sites(categorize(det, Masks(0.005, NO_CELLS, NO_CELLS)), 0.005)
    assert sorted(sites["district"], key=str) == ["A1", None]
    assert sites["district"].map(type).tolist().count(float) == 0
