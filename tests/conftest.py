# -*- coding: utf-8 -*-
"""Shared pytest fixtures and import setup for the GUI-free core tests.

The plugin root (the directory containing ``core/``) is put on ``sys.path`` so
tests can ``import core.*`` directly. We deliberately do NOT import the
``itinera`` package itself — its ``__init__``/``plugin`` modules pull in QGIS,
which is unavailable outside QGIS. Importing ``core`` standalone keeps the suite
runnable in plain CI.
"""

import os
import sys

import numpy as np
import pytest

# tests/ -> plugin root (contains core/)
_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)


CELLSIZE = 10.0


@pytest.fixture
def cellsize():
    return CELLSIZE


@pytest.fixture
def flat_dem():
    """Constant-elevation DEM (no slope anywhere)."""
    return np.full((8, 8), 100.0, dtype=np.float64)


@pytest.fixture
def slope_dem():
    """A tilted plane rising 5 m per row, so movement is genuinely directional.

    Going to a higher row index is uphill (+slope); the reverse is downhill.
    With this DEM the conductance matrix must be asymmetric.
    """
    rows, cols = 8, 8
    dem = np.empty((rows, cols), dtype=np.float64)
    for r in range(rows):
        dem[r, :] = 100.0 + r * 5.0
    return dem


@pytest.fixture
def friction():
    """Strictly positive friction raster (cost per metre), some variation."""
    rng = np.random.default_rng(42)
    return rng.random((8, 8)) * 4.0 + 1.0
