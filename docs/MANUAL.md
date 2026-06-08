# Itinera – User Manual

Itinera models **anisotropic movement** across a landscape for archaeological
route reconstruction: least-cost paths (LCP), corridors (LCC),
From-Everywhere-To-Everywhere (FETE), probabilistic (stochastic) paths,
randomized shortest paths (RSP), circuit-theory connectivity (current density,
pinch points, barriers), sensitivity analysis, and route validation
(Path Deviation Index + buffer overlap). It is a from-scratch reimplementation of
the core ideas of the R package `leastcostpath` (J. Lewis) on the Python
geostack bundled with QGIS — **no external pip packages**.

Literature for every method is in [REFERENCES.md](REFERENCES.md) /
[references.bib](references.bib).

## Contents

1. [Installation](#1-installation)
2. [Key concepts](#2-key-concepts)
3. [Data requirements](#3-data-requirements)
4. [Algorithm reference](#4-algorithm-reference)
5. [Interactive map tool](#5-interactive-map-tool)
6. [Worked example](#6-worked-example)
7. [Performance & memory](#7-performance--memory)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Installation

1. **QGIS ≥ 3.28** (incl. **QGIS 4.0 / Qt6**). Itinera uses only numpy, scipy
   and GDAL, all bundled with QGIS — nothing else to install.
2. Install the plugin ZIP via *Plugins → Manage and Install Plugins → Install
   from ZIP*, or download from the
   [releases page](https://github.com/leiverkus/itinera/releases).
3. Enable **Itinera – Least-Cost Pathways**. The algorithms appear in the
   Processing Toolbox under *Itinera – Least-Cost Pathways*; the interactive
   tool and its settings appear as two buttons on the **Plugins toolbar**
   (enable it via *View → Toolbars → Plugins Toolbar* if hidden) and under
   *Plugins → Itinera*.
4. This is an experimental plugin — tick *"Show also experimental plugins"* in
   the Plugin Manager settings if you don't see it.

## 2. Key concepts

- **Anisotropy.** Cost depends on the *direction* of travel: walking uphill is
  slower than the same slope downhill. Itinera builds a graph (one node per DEM
  cell) whose edge weights are a directional cost function of the signed slope,
  so the cost matrix is **asymmetric** — `cost(A→B) ≠ cost(B→A)`. This is the
  central difference from isotropic raster cost-distance tools.

- **Cost functions.** Each maps `(slope, distance) → cost` (eight available):
  | Key | Reference | Cost type | Direction |
  |---|---|---|---|
  | Tobler / Tobler off-path | Tobler 1993 | travel time | uphill costlier; max speed on gentle downhill |
  | Naismith | Naismith 1892 | travel time | ascent penalty only |
  | Herzog | Herzog 2013 | metabolic | uphill costlier |
  | Llobera & Sluckin | Llobera & Sluckin 2007 | metabolic energy | **descent** costlier at moderate slopes |
  | Irmischer & Clarke | Irmischer & Clarke 2018 | travel time | GPS-calibrated; uphill costlier |
  | Minetti | Minetti et al. 2002 | metabolic energy | uphill costlier; minimum on gentle downhill |
  | Pandolf | Pandolf 1977 + Santee 2001 | metabolic energy | load-aware; **descent** costlier on steep grades |

  **Pandolf** additionally takes a body mass, carried load and terrain factor.
  These appear as *advanced* parameters on every algorithm that builds a cost
  surface (collapsed unless Pandolf is selected); other cost functions ignore
  them.

- **Neighbourhood.** Each cell connects to its 4, 8 or 16 neighbours. More
  neighbours reduce the "grid metric distortion" of paths (fewer forced 45°
  steps) but multiply edge count and memory; 8 is the usual default, 16 for
  smoother paths on important runs.

- **Accumulated cost surface.** The minimum cost to reach every cell from one or
  more sources (Dijkstra). Used directly (Slope/Friction cost surface) and as
  the building block of corridors and FETE.

## 3. Data requirements

- **Projected CRS in metres** (e.g. EPSG:32637 UTM 37N, EPSG:28191 Palestine
  1923). Slope (`Δz / horizontal distance`) and Tobler speed are only meaningful
  in metric units. Geographic (degree) CRSs are **not** supported.
- **DEM**: single-band elevation raster, north-up, unrotated, **square pixels**.
  Rotated or non-square rasters are rejected with a clear error.
- **NoData** becomes unreachable: edges touching a NoData cell are dropped (the
  cell has infinite cost, never zero).
- **Point/line layers** may be in a different CRS than the DEM — Itinera
  reprojects them into the DEM CRS automatically. Optional rasters
  (barrier/friction) must share the DEM's CRS *and* grid (extent, resolution,
  origin); misaligned rasters are rejected rather than silently mis-overlaid.

## 4. Algorithm reference

All Processing algorithms live under *Itinera – Least-Cost Pathways* and can be
run from the Toolbox, the graphical modeller, the Python console, or
`qgis_process`.

### Slope cost surface (accumulated)
- **Purpose**: accumulated least-cost surface from source point(s) over slope.
- **Inputs**: DEM; source point(s); cost function; neighbourhood; optional
  barrier/multiplier raster.
- **Output**: cost raster (cost to reach each cell from the nearest source).
- **Use for**: catchments, accessibility, "how far in N hours" bands (threshold
  the output).

### Friction cost surface (accumulated)
- **Purpose**: cost surface from an arbitrary **friction** raster
  (vegetation, wadis, geology, land cover) instead of, or combined with, slope.
- **Inputs**: friction raster (cost per metre); **optional** DEM (enables the
  anisotropic combined mode); cost function (used only with a DEM); source
  point(s); neighbourhood.
- **Modes**:
  - *Isotropic* (no DEM): `edge cost = mean(friction_A, friction_B) × distance`.
  - *Combined* (with DEM): `edge cost = mean(friction) × cost_fn(slope, distance)`
    — friction acts as a dimensionless multiplier (>1 harder, <1 preferred).
- **NoData / ≤0 friction** = impassable.

### Least-cost path
- **Purpose**: the cheapest route from one origin to one or more destinations.
- **Inputs**: DEM; origin point; destination point(s); cost function;
  neighbourhood; optional barrier/multiplier raster.
- **Output**: line layer, one feature per destination, with accumulated `cost`.

### Stochastic least-cost path (probabilistic corridor)
- **Purpose**: propagate **uncertainty** into the result (Lewis 2021). Runs N
  Monte-Carlo realisations and records how often each cell lies on the LCP.
- **Inputs**: DEM; origin; destination(s); cost function; neighbourhood;
  optional barrier raster; **Iterations** (N); **DEM vertical RMSE** (m);
  **autocorrelation range** (m); **edge-drop fraction** (0–1); **seed**.
- **Output**: probability raster in **[0, 1]** (a probabilistic corridor).
- **Notes**: set RMSE > 0 to model DEM error (with an autocorrelation range),
  and/or an edge-drop fraction for random local impassability. Set a seed for
  reproducible runs. Cost scales with N. With RMSE = 0 and edge-drop = 0 the
  result is just the deterministic path (probability 1 on it).

### Least-cost corridor (LCC)
- **Purpose**: a *band* of near-optimal routes rather than a single brittle line.
- **Inputs**: DEM; origin; destination; cost function; neighbourhood; optional
  barrier raster.
- **Output**: corridor surface = `cost(origin→cell) + cost(cell→destination)`.
  The minimum traces the optimal path; threshold near the minimum to extract a
  corridor of a chosen cost tolerance.

### From-Everywhere-To-Everywhere (FETE)
- **Purpose**: emergent movement network from a set of points (White & Barber
  2012). Computes the LCP between every pair and accumulates traversal frequency.
- **Inputs**: DEM; input points; cost function; neighbourhood; optional barrier.
- **Output**: traversal-frequency raster — high values mark terrain-driven
  corridors. Cost scales with the **square** of the point count; start small.

### Randomized shortest paths (RSP)
- **Purpose**: span the whole optimal↔random movement axis with one parameter
  (Panzacchi et al. 2015; van Etten 2017). A temperature **θ** tunes between the
  deterministic least-cost path (large θ) and the random-walk / circuit current
  density (small θ); intermediate θ is exploratory but cost-biased movement —
  often the most realistic.
- **Inputs**: DEM; origin point; destination point(s); cost function;
  neighbourhood; **θ**; a **Normalise costs** flag; optional barrier.
- **Outputs**: a **movement-density surface** (expected passages per cell,
  0–1) from origin to destination(s), and the RSP **free-energy distance** to
  the nearest destination.
- **θ guidance**: with *Normalise costs* on (default), costs are divided by
  their mean, so **θ ≈ 1** is a sensible start for any cost function — sweep up
  for path-like, down (e.g. 0.05) for diffuse, circuit-like results. With
  normalisation **off**, θ acts on raw cost units (gdistance-style) and a much
  smaller θ (≈ 1e-3) is typically needed. θ is **scale-dependent** — calibrate
  per study; extremely large θ underflows numerically (use the LCP tool for the
  exact optimum).
- **Cost**: RSP factorises a sparse linear system (LU), heavier than the
  Dijkstra tools — clip or resample very large DEMs.

### Circuit current density / pinch points
- **Purpose**: model movement as electrical **current flow** over the resistance
  surface (McRae et al. 2008) — the random-walk end of the spectrum. High-current
  cells are where movement concentrates; the peaks within the least-cost corridor
  are **pinch points** (bottlenecks dispersers must pass through).
- **Inputs**: DEM; source point(s); target point(s); cost function;
  neighbourhood; optional barrier; **pinch-point corridor tolerance** (cost
  units, 0 = current density only) and an optional pinch-point output.
- **Outputs**: a **current-density** raster (0–1); optionally a **pinch-point**
  raster (current within the corridor band).
- **Caveat**: circuit theory is an **undirected** resistor network, so the
  anisotropic conductance is **symmetrised** (`(G+Gᵀ)/2`). For the
  direction-preserving current, use **RSP** with a small θ. Factorises a sparse
  Laplacian — heavier than the Dijkstra tools.

### Connectivity barriers / restoration (McRae 2012)
- **Purpose**: detect **barriers** and quantify **restoration benefit** — for
  each cell, how much the least-cost corridor would improve if a strip across the
  search window were restored to a low resistance. High scores mark the strongest
  barriers.
- **Inputs**: DEM; source/target point(s); cost function; neighbourhood;
  **search-window diameter** (map units); **restored resistance R'** (cost per
  metre of restored land).
- **Output**: a restoration / barrier-improvement raster (cost units saved).
- **Note**: a moving-window approximation over the accumulated-cost corridor
  surfaces (fast, no per-cell re-solve). R' is scale-dependent — calibrate per
  study.

### Sensitivity analysis (cost function × connectivity)
- **Purpose**: test how stable a route is across modelling choices (Herzog 2022;
  Verhagen 2019). Re-runs the LCP for every selected cost function ×
  connectivity between one origin and destination.
- **Inputs**: DEM; origin point; destination point; the cost functions and
  connectivities to sweep (multi-select, default all); optional barrier; optional
  stability tolerance buffer (default = one DEM cell).
- **Outputs**: an **agreement raster** (per-cell count of how many
  configurations' paths cross it), a **summary table** (one row per
  configuration: length, total cost, cell count, reachability), an optional
  **individual-paths** line layer, and a **route-stability** value — the mean
  pairwise buffer-overlap across the reachable paths (100 % = all routes agree).
- **Tip**: limit the selection to keep the full 8 × 3 sweep fast on large DEMs.

### PDI validation
- **Purpose**: quantify how far a modelled path deviates from a known reference
  line (Goodchild & Hunter 1997).
- **Inputs**: modelled line; reference line.
- **Output**: PDI (mean deviation in map units), area, reference length.
- **Caveat**: reliable only for similar, roughly parallel, non-crossing lines —
  see `core/validation.py`.

### Buffer validation
- **Purpose**: the Goodchild & Hunter (1997) buffer method, complementary to the
  PDI. For each tolerance distance, reports the share (%) of the modelled path's
  length lying within that distance of the reference (the metric R
  `leastcostpath` exposes as `buffer_validation`).
- **Inputs**: modelled line; reference line; buffer distances (comma-separated,
  **all must be > 0**); optional sampling step (0 = auto).
- **Output**: a table of (distance, similarity %). Higher is better; 100 % means
  the whole modelled path lies within the tolerance buffer.

### Resample DEM (block mean)
- **Purpose**: downsample a large DEM by an integer factor (NoData-aware block
  mean) to cut the cell count — and the conductance-matrix memory — by `factor²`.
- **Inputs**: DEM; downsample factor (≥ 2).
- **Output**: coarser DEM (same origin, pixel size × factor).

## 5. Interactive map tool

Itinera adds two buttons to the QGIS **Plugins toolbar** (and to *Plugins →
Itinera*). If you don't see them, enable the toolbar via *View → Toolbars →
Plugins Toolbar*.

The **Interactive LCP (two clicks)** button computes a path on the **active DEM
layer**: click the origin, then the destination, and the path is drawn and added
as a memory layer. Use **Interactive LCP settings…** to choose the cost function
and neighbourhood (defaults: Tobler, 8-neighbour). The graph is cached between
clicks and rebuilt only when the DEM or the settings change.

## 6. Worked example

A probabilistic corridor between two sites, accounting for DEM error:

1. Load a projected DEM (metres) and a point layer with two sites.
2. *Processing Toolbox → Itinera → Stochastic least-cost path*.
3. Set **Origin** and **Destination** to the two sites, **Cost function** =
   Tobler, **Iterations** = 100, **DEM vertical RMSE** = 5 m (typical SRTM-class
   error), **autocorrelation range** = 100 m, **seed** = 1.
4. Run. The output raster shows, per cell, the fraction of the 100 realisations
   in which it lay on the least-cost path. Style it 0→1 to see the corridor: a
   single sharp line means the route is robust to DEM error; a broad fuzzy band
   means it is not, and other factors likely governed the real route (Lewis
   2021).
5. Optionally validate a modelled LCP against a known road with **PDI
   validation**.

For large DEMs, run **Resample DEM (block mean)** (e.g. factor 2–4) first, or
clip to the study area.

## 7. Performance & memory

- The whole graph is held in RAM: roughly `cells × neighbours` edges. The
  algorithms **warn above ~4 million cells** and estimate the matrix size.
- To stay in memory: **clip** to the study area, or **Resample DEM (block mean)**
  (factor 2 ≈ ¼ the cells, factor 3 ≈ ⅑). 16-neighbour roughly doubles memory
  vs 8.
- FETE is O(points²) and the stochastic tool is O(iterations); start small and
  scale up.

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| "Unsupported raster … rotated/non-square" | The DEM is rotated or has non-square pixels. Reproject/resample to a clean north-up grid. |
| "… must share the same grid as the DEM" | A barrier/friction raster differs in CRS, extent, resolution or origin. Align it to the DEM (same grid). |
| "… is outside the DEM extent" | The point falls off the DEM. Check it really lies over the DEM (CRS is handled automatically). |
| Point seems snapped to the DEM edge | Fixed in v0.2.2 — update if older. |
| QGIS runs out of memory / very slow | DEM too large: clip or *Resample DEM (block mean)*; reduce neighbourhood to 8 or 4. |
| Path hugs a NoData hole | NoData is impassable by design; fill or interpolate the DEM if that's not intended. |
| Geographic-CRS results look wrong | Use a projected CRS in metres; degrees are not supported. |

---

*Method citations: see [REFERENCES.md](REFERENCES.md). Contributions and issues:
<https://github.com/leiverkus/itinera>.*
