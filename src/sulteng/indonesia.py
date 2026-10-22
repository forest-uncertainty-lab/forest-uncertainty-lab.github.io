"""All of Indonesia for the fire history, and the haze cities, loaded from config/indonesia.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from sulteng.config import ROOT, Province

INDONESIA_CONFIG = ROOT / "config" / "indonesia.toml"
ISLANDS = ("Sumatra", "Java", "Bali and Nusa Tenggara", "Kalimantan", "Sulawesi", "Maluku and Papua")


@dataclass(frozen=True)
class Region:
    source_name: str  # shapeName in geoBoundaries ADM1
    name: str  # Indonesian name, the key in every output
    name_en: str
    island: str
    island_id: str


@dataclass(frozen=True)
class City:
    key: str
    name: str
    lat: float
    lon: float
    utc_offset: int
    tz: str
    country: str  # sg, my or id: picks the official air-quality link


@dataclass(frozen=True)
class Indonesia:
    regions: tuple[Region, ...]
    cities: tuple[City, ...]
    archive_first: int
    archive_last: int
    area_bbox: str
    map_bbox: tuple[float, float, float, float]

    def provinces(self) -> tuple[Province, ...]:
        """The regions in the shape `boundaries.load_provinces` expects."""
        return tuple(Province(source_name=r.source_name, name=r.name, island=r.island) for r in self.regions)


def load_indonesia(path: Path | str = INDONESIA_CONFIG) -> Indonesia:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    ind = Indonesia(
        regions=tuple(Region(**r) for r in raw["regions"]),
        cities=tuple(City(**{**c, "lat": float(c["lat"]), "lon": float(c["lon"])}) for c in raw["cities"]),
        archive_first=int(raw["archive_first"]),
        archive_last=int(raw["archive_last"]),
        area_bbox=str(raw["area_bbox"]),
        map_bbox=tuple(float(v) for v in raw["map_bbox"]),
    )
    unknown = sorted({r.island for r in ind.regions} - set(ISLANDS))
    if unknown:
        raise ValueError(f"unknown island(s) in {path}: {', '.join(unknown)}")
    for field in ("source_name", "name"):
        values = [getattr(r, field) for r in ind.regions]
        if len(set(values)) != len(values):
            raise ValueError(f"duplicate region {field} in {path}")
    if len({c.key for c in ind.cities}) != len(ind.cities):
        raise ValueError(f"duplicate city key in {path}")
    if ind.archive_first > ind.archive_last:
        raise ValueError("archive_first must not be after archive_last")
    return ind
