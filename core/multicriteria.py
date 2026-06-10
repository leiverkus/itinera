# -*- coding: utf-8 -*-
"""Multi-criteria cost builder: combine penalty rasters into one friction.

Real routes are shaped by more than slope — water crossings, wetness, fords,
land cover, intervisibility. Herzog (2022) composes slope with hydrological cost;
Litvine et al. (2024) weight and combine many environmental rasters into one
cost surface. Itinera already multiplies its anisotropic slope cost by a single
penalty raster (the ``multiplier`` on the slope tools, or ``friction`` on the
friction cost surface); this module builds that penalty layer from several
rasters.

**Scope / provenance.** This is a **generic Itinera heuristic combiner**, *not* a
reproduction of a specific published multi-criteria model. Litvine et al. (2024),
for instance, use domain-calibrated, largely multiplicative components with
meaning-bearing units; here the layers are combined generically with no
per-domain calibration. Use it to prototype a composite friction, then justify
the weighting and components against your own evidence.

Each layer is min-max normalised to ``[0, 1]`` (NaN-aware; high = costlier,
unless inverted), then combined into a friction multiplier in ``out_range``:

* ``sum``     — weighted arithmetic mean (weighted linear combination);
* ``product`` — weighted geometric mean of the per-layer multipliers (the
  multiplicative, Herzog slope x hydrology analogue).

**Caveat — extent dependence.** Min-max normalisation is taken over each layer's
own finite cells, so the same input value maps to a different normalised cost
depending on the raster's *extent* (clip the study area differently and the
composite changes). For results that are stable across extents, pre-normalise the
layers to fixed, physically-meaningful ranges before combining.

``out_range = (lo, hi)`` (default ``(1.0, 10.0)``): ``1`` neutral, ``> 1``
discourages, ``< 1`` would prefer. NoData in *any* layer makes that cell NaN —
impassable once fed to the conductance builders. Pure numpy (GDAL-free).
"""

import numpy as np

_METHODS = ("sum", "product")


def _minmax_normalise(layer):
    """Min-max scale a 2D array to [0, 1] over its finite cells (NaN-aware).

    A constant (or all-NaN) layer maps to all zeros; NaNs are preserved.
    """
    layer = np.asarray(layer, dtype=float)
    finite = np.isfinite(layer)
    if not finite.any():
        return np.zeros_like(layer)
    lo = layer[finite].min()
    hi = layer[finite].max()
    if hi <= lo:
        out = np.zeros_like(layer)
        out[~finite] = np.nan
        return out
    norm = (layer - lo) / (hi - lo)
    return np.clip(norm, 0.0, 1.0)


def composite_friction(layers, weights=None, method="sum", invert=None,
                       out_range=(1.0, 10.0)):
    """Combine penalty rasters into one friction-multiplier surface.

    Parameters
    ----------
    layers : list of equal-shape 2D arrays (penalty rasters).
    weights : per-layer weights (default equal). Must be all > 0.
    method : "sum" (weighted arithmetic mean) or "product" (weighted geometric
        mean of the per-layer multipliers).
    invert : optional per-layer bool; True flips a layer so that a *high* input
        value becomes a *low* cost.
    out_range : (lo, hi) friction range the composite is mapped onto.

    Returns
    -------
    2D ndarray — the composite friction (NaN where any input is NaN).
    """
    if not layers:
        raise ValueError("provide at least one layer")
    if method not in _METHODS:
        raise ValueError("method must be one of %s" % (_METHODS,))

    arrays = [np.asarray(la, dtype=float) for la in layers]
    shape = arrays[0].shape
    if any(a.shape != shape for a in arrays):
        raise ValueError("all layers must have the same shape")

    k = len(arrays)
    if weights is None:
        weights = np.ones(k)
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (k,):
        raise ValueError("weights must have one entry per layer")
    if np.any(weights <= 0) or not np.all(np.isfinite(weights)):
        raise ValueError("weights must be finite and > 0")

    if invert is None:
        invert = [False] * k
    invert = list(invert)
    if len(invert) != k:
        raise ValueError("invert must have one entry per layer")

    lo, hi = float(out_range[0]), float(out_range[1])
    if not (np.isfinite(lo) and np.isfinite(hi)) or not 0.0 < lo < hi:
        # The geometric mean takes log(mult); lo <= 0 yields log(<=0) = -inf/NaN,
        # and lo == 0 yields impassable (zero-cost) cells. Both branches need a
        # strictly positive, finite, ordered range.
        raise ValueError(
            "out_range must be finite with 0 < lo < hi (got (%r, %r))"
            % (out_range[0], out_range[1]))

    nodata = np.zeros(shape, dtype=bool)
    norms = []
    for a, inv in zip(arrays, invert):
        nodata |= ~np.isfinite(a)
        n = _minmax_normalise(a)
        if inv:
            n = 1.0 - n
        norms.append(n)

    wsum = weights.sum()
    if method == "sum":
        stacked = np.stack([w * n for w, n in zip(weights, norms)], axis=0)
        index = np.nansum(stacked, axis=0) / wsum          # weighted mean, [0,1]
        friction = lo + (hi - lo) * index
    else:  # product: weighted geometric mean of per-layer multipliers
        log_acc = np.zeros(shape, dtype=float)
        for w, n in zip(weights, norms):
            mult = lo + (hi - lo) * np.nan_to_num(n, nan=0.0)
            log_acc += w * np.log(mult)
        friction = np.exp(log_acc / wsum)

    friction[nodata] = np.nan
    return friction
