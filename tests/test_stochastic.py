# -*- coding: utf-8 -*-
"""Stochastic least-cost path: DEM error, edge dropping, probabilistic corridor."""

import numpy as np
import pytest

from core import cost_functions as cf
from core.conductance import build_conductance
from core.lcp import least_cost_path
from core.stochastic import (
    add_dem_error, add_global_stochasticity, stochastic_lcp,
    simulate_error_field,
)


def _lag1(field):
    """Lag-1 horizontal spatial autocorrelation of a 2D field."""
    return np.corrcoef(field[:, :-1].ravel(), field[:, 1:].ravel())[0, 1]


# --- add_dem_error ----------------------------------------------------------

def test_dem_error_zero_rmse_is_noop(slope_dem, cellsize):
    out = add_dem_error(slope_dem, 0.0, 100.0, cellsize, np.random.default_rng(0))
    assert out is slope_dem


def test_dem_error_matches_target_rmse(slope_dem, cellsize):
    rng = np.random.default_rng(1)
    out = add_dem_error(slope_dem, 5.0, 0.0, cellsize, rng)
    err = out - slope_dem
    assert out.shape == slope_dem.shape
    assert np.isclose(err.std(), 5.0)          # field rescaled to target RMSE


def test_dem_error_preserves_nodata(cellsize):
    dem = np.full((8, 8), 100.0)
    dem[2, 2] = np.nan
    out = add_dem_error(dem, 3.0, 20.0, cellsize, np.random.default_rng(2))
    assert np.isnan(out[2, 2])
    assert np.all(np.isfinite(out[np.isfinite(dem)]))


def test_dem_error_is_reproducible(slope_dem, cellsize):
    a = add_dem_error(slope_dem, 4.0, 30.0, cellsize, np.random.default_rng(7))
    b = add_dem_error(slope_dem, 4.0, 30.0, cellsize, np.random.default_rng(7))
    assert np.array_equal(a, b)


# --- simulate_error_field (variogram-based) --------------------------------

def test_error_field_shape_mean_std():
    rng = np.random.default_rng(0)
    f = simulate_error_field((40, 50), 2.0, 80.0, 10.0, rng, "exponential")
    assert f.shape == (40, 50)
    assert np.all(np.isfinite(f))
    assert abs(f.mean()) < 1e-6
    assert f.std() == pytest.approx(2.0)


@pytest.mark.parametrize("model", ["exponential", "spherical", "gaussian"])
def test_range_increases_autocorrelation(model):
    rng = np.random.default_rng(3)
    rough = simulate_error_field((80, 80), 1.0, 20.0, 10.0, rng, model)
    smooth = simulate_error_field((80, 80), 1.0, 400.0, 10.0, rng, model)
    assert _lag1(smooth) > _lag1(rough)
    assert _lag1(smooth) > 0.5            # a long range really is smooth


def test_nugget_reduces_autocorrelation():
    rng = np.random.default_rng(4)
    structured = simulate_error_field((80, 80), 1.0, 400.0, 10.0, rng,
                                      "exponential", nugget=0.0)
    nuggety = simulate_error_field((80, 80), 1.0, 400.0, 10.0, rng,
                                   "exponential", nugget=0.95)
    assert _lag1(structured) > _lag1(nuggety)
    assert _lag1(nuggety) < 0.3           # mostly white


def test_error_field_reproducible_and_seed_varies():
    a = simulate_error_field((30, 30), 1.0, 50.0, 10.0,
                             np.random.default_rng(9), "exponential")
    b = simulate_error_field((30, 30), 1.0, 50.0, 10.0,
                             np.random.default_rng(9), "exponential")
    c = simulate_error_field((30, 30), 1.0, 50.0, 10.0,
                             np.random.default_rng(10), "exponential")
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_error_field_validation():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        simulate_error_field((10, 10), 1.0, 50.0, 10.0, rng, "median")
    with pytest.raises(ValueError):
        simulate_error_field((10, 10), 1.0, 50.0, 10.0, rng,
                             "exponential", nugget=1.0)


