# -*- coding: utf-8 -*-
"""
milsymbol.js integration via Qt's QJSEngine.

Loads the milsymbol v3.0.4 UMD bundle into a QJSEngine instance and
exposes a simple Python API::

    from kadas_milsymb.symbology.milsymbol_engine import render_svg

    svg = render_svg("10031000001211000000")
    svg = render_svg("SFG-UCI---")   # 2525C also supported

milsymbol natively supports both APP-6 and MIL-STD-2525 (B/C/D), so
any valid SIDC string can be passed directly.

The engine is initialised lazily on the first call and reused
thereafter.  It is safe to call from multiple threads as long as each
thread creates its own ``MilSymbolEngine`` or uses the module-level
singleton behind the lock.

Reference:
    https://github.com/spatialillusions/milsymbol
    https://www.spatialillusions.com/milsymbol/
"""

from __future__ import annotations

import json
import os
import threading
from typing import Optional

from ..logger import get_logger

LOG = get_logger("kadas_milsymb.symbology.milsymbol_engine")

# Path to the bundled milsymbol UMD file
_JS_DIR = os.path.join(os.path.dirname(__file__), "js")
_MILSYMBOL_JS = os.path.join(_JS_DIR, "milsymbol.js")

# Module-level singleton + lock
_engine_instance: Optional["MilSymbolEngine"] = None
_engine_lock = threading.Lock()


