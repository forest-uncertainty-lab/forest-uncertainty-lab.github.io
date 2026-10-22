# Haze, Explained Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tabbed public site (Haze, Fire history, Sulawesi Tengah) refreshed every six hours, whose fire history covers all 34 Indonesian provinces from 2013 to the latest complete day and whose numbers carry their statistical method and uncertainty.

**Architecture:** Python modules in `src/sulteng/` build three JSON products (`history_archive.json` once from the yearly archive; `history.json` and `haze.json` on every refresh from the feeds, the FIRMS API, Open-Meteo and NEA). The static site in `site/` reads them; the Haze tab also refreshes its air numbers live from NEA and Open-Meteo in the browser. The existing Sulawesi Tengah monitor moves unchanged to `site/sulawesi-tengah/`.

**Tech Stack:** Python 3.11+, pandas, geopandas, shapely, numpy (already installed through pandas), pytest; vanilla HTML/CSS/JS; GitHub Actions and Pages. No new dependency.

**Spec:** `docs/superpowers/specs/2026-10-22-haze-explained-design.md`. The visual reference is the approved mockup, kept as `docs/superpowers/specs/2026-10-22-haze-explained-mockup.html` (copied in Task 12).

## Global Constraints

- Fire history counts Suomi NPP only. Detections count when inside one of the 34 geoBoundaries provinces, outside the volcano and static mask cells, and (where a `type` column exists) not of FIRMS type 1, 2 or 3.
- Weeks: local date in UTC+8; week index `(day_of_year - 1) // 7`, capped at 51.
- A UTC day with no Suomi NPP row anywhere in the area is a gap. It is filled from NOAA-20 detections of the same UTC day, each weighted by that year's Suomi NPP to NOAA-20 ratio; if NOAA-20 has no row that day either, it stays missing. Missing is `null`, never 0.
- Intervals are 80% (10th, 50th, 90th percentiles). Random draws use a fixed seed (0) so outputs are reproducible.
- Every page string exists in English and Indonesian (British English; no-ai-slop rules). The footer reads "Made by" / "Dibuat oleh" followed by `<a href="https://vickyfeliren.com/">Vicky Feliren</a>`. No Claude or Anthropic attribution in code, pages or commits.
- Estimates (model, nowcast, outlook, filled days) are always labelled as such and drawn dashed or hatched.
- The key is read only from the `FIRMS_MAP_KEY` environment variable and never printed; request labels use `key="***"`, as `refresh.py` does today.
- `make test` stays green after every task.

## Review Focus

1. **The FIRMS API answers a day with a header and no rows.** That day is a gap, recorded as fetched-empty and not requested again on every run. Pinned in Task 7 (`test_empty_api_day_is_a_gap_not_refetched`).
2. **New Year.** On 3 January the running week is week 0 and the previous year is not yet in the archive; the store must keep and show it. Pinned in Task 8 (`test_year_after_archive_stays_in_store_and_page`).
3. **A province with no history** (DKI Jakarta has weeks with zero in every year): ratio and outlook are `None`, not division errors. Pinned in Task 4 (`test_zero_history_gives_no_ratio`) and Task 8.
4. **Open-Meteo returns `null` for some hours or levels.** The trajectory stops at the gap instead of moving on NaN. Pinned in Task 9 (`test_trajectory_stops_at_missing_wind`).
5. **NEA omits a region for an hour.** The band uses the regions present; an hour with none is skipped. Pinned in Task 9 (`test_nea_band_ignores_missing_regions`).

---

### Task 1: Indonesia configuration

**Files:**
- Create: `config/indonesia.toml`, `src/sulteng/indonesia.py`
- Modify: `config/params.toml` (`[sources]`)
- Test: `tests/test_indonesia.py`

