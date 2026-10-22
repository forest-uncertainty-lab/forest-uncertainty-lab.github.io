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
| NASA FIRMS VIIRS yearly archives, Suomi NPP 2013–2025 and NOAA-20 2018–2025 | Research checks G0-01 and G0-04 only |
| geoBoundaries ADM1/ADM2 (OpenStreetMap) | Provinces, districts, land area |

Without a key the site starts with the last 7 days and grows a day at a time. Get a free key at https://firms.modaps.eosdis.nasa.gov/api/map_key/. For local runs, put it after `FIRMS_MAP_KEY=` in `.env` (copy `.env.example` if the file is missing); `make refresh` loads it. For GitHub Actions, store it as the repository secret `FIRMS_MAP_KEY`.

### Keeping the key away from AI coding tools

`.env` is gitignored, and every coding tool that offers a way to exclude files is told to leave it alone:

| Tool | Where | Strength |
|---|---|---|
| Codex CLI | `default_permissions = "no-dotenv"` profile in `~/.codex/config.toml` | Enforced by the macOS sandbox, shell commands included (tested 2026-10-19) |
| Claude Code | `Read`/`Edit` deny rules and the PreToolUse hook `~/.claude/hooks/no-dotenv.py` in `~/.claude/settings.json`; deny rules also in `.claude/settings.json` | File tools are blocked outright. The hook blocks shell commands that name `.env`, recursive `grep` and `rg -uu`; a script that opens the file indirectly gets past it unless Claude Code's sandbox is on |
| Cursor, Gemini CLI, Aider, Windsurf, JetBrains AI | `.cursorignore`, `.geminiignore`, `.aiderignore`, `.codeiumignore`, `.aiignore` | Keeps the file out of indexing and file tools; their terminals can still read it |
| Any agent that reads `AGENTS.md` or `CLAUDE.md` | Written rule | Instruction only |

GitHub Copilot has no exclusion file; its content exclusion is set in the repository settings on GitHub (paid plans).

`make masks` refuses archive files dated before 2025-06-01, when FIRMS fixed the VIIRS fire-type codes the masks rely on.

## Running it

Needs [uv](https://docs.astral.sh/uv/). Google Chrome is used, when present, to print the PDF brief.

```bash
uv sync
make test      # unit tests, no network
make refresh   # download the latest detections into data/live/
make serve     # build _site/ and serve it on http://localhost:8000
make masks     # rebuild masks and boundaries from the archive (occasional; outputs are committed)
make history ARCHIVE_DIR=~/Library/Caches/sulteng-remote-sensing   # weekly fire history of all 34 provinces, 2013 to the last archive year (occasional; output committed)
make g0 ARCHIVE_DIR=~/Library/Caches/sulteng-remote-sensing   # G0-01 and G0-04 reports (about 350 MB of archive)
```

If `uv run python …` fails with `No module named 'sulteng'` on a Mac, a file-sync app (iCloud Drive, Google Drive) has set the "hidden" flag on the files in `.venv`, and Python 3.13 ignores hidden `.pth` files. The `make` targets and pytest put `src/` on the path themselves, so use them; `chflags -R nohidden .venv` fixes plain `uv run` until the sync app sets the flag again.

## How it is put together

- `config/params.toml`: provinces, sensors, URLs, the static-source rule.
- `src/sulteng/`: the data code, one module per job (download, parse, assign, masks, store, coverage, summary, refresh, brief, site build).
- `data/boundaries/`, `data/public/`: committed outputs of `make masks`. The masks and static sites cover all 34 provinces (`data/boundaries/indonesia.geojson`); the Sulawesi Tengah monitor still compares 11. `data/public/static_site_ids.csv` lists every static-site ID ever issued and is read back on each rebuild, so a site keeps its ID; never delete it.
- `data/live/`: the rolling two-month store and the files the site reads. In GitHub Actions it lives on the `data-store` branch, which is overwritten on each run so history does not grow.
- `site/`: the HTML, CSS and JavaScript of the page.
- `.github/workflows/publish.yml`: refresh every six hours, save `data/live/`, build, deploy to GitHub Pages.

## Design and plan

- Project plan: `01_Simple_Project_Plan.docx`
- Design: `docs/superpowers/specs/2026-10-18-sp1-fire-monitor-now-design.md`
- Implementation plan: `docs/superpowers/plans/2026-10-18-sp1-fire-monitor-now.md`
- Static-source sites to check by hand: `reports/static_review.md`, with an OpenStreetMap pre-check in `reports/static_osm_precheck.md`
- Research checks G0-01 (province comparison) and G0-04 (archive 2013–2025, Suomi NPP against NOAA-20): `reports/g0/README.md`
- Action items and data-source decisions: `docs/backlog.md`
