# -*- coding: utf-8 -*-
"""Stochastic least-cost path: DEM error, edge dropping, probabilistic corridor."""

import numpy as np
import pytest

from core import cost_functions as cf
from core.conductance import build_conductance
from core.lcp import least_cost_path
from core.stochastic import (
    add_dem_error, add_global_stochasticity, stochastic_lcp,
    simulate_error_field, _max_ci_error,
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


# --- cost-model randomisation ----------------------------------------------

def _hill_dem(n=25):
    """A tilted plane with an off-diagonal Gaussian hill, so different cost
    functions choose genuinely different least-cost paths."""
    yy, xx = np.mgrid[0:n, 0:n]
    hill = 120.0 * np.exp(-(((xx - 12) ** 2 + (yy - 12) ** 2) / 40.0))
    return (xx + yy).astype(float) * 2.0 + hill


def _deterministic_path_prob(dem, cellsize, cost_fn, s, t):
    """The corridor a single fixed model produces (rmse=0, no edge drop)."""
    prob, _ = stochastic_lcp(dem, cellsize, cost_fn, s, [t], 5,
                             np.random.default_rng(0))
    return prob


def test_single_cost_function_identity(cellsize):
    """Sampling identical functions changes nothing (rmse=0, no drop)."""
    dem = _hill_dem()
    n = dem.shape[1]
    s, t = 0, n * n - 1
    twin, _ = stochastic_lcp(dem, cellsize, cf.tobler, s, [t], 8,
                             np.random.default_rng(0),
                             cost_fns=[cf.tobler, cf.tobler])
    single = _deterministic_path_prob(dem, cellsize, cf.tobler, s, t)
    assert np.array_equal(twin, single)


def test_function_sampling_spreads_corridor(cellsize):
    dem = _hill_dem()
    n = dem.shape[1]
    s, t = 0, n * n - 1
    tob = _deterministic_path_prob(dem, cellsize, cf.tobler, s, t)
    her = _deterministic_path_prob(dem, cellsize, cf.herzog, s, t)
    assert not np.array_equal(tob, her)        # the two models really disagree

    prob, _ = stochastic_lcp(dem, cellsize, cf.tobler, s, [t], 40,
                             np.random.default_rng(1),
                             cost_fns=[cf.tobler, cf.herzog])
    # Cells unique to one model carry partial probability.
    assert np.any((prob > 0) & (prob < 1))
    # Both models' paths are represented.
    assert np.all(prob[tob > 0] > 0) and np.all(prob[her > 0] > 0)


def test_cost_weights_select_one_model(cellsize):
    dem = _hill_dem()
    n = dem.shape[1]
    s, t = 0, n * n - 1
    tob = _deterministic_path_prob(dem, cellsize, cf.tobler, s, t)
    only_tobler, _ = stochastic_lcp(dem, cellsize, cf.tobler, s, [t], 10,
                                    np.random.default_rng(2),
                                    cost_fns=[cf.tobler, cf.herzog],
                                    cost_weights=[1.0, 0.0])
    assert np.array_equal(only_tobler, tob)    # herzog never sampled


def test_param_jitter_spreads_corridor(cellsize):
    dem = _hill_dem()
    n = dem.shape[1]
    s, t = 0, n * n - 1
    params = {"mass": 70.0, "load": 30.0, "terrain": 1.0}
    base, _ = stochastic_lcp(dem, cellsize, cf.pandolf, s, [t], 30,
                             np.random.default_rng(3), cost_params=params,
                             param_jitter=0.0)
    jit, _ = stochastic_lcp(dem, cellsize, cf.pandolf, s, [t], 30,
                            np.random.default_rng(3), cost_params=params,
                            param_jitter=0.5)
    assert np.all((base == 0) | (base == 1))   # no jitter -> one fixed path
    assert np.any((jit > 0) & (jit < 1))       # jitter perturbs the route


def test_cost_weights_validation(cellsize):
    dem = _hill_dem()
    n = dem.shape[1]
    with pytest.raises(ValueError):
        stochastic_lcp(dem, cellsize, cf.tobler, 0, [n * n - 1], 5,
                       np.random.default_rng(0),
                       cost_fns=[cf.tobler, cf.herzog], cost_weights=[1.0])
    with pytest.raises(ValueError):
        stochastic_lcp(dem, cellsize, cf.tobler, 0, [n * n - 1], 5,
                       np.random.default_rng(0),
                       cost_fns=[cf.tobler, cf.herzog], cost_weights=[0.0, 0.0])
    # P3: non-finite weights must be rejected with a clear error, not slip
    # through to NumPy's "Probabilities contain NaN" deep inside rng.choice.
    for bad in ([np.nan, 1.0], [np.inf, 1.0]):
        with pytest.raises(ValueError):
            stochastic_lcp(dem, cellsize, cf.tobler, 0, [n * n - 1], 5,
                           np.random.default_rng(0),
                           cost_fns=[cf.tobler, cf.herzog], cost_weights=bad)


# --- convergence / stop criterion ------------------------------------------

def test_no_tol_runs_all_iterations(slope_dem, cellsize):
    n = slope_dem.shape[1]
    _, _, d = stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, [n * n - 1], 12,
                             np.random.default_rng(0), return_diagnostics=True)
    assert d["iterations"] == 12 and d["converged"] is False


