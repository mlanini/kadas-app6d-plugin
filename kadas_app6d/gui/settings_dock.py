# -*- coding: utf-8 -*-
"""
Settings dock widget – plugin configuration and project persistence.

Sections
--------
1. **Symbol Server** – status, port, restart button
2. **Defaults** – default identity, echelon, status
3. **Project I/O** – save / load MilSymbProject JSON
4. **About** – version, links
"""

from __future__ import annotations

from typing import Optional

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import DARK_THEME_SS
from ..core.models import MilSymbProject
from ..core.sidc import Echelon, StandardIdentity, Status
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.settings_dock")


# ======================================================================
# SettingsDockWidget
# ======================================================================

class SettingsDockWidget(QDockWidget):
    """Plugin settings and project save/load dock.

    Parameters
    ----------
    iface
        ``KadasPluginInterface`` reference.
    action : QAction
        The toggle action that controls visibility.
    parent : QWidget or None
        Parent widget (usually the main window).
    """

    project_loaded = pyqtSignal(object)   # MilSymbProject (kept for back-compat)
    project_saved = pyqtSignal(str)       # file path (kept for back-compat)
    symbol_size_changed = pyqtSignal(int) # new size in pixels
    show_text_modifiers_changed = pyqtSignal(bool) # toggle to show extended text on map
    temporal_filtering_toggled = pyqtSignal(bool)  # True = enabled
    temporal_fit_to_data_requested = pyqtSignal(float)  # step_hours

    def __init__(self, iface, action=None, parent=None):
        super().__init__("MilSymb Settings", parent)
        self._iface = iface
        self._action = action
        self._project_data: Optional[MilSymbProject] = None
        self._symbol_server = None
        self._layer_manager = None

        self._build_ui()

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

    def set_symbol_server(self, srv) -> None:
        self._symbol_server = srv
        self._update_server_status()

    def set_layer_manager(self, mgr) -> None:
        self._layer_manager = mgr

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        container = QWidget()
        container.setStyleSheet(DARK_THEME_SS)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # ---- Symbol Server group ----
        srv_group = QGroupBox("Symbol Server")
        srv_layout = QFormLayout(srv_group)

        self._server_status_lbl = QLabel("–")
        srv_layout.addRow("Status:", self._server_status_lbl)

        self._server_port_lbl = QLabel("–")
        srv_layout.addRow("Port:", self._server_port_lbl)

        self._restart_btn = QPushButton("Restart Server")
        self._restart_btn.clicked.connect(self._on_restart_server)
        srv_layout.addRow(self._restart_btn)

        layout.addWidget(srv_group)

        # ---- Defaults group ----
        def_group = QGroupBox("Defaults")
        def_layout = QFormLayout(def_group)

        self._def_identity_combo = QComboBox()
        for si in StandardIdentity:
            self._def_identity_combo.addItem(si.name.replace("_", " ").title(), si)
        self._def_identity_combo.setCurrentIndex(3)  # FRIEND
        def_layout.addRow("Identity:", self._def_identity_combo)

        self._def_echelon_combo = QComboBox()
        for ech in Echelon:
            self._def_echelon_combo.addItem(ech.name.replace("_", " ").title(), ech)
        def_layout.addRow("Echelon:", self._def_echelon_combo)

        self._def_status_combo = QComboBox()
        for st in Status:
            self._def_status_combo.addItem(st.name.title(), st)
        def_layout.addRow("Status:", self._def_status_combo)

        self._symbol_size_spin = QSlider(Qt.Horizontal)
        self._symbol_size_spin.setMinimum(16)
        self._symbol_size_spin.setMaximum(256)
        self._symbol_size_spin.setValue(64)
        self._symbol_size_spin.valueChanged.connect(self.symbol_size_changed)
        def_layout.addRow("Symbol size:", self._symbol_size_spin)

        self._show_text_modifiers_cb = QCheckBox("Display text fields around symbols")
        self._show_text_modifiers_cb.setToolTip("Show extra text fields (quantity, speed, evaluation, etc.) in map symbol drawing.")
        self._show_text_modifiers_cb.setChecked(False)
        self._show_text_modifiers_cb.toggled.connect(self.show_text_modifiers_changed.emit)
        def_layout.addRow(self._show_text_modifiers_cb)

        layout.addWidget(def_group)

        # ---- Temporal group ----
        temp_group = QGroupBox("Temporal Controller")
        temp_layout = QFormLayout(temp_group)

        self._temporal_enable_cb = QCheckBox("Enable temporal filtering")
        self._temporal_enable_cb.setChecked(True)
        self._temporal_enable_cb.setToolTip(
            "When checked, symbols are shown/hidden according to the QGIS "
            "Temporal Controller current time window."
        )
        self._temporal_enable_cb.toggled.connect(self.temporal_filtering_toggled)
        temp_layout.addRow(self._temporal_enable_cb)

        self._temporal_status_lbl = QLabel("–")
        self._temporal_status_lbl.setWordWrap(True)
        temp_layout.addRow("Current range:", self._temporal_status_lbl)

        self._temporal_step_spin = QDoubleSpinBox()
        self._temporal_step_spin.setMinimum(0.1)
        self._temporal_step_spin.setMaximum(8760.0)  # 1 year
        self._temporal_step_spin.setSingleStep(1.0)
        self._temporal_step_spin.setValue(1.0)
        self._temporal_step_spin.setSuffix(" h")
        self._temporal_step_spin.setToolTip(
            "Frame duration (step) to set on the Temporal Controller "
            "when fitting the range to the data."
        )
        temp_layout.addRow("Frame step:", self._temporal_step_spin)

        self._temporal_fit_btn = QPushButton("Fit TC range to data")
        self._temporal_fit_btn.setToolTip(
            "Set the Temporal Controller range and step from the temporal "
            "extents of all symbols in the current project."
        )
        self._temporal_fit_btn.clicked.connect(
            lambda: self.temporal_fit_to_data_requested.emit(
                self._temporal_step_spin.value()
            )
        )
        temp_layout.addRow(self._temporal_fit_btn)

        layout.addWidget(temp_group)

        # ---- Spacer ----
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        self.setWidget(scroll)

    # ------------------------------------------------------------------
    # Server management
    # ------------------------------------------------------------------

    def _update_server_status(self) -> None:
        if self._symbol_server is not None:
            self._server_status_lbl.setText(
                '<span style="color:green;">Running</span>'
            )
            self._server_port_lbl.setText(str(self._symbol_server.port))
        else:
            self._server_status_lbl.setText(
                '<span style="color:red;">Stopped</span>'
            )
            self._server_port_lbl.setText("–")

    def _on_restart_server(self) -> None:
        """Stop and restart the symbol server."""
        if self._symbol_server is not None:
            self._symbol_server.stop()
            self._symbol_server.start()
            LOG.info("Symbol server restarted on port %d",
                     self._symbol_server.port)
        self._update_server_status()

    # ------------------------------------------------------------------
    # Public accessors for defaults
    # ------------------------------------------------------------------

    @property
    def default_identity(self) -> StandardIdentity:
        return self._def_identity_combo.currentData()

    @property
    def default_echelon(self) -> Echelon:
        return self._def_echelon_combo.currentData()

    @property
    def default_status(self) -> Status:
        return self._def_status_combo.currentData()

    @property
    def symbol_size(self) -> int:
        return self._symbol_size_spin.value()

    @property
    def show_text_modifiers(self) -> bool:
        return self._show_text_modifiers_cb.isChecked()

    def update_temporal_status(self, label: str) -> None:
        """Update the temporal range status label shown in the settings dock."""
        self._temporal_status_lbl.setText(label if label else "–")

    def set_temporal_filtering_enabled(self, enabled: bool) -> None:
        """Sync the enable checkbox without emitting the signal."""
        self._temporal_enable_cb.blockSignals(True)
        self._temporal_enable_cb.setChecked(enabled)
        self._temporal_enable_cb.blockSignals(False)
