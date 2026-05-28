# -*- coding: utf-8 -*-
"""
SVG symbol renderer – the main composition engine.

**Primary engine**: milsymbol v3.0.4 via Qt's QJSEngine.
**Fallback engine**: hand-drawn Python SVG (frames + icons + modifiers).

The milsymbol engine produces professional-quality NATO APP-6 / MIL-STD-2525
symbology identical to orbat-mapper and other industry tools.

Given a 20-character SIDC (or a 15-character 2525C SIDC) and optional
text amplifiers, this module returns a complete SVG document string,
and can optionally rasterise it to PNG via Qt's ``QSvgRenderer``.

Usage::

    from kadas_milsymb.symbology.renderer import render_symbol

    svg = render_symbol("10031000001200000000")
    svg = render_symbol("SFG-UCI---", designation="BA01")  # 2525C
    png = render_symbol_png("10031000001200000000", size=64)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from ..core.sidc import parse_any_sidc
from .frames import render_frame
from .icons import render_icon
from .modifiers import (
    render_echelon, render_hqtf, render_designation,
    render_higher_formation, render_mobility, render_operational_condition,
)
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.symbology.renderer")

# Canvas constants for the fallback Python renderer
_VIEWBOX = "0 0 200 260"
_WIDTH = 200
_HEIGHT = 260

# Default rendering options
DEFAULT_STROKE_WIDTH = 3.0
DEFAULT_OUTLINE_WIDTH = 0
DEFAULT_INFO_SIZE = 40

# milsymbol default render size (pixels)
MILSYMBOL_DEFAULT_SIZE = 80

# ======================================================================
# milsymbol engine (lazy singleton)
# ======================================================================

_milsymbol_checked = False
_milsymbol_available = False


def _check_milsymbol() -> bool:
    """Check and cache whether the milsymbol engine is available."""
    global _milsymbol_checked, _milsymbol_available
    if not _milsymbol_checked:
        try:
            from .milsymbol_engine import is_available
            _milsymbol_available = is_available()
        except Exception as exc:
            LOG.debug("milsymbol engine not available: %s", exc)
            _milsymbol_available = False
        _milsymbol_checked = True
        if _milsymbol_available:
            LOG.info("Using milsymbol engine for symbol rendering")
        else:
            LOG.info("Using fallback Python renderer for symbols")
    return _milsymbol_available


def _render_via_milsymbol(
    sidc_code: str,
    designation: str = "",
    higher_formation: str = "",
    size: int = MILSYMBOL_DEFAULT_SIZE,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    outline_width: float = DEFAULT_OUTLINE_WIDTH,
    operational_condition: str = "",
    quantity: str = "",
    staff_comments: str = "",
    additional_information: str = "",
    evaluation_rating: str = "",
    combat_effectiveness: str = "",
    dtg: str = "",
    type_str: str = "",
    speed: str = "",
    altitude_depth: str = "",
    direction: Optional[float] = None,
) -> Optional[str]:
    """Attempt to render using the milsymbol JS engine."""
    from .milsymbol_engine import render_svg

    kwargs: dict = {
        "size": size,
        "unique_designation": designation,
        "higher_formation": higher_formation,
        "quantity": quantity,
        "staff_comments": staff_comments,
        "additional_information": additional_information,
        "evaluation_rating": evaluation_rating,
        "combat_effectiveness": combat_effectiveness,
        "dtg": dtg,
        "type_str": type_str,
        "speed": speed,
        "altitude_depth": altitude_depth,
        "direction": direction,
    }
    if stroke_width != DEFAULT_STROKE_WIDTH:
        kwargs["stroke_width"] = stroke_width
    if outline_width:
        kwargs["outline_width"] = outline_width
    if operational_condition:
        kwargs["operational_condition"] = operational_condition
    return render_svg(sidc_code, **kwargs)


# ======================================================================
# SVG composition
# ======================================================================

def render_symbol(
    sidc_code: str,
    designation: str = "",
    higher_formation: str = "",
    size: Optional[int] = None,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    outline_width: float = DEFAULT_OUTLINE_WIDTH,
    operational_condition: str = "",
    use_dimension_frames: bool = True,
    quantity: str = "",
    staff_comments: str = "",
    additional_information: str = "",
    evaluation_rating: str = "",
    combat_effectiveness: str = "",
    dtg: str = "",
    type_str: str = "",
    speed: str = "",
    altitude_depth: str = "",
    direction: Optional[float] = None,
) -> str:
    """Render a complete APP-6(D) symbol as an SVG string.

    Uses the milsymbol JS engine as primary renderer.  Falls back to
    the hand-drawn Python SVG renderer if milsymbol is unavailable.

    Parameters
    ----------
    sidc_code : str
        20-character APP-6D SIDC or 15-character 2525C SIDC.
    designation : str
        Unit designator text (drawn below the frame).
    higher_formation : str
        Higher-formation label (drawn above echelon marks).
    size : int or None
        If given, set explicit ``width``/``height`` on the ``<svg>``
        element (pixels).  Otherwise the SVG scales to its container.
    stroke_width : float
        Frame stroke width (default 3.0).
    outline_width : float
        Extra outline around the frame (0 = none).
    operational_condition : str
        One of ``""``, ``"damaged"``, ``"destroyed"``.
    use_dimension_frames : bool
        If True (default), use APP-6D dimension-specific frame shapes
        (air, sea, subsurface variants). Set False to always use
        standard land-type frames.

    Returns
    -------
    str
        A self-contained SVG document (UTF-8, XML header included).
    """
    # --- Try milsymbol engine first ---
    if _check_milsymbol():
        ms_size = size if size else MILSYMBOL_DEFAULT_SIZE
        svg = _render_via_milsymbol(
            sidc_code, designation, higher_formation, ms_size,
            stroke_width, outline_width, operational_condition,
            quantity=quantity,
            staff_comments=staff_comments,
            additional_information=additional_information,
            evaluation_rating=evaluation_rating,
            combat_effectiveness=combat_effectiveness,
            dtg=dtg,
            type_str=type_str,
            speed=speed,
            altitude_depth=altitude_depth,
            direction=direction,
        )
        if svg is not None:
            return svg
        LOG.debug(
            "milsymbol failed for SIDC %s, falling back to Python renderer",
            sidc_code,
        )

    # --- Fallback: Python SVG composition ---
    return _render_python_fallback(
        sidc_code, designation, higher_formation, size,
        stroke_width, outline_width, operational_condition,
        use_dimension_frames,
    )


def _render_python_fallback(
    sidc_code: str,
    designation: str = "",
    higher_formation: str = "",
    size: Optional[int] = None,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    outline_width: float = DEFAULT_OUTLINE_WIDTH,
    operational_condition: str = "",
    use_dimension_frames: bool = True,
) -> str:
    """Fallback renderer using pure-Python SVG composition."""
    sidc = parse_any_sidc(sidc_code)

    # Determine frame shape – dimension-aware or standard
    if use_dimension_frames:
        shape = sidc.frame_shape_for_dimension
    else:
        shape = sidc.frame_shape

    fill = sidc.fill_color
    stroke = sidc.stroke_color
    dashed = sidc.status.value == "1"  # planned / anticipated

    parts: list[str] = []

    # 0. Optional outline (drawn first, behind everything)
    if outline_width > 0:
        parts.append(render_frame(shape, "none", "#ffffff", False))

    # 1. Frame
    parts.append(render_frame(shape, fill, stroke, dashed))

    # 2. Entity icon
    parts.append(render_icon(sidc.symbol_set.value, sidc.entity))

    # 3. Echelon (only for echelon-type amplifiers, codes 00-26)
    amp_code = sidc.amplifier
    amp_num = int(amp_code) if amp_code.isdigit() else 0
    if amp_num <= 26:
        parts.append(render_echelon(amp_code, shape))
    else:
        # Mobility / towed-array modifier (codes 31+)
        parts.append(render_mobility(amp_code, shape))

    # 4. HQ / Task Force / Dummy
    parts.append(render_hqtf(sidc.hq_tf_dummy.value, shape))

    # 5. Text amplifiers
    parts.append(render_designation(designation, shape))
    parts.append(render_higher_formation(higher_formation, shape))

    # 6. Operational condition overlay
    if operational_condition:
        parts.append(render_operational_condition(operational_condition, shape))

    body = "\n  ".join(p for p in parts if p)

    size_attrs = ""
    if size:
        size_attrs = f' width="{size}" height="{size}"'

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{_VIEWBOX}"{size_attrs}>\n'
        f"  {body}\n"
        "</svg>\n"
    )
    return svg


# ======================================================================
# PNG rasterisation (Qt-based, optional)
# ======================================================================

def render_symbol_png(
    sidc_code: str,
    size: int = 64,
    designation: str = "",
    higher_formation: str = "",
    operational_condition: str = "",
) -> Optional[bytes]:
    """Render a symbol to PNG bytes using Qt's SVG renderer.

    Accepts both APP-6D (20-char) and 2525C (15-char) SIDCs.
    Returns ``None`` if Qt SVG modules are not available.
    """
    try:
        from qgis.PyQt.QtCore import QByteArray, QBuffer, QIODevice
        from qgis.PyQt.QtGui import QImage, QPainter
        from qgis.PyQt.QtSvg import QSvgRenderer
    except ImportError:
        return None

    svg_str = render_symbol(
        sidc_code, designation, higher_formation,
        operational_condition=operational_condition,
    )
    svg_bytes = svg_str.encode("utf-8")

    renderer = QSvgRenderer(QByteArray(svg_bytes))
    if not renderer.isValid():
        return None

    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)  # transparent

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    # Encode to PNG bytes
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    image.save(buf, "PNG")
    buf.close()
    return bytes(ba.data())


# ======================================================================
# Cache-friendly wrappers
# ======================================================================

@lru_cache(maxsize=1024)
def cached_svg(
    sidc_code: str,
    designation: str = "",
    higher_formation: str = "",
    quantity: str = "",
    staff_comments: str = "",
    additional_information: str = "",
    evaluation_rating: str = "",
    combat_effectiveness: str = "",
    dtg: str = "",
    type_str: str = "",
    speed: str = "",
    altitude_depth: str = "",
    direction: Optional[float] = None,
) -> str:
    """LRU-cached version of :func:`render_symbol`.

    Accepts both APP-6D (20-char) and 2525C (15-char) SIDCs.
    Cache size increased from 512 → 1024 for better hit rates.
    """
    return render_symbol(
        sidc_code=sidc_code,
        designation=designation,
        higher_formation=higher_formation,
        quantity=quantity,
        staff_comments=staff_comments,
        additional_information=additional_information,
        evaluation_rating=evaluation_rating,
        combat_effectiveness=combat_effectiveness,
        dtg=dtg,
        type_str=type_str,
        speed=speed,
        altitude_depth=altitude_depth,
        direction=direction,
    )


@lru_cache(maxsize=512)
def cached_png(sidc_code: str, size: int = 64) -> Optional[bytes]:
    """LRU-cached version of :func:`render_symbol_png`.

    Accepts both APP-6D (20-char) and 2525C (15-char) SIDCs.
    Cache size increased from 256 → 512.
    """
    return render_symbol_png(sidc_code, size)


def svg_data_uri(sidc_code: str) -> str:
    """Return a ``data:image/svg+xml;utf8,...`` URI for inline embedding."""
    svg = cached_svg(sidc_code)
    # Minimal percent-encoding for data URI
    encoded = svg.replace("#", "%23").replace("\n", "%0A")
    return f"data:image/svg+xml;utf8,{encoded}"


def clear_caches() -> None:
    """Clear all LRU caches — useful after configuration changes."""
    global _milsymbol_checked
    cached_svg.cache_clear()
    cached_png.cache_clear()
    _milsymbol_checked = False  # re-check availability on next call
