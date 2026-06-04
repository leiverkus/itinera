# -*- coding: utf-8 -*-
"""Small shared helpers for the Processing algorithm wrappers."""

from ..core.raster_io import RasterGrid


def load_aligned_raster(layer, reference_grid, what):
    """Load an optional raster that must share the reference grid.

    Parameters
    ----------
    layer : QgsRasterLayer or None (an optional Processing raster parameter)
    reference_grid : RasterGrid the raster must align with (same shape)
    what : str, a human label for the error message

    Returns
    -------
    2D float ndarray, or None if ``layer`` is None.

    Raises
    ------
    ValueError if the raster's shape differs from ``reference_grid``.
    """
    if layer is None:
        return None
    grid = RasterGrid.from_path(layer.source())
    if grid.array.shape != reference_grid.array.shape:
        raise ValueError(
            "%s must share the same grid (identical extent and resolution) "
            "as the DEM." % what)
    return grid.array
