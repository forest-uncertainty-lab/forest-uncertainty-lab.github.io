.PHONY: test masks history refresh site serve all g0

# Python 3.13 skips .pth files that carry the macOS "hidden" flag, and file-sync apps set that flag
# on everything inside .venv when the project sits in a synced folder such as ~/Desktop. The
# editable install then disappears, so put src/ on the path directly.
export PYTHONPATH := $(CURDIR)/src$(if $(PYTHONPATH),:$(PYTHONPATH))

test:
	uv run pytest -q

masks:
	uv run python scripts/build_masks.py

# G0-01 and G0-04 research checks; the yearly archive files go to ARCHIVE_DIR (about 260 MB).
ARCHIVE_DIR ?= data/raw
g0:
	uv run python scripts/g0_checks.py --archive-dir $(ARCHIVE_DIR)

# Weekly fire history of all 34 provinces from the yearly archive; Suomi NPP and NOAA-20 files go to ARCHIVE_DIR.
history:
	uv run python scripts/build_history.py --archive-dir $(ARCHIVE_DIR)

# uv loads FIRMS_MAP_KEY from .env when the file exists. Only this target gets it.
refresh:
	uv run $(if $(wildcard .env),--env-file .env) python scripts/refresh.py

site:
	uv run python scripts/build_site.py

serve: site
	uv run python -m http.server 8000 -d _site

all: refresh site