**Interfaces:**
- Produces: `Region(source_name: str, name: str, name_en: str, island: str, island_id: str)` (frozen dataclass); `City(key: str, name: str, lat: float, lon: float, utc_offset: int, tz: str, country: str)`; `Indonesia(regions: tuple[Region, ...], cities: tuple[City, ...], archive_first: int, archive_last: int, area_bbox: str, map_bbox: tuple[float, float, float, float])`; `load_indonesia(path=ROOT/"config"/"indonesia.toml") -> Indonesia`; `Indonesia.provinces() -> tuple[Province, ...]` (for `load_provinces`); `Params.availability_url: str`.
- `indonesia.toml` holds the 34 provinces in island order with the names in `fire_history.py` from the mockup (`ISLANDS`, `ID_NAMES`, `ISLAND_ID`), the nine cities with offsets SGT 8, MYT 8, WIB 7 (Jakarta, Pekanbaru, Jambi, Palembang, Pontianak, Palangka Raya), WITA 8 (Palu), `archive_first = 2013`, `archive_last = 2025`, `area_bbox = "94.5,-11.5,141.5,6.5"`, `map_bbox = [95.0, -11.0, 141.0, 8.0]`. `params.toml` gains `availability_url = "https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{key}/ALL"`.

- [ ] **Step 1: Write the failing tests**

```python
def test_indonesia_has_34_provinces_in_six_islands():
    ind = load_indonesia()
    assert len(ind.regions) == 34 and len({r.source_name for r in ind.regions}) == 34
    assert [r.island for r in ind.regions][:1] == ["Sumatra"] and ind.regions[-1].source_name == "Papua"
    assert {r.island for r in ind.regions} == {"Sumatra", "Java", "Bali and Nusa Tenggara", "Kalimantan", "Sulawesi", "Maluku and Papua"}
    assert next(r for r in ind.regions if r.source_name == "Central Sulawesi").name == "Sulawesi Tengah"

def test_regions_match_geoboundaries():
    path = ROOT / "data" / "raw" / "adm1.geojson"
    if not path.exists():
        pytest.skip("geoBoundaries ADM1 not downloaded")
    names = {f["properties"]["shapeName"] for f in json.loads(path.read_text())["features"]}
    assert {r.source_name for r in load_indonesia().regions} == names

def test_cities_carry_their_clock():
    c = {c.key: c for c in load_indonesia().cities}
    assert (c["singapore"].tz, c["palangka-raya"].tz, c["palu"].tz) == ("SGT", "WIB", "WITA")
    assert c["palu"].utc_offset == 8 and c["jakarta"].utc_offset == 7

def test_rejects_unknown_island(tmp_path): ...  # an island outside the six raises ValueError naming it
```

- [ ] **Step 2: Run them to see them fail** — `uv run pytest tests/test_indonesia.py -q` → `ModuleNotFoundError: sulteng.indonesia`.
- [ ] **Step 3: Write `config/indonesia.toml`, `src/sulteng/indonesia.py` and the `availability_url` field** (validated like `archive_url`: must contain `{key}`).
- [ ] **Step 4: Run** `make test` → all pass.
- [ ] **Step 5: Commit** — `git commit -m "Add the 34 provinces and nine haze cities as configuration"`

---

### Task 2: Shared download helpers

**Files:**
- Modify: `src/sulteng/fetch.py`, `scripts/g0_checks.py`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Produces: `fetch_yearly(url_template: str, years, archive_dir: Path, *, fetch=download) -> dict[int, dict]` (moved from `g0_checks.fetch_years`, same behaviour); `get_json(url: str, *, label: str | None = None, timeout: float = 60, retries: int = 2) -> object` (same retry and 4xx rules as `download`, raises `FetchError(label…)`).

- [ ] **Step 1: Failing tests** — `test_fetch_yearly_downloads_only_missing_years` (fake `fetch` records calls; a year already in the manifest is not fetched) and `test_get_json_parses_and_hides_label_url` (a local `http.server` fixture serving `{"a": 1}` and a 404 path; the error text contains the label, not the URL).
- [ ] **Step 2: Run** → fail on import.
- [ ] **Step 3: Implement** both in `fetch.py`; `g0_checks.py` imports `fetch_yearly`.
- [ ] **Step 4: Run** `make test`.
- [ ] **Step 5: Commit** — `"Share the yearly-archive download and add a JSON fetch"`

