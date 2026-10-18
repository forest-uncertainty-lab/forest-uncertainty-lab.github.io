# SP1: G0 data checks and R1 public evidence — design

Date: 2026-10-18
Source brief: `01_Simple_Project_Plan.docx` (the project plan; referred to below as "the plan")

## 1. Understanding

What the plan says:

- Purpose: help people see reliable evidence of forest and land fires in Central Sulawesi (Sulawesi Tengah, "Sulteng") and, separately, study how to choose which uncertain cases to check.
- R1 (public evidence) comes first. R2 (decision study) must not be built at R1's expense.
- Non-negotiable rules: no hotspot is called a confirmed forest fire; missing data is never shown as zero; suspected industrial heat is counted separately and never quietly removed; province comparisons use the same product, years and denominator for all 11 provinces; no paid database, backend, API, domain or hosted model.

Assumptions added for this spec (correct them if wrong):

- A1. The person running this session wants SP1 executed without pausing for approvals. The plan is treated as the approved brief.
- A2. Nothing is pushed to GitHub or published. The repository stays local until a human creates the organization and repository.
- A3. Indonesian text written here is a draft. The plan requires NGO review of public wording, so the site and the brief carry a visible draft label until a reviewer clears them.
- A4. The governance agreement in plan §3 (ownership, credit, data sharing, correction process) is a human task and is not blocked on by code work.

## 2. Decomposition

The plan covers 116–203 volunteer hours. It splits into three sub-projects with separate spec → plan → build cycles:

| Sub-project | Scope | Why separate |
|---|---|---|
| **SP1 (this spec)** | Repository foundation; G0-01 fair comparison; G0-02 static/industrial heat flags; G0-04 archive completeness 2013–2025; R1 pipeline, public site, Indonesian brief draft; case candidates for the NGO to review | Needs only FIRMS and geoBoundaries, both downloadable without credentials (checked 2026-10-18) |
| SP2 | G0-03 burned-area matching (MCD64A1 C6.1) and the 30-case image-check pilot; final 3–5 case stories | MCD64A1 needs a NASA Earthdata login; image interpretation needs a human |
| SP3 | R2 decision study (B0, B1, B1+, B2, B3), G0-05 power check, G0 amendment (pre-registration) | Depends on SP2 labels and the frozen G0 amendment |

## 3. SP1 scope

In scope:

1. Reproducible download of FIRMS VIIRS S-NPP yearly country archives for Indonesia (2013–2025) and geoBoundaries ADM1/ADM2 boundaries, with a manifest of URLs, retrieval times, sizes and SHA-256 hashes.
2. G0-04: per-year archive completeness report for 2013–2025.
3. G0-02: static/industrial heat flagging, with a threshold sensitivity table and a focused list of flagged sites near Morowali and Banggai.
4. G0-01: 11-province comparison for 2023–2025 on one basis, with all detections and flagged categories shown separately.
5. Freshness layer from the FIRMS 7-day near-real-time feed, with explicit `ok`, `no detections` and `update failed` states.
6. Static public site (Indonesian, mobile-friendly): map, trend chart, comparison, separate counts, sources and dates, limits, brief download.
7. Indonesian evidence brief (1–2 pages) rendered from pipeline numbers to PDF, labelled draft.
8. Case candidates for Sulteng: a generated list of the largest non-flagged detection groups with imagery-browser links, for the NGO reviewer. These are not published as stories.
9. A G0 results note recording what G0-01, G0-02 and G0-04 showed, and that G0-03 and G0-05 are not yet run.
10. GitHub Actions workflows for tests, the daily freshness refresh, and Pages deployment. They are written but cannot be run until the repository exists on GitHub.

Out of scope for SP1: MCD64A1, Sentinel-2/Landsat image processing, any model, R2 policies, forest-area denominators, news/funding/response "neglect" measures, the stakeholder list (kept privately by the outreach lead, not in git).

## 4. Fixed choices

| Choice | Value | Reason |
|---|---|---|
| Sensor/product | VIIRS S-NPP 375 m, FIRMS yearly country archive, standard processing (version `2`) | Only VIIRS record that reaches back to 2013; one sensor for all provinces and years |
| Provinces | Kalimantan Barat, Tengah, Selatan, Timur, Utara; Sulawesi Utara, Gorontalo, Sulawesi Tengah, Sulawesi Barat, Sulawesi Selatan, Sulawesi Tenggara | Plan §5 |
| Public comparison years | 2023, 2024, 2025 (complete calendar years) | Plan §5; 2025 archive checked: 12 months, all version `2` |
| Research archive years | 2013–2025, subject to G0-04 | Plan §5 |
| Denominator | Land area per province, from geoBoundaries gbOpen IDN ADM1 (OSM, 2017) polygons, computed in an equal-area projection (EPSG:6933) | Plan allows land area; forest area needs another dataset (later) |
| Confidence levels | All levels counted; low/nominal/high breakdown kept in the data | Nothing removed silently; the breakdown lets readers apply their own filter |
| Districts | geoBoundaries gbOpen IDN ADM2 (2020) for district attribution | Needed for Morowali and Banggai review and Sulteng district table |

