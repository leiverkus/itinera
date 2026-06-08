# Changelog

All notable changes to **Itinera – Least-Cost Pathways** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.0] - 2026-06-08

### Added

- **Randomized Shortest Paths (RSP)** — a θ-tunable movement model that subsumes
  the whole optimal↔random axis: large θ → the least-cost path, small θ → the
  random-walk / circuit current density (Panzacchi et al. 2015; van Etten 2017).
  New `core/rsp.py::rsp_passages` (pure numpy/scipy: `W = P_ref ∘ exp(−θ·C)`,
  one sparse LU of `(I−W)` over the existing conductance matrix, expected
  passages `n_i = z_si·z_it/z_st`, free-energy distance) and a *Randomized
  shortest paths (RSP)* Processing algorithm (one origin → destination(s); a
  movement-density raster + the free-energy distance; a *Normalise costs* flag so
  θ≈1 is meaningful across cost functions, or raw gdistance-style θ when off).
  Keeps Itinera's anisotropy throughout (directed-random-walk current at θ→0).

## [0.7.1] - 2026-06-08

### Fixed

- **Buffer validation rejects non-positive distances.** `buffer_overlap` and the
  Buffer Validation algorithm now raise on a zero or negative buffer distance,
  and `buffer_overlap` rejects a non-positive explicit `step`;
  `mean_pairwise_overlap` likewise requires a positive distance. Previously a `0`
  distance collapsed the auto-step to ~epsilon, which could make the densifier
  allocate a near-unbounded number of points on long lines.

### Changed

- **Documentation brought up to date with 0.7.0.** README, the PyPI description
  (`README-pypi.md`) and the user manual now cover the eight cost functions,
  Buffer Validation and Sensitivity Analysis (previously they still listed only
  the five 0.6.x cost functions and `pdi`). README release badge → 0.7.1.

## [0.7.0] - 2026-06-08

### Added

- **Energetics cost functions** — Irmischer & Clarke (2018, GPS-calibrated
  speed), Minetti (2002, cost of transport) and load-aware Pandolf (1977) with
  the Santee/Yokota downhill correction, raising the menu to eight. The
  cost-function contract now accepts extra keyword parameters (body mass / load /
  terrain), threaded via `cost_params` through `build_conductance`,
  `build_conductance_friction` and `stochastic_lcp` and exposed on every
  conductance-building algorithm.
- **Buffer-overlap validation** (Goodchild & Hunter 1997) —
  `core/validation.py::buffer_overlap` plus `mean_pairwise_overlap`, and a
  Buffer Validation Processing algorithm producing a multi-distance similarity
  table beside the PDI.
- **Sensitivity analysis** — a Processing algorithm that sweeps the selected
  cost functions × connectivities for one origin/destination pair and outputs an
  agreement raster, a per-configuration summary table, an optional
  individual-paths layer, and a route-stability scalar.

## [0.6.1] - 2026-06-05

### Added

- **FETE optional path output.** The From-Everywhere-To-Everywhere algorithm
  can now also emit the individual least-cost paths as a line layer (one feature
  per point pair, with `from_id` / `to_id` / `cost`), in addition to the
  traversal-frequency raster. `core/fete.py::fete` gained a `return_paths` flag;
  the paths were already computed internally and are now exposed via an optional
  `FeatureSink` (`createByDefault=False`, so the raster stays the default
  output). No change to the frequency surface.

## [0.6.0] - 2026-06-04

### Added

- **`itinera` PyPI library.** The pure numpy/scipy `core/` is now also published
  as a standalone library (`pip install itinera`) from this same repo, single-
  sourced (no file moves): `pyproject.toml` (hatchling) maps `core/` to the
  import package `itinera`, excludes the GDAL-only `raster_io.py`, and reads the
  version from `metadata.txt`. Public API re-exported from `core/__init__.py`;
  built/published by `.github/workflows/publish.yml` via PyPI Trusted Publishing
  on GitHub release. Library README in `README-pypi.md`. The QGIS plugin and its
  packaging are unchanged.

