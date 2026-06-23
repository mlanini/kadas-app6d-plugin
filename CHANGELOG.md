# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.10] – 2026-06-23

### Fixed
- Layer creation at startup now produces only one visible **MilSymb** layer.
- Stale/orphan memory point layers from previous plugin sessions are removed
  during layer bootstrap to prevent duplicate point-only layers.

## [0.1.9] – 2026-06-02

### Added
- **Drag-to-move symbols** on the map canvas: left-click and drag any symbol to
  reposition it directly, without going through the right-click context menu.

### Fixed
- Startup layer-creation prompt shown multiple times on the same project; now
  appears at most once per project (guarded by project key).
- "Move Symbol" context-menu action was silently failing because the
  `SymbolMoveTool` was immediately overwritten by KADAS when the menu closed;
  the tool activation is now deferred via `QTimer.singleShot(0, …)`.
- Post-move callback referenced `_symbol_editor_dock` (wrong name) instead of
  `_editor_dock`; symbol editor no longer fails to sync after a move.

---

## [0.1.8] – 2026-05-27

### Added
- **Symbol Editor** single-click sync: clicking a symbol on the map canvas now
  immediately loads it into the Symbol Editor dock (no double-click required).
- **Companion QgsVectorLayer** per symbol layer: each `KadasMapItemLayer` is now
  mirrored by a hidden `QgsVectorLayer` so that attributes appear in the QGIS
  attribute table and the Temporal Controller can filter symbols by DTG range.

---

## [0.1.7] – 2026-05-20

### Added
- **Land Unit** catalog: new **UAS / Drone** category with four entries:
  - `Unmanned Aerial Vehicle (UAS)` – generic
  - `UAS – Attack` (M1=03)
  - `UAS – Reconnaissance` (M1=18)
  - `UAS – Logistics / Cargo` (M1=69)
- **KMZ export** (all layers / current layer): produces a ZIP archive containing
  `doc.kml` and `icons/<sidc>.png` rendered via `milsymbol_engine`.
- **About dialog**: replaced simple message box with a `QDialog` showing plugin
  icon, version, author, and a clickable repository link.

### Fixed
- `subprocess` import annotated with `# noqa: B404` (used only for OS log viewer,
  not a security risk).
- `hashlib.md5()` now passes `usedforsecurity=False` (Bandit B324).

---

## [0.1.0] – 2026-05-15

### Added
- Initial release as a standalone **KADAS Albireo 2** plugin, ported from
  [qgis-app6d-plugin](https://github.com/intelligeo/qgis-app6d-plugin).
- APP-6(D) Symbol Catalog dock with full-text search and drag-and-drop onto the
  map canvas.
- Symbol Editor dock: 20-character SIDC builder, text modifiers (designation,
  higher formation, DTG, equipment, …), temporal extent fields.
- ORBAT Manager: hierarchical Order of Battle editor; import/export `.orbat.json`.
- Built-in HTTP symbol rendering server powered by
  [milsymbol.js](https://github.com/spatialillusions/milsymbol).
- Layer Manager dock: named symbol layers, per-layer JSON export.
- Temporal filtering integrated with the QGIS Temporal Controller.

---

[Unreleased]: https://github.com/mlanini/kadas-app6d-plugin/compare/v0.1.10...HEAD
[0.1.10]: https://github.com/mlanini/kadas-app6d-plugin/compare/v0.1.9...v0.1.10
[0.1.9]: https://github.com/mlanini/kadas-app6d-plugin/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/mlanini/kadas-app6d-plugin/compare/v0.1.0...v0.1.8
[0.1.0]: https://github.com/mlanini/kadas-app6d-plugin/releases/tag/v0.1.0
