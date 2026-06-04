# -*- coding: utf-8 -*-
"""Invariants for the anisotropic cost functions."""

import numpy as np
import pytest

from core import cost_functions as cf

DIST = 10.0
ALL_FUNCS = list(cf.COST_FUNCTIONS.items())

# Functions where uphill must cost more than the mirrored downhill. Llobera &
# Sluckin is intentionally excluded: its model makes *downhill* slightly costlier
# at moderate gradients (descent effort), which the test below pins down.
UPHILL_COSTLIER = {"tobler", "tobler_offpath", "herzog", "naismith"}


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
