# -*- coding: utf-8 -*-
"""Least-cost path between an origin and one or more destinations."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink, QgsProcessing, QgsFeatureRequest,
    QgsFeature, QgsFields, QgsField, QgsGeometry, QgsPointXY, QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant
import numpy as np

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.lcp import least_cost_path
from ..core import cost_functions as cf


class LcpAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    ORIGIN = "ORIGIN"
    DEST = "DEST"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    OUTPUT = "OUTPUT"

    _NEIGHBOUR_VALS = [4, 8, 16]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.ORIGIN, "Origin point", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.DEST, "Destination point(s)",
            [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterEnum(
            self.COST_FN, "Cost function",
            options=cf.COST_FUNCTION_LABELS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Neighbourhood",
            options=["4", "8", "16"], defaultValue=1))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Least-cost path(s)",
            QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        origin_src = self.parameterAsSource(parameters, self.ORIGIN, context)
        dest_src = self.parameterAsSource(parameters, self.DEST, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]

        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]

        feedback.pushInfo("Building conductance matrix …")
        matrix, rows, cols = build_conductance(
            grid.array, grid.cellsize, cost_fn, neighbours=nb)

        origin_node = self._first_node(origin_src, grid, cols)
        if origin_node is None:
            raise ValueError("Origin point is outside the DEM extent.")

        fields = QgsFields()
        fields.append(QgsField("dest_id", QVariant.Int))
        fields.append(QgsField("cost", QVariant.Double))
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, fields,
            QgsWkbTypes.LineString, grid_crs(dem_layer))

        dests = list(dest_src.getFeatures(QgsFeatureRequest()))
        for i, feat in enumerate(dests):
            pt = feat.geometry().asPoint()
            r, c = grid.xy_to_rowcol(pt.x(), pt.y())
            if not grid.in_bounds(r, c):
                feedback.pushWarning("Destination %d outside DEM – skipped." % i)
                continue
            dest_node = r * cols + c

            path_nodes, total = least_cost_path(matrix, origin_node, dest_node)
            if not path_nodes:
                feedback.pushWarning("No path to destination %d." % i)
                continue

            points = []
            for node in path_nodes:
                pr, pc = divmod(node, cols)
                x, y = grid.rowcol_to_xy(pr, pc)
                points.append(QgsPointXY(x, y))

            out_feat = QgsFeature(fields)
            out_feat.setGeometry(QgsGeometry.fromPolylineXY(points))
            out_feat.setAttributes([i, float(total)])
            sink.addFeature(out_feat)
            feedback.setProgress(100 * (i + 1) / max(len(dests), 1))

        return {self.OUTPUT: dest_id}

    @staticmethod
    def _first_node(source, grid, n_cols):
        for feat in source.getFeatures(QgsFeatureRequest()):
            pt = feat.geometry().asPoint()
            r, c = grid.xy_to_rowcol(pt.x(), pt.y())
            if grid.in_bounds(r, c):
                return r * n_cols + c
        return None

    def name(self):
        return "leastcostpath"

    def displayName(self):
        return "Least-cost path"

    def group(self):
        return "Paths"

    def groupId(self):
        return "paths"

    def shortHelpString(self):
        return ("Computes anisotropic least-cost path(s) from one origin to "
                "one or more destinations. Output is a line layer with the "
                "accumulated cost per path.")

    def createInstance(self):
        return LcpAlgorithm()


def grid_crs(layer):
    return layer.crs()
