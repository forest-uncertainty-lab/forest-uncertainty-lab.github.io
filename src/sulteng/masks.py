"""Static-source and volcano masks from the archive, and the category of each detection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import shapely

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


def _wita_month_year(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Calendar month and year of each detection's WITA date (night passes fall on the previous UTC day)."""
    local = df["local_date"].str
    return local[5:7].astype(int).to_numpy(), local[:4].astype(int).to_numpy()


def within_years(df: pd.DataFrame, years) -> pd.DataFrame:
    """Rows whose WITA date falls in one of `years`. The yearly FIRMS files are cut at UTC midnight,
    so the last file's final night passes belong to the next WITA year."""
    _, year = _wita_month_year(df)
    return df[np.isin(year, list(years))]


def pooled_cell_stats(df: pd.DataFrame, cell_deg: float) -> pd.DataFrame:
    """For each cell: distinct WITA calendar months and years with detections in its 3×3 neighbourhood."""
    idx = cell_index(df, cell_deg)
    month, year = _wita_month_year(df)
    base = pd.DataFrame({
        "iy": idx.get_level_values("iy"),
        "ix": idx.get_level_values("ix"),
        "month": month,
        "year": year,
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
# Every site ID ever issued, with the point where it was issued: active, merged (into another ID) or gone.
SITE_ID_COLUMNS = ["site_id", "latitude", "longitude", "status", "merged_into"]


def static_sites(categorized: pd.DataFrame, cell_deg: float, site_ids: pd.DataFrame | None = None):
    """Static-suspect detections grouped into sites, largest first, and the updated site ID register.

    IDs stay with places. Each registered ID claims the site holding the flagged detection nearest its
    point, if one lies within 2 × cell_deg (the distance that joins detections into one site). A site
    claimed by several IDs keeps the lowest; the others are marked merged into it. An ID that claims
    nothing is marked gone and is never issued again. Unclaimed sites get new numbers.
    """
    known = pd.DataFrame(columns=SITE_ID_COLUMNS) if site_ids is None else site_ids[SITE_ID_COLUMNS]
    flagged = categorized[categorized["category"] == "static_suspect"].reset_index(drop=True)
    if flagged.empty:
        return pd.DataFrame(columns=SITE_COLUMNS), known.assign(status="gone", merged_into="")
    month, year = _wita_month_year(flagged)
    flagged = flagged.assign(
        site=group_nearby(flagged["latitude"], flagged["longitude"], cell_deg),
        month=month,
        year=year,
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
    }).sort_values(["detections", "latitude"], ascending=[False, True])

    known = known.assign(site=_claimed_sites(known, flagged, cell_deg), number=_id_number(known["site_id"]))
    known = known.sort_values("number")
    owner = known[known["site"] >= 0].groupby("site")["site_id"].first()
    winner = known["site"].map(owner).fillna("")
    known["status"] = np.select([known["site"] < 0, winner == known["site_id"]], ["gone", "active"], default="merged")
    known["merged_into"] = winner.where(known["status"] == "merged", "")

    sites["site_id"] = sites.index.map(owner).astype(object)
    new = sites["site_id"].isna()
    start = int(known["number"].max()) + 1 if len(known) else 1
    sites.loc[new, "site_id"] = [f"S{start + i:03d}" for i in range(int(new.sum()))]
    issued = sites.loc[new, ["site_id", "latitude", "longitude"]].assign(status="active", merged_into="")
    register = pd.concat([known[SITE_ID_COLUMNS], issued], ignore_index=True)
    return sites[SITE_COLUMNS].reset_index(drop=True), register


def _claimed_sites(known: pd.DataFrame, flagged: pd.DataFrame, cell_deg: float) -> np.ndarray:
    """Site label of the flagged detection nearest each registered point, or -1 if none is within 2 × cell_deg."""
    claimed = np.full(len(known), -1, dtype=np.int64)
    if known.empty:
        return claimed
    tree = shapely.STRtree(shapely.points(flagged["longitude"].to_numpy(), flagged["latitude"].to_numpy()))
    points = shapely.points(known["longitude"].to_numpy(dtype=float), known["latitude"].to_numpy(dtype=float))
    which, nearest = tree.query_nearest(points, max_distance=2 * cell_deg, all_matches=False)
    claimed[which] = flagged["site"].to_numpy()[nearest]
    return claimed


def _id_number(site_id: pd.Series) -> pd.Series:
    return site_id.str[1:].astype(int)


def site_ids_from_features(features: list[dict]) -> pd.DataFrame:
    """A site ID register started from published static_sites.geojson features, every site active."""
    rows = [
        (f["properties"]["site_id"], f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0], "active", "")
        for f in features
    ]
    return pd.DataFrame(rows, columns=SITE_ID_COLUMNS)


def read_site_ids(path: Path | str) -> pd.DataFrame:
    text = {"site_id": str, "status": str, "merged_into": str}
    return pd.read_csv(path, dtype=text, keep_default_na=False)[SITE_ID_COLUMNS]


def write_site_ids(site_ids: pd.DataFrame, path: Path | str) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".part")
    site_ids[SITE_ID_COLUMNS].to_csv(tmp, index=False, float_format="%.4f")
    os.replace(tmp, path)


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
