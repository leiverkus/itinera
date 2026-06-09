# -*- coding: utf-8 -*-
"""Accessibility / cost-catchment surfaces (focal mobility).

The cost-distance from a set of source cells is itself an accessibility surface
(Verhagen et al. 2019, movement potential): how costly each location is to reach.
On top of it this module derives the two products field archaeologists usually
want — a **catchment** (the area reachable within a cost budget) and **isochrone
bands** (cost rings) — reusing the deterministic Dijkstra accumulation. Pure
numpy.
"""

import numpy as np

from .lcp import accumulated_cost


def accessibility(matrix, sources, budget=None, band_interval=None):
    """Cost-distance accessibility from ``sources``.

    Parameters
    ----------
    matrix : scipy.sparse cost matrix (from ``build_conductance``).
    sources : node index or iterable of node indices.
    budget : if given, also return a catchment mask (1 where reachable within
        ``budget`` cost, else 0).
    band_interval : if given, also return isochrone bands
        ``ceil(cost / band_interval)`` (NaN where unreachable).

    Returns
    -------
    ``(cost_surface, catchment, bands)`` — flat arrays of length ``n_cells``.
    ``cost_surface`` is the accumulated cost (``inf`` where unreachable);
    ``catchment`` / ``bands`` are ``None`` when their parameter is ``None``.
    """
    if np.isscalar(sources):
        sources = [sources]
    sources = [int(s) for s in sources]

    cost = accumulated_cost(matrix, sources)
    reachable = np.isfinite(cost)

    catchment = None
    if budget is not None and budget > 0:
        catchment = (reachable & (cost <= budget)).astype(np.float64)

    bands = None
    if band_interval is not None and band_interval > 0:
        bands = np.where(reachable, np.ceil(cost / band_interval), np.nan)

    return cost, catchment, bands
