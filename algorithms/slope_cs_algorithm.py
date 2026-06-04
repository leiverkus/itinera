# -*- coding: utf-8 -*-
"""Build an accumulated cost surface from a DEM and a single source point."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination, QgsProcessing, QgsFeatureRequest,
)
import numpy as np

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.lcp import accumulated_cost
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster


class SlopeCostSurfaceAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    SOURCE = "SOURCE"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    OUTPUT = "OUTPUT"

    _NEIGHBOUR_OPTS = ["4", "8", "16"]
    _NEIGHBOUR_VALS = [4, 8, 16]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.SOURCE, "Source point(s)",
            [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterEnum(
            self.COST_FN, "Cost function",
            options=cf.COST_FUNCTION_LABELS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Neighbourhood",
            options=self._NEIGHBOUR_OPTS, defaultValue=1))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.MULTIPLIER, "Barrier / multiplier raster (optional)",
            optional=True))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Accumulated cost surface"))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        source = self.parameterAsSource(parameters, self.SOURCE, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        feedback.pushInfo("Loading DEM …")
        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]
        multiplier = load_aligned_raster(
            self.parameterAsRasterLayer(parameters, self.MULTIPLIER, context),
            grid, "Barrier/multiplier raster")

        feedback.pushInfo("Building conductance matrix …")
        matrix, rows, cols = build_conductance(
            grid.array, grid.cellsize, cost_fn, neighbours=nb,
            multiplier=multiplier)

        nodes = self._features_to_nodes(source, grid, cols)
        if not nodes:
            raise ValueError("No source point falls within the DEM extent.")

        feedback.pushInfo("Running Dijkstra accumulation …")
        acc = accumulated_cost(matrix, nodes)
        surface = acc.reshape(rows, cols)

        grid.write_like(out_path, surface)
        return {self.OUTPUT: out_path}

    @staticmethod
    def _features_to_nodes(source, grid, n_cols):
        nodes = []
        for feat in source.getFeatures(QgsFeatureRequest()):
            pt = feat.geometry().asPoint()
            r, c = grid.xy_to_rowcol(pt.x(), pt.y())
            if grid.in_bounds(r, c):
                nodes.append(r * n_cols + c)
        return nodes

    def name(self):
        return "slopecostsurface"

    def displayName(self):
        return "Slope cost surface (accumulated)"

    def group(self):
        return "Cost surfaces"

    def groupId(self):
        return "costsurfaces"

    def shortHelpString(self):
        return ("Builds an anisotropic conductance matrix from a DEM using the "
                "selected cost function, then computes the accumulated "
                "least-cost surface from the source point(s) via scipy "
                "Dijkstra.\n\n"
                "Optional barrier / multiplier raster (same grid as the DEM): "
                "edge cost is multiplied by the mean of the two cells' values "
                "(>1 discourages, <1 prefers); NoData or <=0 cells are "
                "impassable (cliffs, deep wadis).")

    def createInstance(self):
        return SlopeCostSurfaceAlgorithm()
