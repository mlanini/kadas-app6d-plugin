# -*- coding: utf-8 -*-
"""
Modifier SVG fragments for APP-6(D) military symbols.

Modifiers are drawn **outside** the frame:
* Echelon marks – centred above the frame top
* HQ staff – vertical line from the frame bottom-left corner downward
* Task-Force bar – horizontal bar above the frame
* Feint / Dummy – arc above the frame
"""

from __future__ import annotations

from .frames import frame_top, frame_bottom, frame_left, frame_right

_CX = 100
_SC = "#000000"
_SW = 3.0


# ======================================================================
# Echelon indicators  (Pos 9-10, amplifier/descriptor)
# ======================================================================

# Echelon marks are placed above the frame, centred at x = 100.
# They consist of dots (small circles), bars (|) and X-like marks
# depending on the echelon level.

def _echelon_y(shape: str) -> float:
    """Return the y baseline for echelon marks (above frame)."""
    return frame_top(shape) - 8


def _dot(cx: float, cy: float, r: float = 4) -> str:
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{_SC}"/>'


def _bar(cx: float, y1: float, y2: float) -> str:
    return (
        f'<line x1="{cx}" y1="{y1}" x2="{cx}" y2="{y2}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
    )


def echelon_none(shape: str) -> str:
    return ""


def echelon_team_crew(shape: str) -> str:
    """Team / Crew – single Open dot (∅)."""
    ey = _echelon_y(shape)
    return f'<circle cx="{_CX}" cy="{ey}" r="5" fill="none" stroke="{_SC}" stroke-width="2"/>'


def echelon_squad(shape: str) -> str:
    """Squad – one filled dot."""
    return _dot(_CX, _echelon_y(shape))


def echelon_section(shape: str) -> str:
    """Section – two dots."""
    ey = _echelon_y(shape)
    return _dot(_CX - 8, ey) + _dot(_CX + 8, ey)


def echelon_platoon(shape: str) -> str:
    """Platoon / Detachment – three dots."""
    ey = _echelon_y(shape)
    return _dot(_CX - 12, ey) + _dot(_CX, ey) + _dot(_CX + 12, ey)


def echelon_company(shape: str) -> str:
    """Company / Battery / Troop – one vertical bar."""
    ey = _echelon_y(shape)
    return _bar(_CX, ey - 12, ey)


def echelon_battalion(shape: str) -> str:
    """Battalion / Squadron – two bars."""
    ey = _echelon_y(shape)
    return _bar(_CX - 8, ey - 12, ey) + _bar(_CX + 8, ey - 12, ey)


def echelon_regiment(shape: str) -> str:
    """Regiment / Group – three bars."""
    ey = _echelon_y(shape)
    return (
        _bar(_CX - 14, ey - 12, ey)
        + _bar(_CX, ey - 12, ey)
        + _bar(_CX + 14, ey - 12, ey)
    )


def echelon_brigade(shape: str) -> str:
    """Brigade – X mark."""
    ey = _echelon_y(shape) - 6
    s = 10
    return (
        f'<line x1="{_CX - s}" y1="{ey - s}" x2="{_CX + s}" y2="{ey + s}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX + s}" y1="{ey - s}" x2="{_CX - s}" y2="{ey + s}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
    )


def echelon_division(shape: str) -> str:
    """Division – XX (two X marks)."""
    ey = _echelon_y(shape) - 6
    s = 8
    parts = ""
    for dx in (-14, 14):
        cx = _CX + dx
        parts += (
            f'<line x1="{cx - s}" y1="{ey - s}" x2="{cx + s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
            f'<line x1="{cx + s}" y1="{ey - s}" x2="{cx - s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
        )
    return parts


def echelon_corps(shape: str) -> str:
    """Corps – XXX."""
    ey = _echelon_y(shape) - 6
    s = 7
    parts = ""
    for dx in (-22, 0, 22):
        cx = _CX + dx
        parts += (
            f'<line x1="{cx - s}" y1="{ey - s}" x2="{cx + s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
            f'<line x1="{cx + s}" y1="{ey - s}" x2="{cx - s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
        )
    return parts


