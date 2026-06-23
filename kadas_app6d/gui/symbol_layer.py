# -*- coding: utf-8 -*-
"""
Symbol layer manager – one ``QgsVectorLayer`` per
:class:`~kadas_app6d.core.models.SymbolLayer`.

Architecture (single-layer)
---------------------------
* One ``QgsVectorLayer`` (in-memory Point, EPSG:4326) per ``SymbolLayer``.
* Each MilSymbol becomes one *feature* with all its attributes stored
  as fields on the layer:
  ``sym_id``, ``sidc``, ``designation``, ``higher_formation``,
  ``comment``, ``quantity``, ``start_date``, ``end_date``
  (plus extended amplifiers).
* The layer is rendered by ``MilSymbRenderer`` which reads the ``sidc``
  field and generates the APP-6(D) SVG icon dynamically.
* ``QgsVectorLayerTemporalProperties`` (ModeFeatureDateTimeStartAndEndFromFields)
  makes the layer fully compatible with the KADAS / QGIS Temporal Controller
  without any manual hide/show logic.
* ``_feature_map`` maps ``sym_id -> (sl_id, fid)`` so CRUD operations
  can reach the right feature quickly.

Benefits over the previous KadasItemLayer + companion design
------------------------------------------------------------
* Single layer in the Layers panel – no duplicates, no groups.
* Attribute table works out of the box (identify tool, table view).
* Full TC integration via native QGIS temporal filtering.
* Drag-to-move still works through the KADAS move tool (the layer
  exposes regular QgsVectorLayer geometry editing).
"""

from __future__ import annotations

from typing import Optional

from qgis.PyQt.QtCore import QObject, QVariant, pyqtSignal
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsGeometry,
    QgsMapSettings,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)

from ..core.models import MilSymbol, MilSymbProject, SymbolLayer
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.symbol_layer")

_LAYER_PREFIX = "MilSymb - "
_CRS_WGS84 = "EPSG:4326"
_SYMBOL_SIZE_PX = 64

# Tolerance for hit-testing: half the symbol size in pixels
_HIT_HALF_PX = _SYMBOL_SIZE_PX / 2


# ---------------------------------------------------------------------------
# Layer field schema
# ---------------------------------------------------------------------------

_FIELDS = [
    QgsField("sym_id",              QVariant.String,   len=64),
    QgsField("sidc",                QVariant.String,   len=20),
    QgsField("designation",         QVariant.String,   len=256),
    QgsField("higher_formation",    QVariant.String,   len=256),
    QgsField("comment",             QVariant.String,   len=1024),
    QgsField("quantity",            QVariant.String,   len=64),
    QgsField("staff_comments",      QVariant.String,   len=256),
    QgsField("additional_info",     QVariant.String,   len=256),
    QgsField("evaluation_rating",   QVariant.String,   len=32),
    QgsField("combat_effectiveness",QVariant.String,   len=32),
    QgsField("dtg",                 QVariant.String,   len=64),
    QgsField("type_str",            QVariant.String,   len=64),
    QgsField("speed",               QVariant.String,   len=32),
    QgsField("altitude_depth",      QVariant.String,   len=32),
    QgsField("direction",           QVariant.Double),
    QgsField("start_date",          QVariant.DateTime),
    QgsField("end_date",            QVariant.DateTime),
]


