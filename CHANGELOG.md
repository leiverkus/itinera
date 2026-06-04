# Changelog

All notable changes to **Itinera – Least-Cost Pathways** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/leiverkus/itinera/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/leiverkus/itinera/releases/tag/v0.1.0
