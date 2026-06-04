# -*- coding: utf-8 -*-
"""Geo-grid regularity and alignment checks — pure Python, no GDAL/QGIS.

Kept GUI-free so it is unit-testable outside QGIS. ``RasterGrid`` (the GDAL
layer in ``core/raster_io.py``) and the Processing algorithm wrappers call into
these helpers to fail loudly on rasters that would otherwise produce silently
wrong indices.

A GDAL geotransform is the 6-tuple
``(x_origin, pixel_width, row_rotation, y_origin, col_rotation, pixel_height)``.
``RasterGrid.xy_to_rowcol`` and the slope/distance maths assume an axis-aligned
(unrotated, north-up) grid with square pixels.
"""

# Relative tolerance (fraction of a pixel) for comparing origins / pixel sizes.
_ALIGN_TOL = 1e-6
# Squareness check is a little more lenient — real DEMs carry rounding noise.
_SQUARE_TOL = 1e-3


def check_regular_geotransform(gt, square_tol=_SQUARE_TOL):
    """Return ``(ok, reason)`` for an axis-aligned, square-pixel geotransform."""
    if gt[2] != 0.0 or gt[4] != 0.0:
        return False, "raster is rotated (geotransform rotation terms non-zero)"
    px, py = abs(gt[1]), abs(gt[5])
    if px == 0.0 or py == 0.0:
        return False, "raster has a zero pixel dimension"
    if abs(px - py) > square_tol * max(px, py):
        return False, "raster pixels are not square (%.6g x %.6g)" % (px, py)
    return True, ""


def assert_regular_geotransform(gt, square_tol=_SQUARE_TOL):
    """Raise ValueError unless the geotransform is north-up, unrotated, square."""
    ok, reason = check_regular_geotransform(gt, square_tol)
    if not ok:
        raise ValueError(
            "Unsupported raster: %s. Itinera assumes north-up, unrotated, "
            "square pixels in a projected CRS (metres)." % reason)


def check_grids_aligned(gt_a, shape_a, gt_b, shape_b, align_tol=_ALIGN_TOL):
    """Return ``(ok, reason)``: same shape, origin and pixel size.

    ``shape_*`` are ``(rows, cols)`` tuples; ``gt_*`` are GDAL 6-tuples.
    """
    if tuple(shape_a) != tuple(shape_b):
        return False, ("raster sizes differ (%dx%d vs %dx%d)" % (
            shape_a[0], shape_a[1], shape_b[0], shape_b[1]))
    tol = align_tol * max(abs(gt_a[1]), abs(gt_a[5]), 1.0)
    for i, name in ((0, "x-origin"), (1, "pixel width"),
                    (3, "y-origin"), (5, "pixel height")):
        if abs(gt_a[i] - gt_b[i]) > tol:
            return False, "%s differs (%.10g vs %.10g)" % (name, gt_a[i], gt_b[i])
    return True, ""


def assert_grids_aligned(gt_a, shape_a, gt_b, shape_b, what,
                         align_tol=_ALIGN_TOL):
    """Raise ValueError unless grid B aligns with reference grid A."""
    ok, reason = check_grids_aligned(gt_a, shape_a, gt_b, shape_b, align_tol)
    if not ok:
        raise ValueError(
            "%s must share the same grid as the DEM (identical extent, "
            "resolution and origin): %s." % (what, reason))
