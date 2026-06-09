# -*- coding: utf-8 -*-
"""Multi-criteria composite friction."""

import numpy as np
import pytest

from core.multicriteria import composite_friction

A = np.array([[0.0, 1.0], [0.0, 1.0]])
B = np.array([[0.0, 0.0], [1.0, 1.0]])


def test_weighted_sum_exact():
    out = composite_friction([A, B], method="sum", out_range=(1.0, 10.0))
    # P = (A + B) / 2 -> friction = 1 + 9*P
    assert np.allclose(out, [[1.0, 5.5], [5.5, 10.0]])


def test_product_is_geometric_mean():
    out = composite_friction([A, B], method="product", out_range=(1.0, 10.0))
    r = np.sqrt(10.0)
    assert out == pytest.approx(np.array([[1.0, r], [r, 10.0]]))


def test_all_best_is_lo_all_worst_is_hi():
    out = composite_friction([A, B], out_range=(1.0, 10.0))
    assert out[0, 0] == pytest.approx(1.0)      # both layers minimal
    assert out[1, 1] == pytest.approx(10.0)     # both layers maximal


def test_invert_flips_a_layer():
    base = composite_friction([A, B], out_range=(1.0, 10.0))
    inv = composite_friction([A, B], invert=[False, True], out_range=(1.0, 10.0))
    # Cell (1,1): A=1, B=1 -> inverted B becomes 0, so friction drops.
    assert inv[1, 1] < base[1, 1]
    assert inv[0, 0] > base[0, 0]               # A=0,B=0 -> inverted B=1, rises


def test_weights_shift_toward_heavier_layer():
    # Heavier weight on B pulls cell (1,0) (A=0, B=1) toward B's high penalty.
    light = composite_friction([A, B], weights=[1.0, 1.0])[1, 0]
    heavy = composite_friction([A, B], weights=[1.0, 9.0])[1, 0]
    assert heavy > light


def test_constant_layer_is_neutral():
    const = np.full((2, 2), 5.0)
    out = composite_friction([const], out_range=(1.0, 10.0))
    assert np.allclose(out, 1.0)                # no variation -> lo


def test_nodata_propagates_to_impassable():
    a = A.copy()
    a[0, 0] = np.nan
    out = composite_friction([a, B])
    assert np.isnan(out[0, 0])
    assert np.all(np.isfinite(out[[0, 1, 1], [1, 0, 1]]))


def test_validation_errors():
    with pytest.raises(ValueError):
        composite_friction([])
    with pytest.raises(ValueError):
        composite_friction([A, np.zeros((3, 3))])         # shape mismatch
    with pytest.raises(ValueError):
        composite_friction([A, B], weights=[1.0])          # wrong length
    with pytest.raises(ValueError):
        composite_friction([A, B], weights=[1.0, 0.0])     # non-positive
    with pytest.raises(ValueError):
        composite_friction([A, B], method="median")        # bad method
    with pytest.raises(ValueError):
        composite_friction([A, B], invert=[True])          # wrong length
    # P2: the output range must be finite with 0 < lo < hi. A non-positive lo
    # would make cells impassable (lo == 0) or break the geometric mean
    # (lo < 0 -> log of a non-positive multiplier -> NaN/-inf).
    for bad in [(-1.0, 10.0), (0.0, 10.0), (5.0, 5.0), (5.0, 1.0),
                (np.nan, 10.0), (1.0, np.inf)]:
        with pytest.raises(ValueError):
            composite_friction([A, B], out_range=bad)
