# -*- coding: utf-8 -*-
"""Downsample a DEM by an integer factor (block mean) to save memory."""

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
)

from ..core.raster_io import RasterGrid
from ..core.resample import block_reduce_mean


class ResampleDemAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    FACTOR = "FACTOR"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, "Digital Elevation Model"))
        self.addParameter(QgsProcessingParameterNumber(
            self.FACTOR, "Downsample factor (integer ≥ 2)",
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=2, minValue=2))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT, "Resampled DEM"))

    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        factor = self.parameterAsInt(parameters, self.FACTOR, context)
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        grid = RasterGrid.from_path(dem_layer.source())
        feedback.pushInfo("Resampling %dx%d by factor %d (block mean) …"
                          % (grid.rows, grid.cols, factor))

        reduced = block_reduce_mean(grid.array, factor)

        # Coarser geotransform: same origin, pixel size scaled by the factor.
        gt = grid.gt
        new_gt = (gt[0], gt[1] * factor, gt[2],
                  gt[3], gt[4], gt[5] * factor)
        RasterGrid.write_raster(out_path, reduced, new_gt, grid.projection)

        feedback.pushInfo("Output: %dx%d cells (%.1f%% of the original)."
                          % (reduced.shape[0], reduced.shape[1],
                             100.0 * reduced.size / grid.array.size))
        return {self.OUTPUT: out_path}

    def name(self):
        return "resampledem"

    def displayName(self):
        return "Resample DEM (block mean)"

    def group(self):
        return "Tools"

    def groupId(self):
        return "tools"

    def shortHelpString(self):
        return ("Downsamples a DEM by an integer factor using a NoData-aware "
                "block mean, cutting the cell count (and the conductance-matrix "
                "memory) by factor squared. Use this to fit a large DEM in RAM "
                "when clipping is not an option. The origin is preserved and the "
                "pixel size is multiplied by the factor.")

    def createInstance(self):
        return ResampleDemAlgorithm()