Each comparison output carries a `basis` object (sensor, product version, years, denominator source, confidence rule) and a short `basis_id` hash of it. If any element changes, the `basis_id` changes and the site shows the new label. Values computed on different bases are never mixed in one chart.

## 5. Detection categories

Every detection inside the 11 provinces gets exactly one category. Precedence runs top to bottom:

| Category | Rule | Public label (draft Indonesian) |
|---|---|---|
| `volcano` | FIRMS `type == 1` | Gunung api aktif |
| `offshore` | FIRMS `type == 3` | Lepas pantai |
| `static_suspect` | FIRMS `type == 2`, **or** the recurrence rule below | Dugaan sumber panas tetap/industri |
| `other` | everything else | Titik panas lain (mungkin kebakaran vegetasi/lahan, belum dikonfirmasi) |

No category says "forest fire". `other` is the closest the data gets, and its label says it is unconfirmed.

Recurrence rule (G0-02), applied to the full archive window used for the comparison (2023–2025):

- Snap each detection to a 0.005° grid cell (about 550 m).
- For each cell, pool detections in the cell and its 8 neighbours (about 1.65 km window). This absorbs VIIRS geolocation jitter.
- A cell is a static suspect if its pooled detections fall in at least `min_calendar_months` distinct calendar months (default 7 of 12) **and** at least `min_years` distinct years (default 2).
- Reason: vegetation and land-clearing fires in this region cluster in the dry season (roughly July–November). A source that is hot in seven or more different calendar months across more than one year is behaving like a fixed heat source.

The thresholds live in `config/params.toml`. The G0-02 report shows how the static-suspect counts per province change across a small grid of thresholds (calendar months 5–9, years 1–3). It also lists flagged sites within 30 km of Morowali (IMIP, Bahodopi) and Banggai (Donggi-Senoro LNG, Batui) district centroids for human review. Flagged detections stay in every "all detections" total.

The near-real-time feed has no `type` column. Recent detections are flagged only if they fall in a static-suspect neighbourhood derived from the archive. The site says this flag is based on historical recurrence.

## 6. Missing versus zero

- A calendar month is a **national data gap** if the Indonesia archive has zero detections in that month. Indonesia always has some detections, so zero means missing data. A province-month inside a gap month is `null`, never `0`.
- A day with zero national detections is listed in the G0-04 report as a possible gap day. It does not by itself null out a month.
- A province-month with national data present and no detections in that province is a true `0` ("no detections reported").
- On the site, `null` renders as a visible gap in the trend line with a "data tidak tersedia" note, never as a zero.

## 7. Architecture and data flow

```
FIRMS yearly CSVs ─┐
geoBoundaries ADM1 ┼─ fetch ─▶ data/raw/ (gitignored) + data/raw/manifest.json
geoBoundaries ADM2 ┘                      │
                                          ▼
                       load + validate schema ─▶ assign province/district (spatial join)
                                          │
                      ┌───────────────────┼─────────────────────┐
                      ▼                   ▼                     ▼
              archive check (G0-04)  static flags (G0-02)   comparison + monthly (G0-01)
                      │                   │                     │
                      └──────────────▶ data/public/*.json|geojson ◀── recent (NRT 7-day)
                                          │
                       brief renderer (pandoc + xelatex) ─▶ data/public/ringkasan-bukti.pdf
                                          │
                      build_site: site/ + data/public/ ─▶ _site/ (gitignored, deployed to Pages)
```

Repository layout (plan §10, with one adjustment: library code sits in a package so it can be tested):

```
config/params.toml        thresholds, years, province list, URLs
src/sulteng/              library code (one module per responsibility)
scripts/                  thin command-line entry points
data/raw/                 downloads (gitignored)
data/public/              safe-to-share outputs (committed)
site/                     HTML, CSS, JS for GitHub Pages
reports/                  brief template, G0 notes, case candidates
tests/                    pytest, synthetic fixtures, no network
.github/workflows/        ci.yml, refresh.yml
```

R2 decision methods will go in `src/sulteng/policies/` (plan said `/src/policies`).

### Modules (`src/sulteng/`)

