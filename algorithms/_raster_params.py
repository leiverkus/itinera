# -*- coding: utf-8 -*-
"""Shared raster-parameter helpers for the Processing algorithm wrappers."""

from ..core.raster_io import RasterGrid
from ..core.grid_align import assert_grids_aligned
from ..core.memory import (
    estimate_conductance_bytes, format_bytes, RECOMMENDED_MAX_CELLS,
)


def warn_if_large(grid, neighbours, feedback):
    """Warn (non-fatally) when the DEM is large enough to risk running out of
    memory while building the conductance matrix."""
    cells = grid.rows * grid.cols
    if cells > RECOMMENDED_MAX_CELLS:
        feedback.pushWarning(
            "Large DEM: %d cells (> %d recommended). The conductance matrix "
            "needs roughly %s in RAM; if this runs out of memory, clip the DEM "
            "or use 'Resample DEM (block mean)' first."
            % (cells, RECOMMENDED_MAX_CELLS,
               format_bytes(estimate_conductance_bytes(
                   grid.rows, grid.cols, neighbours))))


def load_aligned_raster(layer, reference_grid, reference_crs, what):
    """Load an optional raster that must align with the reference grid.

    Checks the CRS (against ``reference_crs``) and the full geotransform —
    extent, resolution and origin — not merely the pixel count, so a raster
    that happens to have the same shape but a different origin/resolution/CRS is
    rejected instead of being silently mis-overlaid.

    Parameters
    ----------
    layer : QgsRasterLayer or None (an optional Processing raster parameter)
    reference_grid : RasterGrid the raster must align with
    reference_crs : QgsCoordinateReferenceSystem of the reference (the DEM)
    what : str, a human label for error messages

    Returns
    -------
    2D float ndarray, or None if ``layer`` is None.

    Raises
    ------
    ValueError if the raster's CRS or grid differs from the reference.
    """
    if layer is None:
        return None

    layer_crs = layer.crs()
    if (reference_crs is not None and reference_crs.isValid()
            and layer_crs.isValid() and layer_crs != reference_crs):
        raise ValueError(
            "%s has a different CRS (%s) than the DEM (%s). Reproject it to "
            "match the DEM first." % (what, layer_crs.authid(),
                                      reference_crs.authid()))

    grid = RasterGrid.from_path(layer.source())
    assert_grids_aligned(
        reference_grid.gt, (reference_grid.rows, reference_grid.cols),
        grid.gt, (grid.rows, grid.cols), what)
    return grid.array
