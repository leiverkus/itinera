# -*- coding: utf-8 -*-
"""Invariants for the slope-driven conductance builder."""

import numpy as np
import pytest

from core import cost_functions as cf
from core.conductance import (
    build_conductance, rowcol_to_node, node_to_rowcol,
)


def test_matrix_is_asymmetric(slope_dem, cellsize):
    """The central invariant: directional slope => asymmetric matrix."""
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    assert (rows, cols) == slope_dem.shape
    assert (m != m.T).nnz > 0


def test_weights_finite_and_positive(slope_dem, cellsize):
    m, _, _ = build_conductance(slope_dem, cellsize, cf.tobler)
    assert m.nnz > 0
    assert np.all(np.isfinite(m.data))
    assert np.all(m.data > 0.0)


@pytest.mark.parametrize("neighbours", [4, 8, 16])
def test_neighbour_counts(slope_dem, cellsize, neighbours):
    m, _, _ = build_conductance(slope_dem, cellsize, cf.tobler,
                                neighbours=neighbours)
    assert m.nnz > 0


def test_invalid_neighbours_raises(slope_dem, cellsize):
    with pytest.raises(ValueError):
        build_conductance(slope_dem, cellsize, cf.tobler, neighbours=5)


def test_nodata_cell_is_isolated(slope_dem, cellsize):
    """A NaN cell must have no incident edges (unreachable, not free)."""
    dem = slope_dem.copy()
    dem[3, 3] = np.nan
    m, _, cols = build_conductance(dem, cellsize, cf.tobler)
    node = rowcol_to_node(3, 3, cols)
    assert m[node].nnz == 0          # no outgoing edges
    assert m[:, node].nnz == 0       # no incoming edges
    assert np.all(np.isfinite(m.data))


def test_node_helpers_roundtrip():
    cols = 8
    for row in range(8):
        for col in range(cols):
            node = rowcol_to_node(row, col, cols)
            assert node_to_rowcol(node, cols) == (row, col)


# --- barrier / multiplier raster -------------------------------------------

def test_unit_multiplier_is_a_noop(slope_dem, cellsize):
    """A multiplier of all ones must reproduce the un-multiplied matrix."""
    base, _, _ = build_conductance(slope_dem, cellsize, cf.tobler)
    ones = np.ones_like(slope_dem)
    m, _, _ = build_conductance(slope_dem, cellsize, cf.tobler, multiplier=ones)
    assert m.nnz == base.nnz
    assert np.allclose(m.data, base.data)


def test_constant_multiplier_scales_costs(slope_dem, cellsize):
    base, _, _ = build_conductance(slope_dem, cellsize, cf.tobler)
    twos = np.full_like(slope_dem, 2.0)
    m, _, _ = build_conductance(slope_dem, cellsize, cf.tobler, multiplier=twos)
    assert np.allclose(m.data, 2.0 * base.data)


def test_multiplier_preserves_asymmetry(slope_dem, cellsize):
    twos = np.full_like(slope_dem, 2.0)
    m, _, _ = build_conductance(slope_dem, cellsize, cf.tobler, multiplier=twos)
    assert (m != m.T).nnz > 0


def test_impassable_multiplier_cell_is_isolated(slope_dem, cellsize):
    """NoData / non-positive multiplier marks an impassable barrier."""
    mult = np.ones_like(slope_dem)
    mult[3, 3] = np.nan          # e.g. a cliff
    mult[5, 2] = 0.0             # zero is also impassable
    m, _, cols = build_conductance(
        slope_dem, cellsize, cf.tobler, multiplier=mult)
    for r, c in [(3, 3), (5, 2)]:
        node = rowcol_to_node(r, c, cols)
        assert m[node].nnz == 0
        assert m[:, node].nnz == 0


def test_multiplier_shape_mismatch_raises(slope_dem, cellsize):
    with pytest.raises(ValueError):
        build_conductance(slope_dem, cellsize, cf.tobler,
                          multiplier=np.ones((4, 4)))


# --- cost_params passthrough -----------------------------------------------

def test_cost_params_are_forwarded(slope_dem, cellsize):
    """Pandolf params threaded via cost_params must reach the cost function."""
    light, _, _ = build_conductance(
        slope_dem, cellsize, cf.pandolf, cost_params={"load": 0.0})
    heavy, _, _ = build_conductance(
        slope_dem, cellsize, cf.pandolf, cost_params={"load": 40.0})
    assert light.nnz == heavy.nnz
    assert not np.allclose(light.data, heavy.data)
    assert np.all(heavy.data > light.data)


def test_cost_params_default_is_noop(slope_dem, cellsize):
    """Omitting cost_params must equal passing an empty dict."""
    a, _, _ = build_conductance(slope_dem, cellsize, cf.tobler)
    b, _, _ = build_conductance(slope_dem, cellsize, cf.tobler, cost_params={})
    assert np.allclose(a.data, b.data)
