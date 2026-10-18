import hashlib

import pytest

from sulteng.fetch import FetchError, download, load_manifest, save_manifest


def test_download_writes_file_and_hash(tmp_path):
    src = tmp_path / "src.csv"
    src.write_bytes(b"a,b\n1,2\n")
    entry = download(src.as_uri(), tmp_path / "out" / "copy.csv")
    assert (tmp_path / "out" / "copy.csv").read_bytes() == b"a,b\n1,2\n"
    assert entry.sha256 == hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    assert entry.bytes == 8 and entry.file == "copy.csv"
    assert entry.last_modified is not None and entry.last_modified.endswith("+00:00")


def test_missing_source_raises_with_label_and_leaves_nothing(tmp_path):
    secret_url = (tmp_path / "SECRETKEY" / "missing.csv").as_uri()
    with pytest.raises(FetchError) as info:
        download(secret_url, tmp_path / "out.csv", label="api/***/missing", retries=1, backoff=0)
    assert "SECRETKEY" not in str(info.value)
    assert "api/***/missing" in str(info.value)
    assert not (tmp_path / "out.csv").exists()
    assert not (tmp_path / "out.csv.part").exists()


def test_empty_body_is_an_error(tmp_path):
    src = tmp_path / "empty.csv"
    src.write_bytes(b"")
    with pytest.raises(FetchError, match="empty"):
        download(src.as_uri(), tmp_path / "out.csv", retries=0)
    assert not (tmp_path / "out.csv").exists()


def test_manifest_round_trip(tmp_path):
    path = tmp_path / "manifest.json"
    assert load_manifest(path) == {}
    save_manifest(path, {"a.csv": {"sha256": "x"}})
    assert load_manifest(path) == {"a.csv": {"sha256": "x"}}
