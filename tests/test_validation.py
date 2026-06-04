# -*- coding: utf-8 -*-
"""Path Deviation Index (PDI)."""

import numpy as np

from core.validation import pdi


def test_identical_lines_have_zero_pdi():
    line = [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)]
    result = pdi(line, line)
    assert result["area"] == 0.0
    assert result["pdi"] == 0.0


def test_parallel_offset_pdi_is_offset_distance():
    """A modelled line running 1 m beside a 10 m reference => mean deviation 1."""
    reference = [(0.0, 0.0), (10.0, 0.0)]
    modelled = [(0.0, 1.0), (10.0, 1.0)]
    result = pdi(modelled, reference)
    assert result["reference_length"] == 10.0
    assert result["area"] == 10.0          # 10 x 1 rectangle
    assert result["pdi"] == 1.0


def test_zero_length_reference_is_inf():
    reference = [(5.0, 5.0), (5.0, 5.0)]
    modelled = [(0.0, 0.0), (10.0, 0.0)]
    result = pdi(modelled, reference)
    assert not np.isfinite(result["pdi"])