## [0.5.9] - 2026-06-04

### Changed

- **flake8 is now a real CI check.** Added `flake8` to `requirements-dev.txt`
  and a `lint` job to the CI workflow. Set `max-line-length = 88` (Black's
  default) in `setup.cfg` and removed two unused `numpy` imports in the tests so
  the suite lints clean.
- The plugin zip now also excludes the maintainer/dev-only files `CLAUDE.md`,
  `setup.cfg`, `pytest.ini` and `requirements-dev.txt` (documented in
  `PUBLISHING.md`).

## [0.5.8] - 2026-06-04

### Fixed

- **QGIS 4 / Qt6 runtime crashes from Qt-native unscoped enums** (Qt6 removed
  the unscoped forms; QGIS keeps its *own* enums but not Qt's):
  - The interactive **settings dialog** raised
    `AttributeError: ... 'QDialogButtonBox' has no attribute 'Ok'`. Switched to
    the scoped `QDialogButtonBox.StandardButton.Ok/Cancel` (works on Qt5 & Qt6).
  - The **LCP** output built fields with `QVariant.Int`/`QVariant.Double`, which
    PyQt6 no longer exposes. Now version-branched: `QMetaType.Type.*` on Qt6
    (QGIS 4), `QVariant.*` on Qt5 (QGIS 3).
  Verified on QGIS 3.28 and QGIS 4.0.

## [0.5.7] - 2026-06-04

### Changed

- Removed unused imports flagged by flake8 (F401) across the algorithm wrappers
  and the map tool. Added a `setup.cfg` flake8 config that ignores W503/W504
  (mutually exclusive line-break-around-operator rules; we follow PEP 8's
  break-before-operator style). No behaviour change.

## [0.5.6] - 2026-06-04

### Fixed

- **QGIS 4 marked the plugin incompatible.** Without a `qgisMaximumVersion`,
  QGIS assumes a `<major>.99` maximum — i.e. 3.99 — so QGIS 4.0 refused to load
  it despite the code being Qt6-ready. Set `qgisMaximumVersion=4.99`. Verified
  loading and the settings dialog on QGIS 4.0.

## [0.5.5] - 2026-06-04

### Documentation

- Added QGIS 3.28+/4.0 and Qt 5/6 compatibility badges to the README.

## [0.5.4] - 2026-06-04

### Fixed

- **QGIS 4 / Qt6 compatibility.** The interactive-tool settings dialog called
  `QDialog.exec_()`, which PyQt6 (QGIS 4.0) removed — it would have raised
  `AttributeError` on QGIS 4. Switched to `exec()`, which works on both PyQt5
  (QGIS 3) and PyQt6 (QGIS 4). All Qt access already routes through the
  `qgis.PyQt` compatibility layer; the numpy/scipy core is Qt-independent.
  Remaining deprecated-but-working items (unscoped enums, `QVariant` field
  types) are left until QGIS 3.x support is dropped.

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

[Unreleased]: https://github.com/leiverkus/itinera/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/leiverkus/itinera/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/leiverkus/itinera/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/leiverkus/itinera/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/leiverkus/itinera/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/leiverkus/itinera/compare/v0.5.9...v0.6.0
[0.5.9]: https://github.com/leiverkus/itinera/compare/v0.5.8...v0.5.9
[0.5.8]: https://github.com/leiverkus/itinera/compare/v0.5.7...v0.5.8
[0.5.7]: https://github.com/leiverkus/itinera/compare/v0.5.6...v0.5.7
[0.5.6]: https://github.com/leiverkus/itinera/compare/v0.5.5...v0.5.6
[0.5.5]: https://github.com/leiverkus/itinera/compare/v0.5.4...v0.5.5
[0.5.4]: https://github.com/leiverkus/itinera/compare/v0.5.3...v0.5.4
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
