# -*- coding: utf-8 -*-
"""Sensitivity analysis: sweep cost function x connectivity for one O/D pair.

Re-runs the least-cost path for every selected (cost function, connectivity)
combination between a single origin and destination, then summarises how much
the route varies. A route that is stable across reasonable modelling choices is
more trustworthy than one that swings wildly (Herzog 2022; Verhagen 2019).
"""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterEnum,
    QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
    QgsProcessingParameterFeatureSink, QgsProcessingOutputNumber,
    QgsProcessing, QgsFeature, QgsFields, QgsField, QgsGeometry, QgsPointXY,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QT_VERSION

# Field types: QGIS 4 / Qt6 uses QMetaType; QGIS 3 / Qt5 expects QVariant.
if QT_VERSION >= 0x060000:
    from qgis.PyQt.QtCore import QMetaType
    _FIELD_INT = QMetaType.Type.Int
    _FIELD_DOUBLE = QMetaType.Type.Double
    _FIELD_STR = QMetaType.Type.QString
else:
    from qgis.PyQt.QtCore import QVariant
    _FIELD_INT = QVariant.Int
    _FIELD_DOUBLE = QVariant.Double
    _FIELD_STR = QVariant.String

import numpy as np

from ..core.raster_io import RasterGrid
from ..core.conductance import build_conductance
from ..core.lcp import least_cost_path
from ..core.validation import mean_pairwise_overlap
from ..core import cost_functions as cf
from ._raster_params import load_aligned_raster, warn_if_large
from ._points import make_transform, source_to_nodes
from ._cost_params import add_cost_params, read_cost_params


class SensitivityAnalysisAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    ORIGIN = "ORIGIN"
    DEST = "DEST"
    COST_FNS = "COST_FNS"
    NEIGHBOURS = "NEIGHBOURS"
    MULTIPLIER = "MULTIPLIER"
    STABILITY_BUFFER = "STABILITY_BUFFER"
    AGREEMENT = "AGREEMENT"
    SUMMARY = "SUMMARY"
    PATHS = "PATHS"
    OUT_STABILITY = "STABILITY"

    _NEIGHBOUR_OPTS = ["4", "8", "16"]
    _NEIGHBOUR_VALS = [4, 8, 16]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.ORIGIN, "Origin point", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.DEST, "Destination point", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterEnum(
            self.COST_FNS, "Cost functions to sweep",
            options=cf.COST_FUNCTION_LABELS, allowMultiple=True,
            defaultValue=list(range(len(cf.COST_FUNCTION_LABELS)))))
        self.addParameter(QgsProcessingParameterEnum(
            self.NEIGHBOURS, "Connectivities to sweep",
            options=self._NEIGHBOUR_OPTS, allowMultiple=True,
            defaultValue=[0, 1, 2]))
        add_cost_params(self)
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.MULTIPLIER, "Barrier / multiplier raster (optional)",
            optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.STABILITY_BUFFER,
            "Stability tolerance buffer (map units, 0 = one DEM cell)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.AGREEMENT, "Agreement surface (path frequency)"))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.SUMMARY, "Summary table", QgsProcessing.TypeVector))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.PATHS, "Individual paths (optional)",
            QgsProcessing.TypeVectorLine, optional=True,
            createByDefault=False))
        self.addOutput(QgsProcessingOutputNumber(
            self.OUT_STABILITY, "Route stability (mean pairwise overlap %)"))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        origin_src = self.parameterAsSource(parameters, self.ORIGIN, context)
        dest_src = self.parameterAsSource(parameters, self.DEST, context)
        fn_idxs = self.parameterAsEnums(parameters, self.COST_FNS, context)
        nb_idxs = self.parameterAsEnums(parameters, self.NEIGHBOURS, context)
        if not fn_idxs:
            raise ValueError("Select at least one cost function.")
        if not nb_idxs:
            raise ValueError("Select at least one connectivity.")

        grid = RasterGrid.from_path(dem_layer.source())
        cost_params = read_cost_params(self, parameters, context)
        multiplier = load_aligned_raster(
            self.parameterAsRasterLayer(parameters, self.MULTIPLIER, context),
            grid, dem_layer.crs(), "Barrier/multiplier raster")

        tc = context.transformContext()
        dem_crs = dem_layer.crs()
        cols = grid.cols
        origin_node = source_to_nodes(
            origin_src, grid, cols,
            make_transform(origin_src.sourceCrs(), dem_crs, tc),
            first_only=True)
        if origin_node is None:
            raise ValueError("Origin point is outside the DEM extent.")
        dest_node = source_to_nodes(
            dest_src, grid, cols,
            make_transform(dest_src.sourceCrs(), dem_crs, tc),
            first_only=True)
        if dest_node is None:
            raise ValueError("Destination point is outside the DEM extent.")

        tol = self.parameterAsDouble(parameters, self.STABILITY_BUFFER, context)
        if tol <= 0:
            tol = grid.cellsize

        max_nb = max(self._NEIGHBOUR_VALS[i] for i in nb_idxs)
        warn_if_large(grid, max_nb, feedback)
        feedback.pushInfo(
            "Sweeping %d configuration(s) …" % (len(fn_idxs) * len(nb_idxs)))

        # Output sinks.
        summary_fields = QgsFields()
        summary_fields.append(QgsField("cost_function", _FIELD_STR))
        summary_fields.append(QgsField("connectivity", _FIELD_INT))
        summary_fields.append(QgsField("length_m", _FIELD_DOUBLE))
        summary_fields.append(QgsField("total_cost", _FIELD_DOUBLE))
        summary_fields.append(QgsField("n_cells", _FIELD_INT))
        summary_fields.append(QgsField("reachable", _FIELD_INT))
        (summary_sink, summary_id) = self.parameterAsSink(
            parameters, self.SUMMARY, context, summary_fields)

        path_fields = QgsFields()
        path_fields.append(QgsField("cost_function", _FIELD_STR))
        path_fields.append(QgsField("connectivity", _FIELD_INT))
        path_fields.append(QgsField("length_m", _FIELD_DOUBLE))
        path_fields.append(QgsField("total_cost", _FIELD_DOUBLE))
        (paths_sink, paths_id) = self.parameterAsSink(
            parameters, self.PATHS, context, path_fields,
            QgsWkbTypes.LineString, dem_crs)
        want_paths = paths_sink is not None

        agreement = np.zeros(grid.rows * cols, dtype=np.int32)
        coord_paths = []        # Nx2 arrays for the stability metric
        configs = [(fk, nb) for fk in fn_idxs for nb in nb_idxs]
        n_done = 0

        for fn_idx, nb_idx in configs:
            if feedback.isCanceled():
                break
            fn_key = cf.COST_FUNCTION_KEYS[fn_idx]
            nb = self._NEIGHBOUR_VALS[nb_idx]
            cost_fn = cf.COST_FUNCTIONS[fn_key]

            matrix, _, _ = build_conductance(
                grid.array, grid.cellsize, cost_fn, neighbours=nb,
                multiplier=multiplier, cost_params=cost_params)
            path_nodes, total = least_cost_path(matrix, origin_node, dest_node)

            n_done += 1
            feedback.setProgress(100 * n_done / len(configs))

            if not path_nodes:
                feedback.pushWarning(
                    "No path for %s / %d-connectivity." % (fn_key, nb))
                summary_sink.addFeature(self._summary_row(
                    summary_fields, fn_key, nb, 0.0, float("inf"), 0, 0))
                continue

            nodes = np.asarray(path_nodes)
            agreement[np.unique(nodes)] += 1
            coords = np.column_stack(grid.rowcol_to_xy(*np.divmod(nodes, cols)))
            length = float(np.sum(np.hypot(*np.diff(coords, axis=0).T)))
            coord_paths.append(coords)

            summary_sink.addFeature(self._summary_row(
                summary_fields, fn_key, nb, length, float(total),
                len(path_nodes), 1))

            if want_paths:
                feat = QgsFeature(path_fields)
                feat.setGeometry(QgsGeometry.fromPolylineXY(
                    [QgsPointXY(x, y) for x, y in coords]))
                feat.setAttributes([fn_key, nb, length, float(total)])
                paths_sink.addFeature(feat)

        out_path = self.parameterAsOutputLayer(
            parameters, self.AGREEMENT, context)
        grid.write_like(
            out_path, agreement.reshape(grid.rows, cols).astype(np.float32))

        stability = mean_pairwise_overlap(coord_paths, tol)
        feedback.pushInfo(
            "%d of %d configurations reached the destination."
            % (len(coord_paths), len(configs)))
        feedback.pushInfo(
            "Route stability (mean pairwise overlap at %.3g map units) = %s"
            % (tol, "n/a" if np.isnan(stability) else "%.1f %%" % stability))

        outputs = {
            self.AGREEMENT: out_path,
            self.SUMMARY: summary_id,
            self.OUT_STABILITY: float(stability),
        }
        if want_paths:
            outputs[self.PATHS] = paths_id
        return outputs

    @staticmethod
    def _summary_row(fields, fn_key, nb, length, total, n_cells, reachable):
        feat = QgsFeature(fields)
        feat.setAttributes([fn_key, nb, length, total, n_cells, reachable])
        return feat

    def name(self):
        return "sensitivityanalysis"

    def displayName(self):
        return "Sensitivity analysis (cost function x connectivity)"

    def group(self):
        return "Paths"

    def groupId(self):
        return "paths"

    def shortHelpString(self):
        return ("Sweeps the selected cost functions and connectivities for one "
                "origin/destination pair and summarises how much the route "
                "varies (Herzog 2022; Verhagen 2019).\n\n"
                "Outputs: an agreement raster (per-cell count of how many "
                "configurations' paths cross it), a summary table (one row per "
                "configuration: length, total cost, cell count, reachability), "
                "an optional individual-paths line layer, and a route-stability "
                "scalar — the mean pairwise buffer-overlap across the reachable "
                "paths at the tolerance buffer (100 % = all routes agree).\n\n"
                "Unreachable configurations are reported in the table and "
                "skipped from the agreement surface and stability metric. Limit "
                "the selection to keep the full cost-function x connectivity "
                "sweep tractable on large DEMs.")

    def createInstance(self):
        return SensitivityAnalysisAlgorithm()
