# -*- coding: utf-8 -*-
"""
Layer management dock widget – add, rename, delete symbol layers and
export data per-layer or as a single multi-layer JSON file.

Integrated into the main plugin panel as a collapsible group at the top
of the catalog dock, or as a standalone dock accessible from the ribbon.
"""

from __future__ import annotations

import html
import json
import os
import zipfile
from typing import List, Optional

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import DARK_THEME_SS
from ..core.models import MilSymbProject
from ..core.utils import milsymb_data_dir
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.layer_manager_dock")


class LayerManagerDockWidget(QDockWidget):
    """Dock for managing multiple MilSymb symbol layers.

    Features
    --------
    * Layer selector (QComboBox) – pick the active layer
    * Add / Rename / Delete buttons
    * Export panel – single multi-layer JSON **or** one file per layer

    Signals
    -------
    active_layer_changed(str)
        Emitted with the ``SymbolLayer.id`` when the user picks a
        different layer in the combo box.
    """

    active_layer_changed = pyqtSignal(str)

    def __init__(self, iface=None, action=None, parent=None):
        super().__init__("Layer Manager", parent)
        self._iface = iface
        self._action = action

        self._project_data: Optional[MilSymbProject] = None
        self._layer_manager = None   # set externally

        self._build_ui()

    # ------------------------------------------------------------------
    # Dock lifecycle
    # ------------------------------------------------------------------

    def showEvent(self, event):  # noqa: N802
        """Refresh the combo whenever the dock becomes visible."""
        super().showEvent(event)
        self._refresh_combo()

    def closeEvent(self, event):  # noqa: N802
        """Uncheck the ribbon action when the dock is closed by the user."""
        if self._action is not None:
            self._action.setChecked(False)
        super().closeEvent(event)

    # External bindings
    # ------------------------------------------------------------------

    def set_project_data(self, proj: MilSymbProject) -> None:
        self._project_data = proj
        self._refresh_combo()

    def set_layer_manager(self, mgr) -> None:
        self._layer_manager = mgr
        if mgr is not None:
            mgr.layer_added.connect(self._on_layer_added)
            mgr.layer_removed.connect(self._on_layer_removed)
            mgr.layer_renamed.connect(self._on_layer_renamed)
        self._refresh_combo()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        container = QWidget()
        container.setStyleSheet(DARK_THEME_SS)
        root = QVBoxLayout(container)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # ---- Layer selector group ----
        grp = QGroupBox("Symbol Layers")
        grp_layout = QVBoxLayout(grp)

        # Combo + buttons row
        sel_row = QHBoxLayout()
        self._layer_combo = QComboBox()
        self._layer_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self._layer_combo.currentIndexChanged.connect(self._on_combo_changed)
        sel_row.addWidget(self._layer_combo, 1)

        self._add_btn = QToolButton()
        self._add_btn.setText("+")
        self._add_btn.setToolTip("Add layer")
        self._add_btn.clicked.connect(self._on_add)
        sel_row.addWidget(self._add_btn)

        self._rename_btn = QToolButton()
        self._rename_btn.setText("Rename")
        self._rename_btn.setToolTip("Rename layer")
        self._rename_btn.clicked.connect(self._on_rename)
        self._rename_btn.setEnabled(False)
        sel_row.addWidget(self._rename_btn)

        self._del_btn = QToolButton()
        self._del_btn.setText("−")
        self._del_btn.setToolTip("Delete layer")
        self._del_btn.clicked.connect(self._on_delete)
        self._del_btn.setEnabled(False)
        sel_row.addWidget(self._del_btn)

        grp_layout.addLayout(sel_row)

        # Info label
        self._info_lbl = QLabel("")
        self._info_lbl.setWordWrap(True)
        grp_layout.addWidget(self._info_lbl)

        root.addWidget(grp)

        # ---- APP-6(D) JSON group (export + import) ----
        json_grp = QGroupBox("APP-6(D) JSON")
        json_layout = QVBoxLayout(json_grp)

        self._export_all_btn = QPushButton("Export all layers (single file)")
        self._export_all_btn.clicked.connect(self._on_export_all)
        json_layout.addWidget(self._export_all_btn)

        self._export_each_btn = QPushButton("Export each layer separately")
        self._export_each_btn.clicked.connect(self._on_export_each)
        json_layout.addWidget(self._export_each_btn)

        self._export_current_btn = QPushButton("Export current layer")
        self._export_current_btn.clicked.connect(self._on_export_current)
        json_layout.addWidget(self._export_current_btn)

        self._import_file_btn = QPushButton("Import layers from JSON file\u2026")
        self._import_file_btn.setToolTip(
            "Import symbol layers from a MilSymb JSON file and append them "
            "to the current project."
        )
        self._import_file_btn.clicked.connect(self._on_import_from_file)
        json_layout.addWidget(self._import_file_btn)

        self._import_folder_btn = QPushButton("Import from data folder\u2026")
        self._import_folder_btn.setToolTip(
            "Browse and pick a JSON file from the MilSymb data folder "
            "(bundled or previously saved files)."
        )
        self._import_folder_btn.clicked.connect(self._on_import_from_data_folder)
        json_layout.addWidget(self._import_folder_btn)

        root.addWidget(json_grp)

        # ---- KMZ / KML group ----
        kmz_grp = QGroupBox("KMZ / KML")
        kmz_layout = QVBoxLayout(kmz_grp)

        self._kmz_import_btn = QPushButton("Import .kmz / .kml as new layer…")
        self._kmz_import_btn.setToolTip(
            "Import a KMZ or KML file and create a new symbol layer. "
            "Placemarks with an APP6D_SIDC extended-data field are imported "
            "with full fidelity; generic placemarks use a default SIDC."
        )
        self._kmz_import_btn.clicked.connect(self._on_kmz_import)
        kmz_layout.addWidget(self._kmz_import_btn)
        self._kmz_export_all_btn = QPushButton("Export all layers as .kmz\u2026")
        self._kmz_export_all_btn.setToolTip(
            "Export all layers into a single KMZ file with embedded PNG icons. "
            "Each layer becomes a Folder; each symbol becomes a Placemark with "
            "APP-6D SIDC stored in ExtendedData for lossless round-tripping."
        )
        self._kmz_export_all_btn.clicked.connect(self._on_export_all_kmz)
        kmz_layout.addWidget(self._kmz_export_all_btn)
        self._kmz_export_btn = QPushButton("Export current layer as .kmz…")
        self._kmz_export_btn.setToolTip(
            "Export the currently selected layer to a KMZ file. "
            "Each symbol becomes a Placemark with inline PNG icon and "
            "APP-6D SIDC stored in ExtendedData for lossless round-tripping."
        )
        self._kmz_export_btn.clicked.connect(self._on_kmz_export)
        kmz_layout.addWidget(self._kmz_export_btn)

        root.addWidget(kmz_grp)

        root.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        self.setWidget(scroll)

    # ------------------------------------------------------------------
    # Combo helpers
    # ------------------------------------------------------------------

    def _refresh_combo(self) -> None:
        """Rebuild the combo box from the project layers list."""
        self._layer_combo.blockSignals(True)
        self._layer_combo.clear()
        if self._project_data is None:
            self._layer_combo.blockSignals(False)
            return
        active_id = None
        if self._layer_manager is not None:
            active_id = self._layer_manager.active_layer_id
        sel_idx = 0
        for i, sl in enumerate(self._project_data.layers):
            label = f"{sl.name}  ({len(sl.symbols)} sym)"
            self._layer_combo.addItem(label, sl.id)
            if sl.id == active_id:
                sel_idx = i
        self._layer_combo.setCurrentIndex(sel_idx)
        self._layer_combo.blockSignals(False)
        has_layers = self._layer_combo.count() > 0
        self._rename_btn.setEnabled(has_layers)
        self._del_btn.setEnabled(has_layers)
        self._update_info()

    def _current_layer_id(self) -> str | None:
        idx = self._layer_combo.currentIndex()
        if idx < 0:
            return None
        return self._layer_combo.itemData(idx)

    def _update_info(self) -> None:
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            self._info_lbl.setText("")
            return
        sl = self._project_data.layer_by_id(lid)
        if sl is None:
            self._info_lbl.setText("")
            return
        self._info_lbl.setText(f"Symbols: {len(sl.symbols)}")

    # ------------------------------------------------------------------
    # Slots – combo
    # ------------------------------------------------------------------

    def _on_combo_changed(self, idx: int) -> None:
        lid = self._current_layer_id()
        if lid is None:
            return
        if self._layer_manager is not None:
            self._layer_manager.set_active_layer(lid)
        self.active_layer_changed.emit(lid)
        self._update_info()

    # ------------------------------------------------------------------
    # Slots – add / rename / delete
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        name, ok = QInputDialog.getText(
            self, "New Layer", "Layer name:", text="New Layer",
        )
        if not ok or not name.strip():
            return
        if self._layer_manager is not None:
            sl = self._layer_manager.add_layer(name.strip())
            self._layer_manager.set_active_layer(sl.id)
        elif self._project_data is not None:
            self._project_data.add_layer(name.strip())
        self._refresh_combo()

    def _on_rename(self) -> None:
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            return
        sl = self._project_data.layer_by_id(lid)
        if sl is None:
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Layer", "New name:", text=sl.name,
        )
        if not ok or not new_name.strip():
            return
        if self._layer_manager is not None:
            self._layer_manager.rename_layer(lid, new_name.strip())
        else:
            self._project_data.rename_layer(lid, new_name.strip())
        self._refresh_combo()

    def _on_delete(self) -> None:
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            return
        if len(self._project_data.layers) <= 1:
            QMessageBox.information(
                self, "Cannot delete",
                "At least one symbol layer must exist.",
            )
            return
        sl = self._project_data.layer_by_id(lid)
        name = sl.name if sl else "?"
        btn = QMessageBox.question(
            self, "Delete Layer",
            f"Delete layer \"{name}\" and all its {len(sl.symbols)} symbol(s)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if btn != QMessageBox.Yes:
            return
        if self._layer_manager is not None:
            self._layer_manager.remove_layer(lid)
        else:
            self._project_data.remove_layer(lid)
        self._refresh_combo()

    # ------------------------------------------------------------------
    # Slots – layer_manager signals
    # ------------------------------------------------------------------

    def _on_layer_added(self, _lid: str) -> None:
        self._refresh_combo()

    def _on_layer_removed(self, _lid: str) -> None:
        self._refresh_combo()

    def _on_layer_renamed(self, _lid: str, _name: str) -> None:
        self._refresh_combo()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_export_all(self) -> None:
        """Export all layers into a single JSON file."""
        if self._project_data is None:
            return
        default_dir = milsymb_data_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export all layers",
            os.path.join(default_dir, "milsymb_all_layers.json"),
            "MilSymb JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._project_data.to_json())
            n_sym = len(self._project_data.symbols)
            n_lyr = len(self._project_data.layers)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {n_lyr} layer(s) with {n_sym} symbol(s) to\n{path}",
            )
            LOG.info("Exported all layers to %s", path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    def _on_export_each(self) -> None:
        """Export each layer as a separate JSON file into a chosen folder."""
        if self._project_data is None:
            return
        default_dir = milsymb_data_dir()
        folder = QFileDialog.getExistingDirectory(
            self, "Choose export folder", default_dir,
        )
        if not folder:
            return
        try:
            exported = 0
            for sl in self._project_data.layers:
                safe_name = sl.name.replace(" ", "_").replace("/", "_")
                fname = f"milsymb_layer_{safe_name}.json"
                path = os.path.join(folder, fname)
                data = self._project_data.layer_to_json(sl.id)
                if data is None:
                    continue
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(data)
                exported += 1
                LOG.info("Exported layer '%s' to %s", sl.name, path)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {exported} layer file(s) to\n{folder}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    # ------------------------------------------------------------------
    # KMZ import / export
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Import (JSON)
    # ------------------------------------------------------------------

    def _import_project(self, imported: MilSymbProject) -> int:
        """Merge *imported* layers into the current project.

        Returns the number of layers actually added.
        Existing layer names get a numeric suffix to avoid duplicates.
        """
        if self._project_data is None:
            return 0

        existing_names = {sl.name for sl in self._project_data.layers}
        added = 0
        first_new_id: str | None = None

        for sl in imported.layers:
            # Resolve name conflict
            name = sl.name
            if name in existing_names:
                base = name
                counter = 2
                while name in existing_names:
                    name = f"{base} ({counter})"
                    counter += 1
                sl.name = name
            existing_names.add(sl.name)

            if self._layer_manager is not None:
                self._layer_manager.import_layer(sl)
            else:
                self._project_data.layers.append(sl)

            if first_new_id is None:
                first_new_id = sl.id
            added += 1

        self._refresh_combo()

        # Switch to the first newly imported layer
        if first_new_id is not None and self._layer_manager is not None:
            self._layer_manager.set_active_layer(first_new_id)

        return added

    def _on_import_from_file(self) -> None:
        """Browse filesystem and import layers from a MilSymb JSON file."""
        default_dir = milsymb_data_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import layers from JSON file",
            default_dir,
            "MilSymb JSON (*.json);;All files (*)",
        )
        if not path:
            return
        self._import_json_file(path)

    def _on_import_from_data_folder(self) -> None:
        """Browse the MilSymb data folder for JSON files to import."""
        data_dir = milsymb_data_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import layers from data folder",
            data_dir,
            "MilSymb JSON (*.json);;All files (*)",
        )
        if not path:
            return
        self._import_json_file(path)

    def _import_json_file(self, path: str) -> None:
        """Parse *path* as a MilSymb JSON file and merge its layers."""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            imported = MilSymbProject.from_json(text)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            QMessageBox.critical(
                self, "Import error",
                f"Could not read {os.path.basename(path)}:\n{exc}",
            )
            return

        if not imported.layers:
            QMessageBox.information(self, "Import", "No layers found in the file.")
            return

        added = self._import_project(imported)
        QMessageBox.information(
            self, "Import complete",
            f"Imported {added} layer(s) from\n{path}",
        )
        LOG.info("Imported %d layer(s) from %s", added, path)

    def _on_kmz_import(self) -> None:
        """Import a .kmz or .kml file and create a new layer."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import KMZ / KML",
            str(milsymb_data_dir()),
            "KMZ / KML (*.kmz *.kml);;All files (*)",
        )
        if not path:
            return
        try:
            from ..core.kmz_io import import_kmz
            layer_name, symbols = import_kmz(path)
        except Exception as exc:
            QMessageBox.critical(self, "Import error",
                                 f"Failed to read KMZ/KML file:\n{exc}")
            return

        if not symbols:
            QMessageBox.information(self, "Import", "No Point placemarks found in the file.")
            return

        if self._layer_manager is not None:
            new_sl = self._layer_manager.add_layer(layer_name)
            for sym in symbols:
                self._layer_manager.add_symbol(sym, layer_id=new_sl.id)
            self._layer_manager.set_active_layer(new_sl.id)
        elif self._project_data is not None:
            new_sl = self._project_data.add_layer(layer_name)
            for sym in symbols:
                new_sl.symbols.append(sym)
        else:
            QMessageBox.warning(self, "Import error", "No layer manager available.")
            return

        self._refresh_combo()
        QMessageBox.information(
            self, "Import complete",
            f"Imported {len(symbols)} symbol(s) from\n"
            f"{os.path.basename(path)}\n"
            f"into new layer \u201c{layer_name}\u201d.",
        )
        LOG.info("KMZ: imported %d symbols from %s into layer '%s'",
                 len(symbols), path, layer_name)

    def _on_kmz_export(self) -> None:
        """Export the current layer to a .kmz file."""
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            return
        sl = self._project_data.layer_by_id(lid)
        if sl is None:
            return

        safe_name = sl.name.replace(" ", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export layer \"{sl.name}\" as KMZ",
            os.path.join(str(milsymb_data_dir()), f"{safe_name}.kmz"),
            "KMZ (*.kmz);;KML (*.kml);;All files (*)",
        )
        if not path:
            return

        try:
            from ..core.kmz_io import export_kmz
            # If the user chose .kml, write unzipped KML instead
            if path.lower().endswith(".kml"):
                import zipfile as _zf
                tmp = path + "._tmp.kmz"
                export_kmz(sl.symbols, sl.name, tmp, render_icons=False)
                with _zf.ZipFile(tmp, "r") as z:
                    with open(path, "wb") as fh:
                        fh.write(z.read("doc.kml"))
                os.remove(tmp)
            else:
                export_kmz(sl.symbols, sl.name, path)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {len(sl.symbols)} symbol(s) from layer "
                f"\"{sl.name}\" to\n{path}",
            )
            LOG.info("KMZ: exported layer '%s' (%d syms) to %s",
                     sl.name, len(sl.symbols), path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    def _on_export_current(self) -> None:
        """Export only the currently selected layer."""
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            return
        sl = self._project_data.layer_by_id(lid)
        if sl is None:
            return
        default_dir = milsymb_data_dir()
        safe_name = sl.name.replace(" ", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export layer \"{sl.name}\"",
            os.path.join(default_dir, f"milsymb_layer_{safe_name}.json"),
            "MilSymb JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            data = self._project_data.layer_to_json(lid)
            if data is None:
                QMessageBox.warning(self, "Error", "Layer data not found.")
                return
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(data)
            QMessageBox.information(
                self, "Export complete",
                f"Exported layer \"{sl.name}\" ({len(sl.symbols)} symbols) to\n{path}",
            )
            LOG.info("Exported layer '%s' to %s", sl.name, path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    # ------------------------------------------------------------------
    # KMZ – all-layers export
    # ------------------------------------------------------------------

    def _on_export_all_kmz(self) -> None:
        """Export all layers as a single KMZ file with embedded PNG icons."""
        if self._project_data is None:
            return
        default_dir = milsymb_data_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export all layers as KMZ",
            os.path.join(default_dir, "milsymb_all_layers.kmz"),
            "KMZ (*.kmz);;All files (*)",
        )
        if not path:
            return
        layers = self._project_data.layers
        # Render one PNG icon per unique SIDC
        size = 64
        icon_files: dict = {}
        png_data: dict = {}
        for sl in layers:
            for sym in sl.symbols:
                sidc = sym.sidc
                if sidc not in icon_files:
                    png = self._sidc_to_png_bytes(sidc, size)
                    if png is not None:
                        arc = f"icons/{sidc}.png"
                        icon_files[sidc] = arc
                        png_data[sidc] = png
        kml_str = self._build_kml(layers, icon_files)
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("doc.kml", kml_str.encode("utf-8"))
                for sidc, data in png_data.items():
                    zf.writestr(f"icons/{sidc}.png", data)
            n_sym = sum(len(sl.symbols) for sl in layers)
            n_lyr = len(layers)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {n_lyr} layer(s) with {n_sym} symbol(s) to\n{path}",
            )
            LOG.info("KMZ: exported all layers (%d sym) to %s", n_sym, path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    @staticmethod
    def _sidc_to_png_bytes(sidc: str, size: int = 64) -> Optional[bytes]:
        """Render *sidc* as a PNG byte-string via QSvgRenderer, or None on failure."""
        try:
            from qgis.PyQt.QtCore import QByteArray, QBuffer, QIODevice
            from qgis.PyQt.QtGui import QImage, QPainter
            from qgis.PyQt.QtSvg import QSvgRenderer
            from ..symbology.milsymbol_engine import MilsymbolEngine

            engine = MilsymbolEngine.instance()
            svg_str = engine.render_svg(sidc, size=size)
            if not svg_str:
                return None
            renderer = QSvgRenderer(QByteArray(svg_str.encode()))
            image = QImage(size, size, QImage.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
            buf = QBuffer()
            buf.open(QIODevice.WriteOnly)
            image.save(buf, "PNG")
            return bytes(buf.data())
        except Exception:
            return None

    @staticmethod
    def _build_kml(layers, icon_files: dict) -> str:
        """Build a KML string for the given layers.

        Parameters
        ----------
        layers:
            Iterable of ``SymbolLayer`` objects.
        icon_files : dict
            Mapping ``sidc -> 'icons/<sidc>.png'`` for icons successfully
            rendered.  Used to set ``<href>`` inside each ``<IconStyle>``.
        """
        lines: List[str] = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
        lines.append('  <Document>')

        for sl in layers:
            lines.append('    <Folder>')
            lines.append(f'      <name>{html.escape(sl.name)}</name>')
            for sym in sl.symbols:
                if sym.longitude == 0.0 and sym.latitude == 0.0:
                    continue
                name = html.escape(sym.designation or sym.sidc[:10])
                lines.append('      <Placemark>')
                lines.append(f'        <name>{name}</name>')
                sidc_val = sym.sidc
                icon_href = icon_files.get(sidc_val)
                if icon_href:
                    lines.append('        <Style>')
                    lines.append('          <IconStyle>')
                    lines.append(f'            <Icon><href>{icon_href}</href></Icon>')
                    lines.append('          </IconStyle>')
                    lines.append('        </Style>')
                lines.append('        <Point>')
                lines.append(
                    f'          <coordinates>{sym.longitude},{sym.latitude},0</coordinates>'
                )
                lines.append('        </Point>')
                lines.append('        <ExtendedData>')
                lines.append(
                    f'          <Data name="APP6D_SIDC"><value>{sidc_val}</value></Data>'
                )
                if sym.designation:
                    lines.append(
                        f'          <Data name="designation">'
                        f'<value>{html.escape(sym.designation)}</value></Data>'
                    )
                if sym.higher_formation:
                    lines.append(
                        f'          <Data name="higher_formation">'
                        f'<value>{html.escape(sym.higher_formation)}</value></Data>'
                    )
                lines.append('        </ExtendedData>')
                lines.append('      </Placemark>')
            lines.append('    </Folder>')

        lines.append('  </Document>')
        lines.append('</kml>')
        return "\n".join(lines)
