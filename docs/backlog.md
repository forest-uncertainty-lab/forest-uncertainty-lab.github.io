# Backlog

Last updated 2026-10-22, after the third working session. Owners follow the roles in the project plan (§3): **TL** technical lead, **NGO** NGO reviewer, **OL** outreach lead.

Of the 31 items, 10 are closed and 2 are partly done. Everything still open needs a person, an account, a decision or the SP2 labels.

## Done on 2026-10-22 (third session)

All commits are on the `sp1-fire-monitor` branch; the full suite passes (105 tests).

| Item | What changed | Where |
|---|---|---|
| 29 | A static site keeps its ID when the masks are rebuilt. `data/public/static_site_ids.csv` records every ID ever issued, with the point where it was issued, and whether it is active, merged into another ID, or gone. On a rebuild each ID claims the site whose nearest flagged detection lies within the grouping distance (0.01°); a site claimed twice keeps the lower ID, and an ID that claims nothing is never issued again. The register started from the published sites, so every ID in `static_review.md` and `static_osm_precheck.md` carried over: `static_sites.geojson` is byte-identical. Tried on 2024–2025 data alone, the six reviewed sites that still pass the rule kept their IDs; ranking would have renumbered five of them. | `47485f0`, `0f459fa` |
| 28 | Suomi NPP against NOAA-20, 2018–2025: 0.96 to 1.02 Suomi NPP detections per NOAA-20 detection each year, with no trend, by day and by night. NOAA-20 has data on all 38 Suomi NPP gap days. `make g0` now downloads the NOAA-20 yearly files too (about 105 MB; 350 MB with Suomi NPP). | `daa95e3`, `reports/g0/g0-04-sensor-drift.md`, read in `reports/g0/README.md` |

Also fixed: `data/public/manifest.json` said `"dirty": true` after every `make masks`, even from a clean tree, because the build checked git after it had rewritten its own outputs. It now checks first (`369373c`); the rebuilt manifest names commit `369373c` with `"dirty": false`.

Found while starting the session: `make test` hung with no CPU use. The sync app covering `~/Desktop` had evicted 91 files in `.venv` to the cloud (macOS marks them `dataless`), and Python waited for them to download. Deleting `.venv` and running `uv sync` fixed it. 20 objects in `.git` are evicted too. See item 30.

## Done on 2026-10-19 (second session)

All commits are on the `sp1-fire-monitor` branch; the full suite passes (95 tests).

| Item | What changed | Where |
|---|---|---|
| 1 (prepared) | `make refresh` loads `FIRMS_MAP_KEY` from a gitignored `.env`. `.env` exists with an empty value, ready for the key. Coding agents are kept out of it: Codex by a sandbox rule (tested), Claude Code by deny rules and a hook (tested), five other tools by ignore files, and every agent by `AGENTS.md`. The README lists how strong each one is. | `a671e33`; settings outside the repo in `~/.codex/config.toml` and `~/.claude/settings.json` (backups saved next to each as `*.bak-2026-10-19`) |
| 9 | Found NASA's notice and linked it below. The date matches, so `archive_min_last_modified` stays 2025-06-01. | this file |
| 23 | Permanent HTTP 4xx errors are no longer retried; 408, 429 and 5xx still are. | `dd4b0ae` |
| 24 | Mask months and years now follow the WITA date. That exposed a second bug: the last night passes of 2025 fell on 1 January 2026, so some sites showed four years in a three-year archive. The archive is now cut to whole WITA years. Masks rebuilt: 1,879 static cells (was 1,881), the same 73 volcano cells and 168 sites. | `b584bc8`, `227040c`, `8f4403e` |
| 25 | Closed without a change. Measured on live data, `day_status` takes about 1 ms of a 272 ms summary, so the refactor would not pay for its API change. | |
| 26 | `store.combine` works on detection columns only, so each refresh categorizes once. | `24ab719` |
| 27 | One `read_json` for status, coverage and the download manifest. A corrupt file reads as empty with a warning: coverage then claims nothing (days show as missing, never zero), and a lost manifest makes `make masks` download again. | `8fcce9d` |
| 14 | G0-01 done. Sulawesi Tengah is 8th of 11 by "other" detections per 1,000 km² of land over 2023–2025; 40% of its detections are at suspected static sources. | `babe1f9`, `reports/g0/` |
| 15 | G0-04 done. The 2013–2025 archive has the same fields every year; Suomi NPP has no data on 38 days in 2022–2025. | `babe1f9`, `reports/g0/` |
| 6 (partly) | OpenStreetMap pre-check of the nine Morowali and Banggai sites: five lie in or next to a mapped industrial area, four are unclear. | `babe1f9`, `reports/static_osm_precheck.md` |

Also fixed: `make` targets and pytest failed locally with `No module named 'sulteng'`. Something syncing `~/Desktop` sets the macOS hidden flag on every file in `.venv`, and Python 3.13 skips hidden `.pth` files. Both now put `src/` on the path themselves (`172e961`). CI on Ubuntu was not affected. See item 30.

