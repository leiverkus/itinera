# -*- coding: utf-8 -*-
"""The numeric recipe behind the sensitivity-analysis algorithm.

The Processing wrapper itself needs QGIS, but its core sweep — build a
conductance matrix per (cost function, connectivity), solve the LCP, accumulate
a per-cell agreement count and measure route stability — is pure numpy/scipy and
is exercised here on the synthetic DEM fixtures.
"""

import numpy as np

from core.conductance import build_conductance
from core.lcp import least_cost_path
from core.validation import mean_pairwise_overlap
from core import cost_functions as cf


def _nodes_to_xy(nodes, cols):
    """Stand in for RasterGrid.rowcol_to_xy: use (col, row) as planar coords."""
    r, c = np.divmod(np.asarray(nodes), cols)
    return np.column_stack([c.astype(float), r.astype(float)])


def test_sweep_agreement_and_stability(slope_dem, cellsize):
    rows, cols = slope_dem.shape
    origin, dest = 0, rows * cols - 1

    agreement = np.zeros(rows * cols, dtype=int)
    paths = []
    configs = [(k, nb) for k in ("tobler", "pandolf") for nb in (4, 8)]
    for key, nb in configs:
        matrix, _, _ = build_conductance(
            slope_dem, cellsize, cf.COST_FUNCTIONS[key], neighbours=nb)
        nodes, total = least_cost_path(matrix, origin, dest)
        assert nodes, "%s / %d-connectivity should reach the destination" % (key, nb)
        assert np.isfinite(total)
        agreement[np.unique(nodes)] += 1
        paths.append(_nodes_to_xy(nodes, cols))

    # Origin and destination lie on every path.
    assert agreement[origin] == len(configs)
    assert agreement[dest] == len(configs)
    assert agreement.max() <= len(configs)

    stability = mean_pairwise_overlap(paths, distance=1.0)
    assert 0.0 <= stability <= 100.0


def test_pandolf_load_changes_the_swept_path(slope_dem, cellsize):
    """cost_params must flow into the sweep (Pandolf load shifts the route/cost)."""
    rows, cols = slope_dem.shape
    origin, dest = 0, rows * cols - 1
    light = build_conductance(slope_dem, cellsize, cf.pandolf, neighbours=8,
                              cost_params={"load": 0.0})[0]
    heavy = build_conductance(slope_dem, cellsize, cf.pandolf, neighbours=8,
                              cost_params={"load": 40.0})[0]
    _, cost_light = least_cost_path(light, origin, dest)
    _, cost_heavy = least_cost_path(heavy, origin, dest)
    assert cost_heavy > cost_light
