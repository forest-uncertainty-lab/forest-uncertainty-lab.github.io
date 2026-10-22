# Haze, Explained: design

Date: 2026-10-22. Branch: `haze-explained`. Status: approved to build in chat ("just continue the rest of the work"); the owner opted out of further questions, so every choice marked *my call* below is the builder's and open to review.

## 1. Intent

The public site becomes **Haze, Explained**, a Forest Uncertainty Lab project by Vicky Feliren. It serves two readers:

- **A resident** in Singapore, Kuala Lumpur, Jakarta, Pekanbaru, Jambi, Palembang, Pontianak, Palangka Raya or Palu who is breathing haze and wants to know how bad the air is, whether it will improve, where the air came from, and what is still unknown.
- **An analyst or journalist** who needs defensible evidence. The owner's motivating case: news outlets cover Kalimantan and Sumatra fires, while Sulawesi, Maluku and Papua burn with little coverage. In the 2026 data so far (1 January to 21 October), Maluku and Papua have their highest Suomi NPP count since at least 2013 (119,746 against a previous maximum of 79,725 in 2015), West Papua is at 56 times its usual level and North Maluku at 28 times, and Sulawesi has its second-highest year. A check of where those detections fall (thousands of separate 1 km cells, almost none active year-round, a sharp dry-season rise) shows fires rather than unmasked industrial heat.

Everything shown must be recent (refreshed every six hours, the air numbers live in the browser), and every number must say how it was made and how sure it is.

## 2. Goals

1. One page with tabs: **Haze** (Kabut asap), **Fire history** (Riwayat api), and a link tab to the existing **Sulawesi Tengah** monitor. English and Indonesian for every word; dark (default) and light themes; the footer credits "Made by Vicky Feliren", linked to https://vickyfeliren.com/. No Claude or Anthropic attribution anywhere.
2. **Fire history** for all 34 provinces (geoBoundaries ADM1), grouped by island, weekly from 2013 to the latest complete day, with Suomi NPP only so every year is counted the same way.
3. **Haze** for nine cities: measured air where an open official feed exists (NEA, Singapore), a clearly labelled model estimate elsewhere (CAMS via Open-Meteo), a three-day outlook, wind back-trajectories at three heights over recent fire detections, and the known / not known / would settle it panel.
4. Statistical methods that make the numbers recent and fair, each explained on the page:
   - **Gap filling (interpolation across satellites).** A Suomi NPP day with no data anywhere is filled, province by province, from NOAA-20 the same day times the year's Suomi NPP to NOAA-20 ratio (G0-04: 0.96 to 1.02). Filled days are marked; a day both satellites missed stays missing.
   - **Nowcast of the running week (Bayesian bootstrap).** The unfinished week is completed with draws from the province's last 14 complete days, weighted by Dirichlet(1, …, 1) weights, giving a median and an 80% interval. The cell and the line show it as an estimate.
   - **Season outlook (extrapolation from analog years).** The rest of the current year is projected by scaling each past year's remaining weeks by this year's total so far relative to that year's total over the same weeks. The page shows the median, an 80% range across the 13 analog years, and the share of analogs in which the year ends above the previous record.
   - **Fair "unusual for this place" (Bayesian rate with Jeffreys prior).** For each province, the year-to-date count gets a Gamma(n + ½, 1) posterior; the page shows times the usual level (median of past years over the same weeks) with an 80% interval, the rank among years, and the probability that the underlying level is above the previous record. Small provinces get wide intervals instead of noisy extremes.
   - **Back-trajectory ensemble (Monte Carlo).** Each city gets 9 members per height (start time 0, −1, −2 h; wind speed ×0.9, ×1.0, ×1.1 with direction ±10°), and the page reports the share of members that passed within 50 km of a fire detection.
   - **Model track record.** The CAMS estimate is compared with NEA's hourly readings over the last 30 days (a rolling store); the page reports the median measured-to-model ratio and its 10th to 90th percentile range for Singapore, and says plainly that this cannot be transferred to cities without stations.

## 3. Non-goals

- Smoke attribution to a specific fire, dispersion modelling (HYSPLIT), or health advice of our own. The page links to NEA, APIMS and ISPU.
- News-coverage measurement (GDELT dropped by the owner on 2026-10-22).
- Forest versus non-forest classification of detections. Needed for the claim "forest is burning"; recorded as a backlog item for SP2 (Earth Engine) because it needs a land-cover map the pipeline does not have.
- The R2 decision replay. Later.
- Neighbouring countries' fires in the fire history (Indonesia only; the haze map shows the whole region's detections).

## 4. Anti-goals

- A number without its method or its uncertainty next to it.
- A modelled or estimated value that looks like a measurement (estimates always carry a dashed badge or dashed outline and the word "estimate").
- A missing day shown as zero.
- A rank or ratio that makes a small province look extreme on a handful of detections.