def echelon_army(shape: str) -> str:
    """Army – XXXX."""
    ey = _echelon_y(shape) - 6
    s = 6
    parts = ""
    for dx in (-30, -10, 10, 30):
        cx = _CX + dx
        parts += (
            f'<line x1="{cx - s}" y1="{ey - s}" x2="{cx + s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
            f'<line x1="{cx + s}" y1="{ey - s}" x2="{cx - s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
        )
    return parts


def echelon_army_group(shape: str) -> str:
    """Army Group / Front – XXXXX."""
    ey = _echelon_y(shape) - 6
    s = 5
    parts = ""
    for dx in (-36, -18, 0, 18, 36):
        cx = _CX + dx
        parts += (
            f'<line x1="{cx - s}" y1="{ey - s}" x2="{cx + s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
            f'<line x1="{cx + s}" y1="{ey - s}" x2="{cx - s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
        )
    return parts


def echelon_region(shape: str) -> str:
    """Region / Theater – XXXXXX."""
    ey = _echelon_y(shape) - 6
    s = 5
    parts = ""
    for dx in (-40, -24, -8, 8, 24, 40):
        cx = _CX + dx
        parts += (
            f'<line x1="{cx - s}" y1="{ey - s}" x2="{cx + s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
            f'<line x1="{cx + s}" y1="{ey - s}" x2="{cx - s}" y2="{ey + s}" '
            f'stroke="{_SC}" stroke-width="{_SW}"/>'
        )
    return parts


_ECHELON_FUNCS: dict[str, callable] = {
    "00": echelon_none,
    "11": echelon_team_crew,
    "12": echelon_squad,
    "13": echelon_section,
    "14": echelon_platoon,
    "15": echelon_company,
    "16": echelon_battalion,
    "17": echelon_regiment,
    "18": echelon_brigade,
    "21": echelon_division,
    "22": echelon_corps,
    "23": echelon_army,
    "24": echelon_army_group,
    "25": echelon_region,
}


# ======================================================================
# Mobility indicators  (Pos 9-10, codes 31–38)
# ======================================================================
# Mobility symbols are drawn below the frame as wheel/track/rail indicators.

def _mobility_y(shape: str) -> float:
    """Return the y baseline for mobility indicators (below frame)."""
    return frame_bottom(shape) + 6


def mobility_wheeled(shape: str) -> str:
    """Wheeled – single axle with two wheels."""
    my = _mobility_y(shape)
    r = 5
    return (
        f'<line x1="{_CX - 25}" y1="{my}" x2="{_CX + 25}" y2="{my}" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<circle cx="{_CX - 20}" cy="{my}" r="{r}" fill="none" stroke="{_SC}" stroke-width="2"/>'
        f'<circle cx="{_CX + 20}" cy="{my}" r="{r}" fill="none" stroke="{_SC}" stroke-width="2"/>'
    )


def mobility_wheeled_cross_country(shape: str) -> str:
    """Wheeled (cross-country) – three wheels."""
    my = _mobility_y(shape)
    r = 4
    return (
        f'<line x1="{_CX - 30}" y1="{my}" x2="{_CX + 30}" y2="{my}" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<circle cx="{_CX - 24}" cy="{my}" r="{r}" fill="none" stroke="{_SC}" stroke-width="2"/>'
        f'<circle cx="{_CX}" cy="{my}" r="{r}" fill="none" stroke="{_SC}" stroke-width="2"/>'
        f'<circle cx="{_CX + 24}" cy="{my}" r="{r}" fill="none" stroke="{_SC}" stroke-width="2"/>'
    )


def mobility_tracked(shape: str) -> str:
    """Tracked – rectangular track impression."""
    my = _mobility_y(shape)
    w, h = 50, 10
    return (
        f'<rect x="{_CX - w // 2}" y="{my - h // 2}" width="{w}" height="{h}" '
        f'rx="5" fill="none" stroke="{_SC}" stroke-width="2"/>'
    )


