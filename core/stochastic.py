# -*- coding: utf-8 -*-
"""Stochastic least-cost paths (Lewis 2021).

Two sources of uncertainty are modelled and combined over N Monte-Carlo
realisations to produce a *probabilistic corridor* — the fraction of iterations
in which each cell lies on the least-cost path:

* **DEM error** — a vertical-accuracy (RMSE) error field is added to the DEM
  each iteration, so the slope (and therefore the cost surface) varies.
* **Global stochasticity** — edges are randomly dropped each iteration, modelling
  unmodelled local impassability.

Both are pure numpy/scipy and reuse the deterministic core (`build_conductance`,
`least_cost_path`), so there is no duplicated path logic.

Note on the DEM-error model: ``leastcostpath`` (R) simulates spatially
autocorrelated error with a variogram (gstat). Without that dependency we
approximate it (Hunter & Goodchild 1997 style): white Gaussian noise smoothed
with a Gaussian kernel whose sigma encodes the autocorrelation range, then
rescaled so the field's standard deviation equals the target RMSE.
"""

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.sparse import csr_matrix

from .conductance import build_conductance
from .lcp import least_cost_path


def add_dem_error(dem, rmse, autocorr_range, cellsize, rng):
    """Return ``dem`` plus a spatially-correlated Gaussian error field.

    Parameters
    ----------
    dem : 2D float ndarray (elevations, metres); NoData as NaN is preserved.
    rmse : float, target vertical RMSE in metres (<= 0 returns ``dem`` unchanged).
    autocorr_range : float, spatial autocorrelation range in metres (0 = white
        noise, no smoothing).
    cellsize : float, metres per pixel.
    rng : numpy.random.Generator.
    """
    if rmse <= 0:
        return dem

    finite = np.isfinite(dem)
    noise = rng.standard_normal(dem.shape)

    sigma = (autocorr_range / cellsize) if (autocorr_range > 0 and cellsize) else 0.0
    if sigma > 0:
        noise = gaussian_filter(noise, sigma=sigma, mode="nearest")

    # Rescale so the error over the valid area has standard deviation = rmse.
    std = noise[finite].std() if finite.any() else 0.0
    if std > 0:
        noise = noise / std * rmse

    out = dem.copy()
    out[finite] = dem[finite] + noise[finite]
    return out


def add_global_stochasticity(matrix, drop_fraction, rng):
    """Return a copy of ``matrix`` with a random fraction of edges removed.

    Each directed edge is independently dropped with probability
    ``drop_fraction`` (0 returns the matrix unchanged; 1 removes every edge).
    Dropping edges can disconnect origin from destination in a given
    realisation — that iteration then contributes no path, which is the intended
    behaviour.
    """
    if drop_fraction <= 0:
        return matrix
    coo = matrix.tocoo(copy=False)
    keep = rng.random(coo.data.shape[0]) >= drop_fraction
    return csr_matrix(
        (coo.data[keep], (coo.row[keep], coo.col[keep])), shape=coo.shape)


def stochastic_lcp(dem, cellsize, cost_fn, origin, destinations, n_iter, rng,
                   rmse=0.0, autocorr_range=0.0, drop_fraction=0.0,
                   neighbours=8, multiplier=None, progress=None):
    """Probabilistic least-cost corridor over N stochastic realisations.

    Returns ``(prob, n_cells)`` where ``prob[i]`` is the fraction of the
    ``n_iter`` realisations in which cell ``i`` lay on a least-cost path from
    ``origin`` to any of ``destinations`` (a value in [0, 1]).

    When ``rmse <= 0`` the conductance matrix is built once and reused (only edge
    dropping varies); otherwise it is rebuilt each iteration on a freshly
    perturbed DEM. ``progress`` is an optional callable(fraction_0_to_1).
    """
    if n_iter < 1:
        raise ValueError("n_iter must be >= 1")

    rows, cols = dem.shape
    n_cells = rows * cols
    if np.isscalar(destinations):
        destinations = [destinations]

    static_matrix = None
    if rmse <= 0:
        static_matrix, _, _ = build_conductance(
            dem, cellsize, cost_fn, neighbours=neighbours, multiplier=multiplier)

    freq = np.zeros(n_cells, dtype=np.float64)

    for k in range(n_iter):
        if static_matrix is None:
            dem_k = add_dem_error(dem, rmse, autocorr_range, cellsize, rng)
            matrix = build_conductance(
                dem_k, cellsize, cost_fn,
                neighbours=neighbours, multiplier=multiplier)[0]
        else:
            matrix = static_matrix

        if drop_fraction > 0:
            matrix = add_global_stochasticity(matrix, drop_fraction, rng)

        on_path = np.zeros(n_cells, dtype=bool)
        for dest in destinations:
            nodes, _ = least_cost_path(matrix, origin, dest)
            on_path[nodes] = True
        freq[on_path] += 1.0

        if progress:
            progress((k + 1) / n_iter)

    return freq / n_iter, n_cells
