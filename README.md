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
