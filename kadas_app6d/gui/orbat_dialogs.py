# -*- coding: utf-8 -*-
"""
Dialogs for ORBAT unit creation and editing.

``UnitEditDialog``
    Modal dialog for creating / editing an :class:`OrbatUnit`.
    Used by both the ORBAT tree context menu and the "Add Unit" button.

``OrbatImportExportDialog``
    File-based import / export of a single :class:`Orbat` as JSON.
"""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt, QByteArray
from qgis.PyQt.QtGui import QImage, QPainter, QPixmap
from qgis.PyQt.QtCore import QRegExp
from qgis.PyQt.QtGui import QRegExpValidator
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from . import DARK_THEME_SS
from ..core.models import Orbat, OrbatUnit
from ..core.sidc import Echelon, HqTfDummy, StandardIdentity, Status, SymbolSet
from ..symbology.catalog_data import (
    SYMBOL_SET_NAMES,
    CatalogEntry,
    entries_by_symbol_set,
)
from ..symbology.renderer import cached_svg
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.orbat_dialogs")

_PREVIEW_SIZE = 80


# ======================================================================
# Helpers – identical to catalog_dock._svg_to_pixmap
# ======================================================================

def _svg_to_pixmap(svg_str: str, size: int) -> QPixmap | None:
    """Convert an SVG string to a QPixmap via QSvgRenderer."""
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


# ======================================================================
# UnitEditDialog
# ======================================================================

