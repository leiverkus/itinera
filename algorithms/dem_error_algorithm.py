# -*- coding: utf-8 -*-
"""Generate one spatially-autocorrelated DEM error realisation."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterEnum, QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
)
import numpy as np

from ..core.raster_io import RasterGrid
from ..core.stochastic import add_dem_error


class DemErrorAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    RMSE = "RMSE"
    AUTOCORR = "AUTOCORR"
    MODEL = "MODEL"
    NUGGET = "NUGGET"
    SEED = "SEED"
    OUTPUT = "OUTPUT"

    _ERROR_MODELS = ["exponential", "spherical", "gaussian", "gaussian_filter"]
    _MODEL_LABELS = ["Exponential (variogram)", "Spherical (variogram)",
                     "Gaussian (variogram)", "Gaussian filter (fast)"]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterNumber(
            self.RMSE, "Vertical RMSE (m)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=2.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.AUTOCORR, "Autocorrelation range (m)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=100.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterEnum(
            self.MODEL, "Error model", options=self._MODEL_LABELS,
            defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            self.NUGGET, "Nugget (uncorrelated fraction, 0–1; variogram only)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0, maxValue=0.99))
        self.addParameter(QgsProcessingParameterNumber(
            self.SEED, "Random seed (optional, for reproducibility)",
            type=QgsProcessingParameterNumber.Integer, optional=True))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Perturbed DEM (one error realisation)"))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        rmse = self.parameterAsDouble(parameters, self.RMSE, context)
        autocorr = self.parameterAsDouble(parameters, self.AUTOCORR, context)
        model = self._ERROR_MODELS[
            self.parameterAsEnum(parameters, self.MODEL, context)]
        nugget = self.parameterAsDouble(parameters, self.NUGGET, context)
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        raw_seed = parameters.get(self.SEED)
        seed = None if raw_seed is None else self.parameterAsInt(
            parameters, self.SEED, context)
        rng = np.random.default_rng(seed)

        grid = RasterGrid.from_path(dem_layer.source())
        feedback.pushInfo(
            "Simulating a %s error field (RMSE %.3g m, range %.3g m) …"
            % (model, rmse, autocorr))
        perturbed = add_dem_error(
            grid.array, rmse, autocorr, grid.cellsize, rng,
            model=model, nugget=nugget)

        grid.write_like(out_path, perturbed)
        return {self.OUTPUT: out_path}

    def name(self):
        return "demerrorrealisation"

    def displayName(self):
        return "DEM error realisation"

    def group(self):
        return "Tools"

    def groupId(self):
        return "tools"

    def shortHelpString(self):
        return ("Generates one spatially-autocorrelated DEM error realisation "
                "and adds it to the DEM (Hunter & Goodchild 1997). The error "
                "field is a Gaussian random field with the chosen variogram "
                "model (exponential / spherical / gaussian, FFT spectral "
                "simulation) scaled to the target vertical RMSE, with an "
                "optional nugget (uncorrelated fraction). A fast Gaussian-filter "
                "approximation is also available.\n\n"
                "Useful for inspecting how DEM uncertainty perturbs the terrain, "
                "and as the building block of the Stochastic LCP corridor. Set a "
                "seed for reproducibility.")

    def createInstance(self):
        return DemErrorAlgorithm()
