# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

**Itinera – Least-Cost Pathways** (plugin id `itinera`) is a QGIS plugin for
**anisotropic movement modelling** in archaeology:
least-cost paths (LCP), least-cost corridors (LCC), From-Everywhere-To-
Everywhere (FETE), and Path Deviation Index (PDI) validation. It is a
from-scratch reimplementation of the core ideas of the R package
`leastcostpath` (Joseph Lewis), built on the Python geostack that ships with
QGIS.

Target users are field archaeologists reconstructing past route networks
(here: Southern Levant — projected CRS EPSG:32637 UTM 37N and EPSG:28191
Palestine 1923).

## Non-negotiable constraints

These are the rules that define the project. Do not break them without an
explicit instruction to do so.

1. **No external pip dependencies.** Only `numpy`, `scipy`, `osgeo.gdal`, and
   `qgis.*` / `qgis.PyQt.*` may be imported. All three are bundled with QGIS.
   `scikit-image`, `rasterio`, `networkx`, `igraph`, `geopandas` etc. are
   forbidden — they create installation friction in the QGIS Python
   environment. If a feature seems to need one, find a numpy/scipy/GDAL
   equivalent or raise it with the user first.

2. **`core/` is GUI-free.** Nothing under `core/` may import `qgis`,
   `osgeo`, or PyQt. It is pure numpy/scipy so it can be unit-tested outside
   QGIS (see "Testing"). Raster/vector I/O and Qt live in `algorithms/`,
   `gui/`, and `core/raster_io.py` (the one GDAL exception, kept separate).
   New numerics go in `core/`; new QGIS wrappers call into `core/`.

3. **Anisotropy is the point.** The conductance matrix is intentionally
   **asymmetric**: cost(A→B) ≠ cost(B→A) because slope is directional
   (rise/run signed by travel direction). Never "symmetrise" the matrix for
   convenience. When growing a surface *towards* a destination (corridors),
   use the **transposed** matrix (`matrix.transpose().tocsr()`), not the
   original — see `core/corridor.py`.

4. **No duplicated path logic.** Processing algorithms and the interactive map
   tool both call the same `core/` functions. If you add a computation, add it
   once in `core/` and wrap it; do not inline numerics into an algorithm or
   the map tool.

## Architecture

```
itinera/
├── metadata.txt              # plugin manifest (version lives here)
├── __init__.py               # classFactory -> plugin.py
├── plugin.py                 # QGIS plugin: registers provider + map tool
├── provider.py               # QgsProcessingProvider, lists all algorithms
├── core/                     # PURE numpy/scipy — no qgis/PyQt imports
│   ├── cost_functions.py     # Tobler, Herzog, Naismith, Llobera (+ registry)
│   ├── conductance.py        # DEM -> sparse asymmetric cost matrix
│   ├── lcp.py                # dijkstra: accumulated_cost, least_cost_path
│   ├── corridor.py           # LCC = sum of two accumulations (one reversed)
│   ├── fete.py               # all-pairs LCP traversal frequency
│   ├── validation.py         # PDI
│   └── raster_io.py          # RasterGrid: GDAL read/write + coord transforms
├── algorithms/               # QgsProcessingAlgorithm wrappers (thin)
│   ├── slope_cs_algorithm.py
│   ├── lcp_algorithm.py
│   ├── lcc_algorithm.py
│   ├── fete_algorithm.py
│   └── validation_algorithm.py
└── gui/
    └── point_pick_tool.py    # QgsMapToolEmitPoint, two-click interactive LCP
```

### Data flow

DEM raster → `RasterGrid.from_path` (GDAL, NoData→nan) → `build_conductance`
(one node per cell, sparse CSR edge weights) → `scipy.sparse.csgraph.dijkstra`
→ reshape back to grid → `RasterGrid.write_like` (GeoTIFF) **or** node→xy →
`QgsGeometry` line.

Node indexing is **row-major**: `node = row * n_cols + col`. Helpers:
`rowcol_to_node` / `node_to_rowcol` in `conductance.py`, and
`RasterGrid.xy_to_rowcol` / `rowcol_to_xy` for map coordinates (cell centre).

