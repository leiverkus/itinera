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

- **Cost functions** (eight): `tobler`, `tobler_offpath`, `herzog`, `naismith`,
  `llobera_sluckin`, `irmischer_clarke`, `minetti`, `pandolf` — each
  `(slope, distance, **params) -> cost`. `pandolf` reads optional `mass` /
  `load` / `terrain` keyword parameters.
- **Conductance**: `build_conductance` (slope, optional barrier/multiplier,
  `cost_params`), `build_conductance_friction` (friction raster, optional DEM).
- **Paths**: `accumulated_cost`, `least_cost_path`, `corridor` / `corridor_band`,
  `fete`.
- **Stochastic**: `stochastic_lcp`, `add_dem_error`, `add_global_stochasticity`.
- **Validation**: `pdi`, `buffer_overlap` (Goodchild & Hunter buffer method),
  `mean_pairwise_overlap` (route-stability indicator across a set of paths).
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

MIT — see [LICENSE](LICENSE). References for the methods (Tobler, Naismith,
Herzog, Llobera & Sluckin, Irmischer & Clarke, Minetti, Pandolf/Santee, White &
Barber, Lewis, Goodchild & Hunter) are in
[`docs/REFERENCES.md`](https://github.com/leiverkus/itinera/blob/main/docs/REFERENCES.md).
