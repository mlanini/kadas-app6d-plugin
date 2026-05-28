# -*- coding: utf-8 -*-
"""
SVG frame shapes for APP-6(D) military symbols.

Each frame function returns an SVG fragment string (one or more SVG elements)
ready to be embedded inside the root ``<svg>`` element produced by the
renderer.

APP-6D specifies different frame geometries by *dimension* (domain):

* **Land / Activities / Installations** → standard frames
  (rectangle, diamond, square, quatrefoil)
* **Air / Space** → top-arc variation (closed with an arc at the top)
* **Sea Surface** → flat-bottom variation
* **Sea Subsurface** → inverted trapezoid form

For each dimension there are four affiliation variants:
friend, hostile, neutral, unknown/pending.

Coordinate system
-----------------
* viewBox  : ``0 0 200 260``
* All frames are centred at **(100, 130)**.
* Echelon / modifier area : y ∈ [10, 60]
* HQ staff area           : y ∈ [190, 250]
"""

from __future__ import annotations

# ======================================================================
# Frame dimensions (centre = 100, 130)
# ======================================================================

# Friend / Assumed-Friend  – rectangle (landscape)
_FR_X, _FR_Y, _FR_W, _FR_H = 15, 75, 170, 110

# Hostile / Suspect-Joker  – diamond
_HO_CX, _HO_CY = 100, 130
_HO_HW, _HO_HH = 85, 75   # half-width, half-height

# Neutral – square (upright)
_NE_X, _NE_Y, _NE_S = 40, 70, 120

# Unknown / Pending – quatrefoil approximation
_UN_CX, _UN_CY = 100, 130
_UN_RX, _UN_RY = 85, 72


def _stroke_attrs(color: str, width: float = 3.0, dashed: bool = False) -> str:
    """Return common stroke attributes."""
    da = ' stroke-dasharray="12,6"' if dashed else ""
    return f'stroke="{color}" stroke-width="{width}"{da}'


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def friend_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Rectangle frame for Friend / Assumed-Friend."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    return (
        f'<rect x="{_FR_X}" y="{_FR_Y}" '
        f'width="{_FR_W}" height="{_FR_H}" '
        f'fill="{fill}" {sa} rx="2" ry="2"/>'
    )


def hostile_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Diamond frame for Hostile / Suspect-Joker."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    cx, cy, hw, hh = _HO_CX, _HO_CY, _HO_HW, _HO_HH
    pts = (
        f"{cx},{cy - hh} "
        f"{cx + hw},{cy} "
        f"{cx},{cy + hh} "
        f"{cx - hw},{cy}"
    )
    return f'<polygon points="{pts}" fill="{fill}" {sa}/>'


def neutral_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Square frame for Neutral."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    return (
        f'<rect x="{_NE_X}" y="{_NE_Y}" '
        f'width="{_NE_S}" height="{_NE_S}" '
        f'fill="{fill}" {sa}/>'
    )


