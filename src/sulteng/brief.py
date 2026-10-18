"""The Indonesian brief: last month and this month, filled from now.json."""

from __future__ import annotations

import html
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sulteng.config import ROOT
from sulteng.summary import MONTHS_ID

TEMPLATE = ROOT / "reports" / "brief" / "ringkasan.html.tmpl"
PERIOD_TEMPLATE = ROOT / "reports" / "brief" / "periode.html.tmpl"
NO_DATA = "<p>Belum ada data satelit untuk periode ini.</p>"
_SWAP = str.maketrans({",": ".", ".": ","})


def fmt_int(n) -> str:
    return f"{int(n):,}".translate(_SWAP)


def fmt_dec(x: float, digits: int = 1) -> str:
    return f"{x:,.{digits}f}".translate(_SWAP)


def fmt_datetime(iso: str, utc_offset_hours: int) -> str:
    moment = datetime.fromisoformat(iso).astimezone(timezone(timedelta(hours=utc_offset_hours)))
    return f"{moment.day} {MONTHS_ID[moment.month - 1]} {moment.year}, pukul {moment:%H.%M} WITA"


def no_data(c: dict) -> bool:
    return c["days"] > 0 and c["missing"] == c["days"]


def coverage_sentence(c: dict) -> str:
    if no_data(c):
        return "Belum ada data satelit untuk periode ini, jadi angkanya belum bisa dipakai."
    if c["complete"] == c["days"]:
        return f"Data satelit lengkap untuk {c['days']} hari dalam periode ini."
    parts = [f"Data satelit lengkap untuk {c['complete']} dari {c['days']} hari"]
    if c["partial"]:
        parts.append(f"{c['partial']} hari hanya sebagian")
    if c["missing"]:
        parts.append(f"{c['missing']} hari tanpa data")
    return ", ".join(parts) + ". Jumlah sebenarnya bisa lebih tinggi."


def _focus(window: dict, focus: str) -> dict:
    return next(p for p in window["provinces"] if p["name"] == focus)["counts"]


def district_rows(window: dict, limit: int = 8) -> str:
    rows = [d for d in window["focus_districts"] if d["counts"]["all"]][:limit]
    if not rows:
        return '<tr><td colspan="3">Tidak ada titik panas yang tercatat.</td></tr>'
    return "".join(
        f'<tr><td>{html.escape(d["district"])}</td><td class="num">{fmt_int(d["counts"]["other"])}</td>'
        f'<td class="num">{fmt_int(d["counts"]["static_suspect"])}</td></tr>'
        for d in rows
    )


def province_rows(window: dict, focus: str) -> str:
    rows = []
    for p in sorted(window["provinces"], key=lambda p: (-p["per_1000_km2"]["other"], p["name"])):
        cls = ' class="focus"' if p["name"] == focus else ""
        rows.append(
            f'<tr{cls}><td>{html.escape(p["name"])}</td>'
            f'<td class="num">{fmt_dec(p["per_1000_km2"]["other"])}</td>'
            f'<td class="num">{fmt_int(p["counts"]["other"])}</td>'
            f'<td class="num">{fmt_int(p["counts"]["static_suspect"])}</td></tr>'
        )
    return "".join(rows)


def period_section(window: dict, focus: str) -> str:
    """One period of the brief; a period without satellite data gets a single sentence."""
    label = html.escape(window["label"])
    if no_data(window["coverage"]):
        return f"<h2>{label}</h2>\n{NO_DATA}"
    counts = _focus(window, focus)
    return string.Template(PERIOD_TEMPLATE.read_text(encoding="utf-8")).substitute(
        label=label,
        focus=html.escape(focus),
        **{k: fmt_int(counts[k]) for k in ("all", "other", "static_suspect", "volcano")},
        coverage=coverage_sentence(window["coverage"]),
        district_rows=district_rows(window),
        province_rows=province_rows(window, focus),
    )


def brief_values(now: dict) -> dict[str, str]:
    focus = now["focus"]
    last, this = now["windows"]["last_month"], now["windows"]["this_month"]
    return {
        "focus": html.escape(focus),
        "generated": fmt_datetime(now["generated_at"], now["utc_offset_hours"]),
        "sensors": html.escape(", ".join(s["name"] for s in now["sensors"])),
        "this_label": html.escape(this["label"]),
        "last_label": html.escape(last["label"]),
        "this_section": period_section(this, focus),
        "last_section": period_section(last, focus),
    }


def render_brief(now: dict, template: str | None = None) -> str:
    text = template if template is not None else Path(TEMPLATE).read_text(encoding="utf-8")
    return string.Template(text).substitute(brief_values(now))
