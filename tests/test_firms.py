import pytest

from sulteng.firms import COLUMNS, SchemaError, read_archive, read_nrt

ARCHIVE = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight,type
-2.68407,115.27225,331.22,0.47,0.4,2023-01-01,0559,N,VIIRS,n,2,286.06,2.68,D,0
-2.16171,115.58096,334.23,0.49,0.4,2023-01-01,559,N,VIIRS,h,2,286.64,5.88,D,2
"""

NRT = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight
-8.36666,141.28905,348.64,0.55,0.68,2026-10-11,0332,N,nominal,2.0NRT,304.98,14.73,D
-7.75267,140.33269,367,0.62,0.72,2026-10-11,1745,N,high,2.0NRT,302.89,13.96,N
"""


def write(tmp_path, text, name="f.csv"):
    path = tmp_path / name
    path.write_text(text)
    return path


def test_read_archive(tmp_path):
    df = read_archive(write(tmp_path, ARCHIVE), utc_offset_hours=8)
    assert list(df.columns) == COLUMNS
    assert list(df["acq_time"]) == ["0559", "0559"]
    assert list(df["confidence"]) == ["n", "h"]
    assert list(df["type"]) == [0, 2]
    assert str(df["type"].dtype) == "Int64"
    assert str(df["acq_utc"].dt.tz) == "UTC"
    assert (df["sensor"] == "N").all()


def test_read_nrt_normalises_confidence_and_has_no_type(tmp_path):
    df = read_nrt(write(tmp_path, NRT), sensor="N20", utc_offset_hours=8)
    assert list(df["confidence"]) == ["n", "h"]
    assert df["type"].isna().all()
    assert (df["sensor"] == "N20").all()


def test_local_date_crosses_midnight(tmp_path):
    df = read_nrt(write(tmp_path, NRT), sensor="N", utc_offset_hours=8)
    # 03:32 UTC is 11:32 WITA the same day; 17:45 UTC is 01:45 WITA the next day
    assert list(df["acq_date"]) == ["2026-10-11", "2026-10-11"]
    assert list(df["local_date"]) == ["2026-10-11", "2026-10-12"]


def test_missing_column_is_rejected(tmp_path):
    text = NRT.replace("acq_date,", "day,")
    with pytest.raises(SchemaError, match="acq_date"):
        read_nrt(write(tmp_path, text), sensor="N", utc_offset_hours=8)


def test_archive_requires_type(tmp_path):
    with pytest.raises(SchemaError, match="type"):
        read_archive(write(tmp_path, NRT), utc_offset_hours=8)


@pytest.mark.parametrize("body", ["<html><body>Service unavailable</body></html>", "Invalid MAP_KEY.", ""])
def test_non_firms_bodies_are_rejected(tmp_path, body):
    with pytest.raises(SchemaError):
        read_nrt(write(tmp_path, body), sensor="N", utc_offset_hours=8)


def test_unknown_confidence_is_rejected(tmp_path):
    with pytest.raises(SchemaError, match="confidence"):
        read_nrt(write(tmp_path, NRT.replace("nominal", "medium")), sensor="N", utc_offset_hours=8)


def test_header_only_file_gives_empty_frame(tmp_path):
    df = read_nrt(write(tmp_path, NRT.splitlines()[0] + "\n"), sensor="N", utc_offset_hours=8)
    assert df.empty and list(df.columns) == COLUMNS
