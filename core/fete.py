# -*- coding: utf-8 -*-
"""From-Everywhere-To-Everywhere (FETE), White & Barber (2012).

Compute least-cost paths between every pair of input points and accumulate how
often each cell is traversed. High-traffic cells indicate "natural" movement
corridors that emerge from the terrain rather than from any single O/D pair.
"""

import numpy as np
from itertools import combinations
from .lcp import least_cost_path


def fete(matrix, nodes, n_cells, progress=None):
    """Return a 1D traversal-frequency array (length = n_cells).

    Parameters
    ----------
    matrix : sparse conductance matrix
    nodes : list of node indices (the input points)
    n_cells : total number of raster cells
    progress : optional callable(fraction_0_to_1) for UI feedback
    """
    freq = np.zeros(n_cells, dtype=np.float64)
    pairs = list(combinations(nodes, 2))
    total = len(pairs)

    for k, (a, b) in enumerate(pairs):
        path, cost = least_cost_path(matrix, a, b)
        for node in path:
            freq[node] += 1.0
        if progress and total:
            progress((k + 1) / total)

    return freq
