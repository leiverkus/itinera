# -*- coding: utf-8 -*-
"""Randomized Shortest Paths: the theta-axis between LCP and random walk."""

import numpy as np
import pytest

from core import cost_functions as cf
from core.conductance import build_conductance, rowcol_to_node
from core.lcp import least_cost_path
from core.rsp import rsp_passages


def _carrying(passages, frac=0.01):
    """Number of cells carrying at least ``frac`` of the peak passage."""
    return int(np.count_nonzero(passages >= frac))


def test_output_shape_and_range(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    s = rowcol_to_node(0, 0, cols)
    t = rowcol_to_node(rows - 1, cols - 1, cols)
    passages, n = rsp_passages(m, s, [t], theta=1.0)
    assert n == rows * cols
    assert passages.shape == (n,)
    assert np.all(np.isfinite(passages))
    assert passages.min() >= 0.0 and passages.max() == pytest.approx(1.0)
    assert passages[s] > 0.0 and passages[t] > 0.0


def test_theta_zero_rejected(slope_dem, cellsize):
    m, _, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    with pytest.raises(ValueError):
        rsp_passages(m, 0, [10], theta=0.0)
    with pytest.raises(ValueError):
        rsp_passages(m, 0, [10], theta=-1.0)


def test_high_theta_concentrates_on_lcp(slope_dem, cellsize):
    """Large theta: passage mass collapses onto the least-cost path."""
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    s = rowcol_to_node(0, 0, cols)
    t = rowcol_to_node(rows - 1, cols - 1, cols)
    passages, _ = rsp_passages(m, s, [t], theta=50.0)
    lcp_nodes, _ = least_cost_path(m, s, t)
    # Every LCP cell carries passage; the high-passage set is essentially the LCP.
    assert all(passages[node] > 0.0 for node in lcp_nodes)
    assert _carrying(passages, 0.05) <= len(lcp_nodes) + 2


def test_low_theta_spreads_more_than_high_theta(slope_dem, cellsize):
    """Small theta explores (circuit-like) — many more cells carry passage."""
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    s = rowcol_to_node(0, 0, cols)
    t = rowcol_to_node(rows - 1, cols - 1, cols)
    lo, _ = rsp_passages(m, s, [t], theta=0.05)
    hi, _ = rsp_passages(m, s, [t], theta=50.0)
    assert _carrying(lo, 0.01) > _carrying(hi, 0.01)


def test_concentration_is_monotone_in_theta(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    s = rowcol_to_node(0, 0, cols)
    t = rowcol_to_node(rows - 1, cols - 1, cols)
    counts = [_carrying(rsp_passages(m, s, [t], theta=th)[0], 0.1)
              for th in (0.05, 0.5, 5.0, 50.0)]
    # Rising theta concentrates the surface -> fewer carrying cells.
    assert counts == sorted(counts, reverse=True)


def test_free_energy_distance(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    s = rowcol_to_node(0, 0, cols)
    t = rowcol_to_node(rows - 1, cols - 1, cols)
    _, lcp_cost = least_cost_path(m, s, t)
    _, _, d_lo = rsp_passages(m, s, [t], theta=0.1, return_distance=True)
    _, _, d_hi = rsp_passages(m, s, [t], theta=50.0, return_distance=True)
    assert np.isfinite(d_lo[0]) and np.isfinite(d_hi[0])
    # The free-energy distance is >= the shortest-path cost and shrinks toward
    # it as theta grows (entropy-regularised distance, LCP in the limit).
    assert d_hi[0] >= lcp_cost - 1e-6
    assert d_lo[0] > d_hi[0]
    assert d_hi[0] == pytest.approx(lcp_cost, rel=0.10)


def test_unreachable_destination_is_inf(slope_dem, cellsize):
    """A NoData-isolated destination is unreachable -> inf distance, skipped."""
    dem = slope_dem.copy()
    rows, cols = dem.shape
    # Ring-fence the destination cell with NoData so no edge reaches it.
    dem[rows - 2:, cols - 2:] = np.nan
    m, _, cols = build_conductance(dem, cellsize, cf.tobler)
    s = rowcol_to_node(0, 0, cols)
    t = rowcol_to_node(rows - 1, cols - 1, cols)
    passages, _, dist = rsp_passages(m, s, [t], theta=1.0, return_distance=True)
    assert not np.isfinite(dist[0])
    assert np.all(passages == 0.0)


def test_multiple_destinations_accumulate(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    s = rowcol_to_node(0, 0, cols)
    t1 = rowcol_to_node(rows - 1, cols - 1, cols)
    t2 = rowcol_to_node(rows - 1, 0, cols)
    passages, _, dists = rsp_passages(
        m, s, [t1, t2], theta=1.0, return_distance=True)
    assert len(dists) == 2 and all(np.isfinite(d) for d in dists)
    assert passages[t1] > 0.0 and passages[t2] > 0.0


@pytest.mark.parametrize("normalize", [True, False])
def test_normalize_on_and_off_run(slope_dem, cellsize, normalize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    s = rowcol_to_node(0, 0, cols)
    t = rowcol_to_node(rows - 1, cols - 1, cols)
    theta = 1.0 if normalize else 1e-3
    passages, _ = rsp_passages(m, s, [t], theta=theta, normalize=normalize)
    assert np.all(np.isfinite(passages)) and passages.max() == pytest.approx(1.0)