def test_precision_deterministic_converges_at_min_iter(slope_dem, cellsize):
    n = slope_dem.shape[1]
    _, _, d = stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, [n * n - 1], 500,
                             np.random.default_rng(0), tol=0.05,
                             convergence="precision", min_iter=20,
                             check_every=10, return_diagnostics=True)
    # A deterministic-looking map must NOT converge early: the Wilson interval
    # still reaches ~0.161 at 0/20 and ~0.088 at 0/40 (the error on the reported
    # p_hat, not the half-width). With tol=0.05 it only converges once every cell
    # is pinned — k=80 here, where the one-sided gap is ~0.046.
    assert d["converged"] and d["iterations"] == 80
    assert 0.0 < d["metric"] < 0.05


def test_ci_error_does_not_collapse_for_unobserved_route():
    """Regression (P1): the precision metric must reflect how far the *reported*
    p_hat could be from the truth — max(p_hat - lower, upper - p_hat) — not the
    Wilson half-width around the shifted centre. A map that looks fully
    determined (p_hat in {0, 1}) must keep a wide error so a rarely-sampled route
    is unlikely to fake convergence under a typical tol=0.05."""
    k = 20
    freq = np.array([0.0, float(k), 0.0, float(k)])   # every cell "certain"
    err20 = _max_ci_error(freq, k)
    err40 = _max_ci_error(freq * 2, 2 * k)            # same map, twice the trials
    assert err20 == pytest.approx(0.1612, abs=1e-3)   # not the 0.044 half-width
    assert err40 == pytest.approx(0.0876, abs=1e-3)   # interval still reaches .088
    assert err40 > 0.05                               # tol=0.05 must NOT converge
    assert err40 < err20                              # tightens as k grows
    assert _max_ci_error(freq, 0) == np.inf           # no trials -> unbounded


def test_stabilisation_deterministic_converges_after_patience(slope_dem, cellsize):
    n = slope_dem.shape[1]
    _, _, d = stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, [n * n - 1], 500,
                             np.random.default_rng(0), tol=0.01,
                             convergence="stabilisation", min_iter=20,
                             check_every=10, patience=2, return_diagnostics=True)
    assert d["converged"] and d["iterations"] == 40


def test_precision_stochastic_stops_below_max(cellsize):
    dem = _hill_dem()
    n = dem.shape[1]
    s, t = 0, n * n - 1
    # Cells unique to one of two equally-weighted models sit near p=0.5, whose
    # Wilson half-width needs a few hundred realisations to fall below tol — so
    # give a generous ceiling and check it stops strictly before it.
    n_iter = 1500
    _, _, d = stochastic_lcp(dem, cellsize, cf.tobler, s, [t], n_iter,
                             np.random.default_rng(1),
                             cost_fns=[cf.tobler, cf.herzog], tol=0.06,
                             convergence="precision", return_diagnostics=True)
    assert d["converged"] and d["iterations"] < n_iter and d["metric"] < 0.06


def test_convergence_params_validated(slope_dem, cellsize):
    """P2: the public API must reject convergence parameters that would crash or
    falsely converge — check_every=0 (ZeroDivisionError), min_iter/patience < 1,
    and non-finite or non-positive tol."""
    n = slope_dem.shape[1]
    dst = [n * n - 1]
    base = dict(convergence="precision")
    for bad in (dict(tol=0.05, check_every=0),
                dict(tol=0.05, min_iter=0),
                dict(tol=0.05, patience=0),
                dict(tol=float("nan")),
                dict(tol=float("inf")),
                dict(tol=-0.1),
                dict(tol=0.0)):
        with pytest.raises(ValueError):
            stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, dst, 50,
                           np.random.default_rng(0), **{**base, **bad})


def test_min_iter_respected(slope_dem, cellsize):
    n = slope_dem.shape[1]
    # tol=0.15 would already be met by k=30 (error ~0.114); min_iter=50 must hold
    # the loop until 50 (error ~0.071), proving the floor is respected.
    _, _, d = stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, [n * n - 1], 500,
                             np.random.default_rng(0), tol=0.15,
                             convergence="precision", min_iter=50,
                             check_every=10, return_diagnostics=True)
    assert d["iterations"] == 50


def test_on_check_is_called(slope_dem, cellsize):
    n = slope_dem.shape[1]
    calls = []
    stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, [n * n - 1], 500,
                   np.random.default_rng(0), tol=0.05, convergence="precision",
                   min_iter=20, check_every=10,
                   on_check=lambda it, m, ok: calls.append((it, m, ok)))
    assert calls and calls[0][0] == 20 and calls[-1][2] is True


def test_bad_convergence_method_raises(slope_dem, cellsize):
    n = slope_dem.shape[1]
    with pytest.raises(ValueError):
        stochastic_lcp(slope_dem, cellsize, cf.tobler, 0, [n * n - 1], 50,
                       np.random.default_rng(0), tol=0.05, convergence="median")


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
