# -*- coding: utf-8 -*-
"""Least-cost corridor — and the transpose gotcha it depends on."""

import numpy as np

from core import cost_functions as cf
from core.conductance import build_conductance
from core.corridor import corridor, corridor_band
from core.lcp import least_cost_path


def test_corridor_minimum_equals_lcp_cost(slope_dem, cellsize):
    """corridor[i] = cost(o->i) + cost(i->d); its minimum is cost(o->d).

    This only holds if the second surface is grown on the *transposed* matrix.
    If a refactor drops the transpose, the minimum diverges from the true LCP
    cost and this test fails — guarding the documented gotcha.
    """
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    origin = 0
    dest = rows * cols - 1

    _, lcp_cost = least_cost_path(m, origin, dest)
    surface, minimum = corridor(m, origin, dest)

    assert surface.shape == (rows * cols,)
    assert minimum == lcp_cost


def test_corridor_band_includes_optimum(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    surface, minimum = corridor(m, 0, rows * cols - 1)

    band = corridor_band(surface, minimum, tolerance=0.0)
    assert band.dtype == bool
    assert band.any()                       # at least the optimal cells
    # Widening the tolerance can only grow the band.
    wider = corridor_band(surface, minimum, tolerance=minimum)
    assert wider.sum() >= band.sum()
