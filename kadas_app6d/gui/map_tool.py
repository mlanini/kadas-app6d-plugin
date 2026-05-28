# -*- coding: utf-8 -*-
"""
Map tool for placing military symbols on the canvas.

Activated when the user clicks **"Place on Map"** in the catalog dock.
A single left-click places the symbol at the clicked coordinate; the
tool then deactivates itself and restores the previous tool.

Emits ``symbol_placed(MilSymbol)`` on success.
"""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QPixmap
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
)
from qgis.gui import QgsMapCanvas, QgsMapTool

from ..core.models import MilSymbol
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.map_tool")


class SymbolPlacementTool(QgsMapTool):
    """Click-to-place map tool.

    Parameters
    ----------
    canvas : QgsMapCanvas
        The map canvas.
    sidc : str
        20-character SIDC for the symbol to place.
    designation : str
        Short designator text (optional).
    higher_formation : str
        Higher formation label (optional).
    """

    symbol_placed = pyqtSignal(object)  # MilSymbol

    def __init__(
        self,
        canvas: QgsMapCanvas,
        sidc: str = "10031000000000000000",
        designation: str = "",
        higher_formation: str = "",
    ):
        super().__init__(canvas)
        self._sidc = sidc
        self._designation = designation
        self._higher_formation = higher_formation
        self._previous_tool: QgsMapTool | None = None

        # Crosshair cursor
        self.setCursor(Qt.CrossCursor)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self) -> None:
        super().activate()
        # Remember the tool that was active before us
        canvas = self.canvas()
        if canvas is not None:
            current = canvas.mapTool()
            if current is not self:
                self._previous_tool = current
        LOG.debug("SymbolPlacementTool activated (SIDC=%s)", self._sidc)

    def deactivate(self) -> None:
        super().deactivate()
        LOG.debug("SymbolPlacementTool deactivated")

    # ------------------------------------------------------------------
    # Properties (writable so the catalog dock can reconfigure on the fly)
    # ------------------------------------------------------------------

    @property
    def sidc(self) -> str:
        return self._sidc

    @sidc.setter
    def sidc(self, value: str) -> None:
        self._sidc = value

    @property
    def designation(self) -> str:
        return self._designation

    @designation.setter
    def designation(self, value: str) -> None:
        self._designation = value

    @property
    def higher_formation(self) -> str:
        return self._higher_formation

    @higher_formation.setter
    def higher_formation(self, value: str) -> None:
        self._higher_formation = value

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def canvasReleaseEvent(self, event):  # noqa: N802
        """Handle left-click → place symbol."""
        if event.button() != Qt.LeftButton:
            return

        # Get the click position in map coordinates
        canvas = self.canvas()
        map_point: QgsPointXY = self.toMapCoordinates(event.pos())

        # Transform to WGS84
        map_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")

        if map_crs != wgs84:
            xform = QgsCoordinateTransform(
                map_crs, wgs84, QgsProject.instance()
            )
            map_point = xform.transform(map_point)

        # Create the MilSymbol model
        sym = MilSymbol(
            sidc=self._sidc,
            designation=self._designation,
            higher_formation=self._higher_formation,
            longitude=map_point.x(),
            latitude=map_point.y(),
        )

        LOG.info(
            "Symbol placed at (%.6f, %.6f) SIDC=%s",
            sym.longitude,
            sym.latitude,
            sym.sidc,
        )

        self.symbol_placed.emit(sym)

        # Restore previous tool
        self._restore_previous_tool()

    def canvasPressEvent(self, event):  # noqa: N802
        """Absorb press to avoid default behaviour."""
        pass

    def keyPressEvent(self, event):  # noqa: N802
        """Escape cancels placement."""
        if event.key() == Qt.Key_Escape:
            LOG.debug("Placement cancelled by Escape key")
            self._restore_previous_tool()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _restore_previous_tool(self) -> None:
        """Revert to the previously active map tool."""
        canvas = self.canvas()
        if canvas is not None and self._previous_tool is not None:
            canvas.setMapTool(self._previous_tool)
        elif canvas is not None:
            canvas.unsetMapTool(self)
