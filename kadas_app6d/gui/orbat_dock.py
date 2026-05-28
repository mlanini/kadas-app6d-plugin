# -*- coding: utf-8 -*-
"""
ORBAT Manager dock widget – hierarchical tree editor.

Layout (top → bottom)
---------------------
1. **Toolbar** – New ORBAT, Add Unit, Edit, Delete, Move Up/Down,
   Place on Map, Import, Export
2. **ORBAT selector** (QComboBox) – switch between multiple ORBATs
3. **Tree view** (QTreeWidget) – hierarchical unit tree with icons
4. **Detail panel** – selected unit info and map-link status

Interactions
------------
* Double-click a unit → Symbol Editor dock (advanced APP-6D editor)
* Drag and drop → re-parent (move)
* Context menu → add child, edit, delete, place on map
* Place on Map → activates ``SymbolPlacementTool`` with ORBAT linkage
"""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt, QByteArray, pyqtSignal
from qgis.PyQt.QtGui import QIcon, QImage, QPainter, QPixmap
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QScrollArea,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import DARK_THEME_SS
from ..core.models import (
    MilSymbol,
    MilSymbProject,
    Orbat,
    OrbatUnit,
)
from ..symbology.renderer import cached_svg
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.orbat_dock")


# ======================================================================
# Helpers
# ======================================================================

def _svg_to_pixmap(svg_str: str, size: int) -> QPixmap | None:
    try:
        from qgis.PyQt.QtSvg import QSvgRenderer
    except ImportError:
        return None
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    if not renderer.isValid():
        return None
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return QPixmap.fromImage(image)


def _unit_icon(unit: OrbatUnit, size: int = 24) -> QIcon:
    """Build a QIcon from the unit's SIDC."""
    try:
        svg = cached_svg(unit.sidc)
        pm = _svg_to_pixmap(svg, size)
        if pm:
            return QIcon(pm)
    except ValueError:
        pass
    return QIcon()


# ======================================================================
# OrbatDockWidget
# ======================================================================

