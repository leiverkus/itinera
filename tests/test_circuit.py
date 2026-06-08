# -*- coding: utf-8 -*-
"""Circuit theory: current density, pinch points, barriers."""

import numpy as np
import pytest

from core.conductance import build_conductance_friction, rowcol_to_node
from core.circuit import current_density, restoration_score


def _wall_with_gap(size=21, gap_row=None):
    """Friction raster: a high-cost vertical wall at the mid column with a
    single low-cost gap cell. Current from the left must funnel through the gap.
    """
    gap_row = size // 2 if gap_row is None else gap_row
    mid = size // 2
    fr = np.ones((size, size), dtype=np.float64)
    fr[:, mid] = 1.0e4
    fr[gap_row, mid] = 1.0          # the one-cell gap
    return fr, mid, gap_row


def test_current_density_shape_and_range():
    fr, mid, gap = _wall_with_gap()
    m, rows, cols = build_conductance_friction(fr, 10.0, neighbours=8)
    s = rowcol_to_node(gap, 0, cols)
    t = rowcol_to_node(gap, cols - 1, cols)
    current, n = current_density(m, [s], [t])
    assert n == rows * cols
    assert current.shape == (n,)
    assert np.all(np.isfinite(current))
    assert current.min() >= 0.0 and current.max() == pytest.approx(1.0)
    assert current[s] > 0.0 and current[t] > 0.0


def test_gap_is_the_pinch_point():
    """The current density must peak at the single gap cell (a pinch point)."""
    fr, mid, gap = _wall_with_gap()
    m, rows, cols = build_conductance_friction(fr, 10.0, neighbours=8)
    s = rowcol_to_node(gap, 0, cols)
    t = rowcol_to_node(gap, cols - 1, cols)
    current, _ = current_density(m, [s], [t])
    gap_node = rowcol_to_node(gap, mid, cols)
    assert int(current.argmax()) == gap_node


def test_pinch_points_restricted_to_corridor():
    fr, mid, gap = _wall_with_gap()
    m, rows, cols = build_conductance_friction(fr, 10.0, neighbours=8)
    s = rowcol_to_node(gap, 0, cols)
    t = rowcol_to_node(gap, cols - 1, cols)
    current, _, pinch = current_density(
        m, [s], [t], corridor_tolerance=50.0)
    assert pinch.shape == current.shape
    # The pinch surface is a masked subset of the current density.
    assert np.all(pinch <= current + 1e-12)
    assert np.all((pinch == 0.0) | (pinch == current))
    # The gap cell lies in the corridor and carries the peak.
    assert pinch[rowcol_to_node(gap, mid, cols)] > 0.0


def test_current_is_symmetric_on_uniform_friction():
    """Uniform friction: current map is symmetric about the source-target row."""
    fr = np.ones((21, 21), dtype=np.float64)
    m, rows, cols = build_conductance_friction(fr, 10.0, neighbours=8)
    s = rowcol_to_node(10, 0, cols)
    t = rowcol_to_node(10, 20, cols)
    current, _ = current_density(m, [s], [t])
    grid = current.reshape(rows, cols)
    assert np.allclose(grid, grid[::-1, :], atol=1e-9)


def test_unreachable_target_is_graceful():
    """Target ring-fenced by NoData -> zeros, no crash."""
    fr = np.ones((15, 15), dtype=np.float64)
    fr[10:, 10:] = np.nan          # NoData island around the target corner
    m, rows, cols = build_conductance_friction(fr, 10.0, neighbours=8)
    s = rowcol_to_node(0, 0, cols)
    t = rowcol_to_node(14, 14, cols)
    current, _, pinch = current_density(m, [s], [t], corridor_tolerance=10.0)
    assert np.all(current == 0.0) and np.all(pinch == 0.0)


def test_restoration_peaks_on_the_barrier():
    """A solid high-cost wall between S and T: the improvement score should peak
    on the wall (restoring it helps the corridor most)."""
    size = 21
    mid = size // 2
    fr = np.ones((size, size), dtype=np.float64)
    fr[:, mid] = 1.0e3             # solid barrier, no gap
    m, rows, cols = build_conductance_friction(fr, 10.0, neighbours=8)
    s = rowcol_to_node(mid, 0, cols)
    t = rowcol_to_node(mid, size - 1, cols)
    score = restoration_score(
        m, rows, cols, [s], [t], cellsize=10.0, window=3,
        improved_resistance=1.0)
    assert score.shape == (rows * cols,)
    assert np.all(np.isfinite(score)) and np.all(score >= 0.0)
    grid = score.reshape(rows, cols)
    # The strongest improvement is on the barrier column.
    best_col = int(np.argmax(grid.max(axis=0)))
    assert abs(best_col - mid) <= 1
    assert grid.max() > 0.0