## Conventions

- **CRS**: assume a projected CRS in metres. Slope = Δz / horizontal_distance
  and Tobler speed are only meaningful in metric units. Do not add geographic
  (degree) support without reprojection.
- **Square pixels** assumed (`RasterGrid.cellsize` uses |gt[1]|). If you add
  rectangular-pixel support, fix distance calc in `conductance.build_conductance`.
- **NoData** becomes `nan`; edges touching NoData are dropped so those cells
  are unreachable (`inf` cost), never free.
- **English** for code, identifiers, comments, and UI strings (`displayName`,
  `shortHelpString`). The user converses in German but the codebase is English.
- **Style**: PEP 8, lines ≤88 chars (flake8-enforced via `setup.cfg`; W503/W504
  ignored), double-quoted strings (matches existing
  files). Keep algorithm classes thin — parse params, call `core/`, write output.
- A new cost function = one function `(slope, distance) -> cost` in
  `cost_functions.py`, added to **both** `COST_FUNCTIONS` (key) and
  `COST_FUNCTION_LABELS` (display). Order must stay aligned — the enum index
  maps positionally.

## Testing

There is a packaged pytest suite under `tests/` covering the GUI-free `core/`
layer. It runs standalone, outside QGIS (no qgis/GDAL needed) — `tests/
conftest.py` puts the plugin root on `sys.path` and imports `core.*` directly
(never the `itinera` package, which would pull in QGIS).

```bash
python3 -m venv .venv && source .venv/bin/activate   # NOT the QGIS python
pip install -r requirements-dev.txt                  # numpy, scipy, pytest
pytest
```

The suite gates on the project invariants: the conductance matrix stays
asymmetric (slope) and symmetric (friction-only), edge/path costs are finite
and positive, the corridor's transpose contract holds (its minimum == the LCP
cost), NoData cells are isolated, and each cost function is directional. Note
`uphill > downhill` holds for tobler/herzog/naismith but **not** llobera_sluckin
(its model makes descent costlier) — see `tests/test_cost_functions.py`.

When adding a `core/` feature, add matching tests asserting these invariants.
Do **not** `import qgis` in tests — it won't resolve outside QGIS. CI runs the
suite via `.github/workflows/tests.yml`.

Syntax-check everything before declaring done:
`python3 -m py_compile itinera/**/*.py` (or list files explicitly).

## How to run inside QGIS during development

