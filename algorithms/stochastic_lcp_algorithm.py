# -*- coding: utf-8 -*-
"""Stochastic least-cost path: probabilistic corridor over N realisations."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString, QgsProcessing,
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
    COST_WEIGHTS = "COST_WEIGHTS"
    PARAM_JITTER = "PARAM_JITTER"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    N_ITER = "N_ITER"
    TOL = "TOL"
    CONV_METHOD = "CONV_METHOD"
    MIN_ITER = "MIN_ITER"
    RMSE = "RMSE"
    AUTOCORR = "AUTOCORR"
    MODEL = "MODEL"
    NUGGET = "NUGGET"
    DROP_FRACTION = "DROP_FRACTION"
    SEED = "SEED"
    OUTPUT = "OUTPUT"

    _CONV_METHODS = ["stabilisation", "precision"]

    _NEIGHBOUR_VALS = [4, 8, 16]
    _ERROR_MODELS = ["exponential", "spherical", "gaussian", "gaussian_filter"]
    _MODEL_LABELS = ["Exponential (variogram)", "Spherical (variogram)",
                     "Gaussian (variogram)", "Gaussian filter (fast)"]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.ORIGIN, "Origin point", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.DEST, "Destination point(s)",
            [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterEnum(
            self.COST_FN, "Cost function(s) to sample",
            options=cf.COST_FUNCTION_LABELS, allowMultiple=True,
            defaultValue=[0]))
        self.addParameter(QgsProcessingParameterString(
            self.COST_WEIGHTS,
            "Cost-function weights (comma-separated; blank = uniform)",
            defaultValue="", optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.PARAM_JITTER,
            "Cost-parameter jitter (±fraction; Pandolf mass/load/terrain)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0, maxValue=1.0))
        add_cost_params(self)
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Neighbourhood",
            options=["4", "8", "16"], defaultValue=1))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.MULTIPLIER, "Barrier / multiplier raster (optional)",
            optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.N_ITER, "Maximum iterations",
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=100, minValue=1))
        self.addParameter(QgsProcessingParameterNumber(
            self.TOL, "Convergence tolerance (0 = run all iterations)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0, maxValue=1.0))
        self.addParameter(QgsProcessingParameterEnum(
            self.CONV_METHOD, "Convergence criterion",
            options=["Stabilisation (max probability change)",
                     "Precision (max standard error)"],
            defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_ITER, "Minimum iterations (before convergence checks)",
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=20, minValue=1))
        self.addParameter(QgsProcessingParameterNumber(
            self.RMSE, "DEM vertical RMSE (m, 0 = no DEM error)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.AUTOCORR, "DEM error autocorrelation range (m)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterEnum(
            self.MODEL, "DEM error model", options=self._MODEL_LABELS,
            defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            self.NUGGET, "Nugget (uncorrelated fraction, 0–1; variogram only)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0, maxValue=0.99))
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
        fn_idxs = self.parameterAsEnums(parameters, self.COST_FN, context)
        if not fn_idxs:
            raise ValueError("Select at least one cost function.")
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        n_iter = self.parameterAsInt(parameters, self.N_ITER, context)
        tol_param = self.parameterAsDouble(parameters, self.TOL, context)
        tol = tol_param if tol_param > 0 else None
        convergence = self._CONV_METHODS[
            self.parameterAsEnum(parameters, self.CONV_METHOD, context)]
        min_iter = self.parameterAsInt(parameters, self.MIN_ITER, context)
        rmse = self.parameterAsDouble(parameters, self.RMSE, context)
        autocorr = self.parameterAsDouble(parameters, self.AUTOCORR, context)
        error_model = self._ERROR_MODELS[
            self.parameterAsEnum(parameters, self.MODEL, context)]
        nugget = self.parameterAsDouble(parameters, self.NUGGET, context)
        param_jitter = self.parameterAsDouble(
            parameters, self.PARAM_JITTER, context)
        drop = self.parameterAsDouble(parameters, self.DROP_FRACTION, context)
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        cost_fns = [cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[i]]
                    for i in fn_idxs]
        raw_weights = self.parameterAsString(
            parameters, self.COST_WEIGHTS, context).strip()
        cost_weights = None
        if raw_weights:
            try:
                cost_weights = [float(tok) for tok
                                in raw_weights.replace(";", ",").split(",")
                                if tok.strip()]
            except ValueError:
                raise ValueError("Cost-function weights must be numbers.")
            if len(cost_weights) != len(cost_fns):
                raise ValueError(
                    "Provide one weight per selected cost function (%d)."
                    % len(cost_fns))

        raw_seed = parameters.get(self.SEED)
        seed = None if raw_seed is None else self.parameterAsInt(
            parameters, self.SEED, context)

        if (rmse <= 0 and drop <= 0 and len(cost_fns) == 1
                and param_jitter <= 0):
            feedback.pushWarning(
                "No stochasticity set (RMSE, edge-drop, parameter jitter are 0 "
                "and a single cost function): the result is the deterministic "
                "least-cost path (probability 1 on it).")

        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cost_fns[0]
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

        metric_label = ("max std error" if convergence == "precision"
                        else "max probability change")

        def on_check(iterations, metric, ok):
            feedback.pushInfo("  iter %d: %s = %.4f%s"
                              % (iterations, metric_label, metric,
                                 " (converged)" if ok else ""))

        feedback.pushInfo(
            "Running up to %d stochastic realisations%s …"
            % (n_iter, "" if tol is None
               else " (stop at %s tolerance %g)" % (convergence, tol)))
        prob, _, diag = stochastic_lcp(
            grid.array, grid.cellsize, cost_fn, origin, dests, n_iter, rng,
            rmse=rmse, autocorr_range=autocorr, drop_fraction=drop,
            neighbours=nb, multiplier=multiplier, progress=progress,
            cost_params=cost_params, error_model=error_model, nugget=nugget,
            cost_fns=cost_fns, cost_weights=cost_weights,
            param_jitter=param_jitter, tol=tol, convergence=convergence,
            min_iter=min_iter, on_check=(on_check if tol else None),
            return_diagnostics=True)

        if diag["converged"]:
            feedback.pushInfo(
                "Converged after %d iterations (%s = %.4f < %g)."
                % (diag["iterations"], metric_label, diag["metric"], tol))
        elif tol is not None:
            feedback.pushWarning(
                "Did not converge within %d iterations (last %s = %.4f)."
                % (n_iter, metric_label, diag["metric"]))
        feedback.setProgress(100)

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