def test_add_dem_error_gaussian_filter_still_works(slope_dem, cellsize):
    out = add_dem_error(slope_dem, 5.0, 30.0, cellsize,
                        np.random.default_rng(1), model="gaussian_filter")
    assert np.isclose((out - slope_dem).std(), 5.0)


def test_add_dem_error_variogram_is_correlated(cellsize):
    dem = np.full((60, 60), 100.0)
    out = add_dem_error(dem, 3.0, 200.0, cellsize, np.random.default_rng(2),
                        model="exponential")
    err = out - dem
    assert np.isclose(err.std(), 3.0)
    assert _lag1(err) > 0.4               # the default model is autocorrelated


# --- add_global_stochasticity ----------------------------------------------

def test_drop_zero_is_noop(slope_dem, cellsize):
    m, _, _ = build_conductance(slope_dem, cellsize, cf.tobler)
    out = add_global_stochasticity(m, 0.0, np.random.default_rng(0))
    assert out is m


def test_drop_all_removes_every_edge(slope_dem, cellsize):
    m, _, _ = build_conductance(slope_dem, cellsize, cf.tobler)
    out = add_global_stochasticity(m, 1.0, np.random.default_rng(0))
    assert out.nnz == 0


def test_drop_half_removes_about_half(slope_dem, cellsize):
    m, _, _ = build_conductance(slope_dem, cellsize, cf.tobler)
    out = add_global_stochasticity(m, 0.5, np.random.default_rng(3))
    assert 0 < out.nnz < m.nnz
    assert out.nnz == pytest.approx(m.nnz * 0.5, rel=0.15)


# --- stochastic_lcp ---------------------------------------------------------

def test_probability_in_unit_range(slope_dem, cellsize):
    n = slope_dem.shape[0] * slope_dem.shape[1]
    prob, n_cells = stochastic_lcp(
        slope_dem, cellsize, cf.tobler, 0, n - 1, n_iter=10,
        rng=np.random.default_rng(0), rmse=5.0, autocorr_range=20.0)
    assert n_cells == n
    assert prob.shape == (n,)
    assert prob.min() >= 0.0 and prob.max() <= 1.0
    assert prob.sum() > 0


def test_zero_iterations_raises(slope_dem, cellsize):
    n = slope_dem.shape[0] * slope_dem.shape[1]
    with pytest.raises(ValueError):
        stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, n - 1, n_iter=0,
                       rng=np.random.default_rng(0))


def test_deterministic_when_no_stochasticity(slope_dem, cellsize):
    """rmse=0, drop=0 -> every iteration identical -> optimal path has prob 1."""
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    origin, dest = 0, rows * cols - 1
    path, _ = least_cost_path(m, origin, dest)

    prob, _ = stochastic_lcp(
        slope_dem, cellsize, cf.tobler, origin, dest, n_iter=3,
        rng=np.random.default_rng(0))
    assert np.allclose(prob[path], 1.0)
    assert prob[origin] == 1.0 and prob[dest] == 1.0


def test_reproducible_with_seed(slope_dem, cellsize):
    n = slope_dem.shape[0] * slope_dem.shape[1]
    kw = dict(rmse=6.0, autocorr_range=15.0, drop_fraction=0.1)
    a, _ = stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, n - 1, 8,
                          np.random.default_rng(42), **kw)
    b, _ = stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, n - 1, 8,
                          np.random.default_rng(42), **kw)
    assert np.array_equal(a, b)


def test_dem_error_spreads_the_corridor(slope_dem, cellsize):
    """Adding DEM error should put >0 probability on more cells than the single
    deterministic path occupies."""
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    origin, dest = 0, rows * cols - 1
    det_path, _ = least_cost_path(m, origin, dest)

    prob, _ = stochastic_lcp(
        slope_dem, cellsize, cf.tobler, origin, dest, n_iter=25,
        rng=np.random.default_rng(5), rmse=8.0, autocorr_range=10.0)
    assert (prob > 0).sum() >= len(det_path)
