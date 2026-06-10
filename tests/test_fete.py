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
    nodes = [0, cols - 1, n_cells - 1]   # three corners -> 3*2 directed routes

    freq, paths = fete(m, nodes, n_cells, return_paths=True)

    # Same frequency surface whether or not paths are returned.
    assert (freq == fete(m, nodes, n_cells)).all()

    # n*(n-1) = 6 directed routes, each labelled with distinct from/to indices
    # that map back to the actual node sequence.
    assert len(paths) == len(nodes) * (len(nodes) - 1)
    seen = set()
    for i, j, path_nodes, cost in paths:
        assert 0 <= i < len(nodes) and 0 <= j < len(nodes) and i != j
        assert path_nodes[0] == nodes[i]
        assert path_nodes[-1] == nodes[j]
        assert cost > 0
        seen.add((i, j))
    assert seen == {(i, j) for i in range(len(nodes))
                    for j in range(len(nodes)) if i != j}

    # Accumulating the returned paths reproduces the frequency surface exactly.
    counts = freq * 0
    for _, _, path_nodes, _ in paths:
        for node in path_nodes:
            counts[node] += 1.0
    assert (counts == freq).all()


def test_routes_are_directed(slope_dem, cellsize):
    """Anisotropy: a->b and b->a are computed separately and can differ."""
    m, rows, cols = build_conductance(slope_dem, cellsize, cf.tobler)
    n_cells = rows * cols
    a, b = 0, n_cells - 1
    _, paths = fete(m, [a, b], n_cells, return_paths=True)
    assert len(paths) == 2                       # both directions, not one
    fwd = next(p for (i, j, p, _) in paths if (i, j) == (0, 1))
    rev = next(p for (i, j, p, _) in paths if (i, j) == (1, 0))
    assert fwd[0] == a and fwd[-1] == b
    assert rev[0] == b and rev[-1] == a
