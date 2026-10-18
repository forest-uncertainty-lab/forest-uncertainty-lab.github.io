# SP1: Central Sulawesi fire monitor (now) — design

Date: 2026-10-18 (revised the same day after direction from the project owner)
Source brief: `01_Simple_Project_Plan.docx` ("the plan")

## 1. Understanding

What the project owner said:

- Purpose (plan §1): help people see reliable evidence of forest and land fires in Central Sulawesi (Sulawesi Tengah, "Sulteng").
- Direction given during design: the public view must be **recent** (this month, last month), "because we wanted to see the forest fire right now". A retrospective of past years is not what they want to look at.

Rules carried over from the plan, unchanged:

- No hotspot is called a confirmed forest fire.
- Missing data is never shown as zero.
- Suspected industrial heat is counted separately and never quietly removed.
- Province comparisons use the same sensors, dates and denominator for all 11 provinces.
- No paid database, backend, API, domain or hosted model. Keys are stored only as secrets.

Assumptions (correct them if wrong):

- A1. The session runs without pausing for approvals; the plan plus the direction above is the approved brief.
- A2. Nothing is pushed to GitHub or published from this session.
- A3. Indonesian text written here is a draft. The site and brief carry a visible draft label until the NGO reviewer clears them.
- A4. The plan's multi-year items (G0-01 province comparison on 2023–2025, G0-04 archive completeness 2013–2025) move to the research track with R2. They are not shown on the public site.

## 2. Decomposition

| Sub-project | Scope |
|---|---|
| **SP1 (this spec)** | Near-real-time monitor for Sulteng with an 11-province comparison for the same window; static-source and volcano masks built from the 2023–2025 archive; Indonesian brief for the last full month; automated refresh |
| SP2 | Burned-area evidence (MCD64A1), Sentinel-2/Landsat image checks, 3–5 reviewed case stories |
| SP3 | Research track: G0-01, G0-03, G0-04, G0-05, the G0 amendment, and the R2 decision study |

## 3. Data sources (checked 2026-10-18)

| Source | Access | Use |
|---|---|---|
| FIRMS VIIRS 7-day regional CSVs for Suomi NPP, NOAA-20, NOAA-21 (South-East Asia) | No key | Main input. Each refresh adds what is new. |
| FIRMS area API, `VIIRS_*_NRT` sources | Free `MAP_KEY`, read from the `FIRMS_MAP_KEY` environment variable | Optional backfill of days the 7-day feed no longer covers (needed to fill "last month" on the first run). Skipped when no key is set. |
| FIRMS VIIRS S-NPP yearly archive for Indonesia, 2023–2025 | No key | Builds the static-source and volcano masks only |
| geoBoundaries gbOpen IDN ADM1 (full resolution, 2017) and ADM2 (simplified, 2020) | No key | Province and district assignment; land area |

The 7-day feed has no `type` column, so near-real-time detections cannot be flagged by FIRMS itself. The archive's `type` column and recurrence patterns supply the flags.

Other sources considered on 2026-10-19 (Google Earth Engine for SP2, Copernicus GWIS as an optional cross-check, Open-Meteo only if the NGO asks, NIFC not used) and the reasons are in `docs/backlog.md`. Archive files must postdate FIRMS's May 2025 reprocessing of the VIIRS `type` field; `scripts/build_masks.py` enforces `archive_min_last_modified` from `config/params.toml`.

## 4. Time windows

All dates are WITA (UTC+8). Indonesia has no daylight saving time, so the offset is fixed.

| Window | Definition |
|---|---|
| 24 jam terakhir | acquisition time within 24 hours before the refresh |
| 7 hari terakhir | acquisition time within 7 days before the refresh |
| Bulan ini | WITA dates from the 1st of the current month to today |
| Bulan lalu | all WITA dates of the previous month |

The store keeps detections for the current and previous month and drops older months.

## 5. Coverage: missing versus zero

Each successful download records the time interval it covers, per sensor:

