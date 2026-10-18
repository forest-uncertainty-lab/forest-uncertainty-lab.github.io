from conftest import make_detections
from sulteng import store


def rows(*specs):
    """specs: (lat, lon, 'YYYY-MM-DD HH:MM' UTC, category)."""
    det = make_detections([(lat, lon, utc, None) for lat, lon, utc, _ in specs]).drop(columns="type")
    return det.assign(province="Alfa", district="A1", category=[c for *_, c in specs])


def test_combine_dedupes_and_newer_row_wins():
    old = rows((-1.5, 120.25, "2026-10-01 05:30", "other"))
    new = rows((-1.5, 120.25, "2026-10-01 05:30", "static_suspect"), (-1.6, 120.3, "2026-10-02 05:30", "other"))
    out = store.combine(old, new)
    assert len(out) == 2
    assert out.loc[out["latitude"] == -1.5, "category"].item() == "static_suspect"


def test_save_writes_kept_months_and_deletes_others(tmp_path):
    df = rows(
        (-1.5, 120.25, "2026-09-30 17:00", "other"),  # 01:00 WITA on 1 Oct
        (-1.5, 120.26, "2026-09-15 05:00", "other"),
        (-1.5, 120.27, "2026-08-15 05:00", "other"),
    )
    (tmp_path / "2026-07.csv").write_text("stale")
    store.save(tmp_path, df, ["2026-09", "2026-10"])
    assert sorted(p.name for p in tmp_path.glob("*.csv")) == ["2026-09.csv", "2026-10.csv"]
    back = store.load(tmp_path, ["2026-09", "2026-10"])
    assert sorted(back["local_date"]) == ["2026-09-15", "2026-10-01"]
    assert back["acq_time"].str.len().eq(4).all()
    assert str(back["acq_utc"].dt.tz) == "UTC"


def test_load_of_missing_months_is_empty(tmp_path):
    df = store.load(tmp_path, ["2026-10"])
    assert df.empty and list(df.columns) == store.STORE_COLUMNS


def test_saved_rows_dedupe_against_a_fresh_parse(tmp_path):
    df = rows((-2.68407, 115.27225, "2026-10-01 05:59", "other"))
    store.save(tmp_path, df, ["2026-10"])
    assert len(store.combine(store.load(tmp_path, ["2026-10"]), df)) == 1
