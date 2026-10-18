"""Which hours each sensor's downloads covered, and what that means for each WITA day."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

Interval = tuple[datetime, datetime]


def merge(spans: list[Interval]) -> list[Interval]:
    merged: list[Interval] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def intervals(coverage: dict, sensor: str) -> list[Interval]:
    return [(datetime.fromisoformat(a), datetime.fromisoformat(b)) for a, b in coverage.get(sensor, [])]


def _encode(spans: list[Interval]) -> list[list[str]]:
    return [[a.isoformat(), b.isoformat()] for a, b in spans]


def add(coverage: dict, sensor: str, start: datetime, end: datetime) -> dict:
    """Copy of coverage with [start, end) added for sensor."""
    out = dict(coverage)
    out[sensor] = _encode(merge(intervals(coverage, sensor) + [(start, end)]))
    return out


def prune(coverage: dict, before: datetime) -> dict:
    """Copy of coverage without anything earlier than `before`."""
    return {
        sensor: _encode([(max(a, before), b) for a, b in intervals(coverage, sensor) if b > before])
        for sensor in coverage
    }


def feed_interval(last_modified: datetime, span_hours: int, latency_hours: int) -> Interval:
    return last_modified - timedelta(hours=span_hours), last_modified - timedelta(hours=latency_hours)


def day_bounds(day: date, utc_offset_hours: int) -> Interval:
    local = timezone(timedelta(hours=utc_offset_hours))
    start = datetime(day.year, day.month, day.day, tzinfo=local).astimezone(timezone.utc)
    return start, start + timedelta(days=1)


def _status(spans: list[Interval], start: datetime, end: datetime) -> str:
    if any(a <= start and b >= end for a, b in spans):
        return "complete"
    if any(a < end and b > start for a, b in spans):
        return "partial"
    return "missing"


def day_status(coverage: dict, sensors, day: date, utc_offset_hours: int) -> str:
    start, end = day_bounds(day, utc_offset_hours)
    states = {_status(intervals(coverage, s), start, end) for s in sensors}
    if states == {"complete"}:
        return "complete"
    if states == {"missing"}:
        return "missing"
    return "partial"


def backfill_requests(
    coverage: dict, sensor: str, first_day: date, last_day: date, utc_offset_hours: int, max_days: int
) -> list[tuple[date, int]]:
    """(UTC start date, number of days) requests covering every WITA day in range that is not complete."""
    spans = intervals(coverage, sensor)
    needed: set[date] = set()
    day = first_day
    while day <= last_day:
        start, end = day_bounds(day, utc_offset_hours)
        if _status(spans, start, end) != "complete":
            utc_day = start.date()
            while datetime(utc_day.year, utc_day.month, utc_day.day, tzinfo=timezone.utc) < end:
                needed.add(utc_day)
                utc_day += timedelta(days=1)
        day += timedelta(days=1)
    requests: list[tuple[date, int]] = []
    for utc_day in sorted(needed):
        if requests:
            first, count = requests[-1]
            if first + timedelta(days=count) == utc_day and count < max_days:
                requests[-1] = (first, count + 1)
                continue
        requests.append((utc_day, 1))
    return requests
