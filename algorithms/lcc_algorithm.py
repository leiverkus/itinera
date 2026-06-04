# -*- coding: utf-8 -*-
"""Least-cost corridor between an origin and a destination."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
    QgsProcessing, QgsFeatureRequest,
)

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.corridor import corridor
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster


class CorridorAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    ORIGIN = "ORIGIN"
    DEST = "DEST"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    OUTPUT = "OUTPUT"

    _NEIGHBOUR_VALS = [4, 8, 16]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.ORIGIN, "Origin point", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.DEST, "Destination point", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterEnum(
            self.COST_FN, "Cost function",
            options=cf.COST_FUNCTION_LABELS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Neighbourhood",
            options=["4", "8", "16"], defaultValue=1))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.MULTIPLIER, "Barrier / multiplier raster (optional)",
            optional=True))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Corridor surface"))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        origin_src = self.parameterAsSource(parameters, self.ORIGIN, context)
        dest_src = self.parameterAsSource(parameters, self.DEST, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]
        multiplier = load_aligned_raster(
            self.parameterAsRasterLayer(parameters, self.MULTIPLIER, context),
            grid, "Barrier/multiplier raster")

        feedback.pushInfo("Building conductance matrix …")
        matrix, rows, cols = build_conductance(
            grid.array, grid.cellsize, cost_fn, neighbours=nb,
            multiplier=multiplier)

        o = self._first_node(origin_src, grid, cols)
        d = self._first_node(dest_src, grid, cols)
        if o is None or d is None:
            raise ValueError("Origin or destination is outside the DEM extent.")

        feedback.pushInfo("Computing corridor (two accumulations) …")
        surface, minimum = corridor(matrix, o, d)
        feedback.pushInfo("Corridor minimum cost: %.3f" % minimum)

        grid.write_like(out_path, surface.reshape(rows, cols))
        return {self.OUTPUT: out_path}

    @staticmethod
    def _first_node(source, grid, n_cols):
        for feat in source.getFeatures(QgsFeatureRequest()):
            pt = feat.geometry().asPoint()
            r, c = grid.xy_to_rowcol(pt.x(), pt.y())
            if grid.in_bounds(r, c):
                return r * n_cols + c
        return None

    def name(self):
        return "corridor"

    def displayName(self):
        return "Least-cost corridor (LCC)"

    def group(self):
        return "Cost surfaces"

    def groupId(self):
        return "costsurfaces"

    def shortHelpString(self):
        return ("Sums accumulated-cost surfaces grown from origin and "
                "destination (the latter on the reversed graph, for "
                "anisotropy). Low values delineate the band of near-optimal "
                "routes. Threshold the output to extract a corridor of a "
                "chosen cost tolerance.")

    def createInstance(self):
        return CorridorAlgorithm()