A live refresh and site build on 2026-10-19 worked: all three satellites `ok`, every category count adds up to its total, and last month (no key yet) shows 30 days of "tidak ada data", not zeros.

## Data sources

Decided on 2026-10-19 from the data-source review the project owner shared. Rule of thumb from that review: add a source only when it answers a question the current data cannot.

| Source | Decision | Role | Notes |
|---|---|---|---|
| NASA FIRMS | In use | Detections from the 7-day feeds every 6 hours; the 2023–2025 yearly archive builds the static-source and volcano masks; the area API backfills last month once a key exists; the Suomi NPP 2013–2025 and NOAA-20 2018–2025 yearly archives feed the G0 checks | Limit: 5,000 map-key transactions per 10 minutes (per the review). The first backfill run makes about 30 API requests (about 10 per satellite); later runs make a few at most. |
| Google Earth Engine | SP2 | Check a small sample (about 30) of candidate events against Sentinel-2 and Landsat imagery and the MCD64A1 burned-area product; prepare labels with their uncertainty written down | Needs a verified noncommercial Earth Engine project (per the review, a Community tier of 150 compute-unit hours a month since April 2026). Run it interactively and export the results into this repository. The public site never calls Earth Engine. |
| Copernicus GWIS | Optional, SP3 | Cross-check burned area and fire danger | Its active-fire layer draws on FIRMS, so it cannot independently confirm a FIRMS hotspot. Its coarse burned-area maps miss small fires. |
| Open-Meteo | Later, only if the NGO asks | Smoke and air-quality context (modelled PM2.5 and carbon monoxide) | Modelled values on a grid of about 45 km. They do not show where a fire burned. |
| NIFC Wildland Fire Open Data | Not used | | Covers the United States only. |

