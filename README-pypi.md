# Itinera

Anisotropic **least-cost path** (LCP), **corridor** (LCC),
**From-Everywhere-To-Everywhere** (FETE), **stochastic / probabilistic** paths
and route **validation** (Path Deviation Index + buffer overlap) primitives for
movement modelling — a pure **numpy / scipy** library extracted from the
[Itinera QGIS plugin](https://github.com/leiverkus/itinera).

Cost is **directional** (uphill ≠ downhill): each DEM cell becomes a graph node,
edge weights come from a directional cost function of the signed slope, so the
conductance matrix is **asymmetric** — true anisotropy. Paths are solved with
`scipy.sparse.csgraph.dijkstra`.

```bash
pip install itinera
```

Only `numpy` and `scipy` are required.

## Quick start

```python
import numpy as np
from itinera import build_conductance, least_cost_path, tobler, rowcol_to_node

# A small DEM (elevations in metres) on a 10 m grid.
dem = np.random.default_rng(0).random((50, 50)) * 100.0

matrix, rows, cols = build_conductance(
    dem, cellsize=10.0, cost_fn=tobler, neighbours=8)

origin = rowcol_to_node(0, 0, cols)
dest = rowcol_to_node(49, 49, cols)
path, total_cost = least_cost_path(matrix, origin, dest)  # path = node indices
```

Turn node indices back into (row, col) with `node_to_rowcol(node, cols)`.

## What's included

- **Cost functions** (ten): `tobler`, `tobler_offpath`, `herzog`, `naismith`,
  `llobera_sluckin`, `irmischer_clarke`, `minetti`, `pandolf`, `wheeled`,
  `pack_animal` — each `(slope, distance, **params) -> cost`. `pandolf` reads
  `mass` / `load` / `terrain`; `wheeled` / `pack_animal` are **experimental
  heuristics** — anisotropic critical-slope presets with illustrative default
  thresholds, not calibrated published functions.
- **Conductance**: `build_conductance` (slope, optional barrier/multiplier,
  `cost_params`), `build_conductance_friction` (friction raster, optional DEM).
- **Paths**: `accumulated_cost`, `least_cost_path`, `corridor` / `corridor_band`,
  `fete`.
- **Accessibility**: `accessibility` — cost-distance surface + catchment mask +
  isochrone bands from source(s).
- **Randomized shortest paths**: `rsp_passages` — a θ-tunable movement-density
  surface that spans the least-cost path (θ→∞) and the random-walk / circuit
  current (θ→0), plus the RSP free-energy distance.
- **Circuit theory**: `current_density` (graph-Laplacian current + pinch points)
  and `restoration_score` (McRae 2012 barrier / restoration improvement map).
- **Multi-criteria**: `composite_friction` — a generic heuristic combiner (not a
  Litvine 2024 reproduction) merging several penalty rasters into one friction
  multiplier (weighted sum/product, per-layer invert, NoData masks); min-max
  normalisation makes it extent-dependent.
- **Stochastic**: `stochastic_lcp` (DEM-error + edge-drop + cost-model
  randomisation via `cost_fns` / `cost_weights` / `param_jitter`, with an
  early-stop convergence criterion via `tol` / `convergence` /
  `return_diagnostics`), `add_dem_error`, `simulate_error_field`
  (variogram-based DEM error field), `add_global_stochasticity`.
- **Validation**: `pdi` (Jan et al. 2000: area / straight-line O–D distance,
  endpoints snapped to the reference O/D), `buffer_overlap` (Goodchild & Hunter
  buffer method), `mean_pairwise_overlap` (route-stability across a set of paths).
- **Grid helpers**: `xy_to_rowcol`, `check_/assert_regular_geotransform`,
  `check_/assert_grids_aligned`.
- **Utilities**: `estimate_conductance_bytes`, `format_bytes`,
  `block_reduce_mean`.

## Scope: bring your own raster I/O

This is a numerics library — it works on **numpy arrays + a GDAL-style
geotransform tuple**. It does **not** depend on GDAL and does **not** read or
write raster files. Load your DEM with whatever you already use
(`rasterio`, `osgeo.gdal`, `xarray`/`rioxarray`, …) and pass the array in.

Use a **projected CRS in metres** so slope and distance are metric.

## Relation to the QGIS plugin

The same code ships inside the
[Itinera QGIS plugin](https://github.com/leiverkus/itinera) (where it is the
plugin's private `core` package, plus QGIS/GDAL wrappers). The PyPI package and
the QGIS plugin share the top-level import name `itinera`; they are meant for
**separate environments**. Don't `pip install itinera` into the Python
interpreter that runs QGIS — the plugin already bundles this code, and the two
would shadow each other on `sys.path`.

## Licence

MIT — see [LICENSE](LICENSE). The QGIS plugin wrapper is licensed separately
under GPLv3. References for the methods (Tobler, Naismith,
Herzog, Llobera & Sluckin, Irmischer & Clarke, Minetti, Pandolf/Santee, White &
Barber, Lewis, Jan et al. for PDI, Goodchild & Hunter for buffer overlap,
Panzacchi/Saerens & van Etten for RSP, McRae for circuit theory) are in
[`docs/REFERENCES.md`](https://github.com/leiverkus/itinera/blob/main/docs/REFERENCES.md).