def unknown_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Quatrefoil (cloverleaf) frame for Unknown / Pending.

    Approximated with four cubic Bézier arcs producing a rounded
    blob with concave indentations.
    """
    sa = _stroke_attrs(stroke, dashed=dashed)
    cx, cy, rx, ry = _UN_CX, _UN_CY, _UN_RX, _UN_RY
    # Control-point offsets for the Bézier bulges
    bx, by = 30, 25
    d = (
        f"M {cx},{cy - ry} "
        f"C {cx + bx},{cy - ry} {cx + rx},{cy - by} {cx + rx},{cy} "
        f"C {cx + rx},{cy + by} {cx + bx},{cy + ry} {cx},{cy + ry} "
        f"C {cx - bx},{cy + ry} {cx - rx},{cy + by} {cx - rx},{cy} "
        f"C {cx - rx},{cy - by} {cx - bx},{cy - ry} {cx},{cy - ry} Z"
    )
    return f'<path d="{d}" fill="{fill}" {sa}/>'


# ------------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------------

_FRAME_FUNCS = {
    # Land (default)
    "friend":  friend_frame,
    "hostile": hostile_frame,
    "neutral": neutral_frame,
    "unknown": unknown_frame,
    "pending": unknown_frame,  # same shape, different fill
}


def render_frame(shape: str, fill: str, stroke: str, dashed: bool = False) -> str:
    """Return the SVG fragment for the given frame *shape*.

    *shape* can be:
    - Land/default: ``"friend"``, ``"hostile"``, ``"neutral"``,
      ``"unknown"``, ``"pending"``
    - Air: ``"friend_air"``, ``"hostile_air"``, etc.
    - Sea surface: ``"friend_sea"``, etc.
    - Subsurface: ``"friend_subsurface"``, etc.
    """
    func = _FRAME_FUNCS.get(shape)
    if func is None:
        # Try dimension-specific frames
        func = _AIR_FRAME_FUNCS.get(shape)
    if func is None:
        func = _SEA_FRAME_FUNCS.get(shape)
    if func is None:
        func = _SUBSURFACE_FRAME_FUNCS.get(shape)
    if func is None:
        func = unknown_frame
    return func(fill, stroke, dashed)


# ======================================================================
# AIR / SPACE frames  –  top has a semi-circular arc
# ======================================================================

# Friend Air: rectangle with rounded top (arc)
def friend_air_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Friend air frame – rectangle bottom with semicircular top."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    x, y, w, h = _FR_X, _FR_Y, _FR_W, _FR_H
    # Arc from top-left to top-right; straight sides and bottom
    rx = w / 2
    ry = 30
    d = (
        f"M {x},{y + h} "              # bottom-left
        f"L {x},{y + ry} "             # left side to arc start
        f"A {rx},{ry} 0 0 1 {x + w},{y + ry} "  # top arc
        f"L {x + w},{y + h} "          # right side
        f"Z"
    )
    return f'<path d="{d}" fill="{fill}" {sa}/>'


def hostile_air_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Hostile air frame – pointed-top triangle/diamond with arc."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    cx, cy, hw, hh = _HO_CX, _HO_CY, _HO_HW, _HO_HH
    # Diamond with the top vertex replaced by an arc
    d = (
        f"M {cx},{cy + hh} "
        f"L {cx - hw},{cy} "
        f"A {hw},{hh * 0.6} 0 0 1 {cx + hw},{cy} "
        f"Z"
    )
    return f'<path d="{d}" fill="{fill}" {sa}/>'


def neutral_air_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Neutral air frame – square with rounded top."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    x, y, s = _NE_X, _NE_Y, _NE_S
    rx = s / 2
    ry = 25
    d = (
        f"M {x},{y + s} "
        f"L {x},{y + ry} "
        f"A {rx},{ry} 0 0 1 {x + s},{y + ry} "
        f"L {x + s},{y + s} "
        f"Z"
    )
    return f'<path d="{d}" fill="{fill}" {sa}/>'


def unknown_air_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Unknown air frame – quatrefoil with extra bump on top."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    # Use the standard unknown frame with a slight arc at top
    cx, cy, rx, ry = _UN_CX, _UN_CY, _UN_RX, _UN_RY
    bx, by = 30, 25
    arc_lift = 15
    d = (
        f"M {cx},{cy - ry - arc_lift} "
        f"C {cx + bx},{cy - ry} {cx + rx},{cy - by} {cx + rx},{cy} "
        f"C {cx + rx},{cy + by} {cx + bx},{cy + ry} {cx},{cy + ry} "
        f"C {cx - bx},{cy + ry} {cx - rx},{cy + by} {cx - rx},{cy} "
        f"C {cx - rx},{cy - by} {cx - bx},{cy - ry} {cx},{cy - ry - arc_lift} Z"
    )
    return f'<path d="{d}" fill="{fill}" {sa}/>'


_AIR_FRAME_FUNCS = {
    "friend_air":  friend_air_frame,
    "hostile_air": hostile_air_frame,
    "neutral_air": neutral_air_frame,
    "unknown_air": unknown_air_frame,
    "pending_air": unknown_air_frame,
}


# ======================================================================
# SEA SURFACE frames  –  flat bottom / hull shape
# ======================================================================

def friend_sea_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Friend sea surface – rectangle with curved (hull) bottom."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    x, y, w, h = _FR_X, _FR_Y, _FR_W, _FR_H
    d = (
        f"M {x},{y} "
        f"L {x + w},{y} "
        f"L {x + w},{y + h} "
        f"A {w / 2},{20} 0 0 1 {x},{y + h} "
        f"Z"
    )
    return f'<path d="{d}" fill="{fill}" {sa}/>'


def hostile_sea_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Hostile sea surface – diamond with flattened bottom."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    cx, cy, hw, hh = _HO_CX, _HO_CY, _HO_HW, _HO_HH
    flat_w = 30
    pts = (
        f"{cx},{cy - hh} "
        f"{cx + hw},{cy} "
        f"{cx + flat_w},{cy + hh} "
        f"{cx - flat_w},{cy + hh} "
        f"{cx - hw},{cy}"
    )
    return f'<polygon points="{pts}" fill="{fill}" {sa}/>'


def neutral_sea_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Neutral sea surface – square with curved bottom."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    x, y, s = _NE_X, _NE_Y, _NE_S
    d = (
        f"M {x},{y} "
        f"L {x + s},{y} "
        f"L {x + s},{y + s} "
        f"A {s / 2},{18} 0 0 1 {x},{y + s} "
        f"Z"
    )
    return f'<path d="{d}" fill="{fill}" {sa}/>'


def unknown_sea_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Unknown sea surface – quatrefoil with flat bottom."""
    # Reuse standard unknown for sea surface (minor variant in APP-6D)
    return unknown_frame(fill, stroke, dashed)


