# -*- coding: utf-8 -*-
"""Multi-criteria cost builder: combine penalty rasters into one friction."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterString, QgsProcessingParameterEnum,
    QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
    QgsProcessing,
)

from ..core.raster_io import RasterGrid
from ..core.multicriteria import composite_friction
from ._raster_params import load_aligned_raster

_METHODS = ["sum", "product"]


def _parse_list(text, n, kind, cast):
    """Parse a comma-separated parameter string into n values (empty = None)."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        vals = [cast(tok) for tok in text.replace(";", ",").split(",")
                if tok.strip()]
    except ValueError:
        raise ValueError("%s must be a comma-separated list." % kind)
    if len(vals) != n:
        raise ValueError(
            "%s has %d value(s) but there are %d layers." % (kind, len(vals), n))
    return vals


class MultiCriteriaFrictionAlgorithm(QgsProcessingAlgorithm):
    LAYERS = "LAYERS"
    WEIGHTS = "WEIGHTS"
    INVERT = "INVERT"
    METHOD = "METHOD"
    OUT_MIN = "OUT_MIN"
    OUT_MAX = "OUT_MAX"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMultipleLayers(
            self.LAYERS, "Penalty rasters (hydrology, wetness, land cover, …)",
            layerType=QgsProcessing.TypeRaster))
        self.addParameter(QgsProcessingParameterString(
            self.WEIGHTS, "Weights (comma-separated, per layer; blank = equal)",
            defaultValue="", optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.INVERT, "Invert flags (comma-separated 0/1; blank = none)",
            defaultValue="", optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.METHOD, "Combination method",
            options=["Weighted sum", "Product (geometric)"], defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            self.OUT_MIN, "Output friction minimum (neutral = 1)",
            type=QgsProcessingParameterNumber.Double, defaultValue=1.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.OUT_MAX, "Output friction maximum",
            type=QgsProcessingParameterNumber.Double, defaultValue=10.0))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Composite friction surface"))

    def processAlgorithm(self, parameters, context, feedback):
        layers = self.parameterAsLayerList(parameters, self.LAYERS, context)
        if not layers:
            raise ValueError("Provide at least one penalty raster.")
        method = _METHODS[self.parameterAsEnum(parameters, self.METHOD, context)]
        out_min = self.parameterAsDouble(parameters, self.OUT_MIN, context)
        out_max = self.parameterAsDouble(parameters, self.OUT_MAX, context)
        if not 0.0 < out_min < out_max:
            raise ValueError(
                "Output friction range must satisfy 0 < minimum < maximum "
                "(both strictly positive): a minimum of 0 makes cells "
                "impassable and a negative minimum breaks the geometric mean.")
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        n = len(layers)
        weights = _parse_list(
            self.parameterAsString(parameters, self.WEIGHTS, context),
            n, "Weights", float)
        invert_raw = _parse_list(
            self.parameterAsString(parameters, self.INVERT, context),
            n, "Invert flags", lambda t: int(float(t)))
        invert = [bool(v) for v in invert_raw] if invert_raw else None

        feedback.pushInfo("Loading %d penalty raster(s) …" % n)
        grid = RasterGrid.from_path(layers[0].source())
        ref_crs = layers[0].crs()
        arrays = [grid.array]
        for i, layer in enumerate(layers[1:], start=2):
            arr = load_aligned_raster(
                layer, grid, ref_crs, "Penalty raster %d" % i)
            arrays.append(arr)

        feedback.pushInfo(
            "Combining (%s) into a composite friction in [%g, %g] …"
            % (method, out_min, out_max))
        composite = composite_friction(
            arrays, weights=weights, method=method, invert=invert,
            out_range=(out_min, out_max))

        grid.write_like(out_path, composite)
        return {self.OUTPUT: out_path}

    def name(self):
        return "multicriteriafriction"

    def displayName(self):
        return "Composite friction (multi-criteria)"

    def group(self):
        return "Cost surfaces"

    def groupId(self):
        return "costsurfaces"

    def shortHelpString(self):
        return ("Combines several penalty rasters (hydrology, wetness, land "
                "cover, intervisibility, …) into a single composite friction "
                "surface. This is a GENERIC HEURISTIC combiner — in the spirit "
                "of Herzog 2022 / Litvine et al. 2024, but not a reproduction of "
                "their domain-calibrated models. Each layer is min-max "
                "normalised to 0–1, optionally inverted (so a high input value "
                "becomes a low cost), weighted, and combined by a weighted sum "
                "(linear) or product (geometric) into a friction in the chosen "
                "range. NOTE: min-max normalisation is taken over each layer's "
                "own cells, so the result depends on the raster EXTENT — "
                "pre-normalise to fixed ranges for extent-stable results.\n\n"
                "The friction is a MULTIPLIER: 1 is neutral, > 1 discourages, "
                "< 1 prefers. NoData in any input makes that cell impassable "
                "(use this for hard-constraint masks).\n\n"
                "All rasters must share the first raster's grid (the rest are "
                "validated/aligned to it). Feed the result into Least-cost path "
                "/ Corridor / FETE as the barrier-multiplier raster, or into the "
                "Friction cost surface as the friction raster.")

    def createInstance(self):
        return MultiCriteriaFrictionAlgorithm()