class OrbatDockWidget(QDockWidget):
    """ORBAT Manager dock widget.

    Parameters
    ----------
    iface
        ``KadasPluginInterface`` reference.
    symbol_server
        ``SymbolServer`` instance (may be *None*).
    action : QAction
        The toggle action that controls visibility.
    parent : QWidget or None
        Parent widget (usually the main window).
    """

    # Emitted when a unit is placed on the map
    unit_placed = pyqtSignal(object)  # MilSymbol
    # Emitted when the user requests editing an existing unit (handled by plugin)
    edit_unit_requested = pyqtSignal(object)  # OrbatUnit

    def __init__(self, iface, symbol_server=None, action=None, parent=None):
        super().__init__("ORBAT Manager", parent)
        self._iface = iface
        self._symbol_server = symbol_server
        self._action = action

        # External bindings (set by plugin)
        self._project_data: MilSymbProject | None = None
        self._layer_manager = None
        self._map_tool = None

        self._build_ui()
        LOG.debug("OrbatDockWidget created")

    # ------------------------------------------------------------------
    # Dock lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):  # noqa: N802
        """Uncheck the ribbon action when the dock is closed by the user."""
        if self._action is not None:
            self._action.setChecked(False)
        super().closeEvent(event)

    # External bindings
    # ------------------------------------------------------------------

    def set_project_data(self, proj: MilSymbProject) -> None:
        self._project_data = proj
        self._refresh_orbat_combo()

    def set_layer_manager(self, mgr) -> None:
        self._layer_manager = mgr

    # ------------------------------------------------------------------
    # Active ORBAT helpers
    # ------------------------------------------------------------------

    def _active_orbat(self) -> Orbat | None:
        """Return the currently selected ORBAT."""
        if self._project_data is None:
            return None
        idx = self._orbat_combo.currentIndex()
        if 0 <= idx < len(self._project_data.orbats):
            return self._project_data.orbats[idx]
        return None

    def _selected_unit(self) -> OrbatUnit | None:
        """Return the unit associated with the currently selected tree item."""
        item = self._tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.UserRole)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        container = QWidget()
        container.setStyleSheet(DARK_THEME_SS)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # ---- Toolbar ----
        self._toolbar = QToolBar()
        self._toolbar.setIconSize(self._toolbar.iconSize())
        self._toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self._act_new_orbat = self._toolbar.addAction("New ORBAT")
        self._act_new_orbat.setToolTip("Create a new Order of Battle")
        self._act_new_orbat.triggered.connect(self._on_new_orbat)

        self._act_del_orbat = self._toolbar.addAction("Delete ORBAT")
        self._act_del_orbat.setToolTip("Delete the current ORBAT")
        self._act_del_orbat.triggered.connect(self._on_delete_orbat)

        self._toolbar.addSeparator()

        self._act_add_unit = self._toolbar.addAction("+ Unit")
        self._act_add_unit.setToolTip("Add a child unit under the selected unit")
        self._act_add_unit.triggered.connect(self._on_add_unit)

        self._act_edit_unit = self._toolbar.addAction("Edit")
        self._act_edit_unit.setToolTip("Edit the selected unit")
        self._act_edit_unit.triggered.connect(self._on_edit_unit)

        self._act_del_unit = self._toolbar.addAction("Delete")
        self._act_del_unit.setToolTip("Delete the selected unit (children re-parented)")
        self._act_del_unit.triggered.connect(self._on_delete_unit)

        self._toolbar.addSeparator()

        self._act_place = self._toolbar.addAction("Place")
        self._act_place.setToolTip("Place selected unit on the map")
        self._act_place.triggered.connect(self._on_place_unit)

        self._toolbar.addSeparator()

        self._act_import = self._toolbar.addAction("Import")
        self._act_import.setToolTip("Import an ORBAT from JSON file")
        self._act_import.triggered.connect(self._on_import)

        self._act_export = self._toolbar.addAction("Export")
        self._act_export.setToolTip("Export current ORBAT to JSON file")
        self._act_export.triggered.connect(self._on_export)

        layout.addWidget(self._toolbar)

        # ---- ORBAT selector ----
        orbat_row = QHBoxLayout()
        orbat_row.addWidget(QLabel("ORBAT:"))
        self._orbat_combo = QComboBox()
        self._orbat_combo.currentIndexChanged.connect(self._on_orbat_switched)
        orbat_row.addWidget(self._orbat_combo, 1)
        layout.addLayout(orbat_row)

        # ---- Tree ----
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Unit", "Echelon", "SIDC"])
        self._tree.setColumnWidth(0, 200)
        self._tree.setColumnWidth(1, 70)
        self._tree.setColumnWidth(2, 160)
        self._tree.setIndentation(20)
        self._tree.setDragDropMode(QTreeWidget.InternalMove)
        self._tree.setDragEnabled(True)
        self._tree.setAcceptDrops(True)
        self._tree.setDropIndicatorShown(True)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._tree.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._tree, 1)

        # ---- Detail panel ----
        self._detail_label = QLabel("")
        self._detail_label.setWordWrap(True)
        self._detail_label.setStyleSheet(
            "QLabel { background: #ffffff; border: 1px solid #ccc;"
            " padding: 4px; font-size: 11px; }"
        )
        self._detail_label.setMinimumHeight(60)
        layout.addWidget(self._detail_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        self.setWidget(scroll)
        self._update_button_states()

    # ------------------------------------------------------------------
    # ORBAT combo management
    # ------------------------------------------------------------------

    def _refresh_orbat_combo(self) -> None:
        self._orbat_combo.blockSignals(True)
        self._orbat_combo.clear()
        if self._project_data:
            for orbat in self._project_data.orbats:
                self._orbat_combo.addItem(orbat.name)
        self._orbat_combo.blockSignals(False)

        if self._orbat_combo.count() > 0:
            self._orbat_combo.setCurrentIndex(0)
            self._rebuild_tree()
        else:
            self._tree.clear()
        self._update_button_states()

    def _on_orbat_switched(self, _idx: int) -> None:
        self._rebuild_tree()
        self._update_button_states()

    # ------------------------------------------------------------------
    # Tree building
    # ------------------------------------------------------------------

    def _rebuild_tree(self) -> None:
        """Fully rebuild the QTreeWidget from the active ORBAT."""
        self._tree.clear()
        orbat = self._active_orbat()
        if orbat is None:
            return

        # Map unit_id → QTreeWidgetItem
        item_map: dict[str, QTreeWidgetItem] = {}

        def _add_unit_item(unit: OrbatUnit, parent_item=None):
            from ..core.sidc import SIDC as SIDCClass

            display_name = unit.short_name or unit.name or "(unnamed)"
            try:
                sidc_obj = SIDCClass.parse(unit.sidc)
                echelon_str = sidc_obj.amplifier
            except ValueError:
                echelon_str = "?"

            tw = QTreeWidgetItem([display_name, echelon_str, unit.sidc])
            tw.setData(0, Qt.UserRole, unit)
            tw.setIcon(0, _unit_icon(unit))
            tw.setFlags(
                tw.flags()
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
            )

            if parent_item is not None:
                parent_item.addChild(tw)
            else:
                self._tree.addTopLevelItem(tw)

            item_map[unit.id] = tw

            for child in orbat.children_of(unit.id):
                _add_unit_item(child, tw)

        for root in orbat.root_units():
            _add_unit_item(root)

        self._tree.expandAll()

    # ------------------------------------------------------------------
    # Drag-drop sync
    # ------------------------------------------------------------------

    def _sync_parent_ids(self) -> None:
        """Synchronise parent_ids in the model from the tree structure."""
        orbat = self._active_orbat()
        if orbat is None:
            return

        def _sync_item(item: QTreeWidgetItem, parent_id: str | None):
            unit: OrbatUnit | None = item.data(0, Qt.UserRole)
            if unit is not None:
                unit.parent_id = parent_id
            for i in range(item.childCount()):
                child_item = item.child(i)
                _sync_item(child_item, unit.id if unit else None)

        for i in range(self._tree.topLevelItemCount()):
            _sync_item(self._tree.topLevelItem(i), None)

        LOG.debug("Parent IDs synced after drag-drop")

    def dropEvent(self, event):  # noqa: N802
        """Override to sync parent_ids after a drag-drop."""
        super().dropEvent(event)
        self._sync_parent_ids()

    # ------------------------------------------------------------------
    # Button state management
    # ------------------------------------------------------------------

    def _update_button_states(self) -> None:
        has_orbat = self._active_orbat() is not None
        has_selection = self._selected_unit() is not None

        self._act_add_unit.setEnabled(has_orbat)
        self._act_edit_unit.setEnabled(has_selection)
        self._act_del_unit.setEnabled(has_selection)
        self._act_place.setEnabled(has_selection)
        self._act_del_orbat.setEnabled(has_orbat)
        self._act_export.setEnabled(has_orbat)

    def _on_selection_changed(self, current, _prev) -> None:
        self._update_button_states()
        self._update_detail_panel()

    # ------------------------------------------------------------------
    # Detail panel
    # ------------------------------------------------------------------

    def _update_detail_panel(self) -> None:
        unit = self._selected_unit()
        if unit is None:
            self._detail_label.setText("")
            return

        map_status = (
            f"Linked to map symbol: {unit.map_symbol_id[:8]}…"
            if unit.map_symbol_id
            else "Not placed on map"
        )
        temporal = ""
        if unit.temporal.start:
            temporal = f"\nValid: {unit.temporal.start}"
            if unit.temporal.end:
                temporal += f" → {unit.temporal.end}"

        self._detail_label.setText(
            f"<b>{unit.name}</b> ({unit.short_name})\n"
            f"SIDC: <code>{unit.sidc}</code>\n"
            f"{map_status}{temporal}"
        )

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _on_context_menu(self, pos) -> None:
        menu = QMenu(self)
        unit = self._selected_unit()

        act_add_root = menu.addAction("Add Root Unit")
        act_add_root.triggered.connect(lambda: self._on_add_unit(as_root=True))

        if unit:
            act_add_child = menu.addAction("Add Child Unit")
            act_add_child.triggered.connect(lambda: self._on_add_unit(as_root=False))

            menu.addSeparator()
            act_edit = menu.addAction("Edit Unit…")
            act_edit.triggered.connect(self._on_edit_unit)

            act_del = menu.addAction("Delete Unit")
            act_del.triggered.connect(self._on_delete_unit)

            menu.addSeparator()
            act_place = menu.addAction("Place on Map")
            act_place.triggered.connect(self._on_place_unit)

            if unit.map_symbol_id:
                act_zoom = menu.addAction("Zoom to Unit")
                act_zoom.triggered.connect(self._on_zoom_to_unit)

            menu.addSeparator()
            act_move_up = menu.addAction("Move Up")
            act_move_up.triggered.connect(self._on_move_up)

            act_move_down = menu.addAction("Move Down")
            act_move_down.triggered.connect(self._on_move_down)

        menu.exec_(self._tree.viewport().mapToGlobal(pos))

    def _on_item_double_clicked(self, item, _col) -> None:
        self._on_edit_unit()

    # ------------------------------------------------------------------
    # ORBAT CRUD
    # ------------------------------------------------------------------

    def _on_new_orbat(self) -> None:
        if self._project_data is None:
            return
        from qgis.PyQt.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "New ORBAT", "ORBAT name:", text="New ORBAT"
        )
        if not ok or not name.strip():
            return
        orbat = Orbat(name=name.strip())
        self._project_data.orbats.append(orbat)
        self._refresh_orbat_combo()
        self._orbat_combo.setCurrentIndex(len(self._project_data.orbats) - 1)
        LOG.info("New ORBAT created: %s", orbat.name)

    def _on_delete_orbat(self) -> None:
        orbat = self._active_orbat()
        if orbat is None or self._project_data is None:
            return
        reply = QMessageBox.question(
            self,
            "Delete ORBAT",
            f"Delete ORBAT '{orbat.name}' and all its units?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._project_data.orbats.remove(orbat)
        self._refresh_orbat_combo()
        LOG.info("ORBAT deleted: %s", orbat.name)

    # ------------------------------------------------------------------
    # Unit CRUD
    # ------------------------------------------------------------------

    def _on_add_unit(self, as_root: bool = False) -> None:
        orbat = self._active_orbat()
        if orbat is None:
            return

        parent_unit = None if as_root else self._selected_unit()

        from .orbat_dialogs import UnitEditDialog
        dlg = UnitEditDialog(
            unit=None,
            parent_unit=parent_unit,
            parent=self,
        )
        if dlg.exec_() != dlg.Accepted:
            return

        new_unit = dlg.get_unit()
        orbat.add_unit(new_unit)
        self._rebuild_tree()
        LOG.info("Unit added: %s (parent=%s)", new_unit.name, new_unit.parent_id)

    def _on_edit_unit(self) -> None:
        unit = self._selected_unit()
        if unit is None:
            return
        # Delegate editing to the advanced Symbol Editor dock (via plugin signal)
        self.edit_unit_requested.emit(unit)

    def refresh_after_edit(self, unit) -> None:
        """Called by the plugin after the Symbol Editor has applied changes to *unit*."""
        self._rebuild_tree()
        self._sync_unit_to_map(unit)
        LOG.info("Unit edited via Symbol Editor: %s", unit.name)

    def _on_delete_unit(self) -> None:
        unit = self._selected_unit()
        orbat = self._active_orbat()
        if unit is None or orbat is None:
            return

        reply = QMessageBox.question(
            self,
            "Delete Unit",
            f"Delete '{unit.name}'?\nChildren will be re-parented to its parent.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Remove linked map symbol
        if unit.map_symbol_id and self._layer_manager:
            self._layer_manager.remove_symbol(unit.map_symbol_id)

        orbat.remove_unit(unit.id)
        self._rebuild_tree()
        LOG.info("Unit deleted: %s", unit.name)

    # ------------------------------------------------------------------
    # Move up / down (sibling reorder)
    # ------------------------------------------------------------------

    def _on_move_up(self) -> None:
        self._move_unit_in_list(-1)

    def _on_move_down(self) -> None:
        self._move_unit_in_list(1)

    def _move_unit_in_list(self, direction: int) -> None:
        """Move the selected unit up (−1) or down (+1) among its siblings."""
        unit = self._selected_unit()
        orbat = self._active_orbat()
        if unit is None or orbat is None:
            return

        siblings = [
            u for u in orbat.units if u.parent_id == unit.parent_id
        ]
        idx = next((i for i, u in enumerate(siblings) if u.id == unit.id), None)
        if idx is None:
            return
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(siblings):
            return

        # Swap in the flat units list
        swap_target = siblings[new_idx]
        a = orbat.units.index(unit)
        b = orbat.units.index(swap_target)
        orbat.units[a], orbat.units[b] = orbat.units[b], orbat.units[a]

        self._rebuild_tree()
        # Re-select the moved unit
        self._select_unit_in_tree(unit.id)

    def _select_unit_in_tree(self, unit_id: str) -> None:
        """Select the tree item matching *unit_id*."""
        def _find(item: QTreeWidgetItem) -> bool:
            u: OrbatUnit | None = item.data(0, Qt.UserRole)
            if u and u.id == unit_id:
                self._tree.setCurrentItem(item)
                return True
            for i in range(item.childCount()):
                if _find(item.child(i)):
                    return True
            return False

        for i in range(self._tree.topLevelItemCount()):
            if _find(self._tree.topLevelItem(i)):
                break

    # ------------------------------------------------------------------
    # Place on Map
    # ------------------------------------------------------------------

    def _on_place_unit(self) -> None:
        """Activate the map tool to place the selected unit."""
        unit = self._selected_unit()
        if unit is None:
            return

        from .map_tool import SymbolPlacementTool

        canvas = self._iface.mapCanvas()
        self._map_tool = SymbolPlacementTool(
            canvas=canvas,
            sidc=unit.sidc,
            designation=unit.short_name or unit.name,
        )
        self._map_tool.symbol_placed.connect(
            lambda sym: self._on_unit_symbol_placed(unit, sym)
        )
        canvas.setMapTool(self._map_tool)
        LOG.info("Placement tool activated for unit '%s'", unit.name)

    def _on_unit_symbol_placed(self, unit: OrbatUnit, sym: MilSymbol) -> None:
        """Link the placed MilSymbol to the ORBAT unit."""
        sym.orbat_unit_id = unit.id
        sym.designation = unit.short_name or unit.name
        unit.map_symbol_id = sym.id
        unit.longitude = sym.longitude
        unit.latitude = sym.latitude

        if self._layer_manager is not None:
            self._layer_manager.add_symbol(sym)

        self.unit_placed.emit(sym)
        self._rebuild_tree()
        self._update_detail_panel()
        LOG.info(
            "Unit '%s' placed at (%.6f, %.6f) → symbol %s",
            unit.name, sym.longitude, sym.latitude, sym.id,
        )

    def _sync_unit_to_map(self, unit: OrbatUnit) -> None:
        """After editing a unit, update its linked map symbol (if any)."""
        if not unit.map_symbol_id or self._layer_manager is None:
            return
        sym = self._layer_manager.get_symbol(unit.map_symbol_id)
        if sym is None:
            return
        sym.sidc = unit.sidc
        sym.designation = unit.short_name or unit.name
        sym.temporal = unit.temporal
        self._layer_manager.update_symbol(sym)

    # ------------------------------------------------------------------
    # Zoom to unit
    # ------------------------------------------------------------------

    def _on_zoom_to_unit(self) -> None:
        unit = self._selected_unit()
        if unit is None or unit.longitude is None or unit.latitude is None:
            return

        from qgis.core import (
            QgsCoordinateReferenceSystem,
            QgsCoordinateTransform,
            QgsPointXY,
            QgsProject,
        )
        from qgis.gui import QgsMapCanvas

        canvas: QgsMapCanvas = self._iface.mapCanvas()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        map_crs = canvas.mapSettings().destinationCrs()

        pt = QgsPointXY(unit.longitude, unit.latitude)
        if map_crs != wgs84:
            xform = QgsCoordinateTransform(wgs84, map_crs, QgsProject.instance())
            pt = xform.transform(pt)

        canvas.setCenter(pt)
        canvas.refresh()
        LOG.debug("Zoomed to unit '%s'", unit.name)

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def _on_import(self) -> None:
        if self._project_data is None:
            return
        from .orbat_dialogs import import_orbat_dialog
        orbat = import_orbat_dialog(parent=self)
        if orbat is None:
            return
        self._project_data.orbats.append(orbat)

        # Re-create map symbols for units that had been placed on the map
        self._restore_map_symbols(orbat)

        self._refresh_orbat_combo()
        self._orbat_combo.setCurrentIndex(len(self._project_data.orbats) - 1)
        LOG.info("ORBAT '%s' imported (%d units)", orbat.name, len(orbat.units))

    def _on_export(self) -> None:
        orbat = self._active_orbat()
        if orbat is None:
            return
        from .orbat_dialogs import export_orbat_dialog
        export_orbat_dialog(orbat, parent=self)

    def _restore_map_symbols(self, orbat: "Orbat") -> None:
        """Re-create :class:`MilSymbol` entries for imported units that
        have coordinates (i.e. were placed on the map before export).

        Each unit gets a *new* ``MilSymbol`` and the unit's
        ``map_symbol_id`` is updated to match.
        """
        if self._layer_manager is None or self._project_data is None:
            return

        count = 0
        for unit in orbat.units:
            if unit.longitude is None or unit.latitude is None:
                continue
            sym = MilSymbol(
                sidc=unit.sidc,
                designation=unit.short_name or unit.name,
                longitude=unit.longitude,
                latitude=unit.latitude,
                temporal=unit.temporal,
                orbat_unit_id=unit.id,
            )
            unit.map_symbol_id = sym.id
            self._layer_manager.add_symbol(sym)
            count += 1

        if count:
            LOG.info("Restored %d map symbols from imported ORBAT '%s'",
                     count, orbat.name)
