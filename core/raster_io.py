# -*- coding: utf-8 -*-
"""Raster I/O helpers using GDAL (bundled with QGIS – no rasterio needed)."""

import numpy as np
from osgeo import gdal

from .grid_align import assert_regular_geotransform, xy_to_rowcol as _xy_to_rowcol

gdal.UseExceptions()


class RasterGrid:
    """Lightweight wrapper around a single-band DEM."""

    def __init__(self, array, geotransform, projection, nodata):
        self.array = array                 # 2D float ndarray, NoData -> nan
        self.gt = geotransform             # GDAL 6-tuple
        self.projection = projection       # WKT
        self.nodata = nodata
        self.rows, self.cols = array.shape

    @classmethod
    def from_path(cls, path):
        ds = gdal.Open(path, gdal.GA_ReadOnly)
        if ds is None:
            raise IOError("Cannot open raster: %s" % path)
        band = ds.GetRasterBand(1)
        arr = band.ReadAsArray().astype(np.float64)
        nodata = band.GetNoDataValue()
        if nodata is not None:
            arr[arr == nodata] = np.nan
        gt = ds.GetGeoTransform()
        # Fail loudly on rotated / non-square grids rather than computing wrong
        # row/col indices silently.
        assert_regular_geotransform(gt)
        grid = cls(arr, gt, ds.GetProjection(), nodata)
        ds = None
        return grid

    @property
    def cellsize(self):
        # Assumes square pixels; uses |pixel width|.
        return abs(self.gt[1])

    def xy_to_rowcol(self, x, y):
        """Map coordinates -> (row, col) integer indices (floor-based)."""
        return _xy_to_rowcol(self.gt, x, y)

    def rowcol_to_xy(self, row, col):
        """(row, col) -> map coordinates at the cell centre."""
        gt = self.gt
        x = gt[0] + (col + 0.5) * gt[1]
        y = gt[3] + (row + 0.5) * gt[5]
        return x, y

    def in_bounds(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    def write_like(self, out_path, data2d, nodata=-9999.0):
        """Write a 2D array with this grid's geo-reference as GeoTIFF."""
        drv = gdal.GetDriverByName("GTiff")
        out = drv.Create(out_path, self.cols, self.rows, 1, gdal.GDT_Float32,
                         options=["COMPRESS=DEFLATE", "TILED=YES"])
        out.SetGeoTransform(self.gt)
        out.SetProjection(self.projection)
        band = out.GetRasterBand(1)
        filled = np.where(np.isfinite(data2d), data2d, nodata)
        band.WriteArray(filled.astype(np.float32))
        band.SetNoDataValue(nodata)
        band.FlushCache()
        out = None
