# -*- coding: utf-8 -*-
"""
Main plugin class for KADAS APP-6(D).

Provides:
- Military symbol catalog browser (dock)
- ORBAT Manager (dock)
- Temporal integration via QGIS Temporal Controller
- Built-in symbol rendering server (SVG/PNG)
"""

import os
import configparser
import subprocess  # noqa: B404
import sys

from qgis.PyQt.QtCore import Qt, QCoreApplication, QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QInputDialog, QMenu, QMessageBox

from kadas.kadasgui import KadasPluginInterface

from .core.models import MilSymbProject
from .core.utils import plugin_path, milsymb_data_dir
from .logger import get_logger

LOG = get_logger()


def _load_plugin_metadata() -> dict[str, str]:
    metadata_path = os.path.join(os.path.dirname(__file__), "metadata.txt")
    parser = configparser.ConfigParser()
    parser.read(metadata_path, encoding="utf-8")
    if not parser.has_section("general"):
        return {}
    return {
        key: value.strip() for key, value in parser.items("general")
    }


_PLUGIN_METADATA = _load_plugin_metadata()
_PLUGIN_NAME = _PLUGIN_METADATA.get("name", "KADAS APP-6(D)")
_PLUGIN_VERSION = _PLUGIN_METADATA.get("version", "0.1.0")
_PLUGIN_AUTHOR = _PLUGIN_METADATA.get("author", "")
_PLUGIN_URL = (
    _PLUGIN_METADATA.get("repository")
    or _PLUGIN_METADATA.get("homepage", "")
)


