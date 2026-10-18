# Data Sources and Backlog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refuse FIRMS archive files that predate the May 2025 fire-type fix, and record the data-source decisions and every open action item in one backlog.

**Architecture:** A pure check `fetch.stale_inputs()` compares each archive file's server date with a configured cutoff; `scripts/build_masks.py` stops when any archive file is older or undated. The decisions and action items go into `docs/backlog.md`, linked from the spec and README.

**Tech Stack:** Python 3.11+, pytest, uv (unchanged).

**Spec:** `docs/superpowers/specs/2026-10-18-sp1-fire-monitor-now-design.md` (design approved in chat on 2026-10-19: archive vintage guard, backlog, spec §3 note, README link).

## Global Constraints

- The cutoff lives only in `config/params.toml` as `archive_min_last_modified = "2025-06-01"`; no default in code.
- `docs/backlog.md` states claims taken from the user's data-source review as "per the review" unless checked in this repo.
- The public site never calls Earth Engine, GWIS or Open-Meteo.
- Commits are local; no `Co-Authored-By` or Claude attribution lines.

## Review Focus

1. An archive file whose server sent no `Last-Modified` header must count as stale, not as fresh. Pinned in Task 1 (`test_stale_inputs_flags_old_and_undated_files`).
2. A malformed cutoff in `params.toml` must fail at load time with the key named. Pinned in Task 1 (`test_rejects_malformed_archive_cutoff`).
3. Boundary files (geoBoundaries) must not be checked against the FIRMS cutoff. Pinned by the `viirs-snpp_` filter in Task 1 Step 5 and checked in Step 7 on real data.

---

### Task 1: Archive vintage guard

**Files:**
- Modify: `config/params.toml` (`[masks]`), `src/sulteng/config.py` (`MaskParams`, `load_params`, `_validate`), `src/sulteng/fetch.py`, `scripts/build_masks.py`, `tests/test_masks.py:7` (MaskParams construction)
- Test: `tests/test_fetch.py`, `tests/test_config.py`
- Regenerated: `data/public/masks.json`, `data/public/manifest.json`, `data/public/static_sites.geojson`, `data/boundaries/*.geojson`, `data/public/*.geojson`, `reports/static_review.md`

**Interfaces:**
- Produces: `MaskParams.archive_min_last_modified: str` (ISO date); `fetch.stale_inputs(entries: list[dict], min_last_modified: str) -> list[str]` returning the `file` names whose `last_modified` is missing or earlier than the cutoff (00:00 UTC), in input order.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fetch.py` (and add `stale_inputs` to its `from sulteng.fetch import ...` line):

```python
def test_stale_inputs_flags_old_and_undated_files():
    entries = [
        {"file": "viirs-snpp_2023_Indonesia.csv", "last_modified": "2025-06-24T17:07:37+00:00"},
        {"file": "viirs-snpp_2022_Indonesia.csv", "last_modified": "2025-03-02T10:00:00+00:00"},
        {"file": "viirs-snpp_2021_Indonesia.csv", "last_modified": None},
        {"file": "viirs-snpp_2020_Indonesia.csv", "last_modified": "2025-06-01T00:00:00+00:00"},
    ]
    assert stale_inputs(entries, "2025-06-01") == ["viirs-snpp_2022_Indonesia.csv", "viirs-snpp_2021_Indonesia.csv"]
```

Append to `tests/test_config.py`:

```python
def test_archive_cutoff_is_loaded():
    assert load_params().masks.archive_min_last_modified == "2025-06-01"


def test_rejects_malformed_archive_cutoff(tmp_path):
    text = DEFAULT_PARAMS.read_text().replace('archive_min_last_modified = "2025-06-01"', 'archive_min_last_modified = "June 2025"')
    path = tmp_path / "params.toml"
    path.write_text(text)
    with pytest.raises(ValueError, match="archive_min_last_modified"):
        load_params(path)
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_fetch.py tests/test_config.py -q`
Expected: FAIL; `ImportError: cannot import name 'stale_inputs'` for test_fetch, and `KeyError`/`AttributeError` for the config tests.

- [ ] **Step 3: Add the setting**

In `config/params.toml`, `[masks]` section, after `min_years = 2`:

```toml
# FIRMS reprocessed the VIIRS fire-type codes (1 = volcano, 2 = static source) in May 2025.
# Archive files dated earlier may carry the faulty codes; build_masks.py refuses them.
archive_min_last_modified = "2025-06-01"
```

In `src/sulteng/config.py`: add `from datetime import date` to the imports; add the field as the last field of `MaskParams`:

```python
    archive_min_last_modified: str  # ISO date; older archive files predate the FIRMS fire-type fix
```

in `load_params`, inside `MaskParams(...)`:

```python
            archive_min_last_modified=str(mk["archive_min_last_modified"]),
```

and at the end of `_validate`:

```python
    try:
        date.fromisoformat(m.archive_min_last_modified)
    except ValueError as exc:
        raise ValueError(f"archive_min_last_modified must be an ISO date (YYYY-MM-DD): {exc}") from exc