---

### Task 3: Masks and outlines for all of Indonesia

**Files:**
- Modify: `scripts/build_masks.py`, `README.md` (one line under "How it is put together")
- Regenerated: `data/public/masks.json`, `data/public/static_sites.geojson`, `data/public/static_site_ids.csv`, `data/public/manifest.json`, `reports/static_review.md`; new `data/boundaries/indonesia.geojson`

**Interfaces:**
- Consumes: `load_indonesia().provinces()`.
- Produces: masks built from archive detections inside all 34 provinces (same rule and `params.masks`); `data/boundaries/indonesia.geojson` (34 provinces, columns `name`, `island`, `area_km2`, written with `write_layer(..., tolerance=0.002, grid=0.0001, precision=4)`). The 11-province layers stay as they are.

- [ ] **Step 1: Change `build_masks.py`** so masks and sites come from `assign(archive, all_provinces, districts)` (districts stay the 11-province ones; others get `district = None`), and it writes `indonesia.geojson`.
- [ ] **Step 2: Run** `make masks`. Expected: static cells about 4,800, volcano cells about 540; `site IDs:` line shows the 168 old IDs still active plus new ones; `git diff data/public/static_sites.geojson` keeps every existing `site_id` at its coordinates.
- [ ] **Step 3: Check the Sulawesi Tengah numbers do not move** — `make refresh` (it reads the new masks) and compare `now.json` category counts for the 11 provinces with the previous run: differences only from cells on borders, if any.
- [ ] **Step 4: Run** `make test`.
- [ ] **Step 5: Commit** — `"Build the masks over all 34 provinces"`

---

### Task 4: Statistics

**Files:**
- Create: `src/sulteng/stats.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- Produces:
  - `jeffreys_vs_history(count: float, past: Sequence[float], *, draws=20000, seed=0) -> dict` with keys `ratio` (`(q10, q50, q90)` of λ / median(past), or `None` when the median is 0), `p_above_max` (P(λ > max(past)), λ ~ Gamma(count + 0.5, 1)), `rank` (1 + number of past values above `count`), `years` (len(past) + 1).
  - `nowcast(observed: float, recent_daily: Sequence[float], days_left: int, *, draws=4000, seed=0) -> tuple[float, float, float] | None` — Bayesian bootstrap: weights ~ Dirichlet(1, …, 1) over `recent_daily`, rate = weights · recent, remainder ~ Poisson(rate × days_left), total = observed + remainder; `None` when `recent_daily` is empty; `(observed,)*3` when `days_left == 0`.
  - `analog_outlook(to_date: float, past_weeks: Sequence[Sequence[float]], from_week: int) -> dict | None` — for each past year y with `sum(past_weeks[y][:from_week]) > 0`: scale `s = to_date / that sum`; `weekly[w] = s × past_weeks[y][w]` for `w ≥ from_week`; `year_end = to_date + Σ weekly`. Returns `{"year_end": (q10, q50, q90), "p_record": share of analogs with year_end > max(sum(past year)), "weekly": [(q10, q50, q90) for w in from_week..51], "analogs": n}`; `None` when no analog qualifies.

- [ ] **Step 1: Failing tests**

```python
def test_jeffreys_interval_narrows_with_count():
    small, big = jeffreys_vs_history(20, [10] * 13), jeffreys_vs_history(2000, [1000] * 13)
    assert small["ratio"][0] < 1.5 < small["ratio"][2] and big["ratio"][0] > 1.9 and big["ratio"][2] < 2.1
def test_jeffreys_probability_above_record():
    r = jeffreys_vs_history(120, [10, 20, 100])
    assert 0.9 < r["p_above_max"] < 1 and r["rank"] == 1 and r["years"] == 4
def test_zero_history_gives_no_ratio():
    assert jeffreys_vs_history(5, [0, 0, 0])["ratio"] is None
