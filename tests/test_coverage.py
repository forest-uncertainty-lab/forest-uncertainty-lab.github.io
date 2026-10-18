from datetime import date, datetime, timezone

from sulteng import coverage as cov


def t(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def test_add_merges_overlaps():
    c = cov.add({}, "N", t("2026-10-01T00:00"), t("2026-10-02T00:00"))
    c = cov.add(c, "N", t("2026-10-01T12:00"), t("2026-10-03T00:00"))
    c = cov.add(c, "N", t("2026-10-05T00:00"), t("2026-10-06T00:00"))
    assert cov.intervals(c, "N") == [
        (t("2026-10-01T00:00"), t("2026-10-03T00:00")),
        (t("2026-10-05T00:00"), t("2026-10-06T00:00")),
    ]


def test_day_status_uses_wita_days():
    # WITA 2 Oct runs from 1 Oct 16:00 UTC to 2 Oct 16:00 UTC
    c = cov.add({}, "N", t("2026-10-01T16:00"), t("2026-10-02T16:00"))
    assert cov.day_status(c, ["N"], date(2026, 10, 2), 8) == "complete"
    assert cov.day_status(c, ["N"], date(2026, 10, 3), 8) == "missing"
    c = cov.add(c, "N", t("2026-10-02T16:00"), t("2026-10-03T00:00"))
    assert cov.day_status(c, ["N"], date(2026, 10, 3), 8) == "partial"


def test_day_is_partial_when_one_sensor_is_missing():
    c = cov.add({}, "N", t("2026-10-01T00:00"), t("2026-10-05T00:00"))
    assert cov.day_status(c, ["N", "N20"], date(2026, 10, 2), 8) == "partial"
    c = cov.add(c, "N20", t("2026-10-01T00:00"), t("2026-10-05T00:00"))
    assert cov.day_status(c, ["N", "N20"], date(2026, 10, 2), 8) == "complete"


def test_feed_interval():
    start, end = cov.feed_interval(t("2026-10-18T12:00"), span_hours=156, latency_hours=3)
    assert (start, end) == (t("2026-10-12T00:00"), t("2026-10-18T09:00"))


def test_prune_cuts_old_parts():
    c = cov.add({}, "N", t("2026-08-20T00:00"), t("2026-09-10T00:00"))
    c = cov.add(c, "N20", t("2026-08-01T00:00"), t("2026-08-10T00:00"))
    c = cov.prune(c, t("2026-08-31T16:00"))
    assert cov.intervals(c, "N") == [(t("2026-08-31T16:00"), t("2026-09-10T00:00"))]
    assert cov.intervals(c, "N20") == []


def test_backfill_requests_cover_incomplete_wita_days_in_chunks():
    # complete for WITA 1-3 Oct; WITA 4-10 Oct need data, i.e. UTC dates 3-10 Oct
    c = cov.add({}, "N", t("2026-09-30T16:00"), t("2026-10-03T16:00"))
    requests = cov.backfill_requests(c, "N", date(2026, 10, 1), date(2026, 10, 10), 8, max_days=5)
    assert requests == [(date(2026, 10, 3), 5), (date(2026, 10, 8), 3)]


def test_backfill_requests_empty_when_complete():
    c = cov.add({}, "N", t("2026-09-30T16:00"), t("2026-10-03T16:00"))
    assert cov.backfill_requests(c, "N", date(2026, 10, 1), date(2026, 10, 3), 8, max_days=5) == []
