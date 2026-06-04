# -*- coding: utf-8 -*-
"""From-Everywhere-To-Everywhere traversal frequency."""

import numpy as np

from core import cost_functions as cf
from core.conductance import build_conductance
from core.fete import fete


def test_frequency_shape_and_endpoints(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    n_cells = rows * cols
    nodes = [0, cols - 1, n_cells - 1]   # three corners

    freq = fete(m, nodes, n_cells)
    assert freq.shape == (n_cells,)
    assert freq.sum() > 0
    # Each input node lies on at least one path, so its frequency is positive.
    for node in nodes:
        assert freq[node] > 0


def test_progress_callback_runs(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    n_cells = rows * cols
    seen = []
    fete(m, [0, cols - 1, n_cells - 1], n_cells, progress=seen.append)
    assert seen                      # called at least once
    assert seen[-1] == 1.0           # finishes at 100 %
