# -*- coding: utf-8 -*-
"""Main plugin class: registers the Processing provider and the map tool."""

import os
from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from .provider import ItineraProvider
from .gui.point_pick_tool import LcpMapTool


class ItineraPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None
        self.map_tool = None

    # --- Processing provider -------------------------------------------
    def initProcessing(self):
        self.provider = ItineraProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.action = QAction(icon, "Interactive LCP (two clicks)",
                              self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.toggle_map_tool)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("Itinera", self.action)

        self.map_tool = LcpMapTool(self.iface.mapCanvas(), self.iface)
        self.map_tool.setAction(self.action)

    def toggle_map_tool(self, checked):
        if checked:
            self.iface.mapCanvas().setMapTool(self.map_tool)
        else:
            self.map_tool.reset()
            self.iface.mapCanvas().unsetMapTool(self.map_tool)

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("Itinera", self.action)
        if self.map_tool is not None:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)
