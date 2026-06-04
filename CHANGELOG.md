# Changelog

All notable changes to **Itinera – Least-Cost Pathways** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/leiverkus/itinera/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/leiverkus/itinera/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/leiverkus/itinera/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/leiverkus/itinera/releases/tag/v0.1.0
