"""Static-source and volcano masks from the archive, and the category of each detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from sulteng.config import MaskParams
from sulteng.grouping import group_nearby

CATEGORIES = ("volcano", "static_suspect", "other")
_NAMES = ["iy", "ix"]


@dataclass(frozen=True)
class Masks:
    cell_deg: float
    static: pd.MultiIndex
    volcano: pd.MultiIndex


def cell_index(df: pd.DataFrame, cell_deg: float) -> pd.MultiIndex:
    iy = np.floor(df["latitude"].to_numpy(dtype=float) / cell_deg).astype(np.int64)
    ix = np.floor(df["longitude"].to_numpy(dtype=float) / cell_deg).astype(np.int64)
    return pd.MultiIndex.from_arrays([iy, ix], names=_NAMES)


def _cells(pairs_iy, pairs_ix) -> pd.MultiIndex:
    return pd.MultiIndex.from_arrays(
        [np.asarray(pairs_iy, dtype=np.int64), np.asarray(pairs_ix, dtype=np.int64)], names=_NAMES
    )


def _spread(cells: pd.DataFrame) -> pd.DataFrame:
    """Rows repeated for their own cell and the 8 neighbouring cells."""
    shifted = [cells.assign(iy=cells["iy"] + dy, ix=cells["ix"] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    return pd.concat(shifted, ignore_index=True).drop_duplicates()


def pooled_cell_stats(df: pd.DataFrame, cell_deg: float) -> pd.DataFrame:
    """For each cell: distinct calendar months and years with detections in its 3×3 neighbourhood."""
    idx = cell_index(df, cell_deg)
    base = pd.DataFrame({
        "iy": idx.get_level_values("iy"),
        "ix": idx.get_level_values("ix"),
        "month": df["acq_utc"].dt.month.to_numpy(),
        "year": df["acq_utc"].dt.year.to_numpy(),
    }).drop_duplicates()
    return _spread(base).groupby(_NAMES).agg(n_months=("month", "nunique"), n_years=("year", "nunique"))


def recurrent_cells(stats: pd.DataFrame, min_calendar_months: int, min_years: int) -> pd.MultiIndex:
    keep = (stats["n_months"] >= min_calendar_months) & (stats["n_years"] >= min_years)
    return stats.index[keep]


def type_cells(df: pd.DataFrame, fire_type: int, cell_deg: float) -> pd.MultiIndex:
    """Cells holding, or next to, an archive detection of the given FIRMS type."""
    hits = df.loc[_type_is(df, fire_type)]
    idx = cell_index(hits, cell_deg)
    spread = _spread(pd.DataFrame({"iy": idx.get_level_values("iy"), "ix": idx.get_level_values("ix")}))
    return _cells(spread["iy"], spread["ix"])


def build_masks(archive: pd.DataFrame, mask_params: MaskParams) -> Masks:
    cell = mask_params.cell_deg
    stats = pooled_cell_stats(archive, cell)
    recurrent = recurrent_cells(stats, mask_params.min_calendar_months, mask_params.min_years)
    static = recurrent.union(type_cells(archive, 2, cell))
    return Masks(cell_deg=cell, static=static, volcano=type_cells(archive, 1, cell))


def categorize(df: pd.DataFrame, masks: Masks) -> pd.DataFrame:
    """Copy of df with `category`: volcano, then static_suspect, then other."""
    cells = cell_index(df, masks.cell_deg)
    volcano = _type_is(df, 1) | cells.isin(masks.volcano)
    static = _type_is(df, 2) | cells.isin(masks.static)
    return df.assign(category=np.select([volcano, static], ["volcano", "static_suspect"], default="other"))


def _type_is(df: pd.DataFrame, value: int) -> np.ndarray:
    if "type" not in df.columns:
        return np.zeros(len(df), dtype=bool)
    return df["type"].astype("Int64").eq(value).to_numpy(dtype=bool, na_value=False)


SITE_COLUMNS = [
    "site_id", "latitude", "longitude", "detections", "first_date", "last_date",
    "calendar_months", "years", "type2_share", "province", "district",
]


def static_sites(categorized: pd.DataFrame, cell_deg: float) -> pd.DataFrame:
    """Static-suspect detections grouped into sites, largest first."""
    flagged = categorized[categorized["category"] == "static_suspect"].reset_index(drop=True)
    if flagged.empty:
        return pd.DataFrame(columns=SITE_COLUMNS)
    flagged = flagged.assign(
        site=group_nearby(flagged["latitude"], flagged["longitude"], cell_deg),
        month=flagged["acq_utc"].dt.month,
        year=flagged["acq_utc"].dt.year,
        is_type2=_type_is(flagged, 2),
    )
    g = flagged.groupby("site")
    sites = pd.DataFrame({
        "latitude": g["latitude"].mean(),
        "longitude": g["longitude"].mean(),
        "detections": g.size(),
        "first_date": g["local_date"].min(),
        "last_date": g["local_date"].max(),
        "calendar_months": g["month"].nunique(),
        "years": g["year"].nunique(),
        "type2_share": g["is_type2"].mean(),
        "province": g["province"].agg(_mode),
        "district": g["district"].agg(_mode),
    })
    sites = sites.sort_values(["detections", "latitude"], ascending=[False, True]).reset_index(drop=True)
    sites.insert(0, "site_id", [f"S{i + 1:03d}" for i in range(len(sites))])
    return sites[SITE_COLUMNS]


def _mode(values: pd.Series):
    values = values.dropna()
    return values.mode().iat[0] if len(values) else None


def masks_to_json(masks: Masks, provenance: dict) -> dict:
    return {
        **provenance,
        "cell_deg": masks.cell_deg,
        "static": [[int(a), int(b)] for a, b in masks.static],
        "volcano": [[int(a), int(b)] for a, b in masks.volcano],
    }


def masks_from_json(obj: dict) -> Masks:
    def cells(pairs):
        return _cells([p[0] for p in pairs], [p[1] for p in pairs])

    return Masks(cell_deg=float(obj["cell_deg"]), static=cells(obj["static"]), volcano=cells(obj["volcano"]))
