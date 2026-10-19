"""Multi-year checks on the FIRMS archive: what each yearly file holds (G0-04) and the
11-province comparison on one sensor, one set of years and one denominator (G0-01)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from sulteng.masks import CATEGORIES

PROFILED_FIELDS = ("satellite", "instrument", "version", "confidence", "daynight", "type")


def longest_gap(seen, first: date, last: date) -> tuple[int, date | None]:
    """Longest run of days in [first, last] with no date in `seen`, and the day the run starts."""
    have = set(seen)
    best, best_start, run, start = 0, None, 0, None
    day = first
    while day <= last:
        if day in have:
            run = 0
        else:
            if run == 0:
                start = day
            run += 1
            if run > best:
                best, best_start = run, start
        day += timedelta(days=1)
    return best, best_start


def raw_profile(path: Path | str, year: int) -> dict:
    """Columns, value counts of the categorical fields, rows per UTC month, and days with no
    detection anywhere in the file. FIRMS cuts the yearly files at UTC midnight."""
    raw = pd.read_csv(path, dtype=str)
    dates = pd.to_datetime(raw["acq_date"].str.strip(), format="%Y-%m-%d").dt.date
    months = pd.Series(dates).map(lambda d: d.strftime("%Y-%m")).value_counts()
    first, last = date(year, 1, 1), date(year, 12, 31)
    in_year = {d for d in dates if first <= d <= last}
    gap, gap_start = longest_gap(in_year, first, last)
    per_month = {f"{year}-{m:02d}": int(months.get(f"{year}-{m:02d}", 0)) for m in range(1, 13)}
    return {
        "year": year,
        "rows": int(len(raw)),
        "rows_outside_year": int(sum(not (first <= d <= last) for d in dates)),
        "columns": list(raw.columns),
        "values": {
            field: {str(k): int(v) for k, v in sorted(raw[field].str.strip().value_counts().items())}
            for field in PROFILED_FIELDS if field in raw.columns
        },
        "rows_per_month": per_month,
        "empty_months": [m for m, n in per_month.items() if n == 0],
        "days_without_rows": (last - first).days + 1 - len(in_year),
        "longest_gap": (gap, gap_start.isoformat() if gap_start else None),
    }


def field_changes(profiles: dict[int, dict]) -> list[str]:
    """Where a year's columns or categorical values differ from the year before."""
    notes: list[str] = []
    years = sorted(profiles)
    for before, year in zip(years, years[1:]):
        a, b = profiles[before], profiles[year]
        added = [c for c in b["columns"] if c not in a["columns"]]
        dropped = [c for c in a["columns"] if c not in b["columns"]]
        if added:
            notes.append(f"{year}: new column(s) {', '.join(added)}")
        if dropped:
            notes.append(f"{year}: dropped column(s) {', '.join(dropped)}")
        for field in sorted(set(a["values"]) | set(b["values"])):
            old, new = set(a["values"].get(field, {})), set(b["values"].get(field, {}))
            if new - old:
                notes.append(f"{year}: {field} gains value(s) {', '.join(sorted(new - old))}")
            if old - new:
                notes.append(f"{year}: {field} loses value(s) {', '.join(sorted(old - new))}")
    return notes


def province_years(categorized: pd.DataFrame, provinces: pd.DataFrame, years) -> pd.DataFrame:
    """Detections per province and WITA year, by category, with rates per 1,000 km² of land.
    Every province gets a row for every year, so a year without detections reads 0."""
    years = list(years)
    year = categorized["local_date"].str[:4].astype(int)
    chosen = categorized.assign(year=year)[year.isin(years)]
    grid = pd.MultiIndex.from_product([list(provinces["name"]), years], names=["province", "year"])
    counts = (chosen.groupby(["province", "year", "category"]).size()
              .unstack(fill_value=0).reindex(columns=list(CATEGORIES), fill_value=0)
              .reindex(grid, fill_value=0))
    counts["all"] = counts[list(CATEGORIES)].sum(axis=1)
    meta = provinces.rename(columns={"name": "province"})[["province", "island", "area_km2"]]
    out = counts.reset_index().merge(meta, on="province")
    out["all_per_1000_km2"] = out["all"] / out["area_km2"] * 1000
    out["other_per_1000_km2"] = out["other"] / out["area_km2"] * 1000
    return out[["province", "island", "area_km2", "year", *CATEGORIES, "all",
                "all_per_1000_km2", "other_per_1000_km2"]]
