"""Project parameters, loaded from config/params.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARAMS = ROOT / "config" / "params.toml"


@dataclass(frozen=True)
class Province:
    source_name: str  # shapeName in geoBoundaries ADM1 (English)
    name: str  # Indonesian name, used in every output
    island: str


@dataclass(frozen=True)
class Sensor:
    code: str
    name: str
    feed_url: str  # keyless 7-day regional CSV
    api_source: str  # FIRMS area API source


@dataclass(frozen=True)
class MaskParams:
    archive_years: tuple[int, ...]
    cell_deg: float
    min_calendar_months: int
    min_years: int
    archive_min_last_modified: str  # ISO date; older archive files predate the FIRMS fire-type fix


@dataclass(frozen=True)
class Params:
    focus_province: str
    utc_offset_hours: int
    archive_url: str
    adm1_url: str
    adm2_url: str
    api_url: str
    api_days_per_request: int
    masks: MaskParams
    sensors: tuple[Sensor, ...]
    provinces: tuple[Province, ...]

    def archive_url_for(self, year: int) -> str:
        return self.archive_url.format(year=year)


def load_params(path: Path | str = DEFAULT_PARAMS) -> Params:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    src, mk = raw["sources"], raw["masks"]
    params = Params(
        focus_province=raw["focus_province"],
        utc_offset_hours=int(raw["utc_offset_hours"]),
        archive_url=src["archive_url"],
        adm1_url=src["adm1_url"],
        adm2_url=src["adm2_url"],
        api_url=src["api_url"],
        api_days_per_request=int(src["api_days_per_request"]),
        masks=MaskParams(
            archive_years=tuple(int(y) for y in mk["archive_years"]),
            cell_deg=float(mk["cell_deg"]),
            min_calendar_months=int(mk["min_calendar_months"]),
            min_years=int(mk["min_years"]),
            archive_min_last_modified=str(mk["archive_min_last_modified"]),
        ),
        sensors=tuple(Sensor(**s) for s in raw["sensors"]),
        provinces=tuple(Province(**p) for p in raw["provinces"]),
    )
    _validate(params)
    return params


def _validate(p: Params) -> None:
    names = [q.name for q in p.provinces]
    if len(names) != 11 or len(set(names)) != 11:
        raise ValueError(f"expected 11 distinct provinces, found {len(set(names))}")
    if p.focus_province not in names:
        raise ValueError(f"focus province {p.focus_province!r} is not in the province list")
    codes = [s.code for s in p.sensors]
    if not codes or len(set(codes)) != len(codes):
        raise ValueError("sensor codes must be present and distinct")
    if "{year}" not in p.archive_url:
        raise ValueError("archive_url must contain {year}")
    if not 1 <= p.api_days_per_request <= 10:
        raise ValueError("api_days_per_request must be between 1 and 10")
    m = p.masks
    if not 0 < m.cell_deg < 0.1:
        raise ValueError("cell_deg must be between 0 and 0.1 degrees")
    if not 1 <= m.min_calendar_months <= 12 or m.min_years < 1:
        raise ValueError("min_calendar_months must be 1-12 and min_years at least 1")
    try:
        date.fromisoformat(m.archive_min_last_modified)
    except ValueError as exc:
        raise ValueError(f"archive_min_last_modified must be an ISO date (YYYY-MM-DD): {exc}") from exc
