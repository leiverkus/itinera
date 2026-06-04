# -*- coding: utf-8 -*-
"""NoData-aware block-mean downsampling of a DEM (pure numpy).

Reducing a DEM by an integer factor cuts the cell count (and therefore the
conductance-matrix RAM) by ``factor**2`` — a simple way to fit a large DEM in
memory when clipping is not an option. Block-mean is a reasonable elevation
downsample; NoData (NaN) cells are ignored per block, and a fully-NoData block
stays NaN.
"""

import numpy as np


def block_reduce_mean(dem, factor):
    """Return ``dem`` downsampled by an integer ``factor`` via block mean.

    The array is trimmed to a whole multiple of ``factor`` in each dimension
    (trailing rows/cols that don't fill a block are dropped). NaN is treated as
    NoData and excluded from each block's mean; an all-NaN block yields NaN.
    ``factor == 1`` returns the input unchanged.
    """
    if factor < 1:
        raise ValueError("factor must be >= 1")
    if factor == 1:
        return dem

    rows, cols = dem.shape
    r2 = (rows // factor) * factor
    c2 = (cols // factor) * factor
    if r2 == 0 or c2 == 0:
        raise ValueError("factor is larger than the DEM")

    trimmed = dem[:r2, :c2]
    mask = np.isfinite(trimmed)
    vals = np.where(mask, trimmed, 0.0)

    br, bc = r2 // factor, c2 // factor
    s = vals.reshape(br, factor, bc, factor).sum(axis=(1, 3))
    n = mask.reshape(br, factor, bc, factor).sum(axis=(1, 3))

    out = np.full((br, bc), np.nan, dtype=np.float64)
    nonzero = n > 0
    out[nonzero] = s[nonzero] / n[nonzero]
    return out
