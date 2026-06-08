# -*- coding: utf-8 -*-
"""Path validation metrics: Path Deviation Index and buffer overlap.

Jan Lewis / Goodchild: the PDI measures how far a modelled path deviates from
a reference path (e.g. a known Roman road). It is the area between the two
polylines divided by the length of the reference path -> mean perpendicular
deviation in map units. Lower is better.

This module works on coordinate sequences (Nx2 arrays), independent of the
raster graph, so it can validate any two lines.

Limitations
-----------
The area is computed with the shoelace formula on the single polygon formed by
``modelled`` followed by ``reference`` reversed. This is only a faithful
"area between the lines" when the two polylines are *similar and roughly
parallel*: they should share orientation (both digitised in the same
direction), not self-intersect, and not cross each other. For lines that cross,
diverge strongly, or double back, the closing polygon self-intersects and the
shoelace area partially cancels, so the PDI is no longer a meaningful mean
deviation. Both coordinate sequences must be in the same projected CRS (metres);
the index is in those map units. A topologically robust area-between-lines
(handling self-intersections) would need geometry operations beyond the
numpy-only core and is out of scope — pre-check inputs accordingly.
"""

import numpy as np

_EPS = 1e-9


def _polyline_length(coords):
    d = np.diff(coords, axis=0)
    return float(np.sum(np.hypot(d[:, 0], d[:, 1])))


def _area_between(path_a, path_b):
    """Approximate area between two polylines via the shoelace formula on the
    closed polygon formed by A followed by reversed B."""
    poly = np.vstack([path_a, path_b[::-1]])
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def pdi(modelled, reference):
    """Return the Path Deviation Index.

    Parameters
    ----------
    modelled, reference : Nx2 / Mx2 arrays of (x, y) coordinates.

    Returns
    -------
    dict with keys: pdi, area, reference_length.
    """
    modelled = np.asarray(modelled, dtype=float)
    reference = np.asarray(reference, dtype=float)

    area = _area_between(modelled, reference)
    ref_len = _polyline_length(reference)
    value = area / ref_len if ref_len > 0 else np.inf

    return {"pdi": value, "area": area, "reference_length": ref_len}


def _densify(coords, step):
    """Resample a polyline to points spaced ~``step`` apart along its length.

    Returns an (M, 2) array of equally-spaced points (endpoints included). Equal
    spacing means counting points is a faithful proxy for arc length.
    """
    coords = np.asarray(coords, dtype=float)
    if len(coords) < 2:
        return coords.copy()
    seg = np.diff(coords, axis=0)
    seg_len = np.hypot(seg[:, 0], seg[:, 1])
    total = float(seg_len.sum())
    if total <= 0:
        return coords[:1].copy()
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    m = max(2, int(np.ceil(total / max(step, _EPS))) + 1)
    s = np.linspace(0.0, total, m)
    idx = np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(seg_len) - 1)
    t = np.where(seg_len[idx] > 0, (s - cum[idx]) / seg_len[idx], 0.0)
    return coords[idx] + t[:, None] * seg[idx]


def _point_to_polyline_dist(points, polyline):
    """Min distance from each of ``points`` (P, 2) to the ``polyline`` (Q, 2).

    Vectorised point-to-segment distance, looping over the Q-1 segments and
    accumulating the running minimum (O(P) memory).
    """
    points = np.asarray(points, dtype=float)
    polyline = np.asarray(polyline, dtype=float)
    if len(polyline) < 2:
        diff = points - polyline[0]
        return np.hypot(diff[:, 0], diff[:, 1])

    a = polyline[:-1]
    ab = np.diff(polyline, axis=0)
    ab_len2 = np.einsum("ij,ij->i", ab, ab)
    best = np.full(len(points), np.inf)
    for k in range(len(a)):
        ap = points - a[k]
        if ab_len2[k] <= 0:
            d = np.hypot(ap[:, 0], ap[:, 1])
        else:
            t = np.clip((ap @ ab[k]) / ab_len2[k], 0.0, 1.0)
            diff = ap - t[:, None] * ab[k]
            d = np.hypot(diff[:, 0], diff[:, 1])
        best = np.minimum(best, d)
    return best


def buffer_overlap(modelled, reference, distances, step=None):
    """Goodchild & Hunter (1997) buffer validation.

    For each buffer distance ``d``, the share (%) of the modelled path's length
    that lies within distance ``d`` of the reference path — the buffer method
    used by R ``leastcostpath``'s ``buffer_validation``. Higher is better
    (100 % = the whole modelled path is within the tolerance buffer).

    Parameters
    ----------
    modelled, reference : Nx2 / Mx2 arrays of (x, y) coordinates (same projected
        CRS, metres).
    distances : iterable of buffer distances in map units. Every distance must
        be strictly positive (a zero or negative buffer is meaningless and, via
        the auto-step below, would force a near-infinite densification).
    step : densification spacing in map units, must be > 0 if given. Default
        ``min(distances) / 20``; smaller is more accurate but slower.

    Returns
    -------
    list of ``{"distance": d, "similarity": pct}`` dicts, in input order.

    Raises
    ------
    ValueError
        If any distance is <= 0, or if an explicit ``step`` is <= 0.
    """
    modelled = np.asarray(modelled, dtype=float)
    reference = np.asarray(reference, dtype=float)
    distances = [float(d) for d in distances]
    if not distances:
        return []
    if any(d <= 0 for d in distances):
        raise ValueError("buffer distances must be strictly positive (> 0)")
    if step is not None and step <= 0:
        raise ValueError("step must be strictly positive (> 0) when given")
    if step is None:
        step = min(distances) / 20.0

    points = _densify(modelled, step)
    dist_to_ref = _point_to_polyline_dist(points, reference)
    n = len(dist_to_ref)

    out = []
    for d in distances:
        share = 100.0 * float(np.count_nonzero(dist_to_ref <= d)) / n if n else 0.0
        out.append({"distance": d, "similarity": share})
    return out


def mean_pairwise_overlap(paths, distance, step=None):
    """Mean buffer-overlap similarity (%) over all ordered pairs of ``paths``.

    A route-stability indicator: 100 % means every path stays within
    ``distance`` of every other; low values mean the routes disagree. Returns
    NaN for fewer than two paths. ``buffer_overlap`` is asymmetric, so averaging
    over ordered pairs symmetrises it. ``distance`` must be strictly positive.
    """
    if distance <= 0:
        raise ValueError("distance must be strictly positive (> 0)")
    paths = [np.asarray(p, dtype=float) for p in paths]
    n = len(paths)
    if n < 2:
        return float("nan")
    vals = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            vals.append(buffer_overlap(
                paths[i], paths[j], [distance], step=step)[0]["similarity"])
    return float(np.mean(vals)) if vals else float("nan")
