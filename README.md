# Haze, Explained

Haze, Explained is a static site by Vicky Feliren for reading Southeast Asian haze and Indonesian satellite fire detections. It has English and Indonesian text, dark and light themes, and three destinations.

- **Haze** shows Singapore’s official readings alongside a model estimate, and model estimates for eight other cities. Moreover, it compares the last two days with a three-day outlook and traces model winds backwards over recent detections.
- **Fire history** compares all 34 historical Indonesian provinces from 2013 onwards. Each province is compared with its own history over the same completed weeks. Furthermore, the charts distinguish missing days, satellite gap filling, the unfinished week and the rest-of-season outlook.
- **Sulawesi Tengah** retains the original monitor at `/sulawesi-tengah/`, with its district view, source categories and PDF brief.

The site remains a draft pending review of its methods and wording. A detection is a hot satellite pixel, so it does not establish that forest burned or measure burned area. Likewise, the site does not quantify news attention or claim that a province is overlooked.

The province chart shows an 80% interval from a Poisson count model. However, that interval excludes uncertainty in the historical baseline, weather, cloud cover and detection errors. Therefore, readers should not interpret a narrow interval as confidence in the full environmental claim. The methods appear beside the charts in both languages.

## Data

| Source | Use |
|---|---|
| NASA FIRMS VIIRS 7-day feeds (Suomi NPP, NOAA-20, NOAA-21), no key needed | Detections, refreshed every 6 hours |
| NASA FIRMS area API (optional `FIRMS_MAP_KEY`) | Fills in days the 7-day feeds no longer cover, such as the start of last month |
| NASA FIRMS VIIRS Suomi NPP yearly archive 2023–2025 | Builds the static-source and volcano masks |
| NASA FIRMS VIIRS yearly archives, Suomi NPP 2013–2025 and NOAA-20 2018–2025 | Weekly fire history and research checks G0-01 and G0-04 |
| [NEA through data.gov.sg](https://guide.data.gov.sg/developer-guide/real-time-apis) | Singapore’s five regional PM2.5 readings and PSI |
| [CAMS through Open-Meteo](https://open-meteo.com/en/docs/air-quality-api) | Air quality model estimates and forecasts; Open-Meteo also supplies pressure-level winds |
| Natural Earth countries at a scale of 1 to 50 million, v5.1.2 | Simplified coastlines for the regional map |
| geoBoundaries ADM1/ADM2 (OpenStreetMap) | Provinces, districts, land area |

Without a key, the current-year store starts with the last seven days and grows a day at a time. Consequently, earlier unfetched days remain marked as missing. Get a free key at https://firms.modaps.eosdis.nasa.gov/api/map_key/. For local runs, put it after `FIRMS_MAP_KEY=` in `.env` (copy `.env.example` if the file is missing); `make refresh` loads it. For GitHub Actions, store it as the repository secret `FIRMS_MAP_KEY`.

### Keeping the key away from AI coding tools

`.env` is gitignored, and every coding tool that offers a way to exclude files is told to leave it alone.

| Tool | Where | Strength |
|---|---|---|
| Codex CLI | `default_permissions = "no-dotenv"` profile in `~/.codex/config.toml` | Enforced by the macOS sandbox, shell commands included (tested 2026-10-19) |
| Claude Code | `Read`/`Edit` deny rules and the PreToolUse hook `~/.claude/hooks/no-dotenv.py` in `~/.claude/settings.json`; deny rules also in `.claude/settings.json` | File tools are blocked outright. The hook blocks shell commands that name `.env`, recursive `grep` and `rg -uu`; a script that opens the file indirectly gets past it unless Claude Code's sandbox is on |
| Cursor, Gemini CLI, Aider, Windsurf, JetBrains AI | `.cursorignore`, `.geminiignore`, `.aiderignore`, `.codeiumignore`, `.aiignore` | Keeps the file out of indexing and file tools; their terminals can still read it |
| Any agent that reads `AGENTS.md` or `CLAUDE.md` | Written rule | Instruction only |

GitHub Copilot has no exclusion file; its content exclusion is set in the repository settings on GitHub (paid plans).

`make masks` refuses archive files dated before 2025-06-01, when FIRMS fixed the VIIRS fire-type codes the masks rely on.

## Running it

Needs [uv](https://docs.astral.sh/uv/). Google Chrome is used, when present, to print the PDF brief. Node is optional for the chart calculation tests.

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

- `config/params.toml` defines provinces, sensors, URLs and the static-source rule.
- `config/indonesia.toml` defines the 34 historical provinces and nine haze cities.
- `src/sulteng/` contains the data pipeline. In addition, `yearstore.py`, `historypage.py` and `stats.py` prepare the history and estimates; `haze.py` prepares the haze snapshot; `extras.py` records their status separately from the monitor.
- `data/boundaries/` and `data/public/` contain committed outputs of `make masks`. The masks and static sites cover all 34 provinces (`data/boundaries/indonesia.geojson`); the Sulawesi Tengah monitor still compares 11. `data/public/static_site_ids.csv` lists every static-site ID ever issued and is read back on each rebuild, so a site keeps its ID; never delete it.
- `data/live/` holds the rolling two-month monitor store and the files the site reads. In GitHub Actions it lives on the `data-store` branch, which is overwritten on each run so history does not grow.
- `site/` contains the tabbed page and the original monitor. The charts use SVG and a canvas fire layer, with no framework or chart dependency. Moreover, `fire-data.js` shares chart calculations with Node tests, which pytest runs when Node is installed.
- `.github/workflows/publish.yml` refreshes every six hours, saves `data/live/`, builds and deploys to GitHub Pages.

## Refresh and uncertainty

The scheduled refresh runs every six hours. It updates `data/live/history_current.json`, combines it with the committed archive into `history.json`, and writes `haze.json` and the rolling Singapore model comparison. After that, the site build copies these files into `_site/data/`. The browser also tries NEA and Open-Meteo for current air readings. If a source fails, the pipeline preserves its last successful component with the original date, and the browser retains the snapshot when its own request fails. Wind paths and their fire encounters stay together to avoid combining different observation periods.

`status_extra.json` records history and haze failures separately. Moreover, the current-year backfill is capped at 30 FIRMS requests per run, so a first deployment may need several refreshes. The wind grid pauses between batches to respect the provider’s minute limit.

The fire history uses Suomi NPP as its baseline. NOAA-20 only fills days Suomi NPP missed, using the annual ratio between the satellites. An unfinished week uses recent daily observations, while the season outlook scales past seasonal patterns. Comparisons and season outlooks remain unavailable while completed weeks contain unresolved missing days. Moreover, the running-week estimate includes missing elapsed days. Counts use Poisson draws, while continuous heat power uses a weighted bootstrap that preserves its units. Neither estimate is a weather forecast. Furthermore, wind paths omit vertical motion, mixing and rain, so a path passing a detection does not establish a smoke source.

## Design and plan

- Haze design and methods are in [the design](docs/superpowers/specs/2026-10-22-haze-explained-design.md), with [the implementation plan](docs/superpowers/plans/2026-10-22-haze-explained.md) and [the approved mockup](docs/superpowers/specs/2026-10-22-haze-explained-mockup.html).
- The original project plan is `01_Simple_Project_Plan.docx`
- The monitor design is `docs/superpowers/specs/2026-10-18-sp1-fire-monitor-now-design.md`
- The monitor implementation plan is `docs/superpowers/plans/2026-10-18-sp1-fire-monitor-now.md`
- Static-source sites for manual checks are in `reports/static_review.md`, with an OpenStreetMap pre-check in `reports/static_osm_precheck.md`
- Research checks G0-01 and G0-04 are documented in `reports/g0/README.md`. They cover province comparisons and the Suomi NPP comparison with NOAA-20.
- Action items and data-source decisions are in `docs/backlog.md`