def test_nowcast_brackets_a_steady_rate():
    q = nowcast(30, [10] * 14, 4)
    assert q[0] <= 70 <= q[2] and q[1] == pytest.approx(70, abs=5)
def test_nowcast_without_recent_days_is_none_and_full_week_is_exact():
    assert nowcast(5, [], 3) is None and nowcast(42, [9] * 14, 0) == (42, 42, 42)
def test_analog_outlook_is_exact_on_proportional_history():
    past = [[1] * 52, [2] * 52, [3] * 52]   # every year has the same shape
    out = analog_outlook(10 * 2, past, 10)  # this year: 2 a week for 10 weeks
    assert out["year_end"] == pytest.approx((104, 104, 104)) and out["weekly"][0] == pytest.approx((2, 2, 2))
    assert out["p_record"] == 0 and out["analogs"] == 3
def test_analog_outlook_skips_years_without_detections_so_far():
    assert analog_outlook(5, [[0] * 52, [0] * 52], 10) is None
```

- [ ] **Step 2: Run** → fail on import.
- [ ] **Step 3: Implement** with `numpy.random.default_rng(seed)` and `numpy.percentile(..., [10, 50, 90])`.
- [ ] **Step 4: Run** `make test`.
- [ ] **Step 5: Commit** — `"Add the statistics: Jeffreys rates, Bayesian-bootstrap nowcast, analog-year outlook"`

---

### Task 5: Fire-history core

**Files:**
- Create: `src/sulteng/firehistory.py`
- Test: `tests/test_firehistory.py`

**Interfaces:**
- Consumes: `masks.cell_index`, `Masks`, `assign` (via a provinces GeoDataFrame with `name`).
- Produces:
  - `local_week(local_dates: pd.Series) -> tuple[np.ndarray, np.ndarray]` (year, week index 0–51).
  - `gap_days(utc_dates_seen: Iterable[str], first: date, last: date) -> list[str]` (UTC days in range with no row).
  - `ratio(snpp_daily: pd.Series, n20_daily: pd.Series) -> float | None` (sum over UTC days both have rows; `None` under 30 shared days).
  - `with_gap_fill(snpp: pd.DataFrame, n20: pd.DataFrame, gaps: Collection[str], r: float | None) -> pd.DataFrame` — `snpp` rows with `weight = 1` plus NOAA-20 rows whose `acq_date` is in `gaps`, `weight = r`, `filled = True` (none when `r is None`).
  - `keep_fires(df, provinces: GeoDataFrame, masks: Masks) -> pd.DataFrame` — rows kept by the Global Constraints rule, with a `province` column.
  - `weekly(df_kept, year: int, province_names: Sequence[str]) -> dict` with `count` and `frp` arrays shaped (provinces, 52) of weighted sums, and `filled_days[52]`.

- [ ] **Step 1: Failing tests** — `test_local_week_crosses_midnight_and_caps_week_52` (`2023-12-31 17:30 UTC` is week 0 of 2024; 31 December is week 51); `test_gap_days_lists_utc_days_without_rows`; `test_gap_fill_weights_noaa20_rows_on_gap_days_only` (two NOAA-20 rows, one on a gap day: only that one is added, weight `r`, `filled`); `test_gap_fill_leaves_double_gaps_missing` (no NOAA-20 rows that day → nothing added); `test_keep_fires_drops_masked_typed_and_outside` (one row each: masked cell, type 2, outside every province, kept); `test_weekly_sums_weights` (weights 1 and 0.98 in the same week give 1.98).
- [ ] **Step 2: Run** → fail.
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run** `make test`.
- [ ] **Step 5: Commit** — `"Add the fire-history core: weeks, gaps, NOAA-20 gap filling, kept detections"`

---

### Task 6: History archive

**Files:**
- Create: `scripts/build_history.py`
- Modify: `Makefile` (`history` target, `ARCHIVE_DIR` reused), `README.md` (one line under "Running it")
- Generated and committed: `data/public/history_archive.json`

**Interfaces:**
- Consumes: Tasks 1, 2, 5; `read_archive`; masks from `data/public/masks.json`; `data/boundaries/indonesia.geojson`.
- Produces: `history_archive.json` = `{"built_at", "years": [2013..2025], "provinces": [source_name…], "count": [p][y][w], "frp": [p][y][w], "filled_days": [y][w], "missing_days": [y][w], "ratio": {year: r}}`, numbers rounded to 0.01 (counts) and 1 (FRP).

- [ ] **Step 1: Write `build_history.py`**: `fetch_yearly` Suomi NPP 2013–2025 and NOAA-20 (`viirs-jpss1`, `params.noaa20_archive_url`) 2018–2025 into `--archive-dir`; per year: `gap_days` from the Suomi NPP file, `ratio` from `history.daily_rows`-style UTC counts, `with_gap_fill`, `keep_fires`, `weekly`.
- [ ] **Step 2: Run** `make history ARCHIVE_DIR=~/Library/Caches/sulteng-remote-sensing`. Expected: the national totals per year within 0.5% of the mockup's `fire_history2.py` output (2015 ≈ 853,051, 2025 ≈ 78,271) plus the filled days of 2022–2025; `filled_days` sums to the gap days NOAA-20 covered (38 minus days both missed).
- [ ] **Step 3: Commit** — `"Build the weekly fire history archive, 2013 to 2025"`

---

### Task 7: Current-year store and backfill

**Files:**
- Create: `src/sulteng/yearstore.py`
- Test: `tests/test_yearstore.py`

**Interfaces:**
- Consumes: Task 5 (`keep_fires`), `fetch.download`, `get_json`, `read_nrt`.
- Produces:
  - Store file `data/live/history_current.json`: `{"rows": [[sensor, province, local_date, utc_date, count, frp]…], "fetched": {"N": {utc_date: "SP"|"NRT"|"feed"|"empty"}, "N20": {…}}}`, covering every year after `archive_last`.
  - `ingest(store: dict, sensor: str, kept: pd.DataFrame, utc_days: Collection[str], source: str) -> dict` — replaces the rows of `sensor` on `utc_days`, marks each day `source`, or `"empty"` when it has no row in the raw (pre-filter) frame.
  - `feed_days(raw: pd.DataFrame) -> list[str]` — UTC days of a 7-day feed except the first (partial) one.
  - `plan_backfill(store, first: date, last: date, sp_last: date | None, nrt_first: date | None, *, max_requests=30) -> list[tuple[str, str, date, int]]` — `(sensor, source, first_day, days)` with `days ≤ 5`: Suomi NPP days not fetched, or fetched as NRT/feed but now covered by SP; NOAA-20 only on Suomi NPP `"empty"` days; SP where `day ≤ sp_last`, NRT from `nrt_first`.
  - `update_year(store, params, indonesia, provinces, masks, raw_dir, now_utc, *, map_key, fetch=download, get=get_json) -> tuple[dict, dict]` — ingests `feed_N.csv` and `feed_N20.csv` from `raw_dir`, backfills through the area API (label with `key="***"`), returns `(store, status)` with `status = {"backfill": "ok"|"partial"|"no key", "requests": n, "errors": [...]}`.

- [ ] **Step 1: Failing tests** — `test_ingest_replaces_only_the_given_days`; `test_feed_days_drop_the_partial_first_day`; `test_plan_prefers_sp_and_refetches_nrt_days_sp_now_covers`; `test_plan_asks_noaa20_only_for_suomi_gap_days`; `test_plan_caps_requests_per_run`; `test_empty_api_day_is_a_gap_not_refetched` (a fake `fetch` writes a header-only CSV for one day: the day becomes `"empty"`, a second `update_year` does not request it again as SP/NRT); `test_update_year_without_key_reads_feeds_only`.
- [ ] **Step 2: Run** → fail.
- [ ] **Step 3: Implement.** Availability comes from `get(params.availability_url.format(key=map_key))` (CSV text parsed for `VIIRS_SNPP_SP` and `VIIRS_SNPP_NRT`); without a key no request is made.
- [ ] **Step 4: Run** `make test`.
- [ ] **Step 5: Commit** — `"Keep the current year's detections per province and day, backfilled from the FIRMS API"`

---

### Task 8: History page data

**Files:**
- Create: `src/sulteng/historypage.py`
- Test: `tests/test_historypage.py`

**Interfaces:**
- Consumes: Tasks 1, 4, 5, 7; the archive JSON.
- Produces: `build_history_page(archive: dict, store: dict, indonesia: Indonesia, now_utc: datetime) -> dict` written to `data/live/history.json`:
  `{"generated_at", "latest_day", "years", "nrt_from", "rows": [{"key", "level", "en", "id"}], "count": [row][year][week], "frp": …, "filled_days": [year][week], "missing_days": [year][week], "running": {"year", "week", "days_seen"}, "nowcast": {"count": [row] -> [q10,q50,q90], "frp": …}, "outlook": {"count": [row] -> analog_outlook dict | null, "frp": …}, "unusual": {"count": [row] -> jeffreys dict + {"to_date", "usual"}, "frp": …}}`.
  Rows: `total` (Indonesia), then `isl:<island>` and its `prov:<i>` rows, labels in English and Indonesian. Weeks after the latest day are `null`. Current-year gap filling uses `ratio` over the store's shared days, else the last archive year's ratio. Complete local days are those before today in UTC+8; `running.week` is today's week; nowcast uses each row's last 14 complete days and the days left in the week; outlook and unusual use complete weeks before `running.week`.

- [ ] **Step 1: Failing tests** on a small synthetic archive (3 years, 2 provinces) and store: `test_rows_sum_provinces_into_islands_and_indonesia`; `test_future_weeks_are_null_and_running_week_is_nowcast`; `test_gap_day_in_current_year_is_filled_from_noaa20`; `test_unusual_uses_the_same_weeks_each_year`; `test_year_after_archive_stays_in_store_and_page` (archive to 2025, `now = 2027-01-03`: years run to 2027, 2026 complete from the store, running week 0).
- [ ] **Step 2: Run** → fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `make test`.
- [ ] **Step 5: Commit** — `"Assemble the fire-history page data with nowcast, outlook and unusual-level statistics"`

---

### Task 9: Haze data

**Files:**
- Create: `src/sulteng/haze.py`
- Test: `tests/test_haze.py` (fixtures in `tests/fixtures/` for one NEA pm25 day, one PSI, one Open-Meteo air-quality and one forecast response, trimmed)

**Interfaces:**
- Produces:
  - `nea(pm25_days: list[dict], psi: dict) -> dict` — `{"pm25_hourly": [{"time", "lo", "hi", "mean", "regions": {…}}], "psi_time", "psi_24h", "pm25_24h"}`, last 48 hours.
  - `cams(payloads: list[dict], cities) -> dict[city_key, {"time": [...], "pm2_5": [...]}]`.
  - `WindField` (frozen dataclass: `times: np.ndarray` of hours since epoch, `lats`, `lons`, `u: dict[str, np.ndarray]`, `v: dict[str, np.ndarray]` shaped time × lat × lon, m/s) and `wind_field(payloads: list[dict], levels=("925", "850", "700")) -> WindField`.
  - `trajectory(field, level, lat, lon, start_h: float, hours=48, speed=1.0, turn_deg=0.0) -> list[list[float]]` — `[lon, lat, h]` hourly, moving against the bilinearly interpolated wind, stopping at the grid edge or a missing value.
  - `ensemble(field, city, now_h) -> dict[level, list[path]]` — 9 members per level: start offsets 0, 1, 2 h × perturbations (speed 0.9, turn −10°), (1.0, 0°), (1.1, +10°); member 0 is the central path.
  - `share_near(paths, fire_lonlat: np.ndarray, km=50.0) -> float`.
  - `binned_fires(df, cell=0.02) -> list[list[float]]` (`[lon, lat, n]`).
  - `track(store: dict, nea_hourly, cams_sg, now_utc, days=30) -> tuple[dict, dict | None]` — appends hourly pairs, drops older than 30 days, returns stats `{"hours", "ratio": (q10, q50, q90)}` once 24 or more pairs exist.
  - `build_haze(indonesia, fires_kept: pd.DataFrame, now_utc, track_store, *, get=get_json) -> tuple[dict, dict]` — fetches NEA (`https://api-open.data.gov.sg/v2/real-time/api/pm25?date=…` for today and yesterday SGT, and `/psi`), CAMS (`https://air-quality-api.open-meteo.com/v1/air-quality`, `hourly=pm2_5`, `past_days=2`, `forecast_days=3`, `timezone=GMT`), winds (`https://api.open-meteo.com/v1/forecast`, `wind_speed_{lv}hPa,wind_direction_{lv}hPa`, `past_days=2`, `forecast_days=1`, `wind_speed_unit=ms`, 1° grid over `map_bbox`, 100 points per request), and returns `(haze_json, track_store)`.

