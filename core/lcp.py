# -*- coding: utf-8 -*-
"""Least-cost path and accumulated-cost computation."""

import numpy as np
from scipy.sparse.csgraph import dijkstra


def accumulated_cost(matrix, sources):
    """Cumulative least-cost surface from one or more source nodes.

    Returns a 1D array (length = n nodes) of minimum cost to reach each node
    from the nearest source. Unreachable nodes are np.inf.
    """
    dist = dijkstra(matrix, directed=True, indices=sources, min_only=True)
    return dist


def least_cost_path(matrix, origin, destination):
    """Return the node sequence of the cheapest path origin -> destination.

    Uses Dijkstra with predecessor tracking. Returns (nodes, total_cost).
    nodes is a list from origin to destination (inclusive); empty if no path.
    """
    dist, predecessors = dijkstra(
        matrix, directed=True, indices=origin,
        return_predecessors=True, min_only=False,
    )
    total = float(dist[destination])
    if not np.isfinite(total):
        return [], np.inf

    # Walk predecessors back from destination to origin.
    path = []
    node = destination
    guard = 0
    max_steps = matrix.shape[0] + 1
    while node != origin and node >= 0:
        path.append(int(node))
        node = int(predecessors[node])
        guard += 1
        if guard > max_steps:
            return [], np.inf
    path.append(int(origin))
    path.reverse()
    return path, total
