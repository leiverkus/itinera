# -*- coding: utf-8 -*-
"""Least-cost corridor (LCC).

A corridor is the sum of two accumulated-cost surfaces: one grown from the
origin, one from the destination. The minimum of that sum traces the optimal
path; values close to the minimum delineate a band of near-optimal routes
(Verhagen 2013). Useful when a single line over-states the precision of the
reconstruction.
"""

import numpy as np
from .lcp import accumulated_cost


def corridor(matrix, origin, destination):
    """Return the corridor surface (1D, length = n nodes) and its minimum.

    corridor[i] = cost(origin -> i) + cost(i -> destination via reversed graph)
    The second term is computed on the transpose, because moving *towards* the
    destination on an anisotropic surface is the reverse of moving *away* from
    it.
    """
    from_origin = accumulated_cost(matrix, [origin])
    # Reverse the graph so the second surface measures cost *into* destination.
    to_dest = accumulated_cost(matrix.transpose().tocsr(), [destination])

    surface = from_origin + to_dest
    finite = surface[np.isfinite(surface)]
    minimum = float(finite.min()) if finite.size else np.inf
    return surface, minimum


def corridor_band(surface, minimum, tolerance):
    """Boolean mask of cells within `tolerance` (absolute cost) of optimum."""
    return np.isfinite(surface) & (surface <= minimum + tolerance)