| Module | Does | Interface |
|---|---|---|
| `config.py` | Load and validate `config/params.toml` | `load_params(path) -> Params` (frozen dataclass) |
| `fetch.py` | Download with timeout, write via temp file + atomic rename, record manifest entry | `download(url, dest) -> ManifestEntry`; raises `FetchError` |
| `firms.py` | Read archive and NRT CSVs into a typed DataFrame; validate required columns; normalise NRT confidence words to `l/n/h` | `read_archive(path)`, `read_nrt(path)`; raises `SchemaError` |
| `boundaries.py` | Load ADM1/ADM2, keep the 11 provinces, compute land area in EPSG:6933, export simplified web GeoJSON | `load_provinces(path, names)`, `load_districts(path, provinces)` |
| `assign.py` | Spatial join detections to province and district; report counts outside all provinces | `assign(detections, provinces, districts) -> DataFrame` |
| `static_sources.py` | Recurrence rule, category assignment, sensitivity grid, site list | `flag_static(df, params) -> (df_with_category, cells)` |
| `completeness.py` | G0-04 per-year schema/version/month/day checks; gap months | `check_year(df, year) -> YearReport` |
| `compare.py` | Per province × year and province × month counts by category, densities, `basis`/`basis_id` | `comparison(df, provinces, params)`, `monthly(df, gaps, params)` |
| `recent.py` | Build the freshness layer and `status.json`; keep last good output on failure | `update_recent(params, out_dir, now) -> Status` |
| `publish.py` | Write JSON/GeoJSON with stable key order and rounded floats | `write_json(obj, path)` |

### Public outputs (`data/public/`)

| File | Content |
|---|---|
| `provinces.geojson` | 11 provinces, simplified, with `name`, `island`, `area_km2` |
| `comparison.json` | `basis`, `basis_id`, per province × year counts by category and confidence, densities per 1,000 km², 3-year totals |
| `monthly.json` | per province × month counts by category for the comparison years (2023–2025); `null` in national gap months |
| `static_sites.geojson` | flagged cell neighbourhoods merged into sites: centroid, detection count, calendar months active, years active, district, FIRMS type-2 share |
| `sulteng_districts.json` | Sulteng district × year counts by category |
| `archive_check.json` | G0-04 per-year results |
| `recent.geojson`, `status.json` | 7-day NRT points in the 11 provinces; status, window, last attempt, last success |
| `manifest.json` | input URLs, hashes, retrieval times, git commit, parameter values |
| `ringkasan-bukti.pdf` | brief draft |

## 8. Error handling

- Downloads: 120 s timeout, two retries, temp file then rename. A failure raises `FetchError` with the URL and the cause. Archive steps stop the run. The recent step catches it, writes `status: "update_failed"` with `last_attempt`, keeps the previous `recent.geojson` and `last_success`, and exits 0 so the site still deploys with the old data clearly marked.
- Schema: a missing required column raises `SchemaError` naming the file and column. A partial file is never processed silently.
- Spatial join: detections outside all 34 provinces are counted and reported, not dropped silently.
- Zero recent detections: `status: "ok"`, `count: 0`; the site says "Tidak ada deteksi yang dilaporkan dalam periode ini."

## 9. Public site

- Indonesian, static, no build tools. Leaflet 1.9.4 from unpkg with subresource integrity; OpenStreetMap tiles with attribution; charts drawn as inline SVG by a small script (no chart library).
- Sections: status bar (data date, freshness status, draft label); comparison of the 11 provinces (density, all vs static suspect shown side by side, basis label); monthly trend (Sulteng highlighted against the other provinces, gaps visible); map (recent detections, static-suspect sites, province outlines); what the data can and cannot say; sources with dates; brief download.
- No ranking language ("peringkat", "terburuk"). Provinces are sorted by value and the values are shown.
- Visual design is settled during implementation with the frontend-design and no-ai-slop-web guidance.

## 10. Brief

`reports/brief/ringkasan-bukti.md.tmpl` holds the text with `$placeholders`. `scripts/render_brief.py` fills them from `comparison.json` and `manifest.json`, then pandoc + xelatex render the PDF. Every number in the brief comes from a public output file. It does not claim Sulteng is more neglected than Kalimantan. If the comparison does not support a strong statement, it says that fire activity exists and warrants checking (plan §6).

## 11. Testing

pytest on small synthetic inputs, no network:

- schema validation rejects a CSV missing `acq_date` and accepts the archive and NRT column sets;
- spatial join assigns points to the right synthetic polygon and counts points outside;
- recurrence rule flags a cell active in 9 calendar months over 2 years, and does not flag a cell active July–October over 3 years;
- category precedence (`type` 1 beats the recurrence rule);
- national gap month produces `null` province-months; a non-gap month with no detections in a province produces `0`;
- `basis_id` changes when years or denominator change;
- recent update: failure keeps the previous file and writes `update_failed`; empty window writes `ok` with `count: 0`;
- public JSON contains no NaN.

End-to-end check: run the full pipeline on real data once, then confirm that totals reconcile (sum of categories = all detections per province-year) and that a flagged site exists near Morowali.

## 12. Open items for humans

- Governance agreement (plan §3).
- NGO review of all Indonesian wording before anything is public.
- Creating the GitHub organization/repository, adding Pages, deciding when to make it public.
- SP2 needs an Earthdata account for MCD64A1.
