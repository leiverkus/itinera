# Changelog

All notable changes to **Itinera – Least-Cost Pathways** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.3] - 2026-06-04

### Added

- A distinct **gear icon** for the "Interactive LCP settings…" toolbar/menu
  button (`icon_settings.png`), so it reads as settings rather than reusing the
  least-cost-path icon of the interactive tool button.

## [0.5.2] - 2026-06-04

### Fixed

- Replaced the blank 16×16 placeholder plugin icon with a real, visible 48×48
  icon (a least-cost path over terrain). The two interactive-tool buttons
  previously rendered as empty/invisible buttons on the Plugins toolbar and were
  effectively impossible to find.

### Documentation

- Clarified in the README and manual that the interactive tool and its settings
  live on the QGIS **Plugins toolbar** (and under *Plugins → Itinera*), with how
  to show that toolbar.

## [0.5.1] - 2026-06-04

### Documentation

- Added status badges to the README (CI, latest release, MIT licence,
  QGIS ≥ 3.28, Python 3.9+, numpy/scipy/GDAL).
- Clarified that the post-roadmap directions are built as needed and in response
  to user feedback, not committed milestones.
- Removed the internal `PUBLISHING.md` link from the README and excluded
  `PUBLISHING.md` from the packaged plugin zip (maintainer-only).

No code changes — the runtime is identical to 0.5.0.

## [0.5.0] - 2026-06-04

### Added

- **Resample DEM (block mean)** Processing algorithm + `core/resample.py`
  (NoData-aware integer downsampling) — cuts the cell count by `factor²` to fit
  large DEMs in memory when clipping isn't an option.
- **Memory pre-flight warning.** The conductance-building algorithms (slope &
  friction cost surface, LCP, LCC, FETE, stochastic LCP) estimate the matrix RAM
  (`core/memory.py`) and warn above ~4M cells, pointing to clipping or the
  resample tool.

### Documentation

- Added a **user manual** (`docs/MANUAL.md`) — concepts, a per-algorithm guide
  with parameters, a worked example, performance/memory notes and
  troubleshooting — plus **`docs/REFERENCES.md`** and **`docs/references.bib`**
  with the (verified) literature behind each cost function and method.
- Corrected the stochastic-LCP citation from "Lewis 2023" to **Lewis 2021**
  (J. Archaeol. Method Theory 28: 911–924).

### Fixed

- `stochastic_lcp` now raises `ValueError` for `n_iter < 1` instead of dividing
  by zero (the Processing algorithm already enforced a minimum of 1, but a
  direct core call could trigger it).

## [0.4.0] - 2026-06-04

### Added

- **Interactive LCP tool settings.** The two-click map tool is no longer
  hard-wired to Tobler + 8-neighbour: a new "Interactive LCP settings…"
  toolbar/menu action opens a dialog (`gui/settings_dialog.py`) to pick the cost
  function and neighbourhood, matching the Processing algorithms. The graph
  cache is invalidated when the settings change and reused otherwise.

## [0.3.0] - 2026-06-04

### Added

- **Stochastic least-cost path** (Lewis 2021) — `core/stochastic.py` and the
  "Stochastic least-cost path (probabilistic corridor)" Processing algorithm.
  Runs N Monte-Carlo realisations, each optionally adding a spatially-correlated
  DEM error (`add_dem_error`: white noise smoothed with `scipy.ndimage.
  gaussian_filter` to an autocorrelation range, rescaled to a target vertical
  RMSE) and/or randomly dropping a fraction of edges
  (`add_global_stochasticity`), then accumulating how often each cell lies on
  the least-cost path → a probabilistic corridor in [0, 1]. Supports the
  optional barrier/multiplier raster and a random seed for reproducibility.
  Reuses `build_conductance` + `least_cost_path` (no duplicated path logic).

## [0.2.2] - 2026-06-04

### Fixed

- **`xy_to_rowcol` off-by-one for points west/north of the raster.** Index
  conversion now uses `math.floor` instead of `int` (which truncates toward
  zero), so coordinates just outside the raster to the west or north map to -1
  rather than being wrongly reported as row/column 0 (inside the grid). The
  arithmetic moved to the GUI-free `core/grid_align.py::xy_to_rowcol` and is
  unit-tested for just-outside coordinates; `RasterGrid` delegates to it.

## [0.2.1] - 2026-06-04

