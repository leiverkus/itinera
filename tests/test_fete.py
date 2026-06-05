# -*- coding: utf-8 -*-
"""From-Everywhere-To-Everywhere traversal frequency."""

from core import cost_functions as cf
from core.conductance import build_conductance
from core.fete import fete


def test_frequency_shape_and_endpoints(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    n_cells = rows * cols
    nodes = [0, cols - 1, n_cells - 1]   # three corners

    freq = fete(m, nodes, n_cells)
    assert freq.shape == (n_cells,)
    assert freq.sum() > 0
    # Each input node lies on at least one path, so its frequency is positive.
    for node in nodes:
        assert freq[node] > 0


def test_progress_callback_runs(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    n_cells = rows * cols
    seen = []
    fete(m, [0, cols - 1, n_cells - 1], n_cells, progress=seen.append)
    assert seen                      # called at least once
    assert seen[-1] == 1.0           # finishes at 100 %


def test_return_paths_matches_frequency(slope_dem, cellsize):
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    n_cells = rows * cols
    nodes = [0, cols - 1, n_cells - 1]   # three corners -> three pairs

    freq, paths = fete(m, nodes, n_cells, return_paths=True)

    # Same frequency surface whether or not paths are returned.
    assert (freq == fete(m, nodes, n_cells)).all()

    # Three reachable pairs, each labelled with valid endpoint indices that
    # map back to the actual node sequence.
    assert len(paths) == 3
    for i, j, path_nodes, cost in paths:
        assert 0 <= i < j < len(nodes)
        assert path_nodes[0] == nodes[i]
        assert path_nodes[-1] == nodes[j]
        assert cost > 0

    # Accumulating the returned paths reproduces the frequency surface exactly.
    counts = freq * 0
    for _, _, path_nodes, _ in paths:
        for node in path_nodes:
            counts[node] += 1.0
    assert (counts == freq).all()
