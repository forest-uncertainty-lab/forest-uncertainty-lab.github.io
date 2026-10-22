# G0 checks: where they stand

Written 2026-10-19 and updated 2026-10-22 from the reports in this folder, which `make g0` regenerates. The plan (§4) has five checks. This file says what each one found and what is still open. Whether that adds up to GO, PIVOT or STOP is the technical lead's decision, recorded in the decision memo.

| Check | Status | Where |
|---|---|---|
| G0-01 Can we compare provinces fairly? | Done | `g0-01-provinces.md`, `g0-01-provinces.csv` |
| G0-02 Are factories creating false fire signals? | Masks built and 9 Morowali and Banggai sites checked against OpenStreetMap. The NGO check is open (backlog item 6). | `../static_review.md`, `../static_osm_precheck.md` |
| G0-03 Can burn maps support the study? | Not started. Needs the SP2 event grouping and MCD64A1. | |
| G0-04 Is the 2013–2025 record usable? | Done | `g0-04-archive.md`, `g0-04-profiles.json`, `g0-04-sensor-drift.md`, `g0-04-sensor-drift.csv` |
| G0-05 Could the study find a meaningful difference? | Not started. Needs G0-03 and the 30-case image check. | |

## G0-01: the 11 provinces, 2023–2025

The comparison meets the plan's three conditions. All 11 provinces use one sensor (VIIRS on Suomi NPP), every WITA day of 2023, 2024 and 2025, and the same denominator (land area).

What it shows:

- Sulawesi Tengah had 45.9 "other" detections per 1,000 km² of land per year. Seven provinces had more, with Kalimantan Selatan highest at 158.2. Sulawesi Barat, Sulawesi Utara and Kalimantan Utara had less.
- Year by year, Sulawesi Tengah was 7th of 11 in 2023, 6th in 2024 and 5th in 2025. 2023 was the highest of the three years in every province except Kalimantan Utara.
- 40% of Sulawesi Tengah's detections (5,598 of 13,929) fell at suspected static sources. Only Sulawesi Utara had a larger flagged share (65%, mostly volcanoes). Counting the flagged detections as fires would raise Sulawesi Tengah's rate from 45.9 to 76.8.

These numbers do not support a claim that Sulawesi Tengah burns more than Kalimantan, or that it is neglected. The plan's fallback applies: fire activity exists and warrants checking (§6).

Limits of the comparison:

- Suomi NPP has no data on some days (see G0-04). The missing days are the same for every province, so the comparison between provinces holds, but each year's totals are lower bounds. 2024 lost the most (20 days, 11 of them in July).
- Clouds hide fires unevenly between provinces and seasons. This check does not measure that.
- The denominator is land area. A forest-area denominator would change the order (backlog item 22).
- The static-source masks were built from the same 2023–2025 detections they are applied to.

## G0-04: the archive, 2013–2025

- Every year has the same columns and the same values in the six categorical fields checked. The `type` field is filled in every year.
- FIRMS regenerated every file on 24 June 2025 (2025's on 10 October 2026), after the May 2025 fix to the fire-type codes.
- No month is empty. Days with no detection anywhere in Indonesia, which point to missing satellite data rather than a day without fires:

| Year | Days | Dates (UTC) |
|---|---|---|
| 2013–2021 | 0 | |
| 2022 | 15 | 27 July – 10 August |
| 2023 | 2 | 26–27 July |
| 2024 | 20 | 30 May – 3 June, 10–15 July, 24–28 July, 26 September, 3–5 November |
| 2025 | 1 | 12 November |

On these checks the record can be used for 2013–2025 if those days count as missing, never as zero. The 2022 and 2024 gaps fall in the dry season, so totals for those years run low.

### Suomi NPP against NOAA-20, 2018–2025

`g0-04-sensor-drift.md` tests whether Suomi NPP's detection rate drifted over the years, by comparing its yearly counts over Indonesia with NOAA-20's on the dates both have data.

- Suomi NPP had 0.96 to 1.02 detections per NOAA-20 detection each year. The yearly ratios show no trend: a straight line through them rises 0.002 a year, about 1% over seven years, which is smaller than the change from one year to the next.
- Only 2021 has a 95% interval that leaves out 1 (0.961, interval 0.938–0.983). The years either side are 0.982 and 0.989, so it reads as one low year, not the start of a drift.
- Day and night passes, taken separately, give the same picture: their ratios rise about 0.002 a year.
- The 38 dates on which only NOAA-20 has data are exactly the 38 Suomi NPP gap days listed above, so NOAA-20 confirms them. NOAA-20 has 7 gap days of its own (19–22 July and 30 September 2023, 4–5 February 2024); the comparison leaves those out too.

So Suomi NPP's record for 2018–2025 shows no drift relative to NOAA-20. The check cannot see a drift that both instruments share, and it says nothing about 2013–2017, before NOAA-20.
