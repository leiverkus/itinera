# -*- coding: utf-8 -*-
"""Accumulated cost surface from a friction raster (optionally + a DEM)."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination, QgsProcessing, QgsFeatureRequest,
)
import numpy as np

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance_friction
from ..core.lcp import accumulated_cost
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster, warn_if_large
from ._points import make_transform, source_to_nodes


class FrictionCostSurfaceAlgorithm(QgsProcessingAlgorithm):
    FRICTION = "FRICTION"
    DEM = "DEM"
    SOURCE = "SOURCE"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    OUTPUT = "OUTPUT"

    _NEIGHBOUR_OPTS = ["4", "8", "16"]
    _NEIGHBOUR_VALS = [4, 8, 16]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.FRICTION, "Friction raster (cost per metre)"))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model (optional, enables anisotropy)",
            optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.SOURCE, "Source point(s)",
            [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterEnum(
            self.COST_FN, "Cost function (only used with a DEM)",
            options=cf.COST_FUNCTION_LABELS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Neighbourhood",
            options=self._NEIGHBOUR_OPTS, defaultValue=1))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Accumulated cost surface"))

    def processAlgorithm(self, parameters, context, feedback):
        fric_layer = self.parameterAsRasterLayer(
            parameters, self.FRICTION, context)
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        source = self.parameterAsSource(parameters, self.SOURCE, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        feedback.pushInfo("Loading friction raster …")
        grid = RasterGrid.from_path(fric_layer.source())

        dem_array = None
        cost_fn = None
        if dem_layer is not None:
            feedback.pushInfo("Loading DEM (combined anisotropic mode) …")
            dem_array = load_aligned_raster(
                dem_layer, grid, fric_layer.crs(), "DEM")
            cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]

        warn_if_large(grid, nb, feedback)
        feedback.pushInfo("Building conductance matrix …")
        matrix, rows, cols = build_conductance_friction(
            grid.array, grid.cellsize, neighbours=nb,
            dem=dem_array, cost_fn=cost_fn)

        xform = make_transform(
            source.sourceCrs(), fric_layer.crs(), context.transformContext())
        nodes = source_to_nodes(source, grid, cols, xform)
        if not nodes:
            raise ValueError(
                "No source point falls within the friction raster extent.")

        feedback.pushInfo("Running Dijkstra accumulation …")
        acc = accumulated_cost(matrix, nodes)
        surface = acc.reshape(rows, cols)

        grid.write_like(out_path, surface)
        return {self.OUTPUT: out_path}

    def name(self):
        return "frictioncostsurface"

    def displayName(self):
        return "Friction cost surface (accumulated)"

    def group(self):
        return "Cost surfaces"

    def groupId(self):
        return "costsurfaces"

    def shortHelpString(self):
        return ("Builds a cost matrix from an arbitrary friction raster "
                "(vegetation, wadis, geology …) and computes the accumulated "
                "least-cost surface from the source point(s).\n\n"
                "Friction only: edge cost = mean(friction) * distance "
                "(isotropic, friction read as cost per metre).\n\n"
                "With an optional DEM: edge cost = mean(friction) * "
                "cost_fn(slope, distance) — friction acts as a dimensionless "
                "multiplier on the anisotropic slope cost.\n\n"
                "The friction raster and DEM must share the same grid "
                "(identical extent and resolution). Non-positive or NoData "
                "friction cells are treated as impassable.")

    def createInstance(self):
        return FrictionCostSurfaceAlgorithm()
