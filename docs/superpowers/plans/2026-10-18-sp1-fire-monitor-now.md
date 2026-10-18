# SP1 Central Sulawesi Fire Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A static Indonesian website, refreshed every six hours, that shows satellite fire detections in Central Sulawesi for the last 24 hours, 7 days, this month and last month. Industrial heat and volcanoes are counted separately, missing days are shown as missing, and the same window is compared fairly across 11 provinces.

**Architecture:** A Python package (`src/sulteng`) does all data work: it downloads FIRMS VIIRS near-real-time feeds, assigns detections to provinces and districts, flags static sources with masks built once from the 2023–2025 archive, keeps a two-month rolling store, records per-sensor coverage, and writes JSON/GeoJSON summaries. A static site (HTML, CSS, plain JS, Leaflet) reads those files. GitHub Actions runs the refresh and deploys to Pages.

**Tech Stack:** Python 3.11+, pandas, geopandas, shapely 2, pyproj, pyogrio, pytest, uv; Leaflet 1.9.4; headless Chrome for the PDF brief.

**Spec:** `docs/superpowers/specs/2026-10-18-sp1-fire-monitor-now-design.md`

## Global Constraints

- Never call a detection a confirmed fire. Public labels: "Titik panas lain (mungkin kebakaran vegetasi/lahan, belum dikonfirmasi)", "Dugaan sumber panas tetap/industri", "Gunung api".
- Missing data is `null` in JSON and "tidak ada data" on the site, never `0`.
- Static-suspect and volcano detections stay in every "all" total and are always shown as their own counts.
- Dates are WITA (UTC+8), fixed offset.
- Store keeps exactly the previous and current WITA month.
- No paid services. `FIRMS_MAP_KEY` comes only from the environment and never appears in any output or error.
- Indonesian text carries the draft label "DRAF — belum ditinjau mitra LSM".
- Nothing is pushed to a remote. Commits are local. No `Co-Authored-By` or Claude attribution lines in commit messages.
- Tests never touch the network.

## Review Focus

1. All three feeds return an HTML maintenance page: the run must end `update_failed` and leave the previous `now.json` untouched. Pinned in Task 9 (`test_html_pages_everywhere_is_update_failed`).
2. Month rollover on the 1st: the store must drop the month before last, and January must reach back to the previous year's December. Pinned in Task 8 (`test_kept_months_rollover_and_january`).
3. A window where every day is missing must not read as zero. The summary reports `missing == days` (Task 8, `test_window_with_no_coverage_reports_missing_days`), and the site shows "tidak ada data" (Task 13, step 6).
4. Detections between 16:00 and 23:59 UTC belong to the next WITA day. Pinned in Task 3 (`test_local_date_crosses_midnight`).
5. The API key must not leak through errors or status. Pinned in Task 9 (`test_backfill_requests_and_key_redaction`).

---

### Task 1: Project scaffold and configuration

**Files:**
- Create: `pyproject.toml`, `config/params.toml`, `src/sulteng/__init__.py`, `src/sulteng/config.py`, `tests/conftest.py`, `tests/test_config.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `sulteng.config.ROOT`, `DEFAULT_PARAMS`, dataclasses `Province(source_name, name, island)`, `Sensor(code, name, feed_url, api_source)`, `MaskParams(archive_years, cell_deg, min_calendar_months, min_years)`, `Params(...)` with `archive_url_for(year) -> str`; `load_params(path=DEFAULT_PARAMS) -> Params` (raises `ValueError`).
- Produces (tests): `tests/conftest.py` with `PROVINCES`, `make_detections(rows)`, fixture `boundary_files`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "sulteng"
version = "0.1.0"
description = "Near-real-time satellite fire detections for Central Sulawesi"
requires-python = ">=3.11"
dependencies = [
  "pandas>=2.2",
  "geopandas>=1.0",
  "shapely>=2.0",
  "pyproj>=3.6",
  "pyogrio>=0.9",
]

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sulteng"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `config/params.toml`**

```toml
focus_province = "Sulawesi Tengah"
utc_offset_hours = 8        # WITA
feed_latency_hours = 3      # newest hours of a 7-day feed treated as not yet complete
feed_span_hours = 156       # 6.5 days of each 7-day feed counted as covered

[sources]
archive_url = "https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{year}/viirs-snpp_{year}_Indonesia.csv"
adm1_url = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IDN/ADM1/geoBoundaries-IDN-ADM1.geojson"
adm2_url = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IDN/ADM2/geoBoundaries-IDN-ADM2_simplified.geojson"
api_url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{bbox}/{days}/{date}"
api_days_per_request = 5

[masks]
archive_years = [2023, 2024, 2025]
cell_deg = 0.005
min_calendar_months = 7
min_years = 2

[[sensors]]
code = "N"
name = "Suomi NPP"
feed_url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_SouthEast_Asia_7d.csv"
api_source = "VIIRS_SNPP_NRT"

[[sensors]]
code = "N20"
name = "NOAA-20"
feed_url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_SouthEast_Asia_7d.csv"
api_source = "VIIRS_NOAA20_NRT"

[[sensors]]
code = "N21"
name = "NOAA-21"
feed_url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_SouthEast_Asia_7d.csv"
api_source = "VIIRS_NOAA21_NRT"

[[provinces]]
source_name = "West Kalimantan"
name = "Kalimantan Barat"
island = "Kalimantan"

[[provinces]]
source_name = "Central Kalimantan"
name = "Kalimantan Tengah"
island = "Kalimantan"

[[provinces]]
source_name = "South Kalimantan"
name = "Kalimantan Selatan"
island = "Kalimantan"

[[provinces]]
source_name = "East Kalimantan"
name = "Kalimantan Timur"
island = "Kalimantan"

[[provinces]]
source_name = "North Kalimantan"
name = "Kalimantan Utara"
island = "Kalimantan"

[[provinces]]
source_name = "North Sulawesi"
name = "Sulawesi Utara"
island = "Sulawesi"

[[provinces]]
source_name = "Gorontalo"
name = "Gorontalo"
island = "Sulawesi"

[[provinces]]
source_name = "Central Sulawesi"
name = "Sulawesi Tengah"
island = "Sulawesi"

[[provinces]]
source_name = "West Sulawesi"
name = "Sulawesi Barat"
island = "Sulawesi"

[[provinces]]
source_name = "South Sulawesi"
name = "Sulawesi Selatan"
island = "Sulawesi"

[[provinces]]
source_name = "Southeast Sulawesi"
name = "Sulawesi Tenggara"
island = "Sulawesi"
```

- [ ] **Step 3: Write the failing test `tests/test_config.py`**

```python
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
```

- [ ] **Step 4: Write `tests/conftest.py`**

```python
import json
from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import box, mapping

from sulteng.config import Province

PROVINCES = (
    Province(source_name="Alpha", name="Alfa", island="Sulawesi"),
    Province(source_name="Beta", name="Beta", island="Kalimantan"),
)


def make_detections(rows, sensor="N", offset=8):
    """rows: (lat, lon, 'YYYY-MM-DD HH:MM' UTC, FIRMS type or None)."""
    df = pd.DataFrame(rows, columns=["latitude", "longitude", "utc", "type"])
    acq_utc = pd.to_datetime(df["utc"], utc=True)
    return pd.DataFrame({
        "sensor": sensor,
        "latitude": df["latitude"].astype(float),
        "longitude": df["longitude"].astype(float),
        "acq_date": acq_utc.dt.strftime("%Y-%m-%d"),
        "acq_time": acq_utc.dt.strftime("%H%M"),
        "acq_utc": acq_utc,
        "local_date": (acq_utc + pd.Timedelta(hours=offset)).dt.strftime("%Y-%m-%d"),
        "confidence": "n",
        "frp": 5.0,
        "daynight": "D",
        "type": df["type"].astype("Int64"),
    })


def write_boxes(path: Path, features) -> Path:
    collection = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"shapeName": name}, "geometry": mapping(box(*bounds))}
            for name, bounds in features
        ],
    }
    path.write_text(json.dumps(collection))
    return path


@pytest.fixture
def boundary_files(tmp_path):
    adm1 = write_boxes(tmp_path / "adm1.geojson", [
        ("Alpha", (120.0, -2.0, 121.0, -1.0)),
        ("Beta", (114.0, -2.0, 115.0, -1.0)),
        ("Gamma", (100.0, -2.0, 101.0, -1.0)),
    ])
    adm2 = write_boxes(tmp_path / "adm2.geojson", [
        ("Distrik A1", (120.0, -2.0, 120.5, -1.0)),
        ("Distrik A2", (120.5, -2.0, 121.0, -1.0)),
        ("Distrik B1", (114.0, -2.0, 115.0, -1.0)),
        ("Distrik G1", (100.0, -2.0, 101.0, -1.0)),
    ])
    return adm1, adm2
```

- [ ] **Step 5: Install and run the tests to see them fail**

Run: `uv sync && uv run pytest tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sulteng.config'`

- [ ] **Step 6: Write `src/sulteng/__init__.py` and `src/sulteng/config.py`**

`src/sulteng/__init__.py`:

```python
"""Near-real-time satellite fire detections for Central Sulawesi."""
```

`src/sulteng/config.py`:

```python
"""Project parameters, loaded from config/params.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARAMS = ROOT / "config" / "params.toml"


@dataclass(frozen=True)
class Province:
    source_name: str  # shapeName in geoBoundaries ADM1 (English)
    name: str  # Indonesian name, used in every output
    island: str


@dataclass(frozen=True)
class Sensor:
    code: str
    name: str
    feed_url: str  # keyless 7-day regional CSV
    api_source: str  # FIRMS area API source


@dataclass(frozen=True)
class MaskParams:
    archive_years: tuple[int, ...]
    cell_deg: float
    min_calendar_months: int
    min_years: int


@dataclass(frozen=True)
class Params:
    focus_province: str
    utc_offset_hours: int
    feed_latency_hours: int
    feed_span_hours: int
    archive_url: str
    adm1_url: str
    adm2_url: str
    api_url: str
    api_days_per_request: int
    masks: MaskParams
    sensors: tuple[Sensor, ...]
    provinces: tuple[Province, ...]

    def archive_url_for(self, year: int) -> str:
        return self.archive_url.format(year=year)


def load_params(path: Path | str = DEFAULT_PARAMS) -> Params:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    src, mk = raw["sources"], raw["masks"]
    params = Params(
        focus_province=raw["focus_province"],
        utc_offset_hours=int(raw["utc_offset_hours"]),
        feed_latency_hours=int(raw["feed_latency_hours"]),
        feed_span_hours=int(raw["feed_span_hours"]),
        archive_url=src["archive_url"],
        adm1_url=src["adm1_url"],
        adm2_url=src["adm2_url"],
        api_url=src["api_url"],
        api_days_per_request=int(src["api_days_per_request"]),
        masks=MaskParams(
            archive_years=tuple(int(y) for y in mk["archive_years"]),
            cell_deg=float(mk["cell_deg"]),
            min_calendar_months=int(mk["min_calendar_months"]),
            min_years=int(mk["min_years"]),
        ),
        sensors=tuple(Sensor(**s) for s in raw["sensors"]),
        provinces=tuple(Province(**p) for p in raw["provinces"]),
    )
    _validate(params)
    return params


def _validate(p: Params) -> None:
    names = [q.name for q in p.provinces]
    if len(names) != 11 or len(set(names)) != 11:
        raise ValueError(f"expected 11 distinct provinces, found {len(set(names))}")
    if p.focus_province not in names:
        raise ValueError(f"focus province {p.focus_province!r} is not in the province list")
    codes = [s.code for s in p.sensors]
    if not codes or len(set(codes)) != len(codes):
        raise ValueError("sensor codes must be present and distinct")
    if "{year}" not in p.archive_url:
        raise ValueError("archive_url must contain {year}")
    if not 0 < p.feed_latency_hours < p.feed_span_hours <= 168:
        raise ValueError("need 0 < feed_latency_hours < feed_span_hours <= 168")
    if not 1 <= p.api_days_per_request <= 10:
        raise ValueError("api_days_per_request must be between 1 and 10")
    m = p.masks
    if not 0 < m.cell_deg < 0.1:
        raise ValueError("cell_deg must be between 0 and 0.1 degrees")
    if not 1 <= m.min_calendar_months <= 12 or m.min_years < 1:
        raise ValueError("min_calendar_months must be 1-12 and min_years at least 1")
```

- [ ] **Step 7: Extend `.gitignore` and run the tests**

Append `data/live/` and `data/raw/` stays. Final `.gitignore`:

```
data/raw/
data/live/
_site/
.venv/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
```

Run: `uv sync && uv run pytest tests/test_config.py -q`
Expected: `3 passed`

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock config src tests .gitignore
git commit -m "Add project scaffold and validated configuration"
```

---

### Task 2: Downloads

**Files:**
- Create: `src/sulteng/fetch.py`, `tests/test_fetch.py`

**Interfaces:**
- Produces: `FetchError(RuntimeError)`; `ManifestEntry(url, file, bytes, sha256, retrieved_at, last_modified)` (all `str` except `bytes: int`; `last_modified: str | None`, ISO UTC); `download(url, dest, *, label=None, timeout=120, retries=2, backoff=2.0) -> ManifestEntry`; `load_manifest(path) -> dict[str, dict]`; `save_manifest(path, manifest) -> None`; `utc_now_iso() -> str`.

- [ ] **Step 1: Write the failing tests `tests/test_fetch.py`**

```python
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
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/test_fetch.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sulteng.fetch'`

- [ ] **Step 3: Write `src/sulteng/fetch.py`**

```python
"""Downloads with retries, atomic writes and SHA-256 hashes."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

USER_AGENT = "sulteng-remote-sensing/0.1"


class FetchError(RuntimeError):
    """A download failed after every retry, or returned no bytes."""


@dataclass(frozen=True)
class ManifestEntry:
    url: str  # the display label; never contains a secret
    file: str
    bytes: int
    sha256: str
    retrieved_at: str
    last_modified: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def download(
    url: str,
    dest: Path | str,
    *,
    label: str | None = None,
    timeout: float = 120,
    retries: int = 2,
    backoff: float = 2.0,
) -> ManifestEntry:
    """Fetch `url` into `dest`. `label` stands in for the URL in errors and in the returned entry."""
    dest = Path(dest)
    shown = label or url
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                digest, size = hashlib.sha256(), 0
                with tmp.open("wb") as fh:
                    while chunk := response.read(1 << 20):
                        fh.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                last_modified = _http_date(response.headers.get("Last-Modified"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            tmp.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(backoff * 2**attempt)
            continue
        if size == 0:
            tmp.unlink(missing_ok=True)
            raise FetchError(f"{shown}: empty response")
        os.replace(tmp, dest)
        return ManifestEntry(
            url=shown,
            file=dest.name,
            bytes=size,
            sha256=digest.hexdigest(),
            retrieved_at=utc_now_iso(),
            last_modified=last_modified,
        )
    raise FetchError(f"{shown}: {_describe(last_error, secret=label is not None)}") from None


def _describe(exc: Exception | None, *, secret: bool) -> str:
    """Short reason. With a label, echo nothing that could contain the real URL or path."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if secret:
        return type(exc).__name__
    return f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"


def _http_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def load_manifest(path: Path | str) -> dict[str, dict]:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_manifest(path: Path | str, manifest: dict[str, dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
```

Why `_describe` drops the message when a label is set: `urllib` errors for `file://` URLs echo the filesystem path, and other errors can echo the request. With a label, only the exception type or HTTP status is kept, so a key in the URL cannot leak.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_fetch.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sulteng/fetch.py tests/test_fetch.py
git commit -m "Add downloader with retries, hashes and redacted errors"
```

---

### Task 3: FIRMS CSV parsing

**Files:**
- Create: `src/sulteng/firms.py`, `tests/test_firms.py`

**Interfaces:**
- Produces: `SchemaError(ValueError)`; `COLUMNS` = `["sensor","latitude","longitude","acq_date","acq_time","acq_utc","local_date","confidence","frp","daynight","type"]`; `read_archive(path, *, utc_offset_hours, sensor="N") -> DataFrame`; `read_nrt(path, *, sensor, utc_offset_hours) -> DataFrame`; `local_dates(acq_utc: Series, utc_offset_hours) -> Series[str]`.
- Column types: `acq_utc` tz-aware UTC; `acq_date`, `local_date` strings `YYYY-MM-DD`; `acq_time` 4-char string; `confidence` in `l/n/h`; `type` nullable `Int64` (all NA for NRT).

- [ ] **Step 1: Write the failing tests `tests/test_firms.py`**

```python
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
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/test_firms.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sulteng.firms'`