1. Symlink or copy the `itinera` folder into the QGIS plugin dir:
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/...`
2. Use the **Plugin Reloader** plugin to reload after edits (faster than
   restarting QGIS).
3. Processing algorithms also run headless via the QGIS Python console or
   `qgis_process`, which is the quickest way to iterate on `core/` + algorithm
   wiring without the GUI.

## Roadmap (with implementation notes)

Ordered roughly by value/effort. Each stays within the constraints above.

### 1. Arbitrary friction raster (not only slope) — DONE
Implemented as `core/conductance.py::build_conductance_friction(friction,
cellsize, neighbours, dem=None, cost_fn=None)`: edge cost =
mean(friction_A, friction_B) * distance (isotropic, friction = cost/m) or, with
an optional DEM, mean(friction) * cost_fn(slope, distance) (friction as an
anisotropic multiplier). Both builders share the `_edge_blocks` iterator.
Exposed via `algorithms/friction_cs_algorithm.py`. Lets users encode
vegetation, wadis, geology as cost.

### 2. Barrier / conductance-multiplier layers — DONE
`build_conductance(..., multiplier=...)` takes an optional per-cell raster:
edge cost *= mean(multiplier_A, multiplier_B) (>1 discourages, <1 prefers);
NoData or <=0 cells are impassable (edge dropped — cliffs, deep wadis). Wired
as an optional parameter into the slope cost surface, LCP, LCC and FETE
algorithms via the shared `algorithms/_raster_params.py::load_aligned_raster`
helper (enforces same-grid alignment with the DEM).

### 3. Stochastic LCP (Lewis 2021) — DONE
`core/stochastic.py`: `add_dem_error` (white noise → `scipy.ndimage.
gaussian_filter` for spatial autocorrelation, rescaled to a target RMSE — a
numpy/scipy approximation of the variogram simulation in leastcostpath),
`add_global_stochasticity` (independently drop a random fraction of edges), and
`stochastic_lcp` (N realisations, accumulate traversal → probability in [0,1],
reusing `build_conductance` + `least_cost_path`). Exposed as
`algorithms/stochastic_lcp_algorithm.py` (seed for reproducibility). Single
origin → destination(s); a FETE-style stochastic network would be the next
extension.

### 4. Map-tool parity — DONE
`gui/settings_dialog.py::LcpSettingsDialog` exposes cost function +
neighbourhood (from `cost_functions.COST_FUNCTION_LABELS`), opened via the
"Interactive LCP settings…" toolbar/menu action in `plugin.py`. The map tool
stores `cost_key`/`neighbours`; the `_ensure_graph` cache key now includes them,
so changing settings rebuilds the matrix while an unchanged second click still
reuses it.

### 5. Packaged tests — DONE
`tests/` holds a pytest suite (synthetic slope/flat DEM + friction fixtures in
`tests/conftest.py`) gating on the "Testing" invariants, with a CI workflow
(`.github/workflows/tests.yml`) running the GUI-free `core/` tests only.

### 6. Memory: windowed/tiled conductance — DONE (pragmatic path)
Took the documented "resample + warn" route rather than a true tiled builder
(cross-tile Dijkstra stitching is complex and out of scope). `core/memory.py`
estimates the matrix RAM and defines `RECOMMENDED_MAX_CELLS`; the conductance
wrappers call `algorithms/_raster_params.py::warn_if_large` before building.
`core/resample.py::block_reduce_mean` (NoData-aware) backs the new
`algorithms/resample_dem_algorithm.py` ("Resample DEM (block mean)", cuts cells
by factor²). A genuine tiled builder remains a future option.

## Gotchas discovered during the build

- `scipy.sparse.csgraph.dijkstra` with `min_only=True` gives the multi-source
  accumulated surface in one call — used for FETE/LCC seeding. With
  `return_predecessors=True` (and `min_only=False`) you get the predecessor
  array for path traceback. Don't mix the two modes up.
- The corridor's second surface must run on the **transposed** matrix, or the
  anisotropic cost "into" the destination is wrong. This is subtle and easy to
  regress — guard it if you refactor.
- GDAL must have `gdal.UseExceptions()` set (done in `raster_io.py`) or errors
  pass silently.
- `metadata.txt` `version=` is the single source of truth for the version;
  bump it there on release.
- **Qt5/Qt6 (QGIS 3 & 4):** import Qt only via `qgis.PyQt.*`; use `dialog.exec()`
  not `exec_()` (gone in PyQt6). Crucial distinction:
  - **Qt-native** unscoped enums are REMOVED in PyQt6 — must be scoped, and the
    scoped form also works on Qt5, so switch unconditionally:
    `QDialogButtonBox.Ok` → `QDialogButtonBox.StandardButton.Ok`. **`QVariant`
    is worse**: PyQt6 exposes neither `QVariant.Int` nor `QVariant.Type`, so for
    `QgsField` types branch on `QT_VERSION` — `QMetaType.Type.Int/Double` on Qt6
    (QGIS 4), `QVariant.Int/Double` on Qt5 (QGIS 3); see `lcp_algorithm.py`.
  - **QGIS-native** unscoped enums (`QgsWkbTypes.LineString`,
    `QgsProcessing.TypeVectorPoint`, `QgsProcessingParameterNumber.Integer`, …)
    are retained on QGIS 4.0 (deprecated) — leave them until 3.x is dropped.
  These are RUNTIME-path bugs: the plugin imports/loads fine and only fails on
  first use (open a dialog, run an algorithm), so always click through the GUI
  on real QGIS 4 when testing, not just "does it load".
