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
* the **target ``t`` is made absorbing** — its outgoing row in ``W`` is zeroed so
  a random walk terminates on reaching ``t`` (Saerens et al.; gdistance's
  ``PASSAGE``, McRae 2008's constrained walk). ``exp(-theta*c~) < 1`` already
  makes ``W`` substochastic; the zeroed target row keeps ``(I - W)`` invertible,
  and ``Z = (I - W)^-1`` is the fundamental matrix of the absorbed walk;
* expected passages through node ``i`` for source ``s`` and absorbing target
  ``t`` are ``n_i = z_si * z_it / z_st`` (RSP node betweenness);
* free-energy distance ``phi(s, t) = -(cbar/theta) * ln z_st`` (``z_tt = 1`` by
  absorption).

Because the absorbing row makes ``W`` (and so ``Z``) **target-specific**, one
sparse LU factorisation of ``(I - W_t)`` is taken per destination, each followed
by a column solve (``z_.t``) and a transposed solve for the source row
(``z_s.``). An earlier version shared a single non-absorbing factorisation across
destinations; that did not match the cited absorbing process and could reorder
the passage values.
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

    # Active set = nodes that can reach at least one destination (reach-T). All
    # s->t walks stay within reach-T, so restricting the linear system to it is
    # exact; nodes that cannot reach a given target t contribute z_it = 0 (hence
    # zero passage) and never appear on an s->t walk, so they do not perturb that
    # target's result.
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
    w_sub = w[idx][:, idx].tocsr()
    eye = identity(idx.size, format="csc")
    s_local = pos[origin]
    e_s = np.zeros(idx.size)
    e_s[s_local] = 1.0

    passages_local = np.zeros(idx.size)
    total = len(destinations)
    for k, t in enumerate(destinations):
        if active[t]:
            t_local = pos[t]
            # Make t absorbing: zero its outgoing row in W so walks terminate on
            # reaching it. This makes (I - W_t) target-specific, so we factorise
            # once per destination.
            w_t = w_sub.copy()
            w_t.data[w_t.indptr[t_local]:w_t.indptr[t_local + 1]] = 0.0
            w_t.eliminate_zeros()
            lu = splu(eye - w_t.tocsc())

            e_t = np.zeros(idx.size)
            e_t[t_local] = 1.0
            x = lu.solve(e_t)             # x[i] = z_it  (column t of Z)
            z_st = x[s_local]
            # z_st > 0 means t is reachable from s. At very large theta z_st is
            # legitimately tiny (passage mass concentrates on the LCP); it only
            # hits exactly 0.0 on true unreachability or hard float underflow,
            # both of which we skip. z_tt = 1 by absorption, so the free-energy
            # distance reduces to -(cbar/theta) * ln z_st.
            if z_st > 0.0:
                y = lu.solve(e_s, trans="T")   # y[i] = z_si  (row s of Z)
                passages_local += (y * x) / z_st
                distances[k] = float(-(cbar / theta) * np.log(z_st))
        if progress is not None:
            progress((k + 1) / total)

    passages[idx] = passages_local
    peak = passages.max()
    if peak > 0:
        passages /= peak

    return (passages, n, distances) if return_distance else (passages, n)
