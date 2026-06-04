# -*- coding: utf-8 -*-
"""Build a sparse anisotropic conductance (cost) matrix from a DEM.

The graph has one node per raster cell. Edges connect each cell to its
neighbours (4, 8, 16 or 32 connectivity). Edge weight = cost of moving from
cell A to cell B, evaluated with a directional cost function, so the matrix is
asymmetric (true anisotropy).

NoData cells are excluded: any edge touching a masked cell is dropped, so they
become unreachable rather than infinitely cheap.
"""

import numpy as np
from scipy.sparse import csr_matrix


# Neighbour offset sets. 16/32 use knight-style moves to reduce the
# "metric distortion" of grid-restricted paths (Llobera-style).
_OFFSETS = {
    4: [(-1, 0), (1, 0), (0, -1), (0, 1)],
    8: [(-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1)],
    16: [(-1, 0), (1, 0), (0, -1), (0, 1),
         (-1, -1), (-1, 1), (1, -1), (1, 1),
         (-2, -1), (-2, 1), (2, -1), (2, 1),
         (-1, -2), (-1, 2), (1, -2), (1, 2)],
}


def _edge_blocks(rows, cols, cellsize, neighbours):
    """Yield (a_idx, b_idx, sl_a, sl_b, dist) for each neighbour offset.

    Shared scaffolding for the conductance builders. ``a_idx``/``b_idx`` are the
    flat node-index arrays for the two ends of every edge in the block; ``sl_a``
    /``sl_b`` are the matching ``(slice, slice)`` tuples so callers can slice
    their own rasters (DEM, friction, NoData mask); ``dist`` is the edge length
    in metres.
    """
    if neighbours not in _OFFSETS:
        raise ValueError("neighbours must be one of 4, 8, 16")

    idx = np.arange(rows * cols).reshape(rows, cols)

    for dr, dc in _OFFSETS[neighbours]:
        r0, r1 = max(0, -dr), rows - max(0, dr)
        c0, c1 = max(0, -dc), cols - max(0, dc)

        sl_a = (slice(r0, r1), slice(c0, c1))
        sl_b = (slice(r0 + dr, r1 + dr), slice(c0 + dc, c1 + dc))

        dist = cellsize * np.hypot(dr, dc)
        yield idx[sl_a], idx[sl_b], sl_a, sl_b, dist


def build_conductance(dem, cellsize, cost_fn, neighbours=8, nodata_mask=None):
    """Return (matrix, n_rows, n_cols).

    Parameters
    ----------
    dem : 2D float ndarray (elevations, metres)
    cellsize : float (metres per pixel; assumes square pixels)
    cost_fn : callable(slope, distance) -> cost
    neighbours : 4, 8 or 16
    nodata_mask : optional bool 2D ndarray, True where data is invalid
    """
    rows, cols = dem.shape
    n = rows * cols

    if nodata_mask is None:
        nodata_mask = ~np.isfinite(dem)

    src_all, dst_all, w_all = [], [], []

    for a_idx, b_idx, sl_a, sl_b, dist in _edge_blocks(
            rows, cols, cellsize, neighbours):
        slope = (dem[sl_b] - dem[sl_a]) / dist   # directional slope A -> B
        cost = cost_fn(slope, dist)

        # Drop edges touching NoData on either end.
        valid = ~(nodata_mask[sl_a] | nodata_mask[sl_b])
        valid &= np.isfinite(cost)

        src_all.append(a_idx[valid])
        dst_all.append(b_idx[valid])
        w_all.append(cost[valid])

    src = np.concatenate(src_all)
    dst = np.concatenate(dst_all)
    w = np.concatenate(w_all)

    matrix = csr_matrix((w, (src, dst)), shape=(n, n))
    return matrix, rows, cols


def build_conductance_friction(friction, cellsize, neighbours=8,
                               dem=None, cost_fn=None,
                               friction_nodata_mask=None):
    """Build a cost matrix from a friction raster (cost per metre).

    Two modes:

    * **Isotropic** (``dem is None``): edge cost =
      ``mean(friction_A, friction_B) * distance``. Friction is read as a
      cost-per-metre, so the matrix is symmetric — correct for a genuinely
      isotropic surface (this is *not* a forbidden symmetrisation of a slope
      matrix; see CLAUDE.md constraint 3).
    * **Combined** (``dem`` and ``cost_fn`` supplied): edge cost =
      ``mean(friction_A, friction_B) * cost_fn(slope, distance)``. Friction
      acts as a dimensionless multiplier (1.0 = neutral, >1 harder, <1
      preferred) on the anisotropic slope cost, so the matrix stays asymmetric.

    Parameters
    ----------
    friction : 2D float ndarray (cost per metre, or a multiplier with a DEM)
    cellsize : float (metres per pixel; assumes square pixels)
    neighbours : 4, 8 or 16
    dem : optional 2D float ndarray (elevations, metres), same shape as friction
    cost_fn : callable(slope, distance) -> cost; required when dem is given
    friction_nodata_mask : optional bool 2D ndarray, True where invalid

    Returns
    -------
    (matrix, n_rows, n_cols)
    """
    rows, cols = friction.shape
    n = rows * cols

    if dem is not None:
        if dem.shape != friction.shape:
            raise ValueError("dem and friction must have the same shape")
        if cost_fn is None:
            raise ValueError("cost_fn is required when a dem is supplied")

    # Non-positive or non-finite friction is impassable (edge dropped).
    if friction_nodata_mask is None:
        friction_nodata_mask = ~np.isfinite(friction) | (friction <= 0)
    dem_nodata_mask = (~np.isfinite(dem)) if dem is not None else None

    src_all, dst_all, w_all = [], [], []

    for a_idx, b_idx, sl_a, sl_b, dist in _edge_blocks(
            rows, cols, cellsize, neighbours):
        fric = 0.5 * (friction[sl_a] + friction[sl_b])

        if dem is None:
            cost = fric * dist
        else:
            slope = (dem[sl_b] - dem[sl_a]) / dist
            cost = fric * cost_fn(slope, dist)

        valid = ~(friction_nodata_mask[sl_a] | friction_nodata_mask[sl_b])
        if dem_nodata_mask is not None:
            valid &= ~(dem_nodata_mask[sl_a] | dem_nodata_mask[sl_b])
        valid &= np.isfinite(cost)

        src_all.append(a_idx[valid])
        dst_all.append(b_idx[valid])
        w_all.append(cost[valid])

    src = np.concatenate(src_all)
    dst = np.concatenate(dst_all)
    w = np.concatenate(w_all)

    matrix = csr_matrix((w, (src, dst)), shape=(n, n))
    return matrix, rows, cols


def rowcol_to_node(row, col, n_cols):
    return row * n_cols + col


def node_to_rowcol(node, n_cols):
    return divmod(node, n_cols)