class UnitEditDialog(QDialog):
    """Create or edit an ORBAT unit.

    Parameters
    ----------
    unit : OrbatUnit or None
        Pass an existing unit to edit it, or *None* to create a new one.
    parent_unit : OrbatUnit or None
        The unit that will become the parent of the new unit.
    parent : QWidget or None
        Qt parent widget.
    """

    def __init__(
        self,
        unit: OrbatUnit | None = None,
        parent_unit: OrbatUnit | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._unit = unit or OrbatUnit()
        self._is_new = unit is None
        self._parent_unit = parent_unit

        self.setWindowTitle("New Unit" if self._is_new else "Edit Unit")
        self.setMinimumWidth(420)

        self._build_ui()
        self._populate_from_unit()
        self._update_preview()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.setStyleSheet(DARK_THEME_SS)

        # ---- Identity section ----
        id_group = QGroupBox("Unit Identity")
        id_layout = QFormLayout(id_group)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. 1st Battalion, 3rd Infantry")
        id_layout.addRow("Name:", self._name_edit)

        self._short_name_edit = QLineEdit()
        self._short_name_edit.setPlaceholderText("e.g. 1/3 Inf")
        id_layout.addRow("Short name:", self._short_name_edit)

        layout.addWidget(id_group)

        # ---- Symbology section ----
        sym_group = QGroupBox("Symbology (APP-6D)")
        sym_layout = QFormLayout(sym_group)

        # Identity combo
        self._identity_combo = QComboBox()
        for si in StandardIdentity:
            self._identity_combo.addItem(
                si.name.replace("_", " ").title(), si
            )
        self._identity_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Identity:", self._identity_combo)

        # Symbol set combo
        self._symbol_set_combo = QComboBox()
        for ss in SymbolSet:
            label = SYMBOL_SET_NAMES.get(ss.value, ss.name)
            self._symbol_set_combo.addItem(label, ss)
        self._symbol_set_combo.currentIndexChanged.connect(self._on_symbol_set_changed)
        sym_layout.addRow("Symbol Set:", self._symbol_set_combo)

        # Entity combo (populated dynamically)
        self._entity_combo = QComboBox()
        self._entity_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Entity:", self._entity_combo)

        # Echelon combo
        self._echelon_combo = QComboBox()
        for ech in Echelon:
            self._echelon_combo.addItem(
                ech.name.replace("_", " ").title(), ech
            )
        self._echelon_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Echelon:", self._echelon_combo)

        # HQ / TF / Dummy combo
        self._hqtf_combo = QComboBox()
        for h in HqTfDummy:
            self._hqtf_combo.addItem(
                h.name.replace("_", " ").title(), h
            )
        self._hqtf_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("HQ/TF/Dummy:", self._hqtf_combo)

        # Status combo
        self._status_combo = QComboBox()
        for st in Status:
            self._status_combo.addItem(st.name.title(), st)
        self._status_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Status:", self._status_combo)

        # Modifier 1 / Modifier 2  (2-char hex, preserved from original SIDC)
        hex2_validator = QRegExpValidator(QRegExp("[0-9A-Fa-f]{0,2}"))
        self._mod1_edit = QLineEdit("00")
        self._mod1_edit.setMaxLength(2)
        self._mod1_edit.setValidator(hex2_validator)
        self._mod1_edit.setPlaceholderText("00")
        self._mod1_edit.textChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Modifier 1:", self._mod1_edit)

        self._mod2_edit = QLineEdit("00")
        self._mod2_edit.setMaxLength(2)
        self._mod2_edit.setValidator(hex2_validator)
        self._mod2_edit.setPlaceholderText("00")
        self._mod2_edit.textChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Modifier 2:", self._mod2_edit)

        # Preview
        preview_row = QHBoxLayout()
        self._preview_label = QLabel()
        self._preview_label.setFixedSize(_PREVIEW_SIZE, _PREVIEW_SIZE)
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setStyleSheet(
            "QLabel { background: white; border: 1px solid #ccc; }"
        )
        preview_row.addStretch()
        preview_row.addWidget(self._preview_label)
        preview_row.addStretch()
        sym_layout.addRow(preview_row)

        self._sidc_label = QLabel("")
        self._sidc_label.setAlignment(Qt.AlignCenter)
        self._sidc_label.setStyleSheet("font-family: monospace; font-size: 11px; color: #666;")
        sym_layout.addRow(self._sidc_label)

        layout.addWidget(sym_group)

        # ---- Temporal section ----
        temp_group = QGroupBox("Temporal Validity (optional)")
        temp_layout = QFormLayout(temp_group)

        self._t_start_edit = QDateTimeEdit()
        self._t_start_edit.setCalendarPopup(True)
        self._t_start_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._t_start_check = self._make_optional_datetime(
            self._t_start_edit, temp_layout, "Start:"
        )

        self._t_end_edit = QDateTimeEdit()
        self._t_end_edit.setCalendarPopup(True)
        self._t_end_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._t_end_check = self._make_optional_datetime(
            self._t_end_edit, temp_layout, "End:"
        )

        layout.addWidget(temp_group)

        # ---- Buttons ----
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    @staticmethod
    def _make_optional_datetime(dt_edit, form_layout, label):
        """Add a row with a checkbox-enabled QDateTimeEdit."""
        from qgis.PyQt.QtWidgets import QCheckBox
        cb = QCheckBox()
        cb.setChecked(False)
        dt_edit.setEnabled(False)
        cb.toggled.connect(dt_edit.setEnabled)
        row = QHBoxLayout()
        row.addWidget(cb)
        row.addWidget(dt_edit, 1)
        form_layout.addRow(label, row)
        return cb

    # ------------------------------------------------------------------
    # Populate from existing unit
    # ------------------------------------------------------------------

    def _populate_from_unit(self) -> None:
        u = self._unit
        self._name_edit.setText(u.name)
        self._short_name_edit.setText(u.short_name)

        # Parse SIDC for field values
        from ..core.sidc import SIDC as SIDCClass
        try:
            sidc = SIDCClass.parse(u.sidc)
        except ValueError:
            sidc = SIDCClass()

        # Identity
        for i in range(self._identity_combo.count()):
            if self._identity_combo.itemData(i) == sidc.standard_identity:
                self._identity_combo.setCurrentIndex(i)
                break

        # Symbol set
        for i in range(self._symbol_set_combo.count()):
            if self._symbol_set_combo.itemData(i) == sidc.symbol_set:
                self._symbol_set_combo.setCurrentIndex(i)
                break

        # Populate entities for the current symbol set, then select
        self._refresh_entity_combo()
        entity_code = sidc.entity
        for i in range(self._entity_combo.count()):
            data = self._entity_combo.itemData(i)
            if data and data.entity_code == entity_code:
                self._entity_combo.setCurrentIndex(i)
                break

        # Echelon
        for i in range(self._echelon_combo.count()):
            if self._echelon_combo.itemData(i).value == sidc.amplifier:
                self._echelon_combo.setCurrentIndex(i)
                break

        # HQ/TF/Dummy
        for i in range(self._hqtf_combo.count()):
            if self._hqtf_combo.itemData(i) == sidc.hq_tf_dummy:
                self._hqtf_combo.setCurrentIndex(i)
                break

        # Status
        for i in range(self._status_combo.count()):
            if self._status_combo.itemData(i) == sidc.status:
                self._status_combo.setCurrentIndex(i)
                break

        # Modifiers – always taken from the original SIDC, never from catalog
        self._mod1_edit.setText(sidc.modifier1 or "00")
        self._mod2_edit.setText(sidc.modifier2 or "00")

        # Temporal
        if u.temporal.start:
            from qgis.PyQt.QtCore import QDateTime
            self._t_start_check.setChecked(True)
            self._t_start_edit.setDateTime(
                QDateTime.fromString(u.temporal.start, Qt.ISODate)
            )
        if u.temporal.end:
            from qgis.PyQt.QtCore import QDateTime
            self._t_end_check.setChecked(True)
            self._t_end_edit.setDateTime(
                QDateTime.fromString(u.temporal.end, Qt.ISODate)
            )

    # ------------------------------------------------------------------
    # Entity combo refresh
    # ------------------------------------------------------------------

    def _on_symbol_set_changed(self, _idx: int) -> None:
        self._refresh_entity_combo()
        self._on_sym_changed()

    def _refresh_entity_combo(self) -> None:
        ss: SymbolSet = self._symbol_set_combo.currentData()
        self._entity_combo.blockSignals(True)
        self._entity_combo.clear()

        # Generic fallback
        self._entity_combo.addItem("(generic)", None)

        entries = entries_by_symbol_set(ss.value)
        for entry in entries:
            self._entity_combo.addItem(entry.name, entry)

        self._entity_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # SIDC builder & preview
    # ------------------------------------------------------------------

    def _build_sidc(self) -> str:
        identity: StandardIdentity = self._identity_combo.currentData()
        ss: SymbolSet = self._symbol_set_combo.currentData()
        echelon: Echelon = self._echelon_combo.currentData()
        hqtf: HqTfDummy = self._hqtf_combo.currentData()
        status: Status = self._status_combo.currentData()

        entry: CatalogEntry | None = self._entity_combo.currentData()
        entity_code = entry.entity_code if entry else "000000"
        # Use the modifier fields (populated from original SIDC or set by user)
        raw_m1 = self._mod1_edit.text().strip().upper().zfill(2)
        raw_m2 = self._mod2_edit.text().strip().upper().zfill(2)
        m1 = raw_m1 if len(raw_m1) == 2 else "00"
        m2 = raw_m2 if len(raw_m2) == 2 else "00"

        return (
            f"10"                           # version
            f"0"                            # context = Reality
            f"{identity.value}"
            f"{ss.value}"
            f"{status.value}"
            f"{hqtf.value}"
            f"{echelon.value}"
            f"{entity_code}"
            f"{m1}"                         # modifier 1
            f"{m2}"                         # modifier 2
        )

    def _on_sym_changed(self, _idx: int = 0) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        sidc = self._build_sidc()
        self._sidc_label.setText(sidc)
        try:
            svg = cached_svg(sidc)
            pm = _svg_to_pixmap(svg, _PREVIEW_SIZE)
            if pm:
                self._preview_label.setPixmap(pm)
            else:
                self._preview_label.setText("?")
        except ValueError:
            self._preview_label.setText("?")

    # ------------------------------------------------------------------
    # Accept
    # ------------------------------------------------------------------

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Unit name is required.")
            return

        self._unit.name = name
        self._unit.short_name = self._short_name_edit.text().strip()
        self._unit.sidc = self._build_sidc()

        if self._is_new and self._parent_unit is not None:
            self._unit.parent_id = self._parent_unit.id

        # Temporal
        if self._t_start_check.isChecked():
            self._unit.temporal.start = (
                self._t_start_edit.dateTime().toString(Qt.ISODate)
            )
        else:
            self._unit.temporal.start = ""
        if self._t_end_check.isChecked():
            self._unit.temporal.end = (
                self._t_end_edit.dateTime().toString(Qt.ISODate)
            )
        else:
            self._unit.temporal.end = None

        self.accept()

    # ------------------------------------------------------------------
    # Public result
    # ------------------------------------------------------------------

    def get_unit(self) -> OrbatUnit:
        """Return the created/edited unit (only meaningful after accept)."""
        return self._unit


# ======================================================================
# Import / Export helpers (used from the dock toolbar)
# ======================================================================

def export_orbat_dialog(orbat: Orbat, parent: QWidget | None = None) -> str | None:
    """Show a Save-As dialog and write the ORBAT JSON.  Returns path or None."""
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "Export ORBAT",
        f"{orbat.name}.orbat.json",
        "ORBAT JSON (*.orbat.json);;All files (*)",
    )
    if not path:
        return None
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(orbat.to_json())
    LOG.info("ORBAT exported to %s", path)
    return path


def import_orbat_dialog(parent: QWidget | None = None) -> Orbat | None:
    """Show an Open dialog and parse an ORBAT JSON.  Returns Orbat or None."""
    path, _ = QFileDialog.getOpenFileName(
        parent,
        "Import ORBAT",
        "",
        "ORBAT JSON (*.orbat.json *.json);;All files (*)",
    )
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as fh:
        orbat = Orbat.from_json(fh.read())
    LOG.info("ORBAT imported from %s (%d units)", path, len(orbat.units))
    return orbat
