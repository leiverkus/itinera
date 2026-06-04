# Manual verification — Friction cost surface (Roadmap 1)

This checklist covers the steps that cannot run outside QGIS. The GUI-free
`core/` numerics are already verified by the standalone test (see "Automated"
below); the items here confirm the QGIS wiring and end-to-end behaviour.

## Automated (already passed)

Run outside QGIS in a throwaway venv with numpy + scipy:

```bash
python3 -m venv /tmp/itinera_test_venv
/tmp/itinera_test_venv/bin/pip install numpy scipy
cd <parent-of-itinera>
/tmp/itinera_test_venv/bin/python3 - <<'PY'
import numpy as np
from itinera.core.conductance import build_conductance, build_conductance_friction
from itinera.core.lcp import least_cost_path
from itinera.core import cost_functions as cf

rng = np.random.default_rng(0)
dem = rng.random((20, 20)) * 50 + 100
fric = rng.random((20, 20)) * 4 + 1

m, R, C = build_conductance(dem, 10.0, cf.tobler, neighbours=8)
assert (m != m.T).nnz > 0                      # slope matrix asymmetric

mf, R, C = build_conductance_friction(fric, 10.0, neighbours=8)
assert (mf != mf.T).nnz == 0                    # friction-only symmetric
assert np.isfinite(least_cost_path(mf, 0, R*C-1)[1]) > 0

mc, R, C = build_conductance_friction(fric, 10.0, neighbours=8,
                                      dem=dem, cost_fn=cf.tobler)
assert (mc != mc.T).nnz > 0                     # combined asymmetric

fric2 = fric.copy(); fric2[5, 5] = -1.0
m2, R, C = build_conductance_friction(fric2, 10.0, neighbours=8)
c = 5 * C + 5
assert m2[c].nnz == 0 and m2[:, c].nnz == 0     # impassable cell isolated
print("ok")
PY
```

Plus syntax check:

```bash
python3 -m py_compile itinera/core/conductance.py \
    itinera/algorithms/friction_cs_algorithm.py itinera/provider.py
```

Status: **passed** (2026-06-04).

## Manual (inside QGIS) — TODO

Prerequisites: QGIS ≥ 3.28, plugin installed/symlinked, a projected CRS in
metres (e.g. EPSG:32637 / EPSG:28191). Have a friction raster and a matching
DEM (identical extent + resolution) plus a point layer with ≥1 source point,
all in the same CRS.

1. **Plugin loads.** Reload via Plugin Reloader. The Processing Toolbox shows
   *Itinera – Least-Cost Pathways → Cost surfaces → Friction cost surface
   (accumulated)*. No import errors in the Python console.

2. **Friction-only run (isotropic).**
   - Friction raster + source point(s); leave DEM empty.
   - Run. Output raster loads.
   - [ ] Source cell(s) read ≈ 0 cost.
   - [ ] Cost grows monotonically with distance from the source, scaled by
         friction (high-friction regions accumulate faster).
   - [ ] NoData / ≤0 friction cells are unreachable (NoData in output), not
         free.

3. **Combined run (friction + DEM, anisotropic).**
   - Same inputs plus the DEM and a cost function (e.g. Tobler).
   - Run. Output raster loads.
   - [ ] Source cell(s) read ≈ 0 cost.
   - [ ] Surface differs from the friction-only run (slope now modulates cost).
   - [ ] Uphill-dominated directions accumulate more cost than downhill
         (anisotropy visible).

4. **Grid-mismatch guard.** Run combined mode with a DEM whose extent/resolution
   differs from the friction raster.
   - [ ] Algorithm fails with a clear message: "Friction raster and DEM must
         share the same grid (identical extent and resolution)."

5. **No source in extent.** Run with a source point outside the friction raster.
   - [ ] Fails with: "No source point falls within the friction raster extent."

6. **Neighbourhood option.** Re-run friction-only with 4 / 8 / 16 neighbours.
   - [ ] All complete; 16 produces smoother (less grid-aligned) iso-cost bands.

Record results (pass/fail + screenshots) below when run.
