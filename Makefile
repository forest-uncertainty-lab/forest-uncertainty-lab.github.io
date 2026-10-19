.PHONY: test masks refresh site serve all

test:
	uv run pytest -q

masks:
	uv run python scripts/build_masks.py

# uv loads FIRMS_MAP_KEY from .env when the file exists. Only this target gets it.
refresh:
	uv run $(if $(wildcard .env),--env-file .env) python scripts/refresh.py

site:
	uv run python scripts/build_site.py

serve: site
	uv run python -m http.server 8000 -d _site

all: refresh site
