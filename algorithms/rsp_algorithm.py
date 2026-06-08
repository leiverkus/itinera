# -*- coding: utf-8 -*-
"""Randomized Shortest Paths: a theta-tunable movement-density corridor."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterNumber, QgsProcessingParameterBoolean,
    QgsProcessingParameterRasterDestination, QgsProcessingOutputNumber,
    QgsProcessing,
)

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.rsp import rsp_passages
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster, warn_if_large
from ._points import make_transform, source_to_nodes
from ._cost_params import add_cost_params, read_cost_params

# RSP factorises (I - W); its LU fill-in is heavier than Dijkstra, so warn well
# below the graph-algorithm cell threshold.
_RSP_RECOMMENDED_MAX_CELLS = 250_000


class RspAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    ORIGIN = "ORIGIN"
    DEST = "DEST"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    THETA = "THETA"
    NORMALIZE = "NORMALIZE"
    OUTPUT = "OUTPUT"
    OUT_DISTANCE = "DISTANCE"

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
        add_cost_params(self)
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Neighbourhood",
            options=["4", "8", "16"], defaultValue=1))
        self.addParameter(QgsProcessingParameterNumber(
            self.THETA, "Theta (randomness; large = least-cost path, "
                        "small = random walk / circuit)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=1.0, minValue=1e-6))
        self.addParameter(QgsProcessingParameterBoolean(
            self.NORMALIZE, "Normalise costs (theta ~ 1 meaningful; "
                            "uncheck for raw gdistance-style theta)",
            defaultValue=True))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.MULTIPLIER, "Barrier / multiplier raster (optional)",
            optional=True))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "RSP movement-density surface"))
        self.addOutput(QgsProcessingOutputNumber(
            self.OUT_DISTANCE, "Free-energy distance (nearest destination)"))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        origin_src = self.parameterAsSource(parameters, self.ORIGIN, context)
        dest_src = self.parameterAsSource(parameters, self.DEST, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        theta = self.parameterAsDouble(parameters, self.THETA, context)
        normalize = self.parameterAsBool(parameters, self.NORMALIZE, context)
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]
        cost_params = read_cost_params(self, parameters, context)
        multiplier = load_aligned_raster(
            self.parameterAsRasterLayer(parameters, self.MULTIPLIER, context),
            grid, dem_layer.crs(), "Barrier/multiplier raster")

        warn_if_large(grid, nb, feedback)
        if grid.rows * grid.cols > _RSP_RECOMMENDED_MAX_CELLS:
            feedback.pushWarning(
                "RSP solves a sparse linear system (LU), which is heavier than "
                "the Dijkstra-based tools: %d cells (> %d recommended for RSP). "
                "Consider clipping the DEM or running Resample DEM (block mean) "
                "first." % (grid.rows * grid.cols, _RSP_RECOMMENDED_MAX_CELLS))

        feedback.pushInfo("Building conductance matrix …")
        matrix, rows, cols = build_conductance(
            grid.array, grid.cellsize, cost_fn, neighbours=nb,
            multiplier=multiplier, cost_params=cost_params)

        tc = context.transformContext()
        dem_crs = dem_layer.crs()
        origin = source_to_nodes(
            origin_src, grid, cols,
            make_transform(origin_src.sourceCrs(), dem_crs, tc),
            first_only=True)
        if origin is None:
            raise ValueError("Origin point is outside the DEM extent.")
        dests = source_to_nodes(
            dest_src, grid, cols,
            make_transform(dest_src.sourceCrs(), dem_crs, tc))
        if not dests:
            raise ValueError("No destination point falls within the DEM extent.")

        def progress(frac):
            feedback.setProgress(100 * frac)
            if feedback.isCanceled():
                raise RuntimeError("Cancelled by user.")

        feedback.pushInfo(
            "Solving RSP (theta = %g, normalise = %s) …" % (theta, normalize))
        passages, _, distances = rsp_passages(
            matrix, origin, dests, theta, normalize=normalize,
            return_distance=True, progress=progress)

        finite = [d for d in distances if d == d and d != float("inf")]
        for i, d in enumerate(distances):
            if d == float("inf") or d != d:
                feedback.pushWarning(
                    "Destination %d not reachable from the origin." % i)
            else:
                feedback.pushInfo(
                    "Free-energy distance to destination %d = %.2f" % (i, d))
        nearest = min(finite) if finite else float("inf")

        grid.write_like(out_path, passages.reshape(grid.rows, grid.cols))
        return {self.OUTPUT: out_path, self.OUT_DISTANCE: nearest}

    def name(self):
        return "randomizedshortestpaths"

    def displayName(self):
        return "Randomized shortest paths (RSP)"

    def group(self):
        return "Paths"

    def groupId(self):
        return "paths"

    def shortHelpString(self):
        return ("Randomized Shortest Paths: a single parameter theta tunes "
                "between the deterministic least-cost path (large theta) and "
                "the random-walk / circuit current density (small theta), with "
                "realistic exploratory movement in between (Panzacchi et al. "
                "2015; van Etten 2017).\n\n"
                "Output is a movement-density surface (expected passages per "
                "cell, normalised to 0–1) from the origin to the "
                "destination(s), plus the RSP free-energy distance to the "
                "nearest destination.\n\n"
                "With 'Normalise costs' on (default), costs are divided by their "
                "mean so theta ≈ 1 is a good starting point for any cost "
                "function; sweep theta up for path-like, down for diffuse "
                "results. With normalisation off, theta is applied to the raw "
                "cost units (gdistance-style) and a much smaller theta (e.g. "
                "1e-3) is usually needed. theta is scale-dependent — calibrate "
                "per study.\n\n"
                "RSP factorises a sparse linear system and is heavier than the "
                "Dijkstra tools; clip or resample very large DEMs.")

    def createInstance(self):
        return RspAlgorithm()
