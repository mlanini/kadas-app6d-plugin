# -*- coding: utf-8 -*-
"""
Catalog dock widget – symbol browser with search, preview and placement.

Layout (top → bottom)
---------------------
1. **Search bar** (QLineEdit) – filters the tree in real time
2. **Identity selector** (QComboBox) – Friend / Hostile / Neutral / Unknown
3. **Echelon selector** (QComboBox) – None … Region
4. **Symbol tree** (QTreeWidget) – Symbol Set → Category → Entity
5. **Preview** (QLabel) – SVG rendered as pixmap via QSvgRenderer
6. **Designation** (QLineEdit) – optional short name
7. **Higher Formation** (QLineEdit) – optional label
8. **Place on Map** button
"""

from __future__ import annotations

import json
from typing import Optional

from qgis.PyQt.QtCore import Qt, QByteArray, QMimeData, pyqtSignal
from qgis.PyQt.QtGui import QDrag, QIcon, QImage, QPainter, QPixmap
from qgis.PyQt.QtWidgets import (
    QAction,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.sidc import (
    Echelon,
    StandardIdentity,
)
from ..core.models import MilSymbol, MilSymbProject
from . import DARK_THEME_SS
from ..symbology.catalog_data import (
    ALL_ENTRIES,
    SYMBOL_SET_NAMES,
    CatalogEntry,
    search_catalog,
)
from ..symbology.renderer import cached_svg
from ..logger import get_logger
from .canvas_drop_filter import MILSYMB_MIME_TYPE

LOG = get_logger("kadas_milsymb.gui.catalog_dock")

# -- Identity combo items ------------------------------------------------

_IDENTITY_ITEMS = [
    ("Friend",  StandardIdentity.FRIEND),
    ("Assumed Friend", StandardIdentity.ASSUMED_FRIEND),
    ("Neutral", StandardIdentity.NEUTRAL),
    ("Unknown", StandardIdentity.UNKNOWN),
    ("Hostile", StandardIdentity.HOSTILE_FAKER),
    ("Suspect", StandardIdentity.SUSPECT_JOKER),
    ("Pending", StandardIdentity.PENDING),
]

# -- Echelon combo items -------------------------------------------------

_ECHELON_ITEMS = [
    ("(none)",       Echelon.NONE),
    ("Team / Crew",  Echelon.TEAM_CREW),
    ("Squad",        Echelon.SQUAD),
    ("Section",      Echelon.SECTION),
    ("Platoon",      Echelon.PLATOON),
    ("Company",      Echelon.COMPANY),
    ("Battalion",    Echelon.BATTALION),
    ("Regiment",     Echelon.REGIMENT),
    ("Brigade",      Echelon.BRIGADE),
    ("Division",     Echelon.DIVISION),
    ("Corps",        Echelon.CORPS),
    ("Army",         Echelon.ARMY),
    ("Army Group",   Echelon.ARMY_GROUP),
    ("Region",       Echelon.REGION),
]

# Preview size
_PREVIEW_SIZE = 100


# ======================================================================
# CatalogDockWidget
# ======================================================================

class CatalogDockWidget(QDockWidget):
    """Symbol catalog browser and placement dock.

    Parameters
    ----------
    iface
        ``KadasPluginInterface`` reference.
    symbol_server
        ``SymbolServer`` instance (may be *None* if not started).
    action : QAction
        The toggle action that controls visibility.
    parent : QWidget or None
        Parent widget (usually the main window).
    """

    # Emitted when user places a symbol via the map tool
    symbol_placed = pyqtSignal(object)  # MilSymbol

    # Emitted when user requests editing a catalog entry in the editor dock
    edit_in_editor_requested = pyqtSignal(object)  # dict with entry, identity, echelon

    def __init__(self, iface, symbol_server=None, action=None, parent=None):
        super().__init__("Symbol Catalog", parent)
        self._iface = iface
        self._symbol_server = symbol_server
        self._action = action

        # Currently selected entry
        self._selected_entry: Optional[CatalogEntry] = None

        # Map tool reference
        self._map_tool = None

        # Symbol layer manager (set externally by plugin)
        self._layer_manager = None

        # Project data (set externally by plugin)
        self._project_data: Optional[MilSymbProject] = None

        self._build_ui()
        self._populate_tree()

    # ------------------------------------------------------------------
    # Dock lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):  # noqa: N802
        """Uncheck the ribbon action when the dock is closed by the user."""
        if self._action is not None:
            self._action.setChecked(False)
        super().closeEvent(event)

    # Layer manager binding
    # ------------------------------------------------------------------

    def set_layer_manager(self, mgr) -> None:
        """Attach the SymbolLayerManager for placement."""
        self._layer_manager = mgr

    def set_project_data(self, proj: MilSymbProject) -> None:
        """Attach the project data container."""
        self._project_data = proj

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        container = QWidget()
        container.setStyleSheet(DARK_THEME_SS)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ---- Search bar ----
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search symbols…")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_edit)

        # ---- Identity selector ----
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("Identity:"))
        self._identity_combo = QComboBox()
        for label, _si in _IDENTITY_ITEMS:
            self._identity_combo.addItem(label, _si)
        self._identity_combo.currentIndexChanged.connect(self._on_config_changed)
        id_layout.addWidget(self._identity_combo, 1)
        layout.addLayout(id_layout)

        # ---- Echelon selector ----
        ech_layout = QHBoxLayout()
        ech_layout.addWidget(QLabel("Echelon:"))
        self._echelon_combo = QComboBox()
        for label, _ech in _ECHELON_ITEMS:
            self._echelon_combo.addItem(label, _ech)
        self._echelon_combo.currentIndexChanged.connect(self._on_config_changed)
        ech_layout.addWidget(self._echelon_combo, 1)
        layout.addLayout(ech_layout)

        # ---- Symbol tree ----
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.setDragEnabled(True)
        self._tree.currentItemChanged.connect(self._on_tree_selection)
        self._tree.itemPressed.connect(self._on_tree_item_pressed)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        layout.addWidget(self._tree, 1)

        # ---- Preview ----
        self._preview_label = QLabel()
        self._preview_label.setFixedSize(_PREVIEW_SIZE, _PREVIEW_SIZE)
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setStyleSheet(
            "QLabel { background: white; border: 1px solid #ccc; }"
        )
        preview_layout = QHBoxLayout()
        preview_layout.addStretch()
        preview_layout.addWidget(self._preview_label)
        preview_layout.addStretch()
        layout.addLayout(preview_layout)

        # ---- SIDC label ----
        self._sidc_label = QLabel("")
        self._sidc_label.setAlignment(Qt.AlignCenter)
        self._sidc_label.setStyleSheet(
            "font-family: monospace; font-size: 11px; color: #666;"
        )
        layout.addWidget(self._sidc_label)

        # ---- Designation ----
        des_layout = QHBoxLayout()
        des_layout.addWidget(QLabel("Designation:"))
        self._designation_edit = QLineEdit()
        self._designation_edit.setPlaceholderText("e.g. 1/Inf Bat 5")
        des_layout.addWidget(self._designation_edit, 1)
        layout.addLayout(des_layout)

        # ---- Higher Formation ----
        hf_layout = QHBoxLayout()
        hf_layout.addWidget(QLabel("Higher Fm:"))
        self._higher_formation_edit = QLineEdit()
        self._higher_formation_edit.setPlaceholderText("e.g. 2 Mech Bde")
        hf_layout.addWidget(self._higher_formation_edit, 1)
        layout.addLayout(hf_layout)

        # ---- Buttons row: Open in Editor | Place on Map ----
        btn_layout = QHBoxLayout()

        self._edit_btn = QPushButton("Open in Editor")
        self._edit_btn.setEnabled(False)
        self._edit_btn.setToolTip("Open the Symbol Editor for the selected entry")
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        btn_layout.addWidget(self._edit_btn)

        self._place_btn = QPushButton("Place on Map")
        self._place_btn.setEnabled(False)
        self._place_btn.clicked.connect(self._on_place_clicked)
        btn_layout.addWidget(self._place_btn)

        layout.addLayout(btn_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        self.setWidget(scroll)

    # ------------------------------------------------------------------
    # Tree population
    # ------------------------------------------------------------------

    def _populate_tree(self, entries: list[CatalogEntry] | None = None) -> None:
        """Fill the tree widget from catalog entries."""
        self._tree.clear()
        source = entries if entries is not None else ALL_ENTRIES

        # Group: Symbol Set → Category → Entry
        ss_map: dict[str, dict[str, list[CatalogEntry]]] = {}
        for e in source:
            ss_name = SYMBOL_SET_NAMES.get(e.symbol_set, e.symbol_set)
            cat = e.category or "Other"
            ss_map.setdefault(ss_name, {}).setdefault(cat, []).append(e)

        for ss_name in sorted(ss_map.keys()):
            ss_item = QTreeWidgetItem([ss_name])
            ss_item.setFlags(ss_item.flags() & ~Qt.ItemIsSelectable)
            font = ss_item.font(0)
            font.setBold(True)
            ss_item.setFont(0, font)

            for cat_name in sorted(ss_map[ss_name].keys()):
                cat_item = QTreeWidgetItem([cat_name])
                cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsSelectable)

                for entry in ss_map[ss_name][cat_name]:
                    entry_item = QTreeWidgetItem([entry.name])
                    entry_item.setData(0, Qt.UserRole, entry)
                    entry_item.setToolTip(
                        0,
                        f"{entry.name_de or entry.name}\n"
                        f"SIDC template: {entry.sidc_template()}",
                    )

                    # Small icon preview
                    icon_pixmap = self._render_entry_icon(entry, 24)
                    if icon_pixmap:
                        entry_item.setIcon(0, QIcon(icon_pixmap))

                    cat_item.addChild(entry_item)

                ss_item.addChild(cat_item)

            self._tree.addTopLevelItem(ss_item)

        self._tree.expandAll()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_search_changed(self, text: str) -> None:
        """Filter the tree based on the search query."""
        if not text.strip():
            self._populate_tree()
            return
        results = search_catalog(text)
        self._populate_tree(results)

    def _on_tree_selection(self, current: QTreeWidgetItem, _prev) -> None:
        """Update preview when a leaf entry is selected."""
        if current is None:
            self._selected_entry = None
            self._place_btn.setEnabled(False)
            self._edit_btn.setEnabled(False)
            return

        entry: CatalogEntry | None = current.data(0, Qt.UserRole)
        if entry is None:
            self._selected_entry = None
            self._place_btn.setEnabled(False)
            self._edit_btn.setEnabled(False)
            return

        self._selected_entry = entry
        self._place_btn.setEnabled(True)
        self._edit_btn.setEnabled(True)
        self._update_preview()

    def _on_config_changed(self, _index: int) -> None:
        """Re-render preview when identity or echelon changes."""
        if self._selected_entry is not None:
            self._update_preview()

    def _on_tree_item_pressed(self, item: QTreeWidgetItem, _column: int) -> None:
        """Start a drag operation when a leaf symbol entry is pressed."""
        entry: CatalogEntry | None = item.data(0, Qt.UserRole)
        if entry is None:
            return  # header/category rows are not draggable

        sidc = self._build_sidc()
        payload = {
            "sidc": sidc,
            "designation": self._designation_edit.text().strip(),
            "higher_formation": self._higher_formation_edit.text().strip(),
        }

        drag = QDrag(self._tree)
        mime = QMimeData()
        mime.setData(
            MILSYMB_MIME_TYPE,
            json.dumps(payload).encode("utf-8"),
        )
        drag.setMimeData(mime)

        # Use the current preview as drag-cursor image (48 px)
        pixmap = self._render_sidc_pixmap(sidc, 48)
        if pixmap:
            drag.setPixmap(pixmap)
            drag.setHotSpot(pixmap.rect().center())

        drag.exec_(Qt.CopyAction)
        LOG.debug("Drag started for SIDC=%s", sidc[:10])

    def _on_tree_context_menu(self, pos) -> None:
        """Show context menu on right-click over a catalog entry."""
        item = self._tree.itemAt(pos)
        if item is None:
            return
        entry: CatalogEntry | None = item.data(0, Qt.UserRole)
        if entry is None:
            return

        menu = QMenu(self._tree)

        act_edit = QAction("Edit Symbol…", menu)
        act_edit.triggered.connect(lambda: self._open_in_editor(entry))
        menu.addAction(act_edit)

        act_place = QAction("Place on Map", menu)
        act_place.triggered.connect(lambda: self._place_entry(entry))
        menu.addAction(act_place)

        menu.exec_(self._tree.viewport().mapToGlobal(pos))

    def _on_edit_clicked(self) -> None:
        """Open the Symbol Editor for the currently selected catalog entry."""
        if self._selected_entry is not None:
            self._open_in_editor(self._selected_entry)

    def _open_in_editor(self, entry: CatalogEntry) -> None:
        """Request that the symbol editor dock opens for *entry*."""
        identity: StandardIdentity = self._identity_combo.currentData()
        echelon: Echelon = self._echelon_combo.currentData()
        self.edit_in_editor_requested.emit({
            "entry": entry,
            "identity": identity,
            "echelon": echelon,
        })
        LOG.info("Edit-in-editor requested for %s", entry.name)

    def _place_entry(self, entry: CatalogEntry) -> None:
        """Quick-place the entry using current identity/echelon."""
        self._selected_entry = entry
        self._on_place_clicked()

    def _on_place_clicked(self) -> None:
        """Activate the map tool for symbol placement."""
        if self._selected_entry is None:
            return

        # Refuse if no symbol layers exist yet
        if self._layer_manager is None or not self._layer_manager.symbol_layers():
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Symbol Layer",
                "Please create a symbol layer first via the Layer Manager "
                "before placing a symbol on the map.",
            )
            return

        sidc = self._build_sidc()

        from .map_tool import SymbolPlacementTool

        canvas = self._iface.mapCanvas()
        self._map_tool = SymbolPlacementTool(
            canvas=canvas,
            sidc=sidc,
            designation=self._designation_edit.text().strip(),
            higher_formation=self._higher_formation_edit.text().strip(),
        )
        self._map_tool.symbol_placed.connect(self._on_symbol_placed)
        canvas.setMapTool(self._map_tool)
        LOG.info("Placement tool activated for SIDC=%s", sidc)

    def _on_symbol_placed(self, sym: MilSymbol) -> None:
        """Handle the symbol_placed signal from the map tool."""
        if self._layer_manager is not None:
            self._layer_manager.add_symbol(sym)
        self.symbol_placed.emit(sym)
        LOG.info("Symbol placed and added to layer: %s", sym.id)

    # ------------------------------------------------------------------
    # SIDC builder
    # ------------------------------------------------------------------

    def _build_sidc(self) -> str:
        """Compose a 20-char SIDC from the current entry + combo selections."""
        entry = self._selected_entry
        if entry is None:
            return "10031000000000000000"

        identity: StandardIdentity = self._identity_combo.currentData()
        echelon: Echelon = self._echelon_combo.currentData()

        return entry.sidc_template(
            identity=identity.value,
        )[:8] + echelon.value + entry.sidc_template()[10:]

    # ------------------------------------------------------------------
    # Preview rendering
    # ------------------------------------------------------------------

    def _update_preview(self) -> None:
        """Render and display the currently selected symbol."""
        sidc = self._build_sidc()
        self._sidc_label.setText(sidc)

        pixmap = self._render_sidc_pixmap(sidc, _PREVIEW_SIZE)
        if pixmap:
            self._preview_label.setPixmap(pixmap)
        else:
            self._preview_label.setText("(no preview)")

    def _render_sidc_pixmap(self, sidc: str, size: int) -> QPixmap | None:
        """Render an SIDC to a QPixmap."""
        try:
            svg_str = cached_svg(sidc)
        except ValueError:
            return None
        return self._svg_to_pixmap(svg_str, size)

    def _render_entry_icon(self, entry: CatalogEntry, size: int) -> QPixmap | None:
        """Render a small icon for a catalog entry."""
        identity: StandardIdentity = self._identity_combo.currentData()
        sidc = entry.sidc_template(identity=identity.value)
        try:
            svg_str = cached_svg(sidc)
        except ValueError:
            return None
        return self._svg_to_pixmap(svg_str, size)

    @staticmethod
    def _svg_to_pixmap(svg_str: str, size: int) -> QPixmap | None:
        """Convert an SVG string to a QPixmap preserving SVG aspect ratio.

        The rendered image fits inside a ``size × size`` bounding box
        (letterboxed / pillarboxed), so rectangular frames (e.g. APP-6
        Friend) appear proportionally correct.
        """
        try:
            from qgis.PyQt.QtSvg import QSvgRenderer
        except ImportError:
            return None

        renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
        if not renderer.isValid():
            return None

        # Determine natural SVG proportions
        natural = renderer.defaultSize()
        if natural.width() > 0 and natural.height() > 0:
            ratio = natural.width() / natural.height()
        else:
            ratio = 1.0

        # Scale to fit *size × size* preserving aspect ratio
        if ratio >= 1.0:           # wider-or-square: fit to width
            w = size
            h = max(1, round(size / ratio))
        else:                       # taller: fit to height
            h = size
            w = max(1, round(size * ratio))

        image = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        return QPixmap.fromImage(image)