def _sym_to_feature(sym: MilSymbol, fields) -> QgsFeature:
    """Build a QgsFeature from a MilSymbol."""
    from qgis.PyQt.QtCore import QDateTime, Qt
    feat = QgsFeature(fields)
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(sym.longitude, sym.latitude)))
    feat.setAttribute("sym_id",                sym.id)
    feat.setAttribute("sidc",                  sym.sidc)
    feat.setAttribute("designation",           sym.designation or "")
    feat.setAttribute("higher_formation",      sym.higher_formation or "")
    feat.setAttribute("comment",               sym.comment or "")
    feat.setAttribute("quantity",              getattr(sym, "quantity", "") or "")
    feat.setAttribute("staff_comments",        getattr(sym, "staff_comments", "") or "")
    feat.setAttribute("additional_info",       getattr(sym, "additional_information", "") or "")
    feat.setAttribute("evaluation_rating",     getattr(sym, "evaluation_rating", "") or "")
    feat.setAttribute("combat_effectiveness",  getattr(sym, "combat_effectiveness", "") or "")
    feat.setAttribute("dtg",                   getattr(sym, "dtg", "") or "")
    feat.setAttribute("type_str",              getattr(sym, "type_str", "") or "")
    feat.setAttribute("speed",                 getattr(sym, "speed", "") or "")
    feat.setAttribute("altitude_depth",        getattr(sym, "altitude_depth", "") or "")
    dr = getattr(sym, "direction", None)
    feat.setAttribute("direction", float(dr) if dr is not None else None)
    t = sym.temporal
    if t and t.start:
        dt = QDateTime.fromString(t.start, Qt.ISODate)
        if not dt.isValid():
            dt = QDateTime.fromString(t.start[:10], "yyyy-MM-dd")
        feat.setAttribute("start_date", dt if dt.isValid() else None)
    else:
        feat.setAttribute("start_date", None)
    if t and t.end:
        dt2 = QDateTime.fromString(t.end, Qt.ISODate)
        if not dt2.isValid():
            dt2 = QDateTime.fromString(t.end[:10], "yyyy-MM-dd")
        feat.setAttribute("end_date", dt2 if dt2.isValid() else None)
    else:
        feat.setAttribute("end_date", None)
    return feat


# ======================================================================
# SymbolLayerManager
# ======================================================================

