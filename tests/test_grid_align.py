# -*- coding: utf-8 -*-
"""Geo-grid regularity and alignment checks (pure, no GDAL)."""

import pytest

from core.grid_align import (
    check_regular_geotransform, assert_regular_geotransform,
    check_grids_aligned, assert_grids_aligned, xy_to_rowcol,
)

# A north-up, unrotated, 10 m square-pixel geotransform.
GT = (500000.0, 10.0, 0.0, 4000000.0, 0.0, -10.0)


def test_xy_to_rowcol_inside():
    assert xy_to_rowcol(GT, 500000.0, 4000000.0) == (0, 0)   # origin corner
    assert xy_to_rowcol(GT, 500025.0, 3999975.0) == (2, 2)   # inside cell


def test_xy_to_rowcol_just_west_is_negative():
    """A point a fraction west of the origin must map to col -1, not 0."""
    row, col = xy_to_rowcol(GT, 499999.0, 3999975.0)
    assert col == -1


def test_xy_to_rowcol_just_north_is_negative():
    """A point a fraction north of the origin must map to row -1, not 0."""
    row, col = xy_to_rowcol(GT, 500025.0, 4000001.0)
    assert row == -1


def test_xy_to_rowcol_floor_not_truncate():
    """floor != int for negative offsets — this is the regression guard."""
    # 0.5 pixel west and north of origin.
    assert xy_to_rowcol(GT, 499995.0, 4000005.0) == (-1, -1)


def test_regular_geotransform_accepts_north_up_square():
    ok, reason = check_regular_geotransform(GT)
    assert ok, reason


def test_regular_geotransform_rejects_rotation():
    rotated = (500000.0, 10.0, 0.5, 4000000.0, 0.5, -10.0)
    ok, _ = check_regular_geotransform(rotated)
    assert not ok
    with pytest.raises(ValueError):
        assert_regular_geotransform(rotated)


def test_regular_geotransform_rejects_non_square():
    rect = (500000.0, 10.0, 0.0, 4000000.0, 0.0, -12.0)
    ok, _ = check_regular_geotransform(rect)
    assert not ok


def test_regular_geotransform_tolerates_rounding_noise():
    noisy = (500000.0, 10.0, 0.0, 4000000.0, 0.0, -10.000001)
    ok, reason = check_regular_geotransform(noisy)
    assert ok, reason


def test_aligned_grids_match():
    ok, reason = check_grids_aligned(GT, (100, 120), GT, (100, 120))
    assert ok, reason


def test_alignment_rejects_shape_mismatch():
    ok, _ = check_grids_aligned(GT, (100, 120), GT, (100, 121))
    assert not ok


def test_alignment_rejects_origin_shift():
    shifted = (500005.0, 10.0, 0.0, 4000000.0, 0.0, -10.0)   # half a pixel east
    ok, reason = check_grids_aligned(GT, (100, 120), shifted, (100, 120))
    assert not ok
    assert "x-origin" in reason


def test_alignment_rejects_resolution_mismatch():
    coarse = (500000.0, 20.0, 0.0, 4000000.0, 0.0, -20.0)
    ok, _ = check_grids_aligned(GT, (100, 120), coarse, (100, 120))
    assert not ok


def test_alignment_tolerates_rounding_noise():
    noisy = (500000.0 + 1e-7, 10.0, 0.0, 4000000.0 - 1e-7, 0.0, -10.0)
    ok, reason = check_grids_aligned(GT, (100, 120), noisy, (100, 120))
    assert ok, reason


def test_assert_grids_aligned_message_includes_label():
    coarse = (500000.0, 20.0, 0.0, 4000000.0, 0.0, -20.0)
    with pytest.raises(ValueError, match="Barrier/multiplier raster"):
        assert_grids_aligned(GT, (100, 120), coarse, (100, 120),
                             "Barrier/multiplier raster")
