# Itinera – Least-Cost Pathways

[![core tests](https://github.com/leiverkus/itinera/actions/workflows/tests.yml/badge.svg)](https://github.com/leiverkus/itinera/actions/workflows/tests.yml)
[![release](https://img.shields.io/badge/release-v0.14.1-2ea44f)](https://github.com/leiverkus/itinera/releases)
[![PyPI](https://img.shields.io/pypi/v/itinera?logo=pypi&logoColor=white&label=PyPI)](https://pypi.org/project/itinera/)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![QGIS 3.28+ and 4.0](https://img.shields.io/badge/QGIS-3.28%2B%20%C2%B7%204.0-589632?logo=qgis&logoColor=white)](https://qgis.org)
[![Qt5 / Qt6 ready](https://img.shields.io/badge/Qt-5%20%2F%206%20ready-41cd52?logo=qt&logoColor=white)](https://www.qt.io)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
![dependencies: numpy · scipy · GDAL](https://img.shields.io/badge/deps-numpy%20%C2%B7%20scipy%20%C2%B7%20GDAL-orange)

Anisotropic least-cost path, corridor (LCC), From-Everywhere-To-Everywhere
(FETE), stochastic (probabilistic) paths, sensitivity analysis and route
validation (Path Deviation Index + buffer overlap) for QGIS — built for
archaeological movement modelling.

No external pip packages required: the numerics use **numpy** and **scipy**,
both bundled with QGIS. Raster I/O uses **GDAL** (also bundled).

## What's inside

| Component | Form | Status |
|---|---|---|
| Slope cost surface (accumulated) | Processing | working |
| Friction cost surface (accumulated) | Processing | working |
| Composite friction (multi-criteria) | Processing | working |
| Accessibility / cost catchment | Processing | working |
| Least-cost path | Processing | working |
| Stochastic LCP (probabilistic corridor) | Processing | working |
| Least-cost corridor (LCC) | Processing | working |
| FETE | Processing | working |
| Randomized shortest paths (RSP) | Processing | working |
| Circuit current density / pinch points | Processing | working |
| Connectivity barriers / restoration | Processing | working |
| Sensitivity analysis (cost fn × connectivity) | Processing | working |
| PDI validation | Processing | working |
| Buffer-overlap validation | Processing | working |
| Resample DEM (block mean) | Processing | working |
| DEM error realisation | Processing | working |
| Interactive two-click LCP | Toolbar tool | working (cost fn + neighbourhood selectable) |

## Method

Each cell becomes a graph node; edges connect neighbouring cells (4/8/16).
Edge weight is a **directional** cost function (slope = rise/run signed by
travel direction), so the conductance matrix is **asymmetric** = true
anisotropy. Paths are solved with `scipy.sparse.csgraph.dijkstra`.

- **Corridor**: sum of two accumulated surfaces — one from the origin, one
  from the destination grown on the *reversed* graph (correct for anisotropy).
- **FETE**: LCPs between all `n(n-1)` **directed** ordered pairs (both
  directions, for anisotropy), traversal frequency per cell (White & Barber
  2012). Cost scales ~O(n²) in the number of points.
- **PDI**: area between modelled and reference polyline / reference length =
  mean deviation in map units.
- **Buffer-overlap validation** (Goodchild & Hunter 1997): for each tolerance
  distance, the share (%) of the modelled path within that distance of the
  reference — a multi-distance similarity table beside the PDI.
- **Sensitivity analysis**: sweeps the selected cost functions × connectivities
  for one O/D pair → an agreement raster (per-cell path frequency), a
  per-configuration summary table, optional individual paths, and a
  route-stability scalar (mean pairwise buffer-overlap).
- **Friction**: a cost-per-metre raster (vegetation, wadis, geology) drives the
  surface directly (isotropic), or — with an optional DEM — acts as a
  dimensionless multiplier on the anisotropic slope cost (combined mode).
- **Composite friction (multi-criteria)** (Herzog 2022; Litvine 2024): merges
  several penalty rasters (hydrology, wetness, land cover, viewshed masks) into
  one friction multiplier — each min-max normalised, optionally inverted,
  weighted, and combined by a weighted sum or product; NoData → impassable. Feed
  it into the slope tools as the barrier/multiplier raster.
- **Accessibility / cost catchment** (Verhagen 2019): cost-distance from source
  point(s) — a movement-potential surface — plus an optional catchment mask
  (reachable within a cost budget) and isochrone bands.
- **Barrier / multiplier**: an optional raster on the slope-based algorithms
  (slope cost surface, LCP, LCC, FETE) scales edge cost by the mean of its two
  cells (>1 discourages, <1 prefers known roads); NoData/≤0 cells are
  impassable (cliffs, deep wadis).
- **Stochastic LCP** (Lewis 2021): N Monte-Carlo realisations adding a
  spatially-correlated DEM error (RMSE-scaled) and/or randomly dropping edges,
  accumulating how often each cell lies on the least-cost path → a
  probabilistic corridor in [0, 1]. The error field is a true **variogram**
  Gaussian random field (exponential/spherical/gaussian + nugget, FFT spectral
  simulation; Hunter & Goodchild 1997), with a fast Gaussian-filter option; a
  standalone *DEM error realisation* tool outputs a single perturbed DEM. The
  corridor also propagates **cost-model** uncertainty (Herzog 2022): each
  realisation can sample a cost function from a weighted set and jitter its
  parameters. An optional **convergence criterion** (stabilisation or precision)
  stops the Monte-Carlo loop early once the corridor has settled, reporting the
  live metric. Set a seed for reproducibility.
- **Randomized shortest paths (RSP)** (Panzacchi 2015; van Etten 2017): a single
  parameter θ tunes between the least-cost path (θ→∞) and the random-walk /
  circuit current density (θ→0), with realistic exploratory movement in between.
  Output is a movement-density surface plus the RSP free-energy distance, solved
  in pure `scipy.sparse` over the existing conductance matrix.
- **Circuit theory** (McRae 2008, 2012): movement as electrical current flow —
  solve the graph Laplacian (`Lv = i`) for **current density** (where movement
  concentrates), **pinch points** (high current within the least-cost corridor),
  and **barriers / restoration** (McRae 2012 moving-window improvement score).
  Circuit theory is undirected, so the conductance is symmetrised — for the
  anisotropic current use RSP at small θ.

Cost functions included (ten): Tobler (on/off-path), Herzog, Naismith,
Llobera & Sluckin, **Irmischer & Clarke** (GPS-calibrated speed), **Minetti**
(cost of transport), **Pandolf** (load-aware metabolic rate with the
Santee/Yokota downhill correction), and the movement-mode presets **Wheeled**
(cart) and **Pack animal** — anisotropic critical-slope functions (uphill limit
tighter than downhill; Herzog 2013, Verhagen 2019). Pandolf reads optional
body-mass / load / terrain parameters, threaded from the GUI via `cost_params`
on every conductance-building algorithm. Add your own in `core/cost_functions.py`
(signature `(slope, distance, **_) -> cost`) and register it in the
`COST_FUNCTIONS` dict + labels list.

## Documentation

- **[User manual](docs/MANUAL.md)** — concepts, per-algorithm guide with
  parameters, a worked example, performance/memory notes and troubleshooting.
- **[References](docs/REFERENCES.md)** / **[references.bib](docs/references.bib)**
  — the literature behind each cost function and method.
- **Python library** — the GUI-free numerics are also on PyPI
  (`pip install itinera`); see [`README-pypi.md`](README-pypi.md).

## Install

1. Download `itinera-<version>.zip` from the
   [Releases](https://github.com/leiverkus/itinera/releases) page — or build it
   yourself with `make zip` (wraps `scripts/package-plugin.sh`, which packages
   only the committed runtime files, dev/CI files stripped).
2. QGIS → Plugins → Manage and Install Plugins → Install from ZIP.
3. Enable **Itinera – Least-Cost Pathways**.
4. Algorithms appear in the Processing Toolbox under *Itinera – Least-Cost
   Pathways*. The interactive tool and its settings appear as two buttons on the
   **Plugins toolbar** (View → Toolbars → Plugins Toolbar if it's hidden) and
   also under *Plugins → Itinera*.

Requires QGIS ≥ 3.28 and runs on **QGIS 4.0 (Qt6)** as well — Qt access goes
through the `qgis.PyQt` compatibility layer. Use a **projected CRS** in metres
(e.g. EPSG:32637 / EPSG:28191) for DEM and points so slope and distance are
metric.

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

## Notes & limits (v0.14.1)

- The interactive map tool's cost function and neighbourhood are set via the
  "Interactive LCP settings…" button on the Plugins toolbar (or *Plugins →
  Itinera*); defaults are Tobler, 8-neighbour.
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
