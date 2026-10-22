"""Weekly Suomi NPP fire detections per province, with satellite gaps filled from NOAA-20.

Weeks follow the local date in UTC+8: week index (day of year - 1) // 7, the last one or two days of
the year folded into week 51. A UTC day with no Suomi NPP row anywhere is a gap; it is filled from
NOAA-20 detections of the same UTC day, each weighted by the year's Suomi NPP to NOAA-20 ratio.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from datetime import date, timedelta

import geopandas as gpd
import numpy as np
import pandas as pd

from sulteng.masks import Masks, cell_index

WEEKS = 52
MIN_SHARED_DAYS = 30  # fewer shared days than this and the ratio is too uncertain to fill gaps with


def local_week(local_dates: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    d = pd.to_datetime(local_dates)
    return d.dt.year.to_numpy(), np.minimum((d.dt.dayofyear.to_numpy() - 1) // 7, WEEKS - 1)


def gap_days(utc_dates_seen: Iterable[str], first: date, last: date) -> list[str]:
    """UTC days in [first, last] with no row at all."""
    seen = set(utc_dates_seen)
    days = (first + timedelta(days=i) for i in range((last - first).days + 1))
    return [d.isoformat() for d in days if d.isoformat() not in seen]


def ratio(snpp_daily: pd.Series, n20_daily: pd.Series) -> float | None:
    """Suomi NPP rows per NOAA-20 row over the UTC days both have rows (series indexed by UTC date)."""
    shared = snpp_daily.index.intersection(n20_daily.index)
    shared = shared[(snpp_daily[shared] > 0) & (n20_daily[shared] > 0)]
    if len(shared) < MIN_SHARED_DAYS:
        return None
    return float(snpp_daily[shared].sum() / n20_daily[shared].sum())


def with_gap_fill(snpp: pd.DataFrame, n20: pd.DataFrame, gaps: Collection[str], r: float | None) -> pd.DataFrame:
    """Suomi NPP rows (weight 1) plus NOAA-20 rows on Suomi NPP gap days (weight r, filled)."""
    parts = [snpp.assign(weight=1.0, filled=False)]
    if r is not None and len(gaps):
        parts.append(n20[n20["acq_date"].isin(set(gaps))].assign(weight=float(r), filled=True))
    return pd.concat(parts, ignore_index=True)


def unmasked(df: pd.DataFrame, masks: Masks) -> pd.DataFrame:
    """Rows outside the volcano and static-source cells, without FIRMS types 1-3 where a type is given."""
    keep = ~cell_index(df, masks.cell_deg).isin(masks.static.union(masks.volcano))
    if "type" in df.columns:
        keep &= ~df["type"].astype("Int64").isin([1, 2, 3]).to_numpy(dtype=bool, na_value=False)
    return df[keep]


def keep_fires(df: pd.DataFrame, provinces: gpd.GeoDataFrame, masks: Masks) -> pd.DataFrame:
    """Possible vegetation fires: unmasked rows inside a province, with its `name` as `province`."""
    rows = unmasked(df, masks).reset_index(drop=True)
    points = gpd.GeoDataFrame(rows, geometry=gpd.points_from_xy(rows["longitude"], rows["latitude"]), crs=provinces.crs)
    inside = gpd.sjoin(points, provinces[["name", "geometry"]], predicate="within", how="inner")
    inside = inside[~inside.index.duplicated(keep="first")].sort_index()
    return pd.DataFrame(inside.drop(columns=["geometry", "index_right"])).rename(columns={"name": "province"})


def weekly(df_kept: pd.DataFrame, year: int, province_names: Sequence[str]) -> dict:
    """Weighted detections and fire radiative power per province and week of `year`, and filled days per week."""
    count = np.zeros((len(province_names), WEEKS))
    frp = np.zeros((len(province_names), WEEKS))
    filled_days = np.zeros(WEEKS, dtype=int)
    if len(df_kept):
        years, weeks = local_week(df_kept["local_date"])
        rows = df_kept[years == year]
        weeks = weeks[years == year]
        index = {p: i for i, p in enumerate(province_names)}
        p = rows["province"].map(index).to_numpy()
        weight = rows["weight"].to_numpy(dtype=float) if "weight" in rows else np.ones(len(rows))
        np.add.at(count, (p, weeks), weight)
        np.add.at(frp, (p, weeks), weight * rows["frp"].to_numpy(dtype=float))
        if "filled" in rows:
            filled = rows["filled"].to_numpy(dtype=bool)
            days = pd.DataFrame({"week": weeks[filled], "day": rows["acq_date"].to_numpy()[filled]}).drop_duplicates()
            np.add.at(filled_days, days["week"].to_numpy(dtype=int), 1)
    return {"count": count, "frp": frp, "filled_days": filled_days}
