# -*- coding: utf-8 -*-
"""
Canvas interaction event filter.

Installed on the map canvas viewport during plugin init; handles:

1. **Drag and Drop** from the Symbol Catalog:
   ``DragEnter`` / ``Drop`` events carrying MIME type
   ``application/x-kadas-app6`` (JSON payload with SIDC and text
   amplifiers).  The pixel position is converted to WGS-84 and the
   ``place_cb`` callback creates the new ``MilSymbol``.

2. **Double-click** (left button) to open the Symbol Editor for the
   feature under the cursor.  Delegates to ``open_editor_cb`` with the
   map-unit ``QgsPointXY`` so the caller can do the feature search.

3. **Single left-click release** to select a symbol and populate the
   Symbol Editor.  The event is NOT consumed so KADAS can still
   process it.  The callback is deferred via QTimer(0) to avoid
   running heavy Qt operations inside the event filter.

4. **Right-click / context menu** to show the symbol context menu.

Note: symbol drag-to-move is handled natively by the KADAS
``KadasMapToolPan`` / ``KadasMapToolEditItem`` toolkit.
"""

from __future__ import annotations

import json
from typing import Callable

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QEvent, QObject, Qt, QTimer
from qgis.PyQt.QtWidgets import QApplication

from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.canvas_drop_filter")

MILSYMB_MIME_TYPE = "application/x-kadas-app6"


