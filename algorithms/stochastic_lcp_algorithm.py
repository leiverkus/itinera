# -*- coding: utf-8 -*-
"""Stochastic least-cost path: probabilistic corridor over N realisations."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
    QgsProcessing,
)
import numpy as np

from ..core.raster_io import RasterGrid
from ..core.stochastic import stochastic_lcp
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster, warn_if_large
from ._points import make_transform, source_to_nodes
from ._cost_params import add_cost_params, read_cost_params


class StochasticLcpAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    ORIGIN = "ORIGIN"
    DEST = "DEST"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    N_ITER = "N_ITER"
    RMSE = "RMSE"
    AUTOCORR = "AUTOCORR"
    DROP_FRACTION = "DROP_FRACTION"
    SEED = "SEED"
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
        add_cost_params(self)
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Neighbourhood",
            options=["4", "8", "16"], defaultValue=1))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.MULTIPLIER, "Barrier / multiplier raster (optional)",
            optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.N_ITER, "Iterations",
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=100, minValue=1))
        self.addParameter(QgsProcessingParameterNumber(
            self.RMSE, "DEM vertical RMSE (m, 0 = no DEM error)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.AUTOCORR, "DEM error autocorrelation range (m)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.DROP_FRACTION, "Random edge-drop fraction (0–1)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0, maxValue=1.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.SEED, "Random seed (optional, for reproducibility)",
            type=QgsProcessingParameterNumber.Integer, optional=True))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Traversal probability surface"))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        origin_src = self.parameterAsSource(parameters, self.ORIGIN, context)
        dest_src = self.parameterAsSource(parameters, self.DEST, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        n_iter = self.parameterAsInt(parameters, self.N_ITER, context)
        rmse = self.parameterAsDouble(parameters, self.RMSE, context)
        autocorr = self.parameterAsDouble(parameters, self.AUTOCORR, context)
        drop = self.parameterAsDouble(parameters, self.DROP_FRACTION, context)
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        raw_seed = parameters.get(self.SEED)
        seed = None if raw_seed is None else self.parameterAsInt(
            parameters, self.SEED, context)

        if rmse <= 0 and drop <= 0:
            feedback.pushWarning(
                "No stochasticity set (RMSE and edge-drop are 0): the result is "
                "the deterministic least-cost path (probability 1 on it).")

        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]
        cost_params = read_cost_params(self, parameters, context)
        multiplier = load_aligned_raster(
            self.parameterAsRasterLayer(parameters, self.MULTIPLIER, context),
            grid, dem_layer.crs(), "Barrier/multiplier raster")

        tc = context.transformContext()
        dem_crs = dem_layer.crs()
        origin = source_to_nodes(
            origin_src, grid, grid.cols,
            make_transform(origin_src.sourceCrs(), dem_crs, tc),
            first_only=True)
        if origin is None:
            raise ValueError("Origin point is outside the DEM extent.")
        dests = source_to_nodes(
            dest_src, grid, grid.cols,
            make_transform(dest_src.sourceCrs(), dem_crs, tc))
        if not dests:
            raise ValueError("No destination point falls within the DEM extent.")

        rng = np.random.default_rng(seed)
        warn_if_large(grid, nb, feedback)

        def progress(frac):
            feedback.setProgress(100 * frac)
            if feedback.isCanceled():
                raise RuntimeError("Cancelled by user.")

        feedback.pushInfo("Running %d stochastic realisations …" % n_iter)
        prob, _ = stochastic_lcp(
            grid.array, grid.cellsize, cost_fn, origin, dests, n_iter, rng,
            rmse=rmse, autocorr_range=autocorr, drop_fraction=drop,
            neighbours=nb, multiplier=multiplier, progress=progress,
            cost_params=cost_params)

        grid.write_like(out_path, prob.reshape(grid.rows, grid.cols))
        return {self.OUTPUT: out_path}

    def name(self):
        return "stochasticlcp"

    def displayName(self):
        return "Stochastic least-cost path (probabilistic corridor)"

    def group(self):
        return "Paths"

    def groupId(self):
        return "paths"

    def shortHelpString(self):
        return ("Monte-Carlo least-cost paths under uncertainty (Lewis 2021). "
                "Each iteration optionally adds a spatially-correlated DEM error "
                "(set RMSE > 0, plus an autocorrelation range) and/or randomly "
                "drops a fraction of edges, then computes the LCP from the "
                "origin to the destination(s). The output is the fraction of "
                "iterations in which each cell lies on a least-cost path — a "
                "probabilistic corridor in [0, 1]. Set a seed for reproducible "
                "runs. Cost scales with the iteration count.")

    def createInstance(self):
        return StochasticLcpAlgorithm()
