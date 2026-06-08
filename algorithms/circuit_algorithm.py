# -*- coding: utf-8 -*-
"""Circuit-theory connectivity: current density / pinch points, and barriers."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
    QgsProcessing,
)

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.circuit import current_density, restoration_score
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster, warn_if_large
from ._points import make_transform, source_to_nodes
from ._cost_params import add_cost_params, read_cost_params

# The current-density solve factorises a Laplacian (heavier than Dijkstra).
_CIRCUIT_RECOMMENDED_MAX_CELLS = 250_000


def _resolve(src, grid, cols, dem_crs, tc, what):
    nodes = source_to_nodes(
        src, grid, cols, make_transform(src.sourceCrs(), dem_crs, tc))
    if not nodes:
        raise ValueError("No %s point falls within the DEM extent." % what)
    return nodes


class CircuitCurrentAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    SOURCE = "SOURCE"
    TARGET = "TARGET"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    PINCH_TOLERANCE = "PINCH_TOLERANCE"
    OUTPUT = "OUTPUT"
    PINCH_OUTPUT = "PINCH_OUTPUT"

    _NEIGHBOUR_VALS = [4, 8, 16]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.SOURCE, "Source point(s)", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.TARGET, "Target point(s)", [QgsProcessing.TypeVectorPoint]))
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
            self.PINCH_TOLERANCE,
            "Pinch-point corridor tolerance (cost units, 0 = none)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Current-density surface"))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.PINCH_OUTPUT, "Pinch points (optional)",
            optional=True, createByDefault=False))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        source_src = self.parameterAsSource(parameters, self.SOURCE, context)
        target_src = self.parameterAsSource(parameters, self.TARGET, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        tol = self.parameterAsDouble(parameters, self.PINCH_TOLERANCE, context)
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        pinch_path = self.parameterAsOutputLayer(
            parameters, self.PINCH_OUTPUT, context)

        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]
        cost_params = read_cost_params(self, parameters, context)
        multiplier = load_aligned_raster(
            self.parameterAsRasterLayer(parameters, self.MULTIPLIER, context),
            grid, dem_layer.crs(), "Barrier/multiplier raster")

        warn_if_large(grid, nb, feedback)
        if grid.rows * grid.cols > _CIRCUIT_RECOMMENDED_MAX_CELLS:
            feedback.pushWarning(
                "Circuit current density factorises a sparse Laplacian, heavier "
                "than the Dijkstra tools: %d cells (> %d recommended). Clip or "
                "resample the DEM first." % (grid.rows * grid.cols,
                                             _CIRCUIT_RECOMMENDED_MAX_CELLS))

        feedback.pushInfo("Building conductance matrix …")
        matrix, rows, cols = build_conductance(
            grid.array, grid.cellsize, cost_fn, neighbours=nb,
            multiplier=multiplier, cost_params=cost_params)

        tc = context.transformContext()
        dem_crs = dem_layer.crs()
        sources = _resolve(source_src, grid, cols, dem_crs, tc, "source")
        targets = _resolve(target_src, grid, cols, dem_crs, tc, "target")

        def progress(frac):
            feedback.setProgress(100 * frac)
            if feedback.isCanceled():
                raise RuntimeError("Cancelled by user.")

        want_pinch = tol > 0 and bool(pinch_path)
        feedback.pushInfo("Solving circuit current density (symmetrised) …")
        if tol > 0:
            current, _, pinch = current_density(
                matrix, sources, targets, corridor_tolerance=tol,
                progress=progress)
        else:
            current, _ = current_density(
                matrix, sources, targets, progress=progress)
            pinch = None

        grid.write_like(out_path, current.reshape(grid.rows, grid.cols))
        outputs = {self.OUTPUT: out_path}
        if want_pinch:
            grid.write_like(pinch_path, pinch.reshape(grid.rows, grid.cols))
            outputs[self.PINCH_OUTPUT] = pinch_path
        return outputs

    def name(self):
        return "circuitcurrentdensity"

    def displayName(self):
        return "Circuit current density / pinch points"

    def group(self):
        return "Connectivity"

    def groupId(self):
        return "connectivity"

    def shortHelpString(self):
        return ("Circuit-theory current density: movement modelled as electrical "
                "current flow from the source(s) to the target(s) over the "
                "resistance surface (McRae et al. 2008). High-current cells are "
                "where movement concentrates; the peaks within the least-cost "
                "corridor are pinch points (set a corridor tolerance > 0 and an "
                "optional pinch-point output).\n\n"
                "Classic circuit theory is an UNDIRECTED resistor network, so "
                "the anisotropic conductance is symmetrised ((G+Gᵀ)/2) here. For "
                "the direction-preserving (anisotropic) current, use the "
                "Randomized shortest paths (RSP) tool with a small theta "
                "instead.\n\n"
                "Factorises a sparse Laplacian — heavier than the Dijkstra "
                "tools; clip or resample very large DEMs.")

    def createInstance(self):
        return CircuitCurrentAlgorithm()


class BarrierAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    SOURCE = "SOURCE"
    TARGET = "TARGET"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    WINDOW = "WINDOW"
    IMPROVED = "IMPROVED_RESISTANCE"
    OUTPUT = "OUTPUT"

    _NEIGHBOUR_VALS = [4, 8, 16]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.SOURCE, "Source point(s)", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.TARGET, "Target point(s)", [QgsProcessing.TypeVectorPoint]))
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
            self.WINDOW, "Search-window diameter (map units)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=100.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.IMPROVED,
            "Restored resistance R' (cost per metre of restored land)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=1.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Restoration / barrier improvement surface"))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        source_src = self.parameterAsSource(parameters, self.SOURCE, context)
        target_src = self.parameterAsSource(parameters, self.TARGET, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        window = self.parameterAsDouble(parameters, self.WINDOW, context)
        improved = self.parameterAsDouble(parameters, self.IMPROVED, context)
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

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

        tc = context.transformContext()
        dem_crs = dem_layer.crs()
        sources = _resolve(source_src, grid, cols, dem_crs, tc, "source")
        targets = _resolve(target_src, grid, cols, dem_crs, tc, "target")

        window_cells = max(1, round(window / grid.cellsize))

        def progress(frac):
            feedback.setProgress(100 * frac)
            if feedback.isCanceled():
                raise RuntimeError("Cancelled by user.")

        feedback.pushInfo(
            "Computing restoration improvement (window = %d cells) …"
            % window_cells)
        score = restoration_score(
            matrix, rows, cols, sources, targets, grid.cellsize,
            window_cells, improved_resistance=improved, progress=progress)

        grid.write_like(out_path, score.reshape(rows, cols))
        return {self.OUTPUT: out_path}

    def name(self):
        return "connectivitybarriers"

    def displayName(self):
        return "Connectivity barriers / restoration (McRae 2012)"

    def group(self):
        return "Connectivity"

    def groupId(self):
        return "connectivity"

    def shortHelpString(self):
        return ("Detects barriers and quantifies restoration benefit (McRae et "
                "al. 2012): for each cell, how much the least-cost corridor "
                "between the source(s) and target(s) would improve if a strip of "
                "land across the search window were restored to the resistance "
                "R'. High scores mark the strongest barriers — where restoration "
                "(or, read inversely, blocking) most affects connectivity.\n\n"
                "A moving-window approximation over the accumulated-cost corridor "
                "surfaces (no per-cell re-solve). R' is the cost-per-metre of "
                "restored land in the chosen cost model's units — scale-"
                "dependent, calibrate per study.")

    def createInstance(self):
        return BarrierAlgorithm()
