# -*- coding: utf-8 -*-
"""NoData-aware block-mean DEM resampling."""

import numpy as np
import pytest

from core.resample import block_reduce_mean


def test_factor_one_is_noop():
    dem = np.arange(16.0).reshape(4, 4)
    assert block_reduce_mean(dem, 1) is dem


def test_shape_reduced_by_factor():
    dem = np.ones((8, 6))
    out = block_reduce_mean(dem, 2)
    assert out.shape == (4, 3)


def test_block_mean_values():
    dem = np.array([[1.0, 1.0, 2.0, 2.0],
                    [1.0, 1.0, 2.0, 2.0],
                    [3.0, 3.0, 4.0, 4.0],
                    [3.0, 3.0, 4.0, 4.0]])
    out = block_reduce_mean(dem, 2)
    assert np.allclose(out, [[1.0, 2.0], [3.0, 4.0]])


def test_trims_to_multiple_of_factor():
    dem = np.ones((5, 5))           # 5 is not a multiple of 2
    out = block_reduce_mean(dem, 2)
    assert out.shape == (2, 2)      # trailing row/col dropped


def test_nodata_ignored_per_block():
    dem = np.array([[1.0, 3.0],
                    [np.nan, np.nan]])
    out = block_reduce_mean(dem, 2)
    # mean of the two finite cells (1, 3) = 2.0
    assert out.shape == (1, 1)
    assert out[0, 0] == 2.0


def test_all_nodata_block_stays_nan():
    dem = np.full((2, 2), np.nan)
    out = block_reduce_mean(dem, 2)
    assert np.isnan(out[0, 0])


def test_factor_larger_than_dem_raises():
    with pytest.raises(ValueError):
        block_reduce_mean(np.ones((2, 2)), 4)


def test_invalid_factor_raises():
    with pytest.raises(ValueError):
        block_reduce_mean(np.ones((4, 4)), 0)
