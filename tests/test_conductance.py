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
