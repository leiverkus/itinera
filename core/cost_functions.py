# -*- coding: utf-8 -*-
"""Anisotropic cost functions.

Each function receives the *directional* slope (dz / horizontal_distance,
i.e. rise over run, signed: positive = uphill in direction of travel) and the
horizontal distance between the two cell centres in metres. It returns the
*cost* of traversing that edge (time in seconds, or an abstract cost).

Because slope is directional, A->B and B->A yield different costs => true
anisotropy. This is the central difference from isotropic MCP approaches.
"""

import numpy as np

# Small epsilon to avoid division by zero in speed-based functions.
_EPS = 1e-9


def tobler(slope, distance):
    """Tobler's Hiking Function (1993).

    Walking speed v (km/h) = 6 * exp(-3.5 * |slope + 0.05|), where slope is
    dh/dx (tan of the angle). Cost returned is travel time in seconds.
    The +0.05 offset makes the maximum speed occur on a gentle downhill,
    which is why this is genuinely anisotropic.
    """
    speed_kmh = 6.0 * np.exp(-3.5 * np.abs(slope + 0.05))
    speed_ms = speed_kmh * 1000.0 / 3600.0
    return distance / (speed_ms + _EPS)


def tobler_offpath(slope, distance):
    """Tobler off-path variant: speed reduced to 0.6 of on-path."""
    speed_kmh = 0.6 * 6.0 * np.exp(-3.5 * np.abs(slope + 0.05))
    speed_ms = speed_kmh * 1000.0 / 3600.0
    return distance / (speed_ms + _EPS)


def herzog(slope, distance):
    """Herzog (2013) metabolic cost function for wheeled/pedestrian movement.

    A symmetric-ish polynomial in slope (here s = dh/dx as a fraction).
    Returns an abstract metabolic cost scaled by distance.
    """
    s = slope
    # Herzog's sixth-order polynomial (cost per metre), normalised so that
    # flat ground ~ 1.0.
    cost_per_m = (1337.8 * s**6 + 278.19 * s**5 - 517.39 * s**4
                  - 78.199 * s**3 + 93.419 * s**2 + 19.825 * s + 1.64)
    cost_per_m = np.clip(cost_per_m, _EPS, None)
    return cost_per_m * distance


def naismith(slope, distance):
    """Naismith's rule (1892) as a time cost.

    Base walking 5 km/h on the flat, plus extra time for ascent. Descent is
    treated as flat in the classic rule (anisotropic on the uphill side only).
    """
    base_ms = 5.0 * 1000.0 / 3600.0
    horiz_time = distance / base_ms
    dz = slope * distance  # vertical change over this edge
    ascent = np.where(dz > 0, dz, 0.0)
    # Naismith: +1 hour per 600 m ascent => 6 s per metre of climb.
    return horiz_time + ascent * 6.0


def llobera_sluckin(slope, distance):
    """Llobera & Sluckin (2007) metabolic energy expenditure (kcal-based)."""
    s = slope
    e = (2.635 + 17.37 * np.abs(s) + 42.37 * s**2
         - 21.43 * s**3 + 14.93 * s**4)
    e = np.clip(e, _EPS, None)
    return e * distance


# Registry consumed by the Processing algorithms (enum order matters for the
# parameter dropdown, so keep this list stable).
COST_FUNCTIONS = {
    "tobler": tobler,
    "tobler_offpath": tobler_offpath,
    "herzog": herzog,
    "naismith": naismith,
    "llobera_sluckin": llobera_sluckin,
}

COST_FUNCTION_LABELS = [
    "Tobler's Hiking Function",
    "Tobler off-path",
    "Herzog (metabolic)",
    "Naismith's rule",
    "Llobera & Sluckin",
]

COST_FUNCTION_KEYS = list(COST_FUNCTIONS.keys())
