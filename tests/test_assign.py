import pandas as pd

from conftest import PROVINCES, make_detections, write_boxes
from sulteng.assign import assign
from sulteng.boundaries import load_districts, load_provinces


def load(boundary_files):
    adm1, adm2 = boundary_files
    provinces = load_provinces(adm1, PROVINCES)
    return provinces, load_districts(adm2, provinces)


def test_assigns_province_and_district_and_drops_outside(boundary_files):
    provinces, districts = load(boundary_files)
    det = make_detections([
        (-1.5, 120.25, "2026-10-01 05:00", None),
        (-1.5, 120.75, "2026-10-01 05:00", None),
        (-1.5, 114.50, "2026-10-01 05:00", None),
        (-1.5, 100.50, "2026-10-01 05:00", None),  # Gamma: not a study province
        (-1.5, 117.00, "2026-10-01 05:00", None),  # sea
    ])
    out = assign(det, provinces, districts)
    assert list(out["province"]) == ["Alfa", "Alfa", "Beta"]
    assert list(out["district"]) == ["Distrik A1", "Distrik A2", "Distrik B1"]
    assert list(out.columns)[-2:] == ["province", "district"]


def test_nearest_district_of_same_province_when_outside_all_districts(boundary_files, tmp_path):
    adm1, _ = boundary_files
    provinces = load_provinces(adm1, PROVINCES)
    adm2 = write_boxes(tmp_path / "gappy.geojson", [
        ("Distrik A1", (120.0, -2.0, 120.5, -1.0)),
        ("Distrik B1", (114.0, -2.0, 115.0, -1.0)),
    ])
    out = assign(make_detections([(-1.5, 120.9, "2026-10-01 05:00", None)]), provinces, load_districts(adm2, provinces))
    assert list(out["district"]) == ["Distrik A1"]


def test_duplicate_input_index_and_empty_input(boundary_files):
    provinces, districts = load(boundary_files)
    one = make_detections([(-1.5, 120.25, "2026-10-01 05:00", None)])
    out = assign(pd.concat([one, one]), provinces, districts)
    assert len(out) == 2
    empty = assign(one.iloc[0:0], provinces, districts)
    assert empty.empty and {"province", "district"} <= set(empty.columns)