## 5. Constraints

- Static site on GitHub Pages; Python pipeline on GitHub Actions every six hours; no server, no paid service.
- Keys: `FIRMS_MAP_KEY` (repository secret; locally in the gitignored env file). No other key is needed. OpenAQ stays out of the pipeline for now (*my call*: it would need a second secret and the low-cost sensors need humidity correction).
- The browser may call NEA (data.gov.sg) and Open-Meteo directly (both allow it), which reverses the earlier rule that the site never calls Open-Meteo. FIRMS is never called from the browser.
- Open-Meteo free tier: under 10,000 calls a day. The wind grid (1°, 95–141° E, 11° S–8° N, about 940 points in batches of 100) four times a day stays well inside it.
- Times are local to the selected city (SGT, MYT, WIB, WITA, WIT); fire weeks are counted in UTC+8 for the whole country.
- The Sulawesi Tengah monitor keeps working unchanged in behaviour; it moves to `/sulawesi-tengah/`.

## 6. Data and pipeline

| Product | Built by | Where | Contents |
|---|---|---|---|
| `indonesia.toml` | hand | `config/` | 34 provinces: geoBoundaries name, Indonesian name, English name, island; nine haze cities with time zone, country and official link |
| Masks for all of Indonesia | `make masks` (extended) | `data/public/masks.json` | static and volcano cells from the 2023–2025 archive, same rule as before, now over all provinces; the site ID register carries existing IDs |
| Province outlines | `make masks` | `data/boundaries/indonesia.geojson` | 34 provinces for point assignment |
| History archive | `make history` (new, occasional) | `data/public/history_archive.json` | per province, year (2013 to last complete year), week: Suomi NPP counts and FRP after masks and fire types, gap days, filled days |
| Current year | `make refresh` (extended) | `data/live/history_current.json` | per province and local day of the current year: Suomi NPP counts and FRP, NOAA-20 counts for gap filling, UTC days seen |
| Fire history for the page | `make refresh` | `data/live/history.json` | archive plus current year as weeks, nowcast, season outlook, per-province "unusual" statistics |
| Haze snapshot | `make refresh` | `data/live/haze.json` | NEA and CAMS series per city, trajectory ensembles, fires of the last 48 h binned to 0.02°, model track record, generated time |
| Model track record store | `make refresh` | `data/live/haze_track.json` | hourly NEA mean and CAMS value for Singapore, last 30 days |

Current-year updates: each refresh already downloads the three 7-day feeds; the Suomi NPP and NOAA-20 feeds replace the days they cover. Days of the current year not yet in the store are backfilled once through the FIRMS area API (Suomi NPP standard data where FIRMS has it, near-real-time after; NOAA-20 only for Suomi NPP gap days). Without a key, the year grows from the feeds alone and the page says so.

## 7. Pages

**Haze tab.** As in the approved mockup (`.superpowers/brainstorm/…/explained.html`): city pills; "The air now" (NEA PSI for Singapore with five regions, the model estimate with a dashed badge elsewhere and the 24-hour mean against the WHO guideline); the last two days and the next three (NEA band, model line, dashed forecast, WHO line); the map with fires and the trajectory ensemble (members thin, central path bold, labels by height); the per-height sentences with the share of members passing fires; known / not known / would settle it; official links; method. New: the model track-record sentence for Singapore, and a live refresh in the browser of the NEA and CAMS current values with a fallback to the snapshot and a visible "updated" time.

**Fire history tab.** As in the mockup, plus: year bars (same weeks or whole year; in whole-year mode the current year carries its outlook range as a whisker); the heatmap with filled-day hatching, the running week as an estimate with a dashed outline; a new "This year by province" dot plot (times usual, 80% interval whisker, log scale, sorted, with the probability above the previous record in the tooltip and a table view); the detail chart with the running-week estimate and the season outlook as a shaded band for the remaining weeks.

**Sulawesi Tengah tab.** A link to `/sulawesi-tengah/`, the existing monitor with its data paths adjusted.

## 8. Testing

Unit tests, no network: gap filling (filled where NOAA-20 has data, missing where it does not, ratio applied); weekly binning (UTC+8 boundaries, week 52 absorbing the last days); Bayesian bootstrap nowcast (deterministic with a seed, interval contains the observed partial sum, widens with fewer days); analog outlook (exact on a constructed history); Jeffreys rate (interval width shrinks with count, probability above the maximum); trajectory ensemble (zero wind stays put, constant wind moves the expected distance, member count); haze parsing of NEA and Open-Meteo payloads (fixtures); history assembly end to end on synthetic detections; site build copies the new files and the moved monitor. The pages are checked by rendering them headless in both languages and themes.

## 9. Left to the builder

Module boundaries, file names beyond those above, chart details within the mockup's visual language, and the exact wording, following the no-slop rules and British English.
