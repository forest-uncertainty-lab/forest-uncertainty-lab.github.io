#!/usr/bin/env bash
# Restore data/live from the data-store branch before a refresh.
# Start empty only when the branch does not exist yet. Any other failure stops the run,
# so the later force-push can never overwrite the stored months with a near-empty store.
set -euo pipefail
dest="${1:-data/live}"
mkdir -p "$dest"
set +e
git ls-remote --exit-code --heads origin data-store > /dev/null
found=$?
set -e
case $found in
  0)
    git fetch -q --depth=1 origin data-store
    git archive FETCH_HEAD | tar -x -C "$dest"
    ;;
  2)
    echo "No data-store branch yet; starting empty."
    ;;
  *)
    echo "Cannot read origin (git ls-remote exit $found); stopping so the stored data is not overwritten." >&2
    exit 1
    ;;
esac
