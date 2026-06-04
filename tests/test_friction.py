# -*- coding: utf-8 -*-
"""Invariants for the friction-driven conductance builder."""

import numpy as np
import pytest

from core import cost_functions as cf
from core.conductance import build_conductance_friction, rowcol_to_node


def test_friction_only_is_symmetric(friction, cellsize):
    """Pure friction is isotropic, so the matrix is symmetric (correct, not a
    forbidden symmetrisation of a slope matrix)."""
    m, _, _ = build_conductance_friction(friction, cellsize)
    assert m.nnz > 0
    assert (m != m.T).nnz == 0
    assert np.all(np.isfinite(m.data))
    assert np.all(m.data > 0.0)


def test_combined_with_dem_is_asymmetric(friction, slope_dem, cellsize):
    m, _, _ = build_conductance_friction(
        friction, cellsize, dem=slope_dem, cost_fn=cf.tobler)
    assert (m != m.T).nnz > 0
    assert np.all(np.isfinite(m.data))
    assert np.all(m.data > 0.0)


def test_nonpositive_friction_is_impassable(friction, cellsize):
    fric = friction.copy()
    fric[4, 4] = -1.0
    m, _, cols = build_conductance_friction(fric, cellsize)
    node = rowcol_to_node(4, 4, cols)
    assert m[node].nnz == 0
    assert m[:, node].nnz == 0


def test_shape_mismatch_raises(friction, cellsize):
    with pytest.raises(ValueError):
        build_conductance_friction(
            friction, cellsize, dem=friction[:4, :4], cost_fn=cf.tobler)


def test_dem_without_cost_fn_raises(friction, slope_dem, cellsize):
    with pytest.raises(ValueError):
        build_conductance_friction(friction, cellsize, dem=slope_dem)


def test_invalid_neighbours_raises(friction, cellsize):
    with pytest.raises(ValueError):
        build_conductance_friction(friction, cellsize, neighbours=5)