_SEA_FRAME_FUNCS = {
    "friend_sea":  friend_sea_frame,
    "hostile_sea": hostile_sea_frame,
    "neutral_sea": neutral_sea_frame,
    "unknown_sea": unknown_sea_frame,
    "pending_sea": unknown_sea_frame,
}


# ======================================================================
# SEA SUBSURFACE frames  –  inverted trapezoid / upside-down shape
# ======================================================================

def friend_subsurface_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Friend subsurface – inverted trapezoid (wider at top)."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    x, y, w, h = _FR_X, _FR_Y, _FR_W, _FR_H
    inset = 25
    pts = (
        f"{x},{y} "
        f"{x + w},{y} "
        f"{x + w - inset},{y + h} "
        f"{x + inset},{y + h}"
    )
    return f'<polygon points="{pts}" fill="{fill}" {sa}/>'


def hostile_subsurface_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Hostile subsurface – inverted diamond variant."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    cx, cy, hw, hh = _HO_CX, _HO_CY, _HO_HW, _HO_HH
    # Diamond rotated to emphasize lower portion
    pts = (
        f"{cx},{cy - hh} "
        f"{cx + hw},{cy - 8} "
        f"{cx},{cy + hh} "
        f"{cx - hw},{cy - 8}"
    )
    return f'<polygon points="{pts}" fill="{fill}" {sa}/>'


def neutral_subsurface_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Neutral subsurface – inverted trapezoid."""
    sa = _stroke_attrs(stroke, dashed=dashed)
    x, y, s = _NE_X, _NE_Y, _NE_S
    inset = 20
    pts = (
        f"{x},{y} "
        f"{x + s},{y} "
        f"{x + s - inset},{y + s} "
        f"{x + inset},{y + s}"
    )
    return f'<polygon points="{pts}" fill="{fill}" {sa}/>'


def unknown_subsurface_frame(fill: str, stroke: str, dashed: bool = False) -> str:
    """Unknown subsurface – quatrefoil with squashed bottom."""
    return unknown_frame(fill, stroke, dashed)


_SUBSURFACE_FRAME_FUNCS = {
    "friend_subsurface":  friend_subsurface_frame,
    "hostile_subsurface": hostile_subsurface_frame,
    "neutral_subsurface": neutral_subsurface_frame,
    "unknown_subsurface": unknown_subsurface_frame,
    "pending_subsurface": unknown_subsurface_frame,
}


# ------------------------------------------------------------------
# Bounding helpers (used by modifiers to position relative to frame)
# ------------------------------------------------------------------

def frame_top(shape: str) -> float:
    """Return the y coordinate of the topmost edge of the frame."""
    if shape == "friend":
        return float(_FR_Y)
    if shape == "hostile":
        return float(_HO_CY - _HO_HH)
    if shape == "neutral":
        return float(_NE_Y)
    return float(_UN_CY - _UN_RY)  # unknown / pending


def frame_bottom(shape: str) -> float:
    """Return the y coordinate of the bottommost edge of the frame."""
    if shape == "friend":
        return float(_FR_Y + _FR_H)
    if shape == "hostile":
        return float(_HO_CY + _HO_HH)
    if shape == "neutral":
        return float(_NE_Y + _NE_S)
    return float(_UN_CY + _UN_RY)


def frame_left(shape: str) -> float:
    if shape == "friend":
        return float(_FR_X)
    if shape == "hostile":
        return float(_HO_CX - _HO_HW)
    if shape == "neutral":
        return float(_NE_X)
    return float(_UN_CX - _UN_RX)


def frame_right(shape: str) -> float:
    if shape == "friend":
        return float(_FR_X + _FR_W)
    if shape == "hostile":
        return float(_HO_CX + _HO_HW)
    if shape == "neutral":
        return float(_NE_X + _NE_S)
    return float(_UN_CX + _UN_RX)
