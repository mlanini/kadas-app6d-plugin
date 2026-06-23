# -*- coding: utf-8 -*-
"""
Temporal controller integration.

Listens to the QGIS Temporal Controller and delegates show/hide
filtering to ``SymbolLayerManager.apply_temporal_filter()``.

Main features
-------------
* Connects to ``QgsMapCanvas.temporalController()`` with automatic
  retries (the canvas TC may not be wired up when ``initGui`` fires).
* ``update_data_extent(symbols)`` — scans all MilSymbol instances,
  computes the overall temporal range and pushes it to the TC so the
  user can navigate the correct time window without manual setup.
* ``set_enabled(bool)`` — lets the Settings dock toggle filtering on/off
  without disconnecting from the TC.
* Emits ``filter_changed(label)`` when the visible window changes.
* Emits ``data_extent_updated(begin_iso, end_iso)`` when the TC range
  has been pushed from data (used by the Settings dock labels).
"""

from __future__ import annotations

from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal

from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.temporal")

# Retry interval when the canvas TC is not yet ready (ms)
_RETRY_MS = 2000
# Maximum number of connection retries
_MAX_RETRIES = 15
# Default frame step in hours when pushing TC range from data
_DEFAULT_STEP_HOURS = 1.0



class TemporalManager(QObject):
    """Bridges the QGIS Temporal Controller with the MilSymb layer manager.

    Parameters
    ----------
    layer_manager : SymbolLayerManager
        The managed symbol layer manager.
    parent : QObject or None
        Qt parent.
    """

    # Emitted with a human-readable range label (or "" when cleared)
    filter_changed = pyqtSignal(str)
    # Emitted after the TC range has been set from symbol data
    data_extent_updated = pyqtSignal(str, str)  # begin_iso, end_iso

    def __init__(self, *, layer_manager=None, parent: QObject | None = None):
        super().__init__(parent)
        self._layer_manager = layer_manager
        self._connected = False
        self._enabled = True          # user-level on/off switch
        self._nav_object = None
        self._retry_count = 0
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._try_connect)

    # ------------------------------------------------------------------
    # Public – enable / disable
    # ------------------------------------------------------------------

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable temporal filtering without disconnecting from TC."""
        self._enabled = enabled
        if not enabled:
            self._clear_filter()
        else:
            # Re-apply the current TC range immediately
            if self._connected and self._nav_object is not None:
                self._on_temporal_range_changed(self._nav_object.dateTimeRangeForFrameNumber(self._nav_object.currentFrameNumber()))

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------
    # Connect / disconnect
    # ------------------------------------------------------------------

    def connect_temporal_controller(self) -> None:
        """Attempt to hook into the canvas temporal controller.

        If the canvas or TC is not yet ready, schedules automatic retries
        up to :data:`_MAX_RETRIES` times with :data:`_RETRY_MS` ms intervals.
        """
        self._retry_count = 0
        self._try_connect()

    def _try_connect(self) -> None:
        if self._connected:
            return
        try:
            canvas = self._get_map_canvas()
            if canvas is None:
                self._schedule_retry("no map canvas")
                return
            controller = canvas.temporalController()
            if controller is None:
                self._schedule_retry("temporal controller not available yet")
                return
            self._nav_object = controller
            controller.updateTemporalRange.connect(self._on_temporal_range_changed)
            self._connected = True
            self._retry_timer.stop()
            LOG.info("Connected to QGIS Temporal Controller")
            # Apply the current TC range immediately (may already be active)
            self._on_temporal_range_changed(controller.dateTimeRangeForFrameNumber(controller.currentFrameNumber()))
        except Exception as exc:  # noqa: BLE001
            self._schedule_retry(str(exc))

    def _schedule_retry(self, reason: str) -> None:
        self._retry_count += 1
        if self._retry_count <= _MAX_RETRIES:
            LOG.debug(
                "TC not ready (%s) – retry %d/%d in %d ms",
                reason, self._retry_count, _MAX_RETRIES, _RETRY_MS,
            )
            self._retry_timer.start(_RETRY_MS)
        else:
            LOG.warning(
                "Giving up connecting to Temporal Controller after %d retries: %s",
                _MAX_RETRIES, reason,
            )

    def disconnect_temporal_controller(self) -> None:
        self._retry_timer.stop()
        if not self._connected or self._nav_object is None:
            return
        try:
            self._nav_object.updateTemporalRange.disconnect(
                self._on_temporal_range_changed
            )
        except (TypeError, RuntimeError):
            pass
        self._connected = False
        self._nav_object = None
        self._clear_filter()
        LOG.info("Disconnected from QGIS Temporal Controller")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Data extent → TC range
    # ------------------------------------------------------------------

    def update_data_extent(
        self,
        symbols,
        step_hours: float = _DEFAULT_STEP_HOURS,
    ) -> bool:
        """Scan *symbols*, compute overall temporal range and push it to the TC.

        Parameters
        ----------
        symbols : iterable of MilSymbol
            All symbols across all layers in the current project.
        step_hours : float
            Frame duration to set on the TC (default 1 h).

        Returns
        -------
        bool
            ``True`` when at least one dated symbol was found and the TC
            was updated; ``False`` otherwise.
        """
        if not self._connected or self._nav_object is None:
            LOG.debug("update_data_extent: TC not connected, skipping")
            return False

        begins: list[str] = []
        ends: list[str] = []
        for sym in symbols:
            t = sym.temporal
            if t and t.start:
                begins.append(t.start)
                ends.append(t.end if t.end else t.start)

        if not begins:
            LOG.debug("update_data_extent: no dated symbols found")
            return False

        begin_iso = min(begins)
        end_iso = max(ends)

        try:
            from qgis.core import QgsDateTimeRange, QgsInterval
            from qgis.PyQt.QtCore import QDateTime

            def _parse(iso: str) -> QDateTime:
                dt = QDateTime.fromString(iso, "yyyy-MM-ddTHH:mm:ss")
                if not dt.isValid():
                    dt = QDateTime.fromString(iso[:10], "yyyy-MM-dd")
                return dt

            begin_dt = _parse(begin_iso)
            end_dt = _parse(end_iso)

            if not begin_dt.isValid() or not end_dt.isValid():
                LOG.warning(
                    "update_data_extent: could not parse dates %s – %s",
                    begin_iso, end_iso,
                )
                return False

            # Pad end so the last symbol's frame is fully included
            end_dt_padded = end_dt.addSecs(int(step_hours * 3600))
            tc_range = QgsDateTimeRange(begin_dt, end_dt_padded)
            self._nav_object.setTemporalExtents(tc_range)

            # Set a sensible frame step
            self._nav_object.setFrameDuration(QgsInterval(step_hours * 3600))

            LOG.info(
                "TC range set from data: %s – %s  (step=%.1f h)",
                begin_iso, end_iso, step_hours,
            )
            self.data_extent_updated.emit(begin_iso, end_iso)
            return True
        except Exception as exc:  # noqa: BLE001
            LOG.error("Failed to set TC range from data: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Temporal range handler (slot)
    # ------------------------------------------------------------------

    def _on_temporal_range_changed(self, temporal_range) -> None:
        if temporal_range is None or temporal_range.isEmpty():
            self._clear_filter()
            return
        begin = temporal_range.begin()
        end = temporal_range.end()
        if not begin.isValid() or not end.isValid():
            self._clear_filter()
            return
        begin_iso = begin.toString("yyyy-MM-ddTHH:mm:ss")
        end_iso = end.toString("yyyy-MM-ddTHH:mm:ss")
        if self._enabled:
            self._apply_filter(begin_iso, end_iso)
        else:
            # Still report the range for the UI, but don't hide symbols
            self.filter_changed.emit(
                f"{begin_iso}  →  {end_iso}  (filtering disabled)"
            )

    # ------------------------------------------------------------------
    # Manual API
    # ------------------------------------------------------------------

    def filter_to_time(self, iso_time: str) -> None:
        """Filter symbols visible at a specific instant."""
        self._apply_filter(iso_time, iso_time)

    def show_all(self) -> None:
        """Remove temporal filter – show all symbols."""
        self._clear_filter()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_filter(self, begin_iso: str, end_iso: str) -> None:
        if self._layer_manager is not None:
            self._layer_manager.apply_temporal_filter(begin_iso, end_iso)
        label = f"{begin_iso}  →  {end_iso}"
        self.filter_changed.emit(label)
        LOG.debug("Temporal filter applied: %s", label)

    def _clear_filter(self) -> None:
        if self._layer_manager is not None:
            self._layer_manager.apply_temporal_filter(None, None)
        self.filter_changed.emit("")
        LOG.debug("Temporal filter cleared")

    @staticmethod
    def _get_map_canvas():
        try:
            from qgis.utils import iface
            if iface is not None:
                return iface.mapCanvas()
        except (ImportError, AttributeError):
            pass
        return None
