# -*- coding: utf-8 -*-
"""Circuit-theory connectivity: current density, pinch points and barriers.

Circuit theory models movement as electrical *current flow* over a resistance
surface — the random-walk extreme opposite the least-cost path (McRae 2006,
2008). Outputs:

* **current density** — where movement concentrates (Kirchhoff/Ohm on the graph
  Laplacian);
* **pinch points** — high current *within the least-cost corridor* (the
  Circuitscape "pinchpoint mapper" definition);
* **barriers / restoration** — McRae (2012)'s moving-window improvement score
  (no Laplacian; built on accumulated-cost corridor surfaces).

Classic circuit theory is an *undirected* resistor network, so the anisotropic
conductance matrix is **symmetrised** here (``G = ½(G + Gᵀ)``). For the
direction-preserving current, use the RSP tool at small ``theta`` instead
(``core.rsp``). Pure numpy/scipy.
"""

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import splu
from scipy.ndimage import minimum_filter

from .lcp import accumulated_cost


def _symmetric_conductance(matrix):
    """Symmetric conductance ``G = ½(g + gᵀ)`` with ``g_ij = 1/cost_ij`` (CSR)."""
    g = csr_matrix((1.0 / matrix.data, matrix.indices, matrix.indptr),
                   shape=matrix.shape)
    return (g + g.transpose()).tocsr() * 0.5


def current_density(matrix, sources, targets, corridor_tolerance=None,
                    progress=None):
    """Symmetric circuit current density from ``sources`` to ``targets``.

    Parameters
    ----------
    matrix : scipy.sparse matrix of edge *costs* (from ``build_conductance``).
    sources, targets : node index or iterable of node indices.
    corridor_tolerance : if given, also return the *pinch-point* surface — the
        current density masked to the least-cost corridor band (cells whose
        origin->cell->target cost is within ``corridor_tolerance`` of the
        optimum).
    progress : optional callable(fraction_0_to_1).

    Returns
    -------
    ``(current, n_cells)`` — ``current[i]`` normalised to [0, 1] — or
    ``(current, n_cells, pinch)`` when ``corridor_tolerance`` is given.
    """
    n = matrix.shape[0]
    sources = ([int(sources)] if np.isscalar(sources)
               else [int(s) for s in sources])
    targets = ([int(targets)] if np.isscalar(targets)
               else [int(t) for t in targets])

    from_s = accumulated_cost(matrix, sources)
    to_t = accumulated_cost(matrix.transpose().tocsr(), targets)
    active = np.isfinite(from_s) & np.isfinite(to_t)

    current = np.zeros(n, dtype=np.float64)
    src = [s for s in sources if active[s]]
    tgt = [t for t in targets if active[t]]
    if not src or not tgt:
        if corridor_tolerance is not None:
            return current, n, current.copy()
        return current, n

    idx = np.flatnonzero(active)
    pos = np.full(n, -1, dtype=np.int64)
    pos[idx] = np.arange(idx.size)

    g_sym = _symmetric_conductance(matrix)
    gs = g_sym[idx][:, idx].tocsr()
    deg = np.asarray(gs.sum(axis=1)).ravel()
    lap = diags(deg) - gs

    tgt_local = np.unique([pos[t] for t in tgt])
    free_mask = np.ones(idx.size, dtype=bool)
    free_mask[tgt_local] = False
    free = np.flatnonzero(free_mask)
    free_pos = np.full(idx.size, -1, dtype=np.int64)
    free_pos[free] = np.arange(free.size)

    b = np.zeros(free.size)
    for s in src:
        b[free_pos[pos[s]]] += 1.0 / len(src)

    lap_free = lap[free][:, free].tocsc()
    if progress is not None:
        progress(0.5)
    v_free = splu(lap_free).solve(b)             # grounded Laplacian is SPD

    v = np.zeros(idx.size)                        # targets stay at 0 V
    v[free] = v_free

    coo = gs.tocoo()
    edge_current = coo.data * np.abs(v[coo.row] - v[coo.col])
    cur_local = np.zeros(idx.size)
    np.add.at(cur_local, coo.row, edge_current)
    cur_local *= 0.5                              # McRae node current = 1/2 sum|I|

    current[idx] = cur_local
    peak = current.max()
    if peak > 0:
        current /= peak
    if progress is not None:
        progress(1.0)

    if corridor_tolerance is None:
        return current, n

    corridor = from_s + to_t
    finite = corridor[np.isfinite(corridor)]
    pinch = np.zeros(n, dtype=np.float64)
    if finite.size:
        band = np.isfinite(corridor) & (corridor <= finite.min()
                                        + corridor_tolerance)
        pinch[band] = current[band]
    return current, n, pinch


def restoration_score(matrix, rows, cols, sources, targets, cellsize,
                      window, improved_resistance=1.0, progress=None):
    """McRae (2012) barrier / restoration improvement map.

    For each cell, how much the least-cost corridor between ``sources`` and
    ``targets`` would improve if a strip of land across a ``window``-cell
    neighbourhood were restored to ``improved_resistance`` (cost per metre).
    High scores mark the strongest barriers. Returns a flat array (length
    ``rows*cols``) of non-negative improvement (cost units); 0 where no
    improvement or unreachable.
    """
    sources = ([int(sources)] if np.isscalar(sources)
               else [int(s) for s in sources])
    targets = ([int(targets)] if np.isscalar(targets)
               else [int(t) for t in targets])

    from_s = accumulated_cost(matrix, sources).reshape(rows, cols)
    to_t = accumulated_cost(
        matrix.transpose().tocsr(), targets).reshape(rows, cols)

    corridor = from_s + to_t
    finite = corridor[np.isfinite(corridor)]
    if not finite.size:
        return np.zeros(rows * cols, dtype=np.float64)
    baseline = float(finite.min())

    w = max(1, int(window))
    if progress is not None:
        progress(0.3)
    min_from = minimum_filter(from_s, size=w, mode="nearest")
    min_to = minimum_filter(to_t, size=w, mode="nearest")
    crossing = improved_resistance * w * cellsize
    improved = min_from + min_to + crossing

    improvement = baseline - improved
    improvement[~np.isfinite(improvement)] = 0.0
    np.clip(improvement, 0.0, None, out=improvement)
    if progress is not None:
        progress(1.0)
    return improvement.ravel()