**FIRMS fire-type codes.** The [FIRMS news page](https://firms.modaps.eosdis.nasa.gov/content/notifications/firms/news.html) says: "A bug in the Collection-2 Vxx14IMGML monthly fire location production software caused the fire "Type" field to be set inconsistently for product versions 1 and 2. As a result, obvious type-2 ("other static land source") hotspots were often incorrectly labeled as type-0 ("presumed vegetation fire") hotspots. This bug was corrected in May 2025 and all VxxIMGML product files reprocessed to version 3." The entry has no date of its own. The masks depend on that field (1 = volcano, 2 = static source), so `scripts/build_masks.py` refuses any archive file dated before `archive_min_last_modified` (2025-06-01) in `config/params.toml`. Every yearly file for 2013–2024 is dated 2025-06-24 and the 2025 file 2026-10-10. The `version` column in the CSVs reads `2` in every year; that is the collection number, not the product version 3 the notice mentions.

**Order of work**, kept from the review: FIRMS evidence first, then Earth Engine checks on a small sample, then the evidence brief, and only then the uncertainty experiment.

## Action items

### To go live

1. [ ] Register a free FIRMS map key at https://firms.modaps.eosdis.nasa.gov/api/map_key/, put it after `FIRMS_MAP_KEY=` in `.env`, and run `make refresh` to fill last month. The backfill has only been tested against fakes. (TL)
2. [ ] Decide whether to merge the `sp1-fire-monitor` branch into `main`. (TL)
3. [ ] Create the GitHub organisation and repository, push, set Pages to deploy from GitHub Actions, add the `FIRMS_MAP_KEY` repository secret, and watch the first `publish` run. Neither workflow has run yet. Pushing publishes the draft site, so items 5 and 7 come first. (TL)
4. [ ] Take a screenshot of the deployed page and add it as the share image (`og:image` in `site/index.html`). Waits for item 3 (`og:image` needs the absolute Pages URL) and item 5 (the screenshot should not show the draft bar). The page already has a description and the other Open Graph tags. (TL)

### Before anything is public

5. [ ] Review all Indonesian wording on the site and in the brief. Once approved, remove the draft bar from `site/index.html` and `reports/brief/ringkasan.html.tmpl`. (NGO, TL)
6. [ ] Check the flagged industrial sites in `reports/static_review.md` against imagery or local knowledge and note the result for each. **Partly done:** `reports/static_osm_precheck.md` has an OpenStreetMap pre-check; the NGO confirms or corrects each row there. Site IDs no longer change on a rebuild (item 29), so results can be recorded against them. (NGO, TL)
7. [ ] Agree in writing on ownership, reuse of code, credit, publication rights, sharing of field data, who approves the public brief, and how a mistake will be corrected. (all)
8. [ ] Keep the stakeholder list, with outreach dates, replies and corrections, privately and outside this repository. (OL)
9. [x] Find NASA's notice on the May 2025 reprocessing of the VIIRS fire-type codes and add its link to this file. Done: linked above; the date matches. (TL)

### Upkeep

10. [ ] Once a year, add the newest complete archive year to `archive_years` in `config/params.toml` and run `make masks`. New smelters stay unflagged until then. Commit `data/public/static_site_ids.csv` with the other outputs: sites keep their IDs, new ones get the next number, and the run prints how many IDs are active, merged or gone. Next: early 2027, for 2026. (TL)

### SP2: verification with Earth Engine

11. [ ] Register a noncommercial Earth Engine project and confirm eligibility. (TL)
12. [ ] Write the SP2 spec: how detections are grouped into candidate events, the 30-case image check, the MCD64A1 comparison, and the label format with its uncertainty. Not started. (TL)
13. [ ] Choose 3–5 case stories from the checked cases, with the NGO. (NGO, TL)

### SP3: research track

14. [x] G0-01: compare the 11 provinces over 2023–2025 on one basis. Done: `reports/g0/g0-01-provinces.md`, read in `reports/g0/README.md`. (TL)
15. [x] G0-04: check the archive for 2013–2025 year by year for gaps, field changes and missing months. Done: `reports/g0/g0-04-archive.md`, read in `reports/g0/README.md`. Rerun both with `make g0 ARCHIVE_DIR=~/Library/Caches/sulteng-remote-sensing` (the files take about 350 MB with the NOAA-20 files item 28 added, so keep them out of synced folders). (TL)
16. [ ] G0-03 burned-area matching (uses the SP2 output) and G0-05 power check. (TL)
17. [ ] Commit the G0 amendment to GitHub before looking at any test results: question, test years, grouping rule, main score, improvement threshold, confidence-interval method. Test years should avoid or flag the Suomi NPP gaps listed in `reports/g0/README.md`. Item 28 found no drift in Suomi NPP against NOAA-20 for 2018–2025; years before 2018 have no second satellite to check against. (TL)
18. [ ] R2 decision study: B0, B1, B1+, B2 and B3 under one budget, with a reliability chart, Brier score, loss-versus-budget figure and one decision trace. Needs the SP2 labels. (TL)
19. [ ] Optional: cross-check burned area against GWIS. (TL)
20. [ ] Six-page methods report, three figures, a five-minute demo, and outreach to 15–20 named recipients. (TL, OL)

### Later, only if needed

21. [ ] Smoke and air-quality context from Open-Meteo, if the NGO asks for it. (TL)
22. [ ] A forest-area denominator alongside land area. G0-01 shows the order of provinces depends on the denominator, so this matters before any public comparison of years. (TL)

### Code, deferred from the first 2026-10-19 review

23. [x] Stop retrying permanent HTTP 4xx errors in `src/sulteng/fetch.py`. Done (`dd4b0ae`).
24. [x] Count calendar months and years in WITA rather than UTC in `src/sulteng/masks.py`. Done, with the archive cut to whole WITA years and the masks rebuilt (`b584bc8`, `227040c`, `8f4403e`).
25. [x] Parse coverage intervals once per summary instead of on every `day_status` call. Closed without a change: about 1 ms of 272 ms per summary.
26. [x] Categorize new detections once, not twice, in `src/sulteng/refresh.py`. Done (`24ab719`).
27. [x] Merge `_read_json` with `load_manifest`, choosing one behaviour for corrupt files. Done: `publish.read_json`, empty with a warning (`8fcce9d`).

### New on 2026-10-19

28. [x] Compare Suomi NPP with NOAA-20 for 2018–2025 to test whether Suomi NPP's detection rate drifted over the years. Done: no drift; `reports/g0/g0-04-sensor-drift.md`, read in `reports/g0/README.md` (`daa95e3`). (TL)
29. [x] Give static-source sites stable IDs. Done: `data/public/static_site_ids.csv` keeps each ID with its place across rebuilds and records merged and vanished IDs (`47485f0`, `0f459fa`). Never delete the file; without it the next build starts again from the published sites and forgets which IDs were retired. (TL)
30. [ ] Exclude `.venv` (or the whole project) from the sync app that covers `~/Desktop`, or move the project out of `~/Desktop`. The sync app hides the files in `.venv`, so plain `uv run python …` breaks until `chflags -R nohidden .venv`; `make` and pytest are protected. Worse, on 2026-10-22 it had evicted 91 `.venv` files to the cloud, and `make test` hung until `.venv` was rebuilt (`rm -rf .venv && uv sync`); 20 objects in `.git` are evicted too, so git may stall offline. The machine also ran slowly during the second session (load average above 150, Google Drive near 90% CPU). (TL)
31. [ ] Optional: turn on Claude Code's sandbox (`"sandbox": {"enabled": true}` in `~/.claude/settings.json`). The `Read(**/.env)` deny rules then also bind shell commands at the operating-system level, as the Codex profile already does. The current hook blocks commands that name `.env`, but not a script that opens it indirectly. Turning the sandbox on also restricts network access for shell commands, so try it on a quiet day. (TL)
