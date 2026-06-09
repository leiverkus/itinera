# -*- coding: utf-8 -*-
"""Accessibility / cost-catchment surfaces."""

import numpy as np

from core.conductance import build_conductance_friction, rowcol_to_node
from core.accessibility import accessibility


def _uniform_grid(n=11, cellsize=10.0):
    fr = np.ones((n, n), dtype=np.float64)
    m, rows, cols = build_conductance_friction(fr, cellsize, neighbours=4)
    return m, rows, cols, cellsize


def test_cost_surface_zero_at_source_and_rises():
    m, rows, cols, cs = _uniform_grid()
    s = rowcol_to_node(0, 0, cols)
    cost, catch, bands = accessibility(m, [s])
    assert cost[s] == 0.0
    assert catch is None and bands is None
    # 4-connectivity, unit friction: cost to (r,c) = (r+c)*cellsize.
    assert cost[rowcol_to_node(2, 3, cols)] == np.float64(5 * cs)


def test_catchment_is_the_reachable_disk():
    m, rows, cols, cs = _uniform_grid()
    s = rowcol_to_node(0, 0, cols)
    budget = 5 * cs                        # cells with r+c <= 5
    _, catch, _ = accessibility(m, [s], budget=budget)
    assert set(np.unique(catch)) <= {0.0, 1.0}
    assert catch[rowcol_to_node(2, 3, cols)] == 1.0     # r+c=5 -> inside
    assert catch[rowcol_to_node(3, 3, cols)] == 0.0     # r+c=6 -> outside
    assert catch[s] == 1.0


def test_isochrone_bands_are_monotone():
    m, rows, cols, cs = _uniform_grid()
    s = rowcol_to_node(0, 0, cols)
    _, _, bands = accessibility(m, [s], band_interval=20.0)
    # ceil(cost/20): (0,0)->0; (1,0) cost 10 -> 1; (2,0) cost 20 -> 1; (3,0) 30 ->2
    assert bands[s] == 0.0
    assert bands[rowcol_to_node(1, 0, cols)] == 1.0
    assert bands[rowcol_to_node(3, 0, cols)] == 2.0
    near = bands[rowcol_to_node(1, 0, cols)]
    far = bands[rowcol_to_node(6, 0, cols)]
    assert far > near


def test_unreachable_cells_handled():
    n = 12
    fr = np.ones((n, n), dtype=np.float64)
    fr[8:, 8:] = np.nan                    # NoData island, unreachable corner
    m, rows, cols = build_conductance_friction(fr, 10.0, neighbours=4)
    s = rowcol_to_node(0, 0, cols)
    cost, catch, bands = accessibility(
        m, [s], budget=1e9, band_interval=50.0)
    t = rowcol_to_node(n - 1, n - 1, cols)
    assert not np.isfinite(cost[t])        # unreachable
    assert catch[t] == 0.0
    assert np.isnan(bands[t])
