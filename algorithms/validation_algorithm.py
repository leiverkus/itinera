# -*- coding: utf-8 -*-
"""Validate a modelled path against a reference path (PDI + buffer overlap)."""

import math

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink, QgsProcessingParameterString,
    QgsProcessingParameterNumber, QgsProcessingOutputNumber, QgsProcessing,
    QgsFields, QgsField, QgsFeature,
)
from qgis.PyQt.QtCore import QT_VERSION

# Field types: QGIS 4 / Qt6 uses QMetaType; QGIS 3 / Qt5 expects QVariant.
if QT_VERSION >= 0x060000:
    from qgis.PyQt.QtCore import QMetaType
    _FIELD_DOUBLE = QMetaType.Type.Double
else:
    from qgis.PyQt.QtCore import QVariant
    _FIELD_DOUBLE = QVariant.Double

from ..core.validation import pdi, buffer_overlap
from ._points import make_transform, first_line_coords


class PdiValidationAlgorithm(QgsProcessingAlgorithm):
    MODELLED = "MODELLED"
    REFERENCE = "REFERENCE"
    OUT_PDI = "PDI"
    OUT_AREA = "AREA"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.MODELLED, "Modelled path (single line)",
            [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.REFERENCE, "Reference path (single line)",
            [QgsProcessing.TypeVectorLine]))
        self.addOutput(QgsProcessingOutputNumber(self.OUT_PDI,
                                                 "Path Deviation Index"))
        self.addOutput(QgsProcessingOutputNumber(self.OUT_AREA,
                                                 "Area between paths"))

    def processAlgorithm(self, parameters, context, feedback):
        modelled_src = self.parameterAsSource(parameters, self.MODELLED, context)
        reference_src = self.parameterAsSource(
            parameters, self.REFERENCE, context)

        modelled = first_line_coords(modelled_src)
        # Compare in the modelled layer's CRS; transform the reference if needed.
        ref_xform = make_transform(
            reference_src.sourceCrs(), modelled_src.sourceCrs(),
            context.transformContext())
        reference = first_line_coords(reference_src, ref_xform)

        if modelled is None or reference is None:
            raise ValueError("Both inputs must contain at least one line.")

        result = pdi(modelled, reference)
        feedback.pushInfo("PDI = %.4f map units (Jan et al. 1999: area / "
                          "straight-line O-D distance)" % result["pdi"])
        feedback.pushInfo("Area between paths = %.2f" % result["area"])
        feedback.pushInfo("Straight-line O-D distance = %.2f"
                          % result["straight_line_distance"])

        return {self.OUT_PDI: result["pdi"], self.OUT_AREA: result["area"]}

    def name(self):
        return "pdivalidation"

    def displayName(self):
        return "PDI validation"

    def group(self):
        return "Validation"

    def groupId(self):
        return "validation"

    def shortHelpString(self):
        return ("Path Deviation Index: area between a modelled and a reference "
                "path, divided by the reference length, giving the mean "
                "perpendicular deviation in map units. Lower is better. Use a "
                "projected CRS in metres (the reference is reprojected to the "
                "modelled layer's CRS if they differ).\n\n"
                "Reliable only for similar, roughly parallel, non-crossing "
                "lines: the shoelace area is meaningless for lines that cross "
                "or diverge strongly (see core/validation.py).")

    def createInstance(self):
        return PdiValidationAlgorithm()


class BufferValidationAlgorithm(QgsProcessingAlgorithm):
    """Goodchild & Hunter (1997) buffer validation as a similarity table."""

    MODELLED = "MODELLED"
    REFERENCE = "REFERENCE"
    DISTANCES = "DISTANCES"
    STEP = "STEP"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.MODELLED, "Modelled path (single line)",
            [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.REFERENCE, "Reference path (single line)",
            [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterString(
            self.DISTANCES, "Buffer distances (map units, comma-separated)",
            defaultValue="50,100,250,500,1000"))
        self.addParameter(QgsProcessingParameterNumber(
            self.STEP, "Sampling step (map units, 0 = auto)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Buffer similarity table",
            QgsProcessing.TypeVector))

    def processAlgorithm(self, parameters, context, feedback):
        modelled_src = self.parameterAsSource(parameters, self.MODELLED, context)
        reference_src = self.parameterAsSource(
            parameters, self.REFERENCE, context)

        modelled = first_line_coords(modelled_src)
        ref_xform = make_transform(
            reference_src.sourceCrs(), modelled_src.sourceCrs(),
            context.transformContext())
        reference = first_line_coords(reference_src, ref_xform)
        if modelled is None or reference is None:
            raise ValueError("Both inputs must contain at least one line.")

        raw = self.parameterAsString(parameters, self.DISTANCES, context)
        try:
            distances = [float(tok) for tok in raw.replace(";", ",").split(",")
                         if tok.strip()]
        except ValueError:
            raise ValueError(
                "Buffer distances must be a comma-separated list of numbers.")
        if not distances:
            raise ValueError("Provide at least one buffer distance.")
        if any((not math.isfinite(d)) or d <= 0 for d in distances):
            raise ValueError(
                "Buffer distances must be finite and strictly positive (> 0); "
                "got %s." % ", ".join("%g" % d for d in distances))

        step = self.parameterAsDouble(parameters, self.STEP, context)
        step = step if step > 0 else None

        fields = QgsFields()
        fields.append(QgsField("distance", _FIELD_DOUBLE))
        fields.append(QgsField("similarity", _FIELD_DOUBLE))
        (sink, sink_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, fields)

        for row in buffer_overlap(modelled, reference, distances, step=step):
            feat = QgsFeature(fields)
            feat.setAttributes([row["distance"], row["similarity"]])
            sink.addFeature(feat)
            feedback.pushInfo("buffer %.3g: %.2f %% of the modelled path within"
                              % (row["distance"], row["similarity"]))

        return {self.OUTPUT: sink_id}

    def name(self):
        return "buffervalidation"

    def displayName(self):
        return "Buffer validation"

    def group(self):
        return "Validation"

    def groupId(self):
        return "validation"

    def shortHelpString(self):
        return ("Buffer-overlap validation (Goodchild & Hunter 1997): for each "
                "buffer distance, the share (%) of the modelled path's length "
                "lying within that distance of the reference path. Higher is "
                "better; 100 % means the whole modelled path is within the "
                "tolerance buffer. Output is a table of (distance, similarity). "
                "Use a projected CRS in metres (the reference is reprojected to "
                "the modelled layer's CRS if they differ). The modelled path is "
                "densified at the sampling step (auto = min(distances)/20) to "
                "approximate the length share.")

    def createInstance(self):
        return BufferValidationAlgorithm()
