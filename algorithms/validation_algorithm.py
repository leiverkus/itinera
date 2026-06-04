# -*- coding: utf-8 -*-
"""Validate a modelled path against a reference path via the PDI."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource,
    QgsProcessingOutputNumber, QgsProcessing, QgsFeatureRequest,
)
import numpy as np

from ..core.validation import pdi


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
        modelled = self._first_line_coords(
            self.parameterAsSource(parameters, self.MODELLED, context))
        reference = self._first_line_coords(
            self.parameterAsSource(parameters, self.REFERENCE, context))

        if modelled is None or reference is None:
            raise ValueError("Both inputs must contain at least one line.")

        result = pdi(modelled, reference)
        feedback.pushInfo("PDI = %.4f map units (mean deviation)"
                          % result["pdi"])
        feedback.pushInfo("Area between paths = %.2f" % result["area"])
        feedback.pushInfo("Reference length = %.2f" % result["reference_length"])

        return {self.OUT_PDI: result["pdi"], self.OUT_AREA: result["area"]}

    @staticmethod
    def _first_line_coords(source):
        for feat in source.getFeatures(QgsFeatureRequest()):
            geom = feat.geometry()
            if geom.isMultipart():
                line = geom.asMultiPolyline()[0]
            else:
                line = geom.asPolyline()
            return np.array([[p.x(), p.y()] for p in line], dtype=float)
        return None

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
                "perpendicular deviation in map units. Lower is better. Both "
                "layers should be in the same projected CRS.")

    def createInstance(self):
        return PdiValidationAlgorithm()