- [ ] **Step 3: Write `src/sulteng/firms.py`**

```python
"""Read FIRMS VIIRS CSVs (yearly archive and near-real-time) into one schema."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUMNS = [
    "sensor", "latitude", "longitude", "acq_date", "acq_time", "acq_utc",
    "local_date", "confidence", "frp", "daynight", "type",
]
_REQUIRED = ("latitude", "longitude", "acq_date", "acq_time", "confidence", "frp", "daynight")
_CONFIDENCE = {"l": "l", "n": "n", "h": "h", "low": "l", "nominal": "n", "high": "h"}


class SchemaError(ValueError):
    """The file is not a FIRMS VIIRS CSV in the expected format."""


def read_archive(path, *, utc_offset_hours: int, sensor: str = "N") -> pd.DataFrame:
    return _read(Path(path), sensor, utc_offset_hours, require_type=True)


def read_nrt(path, *, sensor: str, utc_offset_hours: int) -> pd.DataFrame:
    return _read(Path(path), sensor, utc_offset_hours, require_type=False)


def local_dates(acq_utc: pd.Series, utc_offset_hours: int) -> pd.Series:
    return (acq_utc + pd.Timedelta(hours=utc_offset_hours)).dt.strftime("%Y-%m-%d")


def _read(path: Path, sensor: str, offset: int, require_type: bool) -> pd.DataFrame:
    try:
        raw = pd.read_csv(path, dtype={"acq_date": str, "acq_time": str, "confidence": str})
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise SchemaError(f"{path.name}: not a FIRMS CSV ({exc})") from exc
    required = _REQUIRED + (("type",) if require_type else ())
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise SchemaError(f"{path.name}: missing column(s) {', '.join(missing)}")

    hhmm = raw["acq_time"].astype(str).str.strip().str.zfill(4)
    try:
        acq_utc = pd.to_datetime(
            raw["acq_date"].astype(str).str.strip() + " " + hhmm, format="%Y-%m-%d %H%M", utc=True
        )
        latitude = raw["latitude"].astype(float)
        longitude = raw["longitude"].astype(float)
        frp = raw["frp"].astype(float)
        if "type" in raw.columns:
            kind = raw["type"].astype("Int64")
        else:
            kind = pd.Series(pd.NA, index=raw.index, dtype="Int64")
    except (ValueError, TypeError) as exc:
        raise SchemaError(f"{path.name}: bad value ({exc})") from exc
    if acq_utc.isna().any():
        raise SchemaError(f"{path.name}: rows without acquisition date or time")

    confidence = raw["confidence"].astype(str).str.strip().str.lower().map(_CONFIDENCE)
    if confidence.isna().any():
        bad = sorted(set(raw.loc[confidence.isna(), "confidence"].astype(str)))
        raise SchemaError(f"{path.name}: unexpected confidence values {bad}")

    out = pd.DataFrame({
        "sensor": pd.Series(sensor, index=raw.index, dtype=object),
        "latitude": latitude,
        "longitude": longitude,
        "acq_date": acq_utc.dt.strftime("%Y-%m-%d"),
        "acq_time": hhmm,
        "acq_utc": acq_utc,
        "local_date": local_dates(acq_utc, offset),
        "confidence": confidence,
        "frp": frp,
        "daynight": raw["daynight"].astype(str),
        "type": kind,
    })
    return out[COLUMNS]
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_firms.py -q`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sulteng/firms.py tests/test_firms.py
git commit -m "Parse FIRMS archive and near-real-time CSVs into one schema"
```

---

### Task 4: Boundaries and assignment

**Files:**
- Create: `src/sulteng/boundaries.py`, `src/sulteng/assign.py`, `tests/test_boundaries.py`, `tests/test_assign.py`

**Interfaces:**
- Consumes: `Province` (Task 1); detection frames from Task 3.
- Produces: `boundaries.EQUAL_AREA_CRS = "EPSG:6933"`, `WGS84 = "EPSG:4326"`; `load_provinces(path, provinces) -> GeoDataFrame[name, island, area_km2, geometry]` in config order; `load_districts(path, provinces_gdf) -> GeoDataFrame[district, province, geometry]`; `simplified(gdf, tolerance, grid) -> GeoDataFrame`; `assign(detections, provinces, districts) -> DataFrame` (input columns + `province`, `district`; rows outside the provinces dropped).

- [ ] **Step 1: Write the failing tests**

`tests/test_boundaries.py`:

```python
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
```

`tests/test_assign.py`:

```python
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
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/test_boundaries.py tests/test_assign.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sulteng.boundaries'`

- [ ] **Step 3: Write `src/sulteng/boundaries.py`**

```python
"""Province and district polygons for the 11 study provinces."""

from __future__ import annotations

import geopandas as gpd
import shapely

from sulteng.config import Province

EQUAL_AREA_CRS = "EPSG:6933"
WGS84 = "EPSG:4326"


def load_provinces(path, provinces: tuple[Province, ...]) -> gpd.GeoDataFrame:
    """The study provinces with Indonesian names, island and land area (km²), in config order."""
    gdf = gpd.read_file(path)
    if "shapeName" not in gdf.columns:
        raise ValueError(f"{path}: no shapeName column")
    by_source = {p.source_name: p for p in provinces}
    missing = sorted(set(by_source) - set(gdf["shapeName"]))
    if missing:
        raise ValueError(f"{path}: provinces not found: {', '.join(missing)}")
    gdf = gdf[gdf["shapeName"].isin(by_source)].to_crs(WGS84)
    gdf = gdf.dissolve(by="shapeName", as_index=False)
    out = gpd.GeoDataFrame(
        {
            "name": [by_source[s].name for s in gdf["shapeName"]],
            "island": [by_source[s].island for s in gdf["shapeName"]],
        },
        geometry=gdf.geometry.to_numpy(),
        crs=WGS84,
    )
    out["area_km2"] = out.to_crs(EQUAL_AREA_CRS).area / 1e6
    order = {p.name: i for i, p in enumerate(provinces)}
    return out.sort_values("name", key=lambda s: s.map(order)).reset_index(drop=True)


def load_districts(path, provinces: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Districts whose representative point lies in a study province, tagged with that province."""
    gdf = gpd.read_file(path)
    if "shapeName" not in gdf.columns:
        raise ValueError(f"{path}: no shapeName column")
    gdf = gdf[["shapeName", "geometry"]].rename(columns={"shapeName": "district"}).to_crs(WGS84)
    gdf = gdf.reset_index(drop=True)
    points = gpd.GeoDataFrame(geometry=gdf.representative_point(), crs=WGS84)
    hit = gpd.sjoin(points, provinces[["name", "geometry"]], predicate="within", how="inner")
    hit = hit[~hit.index.duplicated(keep="first")]
    out = gdf.loc[hit.index].assign(province=hit["name"].to_numpy())
    return out[["district", "province", "geometry"]].reset_index(drop=True)


def simplified(gdf: gpd.GeoDataFrame, tolerance: float, grid: float) -> gpd.GeoDataFrame:
    """Copy with simplified geometry snapped to a coordinate grid (keeps polygons valid)."""
    out = gdf.copy()
    geoms = out.geometry.simplify(tolerance, preserve_topology=True).to_numpy()
    out["geometry"] = shapely.set_precision(geoms, grid)
    return out
```

- [ ] **Step 4: Write `src/sulteng/assign.py`**

```python
"""Attach province and district to detections inside the study provinces."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from sulteng.boundaries import EQUAL_AREA_CRS, WGS84


def assign(detections: pd.DataFrame, provinces: gpd.GeoDataFrame, districts: gpd.GeoDataFrame) -> pd.DataFrame:
    """Rows inside a study province, with `province` and `district` added; all other rows are dropped.

    The district is the one containing the point, or the nearest district of the same province
    (coastal points can fall just outside simplified district polygons).
    """
    det = detections.reset_index(drop=True)
    empty = det.iloc[0:0].assign(province=pd.Series(dtype=object), district=pd.Series(dtype=object))
    if det.empty:
        return empty
    points = gpd.GeoDataFrame(det, geometry=gpd.points_from_xy(det["longitude"], det["latitude"]), crs=WGS84)
    inside = gpd.sjoin(points, provinces[["name", "geometry"]], predicate="within", how="inner")
    inside = inside[~inside.index.duplicated(keep="first")]
    if inside.empty:
        return empty
    inside = inside.drop(columns="index_right").rename(columns={"name": "province"})

    parts = []
    for province, group in inside.groupby("province", sort=False):
        candidates = districts.loc[districts["province"] == province, ["district", "geometry"]]
        if candidates.empty:
            parts.append(pd.DataFrame(group.drop(columns="geometry")).assign(district=None))
            continue
        nearest = gpd.sjoin_nearest(group.to_crs(EQUAL_AREA_CRS), candidates.to_crs(EQUAL_AREA_CRS), how="left")
        nearest = nearest[~nearest.index.duplicated(keep="first")]
        parts.append(pd.DataFrame(nearest.drop(columns=["geometry", "index_right"])))
    return pd.concat(parts).sort_index()
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_boundaries.py tests/test_assign.py -q`
Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add src/sulteng/boundaries.py src/sulteng/assign.py tests/test_boundaries.py tests/test_assign.py
git commit -m "Load study provinces and districts; assign detections to them"
```

---
### Task 5: Static-source and volcano masks

**Files:**
- Create: `src/sulteng/grouping.py`, `src/sulteng/masks.py`, `tests/test_masks.py`

**Interfaces:**
- Consumes: `MaskParams` (Task 1); detection frames (Task 3); `province`, `district` columns (Task 4) for `static_sites`.
- Produces: `grouping.group_nearby(lat, lon, radius_deg) -> np.ndarray[int64]`; `masks.CATEGORIES = ("volcano", "static_suspect", "other")`; `Masks(cell_deg, static: MultiIndex, volcano: MultiIndex)`; `build_masks(archive, mask_params) -> Masks`; `categorize(df, masks) -> DataFrame` (adds `category`; works when `type` is absent); `static_sites(categorized, cell_deg) -> DataFrame[site_id, latitude, longitude, detections, first_date, last_date, calendar_months, years, type2_share, province, district]`; `masks_to_json(masks, provenance: dict) -> dict`; `masks_from_json(obj) -> Masks`.

- [ ] **Step 1: Write the failing tests `tests/test_masks.py`**

```python
import numpy as np
import pandas as pd

from conftest import make_detections
from sulteng.config import MaskParams
from sulteng.masks import Masks, build_masks, categorize, masks_from_json, masks_to_json, static_sites

MP = MaskParams(archive_years=(2023, 2024, 2025), cell_deg=0.005, min_calendar_months=7, min_years=2)
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
    sites = static_sites(categorize(det, Masks(0.005, NO_CELLS, NO_CELLS)), 0.005)
    assert list(sites["detections"]) == [3, 1]
    assert list(sites["site_id"]) == ["S001", "S002"]
    assert list(sites["district"]) == ["A1", "A2"]
    assert sites.loc[0, "calendar_months"] == 3 and sites.loc[0, "years"] == 2
    assert sites.loc[0, "type2_share"] == 1.0
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/test_masks.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sulteng.masks'`

- [ ] **Step 3: Write `src/sulteng/grouping.py`**

```python
"""Group points that lie close together."""

from __future__ import annotations

import geopandas as gpd
import numpy as np


def group_nearby(lat, lon, radius_deg: float) -> np.ndarray:
    """One integer label per point. Points within about 2 × radius_deg of each other, chained, share a label."""
    points = gpd.GeoSeries(gpd.points_from_xy(np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)))
    if points.empty:
        return np.array([], dtype=np.int64)
    blobs = gpd.GeoSeries([points.buffer(radius_deg, resolution=4).union_all()])
    blobs = blobs.explode(index_parts=False).reset_index(drop=True)
    joined = gpd.sjoin(
        gpd.GeoDataFrame(geometry=points), gpd.GeoDataFrame(geometry=blobs), predicate="intersects", how="left"
    )
    joined = joined[~joined.index.duplicated(keep="first")]
    return joined["index_right"].to_numpy(dtype=np.int64)
```

- [ ] **Step 4: Write `src/sulteng/masks.py`**