```

In `tests/test_masks.py`, the `MP = MaskParams(...)` line gains `archive_min_last_modified="2025-06-01"`.

- [ ] **Step 4: Add `stale_inputs` to `src/sulteng/fetch.py`**

```python
def stale_inputs(entries: list[dict], min_last_modified: str) -> list[str]:
    """Files whose server date is missing or earlier than `min_last_modified` (YYYY-MM-DD, 00:00 UTC)."""
    cutoff = datetime.fromisoformat(min_last_modified).replace(tzinfo=timezone.utc)
    return [
        e["file"] for e in entries
        if not e.get("last_modified") or datetime.fromisoformat(e["last_modified"]) < cutoff
    ]
```

- [ ] **Step 5: Enforce it in `scripts/build_masks.py`**

Import `stale_inputs` from `sulteng.fetch`. In `main()`, right after `inputs = fetch_inputs(params, args.force)`:

```python
    archives = [e for e in inputs if e["file"].startswith("viirs-snpp_")]
    stale = stale_inputs(archives, params.masks.archive_min_last_modified)
    if stale:
        raise SystemExit(
            f"These archive files are dated before {params.masks.archive_min_last_modified} and may carry the "
            f"FIRMS fire-type codes fixed in May 2025: {', '.join(stale)}. Download them again with "
            "`uv run python scripts/build_masks.py --force`; if FIRMS still serves an older file, do not build masks from it."
        )
```

and add `"archive_min_last_modified": params.masks.archive_min_last_modified,` to the `rule` dict.

- [ ] **Step 6: Run the tests and the suite**

Run: `uv run pytest tests/test_fetch.py tests/test_config.py -q && uv run pytest -q`
Expected: the new tests pass; full suite passes (76 tests).

- [ ] **Step 7: Rebuild the masks on real data**

Run: `uv run python scripts/build_masks.py`
Expected: no SystemExit (archive files are dated 2025-06-24 and 2026-10-10); the same province table as before; `grep archive_min_last_modified data/public/manifest.json` finds the rule. `git diff --stat data/` shows only `built_at`/`rule`/code-version changes plus regenerated files.

- [ ] **Step 8: Commit**

```bash
git add config/params.toml src/sulteng/config.py src/sulteng/fetch.py scripts/build_masks.py tests data reports/static_review.md
git commit -m "Refuse FIRMS archive files that predate the May 2025 fire-type fix"
```

---

### Task 2: Backlog and data-source decisions

**Files:**
- Create: `docs/backlog.md`
- Modify: `docs/superpowers/specs/2026-10-18-sp1-fire-monitor-now-design.md` (§3), `README.md` (Data and Design sections)

- [ ] **Step 1: Write `docs/backlog.md`**

Content: a "Data sources" section with the decision table (FIRMS in use; Google Earth Engine in SP2, exports only, verified noncommercial project needed; Copernicus GWIS optional in SP3, not independent of FIRMS for active fire; Open-Meteo only if the NGO asks; NIFC not used), the FIRMS limit (5,000 map-key transactions per 10 minutes; a refresh makes at most about 30 API requests), the fire-type note with the file dates actually used, and the order of work (FIRMS evidence → Earth Engine checks on a small sample → brief → uncertainty experiment). Then numbered action items with owners (TL technical lead, NGO reviewer, OL outreach lead): to go live (FIRMS key, merge decision, repository and Pages, share image); before public (NGO wording review and DRAF removal, static-site review, governance agreement, private stakeholder list, confirm the FIRMS notice); upkeep (yearly `make masks`); SP2 (Earth Engine project, SP2 spec, 3–5 case stories); SP3 (G0-01, G0-04, G0-03 and G0-05, G0 amendment, R2 study, optional GWIS, report and outreach); later (Open-Meteo, forest-area denominator); deferred code items from the 2026-10-19 review (4xx retries, WITA months in masks, coverage parsing, double categorize, duplicate JSON loader).

- [ ] **Step 2: Link it**

Spec §3, after the paragraph under the sources table, add:

```markdown
Other sources considered on 2026-10-19 (Google Earth Engine for SP2, Copernicus GWIS as an optional cross-check, Open-Meteo only if the NGO asks, NIFC not used) and the reasons are in `docs/backlog.md`. Archive files must postdate FIRMS's May 2025 reprocessing of the VIIRS `type` field; `scripts/build_masks.py` enforces `archive_min_last_modified` from `config/params.toml`.
```

README: after the key paragraph in "Data", add "`make masks` refuses archive files dated before 2025-06-01, when FIRMS fixed the VIIRS fire-type codes the masks rely on."; in "Design and plan", add "- Action items and data-source decisions: `docs/backlog.md`".

- [ ] **Step 3: Check every path the backlog names exists**

Run: `grep -o '`[a-z_./-]*\.\(py\|md\|toml\|html\|tmpl\)`' docs/backlog.md | tr -d '`' | sort -u | while read f; do [ -e "$f" ] || echo "missing: $f"; done; echo checked`
Expected: `checked` with no `missing:` lines.

- [ ] **Step 4: Commit**

```bash
git add docs/backlog.md docs/superpowers/specs/2026-10-18-sp1-fire-monitor-now-design.md README.md
git commit -m "Add backlog with data-source decisions and open action items"
```
