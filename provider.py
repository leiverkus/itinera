# -*- coding: utf-8 -*-
"""Processing provider registering all Itinera algorithms."""

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

from .algorithms.slope_cs_algorithm import SlopeCostSurfaceAlgorithm
from .algorithms.friction_cs_algorithm import FrictionCostSurfaceAlgorithm
from .algorithms.lcp_algorithm import LcpAlgorithm
from .algorithms.lcc_algorithm import CorridorAlgorithm
from .algorithms.fete_algorithm import FeteAlgorithm
from .algorithms.validation_algorithm import PdiValidationAlgorithm


class ItineraProvider(QgsProcessingProvider):

    def loadAlgorithms(self):
        self.addAlgorithm(SlopeCostSurfaceAlgorithm())
        self.addAlgorithm(FrictionCostSurfaceAlgorithm())
        self.addAlgorithm(LcpAlgorithm())
        self.addAlgorithm(CorridorAlgorithm())
        self.addAlgorithm(FeteAlgorithm())
        self.addAlgorithm(PdiValidationAlgorithm())

    def id(self):
        return "itinera"

    def name(self):
        return "Itinera – Least-Cost Pathways"

    def icon(self):
        path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(path):
            return QIcon(path)
        return QgsProcessingProvider.icon(self)

    def longName(self):
        return "Itinera – Least-Cost Pathways (anisotropic movement modelling)"
