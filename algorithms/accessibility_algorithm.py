# -*- coding: utf-8 -*-
"""Accessibility / cost-catchment surface from source point(s)."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
    QgsProcessing,
)

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.accessibility import accessibility
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster, warn_if_large
from ._points import make_transform, source_to_nodes
from ._cost_params import add_cost_params, read_cost_params


class AccessibilityAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    SOURCE = "SOURCE"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    BUDGET = "BUDGET"
    BAND_INTERVAL = "BAND_INTERVAL"
    OUTPUT = "OUTPUT"
    CATCHMENT = "CATCHMENT"
    BANDS = "BANDS"

    _NEIGHBOUR_OPTS = ["4", "8", "16"]
    _NEIGHBOUR_VALS = [4, 8, 16]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.SOURCE, "Source point(s)", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterEnum(
            self.COST_FN, "Cost function",
            options=cf.COST_FUNCTION_LABELS, defaultValue=0))
        add_cost_params(self)
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Neighbourhood",
            options=self._NEIGHBOUR_OPTS, defaultValue=1))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.MULTIPLIER, "Barrier / multiplier raster (optional)",
            optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.BUDGET, "Catchment cost budget (0 = no catchment)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.BAND_INTERVAL, "Isochrone band interval (0 = no bands)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Cost-distance (accessibility) surface"))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.CATCHMENT, "Catchment mask (optional)",
            optional=True, createByDefault=False))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.BANDS, "Isochrone bands (optional)",
            optional=True, createByDefault=False))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        source_src = self.parameterAsSource(parameters, self.SOURCE, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        budget = self.parameterAsDouble(parameters, self.BUDGET, context)
        band_interval = self.parameterAsDouble(
            parameters, self.BAND_INTERVAL, context)
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        catch_path = self.parameterAsOutputLayer(
            parameters, self.CATCHMENT, context)
        bands_path = self.parameterAsOutputLayer(
            parameters, self.BANDS, context)

        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]
        cost_params = read_cost_params(self, parameters, context)
        multiplier = load_aligned_raster(
            self.parameterAsRasterLayer(parameters, self.MULTIPLIER, context),
            grid, dem_layer.crs(), "Barrier/multiplier raster")

        warn_if_large(grid, nb, feedback)
        feedback.pushInfo("Building conductance matrix …")
        matrix, rows, cols = build_conductance(
            grid.array, grid.cellsize, cost_fn, neighbours=nb,
            multiplier=multiplier, cost_params=cost_params)

        xform = make_transform(
            source_src.sourceCrs(), dem_layer.crs(), context.transformContext())
        nodes = source_to_nodes(source_src, grid, cols, xform)
        if not nodes:
            raise ValueError("No source point falls within the DEM extent.")

        want_catch = budget > 0 and bool(catch_path)
        want_bands = band_interval > 0 and bool(bands_path)
        feedback.pushInfo("Computing cost-distance accessibility …")
        cost, catchment, bands = accessibility(
            matrix, nodes,
            budget=budget if want_catch else None,
            band_interval=band_interval if want_bands else None)

        grid.write_like(out_path, cost.reshape(rows, cols))
        outputs = {self.OUTPUT: out_path}
        if want_catch:
            grid.write_like(catch_path, catchment.reshape(rows, cols))
            outputs[self.CATCHMENT] = catch_path
        if want_bands:
            grid.write_like(bands_path, bands.reshape(rows, cols))
            outputs[self.BANDS] = bands_path
        return outputs

    def name(self):
        return "accessibility"

    def displayName(self):
        return "Accessibility / cost catchment"

    def group(self):
        return "Cost surfaces"

    def groupId(self):
        return "costsurfaces"

    def shortHelpString(self):
        return ("Cost-distance accessibility from the source point(s): how "
                "costly each cell is to reach (a movement-potential surface; "
                "Verhagen et al. 2019), via anisotropic Dijkstra over the chosen "
                "cost function.\n\n"
                "Optionally also outputs a **catchment** mask (cells reachable "
                "within a cost budget) and **isochrone bands** (cost rings at the "
                "given interval). Use a projected CRS in metres so the cost "
                "budget / interval are in the cost function's units (e.g. seconds "
                "for Tobler). Unreachable cells are NoData in the catchment and "
                "bands.\n\n"
                "Combine with the Wheeled or Pack animal cost functions for "
                "vehicle/animal accessibility, or a composite friction raster as "
                "the multiplier.")

    def createInstance(self):
        return AccessibilityAlgorithm()