def mobility_wheeled_tracked(shape: str) -> str:
    """Wheeled and tracked combination."""
    my = _mobility_y(shape)
    w, h = 50, 10
    r = 4
    return (
        f'<rect x="{_CX - w // 2}" y="{my - h // 2}" width="{w}" height="{h}" '
        f'rx="5" fill="none" stroke="{_SC}" stroke-width="2"/>'
        f'<circle cx="{_CX - w // 2 - 2}" cy="{my}" r="{r}" fill="none" stroke="{_SC}" stroke-width="2"/>'
    )


def mobility_towed(shape: str) -> str:
    """Towed – single bar with hook."""
    my = _mobility_y(shape)
    return (
        f'<line x1="{_CX - 25}" y1="{my}" x2="{_CX + 25}" y2="{my}" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<line x1="{_CX + 25}" y1="{my}" x2="{_CX + 32}" y2="{my - 8}" '
        f'stroke="{_SC}" stroke-width="2"/>'
    )


def mobility_rail(shape: str) -> str:
    """Rail – track with cross-ties."""
    my = _mobility_y(shape)
    ties = ""
    for dx in (-20, -10, 0, 10, 20):
        ties += (
            f'<line x1="{_CX + dx}" y1="{my - 4}" '
            f'x2="{_CX + dx}" y2="{my + 4}" '
            f'stroke="{_SC}" stroke-width="2"/>'
        )
    return (
        f'<line x1="{_CX - 25}" y1="{my}" x2="{_CX + 25}" y2="{my}" '
        f'stroke="{_SC}" stroke-width="2"/>'
        + ties
    )


def mobility_over_snow(shape: str) -> str:
    """Over snow (ski) – ski shape."""
    my = _mobility_y(shape)
    return (
        f'<path d="M {_CX - 25},{my} Q {_CX - 30},{my - 10} {_CX - 20},{my - 10} '
        f'L {_CX + 25},{my - 10} Q {_CX + 30},{my - 10} {_CX + 30},{my}" '
        f'fill="none" stroke="{_SC}" stroke-width="2"/>'
    )


def mobility_sled(shape: str) -> str:
    """Sled – two parallel ski shapes."""
    my = _mobility_y(shape)
    parts = ""
    for dy in (-3, 5):
        parts += (
            f'<line x1="{_CX - 22}" y1="{my + dy}" '
            f'x2="{_CX + 22}" y2="{my + dy}" '
            f'stroke="{_SC}" stroke-width="2"/>'
            f'<path d="M {_CX - 22},{my + dy} Q {_CX - 28},{my + dy - 6} {_CX - 18},{my + dy - 6}" '
            f'fill="none" stroke="{_SC}" stroke-width="2"/>'
        )
    return parts


def mobility_pack_animals(shape: str) -> str:
    """Pack animals – inverted V."""
    my = _mobility_y(shape)
    return (
        f'<polyline points="{_CX - 18},{my + 8} {_CX},{my - 6} {_CX + 18},{my + 8}" '
        f'fill="none" stroke="{_SC}" stroke-width="2"/>'
    )


_MOBILITY_FUNCS: dict[str, callable] = {
    "31": mobility_wheeled,
    "32": mobility_wheeled_cross_country,
    "33": mobility_tracked,
    "34": mobility_wheeled_tracked,
    "35": mobility_towed,
    "36": mobility_rail,
    "37": mobility_over_snow,
    "38": mobility_sled,
    "41": mobility_pack_animals,         # pack animals
    # 42-48: towed arrays / variations (less common)
    "42": mobility_towed,                # short towed
    "43": mobility_towed,                # long towed
}


def render_mobility(amplifier: str, shape: str) -> str:
    """Return the mobility/towed-array modifier SVG for a given amplifier code."""
    func = _MOBILITY_FUNCS.get(amplifier)
    if func is None:
        return ""
    return func(shape)


# ======================================================================
# Operational condition indicator (Pos 7 extended)
# ======================================================================

