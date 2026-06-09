# -*- coding: utf-8 -*-
"""Processing provider registering all Itinera algorithms."""

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

from .algorithms.slope_cs_algorithm import SlopeCostSurfaceAlgorithm
from .algorithms.friction_cs_algorithm import FrictionCostSurfaceAlgorithm
from .algorithms.lcp_algorithm import LcpAlgorithm
from .algorithms.stochastic_lcp_algorithm import StochasticLcpAlgorithm
from .algorithms.lcc_algorithm import CorridorAlgorithm
from .algorithms.fete_algorithm import FeteAlgorithm
from .algorithms.rsp_algorithm import RspAlgorithm
from .algorithms.circuit_algorithm import (
    CircuitCurrentAlgorithm, BarrierAlgorithm,
)
from .algorithms.multicriteria_algorithm import MultiCriteriaFrictionAlgorithm
from .algorithms.validation_algorithm import (
    PdiValidationAlgorithm, BufferValidationAlgorithm,
)
from .algorithms.sensitivity_algorithm import SensitivityAnalysisAlgorithm
from .algorithms.resample_dem_algorithm import ResampleDemAlgorithm
from .algorithms.dem_error_algorithm import DemErrorAlgorithm


class ItineraProvider(QgsProcessingProvider):

    def loadAlgorithms(self):
        self.addAlgorithm(SlopeCostSurfaceAlgorithm())
        self.addAlgorithm(FrictionCostSurfaceAlgorithm())
        self.addAlgorithm(MultiCriteriaFrictionAlgorithm())
        self.addAlgorithm(LcpAlgorithm())
        self.addAlgorithm(StochasticLcpAlgorithm())
        self.addAlgorithm(CorridorAlgorithm())
        self.addAlgorithm(FeteAlgorithm())
        self.addAlgorithm(RspAlgorithm())
        self.addAlgorithm(CircuitCurrentAlgorithm())
        self.addAlgorithm(BarrierAlgorithm())
        self.addAlgorithm(SensitivityAnalysisAlgorithm())
        self.addAlgorithm(PdiValidationAlgorithm())
        self.addAlgorithm(BufferValidationAlgorithm())
        self.addAlgorithm(ResampleDemAlgorithm())
        self.addAlgorithm(DemErrorAlgorithm())

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
