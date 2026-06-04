# Itinera – Least-Cost Pathways

[![core tests](https://github.com/leiverkus/itinera/actions/workflows/tests.yml/badge.svg)](https://github.com/leiverkus/itinera/actions/workflows/tests.yml)
[![latest release](https://img.shields.io/github/v/release/leiverkus/itinera?sort=semver)](https://github.com/leiverkus/itinera/releases)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![QGIS ≥ 3.28](https://img.shields.io/badge/QGIS-%E2%89%A5%203.28-589632?logo=qgis&logoColor=white)](https://qgis.org)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
![dependencies: numpy · scipy · GDAL](https://img.shields.io/badge/deps-numpy%20%C2%B7%20scipy%20%C2%B7%20GDAL-orange)

Anisotropic least-cost path, corridor (LCC), From-Everywhere-To-Everywhere
(FETE), stochastic (probabilistic) paths and Path Deviation Index (PDI)
validation for QGIS — built for archaeological movement modelling.

No external pip packages required: the numerics use **numpy** and **scipy**,
both bundled with QGIS. Raster I/O uses **GDAL** (also bundled).

## What's inside

| Component | Form | Status |
|---|---|---|
| Slope cost surface (accumulated) | Processing | working |
| Friction cost surface (accumulated) | Processing | working |
| Least-cost path | Processing | working |
| Stochastic LCP (probabilistic corridor) | Processing | working |
| Least-cost corridor (LCC) | Processing | working |
| FETE | Processing | working |
| PDI validation | Processing | working |
| Resample DEM (block mean) | Processing | working |
| Interactive two-click LCP | Toolbar tool | working (cost fn + neighbourhood selectable) |

## Method

Each cell becomes a graph node; edges connect neighbouring cells (4/8/16).
Edge weight is a **directional** cost function (slope = rise/run signed by
travel direction), so the conductance matrix is **asymmetric** = true
anisotropy. Paths are solved with `scipy.sparse.csgraph.dijkstra`.

- **Corridor**: sum of two accumulated surfaces — one from the origin, one
  from the destination grown on the *reversed* graph (correct for anisotropy).
- **FETE**: all pairwise LCPs, traversal frequency per cell (White & Barber
  2012). Cost scales ~O(n²) in the number of points.
- **PDI**: area between modelled and reference polyline / reference length =
  mean deviation in map units.
- **Friction**: a cost-per-metre raster (vegetation, wadis, geology) drives the
  surface directly (isotropic), or — with an optional DEM — acts as a
  dimensionless multiplier on the anisotropic slope cost (combined mode).
- **Barrier / multiplier**: an optional raster on the slope-based algorithms
  (slope cost surface, LCP, LCC, FETE) scales edge cost by the mean of its two
  cells (>1 discourages, <1 prefers known roads); NoData/≤0 cells are
  impassable (cliffs, deep wadis).
- **Stochastic LCP** (Lewis 2021): N Monte-Carlo realisations adding a
  spatially-correlated DEM error (RMSE-scaled) and/or randomly dropping edges,
  accumulating how often each cell lies on the least-cost path → a
  probabilistic corridor in [0, 1]. Set a seed for reproducibility.

Cost functions included: Tobler (on/off-path), Herzog, Naismith, Llobera &
Sluckin. Add your own in `core/cost_functions.py` and register it in the
`COST_FUNCTIONS` dict + labels list.

## Documentation

- **[User manual](docs/MANUAL.md)** — concepts, per-algorithm guide with
  parameters, a worked example, performance/memory notes and troubleshooting.
- **[References](docs/REFERENCES.md)** / **[references.bib](docs/references.bib)**
  — the literature behind each cost function and method.

## Install

1. Zip the `itinera` folder (or use the provided zip).
2. QGIS → Plugins → Manage and Install Plugins → Install from ZIP.
3. Enable **Itinera – Least-Cost Pathways**.
4. Algorithms appear in the Processing Toolbox under *Itinera – Least-Cost
   Pathways*. The interactive tool appears as a toolbar button.

Requires QGIS ≥ 3.28. Use a **projected CRS** in metres (e.g. EPSG:32637 /
EPSG:28191) for DEM and points so slope and distance are metric.

## Tests

The GUI-free `core/` numerics have a pytest suite that runs outside QGIS (no
qgis/GDAL needed):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

It gates on the project invariants — the conductance matrix stays asymmetric,
edge/path costs are finite and positive, friction-only surfaces are symmetric,
and the corridor's transpose contract holds. CI runs the same suite
(`.github/workflows/tests.yml`).

## Notes & limits (v0.5.0)

- The interactive map tool's cost function and neighbourhood are set via its
  "Interactive LCP settings…" toolbar button (defaults: Tobler, 8-neighbour).
- The full conductance matrix is held in memory (~`cells × neighbours` edges).
  The graph algorithms warn above ~4M cells; for very large DEMs, clip or run
  *Resample DEM (block mean)* first (cuts cells by `factor²`). A true tiled
  builder with cross-tile path stitching is out of scope for now.
- 16-neighbour reduces grid metric distortion but quadruples edge count.
- FETE on many points is expensive; start small.

## Roadmap

The original roadmap is complete. Possible future directions — built **as
needed and in response to user feedback**, not committed milestones:

- a true tiled conductance builder with cross-tile path stitching (for DEMs too
  large to hold in memory);
- a FETE-style *stochastic* network (probabilistic all-pairs corridors);
- additional cost functions.

Have a use case that needs one of these, or something else? Please open an
[issue](https://github.com/leiverkus/itinera/issues) — priorities follow demand.

## Versioning, changelog & licence

Versions follow [Semantic Versioning](https://semver.org); `metadata.txt`
`version=` is the single source of truth. Release notes live in
[`CHANGELOG.md`](CHANGELOG.md).

Licensed under the **MIT License** — see [`LICENSE`](LICENSE).

For submitting the plugin to the QGIS plugin repository, see
[`PUBLISHING.md`](PUBLISHING.md).