### Fixed

- **CRS handling for point inputs.** Point/origin/destination layers are now
  transformed into the DEM CRS before being mapped to grid cells, in all
  point-based algorithms (slope & friction cost surface, LCP, LCC, FETE) and in
  the interactive map tool (canvas/project CRS → DEM CRS). Previously, layers in
  a different CRS than the DEM produced wrong cells or spurious "outside DEM"
  errors. PDI validation likewise reprojects the reference line to the modelled
  line's CRS.
- **Real raster alignment checks.** Optional barrier/multiplier and friction
  DEM rasters are validated against the DEM's CRS and full geotransform (extent,
  resolution, origin), not just pixel count — so a same-sized but shifted /
  differently-resolved / differently-projected raster is rejected instead of
  silently mis-overlaid.
- **Raster regularity validation.** `RasterGrid.from_path` now rejects rotated
  or non-square-pixel rasters with a clear error instead of computing wrong
  row/col indices.

### Changed

- Documented the Path Deviation Index's limitations (the shoelace area is only
  meaningful for similar, roughly parallel, non-crossing lines) in
  `core/validation.py` and the algorithm help.
- New GUI-free `core/grid_align.py` (regularity/alignment helpers, unit-tested)
  and shared `algorithms/_points.py` / `algorithms/_raster_params.py` helpers;
  removed the duplicated point-to-node code across the algorithm wrappers.
- `PUBLISHING.md` build/upload steps are now version-neutral (derive the version
  from `metadata.txt`).

## [0.2.0] - 2026-06-04

### Added

- **Barrier / multiplier raster** — an optional per-cell raster on the slope
  cost path (`core/conductance.py::build_conductance(..., multiplier=...)`).
  Edge cost is multiplied by the mean of the two cells' values (>1 discourages,
  <1 prefers, e.g. known roads); NoData or ≤0 cells are impassable (cliffs, deep
  wadis). Exposed as an optional parameter on the Slope cost surface, LCP,
  Corridor (LCC) and FETE algorithms, with a shared
  `algorithms/_raster_params.py` helper enforcing same-grid alignment.

## [0.1.0] - 2026-06-04

Initial release. A from-scratch QGIS reimplementation of the core ideas of the
R package `leastcostpath` for anisotropic archaeological movement modelling,
built purely on the geostack bundled with QGIS (numpy / scipy / GDAL) — no
external pip dependencies.

### Added

- **Slope cost surface** (Processing): accumulated least-cost surface from a DEM
  and source point(s), with selectable cost function and neighbourhood.
- **Friction cost surface** (Processing): cost surface from an arbitrary friction
  raster (vegetation, wadis, geology). Isotropic (`mean(friction) × distance`)
  or, with an optional DEM, combined anisotropic mode where friction acts as a
  dimensionless multiplier on the slope cost. Non-positive/NoData friction is
  treated as impassable.
- **Least-cost path** (Processing): anisotropic LCP from one origin to one or
  more destinations, output as a line layer with accumulated cost per path.
- **Least-cost corridor / LCC** (Processing): sum of two accumulated surfaces,
  the second grown on the transposed graph for correct anisotropy.
- **From-Everywhere-To-Everywhere / FETE** (Processing): all-pairs LCP traversal
  frequency (White & Barber 2012).
- **PDI validation** (Processing): Path Deviation Index between a modelled and a
  reference polyline.
- **Interactive two-click LCP** map tool (Tobler, 8-neighbour).
- Cost functions: Tobler (on/off-path), Herzog, Naismith, Llobera & Sluckin.
- Anisotropic conductance builder: one node per cell, 4/8/16 neighbourhoods,
  directional (asymmetric) sparse cost matrix solved with
  `scipy.sparse.csgraph.dijkstra`.
- Packaged pytest suite for the GUI-free `core/` layer plus a CI workflow.
- MIT licence.

[Unreleased]: https://github.com/leiverkus/itinera/compare/v0.5.3...HEAD
[0.5.3]: https://github.com/leiverkus/itinera/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/leiverkus/itinera/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/leiverkus/itinera/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/leiverkus/itinera/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/leiverkus/itinera/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/leiverkus/itinera/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/leiverkus/itinera/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/leiverkus/itinera/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/leiverkus/itinera/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/leiverkus/itinera/releases/tag/v0.1.0
