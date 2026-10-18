import json

from sulteng.sitebuild import build
from test_brief import now_json


def test_build_copies_site_and_data_and_renders_brief(tmp_path):
    root = tmp_path / "root"
    (root / "site").mkdir(parents=True)
    (root / "site" / "index.html").write_text("<p>hi</p>")
    (root / "data" / "public").mkdir(parents=True)
    (root / "data" / "public" / "masks.json").write_text("{}")
    live = root / "data" / "live"
    (live / "detections").mkdir(parents=True)
    (live / "detections" / "2026-10.csv").write_text("a\n")
    (live / ".git").mkdir()
    (live / ".git" / "HEAD").write_text("ref")
    (live / "now.json").write_text(json.dumps(now_json([])))

    out = tmp_path / "_site"
    notes = build(root, out, chrome=None)
    assert (out / "index.html").exists()
    assert (out / "data" / "masks.json").exists()
    assert (out / "data" / "detections" / "2026-10.csv").exists()
    assert not (out / "data" / ".git").exists()
    assert (out / "ringkasan.html").read_text().count("DRAF") >= 1
    assert any("Chrome" in n for n in notes)


def test_build_without_live_data_notes_it(tmp_path):
    root = tmp_path / "root"
    (root / "site").mkdir(parents=True)
    (root / "site" / "index.html").write_text("<p>hi</p>")
    notes = build(root, tmp_path / "_site", chrome=None)
    assert any("now.json" in n for n in notes)