```python
"""Static-source and volcano masks from the archive, and the category of each detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from sulteng.config import MaskParams
from sulteng.grouping import group_nearby

CATEGORIES = ("volcano", "static_suspect", "other")
_NAMES = ["iy", "ix"]


@dataclass(frozen=True)
class Masks:
    cell_deg: float
    static: pd.MultiIndex
    volcano: pd.MultiIndex


def cell_index(df: pd.DataFrame, cell_deg: float) -> pd.MultiIndex:
    iy = np.floor(df["latitude"].to_numpy(dtype=float) / cell_deg).astype(np.int64)
    ix = np.floor(df["longitude"].to_numpy(dtype=float) / cell_deg).astype(np.int64)
    return pd.MultiIndex.from_arrays([iy, ix], names=_NAMES)


def _cells(pairs_iy, pairs_ix) -> pd.MultiIndex:
    return pd.MultiIndex.from_arrays(
        [np.asarray(pairs_iy, dtype=np.int64), np.asarray(pairs_ix, dtype=np.int64)], names=_NAMES
    )


def _spread(cells: pd.DataFrame) -> pd.DataFrame:
    """Rows repeated for their own cell and the 8 neighbouring cells."""
    shifted = [cells.assign(iy=cells["iy"] + dy, ix=cells["ix"] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    return pd.concat(shifted, ignore_index=True).drop_duplicates()


def pooled_cell_stats(df: pd.DataFrame, cell_deg: float) -> pd.DataFrame:
    """For each cell: distinct calendar months and years with detections in its 3×3 neighbourhood."""
    idx = cell_index(df, cell_deg)
    base = pd.DataFrame({
        "iy": idx.get_level_values("iy"),
        "ix": idx.get_level_values("ix"),
        "month": df["acq_utc"].dt.month.to_numpy(),
        "year": df["acq_utc"].dt.year.to_numpy(),
    }).drop_duplicates()
    return _spread(base).groupby(_NAMES).agg(n_months=("month", "nunique"), n_years=("year", "nunique"))


def recurrent_cells(stats: pd.DataFrame, min_calendar_months: int, min_years: int) -> pd.MultiIndex:
    keep = (stats["n_months"] >= min_calendar_months) & (stats["n_years"] >= min_years)
    return stats.index[keep]


def type_cells(df: pd.DataFrame, fire_type: int, cell_deg: float) -> pd.MultiIndex:
    """Cells holding, or next to, an archive detection of the given FIRMS type."""
    hits = df.loc[_type_is(df, fire_type)]
    idx = cell_index(hits, cell_deg)
    spread = _spread(pd.DataFrame({"iy": idx.get_level_values("iy"), "ix": idx.get_level_values("ix")}))
    return _cells(spread["iy"], spread["ix"])


def build_masks(archive: pd.DataFrame, mask_params: MaskParams) -> Masks:
    cell = mask_params.cell_deg
    stats = pooled_cell_stats(archive, cell)
    recurrent = recurrent_cells(stats, mask_params.min_calendar_months, mask_params.min_years)
    static = recurrent.union(type_cells(archive, 2, cell))
    return Masks(cell_deg=cell, static=static, volcano=type_cells(archive, 1, cell))


def categorize(df: pd.DataFrame, masks: Masks) -> pd.DataFrame:
    """Copy of df with `category`: volcano, then static_suspect, then other."""
    cells = cell_index(df, masks.cell_deg)
    volcano = _type_is(df, 1) | cells.isin(masks.volcano)
    static = _type_is(df, 2) | cells.isin(masks.static)
    return df.assign(category=np.select([volcano, static], ["volcano", "static_suspect"], default="other"))


def _type_is(df: pd.DataFrame, value: int) -> np.ndarray:
    if "type" not in df.columns:
        return np.zeros(len(df), dtype=bool)
    return df["type"].astype("Int64").eq(value).to_numpy(dtype=bool, na_value=False)


SITE_COLUMNS = [
    "site_id", "latitude", "longitude", "detections", "first_date", "last_date",
    "calendar_months", "years", "type2_share", "province", "district",
]


def static_sites(categorized: pd.DataFrame, cell_deg: float) -> pd.DataFrame:
    """Static-suspect detections grouped into sites, largest first."""
    flagged = categorized[categorized["category"] == "static_suspect"].reset_index(drop=True)
    if flagged.empty:
        return pd.DataFrame(columns=SITE_COLUMNS)
    flagged = flagged.assign(
        site=group_nearby(flagged["latitude"], flagged["longitude"], cell_deg),
        month=flagged["acq_utc"].dt.month,
        year=flagged["acq_utc"].dt.year,
        is_type2=_type_is(flagged, 2),
    )
    g = flagged.groupby("site")
    sites = pd.DataFrame({
        "latitude": g["latitude"].mean(),
        "longitude": g["longitude"].mean(),
        "detections": g.size(),
        "first_date": g["local_date"].min(),
        "last_date": g["local_date"].max(),
        "calendar_months": g["month"].nunique(),
        "years": g["year"].nunique(),
        "type2_share": g["is_type2"].mean(),
        "province": g["province"].agg(_mode),
        "district": g["district"].agg(_mode),
    })
    sites = sites.sort_values(["detections", "latitude"], ascending=[False, True]).reset_index(drop=True)
    sites.insert(0, "site_id", [f"S{i + 1:03d}" for i in range(len(sites))])
    return sites[SITE_COLUMNS]


def _mode(values: pd.Series):
    values = values.dropna()
    return values.mode().iat[0] if len(values) else None


def masks_to_json(masks: Masks, provenance: dict) -> dict:
    return {
        **provenance,
        "cell_deg": masks.cell_deg,
        "static": [[int(a), int(b)] for a, b in masks.static],
        "volcano": [[int(a), int(b)] for a, b in masks.volcano],
    }


def masks_from_json(obj: dict) -> Masks:
    def cells(pairs):
        return _cells([p[0] for p in pairs], [p[1] for p in pairs])

    return Masks(cell_deg=float(obj["cell_deg"]), static=cells(obj["static"]), volcano=cells(obj["volcano"]))
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_masks.py -q`
Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add src/sulteng/grouping.py src/sulteng/masks.py tests/test_masks.py
git commit -m "Build static-source and volcano masks; categorize detections"
```

---

### Task 6: Coverage

**Files:**
- Create: `src/sulteng/coverage.py`, `tests/test_coverage.py`

**Interfaces:**
- Produces: coverage is a JSON-ready `dict[sensor_code, list[[iso_start, iso_end]]]`. Functions: `merge(intervals)`, `add(coverage, sensor, start, end) -> dict`, `intervals(coverage, sensor) -> list[tuple[datetime, datetime]]`, `prune(coverage, before) -> dict`, `day_bounds(day, utc_offset_hours) -> (start_utc, end_utc)`, `day_status(coverage, sensors, day, utc_offset_hours) -> "complete"|"partial"|"missing"`, `feed_interval(last_modified, span_hours, latency_hours) -> (start, end)`, `backfill_requests(coverage, sensor, first_day, last_day, utc_offset_hours, max_days) -> list[tuple[date, int]]`.

- [ ] **Step 1: Write the failing tests `tests/test_coverage.py`**

```python
from datetime import date, datetime, timezone

from sulteng import coverage as cov


