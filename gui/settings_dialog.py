# -*- coding: utf-8 -*-
"""Settings dialog for the interactive LCP map tool.

Exposes the same cost function + neighbourhood choices as the Processing
algorithms (read from ``cost_functions.COST_FUNCTION_LABELS``), so the
two-click tool is no longer hard-wired to Tobler + 8-neighbour.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QComboBox, QFormLayout, QVBoxLayout, QDialogButtonBox,
)

from ..core import cost_functions as cf

NEIGHBOUR_VALUES = [4, 8, 16]


class LcpSettingsDialog(QDialog):
    """Pick the cost function and neighbourhood for the interactive LCP tool."""

    def __init__(self, cost_key="tobler", neighbours=8, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Interactive LCP settings")

        self.cost_combo = QComboBox()
        self.cost_combo.addItems(cf.COST_FUNCTION_LABELS)
        if cost_key in cf.COST_FUNCTION_KEYS:
            self.cost_combo.setCurrentIndex(
                cf.COST_FUNCTION_KEYS.index(cost_key))

        self.nb_combo = QComboBox()
        self.nb_combo.addItems([str(v) for v in NEIGHBOUR_VALUES])
        if neighbours in NEIGHBOUR_VALUES:
            self.nb_combo.setCurrentIndex(NEIGHBOUR_VALUES.index(neighbours))

        form = QFormLayout()
        form.addRow("Cost function", self.cost_combo)
        form.addRow("Neighbourhood", self.nb_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def selected_cost_key(self):
        return cf.COST_FUNCTION_KEYS[self.cost_combo.currentIndex()]

    def selected_neighbours(self):
        return NEIGHBOUR_VALUES[self.nb_combo.currentIndex()]