class MilSymbolEngine:
    """Thin wrapper around QJSEngine + milsymbol.js.

    Usage::

        engine = MilSymbolEngine()
        svg_str = engine.as_svg("10031000001211000000", size=80)
    """

    def __init__(self) -> None:
        self._engine = None
        self._ms = None
        self._ready = False
        self._init()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init(self) -> None:
        """Load milsymbol.js into QJSEngine."""
        try:
            from PyQt5.QtQml import QJSEngine
        except ImportError:
            try:
                from qgis.PyQt.QtQml import QJSEngine
            except ImportError:
                LOG.error(
                    "QJSEngine not available – "
                    "milsymbol rendering will fall back to Python SVG."
                )
                return

        if not os.path.isfile(_MILSYMBOL_JS):
            LOG.error(
                "milsymbol.js not found at %s – "
                "milsymbol rendering will fall back to Python SVG.",
                _MILSYMBOL_JS,
            )
            return

        engine = QJSEngine()

        # Provide a console shim – milsymbol.js calls console.warn()
        # and console.info() which do not exist in QJSEngine.
        engine.evaluate(
            "var console = {"
            "  log: function(){},"
            "  info: function(){},"
            "  warn: function(){},"
            "  error: function(){},"
            "  debug: function(){}"
            "};"
        )

        # milsymbol UMD expects `this` to be the global → assign `self`
        # We create a minimal global shim so the UMD wrapper can attach
        # `ms` to the global scope.
        engine.evaluate("var exports = {}; var module = {exports: {}};")

        with open(_MILSYMBOL_JS, "r", encoding="utf-8") as fh:
            js_source = fh.read()

        result = engine.evaluate(js_source, _MILSYMBOL_JS)
        if result.isError():
            LOG.error(
                "Failed to load milsymbol.js: %s (line %s)",
                result.toString(),
                result.property("lineNumber").toInt(),
            )
            return

        # The UMD wrapper sets module.exports or global.ms
        # Try module.exports first, then global.ms
        ms = engine.evaluate("module.exports")
        if ms.isUndefined() or ms.isNull():
            ms = engine.globalObject().property("ms")

        if ms.isUndefined() or ms.isNull():
            LOG.error("milsymbol loaded but 'ms' object not found in scope.")
            return

        # Quick sanity check: ms.Symbol must be a function
        sym_ctor = ms.property("Symbol")
        if not sym_ctor.isCallable():
            LOG.error("ms.Symbol is not callable – milsymbol may be corrupt.")
            return

        self._engine = engine
        self._ms = ms
        self._ready = True

        # Set the global standard to APP-6 (default is MIL-STD-2525)
        std_result = engine.evaluate("module.exports.setStandard('APP6')")
        if std_result.isError():
            LOG.warning(
                "Failed to set milsymbol standard to APP6: %s",
                std_result.toString(),
            )

        LOG.info(
            "milsymbol engine ready (QJSEngine, %d bytes loaded, standard=APP6)",
            len(js_source),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """True if milsymbol.js was loaded successfully."""
        return self._ready

    def as_svg(
        self,
        sidc: str,
        size: int = 80,
        fill: bool = True,
        frame: bool = True,
        color_mode: Optional[str] = None,
        icon_color: Optional[str] = None,
        stroke_width: float = 4.0,
        outline: bool = False,
        outline_color: str = "white",
        outline_width: float = 3.0,
        unique_designation: str = "",
        higher_formation: str = "",
        quantity: str = "",
        direction: Optional[float] = None,
        staff_comments: str = "",
        additional_information: str = "",
        evaluation_rating: str = "",
        combat_effectiveness: str = "",
        dtg: str = "",
        type_str: str = "",
        speed: str = "",
        altitude_depth: str = "",
    ) -> Optional[str]:
        """Render a military symbol as SVG using milsymbol.

        Parameters
        ----------
        sidc : str
            SIDC string (15-char 2525C or 20-char APP-6D).
        size : int
            Symbol pixel size (default 80).
        fill : bool
            Fill the frame with the standard affiliation colour.
        frame : bool
            Draw the frame outline.
        color_mode : str or None
            milsymbol colour mode: ``"Light"``, ``"Medium"``, ``"Dark"``,
            ``"FrameColor"`` or ``None`` (default colours).
        icon_color : str or None
            Override icon colour (CSS colour string).
        stroke_width : float
            Frame stroke width.
        outline : bool
            Draw an outline around the symbol.
        outline_color : str
            Colour of the outline.
        outline_width : float
            Width of the outline.
        unique_designation : str
            Unit designator (text amplifier T).
        higher_formation : str
            Higher-formation label (text amplifier M).
        quantity : str
            Equipment/personnel quantity (text amplifier C).
        direction : float or None
            Direction of movement (degrees).
        staff_comments : str
            Staff comments (text amplifier G).
        additional_information : str
            Additional info (text amplifier H).
        evaluation_rating : str
            Evaluation rating (text amplifier J).
        combat_effectiveness : str
            Combat effectiveness (text amplifier K).
        dtg : str
            Date-time group (text amplifier W).
        type_str : str
            Type / equipment code (text amplifier V).
        speed : str
            Speed (text amplifier Z).
        altitude_depth : str
            Altitude / depth (text amplifier X).

        Returns
        -------
        str or None
            SVG document string, or ``None`` if the engine is not ready.
        """
        if not self._ready:
            return None

        # Build options object as JSON for safe transfer to JS
        opts: dict = {"size": size, "standard": "APP6"}

        if not fill:
            opts["fill"] = False
        if not frame:
            opts["frame"] = False
        if color_mode:
            opts["colorMode"] = color_mode
        if icon_color:
            opts["iconColor"] = icon_color
        if stroke_width != 4.0:
            opts["strokeWidth"] = stroke_width
        if outline:
            opts["outlineWidth"] = outline_width
            opts["outlineColor"] = outline_color

        # Text amplifiers
        if unique_designation:
            opts["uniqueDesignation"] = unique_designation
        if higher_formation:
            opts["higherFormation"] = higher_formation
        if quantity:
            opts["quantity"] = quantity
        if direction is not None:
            opts["direction"] = direction
        if staff_comments:
            opts["staffComments"] = staff_comments
        if additional_information:
            opts["additionalInformation"] = additional_information
        if evaluation_rating:
            opts["evaluationRating"] = evaluation_rating
        if combat_effectiveness:
            opts["combatEffectiveness"] = combat_effectiveness
        if dtg:
            opts["dtg"] = dtg
        if type_str:
            opts["type"] = type_str
        if speed:
            opts["speed"] = speed
        if altitude_depth:
            opts["altitudeDepth"] = altitude_depth

        opts_json = json.dumps(opts)

        # Execute: new ms.Symbol(sidc, opts).asSVG()
        js_code = (
            f"(function() {{"
            f"  var opts = {opts_json};"
            f"  var sym = new module.exports.Symbol({json.dumps(sidc)}, opts);"
            f"  return sym.asSVG();"
            f"}})()"
        )

        result = self._engine.evaluate(js_code)
        if result.isError():
            LOG.warning(
                "milsymbol render error for SIDC %s: %s",
                sidc, result.toString(),
            )
            return None

        svg = result.toString()
        if not svg or not svg.strip().startswith("<svg"):
            LOG.warning(
                "milsymbol returned unexpected output for SIDC %s: %s",
                sidc, svg[:100] if svg else "(empty)",
            )
            return None

        # Post-process: force round line-joins so that rectangle
        # (Friend) frames don't show exaggerated square corners.
        svg = self._fix_stroke_linejoin(svg)

        # Post-process: strip the "?" (unknown icon) glyph that
        # milsymbol overlays when an entity/modifier code is not in
        # its lookup tables.  The glyph is a <path> with a distinctive
        # starting coordinate.
        svg = self._strip_unknown_icon_glyph(svg)

        # Post-process: strip the small black filler squares that
        # milsymbol draws at the four corners of rectangular frames
        # for certain symbol sets (e.g. Activities).  These are
        # rendered as a single <path> with four closed subpaths.
        svg = self._strip_corner_filler_squares(svg)

        # Inject explicit width/height so that
        # QgsSvgMarkerSymbolLayer can scale the icon correctly.
        # milsymbol outputs <svg xmlns="..." version="1.2" ...>
        # with a dynamic viewBox but no width/height.
        svg = self._inject_svg_dimensions(svg, size)

        return svg

    # ------------------------------------------------------------------
    # SVG post-processing
    # ------------------------------------------------------------------

    @staticmethod
    def _fix_stroke_linejoin(svg: str) -> str:
        """Set ``stroke-linejoin="round"`` on the root ``<svg>`` element.

        milsymbol uses the SVG default (``miter``), which produces
        exaggerated square spikes at the corners of rectangle frames
        (Friend identity).  Injecting ``round`` on the root element
        cascades to all child paths/rects via CSS inheritance.
        """
        # Insert the attribute right before the closing '>' of <svg …>
        idx = svg.find(">")
        if idx == -1:
            return svg
        # Avoid duplicate injection
        if "stroke-linejoin" in svg[:idx]:
            return svg
        return svg[:idx] + ' stroke-linejoin="round"' + svg[idx:]

    @staticmethod
    def _strip_unknown_icon_glyph(svg: str) -> str:
        """Remove milsymbol's "?" unknown-icon overlay from the SVG.

        When milsymbol cannot find an entity code or modifier in its
        internal lookup tables it draws a question-mark shaped
        ``<path>`` glyph (starting at ``m 94.8206,78.1372 …``).
        This makes many valid APP-6D symbols show an unwanted "?"
        modifier.  We strip it in post-processing so only the
        recognised frame + icon are rendered.
        """
        import re
        # The "?" glyph is a <path … d="m 94.8206,78.1372 …"/> element.
        # Match and remove it.  The distinctive start coordinate is
        # unique to this glyph and won't collide with real icons.
        # Handle both self-closing (<path … />) and open+close
        # (<path …></path>) formats produced by milsymbol.
        svg = re.sub(
            r'<path\s[^>]*?d="m\s*94\.8206\s*,\s*78\.1372[^"]*"[^>]*>(?:</path>)?',
            '',
            svg,
        )
        return svg

    @staticmethod
    def _strip_corner_filler_squares(svg: str) -> str:
        """Remove corner filler squares from the SVG.

        milsymbol draws four small black filled squares at the corners
        of rectangular frames for certain symbol sets (Activities,
        Installation, etc.).  These appear as a single ``<path>``
        element with four closed sub-paths (``z`` commands), black
        fill, and no stroke.

        Stripping them avoids ugly black boxes at the frame vertices.
        """
        import re
        # The path data contains exactly 4 'z'-closed sub-paths, each
        # drawing a small square.  We match any <path> where:
        #   - d="..." contains ≥4 'z' closings  (4 small squares)
        #   - fill="black"     (filled black)
        #   - stroke="none"    (no stroke)
        # Both self-closing (/>) and open+close (></path>) forms.
        svg = re.sub(
            r'<path\s[^>]*?'
            r'd="m\s*\d+\s*,\s*\d+'
            r'(?:\s+[\d.,-]+)*\s+z'
            r'(?:\s+m\s+[\d.,-]+(?:\s+[\d.,-]+)*\s+z){3}"'
            r'[^>]*fill="black"[^>]*>(?:</path>)?',
            '',
            svg,
        )
        return svg

    @staticmethod
    def _inject_echelon_placeholder(svg: str) -> str:
        """Add an invisible placeholder above the frame to reserve
        the vertical space that echelon marks would normally occupy.

        milsymbol dynamically sizes its viewBox to fit only the drawn
        content.  When no echelon is present, the viewBox is shorter,
        which makes the frame+icon appear larger once scaled to a
        fixed pixel size.  By extending the viewBox upward with a
        transparent element, we keep proportions consistent.

        The placeholder is a zero-opacity ``<rect>`` placed 28 px
        above the current viewBox minimum-Y (≈ height of one echelon
        mark row).
        """
        import re
        vb_match = re.search(r'viewBox="([^"]+)"', svg)
        if not vb_match:
            return svg

        parts = vb_match.group(1).split()
        if len(parts) != 4:
            return svg

        try:
            vb_x = float(parts[0])
            vb_y = float(parts[1])
            vb_w = float(parts[2])
            vb_h = float(parts[3])
        except ValueError:
            return svg

        # Reserve 28 units of extra height above the frame
        echelon_height = 28.0
        new_y = vb_y - echelon_height
        new_h = vb_h + echelon_height
        new_vb = f"{vb_x} {new_y} {vb_w} {new_h}"

        # Replace the viewBox
        svg = svg.replace(vb_match.group(0), f'viewBox="{new_vb}"', 1)

        # Insert an invisible placeholder rect right after the opening <svg ...> tag
        placeholder = (
            f'<rect x="{vb_x}" y="{new_y}" '
            f'width="1" height="1" fill="none" opacity="0"/>'
        )
        # Insert after the first '>'
        idx = svg.index(">") + 1
        svg = svg[:idx] + placeholder + svg[idx:]

        return svg

    @staticmethod
    def _inject_svg_dimensions(svg: str, size: int) -> str:
        """Ensure the ``<svg>`` element has explicit width/height.

        milsymbol outputs SVGs with a dynamic viewBox but no
        width/height attributes.  QGIS's QgsSvgMarkerSymbolLayer
        needs explicit dimensions to scale correctly.
        """
        import re
        # Only inject if width/height are not already present
        if 'width="' in svg[:300]:
            return svg

        # Extract the viewBox to compute aspect ratio
        vb_match = re.search(r'viewBox="([^"]+)"', svg)
        if vb_match:
            parts = vb_match.group(1).split()
            if len(parts) == 4:
                try:
                    vb_w = float(parts[2]) - float(parts[0])
                    vb_h = float(parts[3]) - float(parts[1])
                    # Scale to requested size, preserving aspect ratio
                    if vb_h > 0:
                        ratio = vb_w / vb_h
                        if ratio >= 1:
                            w = size
                            h = int(size / ratio)
                        else:
                            h = size
                            w = int(size * ratio)
                    else:
                        w = h = size
                    # Insert width/height after the opening <svg tag
                    svg = svg.replace(
                        '<svg xmlns=',
                        f'<svg width="{w}" height="{h}" xmlns=',
                        1,
                    )
                except (ValueError, ZeroDivisionError):
                    pass

        return svg


# ======================================================================
# Module-level convenience functions
# ======================================================================


def get_engine() -> MilSymbolEngine:
    """Return the module-level singleton engine (thread-safe)."""
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = MilSymbolEngine()
    return _engine_instance


def render_svg(
    sidc: str,
    size: int = 80,
    **kwargs,
) -> Optional[str]:
    """Convenience: render a military symbol SVG using the global engine.

    Falls back to ``None`` if the engine is not available.  All keyword
    arguments are forwarded to :meth:`MilSymbolEngine.as_svg`.
    """
    engine = get_engine()
    return engine.as_svg(sidc, size=size, **kwargs)


def is_available() -> bool:
    """True if the milsymbol engine was initialised successfully."""
    return get_engine().is_ready
