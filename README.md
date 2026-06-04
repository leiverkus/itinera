# Itinera – Least-Cost Pathways

Anisotropic least-cost path, corridor (LCC), From-Everywhere-To-Everywhere
(FETE) and Path Deviation Index (PDI) validation for QGIS — built for
archaeological movement modelling.

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
| Interactive two-click LCP | Toolbar tool | working (Tobler, 8-neighbour) |

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
- **Stochastic LCP** (Lewis 2023): N Monte-Carlo realisations adding a
  spatially-correlated DEM error (RMSE-scaled) and/or randomly dropping edges,
  accumulating how often each cell lies on the least-cost path → a
  probabilistic corridor in [0, 1]. Set a seed for reproducibility.

Cost functions included: Tobler (on/off-path), Herzog, Naismith, Llobera &
Sluckin. Add your own in `core/cost_functions.py` and register it in the
`COST_FUNCTIONS` dict + labels list.

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

## Notes & limits (v0.3.0)

- The interactive map tool is hard-wired to Tobler + 8-neighbour; the
  Processing algorithms expose all cost functions and neighbourhoods.
- The full conductance matrix is held in memory. For very large DEMs, clip or
  resample first. A windowed/tiled builder is the obvious next step.
- 16-neighbour reduces grid metric distortion but quadruples edge count.
- FETE on many points is expensive; start small.

## Roadmap

- Map-click UI exposing cost function + neighbourhood choice

## Versioning, changelog & licence

Versions follow [Semantic Versioning](https://semver.org); `metadata.txt`
`version=` is the single source of truth. Release notes live in
[`CHANGELOG.md`](CHANGELOG.md).

Licensed under the **MIT License** — see [`LICENSE`](LICENSE).

For submitting the plugin to the QGIS plugin repository, see
[`PUBLISHING.md`](PUBLISHING.md).
