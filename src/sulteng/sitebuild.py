"""Assemble the static site: pages, data files and the brief."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from sulteng.brief import render_brief

CHROME_CANDIDATES = (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def find_chrome() -> str | None:
    for candidate in CHROME_CANDIDATES:
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    return None


def build(root: Path, out: Path, *, chrome: str | None) -> list[str]:
    """Build the site into `out`; return notes about anything that was skipped."""
    notes: list[str] = []
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(root / "site", out)
    data = out / "data"
    data.mkdir(exist_ok=True)
    for source in (root / "data" / "public", root / "data" / "live"):
        if source.exists():
            shutil.copytree(source, data, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "*.part"))
        else:
            notes.append(f"{source.relative_to(root)} not found")
    now_path = data / "now.json"
    if not now_path.exists():
        notes.append("no now.json: brief not built")
        return notes
    page = out / "ringkasan.html"
    page.write_text(render_brief(json.loads(now_path.read_text(encoding="utf-8"))), encoding="utf-8")
    if chrome is None:
        notes.append("Chrome not found: ringkasan.pdf not built")
        return notes
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
         "--print-to-pdf-no-header", f"--print-to-pdf={out / 'ringkasan.pdf'}", page.resolve().as_uri()],
        check=True, capture_output=True, timeout=180,
    )
    return notes
