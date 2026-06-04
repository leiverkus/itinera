# -*- coding: utf-8 -*-
"""Interactive two-click LCP: click origin, click destination, draw path.

Reuses the same core/ numerics as the Processing algorithms, so there is no
duplicated path logic. Requires an active raster (DEM) layer selected in the
layer tree.
"""

from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.core import (
    QgsWkbTypes, QgsPointXY, QgsGeometry, QgsVectorLayer, QgsFeature,
    QgsProject, QgsRaster, QgsCoordinateTransform,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QMessageBox

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.lcp import least_cost_path
from ..core import cost_functions as cf


class LcpMapTool(QgsMapToolEmitPoint):
    """Two-click least-cost path tool."""

    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.origin_xy = None
        self.rubber = QgsRubberBand(canvas, QgsWkbTypes.LineGeometry)
        self.rubber.setColor(QColor(200, 30, 30))
        self.rubber.setWidth(2)
        # Configurable cost function + neighbourhood (parity with Processing).
        self.cost_key = "tobler"
        self.neighbours = 8
        # Cached graph so the second click does not rebuild the matrix. The key
        # also tracks the settings, so changing them invalidates the cache.
        self._grid = None
        self._matrix = None
        self._cols = None
        self._built_key = None

    def set_settings(self, cost_key, neighbours):
        """Update cost function / neighbourhood; invalidate the cached graph."""
        if (cost_key, neighbours) != (self.cost_key, self.neighbours):
            self.cost_key = cost_key
            self.neighbours = neighbours
            self._matrix = None
            self._built_key = None

    def _active_dem(self):
        layer = self.iface.activeLayer()
        if layer is None or layer.type() != layer.RasterLayer:
            return None
        return layer

    def _canvas_crs(self):
        return self.canvas.mapSettings().destinationCrs()

    def _to_dem_crs(self, pt, dem_layer):
        """Transform a canvas-CRS point into the DEM's CRS (no-op if equal)."""
        canvas_crs = self._canvas_crs()
        dem_crs = dem_layer.crs()
        if (canvas_crs.isValid() and dem_crs.isValid()
                and canvas_crs != dem_crs):
            xform = QgsCoordinateTransform(
                canvas_crs, dem_crs, QgsProject.instance())
            return xform.transform(pt)
        return pt

    def _ensure_graph(self, dem_layer):
        key = (dem_layer.source(), self.cost_key, self.neighbours)
        if self._built_key == key and self._matrix is not None:
            return
        self._grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[self.cost_key]
        self._matrix, _, self._cols = build_conductance(
            self._grid.array, self._grid.cellsize, cost_fn,
            neighbours=self.neighbours)
        self._built_key = key

    def canvasReleaseEvent(self, event):
        dem_layer = self._active_dem()
        if dem_layer is None:
            QMessageBox.warning(None, "Itinera",
                                "Select a DEM raster layer first.")
            return

        # Canvas clicks are in the project/canvas CRS; the grid indexes the DEM,
        # so map the point into the DEM CRS before any row/col lookup.
        pt = self._to_dem_crs(self.toMapCoordinates(event.pos()), dem_layer)

        if self.origin_xy is None:
            self.origin_xy = pt          # stored in the DEM CRS
            self.iface.messageBar().pushInfo(
                "Itinera", "Origin set. Click destination.")
            return

        # Second click: compute path.
        try:
            self._ensure_graph(dem_layer)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(None, "Itinera", str(exc))
            self.origin_xy = None
            return

        grid, cols = self._grid, self._cols
        r0, c0 = grid.xy_to_rowcol(self.origin_xy.x(), self.origin_xy.y())
        r1, c1 = grid.xy_to_rowcol(pt.x(), pt.y())

        if not (grid.in_bounds(r0, c0) and grid.in_bounds(r1, c1)):
            QMessageBox.warning(None, "Itinera",
                                "Both points must lie within the DEM.")
            self.origin_xy = None
            return

        nodes, total = least_cost_path(
            self._matrix, r0 * cols + c0, r1 * cols + c1)
        if not nodes:
            QMessageBox.information(None, "Itinera", "No path found.")
            self.origin_xy = None
            return

        points = []
        for node in nodes:
            pr, pc = divmod(node, cols)
            x, y = grid.rowcol_to_xy(pr, pc)
            points.append(QgsPointXY(x, y))

        self._draw_and_store(points, total, dem_layer)
        self.origin_xy = None

    def _draw_and_store(self, points, total, dem_layer):
        # `points` are in the DEM CRS (from grid.rowcol_to_xy).
        geom = QgsGeometry.fromPolylineXY(points)

        # The rubber band overlays the canvas, so it needs canvas-CRS geometry.
        canvas_crs = self._canvas_crs()
        dem_crs = dem_layer.crs()
        rubber_geom = QgsGeometry(geom)
        if (canvas_crs.isValid() and dem_crs.isValid()
                and canvas_crs != dem_crs):
            rubber_geom.transform(QgsCoordinateTransform(
                dem_crs, canvas_crs, QgsProject.instance()))
        self.rubber.setToGeometry(rubber_geom, None)

        crs = dem_layer.crs().authid()
        vl = QgsVectorLayer("LineString?crs=%s" % crs,
                            "LCP (cost %.1f)" % total, "memory")
        vl.dataProvider().addAttributes([])
        vl.updateFields()
        feat = QgsFeature()
        feat.setGeometry(geom)
        vl.dataProvider().addFeature(feat)
        vl.updateExtents()
        QgsProject.instance().addMapLayer(vl)
        self.iface.messageBar().pushInfo(
            "Itinera", "Path drawn (accumulated cost %.1f)." % total)

    def reset(self):
        self.origin_xy = None
        self.rubber.reset(QgsWkbTypes.LineGeometry)
