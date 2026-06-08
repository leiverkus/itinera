#!/usr/bin/env bash
#
# Build the QGIS plugin ZIP: a single top-level `itinera/` folder containing the
# runtime code, with dev / CI / packaging / PyPI-only files stripped out.
#
# Only *committed* files are included (via `git archive`), so nothing untracked
# (`.venv/`, `__pycache__/`, editor dirs, stray zips) can leak in. The version —
# and the zip name — come from `metadata.txt` at the chosen ref.
#
# Usage:
#   scripts/package-plugin.sh [git-ref]      # default ref: HEAD
#   scripts/package-plugin.sh v0.7.1         # package a specific tag
#
set -euo pipefail

cd "$(dirname "$0")/.."
ref="${1:-HEAD}"

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

# Export the tracked tree at <ref> into <stage>/itinera/.
git archive --prefix=itinera/ "$ref" | ( cd "$stage" && tar -x )

# Strip maintainer / CI / packaging / PyPI-only files from the plugin folder.
( cd "$stage/itinera" && rm -rf \
    .github .gitignore .gitattributes \
    CLAUDE.md PUBLISHING.md README-pypi.md \
    pyproject.toml setup.cfg pytest.ini tox.ini requirements-dev.txt \
    tests Makefile scripts )

version="$(grep -oE '^version=[^[:space:]]+' "$stage/itinera/metadata.txt" \
    | cut -d= -f2)"
out="$(pwd)/itinera-${version}.zip"
rm -f "$out"
( cd "$stage" && zip -r -q "$out" itinera )

echo "Built $out  (ref: $ref)"
