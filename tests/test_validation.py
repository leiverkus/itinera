# -*- coding: utf-8 -*-
"""Path validation metrics: PDI and buffer overlap."""

import numpy as np
import pytest

from core.validation import pdi, buffer_overlap, mean_pairwise_overlap


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


# --- buffer overlap (Goodchild & Hunter 1997) ------------------------------

def test_buffer_overlap_identical_is_full():
    line = [(0.0, 0.0), (100.0, 0.0)]
    out = buffer_overlap(line, line, [0.5, 5.0, 50.0])
    assert all(row["similarity"] == 100.0 for row in out)


def test_buffer_overlap_offset_threshold():
    """A path 1 m off the reference is outside a 0.5 m buffer, inside a 2 m one."""
    reference = [(0.0, 0.0), (100.0, 0.0)]
    modelled = [(0.0, 1.0), (100.0, 1.0)]
    out = {row["distance"]: row["similarity"]
           for row in buffer_overlap(modelled, reference, [0.5, 2.0])}
    assert out[0.5] == 0.0
    assert out[2.0] == 100.0


def test_buffer_overlap_half_inside():
    """Run beside the reference (inside d=2) for half the length, offset far
    (distance 10, outside) for the other half => roughly 50 %."""
    reference = [(0.0, 0.0), (100.0, 0.0)]
    modelled = [(0.0, 1.0), (50.0, 1.0), (50.0, 10.0), (100.0, 10.0)]
    sim = buffer_overlap(modelled, reference, [2.0], step=0.5)[0]["similarity"]
    assert 35.0 < sim < 60.0


def test_buffer_overlap_monotonic_in_distance():
    reference = [(0.0, 0.0), (100.0, 0.0)]
    modelled = [(0.0, 3.0), (100.0, 12.0)]
    sims = [row["similarity"]
            for row in buffer_overlap(modelled, reference, [1.0, 5.0, 10.0, 20.0])]
    assert sims == sorted(sims)


def test_buffer_overlap_rejects_nonpositive_distance():
    ref = [(0.0, 0.0), (100.0, 0.0)]
    mod = [(0.0, 1.0), (100.0, 1.0)]
    for bad in ([0.0], [50.0, 0.0], [-10.0]):
        with pytest.raises(ValueError):
            buffer_overlap(mod, ref, bad)


def test_buffer_overlap_rejects_nonpositive_step():
    ref = [(0.0, 0.0), (100.0, 0.0)]
    mod = [(0.0, 1.0), (100.0, 1.0)]
    with pytest.raises(ValueError):
        buffer_overlap(mod, ref, [50.0], step=0.0)
    with pytest.raises(ValueError):
        buffer_overlap(mod, ref, [50.0], step=-1.0)


def test_mean_pairwise_overlap_rejects_nonpositive_distance():
    ref = np.array([[0.0, 0.0], [100.0, 0.0]])
    mod = np.array([[0.0, 1.0], [100.0, 1.0]])
    with pytest.raises(ValueError):
        mean_pairwise_overlap([ref, mod], 0.0)


def test_mean_pairwise_overlap():
    ref = np.array([[0.0, 0.0], [100.0, 0.0]])
    near = np.array([[0.0, 0.5], [100.0, 0.5]])
    far = np.array([[0.0, 500.0], [100.0, 500.0]])
    assert mean_pairwise_overlap([ref, near], 2.0) == 100.0
    assert mean_pairwise_overlap([ref, far], 2.0) == 0.0
    assert np.isnan(mean_pairwise_overlap([ref], 2.0))
