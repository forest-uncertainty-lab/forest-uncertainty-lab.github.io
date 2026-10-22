"""Build the weekly fire history of all 34 provinces from the FIRMS yearly archive.

Writes data/public/history_archive.json. Run occasionally, like `make masks`: when a new yearly file
is added (archive_last in config/indonesia.toml) or the masks change. Suomi NPP 2013 onwards and
NOAA-20 2018 onwards (for gap filling) are downloaded into --archive-dir, about 350 MB together.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from sulteng.config import ROOT, load_params
from sulteng.fetch import fetch_yearly, utc_now_iso
from sulteng.firehistory import WEEKS, gap_days, keep_fires, ratio, weekly, with_gap_fill
from sulteng.firms import read_archive
from sulteng.indonesia import load_indonesia
from sulteng.masks import masks_from_json
from sulteng.publish import write_json

NOAA20_FIRST_YEAR = 2018  # FIRMS has NOAA-20 from April 2018
OFFSET = 8  # weeks are counted in UTC+8 for the whole country


def week_of(day: str) -> int:
    return min((date.fromisoformat(day).timetuple().tm_yday - 1) // 7, WEEKS - 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    params, ind = load_params(), load_indonesia()
    years = list(range(ind.archive_first, ind.archive_last + 1))
    args.archive_dir.mkdir(parents=True, exist_ok=True)
    snpp_files = fetch_yearly(params.archive_url, years, args.archive_dir)
    n20_files = fetch_yearly(params.noaa20_archive_url, [y for y in years if y >= NOAA20_FIRST_YEAR], args.archive_dir)
    provinces = gpd.read_file(ROOT / "data" / "boundaries" / "indonesia.geojson")
    masks = masks_from_json(json.loads((ROOT / "data" / "public" / "masks.json").read_text(encoding="utf-8")))
    names = [r.name for r in ind.regions]

    count = np.zeros((len(names), len(years), WEEKS))
    frp = np.zeros((len(names), len(years), WEEKS))
    filled_days = np.zeros((len(years), WEEKS), dtype=int)
    missing_days = np.zeros((len(years), WEEKS), dtype=int)
    ratios: dict[str, float | None] = {}
    carry = pd.DataFrame()  # the last night passes of 31 December UTC fall on 1 January of the next local year
    for yi, year in enumerate(years):
        snpp = read_archive(args.archive_dir / snpp_files[year]["file"], utc_offset_hours=OFFSET, sensor="N")
        n20 = (read_archive(args.archive_dir / n20_files[year]["file"], utc_offset_hours=OFFSET, sensor="N20")
               if year in n20_files else snpp.iloc[0:0])
        gaps = gap_days(snpp["acq_date"].unique(), date(year, 1, 1), date(year, 12, 31))
        r = ratio(snpp.groupby("acq_date").size(), n20.groupby("acq_date").size()) if len(n20) else None
        kept = keep_fires(with_gap_fill(snpp, n20, gaps, r), provinces, masks)
        kept = pd.concat([carry, kept], ignore_index=True) if len(carry) else kept
        carry = kept[kept["local_date"].str[:4] == str(year + 1)]
        w = weekly(kept, year, names)
        count[:, yi, :], frp[:, yi, :], filled_days[yi] = w["count"], w["frp"], w["filled_days"]
        n20_days = set(n20["acq_date"]) if r is not None else set()
        for day in gaps:
            if day not in n20_days:
                missing_days[yi, week_of(day)] += 1
        ratios[str(year)] = None if r is None else round(r, 4)
        print(f"{year}: {count[:, yi, :].sum():,.0f} detections kept, {len(gaps)} gap days, "
              f"{w['filled_days'].sum()} filled, ratio {r if r is None else round(r, 3)}", flush=True)

    write_json({
        "built_at": utc_now_iso(),
        "years": years,
        "provinces": names,
        "count": np.round(count, 2).tolist(),
        "frp": np.round(frp).astype(int).tolist(),
        "filled_days": filled_days.tolist(),
        "missing_days": missing_days.tolist(),
        "ratio": ratios,
    }, ROOT / "data" / "public" / "history_archive.json")
    print("wrote data/public/history_archive.json")


if __name__ == "__main__":
    main()
