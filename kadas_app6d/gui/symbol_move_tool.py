# -*- coding: utf-8 -*-
"""
One-shot map tool for repositioning a military symbol.

Activated from the canvas **right-click → "Move Symbol"** context-menu
action for a specific symbol already on the map.

Behaviour
---------
* Cursor changes to a crosshair to indicate "click to place here".
* A single **left-click** on the map moves the symbol to the clicked
  WGS-84 coordinate, commits the change via ``SymbolLayerManager``,
  emits ``symbol_moved(sym_id)`` and restores the previous map tool.
* **Escape** cancels the operation, restoring the original position
  (using an in-memory backup taken at activation time).
"""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
)
from qgis.gui import QgsMapCanvas, QgsMapTool

from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.symbol_move_tool")


class SymbolMoveTool(QgsMapTool):
    """Click-to-reposition tool for a single military symbol.

    Parameters
    ----------
    canvas:
        The map canvas.
    layer_manager:
        ``SymbolLayerManager`` instance used to read and write the symbol.
    sym_id:
        UUID of the :class:`~kadas_milsymb.core.models.MilSymbol` to move.
    """

    #: Emitted with the symbol id after a successful move.
    symbol_moved = pyqtSignal(str)
    #: Emitted when the move tool ends: (sym_id, moved)
    finished = pyqtSignal(str, bool)

    def __init__(
        self,
        canvas: QgsMapCanvas,
        layer_manager,
        sym_id: str,
    ) -> None:
        super().__init__(canvas)
        self._layer_manager = layer_manager
        self._sym_id = sym_id
        self._original_lon: float | None = None
        self._original_lat: float | None = None
        self._previous_tool: QgsMapTool | None = None

        # Crosshair cursor signals "click to place"
        self.setCursor(Qt.CrossCursor)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self) -> None:
        super().activate()
        canvas = self.canvas()
        if canvas is not None:
            current = canvas.mapTool()
            if current is not self:
                self._previous_tool = current

        # Back up original position so Escape can restore it
        sym = self._layer_manager.get_symbol(self._sym_id)
        if sym is not None:
            self._original_lon = sym.longitude
            self._original_lat = sym.latitude

        LOG.debug("SymbolMoveTool activated for sym_id=%s", self._sym_id[:8])

    def deactivate(self) -> None:
        super().deactivate()
        LOG.debug("SymbolMoveTool deactivated")

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def canvasReleaseEvent(self, event) -> None:  # noqa: N802
        """Left-click → move symbol to clicked position."""
        if event.button() != Qt.LeftButton:
            return

        canvas = self.canvas()
        map_point: QgsPointXY = self.toMapCoordinates(event.pos())

        # Convert map CRS → WGS-84
        map_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        if map_crs != wgs84:
            xform = QgsCoordinateTransform(
                map_crs, wgs84, QgsProject.instance()
            )
            map_point = xform.transform(map_point)

        sym = self._layer_manager.get_symbol(self._sym_id)
        if sym is not None:
            sym.longitude = map_point.x()
            sym.latitude = map_point.y()
            self._layer_manager.update_symbol(sym)
            self.symbol_moved.emit(self._sym_id)
            self.finished.emit(self._sym_id, True)
            LOG.info(
                "Symbol %s moved to (%.6f, %.6f)",
                self._sym_id[:8], map_point.x(), map_point.y(),
            )

        self._restore_previous_tool()

    def canvasPressEvent(self, event) -> None:  # noqa: N802
        """Absorb press to prevent default canvas behaviour."""

    def keyPressEvent(self, event) -> None:  # noqa: N802
        """Escape cancels the move and restores the original position."""
        if event.key() == Qt.Key_Escape:
            if (
                self._original_lon is not None
                and self._original_lat is not None
            ):
                sym = self._layer_manager.get_symbol(self._sym_id)
                if sym is not None:
                    sym.longitude = self._original_lon
                    sym.latitude = self._original_lat
                    self._layer_manager.update_symbol(sym)
                    LOG.debug(
                        "Symbol move cancelled – restored original position"
                    )
            self.finished.emit(self._sym_id, False)
            self._restore_previous_tool()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _restore_previous_tool(self) -> None:
        """Return to the map tool that was active before this one."""
        canvas = self.canvas()
        if canvas is not None and self._previous_tool is not None:
            canvas.setMapTool(self._previous_tool)
        elif canvas is not None:
            canvas.unsetMapTool(self)
