# -*- coding: utf-8 -*-
"""
Custom QgsFeatureRenderer for APP-6(D) military symbols.

Modelled after the kadas-milstd2525-plugin approach: a custom renderer
that overrides ``symbolForFeature()`` to dynamically create and cache
a ``QgsMarkerSymbol`` per SIDC code, using SVG files generated on
the fly by the symbology engine.

This eliminates the need to rebuild a categorised renderer whenever
symbols are added or removed.
"""

from __future__ import annotations

import os
import tempfile

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeatureRenderer,
    QgsMarkerSymbol,
    QgsRendererAbstractMetadata,
    QgsRenderContext,
    QgsSvgMarkerSymbolLayer,
)

from ..symbology.renderer import cached_svg
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.mil_renderer")

# Default symbol size in pixels
DEFAULT_SIZE_PX = 64

# ---- SVG cache directory (written lazily) ----------------------------
_SVG_CACHE_DIR: str | None = None


def _svg_cache_dir() -> str:
    """Return (and create) a temporary directory for SVG files."""
    global _SVG_CACHE_DIR
    if _SVG_CACHE_DIR is None:
        _SVG_CACHE_DIR = os.path.join(
            tempfile.gettempdir(), "kadas_milsymb_svg"
        )
        os.makedirs(_SVG_CACHE_DIR, exist_ok=True)
    return _SVG_CACHE_DIR


def _write_svg_file(sym, show_text: bool = False) -> str:
    """Write the SVG for the symbol to disk and return the file path.

    *sym* can be:
    * a 20-char SIDC string
    * a MilSymbol dataclass instance
    * a QgsFeature with a ``sidc`` field (and optionally text-amplifier fields)
    """
    import hashlib as _hl
    svg_dir = _svg_cache_dir()

    # --- Extract fields ---
    try:
        # QgsFeature duck-type
        sidc     = str(sym.attribute("sidc") or "")
        desig    = str(sym.attribute("designation") or "") if show_text else ""
        hf       = str(sym.attribute("higher_formation") or "") if show_text else ""
        quant    = str(sym.attribute("quantity") or "") if show_text else ""
        staff    = ""
        addinfo  = ""
        evalrat  = ""
        combeff  = ""
        dtg      = ""
        typestr  = ""
        speed    = ""
        alt      = ""
        dr       = None
    except (AttributeError, TypeError):
        if isinstance(sym, str):
            sidc    = sym
            desig   = ""
            hf      = ""
            quant   = ""
            staff   = ""
            addinfo = ""
            evalrat = ""
            combeff = ""
            dtg     = ""
            typestr = ""
            speed   = ""
            alt     = ""
            dr      = None
        else:
            sidc    = sym.sidc
            desig   = getattr(sym, 'designation', "") if show_text else ""
            hf      = getattr(sym, 'higher_formation', "") if show_text else ""
            quant   = getattr(sym, 'quantity', "") if show_text else ""
            staff   = getattr(sym, 'staff_comments', "") if show_text else ""
            addinfo = getattr(sym, 'additional_information', "") if show_text else ""
            evalrat = getattr(sym, 'evaluation_rating', "") if show_text else ""
            combeff = getattr(sym, 'combat_effectiveness', "") if show_text else ""
            dtg     = getattr(sym, 'dtg', "") if show_text else ""
            typestr = getattr(sym, 'type_str', "") if show_text else ""
            speed   = getattr(sym, 'speed', "") if show_text else ""
            alt     = getattr(sym, 'altitude_depth', "") if show_text else ""
            dr      = getattr(sym, 'direction', None) if show_text else None
    
    # Build a unique filename
    key = f"{sidc}|{desig}|{hf}|{quant}|{staff}|{addinfo}|{evalrat}|{combeff}|{dtg}|{typestr}|{speed}|{alt}|{dr}"
    suffix = _hl.md5(key.encode(), usedforsecurity=False).hexdigest()[:8]
    fname = f"sm_{suffix}.svg"
    path = os.path.join(svg_dir, fname)
    
    svg_content = cached_svg(
        sidc, desig, hf,
        quantity=quant, staff_comments=staff,
        additional_information=addinfo, evaluation_rating=evalrat,
        combat_effectiveness=combeff, dtg=dtg, type_str=typestr,
        speed=speed, altitude_depth=alt, direction=dr
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg_content)
    return path


def _make_marker(svg_path: str, size: float) -> QgsMarkerSymbol:
    """Create a ``QgsMarkerSymbol`` from an SVG file path.

    The marker is built from scratch (default layers stripped) with a
    single ``QgsSvgMarkerSymbolLayer``, exactly like the reference plugin.
    Size is in **pixels** so that symbols keep a constant screen size
    regardless of map zoom.
    """
    symbol = QgsMarkerSymbol()
    # Remove all default symbol layers
    while symbol.symbolLayerCount() > 0:
        symbol.takeSymbolLayer(0)
    svg_layer = QgsSvgMarkerSymbolLayer(svg_path)
    svg_layer.setSize(size)
    svg_layer.setSizeUnit(Qgis.RenderUnit.Pixels)
    symbol.appendSymbolLayer(svg_layer)
    return symbol


# ======================================================================
# MilSymbRenderer
# ======================================================================


