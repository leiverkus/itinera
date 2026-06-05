# -*- coding: utf-8 -*-
"""From-Everywhere-To-Everywhere traversal-frequency surface."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination, QgsProcessingParameterFeatureSink,
    QgsProcessing, QgsFeature, QgsFields, QgsField, QgsGeometry, QgsPointXY,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QT_VERSION

# Field types: QGIS 4 / Qt6 dropped QVariant.Int and uses QMetaType; QGIS 3 /
# Qt5 still expects QVariant. Pick the right one for the running Qt version.
if QT_VERSION >= 0x060000:
    from qgis.PyQt.QtCore import QMetaType
    _FIELD_INT, _FIELD_DOUBLE = QMetaType.Type.Int, QMetaType.Type.Double
else:
    from qgis.PyQt.QtCore import QVariant
    _FIELD_INT, _FIELD_DOUBLE = QVariant.Int, QVariant.Double

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.fete import fete
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster, warn_if_large
from ._points import make_transform, source_to_nodes


class FeteAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    POINTS = "POINTS"
    COST_FN = "COST_FN"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    OUTPUT = "OUTPUT"
    PATHS = "PATHS"

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
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.MULTIPLIER, "Barrier / multiplier raster (optional)",
            optional=True))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Traversal frequency surface"))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.PATHS, "Individual paths (optional)",
            QgsProcessing.TypeVectorLine, optional=True,
            createByDefault=False))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        pts_src = self.parameterAsSource(parameters, self.POINTS, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        grid = RasterGrid.from_path(dem_layer.source())
        cost_fn = cf.COST_FUNCTIONS[cf.COST_FUNCTION_KEYS[fn_idx]]
        multiplier = load_aligned_raster(
            self.parameterAsRasterLayer(parameters, self.MULTIPLIER, context),
            grid, dem_layer.crs(), "Barrier/multiplier raster")

        warn_if_large(grid, nb, feedback)
        feedback.pushInfo("Building conductance matrix …")
        matrix, rows, cols = build_conductance(
            grid.array, grid.cellsize, cost_fn, neighbours=nb,
            multiplier=multiplier)

        xform = make_transform(
            pts_src.sourceCrs(), dem_layer.crs(), context.transformContext())
        nodes = source_to_nodes(pts_src, grid, cols, xform)

        if len(nodes) < 2:
            raise ValueError("FETE needs at least two points within the DEM.")

        feedback.pushInfo("Computing %d pairwise paths …"
                          % (len(nodes) * (len(nodes) - 1) // 2))

        path_fields = QgsFields()
        path_fields.append(QgsField("from_id", _FIELD_INT))
        path_fields.append(QgsField("to_id", _FIELD_INT))
        path_fields.append(QgsField("cost", _FIELD_DOUBLE))
        (paths_sink, paths_id) = self.parameterAsSink(
            parameters, self.PATHS, context, path_fields,
            QgsWkbTypes.LineString, dem_layer.crs())
        want_paths = paths_sink is not None

        def progress(frac):
            feedback.setProgress(100 * frac)
            if feedback.isCanceled():
                raise RuntimeError("Cancelled by user.")

        result = fete(matrix, nodes, rows * cols, progress=progress,
                      return_paths=want_paths)
        if want_paths:
            freq, paths = result
            for i, j, path_nodes, cost in paths:
                points = []
                for node in path_nodes:
                    pr, pc = divmod(node, cols)
                    x, y = grid.rowcol_to_xy(pr, pc)
                    points.append(QgsPointXY(x, y))
                feat = QgsFeature(path_fields)
                feat.setGeometry(QgsGeometry.fromPolylineXY(points))
                feat.setAttributes([i, j, float(cost)])
                paths_sink.addFeature(feat)
        else:
            freq = result

        grid.write_like(out_path, freq.reshape(rows, cols))

        outputs = {self.OUTPUT: out_path}
        if want_paths:
            outputs[self.PATHS] = paths_id
        return outputs

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
                "Cost scales with the square of the point count. Optionally "
                "also outputs the individual paths as a line layer (one "
                "feature per pair, with from_id/to_id/cost) — useful for "
                "inspecting routes, though n points produce n(n-1)/2 lines.")

    def createInstance(self):
        return FeteAlgorithm()
