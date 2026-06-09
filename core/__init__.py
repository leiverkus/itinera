# -*- coding: utf-8 -*-
"""Itinera — anisotropic least-cost path / corridor / FETE primitives.

Pure numpy/scipy, no QGIS and no GDAL. Kept GUI-free so it is unit-testable
outside QGIS and reused by both the Processing algorithms and the interactive
map tool. Published to PyPI this is the importable package ``itinera``; inside
the QGIS plugin it is the private ``core`` package.

Note: ``raster_io`` (GDAL) is intentionally NOT re-exported here, so importing
this package never pulls in ``osgeo``. The plugin imports ``raster_io`` directly
where it needs raster I/O.
"""

from .cost_functions import (
    tobler, tobler_offpath, herzog, naismith, llobera_sluckin,
    irmischer_clarke, minetti, pandolf, wheeled, pack_animal,
)
from .conductance import (
    build_conductance, build_conductance_friction,
    rowcol_to_node, node_to_rowcol,
)
from .lcp import accumulated_cost, least_cost_path
from .corridor import corridor, corridor_band
from .fete import fete
from .accessibility import accessibility
from .rsp import rsp_passages
from .circuit import current_density, restoration_score
from .multicriteria import composite_friction
from .validation import pdi, buffer_overlap, mean_pairwise_overlap
from .stochastic import (
    stochastic_lcp, add_dem_error, add_global_stochasticity,
    simulate_error_field,
)
from .grid_align import (
    xy_to_rowcol,
    check_regular_geotransform, assert_regular_geotransform,
    check_grids_aligned, assert_grids_aligned,
)
from .memory import estimate_conductance_bytes, format_bytes
from .resample import block_reduce_mean

__all__ = [
    # cost functions
    "tobler", "tobler_offpath", "herzog", "naismith", "llobera_sluckin",
    "irmischer_clarke", "minetti", "pandolf", "wheeled", "pack_animal",
    # conductance
    "build_conductance", "build_conductance_friction",
    "rowcol_to_node", "node_to_rowcol",
    # paths
    "accumulated_cost", "least_cost_path",
    "corridor", "corridor_band",
    "fete",
    # accessibility
    "accessibility",
    # randomized shortest paths
    "rsp_passages",
    # circuit theory
    "current_density", "restoration_score",
    # multi-criteria
    "composite_friction",
    # validation
    "pdi", "buffer_overlap", "mean_pairwise_overlap",
    # stochastic
    "stochastic_lcp", "add_dem_error", "add_global_stochasticity",
    "simulate_error_field",
    # grid / alignment
    "xy_to_rowcol",
    "check_regular_geotransform", "assert_regular_geotransform",
    "check_grids_aligned", "assert_grids_aligned",
    # memory / resample
    "estimate_conductance_bytes", "format_bytes",
    "block_reduce_mean",
]
