import json

import pytest

from sulteng.config import ROOT, load_params
from sulteng.indonesia import INDONESIA_CONFIG, load_indonesia

ISLANDS = {"Sumatra", "Java", "Bali and Nusa Tenggara", "Kalimantan", "Sulawesi", "Maluku and Papua"}


def test_indonesia_has_34_provinces_in_six_islands():
    ind = load_indonesia()
    assert len(ind.regions) == 34 and len({r.source_name for r in ind.regions}) == 34
    assert len({r.name for r in ind.regions}) == 34
    assert ind.regions[0].island == "Sumatra" and ind.regions[-1].source_name == "Papua"
    assert {r.island for r in ind.regions} == ISLANDS
    central = next(r for r in ind.regions if r.source_name == "Central Sulawesi")
    assert (central.name, central.name_en, central.island_id) == ("Sulawesi Tengah", "Central Sulawesi", "Sulawesi")


def test_regions_match_geoboundaries():
    path = ROOT / "data" / "raw" / "adm1.geojson"
    if not path.exists():
        pytest.skip("geoBoundaries ADM1 not downloaded")
    names = {f["properties"]["shapeName"] for f in json.loads(path.read_text())["features"]}
    assert {r.source_name for r in load_indonesia().regions} == names


def test_provinces_feed_the_boundary_loader():
    provinces = load_indonesia().provinces()
    assert len(provinces) == 34
    assert next(p for p in provinces if p.source_name == "Papua").name == "Papua"


def test_cities_carry_their_clock():
    c = {c.key: c for c in load_indonesia().cities}
    assert len(c) == 9
    assert (c["singapore"].tz, c["palangka-raya"].tz, c["palu"].tz) == ("SGT", "WIB", "WITA")
    assert c["palu"].utc_offset == 8 and c["jakarta"].utc_offset == 7
    assert (c["singapore"].country, c["kuala-lumpur"].country, c["pontianak"].country) == ("sg", "my", "id")


def test_archive_span_and_boxes():
    ind = load_indonesia()
    assert (ind.archive_first, ind.archive_last) == (2013, 2025)
    assert ind.area_bbox == "94.5,-11.5,141.5,6.5"
    assert ind.map_bbox == (95.0, -11.0, 141.0, 8.0)


def test_rejects_unknown_island(tmp_path):
    text = INDONESIA_CONFIG.read_text().replace('island = "Sulawesi"', 'island = "Atlantis"', 1)
    path = tmp_path / "indonesia.toml"
    path.write_text(text)
    with pytest.raises(ValueError, match="Atlantis"):
        load_indonesia(path)


def test_availability_url_is_loaded():
    assert load_params().availability_url.endswith("/api/data_availability/csv/{key}/ALL")
