# -*- coding: utf-8 -*-
"""Least-cost path between an origin and one or more destinations."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink, QgsProcessing, QgsFeatureRequest,
    QgsFeature, QgsFields, QgsField, QgsGeometry, QgsPointXY, QgsWkbTypes,
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
from ..core.lcp import least_cost_path
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster, warn_if_large
from ._points import make_transform, feature_xy, source_to_nodes


class LcpAlgorithm(QgsProcessingAlgorithm):
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
            self.DEST, "Destination point(s)",
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
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Least-cost path(s)",
            QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        origin_src = self.parameterAsSource(parameters, self.ORIGIN, context)
        dest_src = self.parameterAsSource(parameters, self.DEST, context)
        fn_idx = self.parameterAsEnum(parameters, self.COST_FN, context)
        nb = self._NEIGHBOUR_VALS[
            self.parameterAsEnum(parameters, self.NEIGHBOURS, context)]

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

        tc = context.transformContext()
        dem_crs = dem_layer.crs()
        origin_node = source_to_nodes(
            origin_src, grid, cols,
            make_transform(origin_src.sourceCrs(), dem_crs, tc),
            first_only=True)
        if origin_node is None:
            raise ValueError("Origin point is outside the DEM extent.")

        fields = QgsFields()
        fields.append(QgsField("dest_id", _FIELD_INT))
        fields.append(QgsField("cost", _FIELD_DOUBLE))
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, fields,
            QgsWkbTypes.LineString, grid_crs(dem_layer))

        dest_xform = make_transform(dest_src.sourceCrs(), dem_crs, tc)
        dests = list(dest_src.getFeatures(QgsFeatureRequest()))
        for i, feat in enumerate(dests):
            x, y = feature_xy(feat, dest_xform)
            r, c = grid.xy_to_rowcol(x, y)
            if not grid.in_bounds(r, c):
                feedback.pushWarning("Destination %d outside DEM – skipped." % i)
                continue
            dest_node = r * cols + c

            path_nodes, total = least_cost_path(matrix, origin_node, dest_node)
            if not path_nodes:
                feedback.pushWarning("No path to destination %d." % i)
                continue

            points = []
            for node in path_nodes:
                pr, pc = divmod(node, cols)
                x, y = grid.rowcol_to_xy(pr, pc)
                points.append(QgsPointXY(x, y))

            out_feat = QgsFeature(fields)
            out_feat.setGeometry(QgsGeometry.fromPolylineXY(points))
            out_feat.setAttributes([i, float(total)])
            sink.addFeature(out_feat)
            feedback.setProgress(100 * (i + 1) / max(len(dests), 1))

        return {self.OUTPUT: dest_id}

    def name(self):
        return "leastcostpath"

    def displayName(self):
        return "Least-cost path"

    def group(self):
        return "Paths"

    def groupId(self):
        return "paths"

    def shortHelpString(self):
        return ("Computes anisotropic least-cost path(s) from one origin to "
                "one or more destinations. Output is a line layer with the "
                "accumulated cost per path.")

    def createInstance(self):
        return LcpAlgorithm()


def grid_crs(layer):
    return layer.crs()