- [ ] **Step 1: Failing tests** — `test_nea_band_ignores_missing_regions`; `test_cams_maps_payloads_to_cities_in_order`; `test_trajectory_constant_wind_moves_expected_distance` (10 m/s from the east for 2 h → 0.647° east of start, `[lon, lat, h]` shape); `test_trajectory_stops_at_missing_wind`; `test_ensemble_has_nine_members_per_level_with_central_first`; `test_share_near_counts_members_within_50_km`; `test_track_keeps_30_days_and_reports_after_24_hours`; `test_build_haze_with_fake_get` (fake `get` serving the fixtures; output has every city, three levels, and the generated time).
- [ ] **Step 2: Run** → fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `make test`.
- [ ] **Step 5: Commit** — `"Add the haze data: NEA, CAMS, wind ensembles, fires near paths, model track record"`

---

### Task 10: Refresh wiring

**Files:**
- Modify: `scripts/refresh.py`
- Test: `tests/test_refresh.py` (one test for the new step's isolation)

**Interfaces:**
- Consumes: Tasks 7, 8, 9.
- Produces: after `run_refresh`, `scripts/refresh.py` loads `history_current.json` and `haze_track.json`, runs `update_year`, writes `history_current.json` and `history.json`, then `build_haze` (fires from the three feeds, kept by `keep_fires`, last 48 h), writes `haze.json` and `haze_track.json`. Each step is wrapped so its failure is recorded in `data/live/status_extra.json` (`{"history": {...}, "haze": {...}}`) and never stops the others or the Sulawesi Tengah refresh. Function: `refresh_extras(root: Path, now_utc, map_key, *, get=get_json, fetch=download) -> dict` in `src/sulteng/extras.py`.

- [ ] **Step 1: Failing test** — `test_extras_record_a_haze_failure_and_still_write_history` (fake `get` raising `FetchError` for Open-Meteo).
- [ ] **Step 2: Run** → fail.
- [ ] **Step 3: Implement** `extras.py`; `scripts/refresh.py` calls it after `run_refresh`.
- [ ] **Step 4: Run** `make test`, then `make refresh` (real network; the key comes from the env file). Expected: `history.json` with years 2013–2026, `fetched` counts in the store near the 60 requests of the mockup fetch on the first run and a handful after; `haze.json` with nine cities.
- [ ] **Step 5: Commit** — `"Refresh the fire history and the haze snapshot with the near-real-time data"`

---

### Task 11: Move the Sulawesi Tengah monitor

**Files:**
- Move: `site/index.html`, `site/app.js`, `site/styles.css` → `site/sulawesi-tengah/`
- Modify: `site/sulawesi-tengah/app.js` (`DATA = "../data/"`), `site/sulawesi-tengah/index.html` (links to `../ringkasan.pdf`, `../ringkasan.html`, `../data/…`), `src/sulteng/brief.py` only if it links back to the page
- Test: `tests/test_sitebuild.py`

- [ ] **Step 1: Failing test** — `test_build_keeps_the_monitor_under_its_own_path` (`_site/sulawesi-tengah/index.html` exists and references `../data/`; `_site/index.html` is the new shell).
- [ ] **Step 2: Run** → fail.
- [ ] **Step 3: Move and fix paths.**
- [ ] **Step 4: Run** `make test`, `make serve`, open `/sulawesi-tengah/`: the monitor loads its data.
- [ ] **Step 5: Commit** — `"Move the Sulawesi Tengah monitor to its own path"`

---

### Task 12: Shell and Haze tab

**Files:**
- Create: `site/index.html`, `site/haze.css`, `site/shell.js`, `site/haze.js`; copy the mockup to `docs/superpowers/specs/2026-10-22-haze-explained-mockup.html`

**Interfaces:**
- Consumes: `data/haze.json` (Task 9), `data/status_extra.json`.
- Produces: the shell (brand, tablist Haze / Fire history / Sulawesi Tengah link, EN/ID, theme, note, footer with the credit) dispatching `app:change` `{lang, tab, city, year, row}`; `haze.js` ported from the mockup's haze module, reading `haze.json`, drawing every ensemble member thin and the central path bold, the per-height sentence with "N of 9 paths passed within 50 km of fire detections", the Singapore track-record sentence, and a live update of NEA PSI/PM2.5 and the CAMS current value on load (fallback: the snapshot, with its time).

- [ ] **Step 1: Port** from the mockup (`build_explained.py` composition) into the four files, data from `fetch("data/haze.json")`.
- [ ] **Step 2: Render check** — `make site` then headless Chrome screenshots of `#tab=haze` (EN dark, Singapore) and `#tab=haze&lang=id&theme=light&city=palangka-raya`; read them; no overlap, no empty section, numbers match `haze.json`.
- [ ] **Step 3: Run** the no-ai-slop-web scanner on `site/` and fix real hits.
- [ ] **Step 4: Commit** — `"Add the tabbed shell and the Haze tab"`

---

### Task 13: Fire history tab

**Files:**
- Create: `site/fires.js`; Modify: `site/index.html`, `site/haze.css`

**Interfaces:**
- Consumes: `data/history.json` (Task 8).
- Produces: the mockup's fire tab reading `history.json`, plus: running week drawn from `nowcast` (dashed outline, rank on the median, interval in the tooltip); filled-day hatching from `filled_days` and missing from `missing_days`; whole-year bars with the outlook whisker for the current year; the detail chart's dashed nowcast point and shaded outlook band for weeks after the running week; a new "This year by province" dot plot of `unusual.ratio` (log scale, sorted, whisker = 80% interval, tooltip with rank and `p_above_max`, a table view toggle); method texts in both languages covering gap filling, nowcast, outlook and the Jeffreys rate.

- [ ] **Step 1: Port and extend.**
- [ ] **Step 2: Render check** — screenshots of `#tab=fires` (EN dark), `#tab=fires&year=2015&row=prov:20`, and `#tab=fires&lang=id&theme=light`; read them.
- [ ] **Step 3: Validate** the dot-plot colours with `validate_palette.js` if new ones are added.
- [ ] **Step 4: Commit** — `"Add the Fire history tab with nowcast, outlook and province statistics"`

---

### Task 14: Docs and the full check

**Files:**
- Modify: `README.md` (what the site shows, data sources table with Open-Meteo and NEA, running), `docs/backlog.md` (session section; new items: forest share via Earth Engine; OpenAQ sensors; decision replay), `AGENTS.md` only if commands changed

- [ ] **Step 1: Update the docs.**
- [ ] **Step 2: Run** `make test` (all pass), `make refresh`, `make site`, and the headless render of all three tabs.
- [ ] **Step 3: Commit** — `"Document Haze, Explained and update the backlog"`
