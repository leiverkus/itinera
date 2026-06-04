# -*- coding: utf-8 -*-
"""Itinera – QGIS plugin entry point."""


def classFactory(iface):
    from .plugin import ItineraPlugin
    return ItineraPlugin(iface)
