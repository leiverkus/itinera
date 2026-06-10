# -*- coding: utf-8 -*-
"""From-Everywhere-To-Everywhere (FETE), White & Barber (2012).

Compute least-cost paths between every pair of input points and accumulate how
often each cell is traversed. High-traffic cells indicate "natural" movement
corridors that emerge from the terrain rather than from any single O/D pair.

Routes are **directed**: every ordered pair ``(a -> b)`` *and* ``(b -> a)`` is
computed — ``n*(n-1)`` routes for ``n`` points. On an anisotropic cost surface
the two directions are different paths (uphill != downhill), so collapsing them
to one undirected route per pair (White & Barber compute both) would drop whole
corridor cells that only the return leg traverses.
"""

import numpy as np
from itertools import permutations
from .lcp import least_cost_path


def fete(matrix, nodes, n_cells, progress=None, return_paths=False):
    """Compute the FETE traversal-frequency surface.

    Parameters
    ----------
    matrix : sparse conductance matrix
    nodes : list of node indices (the input points)
    n_cells : total number of raster cells
    progress : optional callable(fraction_0_to_1) for UI feedback
    return_paths : if True, also return the individual paths

    Returns
    -------
    freq : 1D float ndarray (length = n_cells) of traversal counts.
    paths : only when ``return_paths`` is True — a list of
        ``(i, j, path_nodes, cost)`` tuples, one per **directed** route, where
        ``i`` / ``j`` are the positions of the from/to endpoints in ``nodes`` (so
        callers can label the line with the input-point indices) and
        ``path_nodes`` is the node sequence for ``nodes[i] -> nodes[j]``. Both
        ``(i, j)`` and ``(j, i)`` appear (they differ under anisotropy). Pairs
        with no connecting path are omitted.
    """
    freq = np.zeros(n_cells, dtype=np.float64)
    # Ordered pairs -> both travel directions (anisotropy: a->b != b->a).
    pairs = list(permutations(enumerate(nodes), 2))
    total = len(pairs)
    paths = [] if return_paths else None

    for k, ((i, a), (j, b)) in enumerate(pairs):
        path, cost = least_cost_path(matrix, a, b)
        for node in path:
            freq[node] += 1.0
        if return_paths and path:
            paths.append((i, j, path, cost))
        if progress and total:
            progress((k + 1) / total)

    if return_paths:
        return freq, paths
    return freq
