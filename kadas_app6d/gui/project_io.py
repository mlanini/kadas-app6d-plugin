# -*- coding: utf-8 -*-
"""
Project persistence – automatic save/load of MilSymb data with the
QGIS/KADAS project (.qgz).

Strategy
--------
* On ``QgsProject.writeProject`` → write ``MilSymbProject`` JSON into a
  dedicated file next to the .qgz (``<project>.milsymb.json``), and
  store the path as a project variable.
* On ``QgsProject.readProject``  → look for the sidecar file and reload
  the data.
* Also supports explicit save/load via the Settings dock.

This keeps the military data **outside** the .qgz XML to avoid bloating
the native project file, while still providing automatic persistence.
"""

from __future__ import annotations

import os

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import QgsProject

from ..core.models import MilSymbProject
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.project_io")

_PROJECT_KEY = "kadas_milsymb/data_path"


class ProjectIO(QObject):
    """Handles automatic save/load tied to QGIS project signals.

    Parameters
    ----------
    project_data : MilSymbProject
        Reference to the live project data model.
    parent : QObject or None
        Qt parent.
    """

    # Emitted after data is loaded from disk
    project_loaded = pyqtSignal(object)   # MilSymbProject
    # Emitted after data is written to disk
    project_saved = pyqtSignal(str)       # file path

    def __init__(self, project_data: MilSymbProject, parent: QObject | None = None):
        super().__init__(parent)
        self._project_data = project_data
        self._connected = False

    # ------------------------------------------------------------------
    # Mutable reference
    # ------------------------------------------------------------------

    def set_project_data(self, proj: MilSymbProject) -> None:
        self._project_data = proj

    # ------------------------------------------------------------------
    # Connect / disconnect signals
    # ------------------------------------------------------------------

    def connect_signals(self) -> None:
        """Connect to QgsProject write/read signals."""
        if self._connected:
            return
        qp = QgsProject.instance()
        qp.writeProject.connect(self._on_write_project)
        qp.readProject.connect(self._on_read_project)
        qp.cleared.connect(self._on_project_cleared)
        self._connected = True
        LOG.info("ProjectIO signals connected")

    def disconnect_signals(self) -> None:
        """Disconnect from QgsProject signals."""
        if not self._connected:
            return
        qp = QgsProject.instance()
        try:
            qp.writeProject.disconnect(self._on_write_project)
            qp.readProject.disconnect(self._on_read_project)
            qp.cleared.disconnect(self._on_project_cleared)
        except (TypeError, RuntimeError):
            pass
        self._connected = False
        LOG.info("ProjectIO signals disconnected")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_write_project(self, _dom_doc) -> None:
        """Called when the user saves the QGIS project."""
        path = self._sidecar_path()
        if path is None:
            LOG.debug("Project not yet saved – skipping MilSymb data write")
            return
        self._save_to(path)

    def _save_to(self, path: str) -> None:
        try:
            data_json = self._project_data.to_json()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(data_json)

            # Store the path in the project so it can be recovered
            QgsProject.instance().writeEntry(_PROJECT_KEY, "path", path)
            self.project_saved.emit(path)
            LOG.info("MilSymb data saved to %s (%d symbols, %d orbats)",
                     path,
                     len(self._project_data.symbols),
                     len(self._project_data.orbats))
        except Exception as exc:
            LOG.error("Failed to save MilSymb data: %s", exc)

    def save_now(self) -> str | None:
        """Explicitly save to the sidecar path (or return None if unavailable)."""
        path = self._sidecar_path()
        if path is None:
            return None
        self._save_to(path)
        return path

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def _on_read_project(self, _dom_doc) -> None:
        """Called when the user opens a QGIS project."""
        path = self._sidecar_path()
        if path is None:
            # Try the stored entry
            stored, _ = QgsProject.instance().readEntry(_PROJECT_KEY, "path", "")
            if stored and os.path.isfile(stored):
                path = stored
        if path is None or not os.path.isfile(path):
            LOG.debug("No MilSymb sidecar found – starting fresh")
            return
        self._load_from(path)

    def _load_from(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = MilSymbProject.from_json(fh.read())

            # Merge into the existing reference
            self._project_data.layers = loaded.layers
            self._project_data.orbats = loaded.orbats

            self.project_loaded.emit(self._project_data)
            LOG.info("MilSymb data loaded from %s (%d symbols, %d orbats)",
                     path,
                     len(self._project_data.symbols),
                     len(self._project_data.orbats))
        except Exception as exc:
            LOG.error("Failed to load MilSymb data: %s", exc)

    def load_from_file(self, path: str) -> MilSymbProject | None:
        """Explicitly load from a given file path."""
        if not os.path.isfile(path):
            return None
        self._load_from(path)
        return self._project_data

    # ------------------------------------------------------------------
    # Project cleared
    # ------------------------------------------------------------------

    def _on_project_cleared(self) -> None:
        """Called when the user starts a new empty project."""
        self._project_data.layers = []
        self._project_data.orbats.clear()
        self.project_loaded.emit(self._project_data)
        LOG.info("Project cleared – MilSymb data reset")

    # ------------------------------------------------------------------
    # Sidecar path
    # ------------------------------------------------------------------

    @staticmethod
    def _sidecar_path() -> str | None:
        """Return the sidecar path: ``<project_basename>.milsymb.json``.

        Returns *None* if the project has not been saved yet.
        """
        project_path = QgsProject.instance().fileName()
        if not project_path:
            return None
        base, _ext = os.path.splitext(project_path)
        return base + ".milsymb.json"
