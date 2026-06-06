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


def tobler(slope, distance, **_):
    """Tobler's Hiking Function (1993).

    Walking speed v (km/h) = 6 * exp(-3.5 * |slope + 0.05|), where slope is
    dh/dx (tan of the angle). Cost returned is travel time in seconds.
    The +0.05 offset makes the maximum speed occur on a gentle downhill,
    which is why this is genuinely anisotropic.
    """
    speed_kmh = 6.0 * np.exp(-3.5 * np.abs(slope + 0.05))
    speed_ms = speed_kmh * 1000.0 / 3600.0
    return distance / (speed_ms + _EPS)


def tobler_offpath(slope, distance, **_):
    """Tobler off-path variant: speed reduced to 0.6 of on-path."""
    speed_kmh = 0.6 * 6.0 * np.exp(-3.5 * np.abs(slope + 0.05))
    speed_ms = speed_kmh * 1000.0 / 3600.0
    return distance / (speed_ms + _EPS)


def herzog(slope, distance, **_):
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


def naismith(slope, distance, **_):
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


def llobera_sluckin(slope, distance, **_):
    """Llobera & Sluckin (2007) metabolic energy expenditure (kcal-based)."""
    s = slope
    e = (2.635 + 17.37 * np.abs(s) + 42.37 * s**2
         - 21.43 * s**3 + 14.93 * s**4)
    e = np.clip(e, _EPS, None)
    return e * distance


def irmischer_clarke(slope, distance, **_):
    """Irmischer & Clarke (2018) on-path walking speed as a time cost.

    GPS-derived walking speed (m/s) for on-path male travel:

        v = 0.11 + exp(-(G + 5)^2 / (2 * 30^2)),  G = slope * 100 (grade %)

    The grade is *signed* (not |G|, as in some R implementations), so the
    Gaussian peaks at a gentle downhill of ~-5 % grade -- genuinely
    anisotropic, exactly like Tobler's +0.05 offset. Cost returned is travel
    time in seconds. Uphill is slower (costlier) than the mirrored downhill.
    """
    grade = slope * 100.0
    speed_ms = 0.11 + np.exp(-((grade + 5.0) ** 2) / (2.0 * 30.0 ** 2))
    return distance / (speed_ms + _EPS)


def minetti(slope, distance, **_):
    """Minetti et al. (2002) metabolic cost of transport.

    Energy cost of walking per unit mass and distance (J/kg/m) as a quintic
    polynomial in the *signed* gradient i = dh/dx:

        C(i) = 280.5 i^5 - 58.7 i^4 - 76.8 i^3 + 51.9 i^2 + 19.6 i + 2.5

    Returns energy per kg over the edge (J/kg); body mass is a constant
    multiplier that does not change the optimal path, so it is omitted. Valid
    roughly -0.45 <= i <= 0.45; the curve has its minimum near i ~ -0.1, so
    gentle downhill is the cheapest direction while uphill is costlier.
    """
    i = slope
    c = (280.5 * i**5 - 58.7 * i**4 - 76.8 * i**3
         + 51.9 * i**2 + 19.6 * i + 2.5)
    c = np.clip(c, _EPS, None)
    return c * distance


def pandolf(slope, distance, *, mass=70.0, load=0.0, terrain=1.0,
            velocity=None, **_):
    """Pandolf et al. (1977) metabolic rate, with the Santee/Yokota downhill
    correction, as an energy cost.

    Metabolic rate (Watts):

        M = 1.5 W + 2.0 (W+L)(L/W)^2 + N (W+L)(1.5 V^2 + 0.35 V G)

    with W = body mass (kg), L = carried load (kg), N = terrain factor,
    V = walking velocity (m/s) and G = |slope| * 100 (grade %). For *downhill*
    travel (signed grade < 0) the Santee et al. (2001) / Yokota et al. (2004)
    correction is subtracted to model the (eccentric) cost of descent:

        M_dh = M - N [ G(W+L)V/3.5 - (W+L)(G+6)^2/W + (25 - V^2) ]

    Edge cost is energy = M * (distance / V) in joules. When ``velocity`` is
    None, V is derived per-edge from the Tobler on-path speed at the signed
    slope, which keeps the function anisotropic. ``mass``, ``load``,
    ``terrain`` and ``velocity`` are threaded from the GUI via ``cost_params``.
    """
    W = float(mass)
    L = float(load)
    N = float(terrain)
    slope = np.asarray(slope, dtype=float)

    if velocity is None:
        speed_kmh = 6.0 * np.exp(-3.5 * np.abs(slope + 0.05))
        V = speed_kmh * 1000.0 / 3600.0          # Tobler-derived m/s (signed)
    else:
        V = np.full_like(slope, float(velocity))
    V = np.clip(V, _EPS, None)

    g = slope * 100.0                            # signed grade (%)
    a = np.abs(g)                                # grade magnitude
    base = 1.5 * W + 2.0 * (W + L) * (L / W) ** 2 \
        + N * (W + L) * (1.5 * V**2 + 0.35 * V * a)
    correction = N * (a * (W + L) * V / 3.5
                      - (W + L) * (a + 6.0) ** 2 / W
                      + (25.0 - V**2))
    metabolic = np.where(g >= 0.0, base, base - correction)
    metabolic = np.clip(metabolic, _EPS, None)
    return metabolic * (distance / V)


# Registry consumed by the Processing algorithms (enum order matters for the
# parameter dropdown, so keep this list stable -- append new functions, never
# reorder).
COST_FUNCTIONS = {
    "tobler": tobler,
    "tobler_offpath": tobler_offpath,
    "herzog": herzog,
    "naismith": naismith,
    "llobera_sluckin": llobera_sluckin,
    "irmischer_clarke": irmischer_clarke,
    "minetti": minetti,
    "pandolf": pandolf,
}

COST_FUNCTION_LABELS = [
    "Tobler's Hiking Function",
    "Tobler off-path",
    "Herzog (metabolic)",
    "Naismith's rule",
    "Llobera & Sluckin",
    "Irmischer & Clarke (speed)",
    "Minetti (energy)",
    "Pandolf (energy, load-aware)",
]

COST_FUNCTION_KEYS = list(COST_FUNCTIONS.keys())
