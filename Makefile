.PHONY: test masks refresh site serve all

test:
	uv run pytest -q

masks:
	uv run python scripts/build_masks.py

refresh:
	uv run python scripts/refresh.py

site:
	uv run python scripts/build_site.py

serve: site
	uv run python -m http.server 8000 -d _site

all: refresh site
