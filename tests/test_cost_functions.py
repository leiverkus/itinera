# -*- coding: utf-8 -*-
"""Invariants for the anisotropic cost functions."""

import numpy as np
import pytest

from core import cost_functions as cf

DIST = 10.0
ALL_FUNCS = list(cf.COST_FUNCTIONS.items())

# Functions where uphill must cost more than the mirrored downhill. Two models
# are intentionally excluded because they make *downhill* the costlier direction
# at moderate gradients (descent effort), which the test below pins down:
#   * Llobera & Sluckin  — metabolic descent effort;
#   * Pandolf            — the Santee/Yokota eccentric-braking correction, which
#                          at +-0.3 makes a steep descent dearer than the climb.
UPHILL_COSTLIER = {"tobler", "tobler_offpath", "herzog", "naismith",
                   "irmischer_clarke", "minetti", "wheeled", "pack_animal"}


def test_registry_is_aligned():
    """COST_FUNCTIONS, labels and keys must stay positionally aligned."""
    assert len(cf.COST_FUNCTIONS) == len(cf.COST_FUNCTION_LABELS)
    assert cf.COST_FUNCTION_KEYS == list(cf.COST_FUNCTIONS.keys())


@pytest.mark.parametrize("key,fn", ALL_FUNCS)
def test_costs_finite_and_positive(key, fn):
    slopes = np.linspace(-0.5, 0.5, 21)
    cost = fn(slopes, DIST)
    assert np.all(np.isfinite(cost)), key
    assert np.all(cost > 0.0), key


@pytest.mark.parametrize("key,fn", ALL_FUNCS)
def test_is_directional(key, fn):
    """Anisotropy: traversing a slope up vs down must differ."""
    up = float(fn(np.array([0.3]), DIST)[0])
    down = float(fn(np.array([-0.3]), DIST)[0])
    assert up != pytest.approx(down), key


@pytest.mark.parametrize("key,fn", ALL_FUNCS)
def test_uphill_vs_downhill(key, fn):
    up = float(fn(np.array([0.3]), DIST)[0])
    down = float(fn(np.array([-0.3]), DIST)[0])
    if key in UPHILL_COSTLIER:
        assert up > down, key
    else:  # llobera_sluckin: descent is the costlier direction
        assert up < down, key


@pytest.mark.parametrize("key,fn", ALL_FUNCS)
def test_cost_scales_with_distance(key, fn):
    """Doubling the edge length must not decrease its cost."""
    short = float(fn(np.array([0.1]), DIST)[0])
    long = float(fn(np.array([0.1]), 2 * DIST)[0])
    assert long >= short, key


def test_registry_accepts_cost_params():
    """Every function must tolerate the threaded cost_params kwargs."""
    extra = {"mass": 80.0, "load": 15.0, "terrain": 1.2, "velocity": 1.1}
    for fn in cf.COST_FUNCTIONS.values():
        cost = fn(np.array([0.1, -0.1]), DIST, **extra)
        assert np.all(np.isfinite(cost))


def test_irmischer_clarke_flat_reference():
    """Flat-ground speed = 0.11 + exp(-25/1800) m/s => time = dist / speed."""
    speed = 0.11 + np.exp(-(5.0 ** 2) / 1800.0)
    expected = DIST / speed
    assert cf.irmischer_clarke(np.array([0.0]), DIST)[0] == pytest.approx(
        expected, rel=1e-9)


def test_minetti_downhill_optimum():
    """Minetti's cost of transport bottoms out on a gentle downhill (~ -10%)."""
    grades = np.linspace(-0.30, 0.0, 61)
    costs = cf.minetti(grades, 1.0)
    g_min = grades[int(np.argmin(costs))]
    assert -0.25 < g_min < -0.05
    # and the flat cost must exceed that minimum
    assert cf.minetti(np.array([0.0]), 1.0)[0] > costs.min()


def test_pandolf_monotonic_in_load():
    """More carried load can only raise the metabolic cost."""
    slopes = np.array([0.2, -0.2, 0.0])
    light = cf.pandolf(slopes, DIST, load=0.0)
    heavy = cf.pandolf(slopes, DIST, load=30.0)
    assert np.all(heavy > light)


def test_pandolf_params_flow_through():
    """mass, terrain and velocity must all change the result."""
    s = np.array([0.15])
    base = cf.pandolf(s, DIST)
    assert cf.pandolf(s, DIST, mass=90.0)[0] != pytest.approx(float(base[0]))
    assert cf.pandolf(s, DIST, terrain=1.5)[0] != pytest.approx(float(base[0]))
    # fixed velocity overrides the Tobler-derived default
    assert cf.pandolf(s, DIST, velocity=1.2)[0] != pytest.approx(float(base[0]))


def test_critical_slope_flat_is_unit_cost():
    for fn in (cf.wheeled, cf.pack_animal):
        assert fn(np.array([0.0]), DIST)[0] == pytest.approx(DIST)


def test_cart_is_more_slope_averse_than_pack_animal():
    """On a 30 % climb a cart costs far more per metre than a pack animal."""
    s = np.array([0.3])
    assert cf.wheeled(s, DIST)[0] > cf.pack_animal(s, DIST)[0]


def test_critical_slope_param_flows_through():
    s = np.array([0.2])
    base = cf.wheeled(s, DIST)
    # A tighter critical slope makes the same climb costlier.
    assert cf.wheeled(s, DIST, critical_up=0.04)[0] > base[0]
