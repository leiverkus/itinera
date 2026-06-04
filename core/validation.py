# -*- coding: utf-8 -*-
"""Path Deviation Index (PDI) validation.

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
