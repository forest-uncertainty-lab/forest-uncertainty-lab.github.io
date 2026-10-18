import pytest

from conftest import PROVINCES
from sulteng.boundaries import load_districts, load_provinces, simplified


def test_load_provinces_maps_names_and_area(boundary_files):
    adm1, _ = boundary_files
    gdf = load_provinces(adm1, PROVINCES)
    assert list(gdf["name"]) == ["Alfa", "Beta"]
    assert list(gdf["island"]) == ["Sulawesi", "Kalimantan"]
    # a 1°×1° box near 1.5° S is about 12,350 km²
    assert gdf["area_km2"].between(12_000, 12_600).all()


def test_missing_province_is_named(boundary_files, tmp_path):
    adm1, _ = boundary_files
    from sulteng.config import Province
    wanted = PROVINCES + (Province(source_name="Delta", name="Delta", island="Sulawesi"),)
    with pytest.raises(ValueError, match="Delta"):
        load_provinces(adm1, wanted)


def test_load_districts_keeps_only_study_provinces(boundary_files):
    adm1, adm2 = boundary_files
    districts = load_districts(adm2, load_provinces(adm1, PROVINCES))
    assert sorted(districts["district"]) == ["Distrik A1", "Distrik A2", "Distrik B1"]
    assert dict(zip(districts["district"], districts["province"]))["Distrik B1"] == "Beta"


def test_simplified_keeps_attributes(boundary_files):
    adm1, _ = boundary_files
    gdf = simplified(load_provinces(adm1, PROVINCES), 0.01, 0.001)
    assert list(gdf["name"]) == ["Alfa", "Beta"]
    assert gdf.geometry.is_valid.all()