class MilSymbRenderer(QgsFeatureRenderer):
    """Dynamic per-feature SVG renderer for military symbols.

    Reads the ``sidc`` attribute from each feature, generates (or
    retrieves from cache) the corresponding SVG file, and returns a
    ``QgsMarkerSymbol`` pointing to it.

    Parameters
    ----------
    field : str
        Attribute field that contains the 20-char SIDC code.
    size : float
        Symbol size in pixels.
    """

    RENDERER_TYPE = "MilSymbRenderer"

    def __init__(
        self,
        field: str = "sidc",
        size: float = DEFAULT_SIZE_PX,
        show_text: bool = False,
    ):
        super().__init__(self.RENDERER_TYPE)
        self.field = field
        self.size = size
        self.show_text = show_text
        self._cached: dict[str, QgsMarkerSymbol] = {}
        self._default_symbol = self._build_default_symbol()

    # ------------------------------------------------------------------
    # Default / fallback symbol
    # ------------------------------------------------------------------

    def _build_default_symbol(self) -> QgsMarkerSymbol:
        """Build a generic friendly-land-unit symbol as fallback."""
        default_sidc = "10031000000000000000"
        svg_path = _write_svg_file(default_sidc)
        return _make_marker(svg_path, self.size)

    # ------------------------------------------------------------------
    # QgsFeatureRenderer overrides
    # ------------------------------------------------------------------

    def symbolForFeature(self, feature: QgsFeature, context: QgsRenderContext):  # noqa: N802
        """Return the symbol for *feature* based on its SIDC value."""
        idx = feature.fieldNameIndex(self.field) if self.field else -1
        if idx == -1:
            return self._default_symbol

        sidc = feature.attributes()[idx]
        if not sidc:
            return self._default_symbol

        if self.show_text:
            import hashlib as _hl
            key_src = "|".join([
                str(sidc),
                str(feature.attribute("designation") or ""),
                str(feature.attribute("higher_formation") or ""),
                str(feature.attribute("quantity") or ""),
            ])
            cache_key = _hl.md5(key_src.encode(), usedforsecurity=False).hexdigest()
        else:
            cache_key = str(sidc)

        if cache_key not in self._cached:
            try:
                svg_path = _write_svg_file(feature, show_text=self.show_text)
                sym = _make_marker(svg_path, self.size)
                self._cached[cache_key] = sym
            except Exception:
                LOG.warning("Failed to create symbol for SIDC %s", sidc)
                self._cached[cache_key] = self._default_symbol

        symbol = self._cached[cache_key]
        symbol.startRender(context)
        return symbol

    def startRender(self, context: QgsRenderContext, fields=None):  # noqa: N802
        """Prepare rendering – start the default symbol."""
        self._default_symbol.startRender(context=context, fields=fields)
        super().startRender(context=context, fields=fields)

    def stopRender(self, context: QgsRenderContext):  # noqa: N802
        """Finish rendering – stop all cached symbols."""
        for sym in self._cached.values():
            sym.stopRender(context)
        self._default_symbol.stopRender(context)
        super().stopRender(context)

    def usedAttributes(self, context: QgsRenderContext):  # noqa: N802
        """Report that we need the SIDC and text amplifier fields."""
        return {self.field, "designation", "higher_formation"}

    def symbols(self, context: QgsRenderContext):
        """Return all currently cached symbols."""
        return list(self._cached.values())

    def clone(self) -> "MilSymbRenderer":
        """Create a deep copy of this renderer."""
        r = MilSymbRenderer(field=self.field, size=self.size, show_text=self.show_text)
        r._cached = {k: v.clone() for k, v in self._cached.items()}
        return r

    def save(self, doc, context):
        """Serialise renderer settings into a QGIS project XML element."""
        elem = doc.createElement("renderer-v2")
        elem.setAttribute("type", self.RENDERER_TYPE)
        elem.setAttribute("field", self.field)
        elem.setAttribute("size", str(self.size))
        elem.setAttribute("show_text", "1" if self.show_text else "0")
        return elem

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def set_show_text(self, show: bool) -> None:
        """Toggle text-modifier labels and clear cache."""
        if show != self.show_text:
            self.show_text = show
            self._cached.clear()

    def set_size(self, size: float) -> None:
        """Update symbol size (px), rebuild default and clear cache."""
        if size == self.size:
            return
        self.size = size
        self._default_symbol = self._build_default_symbol()
        self._cached.clear()
        LOG.info("MilSymbRenderer size changed to %s px", size)

    def clear_cache(self) -> None:
        """Drop all cached symbols – useful after settings changes."""
        self._cached.clear()
        LOG.debug("MilSymbRenderer cache cleared")

    def invalidate_sidc(self, sidc: str) -> None:
        """Remove all cache entries for *sidc* (e.g. after edit)."""
        # Remove all cache keys starting with this SIDC
        keys_to_remove = [k for k in self._cached if k.startswith(sidc)]
        for k in keys_to_remove:
            del self._cached[k]
        # Also clean up SVG files for this SIDC
        svg_dir = _svg_cache_dir()
        for fname in os.listdir(svg_dir):
            if fname.startswith(sidc):
                try:
                    os.remove(os.path.join(svg_dir, fname))
                except OSError:
                    pass


# ======================================================================
# Renderer metadata (for QGIS registry)
# ======================================================================


class MilSymbRendererMetadata(QgsRendererAbstractMetadata):
    """Registers :class:`MilSymbRenderer` with the QGIS renderer registry.

    This allows the renderer to be saved/loaded with QGIS projects and
    to appear in the Layer Styling panel.
    """

    def __init__(self):
        super().__init__(
            MilSymbRenderer.RENDERER_TYPE,
            "Military Symbol (APP-6D) Renderer",
        )

    def createRenderer(self, element, context):  # noqa: N802
        """Deserialise a renderer from project XML."""
        field = element.attribute("field", "sidc")
        size = float(element.attribute("size", str(DEFAULT_SIZE_PX)))
        show_text = element.attribute("show_text", "0") == "1"
        return MilSymbRenderer(field=field, size=size, show_text=show_text)

    def createRendererWidget(self, layer, style, renderer):  # noqa: N802
        """No configuration widget for now – return None."""
        return None
