import json
from datetime import datetime, timezone

from conftest import make_detections
from sulteng import coverage as cov
from sulteng.brief import coverage_sentence, fmt_datetime, fmt_dec, fmt_int, render_brief
from sulteng.config import load_params
from sulteng.publish import to_public
from sulteng.summary import summarize

PARAMS = load_params()
NOW = datetime(2026, 10, 18, 4, 0, tzinfo=timezone.utc)


def now_json(rows, covered=True):
    det = make_detections([(-1.0, 120.0, utc, None) for _, utc, _ in rows]).drop(columns="type")
    df = det.assign(province="Sulawesi Tengah", district=[d for d, _, _ in rows], category=[c for *_, c in rows])
    c = {}
    if covered:
        for s in PARAMS.sensors:
            c = cov.add(c, s.code, datetime(2026, 8, 31, tzinfo=timezone.utc), NOW)
    areas = {p.name: 1000.0 for p in PARAMS.provinces}
    return json.loads(json.dumps(to_public(summarize(df, c, PARAMS, areas, NOW))))


def test_number_and_date_formats():
    assert fmt_int(12345) == "12.345"
    assert fmt_dec(1234.56) == "1.234,6"
    assert fmt_datetime("2026-10-18T04:00:00+00:00", 8) == "18 Oktober 2026, pukul 12.00 WITA"


def test_coverage_sentences():
    assert "lengkap untuk 30 hari" in coverage_sentence({"days": 30, "complete": 30, "partial": 0, "missing": 0})
    assert "Belum ada data" in coverage_sentence({"days": 30, "complete": 0, "partial": 0, "missing": 30})
    text = coverage_sentence({"days": 30, "complete": 20, "partial": 1, "missing": 9})
    assert "20 dari 30" in text and "9 hari tanpa data" in text


def test_render_fills_everything_and_escapes():
    page = render_brief(now_json([("<script>x</script>", "2026-09-10 05:00", "other"),
                                  ("Morowali", "2026-09-11 05:00", "static_suspect")]))
    assert "$" not in page
    assert "DRAF" in page and "Sulawesi Tengah" in page and "September 2026" in page
    assert "<script>x" not in page and "&lt;script&gt;" in page


def test_period_without_data_gets_one_sentence_not_empty_bullets():
    page = render_brief(now_json([], covered=False))
    assert page.count("Belum ada data satelit untuk periode ini.") == 2
    assert "mencatat" not in page and "<table>" not in page


def test_this_month_comes_first_and_both_periods_get_tables():
    page = render_brief(now_json([("Poso", "2026-10-05 05:00", "other"), ("Poso", "2026-09-05 05:00", "other")]))
    assert page.index("Oktober 2026") < page.index("<h2>September 2026")
    assert page.count("<th>Kabupaten/kota</th>") == 2
    assert page.count("<th>Provinsi</th>") == 2
