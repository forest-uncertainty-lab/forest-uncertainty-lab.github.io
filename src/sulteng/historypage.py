"""The fire-history page data: archive years plus the years in the store, as weeks per row, with the
running-week nowcast, the analog-year outlook and each row's level against its own history.

Rows: Indonesia, then each island followed by its provinces. Missing weeks are None (JSON null), never 0.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from sulteng.firehistory import WEEKS, ratio
from sulteng.indonesia import ISLANDS, Indonesia
from sulteng.stats import analog_outlook, jeffreys_vs_history, nowcast
from sulteng.yearstore import OFFSET

RECENT_DAYS = 14  # complete days the nowcast draws from
KNOWN = ("SP", "NRT", "feed")


def _week(day: date) -> int:
    return min((day.timetuple().tm_yday - 1) // 7, WEEKS - 1)


def _week_days(year: int, week: int) -> list[date]:
    first = date(year, 1, 1) + timedelta(days=7 * week)
    last = date(year, 12, 31) if week == WEEKS - 1 else first + timedelta(days=6)
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def _store_daily(store: dict, names: list[str], fallback_ratio: float | None) -> tuple[pd.DataFrame, dict]:
    """Daily weighted counts and FRP per province from the store, and the state of each UTC day."""
    rows = pd.DataFrame(store.get("rows", []), columns=["sensor", "province", "local_date", "utc_date", "count", "frp"])
    fetched = store.get("fetched", {})
    snpp_state, n20_state = fetched.get("N", {}), fetched.get("N20", {})
    gaps = {d for d, s in snpp_state.items() if s.startswith("empty")}
    snpp = rows[rows["sensor"] == "N"]
    n20 = rows[rows["sensor"] == "N20"]
    r = ratio(snpp.groupby("utc_date")["count"].sum(), n20.groupby("utc_date")["count"].sum())
    r = fallback_ratio if r is None else r
    filled = n20[n20["utc_date"].isin(gaps)] if r is not None else n20.iloc[0:0]
    parts = [snpp.assign(weight=1.0), filled.assign(weight=float(r or 0))]
    daily = pd.concat(parts, ignore_index=True)
    daily = daily.assign(count=daily["count"] * daily["weight"], frp=daily["frp"] * daily["weight"])
    daily = daily[daily["province"].isin(names)].groupby(["province", "local_date"], as_index=False)[["count", "frp"]].sum()
    state = {d: "known" for d, s in snpp_state.items() if s in KNOWN}
    state.update({d: "filled" for d in gaps if r is not None and n20_state.get(d) in KNOWN})
    return daily, state


def build_history_page(archive: dict, store: dict, ind: Indonesia, now_utc: datetime) -> dict:
    names = list(archive["provinces"])
    today = (now_utc + timedelta(hours=OFFSET)).date()
    latest = today - timedelta(days=1)
    archive_years = list(archive["years"])
    later = list(range(ind.archive_last + 1, today.year + 1))
    years = archive_years + later
    n_p, n_y = len(names), len(years)
    values = {m: np.full((n_p, n_y, WEEKS), np.nan) for m in ("count", "frp")}
    for m in values:
        values[m][:, :len(archive_years), :] = np.asarray(archive[m], dtype=float)
    filled_days = np.zeros((n_y, WEEKS), dtype=int)
    missing_days = np.zeros((n_y, WEEKS), dtype=int)
    filled_days[:len(archive_years)] = archive["filled_days"]
    missing_days[:len(archive_years)] = archive["missing_days"]

    fallback = archive["ratio"].get(str(ind.archive_last))
    daily, state = _store_daily(store, names, fallback)
    daily = daily[daily["local_date"] <= latest.isoformat()]
    pidx = {p: i for i, p in enumerate(names)}
    running_week = _week(today)
    for year in later:
        yi = years.index(year)
        last_week = running_week if year == today.year else WEEKS - 1
        for w in range(last_week + 1):
            days = [d for d in _week_days(year, w) if d <= latest]
            states = [state.get(d.isoformat()) for d in days]
            filled_days[yi, w] = states.count("filled")
            missing_days[yi, w] = states.count(None)
            if days and states.count(None) == len(days):
                continue  # nothing known about this week: stays None
            for m in values:
                values[m][:, yi, w] = 0.0
        rows = daily[daily["local_date"].str[:4] == str(year)]
        weeks = [_week(date.fromisoformat(d)) for d in rows["local_date"]]
        for m in values:
            known = ~np.isnan(values[m][:, yi, :])
            add = np.zeros((n_p, WEEKS))
            np.add.at(add, (rows["province"].map(pidx).to_numpy(dtype=int), np.asarray(weeks, dtype=int)), rows[m].to_numpy())
            values[m][:, yi, :] = np.where(known, values[m][:, yi, :] + add, np.nan)

    labels = _rows(ind, names)
    rowvals = {m: np.stack([_combine(values[m], idx) for _, idx in labels]) for m in values}
    current = years.index(today.year)
    days_in_week = len(_week_days(today.year, running_week))
    days_seen = (today - _week_days(today.year, running_week)[0]).days
    complete_past = [i for i in range(current) if not np.isnan(rowvals["count"][0, i]).any()]
    recent = [latest - timedelta(days=i) for i in range(RECENT_DAYS)][::-1]
    recent = [d for d in recent if state.get(d.isoformat()) is not None]

    nowcasts, outlooks, unusual = {}, {}, {}
    for m in values:
        by_day = daily.pivot_table(index="local_date", columns="province", values=m, aggfunc="sum")
        nowcasts[m], outlooks[m], unusual[m] = [], [], []
        for (_, idx), series in zip(labels, rowvals[m]):
            cols = [names[i] for i in idx if names[i] in by_day.columns]
            per_day = by_day[cols].sum(axis=1) if cols else pd.Series(dtype=float)
            recent_values = [float(per_day.get(d.isoformat(), 0.0)) for d in recent]
            observed = float(np.nan_to_num(series[current, running_week]))
            q = nowcast(observed, recent_values, days_in_week - days_seen)
            nowcasts[m].append(None if q is None else [round(v, 1) for v in q])
            to_date = float(np.nansum(series[current, :running_week]))
            past_weeks = [series[i] for i in complete_past]
            out = analog_outlook(to_date, past_weeks, running_week)
            outlooks[m].append(None if out is None else _rounded(out))
            unusual[m].append(_unusual(m, to_date, [float(series[i, :running_week].sum()) for i in complete_past]))

    nrt = sorted(d for d, s in store.get("fetched", {}).get("N", {}).items()
                 if d[:4] == str(today.year) and s in ("NRT", "feed", "empty-NRT", "empty-feed"))
    return {
        "generated_at": now_utc.isoformat(timespec="seconds"),
        "latest_day": latest.isoformat(),
        "years": years,
        "nrt_from": nrt[0] if nrt else None,
        "rows": [row for row, _ in labels],
        "count": _public(rowvals["count"], 2),
        "frp": _public(rowvals["frp"], 0),
        "filled_days": filled_days.tolist(),
        "missing_days": missing_days.tolist(),
        "running": {"year": today.year, "week": running_week, "days_seen": days_seen, "days_in_week": days_in_week},
        "nowcast": nowcasts,
        "outlook": outlooks,
        "unusual": unusual,
    }


def _rows(ind: Indonesia, names: list[str]) -> list[tuple[dict, list[int]]]:
    regions = {r.name: r for r in ind.regions}
    out = [({"key": "total", "level": 0, "en": "Indonesia", "id": "Indonesia"}, list(range(len(names))))]
    for island in ISLANDS:
        idx = [i for i, n in enumerate(names) if regions[n].island == island]
        if not idx:
            continue
        out.append(({"key": f"isl:{island}", "level": 1, "en": island, "id": regions[names[idx[0]]].island_id}, idx))
        out += [({"key": f"prov:{names[i]}", "level": 2, "en": regions[names[i]].name_en, "id": names[i]}, [i]) for i in idx]
    return out


def _combine(values: np.ndarray, idx: list[int]) -> np.ndarray:
    """Sum of provinces; None wherever the provinces are None (they share the same missing weeks)."""
    part = values[idx]
    return np.where(np.isnan(part).all(axis=0), np.nan, np.nansum(part, axis=0))


def _unusual(measure: str, to_date: float, past: list[float]) -> dict:
    usual = float(np.median(past)) if past else 0.0
    if measure == "count":
        stats = jeffreys_vs_history(to_date, past)
        ratio_q = None if stats["ratio"] is None else [round(v, 3) for v in stats["ratio"]]
        p = None if stats["p_above_max"] is None else round(stats["p_above_max"], 3)
        return {"to_date": round(to_date, 2), "usual": round(usual, 2), "ratio": ratio_q, "p_above_max": p,
                "rank": stats["rank"], "years": stats["years"]}
    # Fire radiative power is not a count: a plain ratio and rank, without a Poisson interval.
    point = round(to_date / usual, 3) if usual > 0 else None
    return {"to_date": round(to_date), "usual": round(usual), "ratio": None if point is None else [point] * 3,
            "p_above_max": None, "rank": 1 + sum(v > to_date for v in past), "years": len(past) + 1}


def _rounded(out: dict) -> dict:
    return {"year_end": [round(v, 1) for v in out["year_end"]], "p_record": round(out["p_record"], 3),
            "weekly": [[round(v, 1) for v in q] for q in out["weekly"]], "analogs": out["analogs"]}


def _public(values: np.ndarray, digits: int) -> list:
    rounded = np.round(values, digits)
    return [[[None if np.isnan(v) else (int(v) if digits == 0 else float(v)) for v in week] for week in year] for year in rounded]
