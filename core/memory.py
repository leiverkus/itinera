# -*- coding: utf-8 -*-
"""Rough memory estimates for the in-RAM conductance matrix.

The whole graph is held in memory (one node per cell, up to ``neighbours``
directed edges per cell), so large DEMs can exhaust RAM. These pure helpers let
the algorithm wrappers warn before that happens and let users size a clip or a
resample factor. Pure Python — unit-testable outside QGIS.
"""

# Soft threshold above which the wrappers warn the user (cells = rows * cols).
# At 8-neighbour this is already ~1 GB of matrix + build temporaries; treat it
# as "clip or resample first" rather than a hard limit.
RECOMMENDED_MAX_CELLS = 4_000_000


def estimate_conductance_bytes(rows, cols, neighbours):
    """Estimate peak bytes to build the sparse conductance matrix.

    Counts the CSR storage (float64 weights + int32 indices + int32 indptr) plus
    the transient COO build arrays (int64 src/dst + float64 weights) that exist
    during construction. An upper-ish estimate (border edges are not subtracted)
    — meant for an order-of-magnitude warning, not exact accounting.
    """
    n_cells = rows * cols
    n_edges = n_cells * neighbours          # upper bound (ignores borders)
    csr = n_edges * (8 + 4) + (n_cells + 1) * 4
    build = n_edges * (8 + 8 + 8)           # src + dst + weight temporaries
    return csr + build


def format_bytes(n):
    """Human-readable byte count (e.g. '1.2 GB')."""
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            return "%.1f %s" % (value, unit)
        value /= 1024.0
