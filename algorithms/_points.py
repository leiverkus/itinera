# -*- coding: utf-8 -*-
"""Point-layer helpers: CRS-correct mapping of point features to grid nodes.

Point layers, the project and the DEM may sit in different CRSs. These helpers
transform point coordinates into the DEM (raster) CRS before converting them to
row/col indices, so points are not silently mis-placed or reported as "outside
the DEM".
"""

from qgis.core import QgsCoordinateTransform, QgsFeatureRequest


def make_transform(source_crs, raster_crs, transform_context):
    """Return a QgsCoordinateTransform source_crs -> raster_crs, or None.

    None is returned when no transform is needed (same/invalid CRS), so callers
    can skip transforming.
    """
    if (source_crs is not None and raster_crs is not None
            and source_crs.isValid() and raster_crs.isValid()
            and source_crs != raster_crs):
        return QgsCoordinateTransform(source_crs, raster_crs, transform_context)
    return None


def feature_xy(feature, xform):
    """(x, y) of a point feature, transformed into the raster CRS if needed."""
    pt = feature.geometry().asPoint()
    if xform is not None:
        pt = xform.transform(pt)
    return pt.x(), pt.y()


def source_to_nodes(source, grid, n_cols, xform, first_only=False):
    """Map a point feature source to grid node indices (row * n_cols + col).

    Points are transformed into the raster CRS via ``xform`` (or used as-is when
    ``xform`` is None) and kept only if they fall inside ``grid``.

    Returns a list of node indices, or — when ``first_only`` is True — the first
    in-bounds node index (or None if there is none).
    """
    nodes = []
    for feat in source.getFeatures(QgsFeatureRequest()):
        x, y = feature_xy(feat, xform)
        r, c = grid.xy_to_rowcol(x, y)
        if grid.in_bounds(r, c):
            node = r * n_cols + c
            if first_only:
                return node
            nodes.append(node)
    return None if first_only else nodes
