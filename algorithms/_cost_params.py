# -*- coding: utf-8 -*-
"""Shared GUI parameters for load-aware cost functions (Pandolf).

Most cost functions are pure ``f(slope, distance)``. Pandolf additionally needs
a body mass, a carried load and a terrain factor; these are exposed once here and
threaded into the core builders via the ``cost_params`` dict, so every algorithm
that builds a conductance matrix can offer them with three identical lines. The
parameters are advanced (collapsed by default) and ignored by the functions that
do not read them, so they are harmless when another cost function is selected.
"""

from qgis.core import QgsProcessingParameterNumber

MASS = "BODY_MASS"
LOAD = "LOAD"
TERRAIN = "TERRAIN_FACTOR"


def add_cost_params(alg):
    """Add the Pandolf body-mass / load / terrain-factor parameters to ``alg``.

    Call from ``initAlgorithm``. Each is flagged advanced so it stays out of the
    way unless the Pandolf cost function is in use.
    """
    advanced = QgsProcessingParameterNumber.Double

    mass = QgsProcessingParameterNumber(
        MASS, "Body mass [kg] (Pandolf cost function)",
        type=advanced, defaultValue=70.0, minValue=1.0)
    load = QgsProcessingParameterNumber(
        LOAD, "Carried load [kg] (Pandolf cost function)",
        type=advanced, defaultValue=0.0, minValue=0.0)
    terrain = QgsProcessingParameterNumber(
        TERRAIN, "Terrain factor (Pandolf cost function; 1.0 = treadmill)",
        type=advanced, defaultValue=1.0, minValue=0.1)

    for p in (mass, load, terrain):
        p.setFlags(p.flags() | QgsProcessingParameterNumber.FlagAdvanced)
        alg.addParameter(p)


def read_cost_params(alg, parameters, context):
    """Return the ``cost_params`` dict to forward to the core cost builders."""
    return {
        "mass": alg.parameterAsDouble(parameters, MASS, context),
        "load": alg.parameterAsDouble(parameters, LOAD, context),
        "terrain": alg.parameterAsDouble(parameters, TERRAIN, context),
    }
