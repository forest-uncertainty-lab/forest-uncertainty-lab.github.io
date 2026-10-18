# Backlog

Last updated 2026-10-19. Owners follow the roles in the project plan (§3): **TL** technical lead, **NGO** NGO reviewer, **OL** outreach lead.

## Data sources

Decided on 2026-10-19 from the data-source review the project owner shared. Rule of thumb from that review: add a source only when it answers a question the current data cannot.

| Source | Decision | Role | Notes |
|---|---|---|---|
| NASA FIRMS | In use | Detections from the 7-day feeds every 6 hours; the 2023–2025 yearly archive builds the static-source and volcano masks; the area API backfills last month once a key exists | Limit: 5,000 map-key transactions per 10 minutes (per the review). The first backfill run makes about 30 API requests (about 10 per satellite); later runs make a few at most. |
| Google Earth Engine | SP2 | Check a small sample (about 30) of candidate events against Sentinel-2 and Landsat imagery and the MCD64A1 burned-area product; prepare labels with their uncertainty written down | Needs a verified noncommercial Earth Engine project (per the review, a Community tier of 150 compute-unit hours a month since April 2026). Run it interactively and export the results into this repository. The public site never calls Earth Engine. |
| Copernicus GWIS | Optional, SP3 | Cross-check burned area and fire danger | Its active-fire layer draws on FIRMS, so it cannot independently confirm a FIRMS hotspot. Its coarse burned-area maps miss small fires. |
| Open-Meteo | Later, only if the NGO asks | Smoke and air-quality context (modelled PM2.5 and carbon monoxide) | Modelled values on a grid of about 45 km. They do not show where a fire burned. |
| NIFC Wildland Fire Open Data | Not used | | Covers the United States only. |

**FIRMS fire-type codes.** Per the review, NASA fixed a bug in the historical VIIRS `type` field and reprocessed the files in May 2025. The masks depend on that field (1 = volcano, 2 = static source), so `scripts/build_masks.py` refuses any archive file dated before `archive_min_last_modified` (2025-06-01) in `config/params.toml`. The files used on 2026-10-18 are dated 2025-06-24 (2023 and 2024) and 2026-10-10 (2025). The notice itself is not yet confirmed from the FIRMS site (item 9).

**Order of work**, kept from the review: FIRMS evidence first, then Earth Engine checks on a small sample, then the evidence brief, and only then the uncertainty experiment.

## Action items

### To go live

1. [ ] Register a free FIRMS map key at https://firms.modaps.eosdis.nasa.gov/api/map_key/ and run `FIRMS_MAP_KEY=… make refresh` to fill last month. The backfill has only been tested against fakes. (TL)
2. [ ] Decide whether to merge the `sp1-fire-monitor` branch into `main`. (TL)
3. [ ] Create the GitHub organisation and repository, push, set Pages to deploy from GitHub Actions, add the `FIRMS_MAP_KEY` repository secret, and watch the first `publish` run. Neither workflow has run yet. (TL)
4. [ ] Take a screenshot of the deployed page and add it as the share image (`og:image` in `site/index.html`). (TL)

### Before anything is public

5. [ ] Review all Indonesian wording on the site and in the brief. Once approved, remove the draft bar from `site/index.html` and `reports/brief/ringkasan.html.tmpl`. (NGO, TL)
6. [ ] Check the flagged industrial sites in `reports/static_review.md` against imagery or local knowledge and note the result for each. (NGO, TL)
7. [ ] Agree in writing on ownership, reuse of code, credit, publication rights, sharing of field data, who approves the public brief, and how a mistake will be corrected. (all)
8. [ ] Keep the stakeholder list, with outreach dates, replies and corrections, privately and outside this repository. (OL)
9. [ ] Find NASA's notice on the May 2025 reprocessing of the VIIRS fire-type codes and add its link to this file. If the date differs, change `archive_min_last_modified`. (TL)

### Upkeep

10. [ ] Once a year, add the newest complete archive year to `archive_years` in `config/params.toml` and run `make masks`. New smelters stay unflagged until then. (TL)

### SP2: verification with Earth Engine

11. [ ] Register a noncommercial Earth Engine project and confirm eligibility. (TL)
12. [ ] Write the SP2 spec: how detections are grouped into candidate events, the 30-case image check, the MCD64A1 comparison, and the label format with its uncertainty. (TL)
13. [ ] Choose 3–5 case stories from the checked cases, with the NGO. (NGO, TL)

### SP3: research track

14. [ ] G0-01: compare the 11 provinces over 2023–2025 on one basis (same sensor, years and denominator). (TL)
15. [ ] G0-04: check the archive for 2013–2025 year by year for gaps, field changes and missing months. (TL)
16. [ ] G0-03 burned-area matching (uses the SP2 output) and G0-05 power check. (TL)
17. [ ] Commit the G0 amendment to GitHub before looking at any test results: question, test years, grouping rule, main score, improvement threshold, confidence-interval method. (TL)
18. [ ] R2 decision study: B0, B1, B1+, B2 and B3 under one budget, with a reliability chart, Brier score, loss-versus-budget figure and one decision trace. (TL)
19. [ ] Optional: cross-check burned area against GWIS. (TL)
20. [ ] Six-page methods report, three figures, a five-minute demo, and outreach to 15–20 named recipients. (TL, OL)

### Later, only if needed

21. [ ] Smoke and air-quality context from Open-Meteo, if the NGO asks for it. (TL)
22. [ ] A forest-area denominator alongside land area. (TL)

### Code, deferred from the 2026-10-19 review

23. [ ] Stop retrying permanent HTTP 4xx errors in `src/sulteng/fetch.py`. With a bad key they waste about 4 minutes per run.
24. [ ] Count calendar months and years in WITA rather than UTC in `src/sulteng/masks.py`.
25. [ ] Parse coverage intervals once per summary instead of on every `day_status` call (`src/sulteng/coverage.py`).
26. [ ] Categorize new detections once, not twice, in `src/sulteng/refresh.py`.
27. [ ] Merge `_read_json` in `src/sulteng/refresh.py` with `load_manifest` in `src/sulteng/fetch.py`, choosing one behaviour for corrupt files.