class KadasApp6Plugin:
    """KADAS APP-6(D) – military symbology plugin.

    Instantiated by ``classFactory`` in ``__init__.py``.
    KADAS calls ``initGui()`` once the plugin is enabled, and ``unload()``
    when it is disabled or the application is closed.

    Ribbon actions are registered under a custom KADAS APP-6(D) ribbon tab.
    """

    def __init__(self, iface):
        self.iface: KadasPluginInterface = KadasPluginInterface.cast(iface)

        # Project data model – starts empty; user is prompted at startup
        self._project_data = MilSymbProject(layers=[])

        # Symbol layer manager
        self._layer_manager = None

        # Dock widget instances (created lazily)
        self._catalog_dock = None
        self._orbat_dock = None
        self._settings_dock = None

        # Floating symbol editor dialog
        self._editor_dock = None

        # Canvas interaction filter (drag&drop + double-click)
        self._canvas_filter = None
        # Layer manager dock
        self._layer_manager_dock = None

        # Symbol rendering server
        self._symbol_server = None

        # Renderer metadata (for QGIS registry) - no longer used with KadasItemLayer
        self._renderer_metadata = None

        # Temporal manager
        self._temporal_manager = None

        # Project I/O (automatic save/load)
        self._project_io = None

        # Actions list for cleanup
        self._actions: list[QAction] = []
        self._menu: QMenu | None = None

        LOG.info("%s plugin instantiated (v%s)", _PLUGIN_NAME, _PLUGIN_VERSION)

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------

    def initGui(self) -> None:  # noqa: N802
        """Create and register ribbon buttons under the KADAS APP-6(D) ribbon tab."""
        tools_icon = plugin_path("icons", "tools.svg")

        # ---- Symbol Catalog action (checkable toggle) ----
        self._catalog_action = self._make_action(
            icon_path=plugin_path("icons", "milsymb.svg"),
            text=self.tr("Symbol Catalog"),
            tooltip=self.tr("Open / close the military symbol catalog"),
            checkable=True,
            callback=self._toggle_catalog_dock,
        )

        # ---- Symbol Editor action (standalone, non-checkable) ----
        self._editor_action = self._make_action(
            icon_path=plugin_path("icons", "symbol_editor.svg"),
            text=self.tr("Symbol Editor"),
            tooltip=self.tr("Open the Symbol Editor to create or inspect a symbol"),
            checkable=True,
            callback=self._toggle_editor_dock,
        )

        # ---- ORBAT Manager action (checkable toggle) ----
        self._orbat_action = self._make_action(
            icon_path=plugin_path("icons", "orbat_editor.svg"),
            text=self.tr("ORBAT Manager"),
            tooltip=self.tr("Open / close the ORBAT manager"),
            checkable=True,
            callback=self._toggle_orbat_dock,
        )

        # ---- Layer Manager action (checkable toggle) ----
        self._layer_mgr_action = self._make_action(
            icon_path=plugin_path("icons", "map.svg"),
            text=self.tr("Layer Manager"),
            tooltip=self.tr("Manage symbol layers and export"),
            checkable=True,
            callback=self._toggle_layer_manager_dock,
        )

        # ---- Settings action (checkable toggle) ----
        self._settings_action = self._make_action(
            icon_path=plugin_path("icons", "settings.svg"),
            text=self.tr("Settings"),
            tooltip=self.tr("Open / close plugin settings"),
            checkable=True,
            callback=self._toggle_settings_dock,
        )

        # ---- About action ----
        self._about_action = self._make_action(
            icon_path=plugin_path("icons", "about.svg"),
            text=self.tr("About…"),
            tooltip=self.tr("Plugin information"),
            checkable=False,
            callback=self.show_about,
        )

        # ---- Log file action ----
        self._log_action = self._make_action(
            icon_path=plugin_path("icons", "log.svg"),
            text=self.tr("Open log file"),
            tooltip=self.tr("Open the plugin log file"),
            checkable=False,
            callback=self.open_log_file,
        )

        # ---- Build ribbon buttons for custom KADAS APP-6(D) tab ----
        # Main dock toggles are added as individual full-width ribbon buttons
        # (same pattern as kadas_targeting) so labels are always visible.
        _TAB = "APP-6(D)"
        self.iface.addAction(
            self._catalog_action,
            self.iface.PLUGIN_MENU,
            self.iface.CUSTOM_TAB,
            _TAB,
        )
        self.iface.addAction(
            self._editor_action,
            self.iface.PLUGIN_MENU,
            self.iface.CUSTOM_TAB,
            _TAB,
        )
        self.iface.addAction(
            self._orbat_action,
            self.iface.PLUGIN_MENU,
            self.iface.CUSTOM_TAB,
            _TAB,
        )
        self.iface.addAction(
            self._layer_mgr_action,
            self.iface.PLUGIN_MENU,
            self.iface.CUSTOM_TAB,
            _TAB,
        )

        # Secondary actions grouped in a "Tools" drop-down
        self._menu = QMenu(self.tr("Tools"), self.iface.mainWindow())
        self._menu.addAction(self._settings_action)
        self._menu.addSeparator()
        self._menu.addAction(self._about_action)
        self._menu.addAction(self._log_action)

        self.iface.addActionMenu(
            self.tr("Tools"),
            QIcon(tools_icon),
            self._menu,
            self.iface.PLUGIN_MENU,
            self.iface.CUSTOM_TAB,
            _TAB,
        )

        # Start the built-in symbol rendering server
        self._start_symbol_server()

        # Initialise the symbol layer manager (KadasItemLayer-backed)
        self._init_layer_manager()

        # Trigger creation of all KadasItemLayers
        if self._layer_manager is not None:
            self._layer_manager.ensure_layers()

        # Prompt the user to create a first symbol layer (deferred so
        # that the UI is fully displayed and ProjectIO has had a chance
        # to restore a saved project before the dialog appears).
        QTimer.singleShot(800, self._prompt_initial_layer)

        # Install canvas interaction filter (drag&drop + double-click +
        # right-click context menu).  Right-click is handled inside the
        # event filter so KADAS cannot suppress our handler via its own
        # context-menu policy override.
        self._init_canvas_interactions()

        # Initialise temporal manager
        self._init_temporal_manager()

        # Initialise project I/O (auto save/load with QGIS project)
        self._init_project_io()

        LOG.debug(
            "KadasApp6Plugin.initGui() – %d actions registered",
            len(self._actions),
        )

    def unload(self) -> None:
        """Remove all UI elements and stop background services."""
        # Disconnect project I/O signals
        if self._project_io is not None:
            self._project_io.disconnect_signals()
            self._project_io = None

        # Disconnect temporal manager
        if self._temporal_manager is not None:
            self._temporal_manager.disconnect_temporal_controller()
            self._temporal_manager = None

        # Stop the symbol server
        self._stop_symbol_server()

        # Remove canvas interaction filter (drag&drop + double-click)
        if self._canvas_filter is not None:
            try:
                canvas = self.iface.mapCanvas()
                canvas.removeEventFilter(self._canvas_filter)
                canvas.viewport().removeEventFilter(self._canvas_filter)
            except Exception:
                pass
            self._canvas_filter = None

        # Close docks gracefully
        for dock in (self._catalog_dock, self._orbat_dock,
                     self._settings_dock, self._layer_manager_dock):
            if dock is not None:
                dock.close()

        # Close floating editor dialog
        if self._editor_dock is not None:
            self._editor_dock.close()
            self._editor_dock = None

        self._catalog_dock = None
        self._orbat_dock = None
        self._settings_dock = None
        self._layer_manager_dock = None
        self._layer_manager = None

        # Remove ribbon actions / menu
        _TAB = "APP-6(D)"
        for _act in (self._catalog_action, self._editor_action,
                     self._orbat_action, self._layer_mgr_action):
            try:
                self.iface.removeAction(
                    _act,
                    self.iface.PLUGIN_MENU,
                    self.iface.CUSTOM_TAB,
                    _TAB,
                )
            except Exception:
                pass
        if self._menu is not None:
            try:
                self.iface.removeActionMenu(
                    self._menu,
                    self.iface.PLUGIN_MENU,
                    self.iface.CUSTOM_TAB,
                    _TAB,
                )
            except Exception:
                pass
            self._menu = None

        self._actions.clear()
        LOG.info("KADAS APP-6(D) Plugin unloaded")

    # ------------------------------------------------------------------
    # Layer manager
    # ------------------------------------------------------------------

    def _init_layer_manager(self) -> None:
        """Create the SymbolLayerManager (backed by KadasItemLayer)."""
        try:
            from .gui.symbol_layer import SymbolLayerManager

            self._layer_manager = SymbolLayerManager(
                project_data=self._project_data,
                parent=self.iface.mainWindow(),
            )
            LOG.info("SymbolLayerManager initialised")
        except Exception as exc:
            LOG.error("Failed to initialise layer manager: %s", exc)

    def _prompt_initial_layer(self) -> None:
        """Ask the user if they want to create an initial symbol layer.

        Skipped automatically when a project has already been loaded
        (layers list is non-empty at the time the timer fires).
        """
        if self._project_data.layers:
            # A project was loaded (or user already added layers) – nothing to do
            return

        parent = self.iface.mainWindow()
        reply = QMessageBox.question(
            parent,
            self.tr("Create Symbol Layer"),
            self.tr(
                "No symbol layers are present in this project.\n"
                "Do you want to create a new symbol layer now?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            name, ok = QInputDialog.getText(
                parent,
                self.tr("New Symbol Layer"),
                self.tr("Layer name:"),
                text=self.tr("Layer 1"),
            )
            if ok and name.strip():
                if self._layer_manager is not None:
                    sl = self._layer_manager.add_layer(name.strip())
                    self._layer_manager.set_active_layer(sl.id)
                else:
                    self._project_data.add_layer(name.strip())
        else:
            QMessageBox.information(
                parent,
                self.tr("Symbol Layers"),
                self.tr(
                    "You can create symbol layers at any time via the "
                    "\u201cLayer Manager\u201d panel."
                ),
            )

    # ------------------------------------------------------------------
    # Right-click → open Symbol Editor
    # ------------------------------------------------------------------

    def _on_canvas_context_menu_at_point(
        self, map_point, global_pos
    ) -> bool:
        """Called by CanvasInteractionFilter on right-click.

        Searches for a MilSymb feature near *map_point* and shows the
        symbol context menu when found.  Returns ``True`` if a symbol
        was found (event consumed), ``False`` otherwise.
        """
        if self._layer_manager is None:
            return False
        canvas = self.iface.mapCanvas()
        sym_id = self._layer_manager.find_symbol_at_point(
            map_point, canvas.mapSettings()
        )
        if sym_id is not None:
            sym = self._layer_manager.get_symbol(sym_id)
            if sym is not None:
                self._show_symbol_context_menu(sym, global_pos)
                return True
        return False

    def _show_symbol_context_menu(self, sym, global_pos) -> None:
        """Show a context menu for a symbol on the map canvas."""
        from qgis.PyQt.QtWidgets import QApplication, QMenu, QAction as _QAction

        menu = QMenu(self.iface.mainWindow())

        # Header-like disabled label showing symbol designation / SIDC
        label = sym.designation or sym.sidc[:10]
        act_label = _QAction(f"Symbol: {label}", menu)
        act_label.setEnabled(False)
        menu.addAction(act_label)

        # Temporal validity line (when set)
        if sym.temporal and sym.temporal.start:
            t_text = f"  Valid: {sym.temporal.start}"
            if sym.temporal.end:
                t_text += f" → {sym.temporal.end}"
            act_temporal = _QAction(t_text, menu)
            act_temporal.setEnabled(False)
            menu.addAction(act_temporal)

        menu.addSeparator()

        act_edit = _QAction("Open in Editor…", menu)
        act_edit.triggered.connect(lambda: self._open_editor_for(sym))
        menu.addAction(act_edit)

        act_move = _QAction("Move Symbol", menu)
        act_move.triggered.connect(lambda: self._on_move_symbol(sym))
        menu.addAction(act_move)

        act_zoom = _QAction("Zoom to Symbol", menu)
        act_zoom.triggered.connect(lambda: self._zoom_to_symbol(sym))
        menu.addAction(act_zoom)

        menu.addSeparator()

        act_copy_sidc = _QAction("Copy SIDC", menu)
        act_copy_sidc.triggered.connect(
            lambda: QApplication.clipboard().setText(sym.sidc)
        )
        menu.addAction(act_copy_sidc)

        act_copy_coords = _QAction("Copy Coordinates", menu)
        act_copy_coords.triggered.connect(
            lambda: QApplication.clipboard().setText(
                f"{sym.latitude:.6f}, {sym.longitude:.6f}"
            )
        )
        menu.addAction(act_copy_coords)

        menu.addSeparator()

        act_delete = _QAction("Delete Symbol", menu)
        act_delete.triggered.connect(lambda: self._delete_symbol_from_canvas(sym))
        menu.addAction(act_delete)

        menu.exec_(global_pos)

    def _zoom_to_symbol(self, sym) -> None:
        """Pan and zoom the map canvas to centre on *sym*."""
        try:
            from qgis.core import (
                QgsCoordinateReferenceSystem,
                QgsCoordinateTransform,
                QgsPointXY,
                QgsProject,
            )
            canvas = self.iface.mapCanvas()
            wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
            map_crs = canvas.mapSettings().destinationCrs()
            pt = QgsPointXY(sym.longitude, sym.latitude)
            if map_crs != wgs84:
                xform = QgsCoordinateTransform(wgs84, map_crs, QgsProject.instance())
                pt = xform.transform(pt)
            canvas.setCenter(pt)
            canvas.refresh()
            LOG.info("Zoomed to symbol %s at (%.6f, %.6f)", sym.id[:8], sym.longitude, sym.latitude)
        except Exception as exc:
            LOG.warning("Zoom to symbol failed: %s", exc)

    def _delete_symbol_from_canvas(self, sym) -> None:
        """Delete *sym* directly from canvas context menu (with confirmation)."""
        from qgis.PyQt.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self.iface.mainWindow(),
            "Delete Symbol",
            f"Delete symbol '{sym.designation or sym.sidc}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes and self._layer_manager is not None:
            self._layer_manager.remove_symbol(sym.id)
            LOG.info("Symbol %s deleted from canvas context menu", sym.id[:8])

    def _on_show_text_modifiers_changed(self, show: bool) -> None:
        if self._editor_dock is not None:
            self._editor_dock.set_show_text_modifiers(show)

    def _show_editor_dock(self) -> None:
        """Ensure the editor dock is visible, docked on the right and raised."""
        if self._editor_dock is None:
            return
        # Force back into the right dock area in case it was undocked / floating.
        if self._editor_dock.isFloating():
            self._editor_dock.setFloating(False)
        self._editor_dock.show()
        self._editor_dock.raise_()
        self._editor_dock.activateWindow()

    def _toggle_editor_dock(self, checked: bool) -> None:
        """Show or hide the Symbol Editor dock."""
        if self._editor_dock is None:
            self._ensure_editor_dock()
            # Newly created dock: put it in 'new symbol' mode
            self._editor_dock.reset_to_new_symbol_mode()
        if checked:
            self._show_editor_dock()
        else:
            self._editor_dock.hide()

    def _on_orbat_edit_unit_requested(self, unit) -> None:
        """Open the Symbol Editor dock to edit an ORBAT unit."""
        self._ensure_editor_dock()

        # If the unit is already placed on the map, edit the real MilSymbol so
        # the user can also change position-dependent fields and text modifiers.
        if unit.map_symbol_id and self._layer_manager is not None:
            sym = self._layer_manager.get_symbol(unit.map_symbol_id)
            if sym is not None:
                self._editor_dock.edit_symbol(sym)
                # Re-attach the ORBAT unit so Apply updates both layer and tree
                self._editor_dock._orbat_unit = unit
                self._show_editor_dock()
                self._editor_action.setChecked(True)
                return

        # No map symbol yet – edit only SIDC / name / temporal through ORBAT proxy
        self._editor_dock.edit_orbat_unit(unit)
        self._show_editor_dock()
        self._editor_action.setChecked(True)

    def _on_orbat_unit_updated(self, unit) -> None:
        """Sync the ORBAT tree after the Symbol Editor applied changes to a unit."""
        if self._orbat_dock is not None:
            self._orbat_dock.refresh_after_edit(unit)

    def _open_editor_for(self, sym) -> None:
        """Open the Symbol Editor dock and load *sym* for editing."""
        self._ensure_editor_dock()
        self._editor_dock.edit_symbol(sym)
        self._show_editor_dock()
        self._editor_action.setChecked(True)

    def _on_catalog_edit_requested(self, payload) -> None:
        """Open the editor dock pre-populated with a catalog entry.

        *payload* is a dict with keys ``entry``, ``identity``, ``echelon``.
        """
        self._ensure_editor_dock()
        entry = payload["entry"]
        identity = payload.get("identity")
        echelon = payload.get("echelon")
        self._editor_dock.load_from_catalog(entry, identity=identity, echelon=echelon)
        self._show_editor_dock()
        self._editor_action.setChecked(True)

    def _ensure_editor_dock(self) -> None:
        """Create the floating editor dock if it does not exist yet."""
        import sip
        if self._editor_dock is not None and not sip.isdeleted(self._editor_dock):
            return
        from .gui.symbol_editor_dock import SymbolEditorDockWidget

        self._editor_dock = SymbolEditorDockWidget(
            iface=self.iface,
            action=self._editor_action,
            parent=self.iface.mainWindow(),
        )
        self._editor_dock.set_layer_manager(self._layer_manager)
        if self._settings_dock is not None:
            self._editor_dock.set_show_text_modifiers(
                self._settings_dock.show_text_modifiers
            )
        self._editor_dock.setObjectName("KadasApp6SymbolEditorDock")
        self._editor_dock.orbat_unit_updated.connect(self._on_orbat_unit_updated)
        # Refresh TC extent whenever the editor places or updates a symbol
        self._editor_dock.symbol_updated.connect(
            lambda _sid: self._refresh_temporal_extent()
        )
        self._editor_dock.symbol_placed.connect(
            lambda _sym: self._refresh_temporal_extent()
        )
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self._editor_dock)
        self._tabify_dock(self._editor_dock)

    # ------------------------------------------------------------------
    # Canvas interaction filter (drag&drop + double-click)
    # ------------------------------------------------------------------

    def _init_canvas_interactions(self) -> None:
        """Install the canvas event filter for drag&drop and double-click."""
        try:
            from .gui.canvas_drop_filter import CanvasInteractionFilter

            canvas = self.iface.mapCanvas()
            self._canvas_filter = CanvasInteractionFilter(
                canvas=canvas,
                place_cb=self._on_drop_place_symbol,
                open_editor_cb=self._open_editor_at_point,
                context_menu_cb=self._on_canvas_context_menu_at_point,
                symbol_click_cb=self._on_canvas_symbol_click,
                parent=canvas,
            )
            # Install on both the canvas widget and its viewport so that
            # right-click events intercepted by KADAS at the QgsMapCanvas
            # level (before propagation to the viewport) are also caught.
            canvas.installEventFilter(self._canvas_filter)
            canvas.viewport().installEventFilter(self._canvas_filter)
            canvas.setAcceptDrops(True)
            LOG.info("Canvas interaction filter installed")
        except Exception as exc:
            LOG.error("Failed to install canvas interaction filter: %s", exc)

    def _on_drop_place_symbol(
        self,
        sidc: str,
        designation: str,
        higher_formation: str,
        longitude: float,
        latitude: float,
    ) -> None:
        """Called by CanvasInteractionFilter when a symbol is dropped on the canvas."""
        if self._layer_manager is None:
            return
        if not self._layer_manager.symbol_layers():
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("No Symbol Layer"),
                self.tr(
                    "Please create a symbol layer first via the Layer Manager "
                    "before placing a symbol on the map."
                ),
            )
            return
        from .core.models import MilSymbol

        sym = MilSymbol(
            sidc=sidc,
            designation=designation,
            higher_formation=higher_formation,
            longitude=longitude,
            latitude=latitude,
        )
        self._layer_manager.add_symbol(sym)
        LOG.info("Symbol added via drag&drop: %s SIDC=%s", sym.id[:8], sidc[:10])
        # Refresh TC extent so the new symbol's date is included if set
        if sym.temporal and sym.temporal.start:
            self._refresh_temporal_extent()

    def _on_canvas_symbol_click(self, map_point) -> None:
        """Called by CanvasInteractionFilter on single left-click release.

        If a symbol is found at *map_point*, opens the Symbol Editor and
        loads the symbol for editing (identical to double-click / context-menu
        Edit, but triggered by single click).
        The event is NOT consumed – KADAS continues its default handling.
        """
        if self._layer_manager is None:
            return
        canvas = self.iface.mapCanvas()
        sym_id = self._layer_manager.find_symbol_at_point(
            map_point, canvas.mapSettings()
        )
        if sym_id is not None:
            sym = self._layer_manager.get_symbol(sym_id)
            if sym is not None:
                self._open_editor_for(sym)

    def _open_editor_at_point(self, map_point) -> bool:
        """Called by CanvasInteractionFilter on double-click.

        Searches for a MilSymb feature near *map_point* (in the current
        map CRS) and opens the editor for it if found.  Returns ``True``
        when a symbol was found and the editor was opened (so the event
        can be consumed), ``False`` otherwise.
        """
        if self._layer_manager is None:
            return False
        canvas = self.iface.mapCanvas()
        sym_id = self._layer_manager.find_symbol_at_point(
            map_point, canvas.mapSettings()
        )
        if sym_id is not None:
            sym = self._layer_manager.get_symbol(sym_id)
            if sym is not None:
                self._open_editor_for(sym)
                return True
        return False

    def _on_move_symbol(self, sym) -> None:
        """Activate SymbolMoveTool for *sym* (click-to-reposition)."""
        if self._layer_manager is None:
            return
        from .gui.symbol_move_tool import SymbolMoveTool
        canvas = self.iface.mapCanvas()
        tool = SymbolMoveTool(canvas, self._layer_manager, sym.id)
        tool.symbol_moved.connect(self._on_symbol_moved_by_tool)
        canvas.setMapTool(tool)
        LOG.info("SymbolMoveTool activated for sym_id=%s", sym.id[:8])

    def _on_symbol_moved_by_tool(self, sym_id: str) -> None:
        """Refresh editor if the moved symbol is currently open."""
        if self._symbol_editor_dock is not None:
            sym = self._layer_manager.get_symbol(sym_id) if self._layer_manager else None
            if sym is not None:
                self._symbol_editor_dock.sync_symbol(sym)

    # ------------------------------------------------------------------
    # Temporal manager
    # ------------------------------------------------------------------

    def _init_temporal_manager(self) -> None:
        """Create the TemporalManager and hook into QGIS Temporal Controller."""
        try:
            from .gui.temporal import TemporalManager

            if self._layer_manager is None:
                LOG.warning("Cannot init TemporalManager – layer manager not ready")
                return
            self._temporal_manager = TemporalManager(
                layer_manager=self._layer_manager,
                parent=self.iface.mainWindow(),
            )
            self._temporal_manager.connect_temporal_controller()
            LOG.info("TemporalManager initialised")
        except Exception as exc:
            LOG.error("Failed to initialise TemporalManager: %s", exc)

    # ------------------------------------------------------------------
    # Project I/O
    # ------------------------------------------------------------------

    def _init_project_io(self) -> None:
        """Set up automatic project save/load tied to QGIS project signals."""
        try:
            from .gui.project_io import ProjectIO

            self._project_io = ProjectIO(
                project_data=self._project_data,
                parent=self.iface.mainWindow(),
            )
            self._project_io.project_loaded.connect(self._on_project_loaded)
            self._project_io.connect_signals()
            LOG.info("ProjectIO initialised")
        except Exception as exc:
            LOG.error("Failed to initialise ProjectIO: %s", exc)

    def _on_project_loaded(self, project_data) -> None:
        """Refresh layer and docks after MilSymb data is loaded from disk."""
        LOG.info("Refreshing plugin after project load (%d symbols, %d orbats)",
                 len(project_data.symbols), len(project_data.orbats))

        # Replace the plugin-level reference with the received object
        self._project_data = project_data

        # Keep ProjectIO in sync so future saves use the new data
        if self._project_io is not None:
            self._project_io.set_project_data(project_data)

        # Rebuild map layer features from the loaded symbols
        if self._layer_manager is not None:
            self._layer_manager.rebuild_from_project(project_data)

        # Refresh open docks  (set_project_data already rebuilds the
        # combo / tree in the ORBAT dock)
        if self._catalog_dock is not None:
            self._catalog_dock.set_project_data(project_data)
        if self._orbat_dock is not None:
            self._orbat_dock.set_project_data(project_data)
        if self._settings_dock is not None:
            self._settings_dock.set_project_data(project_data)
        if self._layer_manager_dock is not None:
            self._layer_manager_dock.set_project_data(project_data)
        # Close editor dialog (loaded project may not have the same symbols)
        if self._editor_dock is not None:
            self._editor_dock.close()

        # Update Temporal Controller range from new data
        self._refresh_temporal_extent()

        # If the project was cleared (no layers), re-prompt the user
        # so they can set a proper layer name instead of inheriting "Default".
        if not project_data.layers:
            QTimer.singleShot(300, self._prompt_initial_layer)

    # ------------------------------------------------------------------
    # Temporal helpers
    # ------------------------------------------------------------------

    def _refresh_temporal_extent(self) -> None:
        """Push the overall symbol temporal range to the TC (no-op when no
        dated symbols or when TC is not connected)."""
        if self._temporal_manager is None:
            return
        all_syms = list(self._project_data.symbols)
        step = 1.0
        if self._settings_dock is not None:
            try:
                step = self._settings_dock._temporal_step_spin.value()
            except AttributeError:
                pass
        self._temporal_manager.update_data_extent(all_syms, step_hours=step)

    def _on_temporal_filtering_toggled(self, enabled: bool) -> None:
        """Called when the user toggles the 'Enable temporal filtering' checkbox."""
        if self._temporal_manager is not None:
            self._temporal_manager.set_enabled(enabled)
        LOG.info("Temporal filtering %s", "enabled" if enabled else "disabled")

    def _on_temporal_fit_to_data_requested(self, step_hours: float) -> None:
        """Called when the user presses 'Fit TC range to data'."""
        if self._temporal_manager is None:
            return
        all_syms = list(self._project_data.symbols)
        ok = self._temporal_manager.update_data_extent(all_syms, step_hours=step_hours)
        if not ok:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.information(
                self.iface.mainWindow(),
                "Temporal Controller",
                "No symbols with temporal attributes found in the current project.",
            )

    # ------------------------------------------------------------------
    # Symbol rendering server
    # ------------------------------------------------------------------

    def _start_symbol_server(self) -> None:
        """Start the built-in HTTP symbol server on a free port."""
        try:
            from .server.symbol_server import SymbolServer

            self._symbol_server = SymbolServer()
            self._symbol_server.start()
            LOG.info(
                "Symbol server started on port %d",
                self._symbol_server.port,
            )
        except Exception as exc:
            LOG.error("Failed to start symbol server: %s", exc)

    def _stop_symbol_server(self) -> None:
        """Stop the built-in symbol server."""
        if self._symbol_server is not None:
            self._symbol_server.stop()
            self._symbol_server = None
            LOG.info("Symbol server stopped")

    # ------------------------------------------------------------------
    # Dock toggling
    # ------------------------------------------------------------------

    def _tabify_dock(self, new_dock) -> None:
        """Tabify *new_dock* with the first existing plugin dock so all
        panels share the right dock area as navigable tabs."""
        from qgis.PyQt.QtWidgets import QMainWindow, QTabWidget
        mw = self.iface.mainWindow()
        # Ensure Qt is allowed to merge docks into a tabbed group and
        # places tab labels at the bottom (KADAS convention).
        mw.setDockOptions(
            mw.dockOptions()
            | QMainWindow.AllowTabbedDocks
            | QMainWindow.AnimatedDocks
        )
        for area in (
            Qt.RightDockWidgetArea,
            Qt.LeftDockWidgetArea,
            Qt.BottomDockWidgetArea,
            Qt.TopDockWidgetArea,
        ):
            mw.setTabPosition(area, QTabWidget.South)
        for existing in (self._catalog_dock, self._orbat_dock,
                         self._settings_dock, self._layer_manager_dock,
                         self._editor_dock):
            if existing is not None and existing is not new_dock:
                mw.tabifyDockWidget(existing, new_dock)
                new_dock.show()
                new_dock.raise_()
                return

    def _toggle_catalog_dock(self, checked: bool) -> None:
        """Show or hide the symbol catalog dock widget."""
        if self._catalog_dock is None:
            try:
                from .gui.catalog_dock import CatalogDockWidget

                self._catalog_dock = CatalogDockWidget(
                    iface=self.iface,
                    symbol_server=self._symbol_server,
                    action=self._catalog_action,
                    parent=self.iface.mainWindow(),
                )
                self._catalog_dock.set_layer_manager(self._layer_manager)
                self._catalog_dock.set_project_data(self._project_data)
                self._catalog_dock.setObjectName("KadasApp6CatalogDock")
                self._catalog_dock.edit_in_editor_requested.connect(
                    self._on_catalog_edit_requested
                )
                self.iface.mainWindow().addDockWidget(
                    Qt.RightDockWidgetArea, self._catalog_dock
                )
                self._tabify_dock(self._catalog_dock)
                LOG.info("CatalogDockWidget added to right dock area")
            except Exception as exc:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Error",
                    f"Failed to open the symbol catalog:\n{exc}",
                )
                self._catalog_action.setChecked(False)
                return

        if checked:
            self._catalog_dock.show()
            self._catalog_dock.raise_()
        else:
            self._catalog_dock.hide()

    def _toggle_orbat_dock(self, checked: bool) -> None:
        """Show or hide the ORBAT manager dock widget."""
        if self._orbat_dock is None:
            try:
                from .gui.orbat_dock import OrbatDockWidget

                self._orbat_dock = OrbatDockWidget(
                    iface=self.iface,
                    symbol_server=self._symbol_server,
                    action=self._orbat_action,
                    parent=self.iface.mainWindow(),
                )
                self._orbat_dock.set_project_data(self._project_data)
                self._orbat_dock.set_layer_manager(self._layer_manager)
                self._orbat_dock.edit_unit_requested.connect(
                    self._on_orbat_edit_unit_requested
                )
                self._orbat_dock.setObjectName("KadasApp6OrbatDock")
                self.iface.mainWindow().addDockWidget(
                    Qt.RightDockWidgetArea, self._orbat_dock
                )
                self._tabify_dock(self._orbat_dock)
                LOG.info("OrbatDockWidget added to right dock area")
            except Exception as exc:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Error",
                    f"Failed to open the ORBAT manager:\n{exc}",
                )
                self._orbat_action.setChecked(False)
                return

        if checked:
            self._orbat_dock.show()
            self._orbat_dock.raise_()
        else:
            self._orbat_dock.hide()

    def _toggle_settings_dock(self, checked: bool) -> None:
        """Show or hide the settings dock widget."""
        if self._settings_dock is None:
            try:
                from .gui.settings_dock import SettingsDockWidget

                self._settings_dock = SettingsDockWidget(
                    iface=self.iface,
                    action=self._settings_action,
                    parent=self.iface.mainWindow(),
                )
                self._settings_dock.set_project_data(self._project_data)
                self._settings_dock.set_symbol_server(self._symbol_server)
                self._settings_dock.set_layer_manager(self._layer_manager)
                self._settings_dock.project_loaded.connect(
                    self._on_project_loaded
                )
                if self._layer_manager is not None:
                    self._settings_dock.symbol_size_changed.connect(
                        self._layer_manager.set_symbol_size
                    )
                    self._settings_dock.show_text_modifiers_changed.connect(
                        self._layer_manager.set_show_text_modifiers
                    )
                    self._settings_dock.show_text_modifiers_changed.connect(
                        self._on_show_text_modifiers_changed
                    )
                # Temporal wiring
                self._settings_dock.temporal_filtering_toggled.connect(
                    self._on_temporal_filtering_toggled
                )
                self._settings_dock.temporal_fit_to_data_requested.connect(
                    self._on_temporal_fit_to_data_requested
                )
                if self._temporal_manager is not None:
                    self._temporal_manager.filter_changed.connect(
                        self._settings_dock.update_temporal_status
                    )
                self._settings_dock.setObjectName("KadasApp6SettingsDock")
                self.iface.mainWindow().addDockWidget(
                    Qt.RightDockWidgetArea, self._settings_dock
                )
                self._tabify_dock(self._settings_dock)
                LOG.info("SettingsDockWidget added to right dock area")
            except Exception as exc:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Error",
                    f"Failed to open settings:\n{exc}",
                )
                self._settings_action.setChecked(False)
                return

        if checked:
            self._settings_dock.show()
            self._settings_dock.raise_()
        else:
            self._settings_dock.hide()

    def _toggle_layer_manager_dock(self, checked: bool) -> None:
        """Show or hide the layer manager dock widget."""
        if self._layer_manager_dock is None:
            try:
                from .gui.layer_manager_dock import LayerManagerDockWidget

                self._layer_manager_dock = LayerManagerDockWidget(
                    iface=self.iface,
                    action=self._layer_mgr_action,
                    parent=self.iface.mainWindow(),
                )
                self._layer_manager_dock.set_project_data(self._project_data)
                self._layer_manager_dock.set_layer_manager(self._layer_manager)
                self._layer_manager_dock.setObjectName(
                    "KadasApp6LayerManagerDock"
                )
                self.iface.mainWindow().addDockWidget(
                    Qt.RightDockWidgetArea, self._layer_manager_dock
                )
                self._tabify_dock(self._layer_manager_dock)
                LOG.info("LayerManagerDockWidget added to right dock area")
            except Exception as exc:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Error",
                    f"Failed to open the layer manager:\n{exc}",
                )
                self._layer_mgr_action.setChecked(False)
                return

        if checked:
            self._layer_manager_dock.show()
            self._layer_manager_dock.raise_()
        else:
            self._layer_manager_dock.hide()

    # ------------------------------------------------------------------
    # About dialog
    # ------------------------------------------------------------------

    def show_about(self) -> None:
        """Show the About dialog with plugin icon and optional Buy-me-a-coffee link."""
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtGui import QPixmap
        from qgis.PyQt.QtWidgets import (
            QDialog, QDialogButtonBox, QHBoxLayout,
            QLabel, QVBoxLayout,
        )

        bmc_url = _PLUGIN_METADATA.get("buymeacoffee", "")
        icon_path = plugin_path("icons", "milsymb.svg")

        dlg = QDialog(self.iface.mainWindow())
        dlg.setWindowTitle(f"About {_PLUGIN_NAME}")
        dlg.setMinimumWidth(420)

        root = QVBoxLayout(dlg)
        root.setSpacing(12)

        # ---- Header row: icon + title ----
        header = QHBoxLayout()
        icon_lbl = QLabel()
        px = QPixmap(icon_path)
        if not px.isNull():
            icon_lbl.setPixmap(
                px.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_lbl.setFixedSize(72, 72)
        header.addWidget(icon_lbl)

        title_lbl = QLabel(
            f"<h2>{_PLUGIN_NAME}</h2>"
            f"<p><b>Version {_PLUGIN_VERSION}</b></p>"
        )
        title_lbl.setTextFormat(Qt.RichText)
        header.addWidget(title_lbl, 1)
        root.addLayout(header)

        # ---- Body ----
        body_lbl = QLabel(
            f"<p>Military symbol library (APP-6D) with ORBAT management<br>"
            f"and temporal control for KADAS Albireo 2.</p>"
            f"<p>Features:<br>"
            f"&bull; APP-6(D) symbol catalog with 20-char SIDC<br>"
            f"&bull; Built-in SVG/PNG rendering server<br>"
            f"&bull; ORBAT hierarchical manager<br>"
            f"&bull; KADAS Temporal Controller integration<br>"
            f"&bull; KMZ export with embedded PNG icons</p>"
            f"<p>Author: {_PLUGIN_AUTHOR}<br>"
            f"Repository: coming soon...</p>"
        )
        body_lbl.setWordWrap(True)
        body_lbl.setOpenExternalLinks(True)
        body_lbl.setTextFormat(Qt.RichText)
        root.addWidget(body_lbl)

        # ---- Buy me a coffee (optional) ----
        if bmc_url:
            bmc_lbl = QLabel(
                f"<p style='text-align:center'>"
                f"<a href='{bmc_url}'>"
                f"&#9749; Buy me a coffee \u2013 support this plugin!"
                f"</a></p>"
            )
            bmc_lbl.setAlignment(Qt.AlignCenter)
            bmc_lbl.setOpenExternalLinks(True)
            bmc_lbl.setTextFormat(Qt.RichText)
            root.addWidget(bmc_lbl)

        # ---- Footer ----
        footer_lbl = QLabel(
            "<p style='font-size:10px; color:gray; text-align:center'>"
            "Compatible with KADAS Albireo 2 &middot; GPL-2.0 licence</p>"
        )
        footer_lbl.setAlignment(Qt.AlignCenter)
        footer_lbl.setTextFormat(Qt.RichText)
        root.addWidget(footer_lbl)

        # ---- Close button ----
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.accept)
        root.addWidget(buttons)

        dlg.exec_()

    # ------------------------------------------------------------------
    # Log file
    # ------------------------------------------------------------------

    def open_log_file(self) -> None:
        """Open the plugin log file with the default viewer."""
        log_path = os.environ.get(
            "KADAS_MILSYMB_LOG",
            os.path.join(milsymb_data_dir(), "kadas_milsymb.log"),
        )
        if not os.path.exists(log_path):
            QMessageBox.information(
                self.iface.mainWindow(),
                "Log file not found",
                f"No log file exists yet at:\n{log_path}",
            )
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(log_path)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", log_path])
            else:
                subprocess.Popen(["xdg-open", log_path])
        except Exception as exc:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Cannot open log",
                f"Failed to open the log file:\n{exc}",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_action(
        self,
        icon_path: str,
        text: str,
        tooltip: str,
        checkable: bool,
        callback,
    ) -> QAction:
        """Create a QAction, connect it and add it to _actions."""
        action = QAction(QIcon(icon_path), text)
        action.setToolTip(tooltip)
        action.setCheckable(checkable)
        if checkable:
            action.toggled.connect(callback)
        else:
            action.triggered.connect(callback)
        self._actions.append(action)
        return action

    def tr(self, message: str) -> str:
        """Translate *message* using Qt's translation mechanism."""
        return QCoreApplication.translate("KadasApp6Plugin", message)