class SymbolLayerManager(QObject):
    """Manages one QgsVectorLayer + MilSymbRenderer per SymbolLayer."""

    symbol_added   = pyqtSignal(str)
    symbol_removed = pyqtSignal(str)
    symbol_updated = pyqtSignal(str)
    layer_added    = pyqtSignal(str)
    layer_removed  = pyqtSignal(str)
    layer_renamed  = pyqtSignal(str, str)
    active_layer_changed = pyqtSignal(str)

    def __init__(self, project_data: MilSymbProject, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._project = project_data
        # sl_id -> QgsVectorLayer  (renamed from _kadas_layers for backward compat)
        self._kadas_layers: dict = {}
        # sym_id -> (sl_id, fid)
        self._feature_map: dict = {}
        self._sym_size: int = _SYMBOL_SIZE_PX
        self._show_text_modifiers: bool = False
        self._active_layer_id: str = project_data.layers[0].id if project_data.layers else ""

    # ------------------------------------------------------------------
    # Active layer
    # ------------------------------------------------------------------

    @property
    def active_layer_id(self) -> str:
        return self._active_layer_id

    def set_active_layer(self, layer_id: str) -> None:
        if layer_id != self._active_layer_id:
            self._active_layer_id = layer_id
            self.active_layer_changed.emit(layer_id)

    def active_symbol_layer(self) -> Optional[SymbolLayer]:
        lyr = self._project.layer_by_id(self._active_layer_id)
        if lyr is None and self._project.layers:
            lyr = self._project.layers[0]
            self._active_layer_id = lyr.id
        return lyr

    # ------------------------------------------------------------------
    # Layer access
    # ------------------------------------------------------------------

    def kadas_layer(self, layer_id: str) -> Optional[QgsVectorLayer]:
        """Return the QgsVectorLayer for *layer_id*, creating it if needed."""
        import sip
        existing = self._kadas_layers.get(layer_id)
        if existing is not None and not sip.isdeleted(existing):
            return existing
        sym_layer = self._project.layer_by_id(layer_id)
        if sym_layer is None:
            return None
        return self._create_mil_layer(sym_layer)

    def layer(self) -> Optional[QgsVectorLayer]:
        """Return the active QgsVectorLayer (backward-compat)."""
        if not self._active_layer_id:
            return None
        return self.kadas_layer(self._active_layer_id)

    def all_kadas_layers(self) -> list:
        return [self.kadas_layer(sl.id) for sl in self._project.layers]

    def all_qgs_layers(self) -> list:
        return self.all_kadas_layers()

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def ensure_layers(self) -> None:
        self._remove_stale_project_layers()
        for sl in self._project.layers:
            self.kadas_layer(sl.id)

    def _remove_stale_project_layers(self) -> None:
        """Remove orphan MilSymb vector layers left in the project tree.

        This prevents duplicate "Point" layers when reopening projects or
        re-enabling the plugin in the same KADAS session.
        """
        import sip

        tracked_ids = {
            vl.id()
            for vl in self._kadas_layers.values()
            if vl is not None and not sip.isdeleted(vl)
        }

        for lyr in list(QgsProject.instance().mapLayers().values()):
            if not isinstance(lyr, QgsVectorLayer):
                continue
            if lyr.id() in tracked_ids:
                continue
            if lyr.providerType() != "memory":
                continue

            managed_prop = lyr.customProperty("kadas_milsymb_managed", False)
            is_managed = str(managed_prop).strip().lower() in {"1", "true", "yes"}
            if not is_managed and not lyr.name().startswith(_LAYER_PREFIX):
                continue

            try:
                QgsProject.instance().removeMapLayer(lyr.id())
                LOG.info("Removed stale MilSymb layer from project: %s", lyr.name())
            except Exception as exc:
                LOG.warning("Could not remove stale layer %s: %s", lyr.name(), exc)

    def _create_mil_layer(self, sym_layer: SymbolLayer) -> QgsVectorLayer:
        """Create the single QgsVectorLayer for *sym_layer*."""
        from .mil_renderer import MilSymbRenderer
        name = _LAYER_PREFIX + sym_layer.name
        vl = QgsVectorLayer(f"Point?crs={_CRS_WGS84}&index=yes", name, "memory")
        pr = vl.dataProvider()
        pr.addAttributes(_FIELDS)
        vl.updateFields()

        # --- Renderer ---
        renderer = MilSymbRenderer(
            field="sidc",
            size=self._sym_size,
            show_text=self._show_text_modifiers,
        )
        vl.setRenderer(renderer)

        # --- Temporal properties ---
        try:
            from qgis.core import QgsVectorLayerTemporalProperties
            tp = vl.temporalProperties()
            tp.setIsActive(True)
            tp.setMode(
                QgsVectorLayerTemporalProperties.ModeFeatureDateTimeStartAndEndFromFields
            )
            tp.setStartField("start_date")
            tp.setEndField("end_date")
        except Exception as exc:
            LOG.warning("Could not configure temporal properties: %s", exc)

        vl.setCustomProperty("kadas_milsymb_managed", True)
        QgsProject.instance().addMapLayer(vl)
        self._kadas_layers[sym_layer.id] = vl

        # Add existing symbols as features
        feats = [_sym_to_feature(s, vl.fields()) for s in sym_layer.symbols]
        if feats:
            ok, added = pr.addFeatures(feats)
            if ok:
                for feat in added:
                    sym_id = feat.attribute("sym_id")
                    if sym_id:
                        self._feature_map[sym_id] = (sym_layer.id, feat.id())

        LOG.info("Created mil layer '%s' with %d symbols", name, len(sym_layer.symbols))
        return vl

    def _renderer(self, layer_id: str):
        """Return the MilSymbRenderer for *layer_id*, or None."""
        from .mil_renderer import MilSymbRenderer
        vl = self._kadas_layers.get(layer_id)
        if vl is None:
            return None
        r = vl.renderer()
        return r if isinstance(r, MilSymbRenderer) else None

    # ------------------------------------------------------------------
    # Layer CRUD
    # ------------------------------------------------------------------

    def add_layer(self, name: str = "New Layer") -> SymbolLayer:
        sl = self._project.add_layer(name)
        self._create_mil_layer(sl)
        self.layer_added.emit(sl.id)
        LOG.info("Symbol layer added: %s (%s)", name, sl.id)
        return sl

    def import_layer(self, sl: SymbolLayer) -> SymbolLayer:
        """Append a pre-populated SymbolLayer (from JSON import)."""
        self._project.layers.append(sl)
        self._create_mil_layer(sl)
        self.layer_added.emit(sl.id)
        LOG.info("Symbol layer imported: %s (%s) – %d symbols",
                 sl.name, sl.id, len(sl.symbols))
        return sl

    def remove_layer(self, layer_id: str) -> bool:
        if len(self._project.layers) <= 1:
            LOG.warning("Cannot remove the last symbol layer")
            return False
        # Clean feature_map for this layer
        self._feature_map = {
            sid: v for sid, v in self._feature_map.items() if v[0] != layer_id
        }
        import sip
        vl = self._kadas_layers.pop(layer_id, None)
        if vl is not None:
            try:
                if not sip.isdeleted(vl):
                    QgsProject.instance().removeMapLayer(vl.id())
            except Exception:
                pass
        removed = self._project.remove_layer(layer_id)
        if removed:
            if self._active_layer_id == layer_id:
                self.set_active_layer(self._project.layers[0].id)
            self.layer_removed.emit(layer_id)
            LOG.info("Symbol layer removed: %s", layer_id)
        return removed

    def rename_layer(self, layer_id: str, new_name: str) -> bool:
        ok = self._project.rename_layer(layer_id, new_name)
        if ok:
            vl = self._kadas_layers.get(layer_id)
            if vl is not None:
                vl.setName(_LAYER_PREFIX + new_name)
            self.layer_renamed.emit(layer_id, new_name)
            LOG.info("Symbol layer renamed to '%s'", new_name)
        return ok

    def symbol_layers(self) -> list:
        return self._project.layers

    # ------------------------------------------------------------------
    # Symbol CRUD
    # ------------------------------------------------------------------

    def add_symbol(self, sym: MilSymbol, layer_id: str | None = None) -> None:
        lid = layer_id or self._active_layer_id
        sl = self._project.layer_by_id(lid)
        if sl is None:
            if self._project.layers:
                sl = self._project.layers[0]
                lid = sl.id
                self._active_layer_id = lid
            else:
                LOG.warning("add_symbol: no symbol layers exist – symbol not added")
                return
        sl.symbols.append(sym)
        vl = self.kadas_layer(lid)
        if vl is not None:
            feat = _sym_to_feature(sym, vl.fields())
            ok, added = vl.dataProvider().addFeatures([feat])
            if ok and added:
                self._feature_map[sym.id] = (lid, added[0].id())
                vl.triggerRepaint()
        self.symbol_added.emit(sym.id)
        LOG.info("Symbol added: %s -> layer %s", sym.id[:8], sl.name)

    def remove_symbol(self, sym_id: str) -> None:
        sl = self._project.layer_of_symbol(sym_id)
        if sl is None:
            return
        sl.symbols = [s for s in sl.symbols if s.id != sym_id]
        entry = self._feature_map.pop(sym_id, None)
        if entry is not None:
            sl_id, fid = entry
            vl = self._kadas_layers.get(sl_id)
            if vl is not None:
                import sip
                if not sip.isdeleted(vl):
                    vl.dataProvider().deleteFeatures([fid])
                    vl.triggerRepaint()
        self.symbol_removed.emit(sym_id)
        LOG.info("Symbol removed: %s", sym_id)

    def update_symbol(self, sym: MilSymbol) -> None:
        sl = self._project.layer_of_symbol(sym.id)
        if sl is None:
            return
        for i, s in enumerate(sl.symbols):
            if s.id == sym.id:
                sl.symbols[i] = sym
                break
        entry = self._feature_map.get(sym.id)
        if entry is not None:
            sl_id, fid = entry
            vl = self._kadas_layers.get(sl_id)
            if vl is not None:
                import sip
                if not sip.isdeleted(vl):
                    pr = vl.dataProvider()
                    pr.deleteFeatures([fid])
                    feat = _sym_to_feature(sym, vl.fields())
                    ok, added = pr.addFeatures([feat])
                    if ok and added:
                        self._feature_map[sym.id] = (sl_id, added[0].id())
                    # Invalidate renderer cache for this SIDC
                    r = self._renderer(sl_id)
                    if r is not None:
                        r.invalidate_sidc(sym.sidc)
                    vl.triggerRepaint()
        self.symbol_updated.emit(sym.id)
        LOG.info("Symbol %s updated", sym.id[:8])

    def get_symbol(self, sym_id: str) -> Optional[MilSymbol]:
        return self._project.symbol_by_id(sym_id)

    def symbol_id_at_point(
        self, map_point: QgsPointXY, map_settings: QgsMapSettings
    ) -> Optional[str]:
        """Alias for hit-testing the symbol under *map_point*."""
        return self.find_symbol_at_point(map_point, map_settings)

    def move_symbol_to_point(
        self, sym_id: str, map_point: QgsPointXY, map_settings: QgsMapSettings
    ) -> None:
        """Move *sym_id* to *map_point* (map CRS), updating model + feature."""
        sym = self.get_symbol(sym_id)
        if sym is None:
            return

        map_crs = map_settings.destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem(_CRS_WGS84)
        pt_wgs = map_point
        if map_crs != wgs84:
            xform = QgsCoordinateTransform(map_crs, wgs84, QgsProject.instance())
            pt_wgs = xform.transform(map_point)

        sym.longitude = float(pt_wgs.x())
        sym.latitude = float(pt_wgs.y())
        self.update_symbol(sym)

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------

    def find_symbol_at_point(
        self, map_point: QgsPointXY, map_settings: QgsMapSettings
    ) -> Optional[str]:
        """Return sym_id of the symbol nearest to *map_point*, or None."""
        # Tolerance: half the symbol size in pixels → converted to map units
        tol_map = map_settings.mapUnitsPerPixel() * _HIT_HALF_PX

        # Convert map_point to WGS-84 (layer CRS)
        map_crs = map_settings.destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem(_CRS_WGS84)
        if map_crs != wgs84:
            xform = QgsCoordinateTransform(map_crs, wgs84, QgsProject.instance())
            pt_wgs = xform.transform(map_point)
            # Tolerance also in WGS-84 degrees (rough conversion: 1 deg ≈ 111 km)
            tol_deg = tol_map / 111_000
        else:
            pt_wgs = map_point
            tol_deg = tol_map

        search_rect = QgsRectangle(
            pt_wgs.x() - tol_deg, pt_wgs.y() - tol_deg,
            pt_wgs.x() + tol_deg, pt_wgs.y() + tol_deg,
        )
        req = QgsFeatureRequest().setFilterRect(search_rect).setLimit(1)

        best_sym_id = None
        best_dist2 = float("inf")

        import sip
        for vl in self._kadas_layers.values():
            if vl is None or sip.isdeleted(vl):
                continue
            try:
                for feat in vl.getFeatures(req):
                    geom = feat.geometry()
                    if geom is None or geom.isEmpty():
                        continue
                    fp = geom.asPoint()
                    d2 = (fp.x() - pt_wgs.x()) ** 2 + (fp.y() - pt_wgs.y()) ** 2
                    if d2 < best_dist2:
                        best_dist2 = d2
                        best_sym_id = feat.attribute("sym_id")
            except Exception as exc:
                LOG.warning("find_symbol_at_point error: %s", exc)

        return best_sym_id

    # ------------------------------------------------------------------
    # Temporal filtering (no-op: handled natively by QgsVectorLayer TC)
    # ------------------------------------------------------------------

    def apply_temporal_filter(
        self, begin_iso: Optional[str], end_iso: Optional[str]
    ) -> None:
        """No-op: QgsVectorLayerTemporalProperties handles TC filtering."""
        pass

    # ------------------------------------------------------------------
    # Symbol size & text modifiers
    # ------------------------------------------------------------------

    def set_symbol_size(self, size_px: int) -> None:
        self._sym_size = size_px
        for sl_id in list(self._kadas_layers):
            r = self._renderer(sl_id)
            if r is not None:
                r.set_size(size_px)
                vl = self._kadas_layers[sl_id]
                vl.triggerRepaint()

    def set_show_text_modifiers(self, enabled: bool) -> None:
        if self._show_text_modifiers != enabled:
            self._show_text_modifiers = enabled
            self._refresh_all_symbols()

    def _refresh_all_symbols(self) -> None:
        for sl_id, vl in self._kadas_layers.items():
            r = self._renderer(sl_id)
            if r is not None:
                r.set_show_text(self._show_text_modifiers)
                r.clear_cache()
            import sip
            if not sip.isdeleted(vl):
                vl.triggerRepaint()

    # ------------------------------------------------------------------
    # Rebuild from project data
    # ------------------------------------------------------------------

    def rebuild_from_project(self, project: MilSymbProject) -> None:
        self._project = project
        self._feature_map.clear()
        import sip
        for vl in list(self._kadas_layers.values()):
            try:
                if not sip.isdeleted(vl):
                    QgsProject.instance().removeMapLayer(vl.id())
            except Exception:
                pass
        self._kadas_layers.clear()
        self.ensure_layers()
        self._active_layer_id = project.layers[0].id if project.layers else ""
        LOG.info(
            "Layers rebuilt from project – %d layers, %d symbols",
            len(project.layers), len(project.symbols),
        )

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def feature_count(self) -> int:
        return sum(len(sl.symbols) for sl in self._project.layers)