def render_operational_condition(condition: str, shape: str) -> str:
    """Render an operational condition overlay on the symbol.

    APP-6D condition indicators:
    - Damaged: single slash
    - Destroyed: X across the frame
    """
    if condition == "damaged":
        ft = frame_top(shape)
        fb = frame_bottom(shape)
        fl = frame_left(shape)
        fr = frame_right(shape)
        return (
            f'<line x1="{fl}" y1="{fb}" x2="{fr}" y2="{ft}" '
            f'stroke="#ff0000" stroke-width="4"/>'
        )
    if condition == "destroyed":
        ft = frame_top(shape)
        fb = frame_bottom(shape)
        fl = frame_left(shape)
        fr = frame_right(shape)
        return (
            f'<line x1="{fl}" y1="{fb}" x2="{fr}" y2="{ft}" '
            f'stroke="#ff0000" stroke-width="4"/>'
            f'<line x1="{fl}" y1="{ft}" x2="{fr}" y2="{fb}" '
            f'stroke="#ff0000" stroke-width="4"/>'
        )
    return ""


def render_echelon(amplifier: str, shape: str) -> str:
    """Return the echelon modifier SVG for a given amplifier code."""
    func = _ECHELON_FUNCS.get(amplifier, echelon_none)
    return func(shape)


# ======================================================================
# HQ / Task Force / Dummy  (Pos 8)
# ======================================================================

def _hq_staff(shape: str) -> str:
    """HQ staff – vertical line from bottom-left of frame downward."""
    bx = frame_left(shape)
    by = frame_bottom(shape)
    return (
        f'<line x1="{bx}" y1="{by}" x2="{bx}" y2="{by + 35}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
    )


def _task_force_bar(shape: str) -> str:
    """Task-force bracket – a horizontal bar bridging the top of the frame."""
    ft = frame_top(shape)
    return (
        f'<line x1="{_CX - 50}" y1="{ft}" '
        f'x2="{_CX + 50}" y2="{ft}" '
        f'stroke="{_SC}" stroke-width="4"/>'
        # Small vertical ends
        f'<line x1="{_CX - 50}" y1="{ft}" '
        f'x2="{_CX - 50}" y2="{ft + 8}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX + 50}" y1="{ft}" '
        f'x2="{_CX + 50}" y2="{ft + 8}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
    )


def _feint_dummy_arc(shape: str) -> str:
    """Feint / Dummy – arc (concave down) above the frame."""
    ft = frame_top(shape) - 4
    return (
        f'<path d="M {_CX - 45},{ft} '
        f'Q {_CX},{ft - 28} {_CX + 45},{ft}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
    )


_HQTF_FUNCS: dict[str, callable] = {
    "0": lambda s: "",                          # None
    "1": _feint_dummy_arc,                      # Feint / Dummy
    "2": _hq_staff,                             # HQ
    "3": lambda s: _feint_dummy_arc(s) + _hq_staff(s),  # Feint/Dummy + HQ
    "4": _task_force_bar,                       # Task Force
    "5": lambda s: _feint_dummy_arc(s) + _task_force_bar(s),
    "6": lambda s: _task_force_bar(s) + _hq_staff(s),   # TF + HQ
    "7": lambda s: _feint_dummy_arc(s) + _task_force_bar(s) + _hq_staff(s),
}


def render_hqtf(code: str, shape: str) -> str:
    """Return the HQ/TF/Dummy modifier SVG for a given code (single char)."""
    func = _HQTF_FUNCS.get(code, lambda s: "")
    return func(shape)


# ======================================================================
# Text amplifiers (designation, higher formation)
# ======================================================================

def render_designation(text: str, shape: str) -> str:
    """Render the unit designation text below the frame."""
    if not text:
        return ""
    by = frame_bottom(shape) + 18
    return (
        f'<text x="{_CX}" y="{by}" text-anchor="middle" '
        f'font-size="14" font-family="Arial,Helvetica,sans-serif" '
        f'fill="{_SC}">{_escape(text)}</text>'
    )


def render_higher_formation(text: str, shape: str) -> str:
    """Render the higher-formation label above the echelon marks."""
    if not text:
        return ""
    ty = frame_top(shape) - 32
    return (
        f'<text x="{_CX}" y="{ty}" text-anchor="middle" '
        f'font-size="11" font-family="Arial,Helvetica,sans-serif" '
        f'fill="{_SC}">{_escape(text)}</text>'
    )


def _escape(text: str) -> str:
    """Minimal XML escaping for SVG text content."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
