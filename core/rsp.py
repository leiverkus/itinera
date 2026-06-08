# -*- coding: utf-8 -*-
"""Randomized Shortest Paths (RSP).

A single inverse-temperature parameter ``theta`` continuously interpolates
between the two movement paradigms:

* ``theta -> inf`` — the deterministic least-cost path ([[core.lcp]]);
* ``theta -> 0``   — the random walk / circuit current density.

RSP is built directly on the existing asymmetric conductance (cost) matrix, so
it keeps Itinera's anisotropy throughout (the theta->0 limit is the *directed*
random-walk current, not the symmetric resistor network). Pure numpy/scipy.

Method (Saerens et al.; Kivimaki et al.; Panzacchi et al. 2015; van Etten 2017):

* reference random walk ``P_ref`` = conductance-weighted (1/cost), row-normalised;
* ``W = P_ref .* exp(-theta * c~)`` with ``c~ = c / mean(c)`` when normalised;
* because every cost ``c > 0`` makes ``exp(-theta*c~) < 1`` for ``theta > 0``,
  ``W`` is strictly *substochastic* (row sums < 1), so ``(I - W)`` is invertible
  with **no absorbing target** and the fundamental matrix ``Z = (I - W)^-1``
  exists;
* expected passages through node ``i`` for a source ``s`` and target ``t`` are
  ``n_i = z_si * z_it / z_st`` (RSP node betweenness);
* free-energy distance ``phi(s, t) = -(cbar/theta) * (ln z_st - ln z_tt)``.

Only column ``t`` and row ``s`` of ``Z`` are needed, so one sparse LU
factorisation of ``(I - W)`` plus one transposed solve (the source row, shared
across destinations) and one solve per destination suffice.
"""

import numpy as np
from scipy.sparse import csr_matrix, identity
from scipy.sparse.linalg import splu

from .lcp import accumulated_cost


def _reference_weight(matrix, theta, normalize):
    """Return ``(W, cbar)``: ``W = P_ref .* exp(-theta * c/cbar)`` (CSR).

    ``P_ref`` is the conductance-weighted (1/cost), row-normalised random walk
    over the existing edge structure; ``cbar`` is the mean edge cost (1.0 when
    ``normalize`` is False).
    """
    n = matrix.shape[0]
    cost = matrix.data
    cbar = float(cost.mean()) if normalize and cost.size else 1.0

    conductance = 1.0 / cost
    g = csr_matrix((conductance, matrix.indices, matrix.indptr),
                   shape=matrix.shape)
    row_sum = np.asarray(g.sum(axis=1)).ravel()
    row_of_nz = np.repeat(np.arange(n), np.diff(matrix.indptr))
    denom = row_sum[row_of_nz]
    p_ref = np.where(denom > 0.0, conductance / denom, 0.0)

    w_data = p_ref * np.exp(-theta * cost / cbar)
    w = csr_matrix((w_data, matrix.indices.copy(), matrix.indptr.copy()),
                   shape=matrix.shape)
    return w, cbar


def rsp_passages(matrix, origin, destinations, theta, normalize=True,
                 return_distance=False, progress=None):
    """Theta-tunable expected-passage (movement-density) surface.

    Parameters
    ----------
    matrix : scipy.sparse matrix of edge *costs* (from ``build_conductance``).
    origin : node index of the source.
    destinations : node index or iterable of node indices.
    theta : inverse-temperature > 0 (theta->inf approaches the LCP; small theta
        approaches the random-walk / circuit current).
    normalize : divide costs by their mean before ``exp(-theta*c)`` so that
        ``theta ~ 1`` is meaningful across cost functions (default True). With
        ``normalize=False`` theta is applied to raw costs (gdistance-style).
    return_distance : also return the free-energy distance per destination.
    progress : optional callable(fraction_0_to_1).

    Returns
    -------
    ``(passages, n_cells)`` — ``passages[i]`` is the expected number of passages
    through cell ``i`` accumulated over destinations, normalised to [0, 1] by its
    maximum. When ``return_distance`` is True, also returns ``distances``: the
    free-energy distance (raw cost units) per destination, ``inf`` if unreachable.
    """
    if theta <= 0:
        raise ValueError(
            "theta must be > 0 (the theta -> 0 random-walk limit is singular)")

    n = matrix.shape[0]
    origin = int(origin)
    if np.isscalar(destinations):
        destinations = [destinations]
    destinations = [int(d) for d in destinations]

    # Active set = nodes that can reach at least one destination (reach-T). On
    # this submatrix z_si, z_it, z_st and z_tt are all exact (a walk involved in
    # any of them never leaves reach-T), so passages and the free-energy
    # distance stay exact while the linear system shrinks. NB: do NOT also
    # intersect with "reachable from origin" — that would corrupt z_tt.
    to_dest = accumulated_cost(matrix.transpose().tocsr(), destinations)
    active = np.isfinite(to_dest)

    passages = np.zeros(n, dtype=np.float64)
    distances = [np.inf] * len(destinations)

    if not active[origin]:
        # Origin cannot reach any destination.
        return (passages, n, distances) if return_distance else (passages, n)

    idx = np.flatnonzero(active)
    pos = np.full(n, -1, dtype=np.int64)
    pos[idx] = np.arange(idx.size)

    w, cbar = _reference_weight(matrix, theta, normalize)
    w_sub = w[idx][:, idx]
    a = (identity(idx.size, format="csc") - w_sub.tocsc())
    lu = splu(a)

    s_local = pos[origin]
    e_s = np.zeros(idx.size)
    e_s[s_local] = 1.0
    y = lu.solve(e_s, trans="T")          # y[i] = z_si  (local indices)

    passages_local = np.zeros(idx.size)
    total = len(destinations)
    for k, t in enumerate(destinations):
        if active[t]:
            t_local = pos[t]
            e_t = np.zeros(idx.size)
            e_t[t_local] = 1.0
            x = lu.solve(e_t)             # x[i] = z_it
            z_st = x[s_local]
            # z_st > 0 means t is reachable from s. At very large theta z_st is
            # legitimately tiny (the passage probabilities concentrate on the
            # LCP); it only hits exactly 0.0 on true unreachability or hard
            # float underflow, both of which we skip. z_tt = Z[t, t] >= 1, so
            # the free-energy distance stays finite whenever z_st > 0.
            if z_st > 0.0:
                passages_local += (y * x) / z_st
                z_tt = x[t_local]
                distances[k] = float(
                    -(cbar / theta) * (np.log(z_st) - np.log(z_tt)))
        if progress is not None:
            progress((k + 1) / total)

    passages[idx] = passages_local
    peak = passages.max()
    if peak > 0:
        passages /= peak

    return (passages, n, distances) if return_distance else (passages, n)