- 7-day feed: from the first to the last acquisition time present in the file. The file's own time is not used, because it does not say which passes the file holds (Suomi NPP lagged its file time by about 10 hours on 2026-10-18). A feed with no rows claims no coverage, so an empty download can never turn into zeros.
- API request: the requested UTC dates, from 00:00 on the first date to 00:00 after the last.

A WITA day is **complete** when every sensor's merged intervals cover the whole day, **missing** when no sensor covers any part of it, and **partial** otherwise. Today is partial once its first pass has arrived; before that it is missing, which the site shows as "tidak ada data" rather than a zero that would read as "no fires". API backfill never claims the last 24 hours, and an API answer with no rows claims nothing.

- Daily counts for a missing day are `null` and show as "tidak ada data", never as 0.
- A complete day with no detections is a true 0.
- Every window reports how many of its days are complete, partial or missing. The site shows that note next to the numbers.

## 6. Detection categories

| Category | Rule | Public label (draft Indonesian) |
|---|---|---|
| `volcano` | FIRMS `type == 1` (archive), or inside the volcano mask | Gunung api |
| `static_suspect` | FIRMS `type == 2` (archive), or inside the static mask | Dugaan sumber panas tetap/industri |
| `other` | everything else | Titik panas lain (mungkin kebakaran vegetasi/lahan, belum dikonfirmasi) |

Masks are built from the 2023–2025 S-NPP archive on a 0.005° grid (about 550 m):

- Static mask: cells whose 3×3 neighbourhood has detections in at least 7 distinct calendar months and at least 2 distinct years (recurrence rule), plus the neighbourhood of every archive detection with `type == 2`. Vegetation fires in this region cluster in the dry season (roughly July–November). A place that is hot in seven or more calendar months, across more than one year, behaves like a fixed heat source: a smelter, a gas flare, a mill boiler.
- Volcano mask: the neighbourhood of every archive detection with `type == 1`.

Flagged detections stay in every "all detections" total and are shown as their own count. Static-suspect sites (grouped flagged archive detections) are drawn on the map, with the sites in the Morowali and Banggai districts listed for review.

## 7. Architecture

```
            ┌──────────── build_masks (occasional, local) ────────────┐
archive 2023–2025 ─▶ masks.json, static_sites.geojson                  │
ADM1/ADM2 ─────────▶ data/boundaries/*.geojson (11 provinces, districts)│
                     data/public/provinces.geojson, districts geojson   │
            └──────────────────────────────────────────────────────────┘
            ┌──────────── refresh (every 6 h, GitHub Actions) ─────────┐
7-day feeds ×3 ─┐                                                       │
API backfill ───┼▶ assign province/district ─▶ categorize (masks)       │
(optional)      │      ─▶ store: data/live/detections/YYYY-MM.csv       │
                │      ─▶ coverage.json, now.json, focus_detections   │
                │         .geojson, status.json                         │
            └──────────────────────────────────────────────────────────┘
build_site: site/ + data/public/ + data/live/ ─▶ _site/ (+ ringkasan.html, ringkasan.pdf)
```

- `data/public/` and `data/boundaries/` are committed on `main`. They change only when masks or boundaries are rebuilt.
- `data/live/` changes on every refresh. It is gitignored on `main`. In CI it is restored from, and saved back to, an orphan `data-store` branch that is force-pushed as a single commit, so the repository history does not grow every six hours.

Repository layout:

```
config/params.toml   sensors, provinces, URLs, thresholds, offsets
src/sulteng/         library code, one module per responsibility
scripts/             build_masks.py, refresh.py, build_site.py
data/boundaries/     11-province and district polygons for assignment (committed)
data/public/         masks and map layers (committed)
data/live/           rolling store and summaries (data-store branch)
site/                static HTML/CSS/JS
reports/brief/       brief template
tests/               pytest, synthetic data, no network
.github/workflows/   ci.yml, publish.yml
```

### Modules (`src/sulteng/`)