class CanvasInteractionFilter(QObject):
    """Event filter installed on ``QgsMapCanvas`` and its viewport.

    Parameters
    ----------
    canvas : QgsMapCanvas
    place_cb : Callable
        Called on drop with ``(sidc, designation, higher_formation,
        longitude_wgs84, latitude_wgs84)``.
    open_editor_cb : Callable
        Called on double-click with a ``QgsPointXY`` in map CRS.
        Should return True to consume the event.
    context_menu_cb : Callable or None
        Called on right-click with ``(QgsPointXY in map CRS,
        QPoint global screen position)``.  Should return ``True`` if a
        context menu was shown, ``False`` otherwise.
    symbol_click_cb : Callable or None
        Called on single left-click release with a ``QgsPointXY`` in
        map CRS.  The event is never consumed.
    symbol_hit_test_cb : Callable or None
        Called with a ``QgsPointXY`` in map CRS and should return the
        ``sym_id`` under the cursor, or ``None``.
    symbol_drag_move_cb : Callable or None
        Called while dragging with ``(sym_id, QgsPointXY map point)``.
    symbol_drag_end_cb : Callable or None
        Called when dragging finishes with ``(sym_id, QgsPointXY map point)``.
    parent : QObject or None
    """

    def __init__(
        self,
        canvas: QgsMapCanvas,
        place_cb: Callable,
        open_editor_cb: Callable,
        context_menu_cb: Callable | None = None,
        symbol_click_cb: Callable | None = None,
        symbol_hit_test_cb: Callable | None = None,
        symbol_drag_move_cb: Callable | None = None,
        symbol_drag_end_cb: Callable | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._place_cb = place_cb
        self._open_editor_cb = open_editor_cb
        self._context_menu_cb = context_menu_cb
        self._symbol_click_cb = symbol_click_cb
        self._symbol_hit_test_cb = symbol_hit_test_cb
        self._symbol_drag_move_cb = symbol_drag_move_cb
        self._symbol_drag_end_cb = symbol_drag_end_cb
        # Re-entrancy guards (filter is installed on both canvas + viewport)
        self._context_menu_active = False
        self._editor_cb_active = False
        self._click_cb_active = False
        self._drag_candidate_sym_id: str | None = None
        self._drag_start_pos = None
        self._dragging_sym_id: str | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _vp_coords_to_map(self, ev) -> QgsPointXY:
        """Convert a mouse event to map-CRS QgsPointXY via globalPos."""
        vp = self._canvas.viewport()
        if hasattr(ev, 'globalPos'):
            vp_pos = vp.mapFromGlobal(ev.globalPos())
        else:
            vp_pos = ev.pos()
        pt = self._canvas.getCoordinateTransform().toMapCoordinates(
            vp_pos.x(), vp_pos.y()
        )
        return QgsPointXY(pt)

    # ------------------------------------------------------------------
    # Event filter – every event type is an independent `if` block
    # ------------------------------------------------------------------

    def eventFilter(self, obj: QObject, ev: QEvent) -> bool:  # noqa: N802
        evt_type = ev.type()

        # ---- Drag enter --------------------------------------------------
        if evt_type == QEvent.DragEnter:
            if ev.mimeData().hasFormat(MILSYMB_MIME_TYPE):
                ev.acceptProposedAction()
                return True
            return False

        # ---- Drop --------------------------------------------------------
        if evt_type == QEvent.Drop:
            if ev.mimeData().hasFormat(MILSYMB_MIME_TYPE):
                raw = bytes(ev.mimeData().data(MILSYMB_MIME_TYPE)).decode("utf-8")
                try:
                    payload = json.loads(raw)
                except Exception as exc:
                    LOG.warning("Failed to decode drop payload: %s", exc)
                    return False

                if hasattr(ev, "position"):
                    pos = ev.position().toPoint()
                else:
                    pos = ev.pos()
                map_pt = self._canvas.getCoordinateTransform().toMapCoordinates(
                    pos.x(), pos.y()
                )

                map_crs = self._canvas.mapSettings().destinationCrs()
                wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
                if map_crs != wgs84:
                    xform = QgsCoordinateTransform(
                        map_crs, wgs84, QgsProject.instance()
                    )
                    map_pt = xform.transform(QgsPointXY(map_pt))

                self._place_cb(
                    payload.get("sidc", "10031000000000000000"),
                    payload.get("designation", ""),
                    payload.get("higher_formation", ""),
                    float(map_pt.x()),
                    float(map_pt.y()),
                )
                ev.acceptProposedAction()
                LOG.info(
                    "Symbol dropped at (%.6f, %.6f) SIDC=%s",
                    map_pt.x(), map_pt.y(),
                    payload.get("sidc", "?")[:10],
                )
                return True
            return False

        # ---- Double-click (left) -> open editor --------------------------
        if evt_type == QEvent.MouseButtonDblClick:
            self._drag_candidate_sym_id = None
            if ev.button() == Qt.LeftButton and not self._editor_cb_active:
                map_pt = self._vp_coords_to_map(ev)
                self._editor_cb_active = True
                try:
                    consumed = self._open_editor_cb(map_pt)
                finally:
                    self._editor_cb_active = False
                return bool(consumed)
            return False

        # ---- Left press -> detect potential drag on symbol --------------
        if evt_type == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
            self._drag_candidate_sym_id = None
            self._dragging_sym_id = None
            if self._symbol_hit_test_cb is not None:
                map_pt = self._vp_coords_to_map(ev)
                sym_id = self._symbol_hit_test_cb(map_pt)
                if sym_id is not None:
                    self._drag_candidate_sym_id = sym_id
                    self._drag_start_pos = ev.pos()
                    return True
            return False

        # ---- Mouse move -> start / continue drag ------------------------
        if evt_type == QEvent.MouseMove:
            if self._drag_candidate_sym_id is None:
                return False

            if self._drag_start_pos is None:
                return False

            pos = ev.pos()
            moved = (pos - self._drag_start_pos).manhattanLength()
            if self._dragging_sym_id is None:
                if moved < QApplication.startDragDistance():
                    return True
                self._dragging_sym_id = self._drag_candidate_sym_id

            if self._dragging_sym_id is not None and self._symbol_drag_move_cb is not None:
                map_pt = self._vp_coords_to_map(ev)
                self._symbol_drag_move_cb(self._dragging_sym_id, map_pt)
                return True
            return True

        # ---- Left release -> finalize click or drag ---------------------
        if evt_type == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
            if self._drag_candidate_sym_id is not None:
                map_pt = self._vp_coords_to_map(ev)
                if self._dragging_sym_id is not None:
                    if self._symbol_drag_end_cb is not None:
                        self._symbol_drag_end_cb(self._dragging_sym_id, map_pt)
                else:
                    if self._symbol_click_cb is not None and not self._click_cb_active:
                        self._click_cb_active = True
                        QTimer.singleShot(
                            0, lambda pt=map_pt: self._fire_click_cb(pt)
                        )
                self._drag_candidate_sym_id = None
                self._drag_start_pos = None
                self._dragging_sym_id = None
                return True

            if self._symbol_click_cb is not None and not self._click_cb_active and not self._editor_cb_active:
                map_pt = self._vp_coords_to_map(ev)
                self._click_cb_active = True
                QTimer.singleShot(0, lambda pt=map_pt: self._fire_click_cb(pt))
            return False

        # ---- Single left-click release -> open editor if symbol hit ------
        # Independent block. Event is NEVER consumed.
        # kept for backward-compatibility in case event is not captured earlier.

        # ---- Right-click release -> symbol context menu ------------------
        # Independent block – must NOT be elif of the left-click block.
        if evt_type == QEvent.MouseButtonRelease and ev.button() == Qt.RightButton:
            if self._context_menu_cb is not None and not self._context_menu_active:
                pos = ev.pos()
                map_pt = QgsPointXY(
                    self._canvas.getCoordinateTransform().toMapCoordinates(
                        pos.x(), pos.y()
                    )
                )
                global_pos = (
                    ev.globalPos() if hasattr(ev, 'globalPos')
                    else self._canvas.viewport().mapToGlobal(pos)
                )
                self._context_menu_active = True
                try:
                    consumed = self._context_menu_cb(map_pt, global_pos)
                finally:
                    self._context_menu_active = False
                if consumed:
                    return True
            return False

        # ---- QEvent.ContextMenu as fallback (standard Qt path) -----------
        if evt_type == QEvent.ContextMenu and self._context_menu_cb is not None:
            if not self._context_menu_active:
                pos = ev.pos()
                map_pt = QgsPointXY(
                    self._canvas.getCoordinateTransform().toMapCoordinates(
                        pos.x(), pos.y()
                    )
                )
                self._context_menu_active = True
                try:
                    consumed = self._context_menu_cb(map_pt, ev.globalPos())
                finally:
                    self._context_menu_active = False
                if consumed:
                    return True

        return False

    def _fire_click_cb(self, map_pt: QgsPointXY) -> None:
        """Deferred single-click callback – runs outside the event filter."""
        try:
            self._symbol_click_cb(map_pt)
        finally:
            self._click_cb_active = False