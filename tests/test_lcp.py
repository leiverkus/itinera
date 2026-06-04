# -*- coding: utf-8 -*-
"""Least-cost path and accumulated-cost surface."""

import numpy as np

from core import cost_functions as cf
from core.conductance import build_conductance, rowcol_to_node
from core.lcp import accumulated_cost, least_cost_path


def test_path_connects_origin_and_destination(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    origin = 0
    dest = rows * cols - 1
    path, cost = least_cost_path(m, origin, dest)
    assert path[0] == origin
    assert path[-1] == dest
    assert np.isfinite(cost) and cost > 0.0


def test_accumulated_surface(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    src = 0
    acc = accumulated_cost(m, [src])
    assert acc.shape == (rows * cols,)
    assert acc[src] == 0.0
    # Every other reachable node has strictly positive accumulated cost.
    reachable = np.isfinite(acc)
    assert reachable.sum() > 1
    assert np.all(acc[reachable][1:] >= 0.0)


def test_unreachable_destination_returns_no_path(slope_dem, cellsize):
    """Fence a destination off with NoData; there must be no path to it."""
    dem = slope_dem.copy()
    cols = dem.shape[1]
    # Surround cell (1,1) with NaN so it is isolated.
    for r, c in [(0, 1), (2, 1), (1, 0), (1, 2),
                 (0, 0), (0, 2), (2, 0), (2, 2)]:
        dem[r, c] = np.nan
    m, rows, cols = build_conductance(dem, cellsize, cf.tobler)
    dest = rowcol_to_node(1, 1, cols)
    path, cost = least_cost_path(m, rows * cols - 1, dest)
    assert path == []
    assert not np.isfinite(cost)