| Module | Responsibility |
|---|---|
| `config.py` | Load and validate `params.toml` into frozen dataclasses |
| `fetch.py` | Download with timeout and retries, atomic write, SHA-256; error messages use a redacted label so the API key never appears |
| `firms.py` | Parse archive and NRT CSVs into one schema (sensor, coordinates, UTC time, WITA date, confidence `l/n/h`, FRP, `type`); reject non-FIRMS bodies |
| `boundaries.py` | Load the 11 provinces from ADM1, map English names to Indonesian, compute land area (EPSG:6933); districts from ADM2; simplified copies for the web |
| `assign.py` | Keep detections inside the 11 provinces; district is the containing or nearest district of the same province |
| `masks.py` | Recurrence statistics, static and volcano masks, categorization, static-site grouping, JSON round trip |
| `store.py` | Combine, deduplicate, retain the two months, save one CSV per month |
| `coverage.py` | Interval merging, per-day status, backfill date ranges |
| `summary.py` | Window definitions, per-window counts per province and district, densities, daily series with `null` for missing days |
| `refresh.py` | One refresh run: feeds, optional backfill, store, coverage, summary, status; keeps the last good outputs when everything fails |
| `brief.py` | Fill the Indonesian brief template from `now.json` |
| `publish.py` | JSON/GeoJSON writing: atomic, numpy-safe, rejects NaN |

## 8. Error handling

- One sensor fails: the run continues with the others. `status.json` says `partial` and names the sensor. Coverage reflects the gap.
- All sources fail: `status.json` says `update_failed` with the time of the attempt and of the last success. All other live outputs are left as they were, and the site says the data may be old.
- A body that is not a FIRMS CSV (HTML maintenance page, "Invalid MAP_KEY") counts as a failure for that source.
- No detections in a window with complete coverage: the site says "Tidak ada deteksi yang dilaporkan dalam periode ini".

## 9. Public site

- Indonesian, static, no build tools. Leaflet 1.9.4 (unpkg, with subresource integrity), OpenStreetMap tiles, charts drawn with plain DOM/SVG.
- One window control (24 jam, 7 hari, bulan ini, bulan lalu) drives every section below it:
  1. Sulteng numbers: other, static suspect, volcano, each shown separately, with the coverage note.
  2. Map: detections in the window, static-suspect sites, district outlines.
  3. District table.
  4. 11-province comparison for the same window: detections per 1,000 km² of land, with the static-suspect share.
- Daily chart for last month and this month, with missing days drawn as gaps.
- Status bar: last refresh (WITA), per-sensor status, draft label. Then sections for how to read the data and what it cannot show, sources with dates, and downloads.
- No ranking language. Provinces are sorted by value, and the value is shown.

## 10. Brief

`reports/brief/ringkasan.html.tmpl` is filled from `now.json` by `brief.py`. It covers last month (complete or with its coverage stated) and this month to date. `build_site.py` writes `ringkasan.html` and prints `ringkasan.pdf` with headless Chrome when Chrome is available. GitHub's Ubuntu runners include it. The brief does not claim Sulteng is more neglected than other provinces.

## 11. Testing

pytest on synthetic data, no network: CSV parsing and rejection; UTC→WITA date crossing midnight; province and district assignment; recurrence rule (year-round source flagged, dry-season fires not, pooling across cell edges and across the equator); category precedence; store deduplication and month pruning; coverage day status (complete, partial, missing, multi-sensor); window boundaries, including January; `null` for missing days and 0 for complete days; refresh outcomes (ok, partial, update_failed, HTML body, backfill ranges, key redaction); JSON NaN rejection; brief rendering and escaping.

End-to-end: build masks from the real archive, run a real refresh, confirm that category counts add up to totals, and that a static site exists in Morowali. Render the site in headless Chrome and look at it.

## 12. Open items for humans

- A free FIRMS `MAP_KEY` (https://firms.modaps.eosdis.nasa.gov/api/map_key/), stored as the `FIRMS_MAP_KEY` secret, to backfill last month.
- Governance agreement (plan §3); NGO review of all Indonesian wording; creating the GitHub repository and enabling Pages.