def t(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def test_add_merges_overlaps():
    c = cov.add({}, "N", t("2026-10-01T00:00"), t("2026-10-02T00:00"))
    c = cov.add(c, "N", t("2026-10-01T12:00"), t("2026-10-03T00:00"))
    c = cov.add(c, "N", t("2026-10-05T00:00"), t("2026-10-06T00:00"))
    assert cov.intervals(c, "N") == [
        (t("2026-10-01T00:00"), t("2026-10-03T00:00")),
        (t("2026-10-05T00:00"), t("2026-10-06T00:00")),
    ]


def test_day_status_uses_wita_days():
    # WITA 2 Oct runs from 1 Oct 16:00 UTC to 2 Oct 16:00 UTC
    c = cov.add({}, "N", t("2026-10-01T16:00"), t("2026-10-02T16:00"))
    assert cov.day_status(c, ["N"], date(2026, 10, 2), 8) == "complete"
    assert cov.day_status(c, ["N"], date(2026, 10, 3), 8) == "missing"
    c = cov.add(c, "N", t("2026-10-02T16:00"), t("2026-10-03T00:00"))
    assert cov.day_status(c, ["N"], date(2026, 10, 3), 8) == "partial"


def test_day_is_partial_when_one_sensor_is_missing():
    c = cov.add({}, "N", t("2026-10-01T00:00"), t("2026-10-05T00:00"))
    assert cov.day_status(c, ["N", "N20"], date(2026, 10, 2), 8) == "partial"
    c = cov.add(c, "N20", t("2026-10-01T00:00"), t("2026-10-05T00:00"))
    assert cov.day_status(c, ["N", "N20"], date(2026, 10, 2), 8) == "complete"


def test_feed_interval():
    start, end = cov.feed_interval(t("2026-10-18T12:00"), span_hours=156, latency_hours=3)
    assert (start, end) == (t("2026-10-12T00:00"), t("2026-10-18T09:00"))


def test_prune_cuts_old_parts():
    c = cov.add({}, "N", t("2026-08-20T00:00"), t("2026-09-10T00:00"))
    c = cov.add(c, "N20", t("2026-08-01T00:00"), t("2026-08-10T00:00"))
    c = cov.prune(c, t("2026-08-31T16:00"))
    assert cov.intervals(c, "N") == [(t("2026-08-31T16:00"), t("2026-09-10T00:00"))]
    assert cov.intervals(c, "N20") == []


def test_backfill_requests_cover_incomplete_wita_days_in_chunks():
    # complete for WITA 1-3 Oct; WITA 4-10 Oct need data, i.e. UTC dates 3-10 Oct
    c = cov.add({}, "N", t("2026-09-30T16:00"), t("2026-10-03T16:00"))
    requests = cov.backfill_requests(c, "N", date(2026, 10, 1), date(2026, 10, 10), 8, max_days=5)
    assert requests == [(date(2026, 10, 3), 5), (date(2026, 10, 8), 3)]


def test_backfill_requests_empty_when_complete():
    c = cov.add({}, "N", t("2026-09-30T16:00"), t("2026-10-03T16:00"))
    assert cov.backfill_requests(c, "N", date(2026, 10, 1), date(2026, 10, 3), 8, max_days=5) == []
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/test_coverage.py -q`
Expected: FAIL with `ImportError: cannot import name 'coverage' from 'sulteng'`

- [ ] **Step 3: Write `src/sulteng/coverage.py`**

```python
"""Which hours each sensor's downloads covered, and what that means for each WITA day."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

Interval = tuple[datetime, datetime]


def merge(spans: list[Interval]) -> list[Interval]:
    merged: list[Interval] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def intervals(coverage: dict, sensor: str) -> list[Interval]:
    return [(datetime.fromisoformat(a), datetime.fromisoformat(b)) for a, b in coverage.get(sensor, [])]


def _encode(spans: list[Interval]) -> list[list[str]]:
    return [[a.isoformat(), b.isoformat()] for a, b in spans]


def add(coverage: dict, sensor: str, start: datetime, end: datetime) -> dict:
    """Copy of coverage with [start, end) added for sensor."""
    out = dict(coverage)
    out[sensor] = _encode(merge(intervals(coverage, sensor) + [(start, end)]))
    return out


def prune(coverage: dict, before: datetime) -> dict:
    """Copy of coverage without anything earlier than `before`."""
    return {
        sensor: _encode([(max(a, before), b) for a, b in intervals(coverage, sensor) if b > before])
        for sensor in coverage
    }


def feed_interval(last_modified: datetime, span_hours: int, latency_hours: int) -> Interval:
    return last_modified - timedelta(hours=span_hours), last_modified - timedelta(hours=latency_hours)


def day_bounds(day: date, utc_offset_hours: int) -> Interval:
    local = timezone(timedelta(hours=utc_offset_hours))
    start = datetime(day.year, day.month, day.day, tzinfo=local).astimezone(timezone.utc)
    return start, start + timedelta(days=1)


def _status(spans: list[Interval], start: datetime, end: datetime) -> str:
    if any(a <= start and b >= end for a, b in spans):
        return "complete"
    if any(a < end and b > start for a, b in spans):
        return "partial"
    return "missing"


def day_status(coverage: dict, sensors, day: date, utc_offset_hours: int) -> str:
    start, end = day_bounds(day, utc_offset_hours)
    states = {_status(intervals(coverage, s), start, end) for s in sensors}
    if states == {"complete"}:
        return "complete"
    if states == {"missing"}:
        return "missing"
    return "partial"


def backfill_requests(
    coverage: dict, sensor: str, first_day: date, last_day: date, utc_offset_hours: int, max_days: int
) -> list[tuple[date, int]]:
    """(UTC start date, number of days) requests covering every WITA day in range that is not complete."""
    spans = intervals(coverage, sensor)
    needed: set[date] = set()
    day = first_day
    while day <= last_day:
        start, end = day_bounds(day, utc_offset_hours)
        if _status(spans, start, end) != "complete":
            utc_day = start.date()
            while datetime(utc_day.year, utc_day.month, utc_day.day, tzinfo=timezone.utc) < end:
                needed.add(utc_day)
                utc_day += timedelta(days=1)
        day += timedelta(days=1)
    requests: list[tuple[date, int]] = []
    for utc_day in sorted(needed):
        if requests:
            first, count = requests[-1]
            if first + timedelta(days=count) == utc_day and count < max_days:
                requests[-1] = (first, count + 1)
                continue
        requests.append((utc_day, 1))
    return requests
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_coverage.py -q`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sulteng/coverage.py tests/test_coverage.py
git commit -m "Track per-sensor download coverage and WITA day status"
```

---

### Task 7: Rolling store and JSON output

**Files:**
- Create: `src/sulteng/store.py`, `src/sulteng/publish.py`, `tests/test_store.py`, `tests/test_publish.py`

**Interfaces:**
- Produces: `store.STORE_COLUMNS` = `["sensor","latitude","longitude","acq_date","acq_time","acq_utc","local_date","confidence","frp","daynight","province","district","category"]`; `store.KEY` = `["sensor","latitude","longitude","acq_date","acq_time"]`; `store.empty()`, `store.load(store_dir, months) -> DataFrame`, `store.combine(existing, new) -> DataFrame` (newer wins), `store.save(store_dir, df, months) -> None` (one CSV per month, deletes others).
- Produces: `publish.to_public(obj)`, `publish.write_json(obj, path)` (atomic, compact, raises `ValueError` on NaN/inf), `publish.point_feature(lon, lat, props)`, `publish.feature_collection(features)`.

- [ ] **Step 1: Write the failing tests**

`tests/test_store.py`:

```python
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
```

`tests/test_publish.py`:

```python
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from sulteng.publish import feature_collection, point_feature, write_json


def test_write_json_converts_numpy_dates_and_missing(tmp_path):
    path = tmp_path / "x.json"
    write_json({
        "a": np.int64(3),
        "b": np.float64(1.234567),
        "c": [pd.NA, None, np.bool_(True)],
        "d": pd.Timestamp("2026-10-01T05:30:00Z"),
        "e": date(2026, 10, 1),
    }, path)
    assert json.loads(path.read_text()) == {
        "a": 3, "b": 1.2346, "c": [None, None, True], "d": "2026-10-01T05:30:00+00:00", "e": "2026-10-01",
    }


def test_write_json_rejects_nan_and_writes_nothing(tmp_path):
    with pytest.raises(ValueError, match="NaN"):
        write_json({"x": float("nan")}, tmp_path / "x.json")
    assert not (tmp_path / "x.json").exists()


def test_geojson_helpers():
    fc = feature_collection([point_feature(120.1, -1.2, {"k": 1})])
    assert fc["type"] == "FeatureCollection"
    assert fc["features"][0]["geometry"] == {"type": "Point", "coordinates": [120.1, -1.2]}
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/test_store.py tests/test_publish.py -q`
Expected: FAIL with `ImportError: cannot import name 'store' from 'sulteng'`

- [ ] **Step 3: Write `src/sulteng/store.py`**

```python
"""Rolling store of detections: one CSV per WITA month."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

STORE_COLUMNS = [
    "sensor", "latitude", "longitude", "acq_date", "acq_time", "acq_utc", "local_date",
    "confidence", "frp", "daynight", "province", "district", "category",
]
KEY = ["sensor", "latitude", "longitude", "acq_date", "acq_time"]
_TEXT = ["sensor", "acq_date", "acq_time", "local_date", "confidence", "daynight", "province", "district", "category"]


def empty() -> pd.DataFrame:
    df = pd.DataFrame({c: pd.Series(dtype=object) for c in STORE_COLUMNS})
    df["acq_utc"] = pd.to_datetime(df["acq_utc"], utc=True)
    return df


def load(store_dir: Path | str, months) -> pd.DataFrame:
    frames = []
    for month in months:
        path = Path(store_dir) / f"{month}.csv"
        if path.exists():
            frames.append(pd.read_csv(path, dtype={c: str for c in _TEXT}))
    if not frames:
        return empty()
    df = pd.concat(frames, ignore_index=True)
    df["acq_utc"] = pd.to_datetime(df["acq_utc"], utc=True)
    return df[STORE_COLUMNS]


def combine(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Union of both frames. When a detection is in both, the row from `new` wins."""
    frames = [f[STORE_COLUMNS] for f in (existing, new) if not f.empty]
    if not frames:
        return empty()
    both = pd.concat(frames, ignore_index=True)
    return both.drop_duplicates(subset=KEY, keep="last").reset_index(drop=True)


def save(store_dir: Path | str, df: pd.DataFrame, months) -> None:
    """Write one CSV per month in `months`; delete CSVs of any other month."""
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    month_of = df["local_date"].str[:7]
    for month in months:
        part = df[month_of == month].sort_values(["acq_utc", "sensor", "latitude", "longitude"])
        path = store_dir / f"{month}.csv"
        tmp = path.with_name(path.name + ".part")
        part[STORE_COLUMNS].to_csv(tmp, index=False)
        os.replace(tmp, path)
    keep = set(months)
    for path in store_dir.glob("*.csv"):
        if path.stem not in keep:
            path.unlink()
```

- [ ] **Step 4: Write `src/sulteng/publish.py`**

```python
"""Write JSON and GeoJSON outputs safely."""

from __future__ import annotations

import datetime as dt
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd


def to_public(obj):
    """Plain JSON types; floats rounded to 4 places; NaN and infinity are errors."""
    if isinstance(obj, dict):
        return {str(k): to_public(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_public(v) for v in obj]
    if obj is None or obj is pd.NA or obj is pd.NaT:
        return None
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        value = float(obj)
        if not math.isfinite(value):
            raise ValueError("NaN or infinity in public output")
        return round(value, 4)
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    return obj


def write_json(obj, path: Path | str) -> None:
    path = Path(path)
    text = json.dumps(to_public(obj), ensure_ascii=False, separators=(",", ":"))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def point_feature(lon: float, lat: float, properties: dict) -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": properties}


def feature_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_store.py tests/test_publish.py -q`
Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add src/sulteng/store.py src/sulteng/publish.py tests/test_store.py tests/test_publish.py
git commit -m "Add two-month detection store and safe JSON output"
```

---

### Task 8: Window summaries

**Files:**
- Create: `src/sulteng/summary.py`, `tests/test_summary.py`

**Interfaces:**
- Consumes: `Params` (Task 1), `coverage.day_status` (Task 6), `masks.CATEGORIES` (Task 5); store-shaped frames (Task 7).
- Produces: `MONTHS_ID`; `local_today(now_utc, offset) -> date`; `previous_month(day) -> (first, last)`; `kept_months(now_utc, offset) -> [prev "YYYY-MM", current "YYYY-MM"]`; `windows(now_utc, offset) -> dict[key, dict(label, kind, start, end, first_day, last_day)]` with keys `24h`, `7d`, `this_month`, `last_month`; `counts(frame) -> dict`; `summarize(df, coverage, params, areas, now_utc) -> dict` (shape below); `daily_series(df, coverage, params, now_utc) -> list[dict(date, coverage, counts|None)]`.
- `now.json` shape: `{generated_at, utc_offset_hours, focus, sensors:[{code,name}], windows:{key:{label,start,end,coverage:{days,complete,partial,missing},provinces:[{name,island,area_km2,counts,per_1000_km2:{all,other}}],focus_districts:[{district,counts}]}}, daily:[...]}`; `counts` = `{all, volcano, static_suspect, other, confidence:{l,n,h}, sensors:{code:n}}`.

- [ ] **Step 1: Write the failing tests `tests/test_summary.py`**

```python
from datetime import date, datetime, timezone

from conftest import make_detections
from sulteng import coverage as cov
from sulteng.config import load_params
from sulteng.summary import daily_series, kept_months, summarize, windows

PARAMS = load_params()
AREAS = {p.name: 1000.0 for p in PARAMS.provinces}
NOW = datetime(2026, 10, 18, 4, 0, tzinfo=timezone.utc)  # 12:00 WITA


def full_coverage(start, end):
    c = {}
    for sensor in PARAMS.sensors:
        c = cov.add(c, sensor.code, start, end)
    return c


def frame(specs):
    """specs: (province, district, 'YYYY-MM-DD HH:MM' UTC, category)."""
    det = make_detections([(-1.0, 120.0, utc, None) for _, _, utc, _ in specs]).drop(columns="type")
    return det.assign(
        province=[p for p, *_ in specs], district=[d for _, d, *_ in specs], category=[c for *_, c in specs]
    )


def test_kept_months_rollover_and_january():
    assert kept_months(NOW, 8) == ["2026-09", "2026-10"]
    assert kept_months(datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc), 8) == ["2026-10", "2026-11"]
    assert kept_months(datetime(2027, 1, 3, tzinfo=timezone.utc), 8) == ["2026-12", "2027-01"]
    # 17:00 UTC on 31 Dec is already 1 Jan in WITA
    assert kept_months(datetime(2026, 12, 31, 17, 0, tzinfo=timezone.utc), 8) == ["2026-12", "2027-01"]


def test_window_bounds_and_labels():
    w = windows(NOW, 8)
    assert (w["this_month"]["start"], w["this_month"]["end"]) == (date(2026, 10, 1), date(2026, 10, 18))
    assert (w["last_month"]["start"], w["last_month"]["end"]) == (date(2026, 9, 1), date(2026, 9, 30))
    assert w["24h"]["start"] == datetime(2026, 10, 17, 4, 0, tzinfo=timezone.utc)
    assert w["last_month"]["label"] == "September 2026"


def test_counts_per_window_province_and_district():
    df = frame([
        ("Sulawesi Tengah", "Morowali", "2026-10-18 02:00", "static_suspect"),
        ("Sulawesi Tengah", "Poso", "2026-10-17 05:00", "other"),
        ("Sulawesi Tengah", "Poso", "2026-10-05 05:00", "other"),
        ("Sulawesi Tengah", "Banggai", "2026-09-10 05:00", "other"),
        ("Kalimantan Tengah", "Kotawaringin Timur", "2026-09-10 05:00", "other"),
    ])
    s = summarize(df, full_coverage(datetime(2026, 8, 31, tzinfo=timezone.utc), NOW), PARAMS, AREAS, NOW)

    def focus(key):
        return next(p for p in s["windows"][key]["provinces"] if p["name"] == "Sulawesi Tengah")

    assert focus("24h")["counts"]["all"] == 2
    assert focus("24h")["counts"]["static_suspect"] == 1
    assert focus("this_month")["counts"]["other"] == 2
    assert focus("this_month")["per_1000_km2"] == {"all": 3.0, "other": 2.0}
    assert focus("last_month")["counts"]["all"] == 1
    kalteng = next(p for p in s["windows"]["last_month"]["provinces"] if p["name"] == "Kalimantan Tengah")
    assert kalteng["counts"]["other"] == 1
    assert [d["district"] for d in s["windows"]["this_month"]["focus_districts"]] == ["Poso", "Morowali"]
    assert s["windows"]["last_month"]["coverage"] == {"days": 30, "complete": 30, "partial": 0, "missing": 0}
    assert s["windows"]["this_month"]["coverage"]["partial"] == 1  # today


def test_window_with_no_coverage_reports_missing_days():
    s = summarize(frame([]), {}, PARAMS, AREAS, NOW)
    assert s["windows"]["last_month"]["coverage"] == {"days": 30, "complete": 0, "partial": 0, "missing": 30}


def test_daily_series_null_for_missing_and_zero_for_complete():
    c = full_coverage(datetime(2026, 9, 30, 16, 0, tzinfo=timezone.utc), NOW)  # from WITA 1 Oct
    df = frame([("Sulawesi Tengah", "Poso", "2026-10-05 05:00", "other")])
    days = {d["date"]: d for d in daily_series(df, c, PARAMS, NOW)}
    assert len(days) == 30 + 18
    assert days["2026-09-15"] == {"date": "2026-09-15", "coverage": "missing", "counts": None}
    assert days["2026-10-04"]["counts"] == {"volcano": 0, "static_suspect": 0, "other": 0}
    assert days["2026-10-05"]["counts"]["other"] == 1
    assert days["2026-10-18"]["coverage"] == "partial"
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/test_summary.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sulteng.summary'`

- [ ] **Step 3: Write `src/sulteng/summary.py`**

```python
"""Counts per time window, province and district, ready for the site."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from sulteng.config import Params
from sulteng.coverage import day_status
from sulteng.masks import CATEGORIES

MONTHS_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def local_today(now_utc: datetime, utc_offset_hours: int) -> date:
    return (now_utc + timedelta(hours=utc_offset_hours)).date()


def previous_month(day: date) -> tuple[date, date]:
    last = day.replace(day=1) - timedelta(days=1)
    return last.replace(day=1), last


def kept_months(now_utc: datetime, utc_offset_hours: int) -> list[str]:
    today = local_today(now_utc, utc_offset_hours)
    first, _ = previous_month(today)
    return [first.strftime("%Y-%m"), today.strftime("%Y-%m")]


def windows(now_utc: datetime, utc_offset_hours: int) -> dict[str, dict]:
    today = local_today(now_utc, utc_offset_hours)
    prev_first, prev_last = previous_month(today)
    offset = timedelta(hours=utc_offset_hours)

    def by_time(label, hours):
        start = now_utc - timedelta(hours=hours)
        return {"label": label, "kind": "utc", "start": start, "end": now_utc,
                "first_day": (start + offset).date(), "last_day": today}

    def by_day(label, first, last):
        return {"label": label, "kind": "local", "start": first, "end": last, "first_day": first, "last_day": last}

    return {
        "24h": by_time("24 jam terakhir", 24),
        "7d": by_time("7 hari terakhir", 24 * 7),
        "this_month": by_day(f"{MONTHS_ID[today.month - 1]} {today.year} (sampai hari ini)", today.replace(day=1), today),
        "last_month": by_day(f"{MONTHS_ID[prev_first.month - 1]} {prev_first.year}", prev_first, prev_last),
    }


def select(df: pd.DataFrame, window: dict) -> pd.DataFrame:
    if window["kind"] == "utc":
        return df[(df["acq_utc"] > window["start"]) & (df["acq_utc"] <= window["end"])]
    local = df["local_date"]
    return df[(local >= window["start"].isoformat()) & (local <= window["end"].isoformat())]


def counts(frame: pd.DataFrame) -> dict:
    cats = frame["category"].value_counts()
    conf = frame["confidence"].value_counts()
    return {
        "all": int(len(frame)),
        **{c: int(cats.get(c, 0)) for c in CATEGORIES},
        "confidence": {k: int(conf.get(k, 0)) for k in ("l", "n", "h")},
        "sensors": {str(k): int(v) for k, v in frame["sensor"].value_counts().items()},
    }


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def summarize(df: pd.DataFrame, coverage: dict, params: Params, areas: dict[str, float], now_utc: datetime) -> dict:
    offset = params.utc_offset_hours
    sensors = [s.code for s in params.sensors]
    focus = params.focus_province
    out = {}
    for key, w in windows(now_utc, offset).items():
        chosen = select(df, w)
        status = [day_status(coverage, sensors, d, offset) for d in _days(w["first_day"], w["last_day"])]
        provinces = []
        for p in params.provinces:
            c = counts(chosen[chosen["province"] == p.name])
            area = float(areas[p.name])
            provinces.append({
                "name": p.name,
                "island": p.island,
                "area_km2": area,
                "counts": c,
                "per_1000_km2": {"all": c["all"] / area * 1000, "other": c["other"] / area * 1000},
            })
        in_focus = chosen[chosen["province"] == focus]
        districts = [{"district": d, "counts": counts(g)} for d, g in in_focus.groupby("district")]
        districts.sort(key=lambda r: (-r["counts"]["other"], -r["counts"]["all"], r["district"]))
        out[key] = {
            "label": w["label"],
            "start": w["start"],
            "end": w["end"],
            "coverage": {"days": len(status), **{s: status.count(s) for s in ("complete", "partial", "missing")}},
            "provinces": provinces,
            "focus_districts": districts,
        }
    return {
        "generated_at": now_utc.isoformat(timespec="seconds"),
        "utc_offset_hours": offset,
        "focus": focus,
        "sensors": [{"code": s.code, "name": s.name} for s in params.sensors],
        "windows": out,
        "daily": daily_series(df, coverage, params, now_utc),
    }


def daily_series(df: pd.DataFrame, coverage: dict, params: Params, now_utc: datetime) -> list[dict]:
    """Focus-province counts per WITA day for last month and this month; None where no data exists."""
    offset = params.utc_offset_hours
    sensors = [s.code for s in params.sensors]
    today = local_today(now_utc, offset)
    first, _ = previous_month(today)
    focus = df[df["province"] == params.focus_province]
    per_day = focus.groupby(["local_date", "category"]).size()
    rows = []
    for d in _days(first, today):
        state = day_status(coverage, sensors, d, offset)
        key = d.isoformat()
        values = None if state == "missing" else {c: int(per_day.get((key, c), 0)) for c in CATEGORIES}
        rows.append({"date": key, "coverage": state, "counts": values})
    return rows
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_summary.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sulteng/summary.py tests/test_summary.py
git commit -m "Summarize detections per window, province, district and day"
```

---

### Task 9: Refresh run

**Files:**
- Create: `src/sulteng/refresh.py`, `tests/test_refresh.py`

**Interfaces:**
- Consumes: everything from Tasks 2–8.
- Produces: `Paths(live: Path, raw: Path)` with `.store`; `run_refresh(params, provinces, districts, masks, paths, now_utc, *, map_key=None, fetch=download) -> dict` (the status). Writes into `paths.live`: `detections/YYYY-MM.csv`, `coverage.json`, `now.json`, `focus_detections.geojson`, `status.json`. `fetch` is called as `fetch(url, dest)` for feeds and `fetch(url, dest, label=...)` for the API, and must return a `ManifestEntry`.
- `status.json` shape: `{status: ok|partial|update_failed, last_attempt, last_success, sensors:{code:{name,status: ok|partial|failed, rows, errors:[...], last_success}}, backfill:{enabled, note}}`.

- [ ] **Step 1: Write the failing tests `tests/test_refresh.py`**

```python
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import PROVINCES
from sulteng.boundaries import load_districts, load_provinces
from sulteng.config import load_params
from sulteng.fetch import FetchError, ManifestEntry
from sulteng.masks import Masks
from sulteng.refresh import Paths, run_refresh

NOW = datetime(2026, 10, 18, 4, 0, tzinfo=timezone.utc)
HEADER = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight\n"
ROW_ALFA = "-1.5,120.25,340,0.4,0.4,2026-10-17,0530,N,nominal,2.0NRT,290,5.0,D\n"
ROW_SEA = "-1.5,117.0,340,0.4,0.4,2026-10-17,0530,N,nominal,2.0NRT,290,5.0,D\n"
NO_CELLS = pd.MultiIndex.from_arrays([np.array([], dtype=np.int64)] * 2, names=["iy", "ix"])
PARAMS = replace(load_params(), provinces=PROVINCES, focus_province="Alfa")


class FakeFetch:
    def __init__(self, body_for, last_modified="2026-10-18T03:00:00+00:00"):
        self.body_for, self.last_modified, self.calls = body_for, last_modified, []

    def __call__(self, url, dest, label=None):
        self.calls.append((url, label))
        body = self.body_for(url)
        if isinstance(body, Exception):
            raise body
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_text(body)
        return ManifestEntry(url=label or url, file=Path(dest).name, bytes=len(body), sha256="x",
                             retrieved_at=NOW.isoformat(), last_modified=self.last_modified)


@pytest.fixture
def run(tmp_path, boundary_files):
    adm1, adm2 = boundary_files
    provinces = load_provinces(adm1, PROVINCES)
    districts = load_districts(adm2, provinces)
    paths = Paths(live=tmp_path / "live", raw=tmp_path / "raw")

    def go(fetch, now=NOW, map_key=None):
        return run_refresh(PARAMS, provinces, districts, Masks(0.005, NO_CELLS, NO_CELLS), paths, now,
                           map_key=map_key, fetch=fetch)

    go.paths = paths
    return go


def read(run, name):
    return json.loads((run.paths.live / name).read_text())


def test_all_feeds_ok(run):
    status = run(FakeFetch(lambda url: HEADER + ROW_ALFA + ROW_SEA))
    assert status["status"] == "ok"
    assert set(status["sensors"]) == {"N", "N20", "N21"}
    alfa = read(run, "now.json")["windows"]["24h"]["provinces"][0]
    assert alfa["name"] == "Alfa" and alfa["counts"]["all"] == 3  # one detection per sensor
    assert len(read(run, "focus_detections.geojson")["features"]) == 3
    assert (run.paths.live / "detections" / "2026-10.csv").exists()
    assert (run.paths.live / "detections" / "2026-09.csv").exists()


def test_repeated_runs_do_not_duplicate(run):
    fetch = FakeFetch(lambda url: HEADER + ROW_ALFA)
    run(fetch)
    run(fetch)
    assert read(run, "now.json")["windows"]["24h"]["provinces"][0]["counts"]["all"] == 3


def test_one_sensor_failing_is_partial(run):
    failing = PARAMS.sensors[1].feed_url
    status = run(FakeFetch(lambda url: FetchError("down") if url == failing else HEADER + ROW_ALFA))
    assert status["status"] == "partial"
    assert status["sensors"]["N20"]["status"] == "failed"
    assert read(run, "coverage.json").get("N20", []) == []


def test_html_pages_everywhere_is_update_failed(run):
    run(FakeFetch(lambda url: HEADER + ROW_ALFA))
    before = (run.paths.live / "now.json").read_text()
    later = datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc)
    status = run(FakeFetch(lambda url: "<html><body>Maintenance</body></html>"), now=later)
    assert status["status"] == "update_failed"
    assert status["last_attempt"] == later.isoformat(timespec="seconds")
    assert status["last_success"] == NOW.isoformat(timespec="seconds")
    assert (run.paths.live / "now.json").read_text() == before
    assert read(run, "status.json")["status"] == "update_failed"


def test_empty_feeds_are_ok_with_zero(run):
    status = run(FakeFetch(lambda url: HEADER))
    assert status["status"] == "ok"
    assert read(run, "now.json")["windows"]["24h"]["provinces"][0]["counts"]["all"] == 0


def test_backfill_requests_and_key_redaction(run):
    def body(url):
        if "/api/" in url:
            return FetchError("HTTP 500") if "VIIRS_NOAA21_NRT" in url else HEADER
        return HEADER + ROW_ALFA

    fetch = FakeFetch(body)
    status = run(fetch, map_key="SECRET123")
    api_calls = [(url, label) for url, label in fetch.calls if "/api/" in url]
    assert api_calls
    assert all("SECRET123" in url and "SECRET123" not in label and "***" in label for url, label in api_calls)
    assert all(int(url.split("/")[-2]) <= PARAMS.api_days_per_request for url, _ in api_calls)
    assert "SECRET123" not in json.dumps(status)
    assert "SECRET123" not in (run.paths.live / "status.json").read_text()
    assert status["sensors"]["N21"]["status"] == "partial"
    assert status["sensors"]["N"]["status"] == "ok"


def test_no_key_means_no_api_calls(run):
    fetch = FakeFetch(lambda url: HEADER)
    status = run(fetch)
    assert not [url for url, _ in fetch.calls if "/api/" in url]
    assert status["backfill"]["enabled"] is False
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/test_refresh.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sulteng.refresh'`

- [ ] **Step 3: Write `src/sulteng/refresh.py`**

```python
"""One refresh run: download the feeds, update the store, write summaries and status."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd

from sulteng import coverage as cov
from sulteng import store
from sulteng.assign import assign
from sulteng.config import Params, Sensor
from sulteng.fetch import FetchError, download
from sulteng.firms import SchemaError, read_nrt
from sulteng.masks import Masks, categorize
from sulteng.publish import feature_collection, point_feature, write_json
from sulteng.summary import kept_months, local_today, previous_month, summarize


@dataclass(frozen=True)
class Paths:
    live: Path  # published live outputs and the rolling store
    raw: Path  # downloads; never published

    @property
    def store(self) -> Path:
        return self.live / "detections"


def run_refresh(
    params: Params,
    provinces: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    masks: Masks,
    paths: Paths,
    now_utc: datetime,
    *,
    map_key: str | None = None,
    fetch=download,
) -> dict:
    previous = _read_json(paths.live / "status.json")
    coverage = _read_json(paths.live / "coverage.json")
    attempt = now_utc.isoformat(timespec="seconds")

    frames: list[pd.DataFrame] = []
    sensors: dict[str, dict] = {}
    for sensor in params.sensors:
        got, errors, coverage = _collect(sensor, params, provinces, paths, now_utc, coverage, map_key, fetch)
        frames.extend(got)
        state = "ok" if got and not errors else ("partial" if got else "failed")
        last = attempt if got else previous.get("sensors", {}).get(sensor.code, {}).get("last_success")
        sensors[sensor.code] = {
            "name": sensor.name,
            "status": state,
            "rows": sum(len(f) for f in got),
            "errors": errors,
            "last_success": last,
        }
    backfill = {
        "enabled": bool(map_key),
        "note": None if map_key else "FIRMS_MAP_KEY not set: only the 7-day feeds were read",
    }

    if not frames:
        status = {"status": "update_failed", "last_attempt": attempt, "last_success": previous.get("last_success"),
                  "sensors": sensors, "backfill": backfill}
        write_json(status, paths.live / "status.json")
        return status

    offset = params.utc_offset_hours
    months = kept_months(now_utc, offset)
    new = categorize(assign(pd.concat(frames, ignore_index=True), provinces, districts), masks)
    combined = store.combine(store.load(paths.store, months), new)
    combined = combined[combined["local_date"].str[:7].isin(months)]
    combined = categorize(combined.drop(columns="category"), masks)[store.STORE_COLUMNS]
    store.save(paths.store, combined, months)

    first_kept = date.fromisoformat(f"{months[0]}-01")
    coverage = cov.prune(coverage, cov.day_bounds(first_kept, offset)[0])
    areas = dict(zip(provinces["name"], provinces["area_km2"].astype(float)))
    write_json(coverage, paths.live / "coverage.json")
    write_json(summarize(combined, coverage, params, areas, now_utc), paths.live / "now.json")
    write_json(focus_geojson(combined, params.focus_province), paths.live / "focus_detections.geojson")

    overall = "ok" if all(s["status"] == "ok" for s in sensors.values()) else "partial"
    status = {"status": overall, "last_attempt": attempt, "last_success": attempt,
              "sensors": sensors, "backfill": backfill}
    write_json(status, paths.live / "status.json")
    return status


def _collect(sensor: Sensor, params: Params, provinces, paths: Paths, now_utc: datetime, coverage: dict,
             map_key: str | None, fetch):
    """Frames for one sensor from its 7-day feed and, with a key, the API; plus errors and new coverage."""
    offset = params.utc_offset_hours
    got: list[pd.DataFrame] = []
    errors: list[str] = []
    dest = paths.raw / f"feed_{sensor.code}.csv"
    try:
        entry = fetch(sensor.feed_url, dest)
        got.append(read_nrt(dest, sensor=sensor.code, utc_offset_hours=offset))
    except (FetchError, SchemaError) as exc:
        errors.append(f"7-day feed: {exc}")
    else:
        stamp = datetime.fromisoformat(entry.last_modified) if entry.last_modified else now_utc
        start, end = cov.feed_interval(stamp, params.feed_span_hours, params.feed_latency_hours)
        coverage = cov.add(coverage, sensor.code, start, end)

    if not map_key:
        return got, errors, coverage
    today = local_today(now_utc, offset)
    first, _ = previous_month(today)
    bbox = _bbox(provinces)
    requests = cov.backfill_requests(coverage, sensor.code, first, today - timedelta(days=1), offset,
                                     params.api_days_per_request)
    for start_day, days in requests:
        fields = {"source": sensor.api_source, "bbox": bbox, "days": days, "date": start_day.isoformat()}
        dest = paths.raw / f"api_{sensor.code}_{start_day.isoformat()}_{days}.csv"
        try:
            fetch(params.api_url.format(key=map_key, **fields), dest, label=params.api_url.format(key="***", **fields))
            got.append(read_nrt(dest, sensor=sensor.code, utc_offset_hours=offset))
        except (FetchError, SchemaError) as exc:
            errors.append(f"API {start_day.isoformat()} +{days}d: {exc}")
            continue
        begin = datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc)
        coverage = cov.add(coverage, sensor.code, begin, begin + timedelta(days=days))
    return got, errors, coverage


def _bbox(provinces: gpd.GeoDataFrame) -> str:
    west, south, east, north = provinces.total_bounds
    rounded = (math.floor(west * 100), math.floor(south * 100), math.ceil(east * 100), math.ceil(north * 100))
    return ",".join(f"{v / 100:.2f}" for v in rounded)


def focus_geojson(df: pd.DataFrame, focus: str) -> dict:
    rows = df[df["province"] == focus].sort_values(["acq_utc", "sensor"])
    return feature_collection([
        point_feature(r.longitude, r.latitude, {
            "sensor": r.sensor,
            "utc": r.acq_utc,
            "local_date": r.local_date,
            "confidence": r.confidence,
            "frp": None if pd.isna(r.frp) else r.frp,
            "category": r.category,
            "district": r.district if isinstance(r.district, str) else None,
        })
        for r in rows.itertuples(index=False)
    ])


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
```

- [ ] **Step 4: Run the tests, then the whole suite**

Run: `uv run pytest tests/test_refresh.py -q && uv run pytest -q`
Expected: `7 passed`, then the full suite passes.

- [ ] **Step 5: Commit**

```bash
git add src/sulteng/refresh.py tests/test_refresh.py
git commit -m "Add refresh run with partial and failed outcomes and optional API backfill"
```

---
### Task 10: Build masks and boundary files from real data

**Files:**
- Create: `scripts/build_masks.py`
- Generated and committed: `data/boundaries/provinces.geojson`, `data/boundaries/districts.geojson`, `data/public/provinces.geojson`, `data/public/districts_focus.geojson`, `data/public/masks.json`, `data/public/static_sites.geojson`, `data/public/manifest.json`, `reports/static_review.md`

**Interfaces:**
- Consumes: `load_params`, `download`, `load_manifest`, `save_manifest`, `utc_now_iso`, `read_archive`, `load_provinces`, `load_districts`, `simplified`, `assign`, `build_masks`, `categorize`, `static_sites`, `masks_to_json`, `write_json`, `point_feature`, `feature_collection`.
- Produces: the files above. `data/boundaries/*.geojson` keep `name, island, area_km2` (provinces) and `district, province` (districts) as properties; Task 11 reads them with `geopandas.read_file`.

- [ ] **Step 1: Write `scripts/build_masks.py`**

```python
"""Build static-source and volcano masks and boundary files from the FIRMS archive.

Run when the archive years or the mask rule change. Outputs are committed.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import asdict

import pandas as pd

from sulteng.assign import assign
from sulteng.boundaries import load_districts, load_provinces, simplified
from sulteng.config import ROOT, load_params
from sulteng.fetch import download, load_manifest, save_manifest, utc_now_iso
from sulteng.firms import read_archive
from sulteng.masks import CATEGORIES, build_masks, categorize, masks_to_json, static_sites
from sulteng.publish import feature_collection, point_feature, write_json

RAW = ROOT / "data" / "raw"
BOUNDARIES = ROOT / "data" / "boundaries"
PUBLIC = ROOT / "data" / "public"
REVIEW_DISTRICTS = ("Morowali", "Banggai")
SITE_PROPS = ("site_id", "detections", "first_date", "last_date", "calendar_months", "years",
              "type2_share", "province", "district")


def fetch_inputs(params, force: bool) -> list[dict]:
    manifest = load_manifest(RAW / "manifest.json")
    wanted = [(params.adm1_url, "adm1.geojson"), (params.adm2_url, "adm2_simplified.geojson")]
    wanted += [(params.archive_url_for(y), f"viirs-snpp_{y}_Indonesia.csv") for y in params.masks.archive_years]
    used = []
    for url, name in wanted:
        if force or name not in manifest or not (RAW / name).exists():
            print(f"downloading {name}", flush=True)
            manifest[name] = asdict(download(url, RAW / name))
            save_manifest(RAW / "manifest.json", manifest)
        used.append(manifest[name])
    return used


def code_version() -> dict:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()

    return {"commit": git("rev-parse", "HEAD") or None, "dirty": bool(git("status", "--porcelain"))}


def write_layer(gdf, path, *, tolerance: float, grid: float, precision: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    simplified(gdf, tolerance, grid).to_file(path, driver="GeoJSON", COORDINATE_PRECISION=precision)


def write_review(sites: pd.DataFrame) -> None:
    chosen = sites[sites["district"].isin(REVIEW_DISTRICTS)]
    lines = [
        "# Static-source sites to review: Morowali and Banggai",
        "",
        "Generated by `scripts/build_masks.py`. Each row is a group of archive detections (2023–2025) flagged",
        "as a static source. Check each against imagery or local knowledge and note the result here.",
        "",
        "| Site | District | Lat | Lon | Detections | Calendar months | Years | FIRMS type 2 share | Map |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in chosen.itertuples(index=False):
        link = f"https://www.openstreetmap.org/?mlat={r.latitude:.4f}&mlon={r.longitude:.4f}#map=15/{r.latitude:.4f}/{r.longitude:.4f}"
        lines.append(
            f"| {r.site_id} | {r.district} | {r.latitude:.4f} | {r.longitude:.4f} | {r.detections} | "
            f"{r.calendar_months} | {r.years} | {r.type2_share:.2f} | [OSM]({link}) |"
        )
    if chosen.empty:
        lines.append("| – | – | – | – | – | – | – | – | no flagged sites in these districts |")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "static_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="download every input again")
    args = parser.parse_args()
    params = load_params()
    inputs = fetch_inputs(params, args.force)

    provinces = load_provinces(RAW / "adm1.geojson", params.provinces)
    districts = load_districts(RAW / "adm2_simplified.geojson", provinces)
    archive = pd.concat(
        [read_archive(RAW / f"viirs-snpp_{y}_Indonesia.csv", utc_offset_hours=params.utc_offset_hours)
         for y in params.masks.archive_years],
        ignore_index=True,
    )
    inside = assign(archive, provinces, districts)
    masks = build_masks(inside, params.masks)
    categorized = categorize(inside, masks)
    sites = static_sites(categorized, params.masks.cell_deg)

    built = utc_now_iso()
    rule = {
        "archive_years": list(params.masks.archive_years),
        "cell_deg": params.masks.cell_deg,
        "min_calendar_months": params.masks.min_calendar_months,
        "min_years": params.masks.min_years,
        "firms_type": "1 = volcano, 2 = other static land source",
    }
    write_layer(provinces, BOUNDARIES / "provinces.geojson", tolerance=0.0005, grid=0.00001, precision=5)
    write_layer(districts, BOUNDARIES / "districts.geojson", tolerance=0.0005, grid=0.00001, precision=5)
    write_layer(provinces, PUBLIC / "provinces.geojson", tolerance=0.01, grid=0.0001, precision=4)
    focus_districts = districts[districts["province"] == params.focus_province]
    write_layer(focus_districts, PUBLIC / "districts_focus.geojson", tolerance=0.002, grid=0.0001, precision=4)
    write_json(masks_to_json(masks, {"built_at": built, "rule": rule}), PUBLIC / "masks.json")
    write_json(
        feature_collection([
            point_feature(r.longitude, r.latitude, {k: getattr(r, k) for k in SITE_PROPS})
            for r in sites.itertuples(index=False)
        ]),
        PUBLIC / "static_sites.geojson",
    )
    write_json({"built_at": built, "code_version": code_version(), "rule": rule, "inputs": inputs},
               PUBLIC / "manifest.json")
    write_review(sites)

    table = categorized.groupby(["province", "category"]).size().unstack(fill_value=0)
    table = table.reindex(columns=list(CATEGORIES), fill_value=0)
    table["all"] = table.sum(axis=1)
    print(table.to_string())
    print(f"static cells: {len(masks.static)}, volcano cells: {len(masks.volcano)}, sites: {len(sites)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it on real data**

Run: `uv run python scripts/build_masks.py`
Expected: downloads 5 files (about 70 MB), prints an 11-row table of archive detections per province and category, and a line with static cells, volcano cells and sites, all non-zero.

- [ ] **Step 3: Check the outputs against reality**

Run:
```bash
ls -la data/boundaries data/public
grep -c "^| S" reports/static_review.md
grep "Morowali" reports/static_review.md | head -3
```
Expected: the boundary files are under 10 MB each, and the public files under 2 MB each. At least one Morowali site lies near the IMIP complex (about 2.8° S, 122.15° E) with detections in 10 or more calendar months. If either check fails, stop and use superpowers:systematic-debugging before going on.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_masks.py data/boundaries data/public reports/static_review.md
git commit -m "Build static-source and volcano masks from the 2023-2025 archive"
```

---

### Task 11: Refresh from the live feeds

**Files:**
- Create: `scripts/refresh.py`

**Interfaces:**
- Consumes: `data/boundaries/*.geojson`, `data/public/masks.json` (Task 10); `run_refresh`, `Paths` (Task 9); `masks_from_json` (Task 5).
- Produces: `data/live/` outputs (gitignored locally).

- [ ] **Step 1: Write `scripts/refresh.py`**

```python
"""Refresh near-real-time detections from the FIRMS feeds. Run every few hours.

Reads FIRMS_MAP_KEY from the environment when set, to backfill days the 7-day feeds no longer cover.
Always exits 0 when the run itself completes: status.json records whether the data was updated.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import geopandas as gpd

from sulteng.config import ROOT, load_params
from sulteng.masks import masks_from_json
from sulteng.refresh import Paths, run_refresh


def main() -> None:
    params = load_params()
    provinces = gpd.read_file(ROOT / "data" / "boundaries" / "provinces.geojson")
    districts = gpd.read_file(ROOT / "data" / "boundaries" / "districts.geojson")
    masks = masks_from_json(json.loads((ROOT / "data" / "public" / "masks.json").read_text(encoding="utf-8")))
    status = run_refresh(
        params, provinces, districts, masks,
        Paths(live=ROOT / "data" / "live", raw=ROOT / "data" / "raw"),
        datetime.now(timezone.utc),
        map_key=os.environ.get("FIRMS_MAP_KEY") or None,
    )
    print(json.dumps(status, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `uv run python scripts/refresh.py`
Expected: prints a status with `"status": "ok"` and three sensors with non-zero `rows`.

- [ ] **Step 3: Reconcile the numbers**

Run:
```bash
uv run python - <<'EOF'
import json
now = json.load(open("data/live/now.json"))
for key, w in now["windows"].items():
    for p in w["provinces"]:
        c = p["counts"]
        assert c["all"] == c["volcano"] + c["static_suspect"] + c["other"], (key, p["name"])
        assert c["all"] == sum(c["confidence"].values()) == sum(c["sensors"].values()), (key, p["name"])
    print(key, w["label"], w["coverage"])
focus = next(p for p in now["windows"]["7d"]["provinces"] if p["name"] == now["focus"])
print("Sulteng 7d:", focus["counts"])
print("missing days in daily:", sum(d["counts"] is None for d in now["daily"]))
EOF
```
Expected: no assertion errors. The last month shows mostly `missing` days when no key is set, the 7-day window shows mostly `complete` days, and the daily series has `null` entries for the missing days.

- [ ] **Step 4: Commit**

```bash
git add scripts/refresh.py
git commit -m "Add refresh entry point"
```

---

### Task 12: Brief and site assembly

**Files:**
- Create: `src/sulteng/brief.py`, `src/sulteng/sitebuild.py`, `reports/brief/ringkasan.html.tmpl`, `scripts/build_site.py`, `tests/test_brief.py`, `tests/test_sitebuild.py`

**Interfaces:**
- Consumes: `now.json` shape (Task 8); `MONTHS_ID`.
- Produces: `brief.fmt_int`, `brief.fmt_dec`, `brief.fmt_datetime(iso, offset) -> str`, `brief.coverage_sentence(c) -> str`, `brief.brief_values(now) -> dict[str, str]`, `brief.render_brief(now, template=None) -> str`; `sitebuild.find_chrome() -> str | None`, `sitebuild.build(root, out, *, chrome) -> list[str]` (notes on skipped parts).

- [ ] **Step 1: Write the failing tests**

`tests/test_brief.py`:

```python
import json
from datetime import datetime, timezone

from conftest import make_detections
from sulteng import coverage as cov
from sulteng.brief import coverage_sentence, fmt_datetime, fmt_dec, fmt_int, render_brief
from sulteng.config import load_params
from sulteng.publish import to_public
from sulteng.summary import summarize

PARAMS = load_params()
NOW = datetime(2026, 10, 18, 4, 0, tzinfo=timezone.utc)


def now_json(rows, covered=True):
    det = make_detections([(-1.0, 120.0, utc, None) for _, utc, _ in rows]).drop(columns="type")
    df = det.assign(province="Sulawesi Tengah", district=[d for d, _, _ in rows], category=[c for *_, c in rows])
    c = {}
    if covered:
        for s in PARAMS.sensors:
            c = cov.add(c, s.code, datetime(2026, 8, 31, tzinfo=timezone.utc), NOW)
    areas = {p.name: 1000.0 for p in PARAMS.provinces}
    return json.loads(json.dumps(to_public(summarize(df, c, PARAMS, areas, NOW))))


def test_number_and_date_formats():
    assert fmt_int(12345) == "12.345"
    assert fmt_dec(1234.56) == "1.234,6"
    assert fmt_datetime("2026-10-18T04:00:00+00:00", 8) == "18 Oktober 2026, pukul 12.00 WITA"


def test_coverage_sentences():
    assert "lengkap untuk 30 hari" in coverage_sentence({"days": 30, "complete": 30, "partial": 0, "missing": 0})
    assert "Belum ada data" in coverage_sentence({"days": 30, "complete": 0, "partial": 0, "missing": 30})
    text = coverage_sentence({"days": 30, "complete": 20, "partial": 1, "missing": 9})
    assert "20 dari 30" in text and "9 hari tanpa data" in text


def test_render_fills_everything_and_escapes():
    page = render_brief(now_json([("<script>x</script>", "2026-09-10 05:00", "other"),
                                  ("Morowali", "2026-09-11 05:00", "static_suspect")]))
    assert "$" not in page
    assert "DRAF" in page and "Sulawesi Tengah" in page and "September 2026" in page
    assert "<script>x" not in page and "&lt;script&gt;" in page


def test_render_without_coverage_says_no_data():
    page = render_brief(now_json([], covered=False))
    assert "Belum ada data satelit" in page
    assert "tidak ada data" in page
```

`tests/test_sitebuild.py`:

```python
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
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/test_brief.py tests/test_sitebuild.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sulteng.brief'`

- [ ] **Step 3: Write `reports/brief/ringkasan.html.tmpl`**

```html
<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>Ringkasan titik panas $focus, $last_label</title>
<style>
  @page { size: A4; margin: 15mm 16mm; }
  body { font: 10.5pt/1.45 "Plus Jakarta Sans", "Segoe UI", Helvetica, Arial, sans-serif; color: #201c16; max-width: 46rem; margin: 2rem auto; padding: 0 1rem; }
  @media print { body { margin: 0; padding: 0; max-width: none; } }
  .draft { background: #201c16; color: #f4efe4; padding: 4px 8px; font-size: 9pt; margin: 0 0 12px; }
  h1 { font-size: 20pt; line-height: 1.1; margin: 0 0 4px; }
  h2 { font-size: 13pt; margin: 18px 0 6px; border-bottom: 1px solid #d9d0bd; padding-bottom: 3px; }
  h3 { font-size: 10.5pt; margin: 12px 0 4px; }
  .meta, .note { color: #6e675b; font-size: 9pt; }
  table { border-collapse: collapse; width: 100%; font-size: 9.5pt; }
  th, td { text-align: left; padding: 3px 6px 3px 0; border-bottom: 1px solid #e6dfcf; }
  th { font-size: 8.5pt; color: #6e675b; font-weight: 600; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  tr.focus td { font-weight: 700; background: #fde8d7; }
  ul { padding-left: 16px; }
</style>
</head>
<body>
<p class="draft">DRAF — belum ditinjau mitra LSM. Mohon jangan dikutip.</p>
<h1>Titik panas di $focus</h1>
<p class="meta">$last_label dan $this_label · dibuat $generated · satelit VIIRS: $sensors</p>

<h2>$last_label</h2>
<p>Satelit mencatat <strong>$last_all</strong> titik panas di $focus:</p>
<ul>
  <li><strong>$last_other</strong> titik panas lain. Sebagian mungkin kebakaran vegetasi atau lahan, tetapi belum dikonfirmasi lewat citra atau di lapangan.</li>
  <li><strong>$last_static_suspect</strong> titik di lokasi yang panas hampir sepanjang tahun, seperti smelter, fasilitas gas, atau pabrik. Titik ini dihitung terpisah dan tidak dihapus.</li>
  <li><strong>$last_volcano</strong> titik di gunung api.</li>
</ul>
<p class="note">$last_coverage</p>

<h3>Kabupaten/kota dengan titik panas lain terbanyak</h3>
<table>
  <thead><tr><th>Kabupaten/kota</th><th class="num">Titik panas lain</th><th class="num">Sumber tetap</th></tr></thead>
  <tbody>$district_rows</tbody>
</table>

<h3>Sebelas provinsi, $last_label</h3>
<p class="note">Titik panas lain per 1.000 km² daratan. Semua provinsi dihitung dengan satelit, tanggal, dan cara mengukur luas yang sama.</p>
<table>
  <thead><tr><th>Provinsi</th><th class="num">Per 1.000 km²</th><th class="num">Titik panas lain</th><th class="num">Sumber tetap</th></tr></thead>
  <tbody>$province_rows</tbody>
</table>

<h2>$this_label</h2>
<p><strong>$this_all</strong> titik panas: $this_other titik panas lain, $this_static_suspect di lokasi sumber tetap, $this_volcano di gunung api.</p>
<p class="note">$this_coverage</p>

<h2>Cara membaca angka ini</h2>
<ul>
  <li>Titik panas adalah piksel yang lebih panas dari sekitarnya ketika satelit lewat. Satu kebakaran bisa menghasilkan banyak titik, dan satu titik bukan bukti kebakaran hutan.</li>
  <li>Api kecil, api singkat, atau api di bawah awan dan asap tebal bisa terlewat.</li>
  <li>Lokasi sumber tetap ditandai dari pola 2023–2025. Penanda ini bisa keliru: industri baru mungkin belum tertandai, dan lahan yang dibakar berulang bisa ikut tertandai.</li>
  <li>Angka ini tidak menunjukkan provinsi mana yang paling kurang diperhatikan. Untuk itu perlu data lain, seperti liputan media atau dana penanganan.</li>
  <li>Semua tanggal dalam WITA.</li>
</ul>

<h2>Sumber</h2>
<p class="note">NASA FIRMS, data VIIRS hampir waktu nyata ($sensors). Penanda sumber tetap dan gunung api: arsip FIRMS VIIRS Suomi NPP 2023–2025. Batas wilayah: geoBoundaries, © kontributor OpenStreetMap.</p>
</body>
</html>
```

- [ ] **Step 4: Write `src/sulteng/brief.py`**

```python
"""The Indonesian brief: last month and this month, filled from now.json."""

from __future__ import annotations

import html
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sulteng.config import ROOT
from sulteng.summary import MONTHS_ID

TEMPLATE = ROOT / "reports" / "brief" / "ringkasan.html.tmpl"
_SWAP = str.maketrans({",": ".", ".": ","})


def fmt_int(n) -> str:
    return f"{int(n):,}".translate(_SWAP)


def fmt_dec(x: float, digits: int = 1) -> str:
    return f"{x:,.{digits}f}".translate(_SWAP)


def fmt_datetime(iso: str, utc_offset_hours: int) -> str:
    moment = datetime.fromisoformat(iso).astimezone(timezone(timedelta(hours=utc_offset_hours)))
    return f"{moment.day} {MONTHS_ID[moment.month - 1]} {moment.year}, pukul {moment:%H.%M} WITA"


def no_data(c: dict) -> bool:
    return c["days"] > 0 and c["missing"] == c["days"]


def coverage_sentence(c: dict) -> str:
    if no_data(c):
        return "Belum ada data satelit untuk periode ini, jadi angkanya belum bisa dipakai."
    if c["complete"] == c["days"]:
        return f"Data satelit lengkap untuk {c['days']} hari dalam periode ini."
    parts = [f"Data satelit lengkap untuk {c['complete']} dari {c['days']} hari"]
    if c["partial"]:
        parts.append(f"{c['partial']} hari hanya sebagian")
    if c["missing"]:
        parts.append(f"{c['missing']} hari tanpa data")
    return ", ".join(parts) + ". Jumlah sebenarnya bisa lebih tinggi."


def _focus(window: dict, focus: str) -> dict:
    return next(p for p in window["provinces"] if p["name"] == focus)["counts"]


def _count(value: int, window: dict) -> str:
    return "tidak ada data" if no_data(window["coverage"]) else fmt_int(value)


def district_rows(window: dict, limit: int = 8) -> str:
    if no_data(window["coverage"]):
        return '<tr><td colspan="3">Tidak ada data.</td></tr>'
    rows = [d for d in window["focus_districts"] if d["counts"]["all"]][:limit]
    if not rows:
        return '<tr><td colspan="3">Tidak ada titik panas yang tercatat.</td></tr>'
    return "".join(
        f'<tr><td>{html.escape(d["district"])}</td><td class="num">{fmt_int(d["counts"]["other"])}</td>'
        f'<td class="num">{fmt_int(d["counts"]["static_suspect"])}</td></tr>'
        for d in rows
    )


def province_rows(window: dict, focus: str) -> str:
    if no_data(window["coverage"]):
        return '<tr><td colspan="4">Tidak ada data.</td></tr>'
    rows = []
    for p in sorted(window["provinces"], key=lambda p: (-p["per_1000_km2"]["other"], p["name"])):
        cls = ' class="focus"' if p["name"] == focus else ""
        rows.append(
            f'<tr{cls}><td>{html.escape(p["name"])}</td>'
            f'<td class="num">{fmt_dec(p["per_1000_km2"]["other"])}</td>'
            f'<td class="num">{fmt_int(p["counts"]["other"])}</td>'
            f'<td class="num">{fmt_int(p["counts"]["static_suspect"])}</td></tr>'
        )
    return "".join(rows)


def brief_values(now: dict) -> dict[str, str]:
    focus = now["focus"]
    last, this = now["windows"]["last_month"], now["windows"]["this_month"]
    lc, tc = _focus(last, focus), _focus(this, focus)
    keys = ("all", "other", "static_suspect", "volcano")
    return {
        "focus": html.escape(focus),
        "generated": fmt_datetime(now["generated_at"], now["utc_offset_hours"]),
        "sensors": html.escape(", ".join(s["name"] for s in now["sensors"])),
        "last_label": html.escape(last["label"]),
        "this_label": html.escape(this["label"]),
        **{f"last_{k}": _count(lc[k], last) for k in keys},
        **{f"this_{k}": _count(tc[k], this) for k in keys},
        "last_coverage": coverage_sentence(last["coverage"]),
        "this_coverage": coverage_sentence(this["coverage"]),
        "district_rows": district_rows(last),
        "province_rows": province_rows(last, focus),
    }


def render_brief(now: dict, template: str | None = None) -> str:
    text = template if template is not None else Path(TEMPLATE).read_text(encoding="utf-8")
    return string.Template(text).substitute(brief_values(now))
```

- [ ] **Step 5: Write `src/sulteng/sitebuild.py` and `scripts/build_site.py`**

`src/sulteng/sitebuild.py`:

```python
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
```

`scripts/build_site.py`:

```python
"""Build the static site into _site/."""

from sulteng.config import ROOT
from sulteng.sitebuild import build, find_chrome


def main() -> None:
    for note in build(ROOT, ROOT / "_site", chrome=find_chrome()):
        print(f"note: {note}")
    print(f"site written to {ROOT / '_site'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_brief.py tests/test_sitebuild.py -q`
Expected: `6 passed`

- [ ] **Step 7: Build with real data and look at the PDF**

Run: `uv run python scripts/build_site.py && ls -la _site _site/data`
Expected: `_site/ringkasan.pdf` exists. Render page 1 to an image with `pdftoppm -png -r 70 -f 1 -l 1 _site/ringkasan.pdf /tmp/brief` and read the image. The draft label, numbers and tables should be visible and no `$` placeholder should remain.

- [ ] **Step 8: Commit**

```bash
git add src/sulteng/brief.py src/sulteng/sitebuild.py reports/brief scripts/build_site.py tests/test_brief.py tests/test_sitebuild.py
git commit -m "Render the Indonesian brief and assemble the static site"
```

---

### Task 13: Public site

**Files:**
- Create: `site/index.html`, `site/styles.css`, `site/app.js`

**Interfaces:**
- Consumes (from `_site/data/`): `now.json`, `status.json`, `focus_detections.geojson`, `static_sites.geojson`, `provinces.geojson`, `districts_focus.geojson`, `manifest.json`.

- [ ] **Step 1: Set the visual direction**

Invoke the `frontend-design` skill. Brief: a public monitoring page for an Indonesian NGO audience (residents, journalists, local officials), mostly read on phones. It shows current fire detections and must feel trustworthy and calm, not alarmist. Starting direction, adjust as the skill advises: warm paper background (`#f4efe4`), dark ink (`#201c16`), one fire colour (`#c2410c`) reserved for possible-fire detections, a slate (`#52606d`) for static sources, an earth brown (`#8b6b3d`) for volcanoes. Plus Jakarta Sans throughout, a typeface designed in Jakarta. Big tabular numbers for the three counts. A sticky period switcher. Record decisions as a comment block at the top of `styles.css`.

- [ ] **Step 2: Write `site/index.html`**

```html
<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Titik panas Sulawesi Tengah</title>
  <meta name="description" content="Titik panas satelit di Sulawesi Tengah: 24 jam terakhir, 7 hari, bulan ini dan bulan lalu. Sumber panas industri dan gunung api dihitung terpisah.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <p class="draft">DRAF — belum ditinjau mitra LSM. Mohon jangan dikutip.</p>

  <header class="top">
    <div class="wrap">
      <h1>Titik panas di Sulawesi Tengah</h1>
      <p class="lede">Deteksi panas dari tiga satelit VIIRS, diperbarui setiap enam jam. Titik panas belum tentu kebakaran hutan. Lokasi industri dan gunung api dihitung terpisah.</p>
      <p class="status" id="status" aria-live="polite">Memuat status data…</p>
    </div>
  </header>

  <nav class="windows" aria-label="Pilih periode">
    <div class="wrap" id="window-buttons">
      <button type="button" data-window="24h" aria-pressed="false">24 jam</button>
      <button type="button" data-window="7d" aria-pressed="true">7 hari</button>
      <button type="button" data-window="this_month" aria-pressed="false">Bulan ini</button>
      <button type="button" data-window="last_month" aria-pressed="false">Bulan lalu</button>
    </div>
  </nav>

  <main class="wrap">
    <section class="now" aria-labelledby="window-label">
      <h2 id="window-label">7 hari terakhir</h2>
      <div class="tallies" id="tallies"></div>
      <p class="coverage" id="coverage-note"></p>
    </section>

    <section class="map-block" aria-labelledby="map-title">
      <h2 id="map-title">Peta</h2>
      <div id="map" role="region" aria-label="Peta titik panas Sulawesi Tengah"></div>
      <ul class="legend">
        <li><span class="key key-other"></span>Titik panas lain</li>
        <li><span class="key key-static"></span>Dugaan sumber panas tetap/industri</li>
        <li><span class="key key-volcano"></span>Gunung api</li>
        <li><span class="key key-site"></span>Lokasi sumber tetap (pola 2023–2025)</li>
      </ul>
    </section>

    <section class="districts" aria-labelledby="districts-title">
      <h2 id="districts-title">Per kabupaten/kota</h2>
      <div id="districts"></div>
    </section>

    <section aria-labelledby="daily-title">
      <h2 id="daily-title">Per hari, bulan lalu dan bulan ini</h2>
      <p class="note">Arsiran: tidak ada data satelit hari itu. Batang pucat: data hari itu belum lengkap.</p>
      <div id="daily" class="daily"></div>
    </section>

    <section aria-labelledby="compare-title">
      <h2 id="compare-title">Dibandingkan dengan sepuluh provinsi lain</h2>
      <p class="note">Titik panas lain per 1.000 km² daratan, periode dan satelit yang sama. Bagian abu-abu: sumber tetap dan gunung api.</p>
      <ul id="compare" class="bars"></ul>
    </section>

    <section class="prose" aria-labelledby="read-title">
      <h2 id="read-title">Cara membaca</h2>
      <ul>
        <li>Titik panas adalah piksel yang lebih panas dari sekitarnya ketika satelit lewat. Satu kebakaran bisa menghasilkan banyak titik, dan satu titik bukan bukti kebakaran hutan.</li>
        <li>Api kecil, api singkat, dan api di bawah awan atau asap tebal bisa terlewat.</li>
        <li>"Dugaan sumber panas tetap" adalah lokasi yang panas di banyak bulan selama 2023–2025, misalnya smelter nikel di Morowali atau kilang gas di Banggai. Penanda ini bisa keliru ke dua arah.</li>
        <li>Angka ini tidak menunjukkan provinsi mana yang paling kurang diperhatikan. Untuk itu perlu data lain, seperti liputan media atau dana penanganan.</li>
        <li>Semua tanggal dan jam dalam WITA.</li>
      </ul>
    </section>

    <section class="prose" aria-labelledby="sources-title">
      <h2 id="sources-title">Sumber dan unduhan</h2>
      <ul id="sources"></ul>
      <ul class="downloads">
        <li><a href="ringkasan.pdf">Ringkasan bulan lalu (PDF)</a> · <a href="ringkasan.html">versi web</a></li>
        <li><a href="data/now.json">Angka per periode (JSON)</a></li>
        <li><a href="data/focus_detections.geojson">Titik panas Sulawesi Tengah (GeoJSON)</a></li>
        <li><a href="data/static_sites.geojson">Lokasi dugaan sumber tetap (GeoJSON)</a></li>
      </ul>
    </section>
  </main>

  <footer class="wrap">
    <p>Data: NASA FIRMS (VIIRS). Batas wilayah: geoBoundaries, © kontributor OpenStreetMap.</p>
  </footer>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Write `site/styles.css`**

```css
/* Direction: field-report calm. Paper and ink; colour only where it carries meaning
   (fire = possible fire, slate = static source, earth = volcano). One typeface, Plus Jakarta Sans.
   Numbers are large and tabular; everything else stays quiet. */
:root {
  --paper: #f4efe4;
  --ink: #201c16;
  --muted: #6e675b;
  --rule: #d9d0bd;
  --fire: #c2410c;
  --static: #52606d;
  --volcano: #8b6b3d;
  --focus: #fde8d7;
  --warn: #8a1c0b;
  --font: "Plus Jakarta Sans", "Segoe UI", system-ui, sans-serif;
}
* { box-sizing: border-box; }
html { background: var(--paper); color: var(--ink); font: 400 16px/1.55 var(--font); -webkit-text-size-adjust: 100%; }
body { margin: 0; }
.wrap { max-width: 68rem; margin: 0 auto; padding: 0 1.25rem; }
.draft { margin: 0; padding: .45rem 1.25rem; background: var(--ink); color: var(--paper); font-size: .8rem; text-align: center; }
.top { padding: 2.5rem 0 1.5rem; }
h1 { font-size: clamp(2rem, 5vw, 3.4rem); line-height: 1.05; font-weight: 800; letter-spacing: -.02em; margin: 0 0 .75rem; max-width: 18ch; }
.lede { font-size: 1.1rem; max-width: 44rem; margin: 0 0 1rem; }
.status { margin: 0; font-size: .9rem; color: var(--muted); }
.status.warn { color: var(--warn); font-weight: 600; }
.windows { position: sticky; top: 0; z-index: 1100; background: var(--paper); border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }
.windows .wrap { display: flex; gap: .4rem; padding-top: .6rem; padding-bottom: .6rem; overflow-x: auto; }
.windows button { font: 600 .95rem var(--font); color: var(--ink); background: transparent; border: 1px solid var(--rule); border-radius: 999px; padding: .4rem .95rem; cursor: pointer; white-space: nowrap; }
.windows button[aria-pressed="true"] { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.windows button:focus-visible { outline: 3px solid var(--fire); outline-offset: 2px; }
main { padding-bottom: 3rem; }
section { padding: 2rem 0; border-bottom: 1px solid var(--rule); min-width: 0; }
h2 { font-size: 1.35rem; font-weight: 700; margin: 0 0 1rem; letter-spacing: -.01em; }
.tallies { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
.tally { border-top: 4px solid var(--rule); padding-top: .6rem; }
.tally-other { border-color: var(--fire); }
.tally-static_suspect { border-color: var(--static); }
.tally-volcano { border-color: var(--volcano); }
.tally-num { display: block; font-size: clamp(2.2rem, 7vw, 3.6rem); font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.tally-label { display: block; font-size: .9rem; color: var(--muted); margin-top: .35rem; }
.coverage, .note, .quiet { color: var(--muted); font-size: .9rem; }
.quiet { margin: .5rem 0 0; }
#map { height: 30rem; max-height: 70vh; border: 1px solid var(--rule); background: #e8e2d4; }
.legend { list-style: none; padding: 0; margin: .75rem 0 0; display: flex; flex-wrap: wrap; gap: .4rem 1.2rem; font-size: .85rem; color: var(--muted); }
.key { display: inline-block; width: .8rem; height: .8rem; border-radius: 50%; margin-right: .4rem; vertical-align: -.05rem; }
.key-other { background: var(--fire); }
.key-static { background: var(--static); }
.key-volcano { background: var(--volcano); }
.key-site { background: #fff; border: 2px solid var(--static); }
.table-scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .95rem; }
th, td { text-align: left; padding: .45rem .6rem .45rem 0; border-bottom: 1px solid var(--rule); }
thead th { font-size: .8rem; font-weight: 600; color: var(--muted); }
tbody th { font-weight: 600; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.daily svg { display: block; }
.daily .grid { stroke: var(--rule); stroke-width: 1; }
.daily .tick { fill: var(--muted); font-size: 11px; font-family: var(--font); }
.daily .hatch { stroke: var(--rule); stroke-width: 2; }
.daily .bar-other { fill: var(--fire); }
.daily .bar-static_suspect { fill: var(--static); }
.daily .bar-volcano { fill: var(--volcano); }
.daily .partial { opacity: .45; }
.bars { list-style: none; padding: 0; margin: 0; display: grid; gap: .3rem; }
.bars li { display: grid; grid-template-columns: 11rem 1fr 14rem; align-items: center; gap: .75rem; padding: .25rem .4rem; }
.bars li.focus { background: var(--focus); font-weight: 700; }
.bar-track { display: flex; height: .9rem; }
.bar-other { background: var(--fire); }
.bar-fixed { background: var(--static); opacity: .5; }
.bar-value { font-variant-numeric: tabular-nums; }
.bar-value small { color: var(--muted); font-weight: 400; }
.prose ul { padding-left: 1.1rem; max-width: 44rem; }
.prose li { margin-bottom: .5rem; }
.downloads { margin-top: 1rem; }
a { color: var(--fire); text-underline-offset: .15em; }
footer { padding-top: 1.5rem; padding-bottom: 3rem; color: var(--muted); font-size: .85rem; }
@media (min-width: 60rem) {
  main { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr); column-gap: 2.5rem; }
  main > section { grid-column: 1 / -1; }
  main > .now { grid-column: 1; grid-row: 1; }
  main > .districts { grid-column: 1; grid-row: 2; }
  main > .map-block { grid-column: 2; grid-row: 1 / span 2; }
}
@media (max-width: 40rem) {
  .tallies { gap: .6rem; }
  .tally-label { font-size: .8rem; }
  .bars li { grid-template-columns: 1fr auto; }
  .bar-track { grid-column: 1 / -1; grid-row: 2; }
  #map { height: 24rem; }
}
```

- [ ] **Step 4: Write `site/app.js`**

```js
"use strict";

const DATA = "data/";
const NS = "http://www.w3.org/2000/svg";
const ORDER = ["other", "static_suspect", "volcano"];
const LABEL = { other: "Titik panas lain", static_suspect: "Dugaan sumber tetap/industri", volcano: "Gunung api" };
const CONFIDENCE = { l: "rendah", n: "sedang", h: "tinggi" };
const nf0 = new Intl.NumberFormat("id-ID");
const nf1 = new Intl.NumberFormat("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const css = getComputedStyle(document.documentElement);
const cssVar = (name) => css.getPropertyValue(name).trim();
const COLOR = { other: cssVar("--fire"), static_suspect: cssVar("--static"), volcano: cssVar("--volcano") };
const state = { window: "7d" };

function setAttrs(node, attrs) {
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    node.setAttribute(key, value === true ? "" : String(value));
  }
}

function h(tag, attrs, ...kids) {
  const node = document.createElement(tag);
  setAttrs(node, attrs);
  node.append(...kids.flat().filter((k) => k !== null && k !== undefined && k !== false));
  return node;
}

function s(tag, attrs, ...kids) {
  const node = document.createElementNS(NS, tag);
  setAttrs(node, attrs);
  node.append(...kids.flat().filter((k) => k !== null && k !== undefined && k !== false));
  return node;
}

function esc(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

async function load(name) {
  const response = await fetch(DATA + name, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
  return response.json();
}

function witaTime(iso) {
  const text = new Date(iso).toLocaleString("id-ID", {
    timeZone: "Asia/Makassar", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
  return `${text} WITA`;
}

function shortDay(isoDate) {
  return new Date(`${isoDate}T12:00:00+08:00`).toLocaleDateString("id-ID", { timeZone: "Asia/Makassar", day: "numeric", month: "short" });
}

const noData = (c) => c.days > 0 && c.missing === c.days;

function coverageNote(c) {
  if (noData(c)) return "Tidak ada data satelit untuk periode ini.";
  if (c.complete === c.days) return `Data satelit lengkap untuk ${c.days} hari.`;
  const parts = [`Data lengkap ${c.complete} dari ${c.days} hari`];
  if (c.partial) parts.push(`${c.partial} hari sebagian`);
  if (c.missing) parts.push(`${c.missing} hari tanpa data`);
  return `${parts.join(", ")}. Jumlah sebenarnya bisa lebih tinggi.`;
}

function renderStatus(status) {
  const target = document.getElementById("status");
  if (!status) {
    target.textContent = "Status pembaruan tidak tersedia.";
    return;
  }
  if (status.status === "update_failed") {
    target.className = "status warn";
    target.textContent = status.last_success
      ? `Pembaruan terakhir gagal (${witaTime(status.last_attempt)}). Data yang tampil berasal dari ${witaTime(status.last_success)} dan mungkin sudah lama.`
      : `Pembaruan gagal (${witaTime(status.last_attempt)}). Belum ada data yang berhasil diambil.`;
    return;
  }
  const lagging = Object.values(status.sensors || {}).filter((v) => v.status !== "ok").map((v) => v.name);
  target.textContent = `Diperbarui ${witaTime(status.last_success)}.`
    + (lagging.length ? ` Data ${lagging.join(", ")} tidak lengkap pada pembaruan ini.` : "");
  if (lagging.length) target.className = "status warn";
}

const focusCounts = (win, focus) => win.provinces.find((p) => p.name === focus).counts;

function renderTallies(win, focus) {
  document.getElementById("window-label").textContent = win.label;
  document.getElementById("coverage-note").textContent = coverageNote(win.coverage);
  const counts = focusCounts(win, focus);
  const empty = noData(win.coverage);
  const target = document.getElementById("tallies");
  target.replaceChildren(...ORDER.map((key) => h("div", { class: `tally tally-${key}` },
    h("span", { class: "tally-num" }, empty ? "–" : nf0.format(counts[key])),
    h("span", { class: "tally-label" }, LABEL[key]))));
  if (!empty && counts.all === 0) {
    target.append(h("p", { class: "quiet" }, "Tidak ada deteksi yang dilaporkan dalam periode ini."));
  }
}

function renderDistricts(win) {
  const target = document.getElementById("districts");
  if (noData(win.coverage)) {
    target.replaceChildren(h("p", { class: "quiet" }, "Tidak ada data untuk periode ini."));
    return;
  }
  if (!win.focus_districts.length) {
    target.replaceChildren(h("p", { class: "quiet" }, "Tidak ada deteksi yang dilaporkan dalam periode ini."));
    return;
  }
  const head = h("tr", {}, h("th", { scope: "col" }, "Kabupaten/kota"),
    ...ORDER.map((k) => h("th", { scope: "col", class: "num" }, LABEL[k])));
  const rows = win.focus_districts.map((d) => h("tr", {}, h("th", { scope: "row" }, d.district),
    ...ORDER.map((k) => h("td", { class: "num" }, nf0.format(d.counts[k])))));
  target.replaceChildren(h("div", { class: "table-scroll" }, h("table", {}, h("thead", {}, head), h("tbody", {}, rows))));
}

function renderCompare(win, focus) {
  const target = document.getElementById("compare");
  if (noData(win.coverage)) {
    target.replaceChildren(h("li", { class: "quiet" }, "Tidak ada data untuk periode ini."));
    return;
  }
  const rows = win.provinces.map((p) => {
    const k = 1000 / p.area_km2;
    return { p, other: p.counts.other * k, fixed: (p.counts.static_suspect + p.counts.volcano) * k };
  }).sort((a, b) => b.other - a.other || a.p.name.localeCompare(b.p.name));
  const max = Math.max(...rows.map((r) => r.other + r.fixed), 1e-9);
  const pct = (v) => `${(v / max) * 100}%`;
  target.replaceChildren(...rows.map(({ p, other, fixed }) => {
    const share = p.counts.all ? (p.counts.static_suspect + p.counts.volcano) / p.counts.all : 0;
    const note = share === 0 ? "" : share < 0.01 ? " · <1% sumber tetap" : ` · ${Math.round(share * 100)}% sumber tetap`;
    return h("li", { class: p.name === focus ? "focus" : null },
      h("span", { class: "bar-name" }, p.name),
      h("span", { class: "bar-track", "aria-hidden": "true" },
        h("span", { class: "bar-other", style: `width:${pct(other)}` }),
        h("span", { class: "bar-fixed", style: `width:${pct(fixed)}` })),
      h("span", { class: "bar-value" }, nf1.format(other), h("small", {}, note)));
  }));
}

function niceCeil(v) {
  const p = 10 ** Math.floor(Math.log10(v));
  for (const f of [1, 2, 2.5, 5, 10]) if (f * p >= v) return f * p;
  return 10 * p;
}

function renderDaily(now) {
  const target = document.getElementById("daily");
  const days = now.daily;
  const width = Math.max(target.clientWidth, 300);
  const height = 200;
  const m = { t: 10, r: 6, b: 26, l: 36 };
  const step = (width - m.l - m.r) / days.length;
  const totals = days.map((d) => (d.counts ? ORDER.reduce((sum, k) => sum + d.counts[k], 0) : 0));
  const top = niceCeil(Math.max(1, ...totals));
  const y = (v) => height - m.b - (v / top) * (height - m.t - m.b);
  const missing = days.filter((d) => !d.counts).length;
  const chart = s("svg", {
    width, height, viewBox: `0 0 ${width} ${height}`, role: "img",
    "aria-label": `Titik panas per hari di ${now.focus}, ${shortDay(days[0].date)} sampai ${shortDay(days[days.length - 1].date)}. ${missing} hari tanpa data.`,
  });
  chart.append(s("defs", {}, s("pattern", { id: "nodata", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" },
    s("line", { x1: 0, y1: 0, x2: 0, y2: 6, class: "hatch" }))));
  for (let i = 0; i <= 4; i += 1) {
    const v = (top * i) / 4;
    chart.append(s("line", { x1: m.l, x2: width - m.r, y1: y(v), y2: y(v), class: "grid" }));
    chart.append(s("text", { x: m.l - 6, y: y(v), class: "tick", "text-anchor": "end", "dominant-baseline": "middle" }, nf0.format(v)));
  }
  days.forEach((d, i) => {
    const x = m.l + i * step + step * 0.12;
    const w = Math.max(step * 0.76, 1);
    if (!d.counts) {
      chart.append(s("rect", { x, y: m.t, width: w, height: height - m.t - m.b, fill: "url(#nodata)" },
        s("title", {}, `${shortDay(d.date)}: tidak ada data`)));
    } else {
      let base = 0;
      for (const key of ORDER) {
        const v = d.counts[key];
        if (!v) continue;
        chart.append(s("rect", { x, y: y(base + v), width: w, height: y(base) - y(base + v), class: `bar-${key}${d.coverage === "partial" ? " partial" : ""}` },
          s("title", {}, `${shortDay(d.date)}: ${nf0.format(v)} ${LABEL[key].toLowerCase()}`)));
        base += v;
      }
    }
    const day = Number(d.date.slice(8, 10));
    if (day === 1 || (day === 15 && step > 6)) {
      chart.append(s("text", { x: m.l + i * step, y: height - 8, class: "tick" }, shortDay(d.date)));
    }
  });
  target.replaceChildren(chart);
}

function sitePopup(p) {
  return `<strong>Dugaan sumber panas tetap</strong><br>${esc(p.district || "")}<br>`
    + `${nf0.format(p.detections)} deteksi pada ${p.calendar_months} bulan berbeda, ${p.years} tahun (2023–2025)`;
}

function pointPopup(p) {
  return `<strong>${esc(LABEL[p.category])}</strong><br>${esc(p.district || "")}<br>${witaTime(p.utc)}<br>`
    + `Satelit ${esc(p.sensor)} · keyakinan ${esc(CONFIDENCE[p.confidence] || p.confidence)}`;
}

function makeMap(provinces, districts, sites, focus) {
  const map = L.map("map", { preferCanvas: true, scrollWheelZoom: false });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 17, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">kontributor OpenStreetMap</a>',
  }).addTo(map);
  let focusLayer = null;
  if (provinces) {
    L.geoJSON(provinces, {
      style: (f) => ({ color: cssVar("--ink"), weight: f.properties.name === focus ? 2 : 0.8, opacity: f.properties.name === focus ? 0.9 : 0.4, fill: false }),
      onEachFeature: (f, layer) => { if (f.properties.name === focus) focusLayer = layer; },
      interactive: false,
    }).addTo(map);
  }
  if (districts) {
    L.geoJSON(districts, { style: { color: cssVar("--muted"), weight: 0.6, dashArray: "3 3", fill: false }, interactive: false }).addTo(map);
  }
  if (sites) {
    L.geoJSON(sites, {
      filter: (f) => f.properties.province === focus,
      pointToLayer: (f, latlng) => L.circleMarker(latlng, { radius: 7, color: COLOR.static_suspect, weight: 2, fillColor: "#ffffff", fillOpacity: 0.9 }),
      onEachFeature: (f, layer) => layer.bindPopup(sitePopup(f.properties)),
    }).addTo(map);
  }
  if (focusLayer) map.fitBounds(focusLayer.getBounds(), { padding: [12, 12] });
  else map.setView([-1.4, 121.4], 7);
  return { map, points: L.layerGroup().addTo(map) };
}

function inWindow(props, win, key) {
  if (key === "24h" || key === "7d") {
    const t = Date.parse(props.utc);
    return t > Date.parse(win.start) && t <= Date.parse(win.end);
  }
  return props.local_date >= win.start && props.local_date <= win.end;
}

function updatePoints(ctx, points, win, key) {
  ctx.points.clearLayers();
  if (!points) return;
  for (const f of points.features) {
    if (!inWindow(f.properties, win, key)) continue;
    const [lon, lat] = f.geometry.coordinates;
    const color = COLOR[f.properties.category];
    L.circleMarker([lat, lon], { radius: 4, color, weight: 1, fillColor: color, fillOpacity: 0.75 })
      .bindPopup(pointPopup(f.properties)).addTo(ctx.points);
  }
}

function renderSources(manifest, status) {
  const items = [];
  for (const v of Object.values((status && status.sensors) || {})) {
    items.push(h("li", {}, `NASA FIRMS, VIIRS ${v.name}, data hampir waktu nyata: `,
      v.last_success ? `diambil ${witaTime(v.last_success)}` : "belum berhasil diambil"));
  }
  if (manifest) {
    items.push(h("li", {}, `Penanda sumber tetap dan gunung api: arsip FIRMS VIIRS Suomi NPP ${manifest.rule.archive_years.join(", ")}, dibuat ${witaTime(manifest.built_at)}.`));
  }
  items.push(h("li", {}, "Batas provinsi dan kabupaten/kota: geoBoundaries (OpenStreetMap)."));
  document.getElementById("sources").replaceChildren(...items);
}

function setupButtons(onChange) {
  const buttons = [...document.querySelectorAll("#window-buttons button")];
  for (const button of buttons) {
    button.addEventListener("click", () => {
      state.window = button.dataset.window;
      for (const b of buttons) b.setAttribute("aria-pressed", String(b === button));
      onChange();
    });
  }
}

function debounce(fn, ms) {
  let timer;
  return () => { clearTimeout(timer); timer = setTimeout(fn, ms); };
}

async function main() {
  const names = ["now.json", "status.json", "focus_detections.geojson", "static_sites.geojson", "provinces.geojson", "districts_focus.geojson", "manifest.json"];
  const results = await Promise.allSettled(names.map(load));
  const [now, status, points, sites, provinces, districts, manifest] = results.map((r) => (r.status === "fulfilled" ? r.value : null));
  renderStatus(status);
  renderSources(manifest, status);
  if (!now) {
    for (const id of ["tallies", "districts", "daily", "compare", "map"]) {
      document.getElementById(id).replaceChildren(h("p", { class: "quiet" }, "Data tidak dapat dimuat."));
    }
    return;
  }
  const ctx = typeof L === "undefined" ? null : makeMap(provinces, districts, sites, now.focus);
  if (!ctx) document.getElementById("map").replaceChildren(h("p", { class: "quiet" }, "Peta tidak dapat dimuat."));
  const update = () => {
    const win = now.windows[state.window];
    renderTallies(win, now.focus);
    renderDistricts(win);
    renderCompare(win, now.focus);
    if (ctx) updatePoints(ctx, points, win, state.window);
  };
  setupButtons(update);
  update();
  renderDaily(now);
  window.addEventListener("resize", debounce(() => renderDaily(now), 150));
}

main();
```

- [ ] **Step 5: Verify the Leaflet SRI hashes**

Run:
```bash
for f in leaflet.css leaflet.js; do printf "%s sha256-" $f; curl -sS https://unpkg.com/leaflet@1.9.4/dist/$f | openssl dgst -sha256 -binary | base64; done
```
Expected: `sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=` and `sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=`. If either differs, use the printed value in `index.html`.

- [ ] **Step 6: Build, serve, and look at it**

Run:
```bash
uv run python scripts/build_site.py
(uv run python -m http.server 8765 -d _site >/dev/null 2>&1 &) ; sleep 1
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1280,2600 --virtual-time-budget=8000 --screenshot=/tmp/site-desktop.png http://localhost:8765/
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=390,3200 --virtual-time-budget=8000 --screenshot=/tmp/site-phone.png http://localhost:8765/
"$CHROME" --headless=new --disable-gpu --virtual-time-budget=8000 --dump-dom http://localhost:8765/ | grep -o 'tally-num">[^<]*' 
```
Expected: both screenshots show the tallies, the map with points, the daily chart with hatched missing days, and the province bars; the DOM dump shows three tally numbers. Read both images and fix layout problems before going on.

Missing-coverage check: copy `_site/data/now.json` aside, edit the copy in `_site/data/` so `windows.last_month.coverage` is `{"days":30,"complete":0,"partial":0,"missing":30}`, click "Bulan lalu" in the browser (or set `state.window = "last_month"` in `app.js` temporarily), and confirm the tallies show "–" and the note says "Tidak ada data satelit untuk periode ini." Restore the file afterwards.

- [ ] **Step 7: Commit**

```bash
git add site
git commit -m "Add the public site: tallies, map, districts, daily chart, comparison"
```

---

### Task 14: Automation, Makefile and README

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/publish.yml`, `Makefile`, `README.md`

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: tests
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --locked
      - run: uv run pytest -q
```

- [ ] **Step 2: Write `.github/workflows/publish.yml`**

```yaml
name: publish
on:
  push:
    branches: [main]
  schedule:
    - cron: "23 */6 * * *"   # every six hours, off the hour
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: publish
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --locked

      - name: Restore live data from the data-store branch
        run: |
          mkdir -p data/live
          if git fetch --depth=1 origin data-store; then
            git archive FETCH_HEAD | tar -x -C data/live
          else
            echo "No data-store branch yet; starting empty."
          fi

      - name: Refresh near-real-time detections
        env:
          FIRMS_MAP_KEY: ${{ secrets.FIRMS_MAP_KEY }}
        run: uv run python scripts/refresh.py

      - name: Save live data to the data-store branch
        run: |
          cd data/live
          git init -q -b data-store
          git add -A
          git -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
            commit -q -m "Live data $(date -u +%Y-%m-%dT%H:%MZ)"
          git push -q -f "https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}.git" data-store

      - run: uv run python scripts/build_site.py
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Write `Makefile`**

```make
.PHONY: test masks refresh site serve all

test:
	uv run pytest -q

masks:
	uv run python scripts/build_masks.py

refresh:
	uv run python scripts/refresh.py

site:
	uv run python scripts/build_site.py

serve: site
	uv run python -m http.server 8000 -d _site

all: refresh site
```

- [ ] **Step 4: Write `README.md`**

````markdown
# Titik panas Sulawesi Tengah

A static website showing satellite fire detections (hotspots) in Central Sulawesi for the last 24 hours, the last 7 days, this month and last month, compared over the same period with the other Sulawesi provinces and the five Kalimantan provinces.

The site is in Indonesian and is a draft until the NGO partner reviews the wording.

## What it shows and what it does not

- A hotspot is a satellite pixel hotter than its surroundings during an overpass. It is not a confirmed forest fire, and the site never calls it one.
- Hotspots at places that are hot in many months of the year (nickel smelters in Morowali, the LNG plant in Banggai, mill boilers) are flagged as suspected static sources. Hotspots at volcanoes are flagged too. Both are counted separately and never removed.
- Days without satellite data show as "tidak ada data", never as zero.

## Data

| Source | Use |
|---|---|
| NASA FIRMS VIIRS 7-day feeds (Suomi NPP, NOAA-20, NOAA-21), no key needed | Detections, refreshed every 6 hours |
| NASA FIRMS area API (optional `FIRMS_MAP_KEY`) | Fills in days the 7-day feeds no longer cover, such as the start of last month |
| NASA FIRMS VIIRS Suomi NPP yearly archive 2023–2025 | Builds the static-source and volcano masks |
| geoBoundaries ADM1/ADM2 (OpenStreetMap) | Provinces, districts, land area |

Without a key the site starts with the last 7 days and grows a day at a time. Get a free key at https://firms.modaps.eosdis.nasa.gov/api/map_key/ and store it as the repository secret `FIRMS_MAP_KEY`.

## Running it

Needs [uv](https://docs.astral.sh/uv/). Google Chrome is used, when present, to print the PDF brief.

```bash
uv sync
make test      # unit tests, no network
make refresh   # download the latest detections into data/live/
make serve     # build _site/ and serve it on http://localhost:8000
make masks     # rebuild masks and boundaries from the archive (occasional; outputs are committed)
```

## How it is put together

- `config/params.toml`: provinces, sensors, URLs, the static-source rule.
- `src/sulteng/`: the data code, one module per job (download, parse, assign, masks, store, coverage, summary, refresh, brief, site build).
- `data/boundaries/`, `data/public/`: committed outputs of `make masks`.
- `data/live/`: the rolling two-month store and the files the site reads. In GitHub Actions it lives on the `data-store` branch, which is overwritten on each run so history does not grow.
- `site/`: the HTML, CSS and JavaScript of the page.
- `.github/workflows/publish.yml`: refresh every six hours, save `data/live/`, build, deploy to GitHub Pages.

## Design and plan

- Project plan: `01_Simple_Project_Plan.docx`
- Design: `docs/superpowers/specs/2026-10-18-sp1-fire-monitor-now-design.md`
- Implementation plan: `docs/superpowers/plans/2026-10-18-sp1-fire-monitor-now.md`
- Static-source sites to check by hand: `reports/static_review.md`
````

- [ ] **Step 5: Validate the workflow YAML and run the full suite**

Run: `uv run python -c "import yaml" 2>/dev/null || uv run --with pyyaml python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in ['.github/workflows/ci.yml','.github/workflows/publish.yml']]; print('yaml ok')"` then `make test`
Expected: `yaml ok`, then all tests pass.

- [ ] **Step 6: Commit**

```bash
git add .github Makefile README.md
git commit -m "Add CI, six-hourly publish workflow, Makefile and README"
```

---

### Task 15: Quality pass

**Files:**
- Modify: whatever the reviews find in `site/`, `reports/brief/ringkasan.html.tmpl`, `README.md`, `src/`.

- [ ] **Step 1: Web review.** Invoke `no-ai-slop-web` on `site/index.html`, `site/styles.css` and the desktop and phone screenshots from Task 13. Fix every finding that applies, rebuild, and take new screenshots.
- [ ] **Step 2: Prose review.** Invoke `no-ai-slop` on the Indonesian strings in `site/index.html`, `site/app.js` and `reports/brief/ringkasan.html.tmpl`, and on `README.md`. Keep the meaning and the safety wording ("belum dikonfirmasi", "bukan bukti kebakaran hutan"). Apply the edits.
- [ ] **Step 3: Code review.** Invoke `code-review` on the branch diff against the first commit. Verify each finding before acting on it (superpowers:receiving-code-review), fix the real ones with a test where the finding is a bug, and debug anything unexpected with superpowers:systematic-debugging.
- [ ] **Step 4: Final verification.** Run `make test`, `make refresh`, `make site`, re-run the reconciliation script from Task 11 Step 3, and take one last pair of screenshots.
- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Quality pass: web, prose and code review fixes"
```
