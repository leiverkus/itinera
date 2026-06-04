# -*- coding: utf-8 -*-
"""Main plugin class: registers the Processing provider and the map tool."""

import os
from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from .provider import ItineraProvider
from .gui.point_pick_tool import LcpMapTool
from .gui.settings_dialog import LcpSettingsDialog


class ItineraPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None
        self.settings_action = None
        self.map_tool = None

    # --- Processing provider -------------------------------------------
    def initProcessing(self):
        self.provider = ItineraProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

        here = os.path.dirname(__file__)
        icon_path = os.path.join(here, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        settings_icon_path = os.path.join(here, "icon_settings.png")
        settings_icon = (QIcon(settings_icon_path)
                         if os.path.exists(settings_icon_path) else icon)
        self.action = QAction(icon, "Interactive LCP (two clicks)",
                              self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.toggle_map_tool)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("Itinera", self.action)

        self.map_tool = LcpMapTool(self.iface.mapCanvas(), self.iface)
        self.map_tool.setAction(self.action)

        self.settings_action = QAction(
            settings_icon, "Interactive LCP settings…",
            self.iface.mainWindow())
        self.settings_action.triggered.connect(self.open_settings)
        self.iface.addToolBarIcon(self.settings_action)
        self.iface.addPluginToMenu("Itinera", self.settings_action)

    def toggle_map_tool(self, checked):
        if checked:
            self.iface.mapCanvas().setMapTool(self.map_tool)
        else:
            self.map_tool.reset()
            self.iface.mapCanvas().unsetMapTool(self.map_tool)

    def open_settings(self):
        dlg = LcpSettingsDialog(
            self.map_tool.cost_key, self.map_tool.neighbours,
            self.iface.mainWindow())
        if dlg.exec_():
            self.map_tool.set_settings(
                dlg.selected_cost_key(), dlg.selected_neighbours())

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("Itinera", self.action)
        if self.settings_action is not None:
            self.iface.removeToolBarIcon(self.settings_action)
            self.iface.removePluginMenu("Itinera", self.settings_action)
        if self.map_tool is not None:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)
