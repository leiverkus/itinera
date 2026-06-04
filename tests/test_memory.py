# -*- coding: utf-8 -*-
"""Conductance memory estimates."""

from core.memory import (
    estimate_conductance_bytes, format_bytes, RECOMMENDED_MAX_CELLS,
)


def test_estimate_is_positive():
    assert estimate_conductance_bytes(100, 100, 8) > 0


def test_estimate_grows_with_cells():
    small = estimate_conductance_bytes(100, 100, 8)
    big = estimate_conductance_bytes(200, 200, 8)
    assert big > small


def test_estimate_grows_with_neighbours():
    n8 = estimate_conductance_bytes(100, 100, 8)
    n16 = estimate_conductance_bytes(100, 100, 16)
    assert n16 > n8


def test_recommended_threshold_is_sane():
    assert RECOMMENDED_MAX_CELLS > 0


def test_format_bytes_units():
    assert format_bytes(512).endswith("B")
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(5 * 1024 ** 3) == "5.0 GB"
