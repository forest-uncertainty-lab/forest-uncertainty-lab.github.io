import pytest

from sulteng.config import DEFAULT_PARAMS, load_params


def test_default_params_load():
    p = load_params()
    assert len(p.provinces) == 11
    assert p.focus_province == "Sulawesi Tengah"
    assert [s.code for s in p.sensors] == ["N", "N20", "N21"]
    assert p.masks.archive_years == (2023, 2024, 2025)
    assert p.archive_url_for(2024).endswith("viirs-snpp_2024_Indonesia.csv")


def test_rejects_focus_outside_province_list(tmp_path):
    text = DEFAULT_PARAMS.read_text().replace('focus_province = "Sulawesi Tengah"', 'focus_province = "Bali"')
    path = tmp_path / "params.toml"
    path.write_text(text)
    with pytest.raises(ValueError, match="Bali"):
        load_params(path)


def test_rejects_api_chunk_over_ten_days(tmp_path):
    text = DEFAULT_PARAMS.read_text().replace("api_days_per_request = 5", "api_days_per_request = 30")
    path = tmp_path / "params.toml"
    path.write_text(text)
    with pytest.raises(ValueError, match="api_days_per_request"):
        load_params(path)


def test_archive_cutoff_is_loaded():
    assert load_params().masks.archive_min_last_modified == "2025-06-01"


def test_rejects_malformed_archive_cutoff(tmp_path):
    text = DEFAULT_PARAMS.read_text().replace('archive_min_last_modified = "2025-06-01"', 'archive_min_last_modified = "June 2025"')
    path = tmp_path / "params.toml"
    path.write_text(text)
    with pytest.raises(ValueError, match="archive_min_last_modified"):
        load_params(path)
