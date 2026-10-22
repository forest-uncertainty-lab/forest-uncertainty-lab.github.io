"""The statistics behind the fire history: how unusual a count is, the running week, the rest of the year.

All intervals are 80% (10th, 50th and 90th percentiles). Random draws use a fixed seed so every
build of the same data gives the same numbers.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

QUANTILES = (10, 50, 90)


def _q(values) -> tuple[float, float, float]:
    return tuple(float(v) for v in np.percentile(values, QUANTILES))


def jeffreys_vs_history(count: float, past: Sequence[float], *, draws: int = 20000, seed: int = 0) -> dict:
    """How this year's count compares with past years over the same weeks.

    The underlying level gets a Gamma(count + 1/2, 1) posterior (Poisson counts, Jeffreys prior), so a
    province with a handful of detections gets a wide interval rather than a noisy extreme.
    `ratio` is that level over the median of past years (None when the median is 0); `p_above_max`
    is the probability the level is above the highest past year; `rank` 1 means no past year was higher.
    """
    past = np.asarray(past, dtype=float)
    level = np.random.default_rng(seed).gamma(count + 0.5, 1.0, draws)
    usual = float(np.median(past)) if len(past) else 0.0
    return {
        "ratio": _q(level / usual) if usual > 0 else None,
        "p_above_max": float((level > past.max()).mean()) if len(past) else None,
        "rank": 1 + int((past > count).sum()),
        "years": len(past) + 1,
    }


def nowcast(observed: float, recent_daily: Sequence[float], days_left: int, *, draws: int = 4000,
            seed: int = 0, poisson: bool = True) -> tuple[float, float, float] | None:
    """The full week from the days seen so far plus the days still to come.

    Bayesian bootstrap: each draw weights the recent complete days with Dirichlet(1, ..., 1) weights to
    get a daily rate. Counts use Poisson draws for remaining days; continuous power uses the
    weighted rate directly so a change of units does not change uncertainty. None without recent days.
    """
    if days_left <= 0:
        return (float(observed),) * 3
    recent = np.asarray(recent_daily, dtype=float)
    if not len(recent):
        return None
    rng = np.random.default_rng(seed)
    rate = rng.dirichlet(np.ones(len(recent)), draws) @ recent
    remaining = rng.poisson(rate * days_left) if poisson else rate * days_left
    return _q(observed + remaining)


def analog_outlook(to_date: float, past_weeks: Sequence[Sequence[float]], from_week: int) -> dict | None:
    """The rest of the year if it follows one of the past years, scaled to this year's level.

    Each past year with detections before `from_week` is scaled by this year's total so far over that
    year's total over the same weeks; its remaining weeks, scaled, are one possible future.
    """
    futures, ends = [], []
    records = [float(sum(year)) for year in past_weeks]
    for year in past_weeks:
        before = float(sum(year[:from_week]))
        if before <= 0:
            continue
        rest = np.asarray(year[from_week:], dtype=float) * (to_date / before)
        futures.append(rest)
        ends.append(to_date + rest.sum())
    if not futures:
        return None
    futures = np.vstack(futures)
    return {
        "year_end": _q(ends),
        "p_record": float(np.mean(np.asarray(ends) > max(records))),
        "weekly": [_q(futures[:, w]) for w in range(futures.shape[1])],
        "analogs": len(ends),
    }
