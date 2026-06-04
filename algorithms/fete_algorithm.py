# -*- coding: utf-8 -*-
"""From-Everywhere-To-Everywhere traversal-frequency surface."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination, QgsProcessing, QgsFeatureRequest,
)

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.fete import fete
from ..core import cost_functions as cf


class FeteAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    POINTS = "POINTS"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    OUTPUT = "OUTPUT"

    _NEIGHBOUR_VALS = [4, 8, 16]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.POINTS, "Input points (all O/D pairs)",
            [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterEnum(
            self.COST_FN, "Cost function",
            options=cf.COST_FUNCTION_LABELS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Neighbourhood",
            options=["4", "8", "16"], defaultValue=1))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Traversal frequency surface"))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        pts_src = self.parameterAsSource(parameters, self.POINTS, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]

        feedback.pushInfo("Building conductance matrix …")
        matrix, rows, cols = build_conductance(
            grid.array, grid.cellsize, cost_fn, neighbours=nb)

        nodes = []
        for feat in pts_src.getFeatures(QgsFeatureRequest()):
            pt = feat.geometry().asPoint()
            r, c = grid.xy_to_rowcol(pt.x(), pt.y())
            if grid.in_bounds(r, c):
                nodes.append(r * cols + c)

        if len(nodes) < 2:
            raise ValueError("FETE needs at least two points within the DEM.")

        feedback.pushInfo("Computing %d pairwise paths …"
                          % (len(nodes) * (len(nodes) - 1) // 2))

        def progress(frac):
            feedback.setProgress(100 * frac)
            if feedback.isCanceled():
                raise RuntimeError("Cancelled by user.")

        freq = fete(matrix, nodes, rows * cols, progress=progress)
        grid.write_like(out_path, freq.reshape(rows, cols))
        return {self.OUTPUT: out_path}

    def name(self):
        return "fete"

    def displayName(self):
        return "From-Everywhere-To-Everywhere (FETE)"

    def group(self):
        return "Paths"

    def groupId(self):
        return "paths"

    def shortHelpString(self):
        return ("Computes least-cost paths between every pair of input points "
                "and accumulates traversal frequency per cell. High values "
                "mark terrain-driven movement corridors (White & Barber 2012). "
                "Cost scales with the square of the point count.")

    def createInstance(self):
        return FeteAlgorithm()
