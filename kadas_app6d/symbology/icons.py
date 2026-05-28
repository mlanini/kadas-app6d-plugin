# -*- coding: utf-8 -*-
"""
Entity icon SVG fragments for APP-6(D) military symbols.

Each function returns an SVG fragment (``<g>`` group or individual elements)
drawn **relative to the icon centre (100, 130)** so they align correctly
inside any frame shape.

The drawing area for icons is approximately 100 × 70 px centred on (100, 130).
"""

from __future__ import annotations

_CX, _CY = 100, 130  # icon centre
_SW = 3.0             # default stroke width
_SC = "#000000"       # default stroke colour


def _g(content: str, label: str = "") -> str:
    """Wrap *content* in a ``<g>`` with an optional aria label."""
    attr = f' aria-label="{label}"' if label else ""
    return f"<g{attr}>{content}</g>"


# ======================================================================
# Land Unit icons  (Symbol Set 10)
# ======================================================================

def icon_unspecified() -> str:
    """Generic / unspecified unit – empty (frame only)."""
    return ""


def icon_infantry() -> str:
    """Infantry – crossed diagonals (×)."""
    x1, y1 = _CX - 40, _CY - 30
    x2, y2 = _CX + 40, _CY + 30
    return _g(
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{x2}" y1="{y1}" x2="{x1}" y2="{y2}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Infantry",
    )


def icon_mechanized_infantry() -> str:
    """Mechanized infantry – × with ellipse."""
    return _g(
        icon_infantry()
        + f'<ellipse cx="{_CX}" cy="{_CY + 40}" rx="28" ry="12" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Mechanized Infantry",
    )


def icon_motorized_infantry() -> str:
    """Motorized infantry – × with filled circle below."""
    return _g(
        icon_infantry()
        + f'<circle cx="{_CX}" cy="{_CY + 42}" r="8" '
        f'fill="{_SC}" stroke="none"/>',
        "Motorized Infantry",
    )


def icon_mountain_infantry() -> str:
    """Mountain infantry – × with mountain peak (^)."""
    mx, my = _CX, _CY - 38
    return _g(
        icon_infantry()
        + f'<polyline points="{mx - 18},{my + 14} {mx},{my} {mx + 18},{my + 14}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Mountain Infantry",
    )


def icon_airborne_infantry() -> str:
    """Airborne infantry – × with parachute arc above."""
    return _g(
        icon_infantry()
        + f'<path d="M {_CX - 30},{_CY - 38} '
        f'Q {_CX},{_CY - 58} {_CX + 30},{_CY - 38}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Airborne Infantry",
    )


def icon_armor() -> str:
    """Armor / Cavalry – ellipse (horizontal)."""
    return _g(
        f'<ellipse cx="{_CX}" cy="{_CY}" rx="55" ry="28" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Armor",
    )


def icon_armored_reconnaissance() -> str:
    """Armored reconnaissance – ellipse with diagonal slash."""
    return _g(
        icon_armor()
        + f'<line x1="{_CX - 40}" y1="{_CY + 25}" '
        f'x2="{_CX + 40}" y2="{_CY - 25}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Armored Reconnaissance",
    )


def icon_artillery() -> str:
    """Field artillery – filled circle (●)."""
    return _g(
        f'<circle cx="{_CX}" cy="{_CY}" r="10" '
        f'fill="{_SC}" stroke="none"/>',
        "Field Artillery",
    )


def icon_self_propelled_artillery() -> str:
    """Self-propelled artillery – filled circle + ellipse."""
    return _g(
        icon_artillery()
        + f'<ellipse cx="{_CX}" cy="{_CY + 40}" rx="28" ry="12" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Self-Propelled Artillery",
    )


def icon_rocket_artillery() -> str:
    """Rocket artillery – three filled circles."""
    return _g(
        f'<circle cx="{_CX - 22}" cy="{_CY}" r="8" fill="{_SC}"/>'
        f'<circle cx="{_CX}" cy="{_CY}" r="8" fill="{_SC}"/>'
        f'<circle cx="{_CX + 22}" cy="{_CY}" r="8" fill="{_SC}"/>',
        "Rocket Artillery",
    )


def icon_air_defense() -> str:
    """Air defence – bow-tie / rotated bowtie shape."""
    x1, y1 = _CX - 35, _CY - 25
    x2, y2 = _CX + 35, _CY + 25
    return _g(
        # Left triangle
        f'<polygon points="{x1},{_CY} {_CX},{y1} {_CX},{y2}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        # Right triangle
        f'<polygon points="{x2},{_CY} {_CX},{y1} {_CX},{y2}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Air Defence",
    )


def icon_aviation() -> str:
    """Aviation (rotary wing) – helicopter rotor shape."""
    return _g(
        # Rotor blades – a cross with circles at tips
        f'<line x1="{_CX - 40}" y1="{_CY}" '
        f'x2="{_CX + 40}" y2="{_CY}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX}" y1="{_CY - 30}" '
        f'x2="{_CX}" y2="{_CY + 30}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<circle cx="{_CX}" cy="{_CY}" r="5" fill="{_SC}"/>',
        "Aviation",
    )


def icon_engineer() -> str:
    """Engineer – castle battlement (crenellation)."""
    bx, by = _CX - 35, _CY - 18
    bw, bh = 70, 36
    # Main rectangle
    s = f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
    # Crenellations on top
    cw, ch = 14, 12
    gap = 14
    sx = bx
    for i in range(3):
        cx = sx + i * (cw + gap)
        s += (
            f'<rect x="{cx}" y="{by - ch}" width="{cw}" height="{ch}" '
            f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        )
    return _g(s, "Engineer")


def icon_signal() -> str:
    """Signal / Communications – lightning bolt (⚡)."""
    x, y = _CX, _CY
    pts = (
        f"{x - 5},{y - 30} {x + 15},{y - 5} {x},{y - 5} "
        f"{x + 5},{y + 30} {x - 15},{y + 5} {x},{y + 5}"
    )
    return _g(
        f'<polygon points="{pts}" fill="{_SC}" stroke="none"/>',
        "Signal",
    )


def icon_military_intelligence() -> str:
    """Military intelligence – eye shape."""
    return _g(
        f'<path d="M {_CX - 40},{_CY} '
        f'Q {_CX},{_CY - 30} {_CX + 40},{_CY} '
        f'Q {_CX},{_CY + 30} {_CX - 40},{_CY} Z" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<circle cx="{_CX}" cy="{_CY}" r="8" fill="{_SC}"/>',
        "Military Intelligence",
    )


def icon_reconnaissance() -> str:
    """Reconnaissance – single diagonal slash (/)."""
    return _g(
        f'<line x1="{_CX - 35}" y1="{_CY + 28}" '
        f'x2="{_CX + 35}" y2="{_CY - 28}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Reconnaissance",
    )


def icon_medical() -> str:
    """Medical / Health services – red cross (+)."""
    return _g(
        f'<rect x="{_CX - 6}" y="{_CY - 22}" width="12" height="44" '
        f'fill="#ff0000" stroke="none"/>'
        f'<rect x="{_CX - 22}" y="{_CY - 6}" width="44" height="12" '
        f'fill="#ff0000" stroke="none"/>',
        "Medical",
    )


def icon_supply() -> str:
    """Supply / Logistics – half-circle (concave up)."""
    return _g(
        f'<path d="M {_CX - 35},{_CY + 5} '
        f'A 35 35 0 0 1 {_CX + 35},{_CY + 5}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX - 35}" y1="{_CY + 5}" '
        f'x2="{_CX + 35}" y2="{_CY + 5}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Supply",
    )


def icon_transportation() -> str:
    """Transportation – wheel (circle with spokes)."""
    r = 22
    return _g(
        f'<circle cx="{_CX}" cy="{_CY}" r="{r}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX}" y1="{_CY - r}" x2="{_CX}" y2="{_CY + r}" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<line x1="{_CX - r}" y1="{_CY}" x2="{_CX + r}" y2="{_CY}" '
        f'stroke="{_SC}" stroke-width="2"/>',
        "Transportation",
    )


def icon_maintenance() -> str:
    """Maintenance – wrench / spanner shape."""
    return _g(
        f'<line x1="{_CX - 30}" y1="{_CY + 25}" '
        f'x2="{_CX + 30}" y2="{_CY - 25}" '
        f'stroke="{_SC}" stroke-width="5"/>'
        f'<circle cx="{_CX - 30}" cy="{_CY + 25}" r="8" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<circle cx="{_CX + 30}" cy="{_CY - 25}" r="8" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Maintenance",
    )


def icon_cbrn() -> str:
    """CBRN – inverted triangle with letter C inside."""
    x, y = _CX, _CY
    return _g(
        f'<polygon points="{x - 30},{y - 22} {x + 30},{y - 22} {x},{y + 25}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<text x="{x}" y="{y + 5}" text-anchor="middle" '
        f'font-size="18" font-family="Arial" fill="{_SC}">C</text>',
        "CBRN",
    )


def icon_military_police() -> str:
    """Military police – MP text."""
    return _g(
        f'<text x="{_CX}" y="{_CY + 8}" text-anchor="middle" '
        f'font-size="26" font-weight="bold" font-family="Arial" '
        f'fill="{_SC}">MP</text>',
        "Military Police",
    )


def icon_special_operations() -> str:
    """Special operations forces – SOF arrow."""
    return _g(
        f'<path d="M {_CX},{_CY - 30} L {_CX + 25},{_CY + 20} '
        f'L {_CX + 8},{_CY + 10} L {_CX + 8},{_CY + 30} '
        f'L {_CX - 8},{_CY + 30} L {_CX - 8},{_CY + 10} '
        f'L {_CX - 25},{_CY + 20} Z" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Special Operations",
    )


def icon_electronic_warfare() -> str:
    """Electronic warfare – zigzag wave."""
    y = _CY
    return _g(
        f'<polyline points='
        f'"{_CX - 40},{y} {_CX - 27},{y - 18} {_CX - 13},{y + 18} '
        f'{_CX},{y} {_CX + 13},{y - 18} {_CX + 27},{y + 18} {_CX + 40},{y}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Electronic Warfare",
    )


def icon_headquarters() -> str:
    """Generic headquarters – H bar across the frame."""
    return _g(
        f'<line x1="{_CX - 35}" y1="{_CY}" '
        f'x2="{_CX + 35}" y2="{_CY}" '
        f'stroke="{_SC}" stroke-width="4"/>',
        "Headquarters",
    )


def icon_command_post() -> str:
    """Command post – star."""
    return _g(
        f'<polygon points="{_CX},{_CY - 22} {_CX + 6},{_CY - 6} '
        f'{_CX + 24},{_CY - 6} {_CX + 10},{_CY + 6} '
        f'{_CX + 16},{_CY + 22} {_CX},{_CY + 14} '
        f'{_CX - 16},{_CY + 22} {_CX - 10},{_CY + 6} '
        f'{_CX - 24},{_CY - 6} {_CX - 6},{_CY - 6}" '
        f'fill="{_SC}" stroke="none"/>',
        "Command Post",
    )


# ======================================================================
# Equipment icons  (Symbol Set 15)  – simplified
# ======================================================================

def icon_tank() -> str:
    """Main battle tank – hull + turret + gun (side view)."""
    return _g(
        # Hull
        f'<rect x="{_CX - 40}" y="{_CY - 8}" width="80" height="25" '
        f'rx="8" fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        # Turret
        f'<rect x="{_CX - 12}" y="{_CY - 20}" width="24" height="15" '
        f'rx="3" fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        # Gun
        f'<line x1="{_CX + 12}" y1="{_CY - 13}" '
        f'x2="{_CX + 45}" y2="{_CY - 13}" '
        f'stroke="{_SC}" stroke-width="3"/>',
        "Tank",
    )


def icon_apc() -> str:
    """Armored personnel carrier – hull shape."""
    return _g(
        f'<rect x="{_CX - 38}" y="{_CY - 12}" width="76" height="28" '
        f'rx="10" fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "APC",
    )


def icon_helicopter() -> str:
    """Helicopter – fuselage + rotor disc."""
    return _g(
        # Fuselage
        f'<ellipse cx="{_CX}" cy="{_CY + 5}" rx="18" ry="10" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        # Rotor disc
        f'<line x1="{_CX - 35}" y1="{_CY - 10}" '
        f'x2="{_CX + 35}" y2="{_CY - 10}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        # Mast
        f'<line x1="{_CX}" y1="{_CY - 5}" '
        f'x2="{_CX}" y2="{_CY - 10}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Helicopter",
    )


def icon_fixed_wing() -> str:
    """Fixed-wing aircraft – simple plane silhouette."""
    return _g(
        # Fuselage
        f'<line x1="{_CX - 35}" y1="{_CY}" '
        f'x2="{_CX + 35}" y2="{_CY}" '
        f'stroke="{_SC}" stroke-width="4"/>'
        # Wings
        f'<line x1="{_CX - 5}" y1="{_CY - 25}" '
        f'x2="{_CX - 5}" y2="{_CY + 25}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        # Tail
        f'<line x1="{_CX + 28}" y1="{_CY - 12}" '
        f'x2="{_CX + 28}" y2="{_CY + 12}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Fixed-Wing Aircraft",
    )


# ======================================================================
# Installation icons  (Symbol Set 20)  – simplified
# ======================================================================

def icon_installation_generic() -> str:
    """Generic installation – building outline."""
    return _g(
        f'<rect x="{_CX - 30}" y="{_CY - 15}" width="60" height="35" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        # Roof
        f'<polygon points="{_CX - 32},{_CY - 15} {_CX},{_CY - 35} '
        f'{_CX + 32},{_CY - 15}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Installation",
    )


# ======================================================================
# Sea icons  (Symbol Set 30)  – simplified
# ======================================================================

def icon_surface_ship() -> str:
    """Surface ship – hull shape."""
    return _g(
        f'<path d="M {_CX - 40},{_CY} '
        f'L {_CX - 35},{_CY + 15} L {_CX + 35},{_CY + 15} '
        f'L {_CX + 40},{_CY} Z" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX}" y1="{_CY}" '
        f'x2="{_CX}" y2="{_CY - 20}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Surface Ship",
    )


def icon_submarine() -> str:
    """Submarine – elongated ellipse with periscope."""
    return _g(
        f'<ellipse cx="{_CX}" cy="{_CY + 5}" rx="45" ry="14" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX}" y1="{_CY - 9}" '
        f'x2="{_CX}" y2="{_CY - 25}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Submarine",
    )


# ======================================================================
# Activity icons  (Symbol Set 40)
# ======================================================================

def icon_activity_generic() -> str:
    """Generic activity – exclamation mark."""
    return _g(
        f'<text x="{_CX}" y="{_CY + 12}" text-anchor="middle" '
        f'font-size="40" font-weight="bold" font-family="Arial" '
        f'fill="{_SC}">!</text>',
        "Activity",
    )


# ======================================================================
# Air icons  (Symbol Set 01)
# ======================================================================

def icon_air_track() -> str:
    """Generic air track – wing shape."""
    return _g(
        f'<path d="M {_CX - 40},{_CY + 5} L {_CX},{_CY - 20} L {_CX + 40},{_CY + 5}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX}" y1="{_CY - 20}" x2="{_CX}" y2="{_CY + 15}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Air Track",
    )


def icon_fighter() -> str:
    """Fighter aircraft – delta wing with tail."""
    return _g(
        f'<polygon points="{_CX},{_CY - 25} {_CX - 35},{_CY + 15} '
        f'{_CX + 35},{_CY + 15}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX - 12}" y1="{_CY + 15}" '
        f'x2="{_CX + 12}" y2="{_CY + 15}" '
        f'stroke="{_SC}" stroke-width="{_SW + 1}"/>',
        "Fighter",
    )


def icon_bomber() -> str:
    """Bomber – wide delta."""
    return _g(
        f'<polygon points="{_CX},{_CY - 22} {_CX - 42},{_CY + 18} '
        f'{_CX - 10},{_CY + 10} {_CX + 10},{_CY + 10} {_CX + 42},{_CY + 18}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "Bomber",
    )


def icon_attack_helicopter() -> str:
    """Attack helicopter – rotary wing with weapons."""
    return _g(
        icon_helicopter()
        + f'<line x1="{_CX - 22}" y1="{_CY + 8}" '
        f'x2="{_CX - 35}" y2="{_CY + 14}" '
        f'stroke="{_SC}" stroke-width="2.5"/>'
        f'<line x1="{_CX + 22}" y1="{_CY + 8}" '
        f'x2="{_CX + 35}" y2="{_CY + 14}" '
        f'stroke="{_SC}" stroke-width="2.5"/>',
        "Attack Helicopter",
    )


def icon_uav() -> str:
    """Unmanned aerial vehicle (UAV) / drone."""
    return _g(
        f'<path d="M {_CX - 35},{_CY} L {_CX},{_CY - 18} L {_CX + 35},{_CY}" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX}" y1="{_CY - 18}" x2="{_CX}" y2="{_CY + 12}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<circle cx="{_CX}" cy="{_CY + 16}" r="4" fill="{_SC}"/>',
        "UAV",
    )


def icon_transport_aircraft() -> str:
    """Transport / cargo aircraft."""
    return _g(
        f'<rect x="{_CX - 30}" y="{_CY - 10}" width="60" height="20" '
        f'rx="10" fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX - 10}" y1="{_CY - 25}" '
        f'x2="{_CX - 10}" y2="{_CY + 25}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>',
        "Transport Aircraft",
    )


def icon_tanker_aircraft() -> str:
    """Tanker (aerial refueling) aircraft."""
    return _g(
        icon_fixed_wing()
        + f'<circle cx="{_CX - 5}" cy="{_CY}" r="6" '
        f'fill="none" stroke="{_SC}" stroke-width="2"/>',
        "Tanker Aircraft",
    )


# ======================================================================
# Space icons  (Symbol Set 05)
# ======================================================================

def icon_satellite() -> str:
    """Satellite – body with solar panels."""
    return _g(
        f'<rect x="{_CX - 8}" y="{_CY - 10}" width="16" height="20" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        # Solar panels
        f'<rect x="{_CX - 35}" y="{_CY - 6}" width="22" height="12" '
        f'fill="none" stroke="{_SC}" stroke-width="2"/>'
        f'<rect x="{_CX + 13}" y="{_CY - 6}" width="22" height="12" '
        f'fill="none" stroke="{_SC}" stroke-width="2"/>',
        "Satellite",
    )


def icon_space_station() -> str:
    """Space station."""
    return _g(
        f'<circle cx="{_CX}" cy="{_CY}" r="14" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX - 35}" y1="{_CY}" x2="{_CX + 35}" y2="{_CY}" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<rect x="{_CX - 35}" y="{_CY - 5}" width="14" height="10" '
        f'fill="none" stroke="{_SC}" stroke-width="2"/>'
        f'<rect x="{_CX + 21}" y="{_CY - 5}" width="14" height="10" '
        f'fill="none" stroke="{_SC}" stroke-width="2"/>',
        "Space Station",
    )


# ======================================================================
# SIGINT icons  (Symbol Set 50-54)
# ======================================================================

def icon_sigint() -> str:
    """Signals intelligence – lightning bolt with eye."""
    return _g(
        f'<polygon points="{_CX - 3},{_CY - 25} {_CX + 12},{_CY - 3} '
        f'{_CX + 2},{_CY - 3} {_CX + 3},{_CY + 25} '
        f'{_CX - 12},{_CY + 3} {_CX - 2},{_CY + 3}" '
        f'fill="{_SC}" stroke="none"/>'
        f'<circle cx="{_CX + 22}" cy="{_CY - 12}" r="6" fill="none" '
        f'stroke="{_SC}" stroke-width="2"/>',
        "SIGINT",
    )


# ======================================================================
# Cyberspace icons  (Symbol Set 60)
# ======================================================================

def icon_cyber() -> str:
    """Cyberspace – network node symbol."""
    return _g(
        f'<circle cx="{_CX}" cy="{_CY}" r="10" fill="none" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<circle cx="{_CX - 28}" cy="{_CY - 18}" r="6" fill="none" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<circle cx="{_CX + 28}" cy="{_CY - 18}" r="6" fill="none" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<circle cx="{_CX - 28}" cy="{_CY + 18}" r="6" fill="none" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<circle cx="{_CX + 28}" cy="{_CY + 18}" r="6" fill="none" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<line x1="{_CX - 8}" y1="{_CY - 7}" x2="{_CX - 22}" y2="{_CY - 15}" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<line x1="{_CX + 8}" y1="{_CY - 7}" x2="{_CX + 22}" y2="{_CY - 15}" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<line x1="{_CX - 8}" y1="{_CY + 7}" x2="{_CX - 22}" y2="{_CY + 15}" '
        f'stroke="{_SC}" stroke-width="2"/>'
        f'<line x1="{_CX + 8}" y1="{_CY + 7}" x2="{_CX + 22}" y2="{_CY + 15}" '
        f'stroke="{_SC}" stroke-width="2"/>',
        "Cyberspace",
    )


# ======================================================================
# Additional Land Unit icons  (Symbol Set 10, beyond the basics)
# ======================================================================

def icon_civil_affairs() -> str:
    """Civil affairs – CA text."""
    return _g(
        f'<text x="{_CX}" y="{_CY + 8}" text-anchor="middle" '
        f'font-size="22" font-weight="bold" font-family="Arial" '
        f'fill="{_SC}">CA</text>',
        "Civil Affairs",
    )


def icon_public_affairs() -> str:
    """Public affairs – PA text."""
    return _g(
        f'<text x="{_CX}" y="{_CY + 8}" text-anchor="middle" '
        f'font-size="22" font-weight="bold" font-family="Arial" '
        f'fill="{_SC}">PA</text>',
        "Public Affairs",
    )


def icon_psychological_operations() -> str:
    """Psychological operations – loudspeaker shape."""
    return _g(
        f'<path d="M {_CX - 10},{_CY - 15} L {_CX + 20},{_CY - 25} '
        f'L {_CX + 20},{_CY + 25} L {_CX - 10},{_CY + 15} Z" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<rect x="{_CX - 22}" y="{_CY - 12}" width="12" height="24" '
        f'fill="none" stroke="{_SC}" stroke-width="{_SW}"/>',
        "PSYOP",
    )


def icon_finance() -> str:
    """Finance – dollar sign."""
    return _g(
        f'<text x="{_CX}" y="{_CY + 12}" text-anchor="middle" '
        f'font-size="36" font-weight="bold" font-family="Arial" '
        f'fill="{_SC}">$</text>',
        "Finance",
    )


def icon_judge_advocate() -> str:
    """Judge Advocate – scales of justice."""
    return _g(
        f'<line x1="{_CX}" y1="{_CY - 25}" x2="{_CX}" y2="{_CY + 20}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX - 25}" y1="{_CY - 15}" x2="{_CX + 25}" y2="{_CY - 15}" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<path d="M {_CX - 30},{_CY} A 8 5 0 0 0 {_CX - 18},{_CY}" '
        f'fill="none" stroke="{_SC}" stroke-width="2"/>'
        f'<path d="M {_CX + 18},{_CY} A 8 5 0 0 0 {_CX + 30},{_CY}" '
        f'fill="none" stroke="{_SC}" stroke-width="2"/>',
        "Judge Advocate",
    )


# ======================================================================
# Mine Warfare icons  (Symbol Set 36)
# ======================================================================

def icon_mine() -> str:
    """Naval mine – circle with spikes."""
    r = 14
    return _g(
        f'<circle cx="{_CX}" cy="{_CY}" r="{r}" fill="none" '
        f'stroke="{_SC}" stroke-width="{_SW}"/>'
        f'<line x1="{_CX}" y1="{_CY - r - 6}" x2="{_CX}" y2="{_CY - r}" '
        f'stroke="{_SC}" stroke-width="3"/>'
        f'<line x1="{_CX}" y1="{_CY + r}" x2="{_CX}" y2="{_CY + r + 6}" '
        f'stroke="{_SC}" stroke-width="3"/>'
        f'<line x1="{_CX - r - 6}" y1="{_CY}" x2="{_CX - r}" y2="{_CY}" '
        f'stroke="{_SC}" stroke-width="3"/>'
        f'<line x1="{_CX + r}" y1="{_CY}" x2="{_CX + r + 6}" y2="{_CY}" '
        f'stroke="{_SC}" stroke-width="3"/>',
        "Mine",
    )


# ======================================================================
# Dispatcher
# ======================================================================

#: Maps (symbol_set_code, entity_6digit) → icon function.
#: Falls back to ``icon_unspecified`` for unknown codes.
_ICON_REGISTRY: dict[tuple[str, str], callable] = {
    # Land Unit (10) ---------------------------------------------------
    ("10", "000000"): icon_unspecified,
    ("10", "110000"): icon_command_post,
    ("10", "120000"): icon_infantry,
    ("10", "120100"): icon_infantry,           # Light Infantry
    ("10", "120200"): icon_motorized_infantry,
    ("10", "120300"): icon_mechanized_infantry,
    ("10", "120400"): icon_mountain_infantry,
    ("10", "120500"): icon_airborne_infantry,
    ("10", "120600"): icon_infantry,           # Air Assault
    ("10", "130000"): icon_armor,
    ("10", "130100"): icon_armor,              # Light Armor
    ("10", "130300"): icon_armored_reconnaissance,
    ("10", "140000"): icon_artillery,
    ("10", "140100"): icon_self_propelled_artillery,
    ("10", "140200"): icon_rocket_artillery,
    ("10", "150000"): icon_air_defense,
    ("10", "160000"): icon_aviation,
    ("10", "170000"): icon_engineer,
    ("10", "180000"): icon_signal,
    ("10", "190000"): icon_military_intelligence,
    ("10", "200000"): icon_reconnaissance,
    ("10", "210000"): icon_medical,
    ("10", "220000"): icon_supply,
    ("10", "230000"): icon_transportation,
    ("10", "240000"): icon_maintenance,
    ("10", "250000"): icon_cbrn,
    ("10", "260000"): icon_military_police,
    ("10", "270000"): icon_special_operations,
    ("10", "280000"): icon_electronic_warfare,
    ("10", "290000"): icon_civil_affairs,
    ("10", "300000"): icon_public_affairs,
    ("10", "310000"): icon_psychological_operations,
    ("10", "320000"): icon_finance,
    ("10", "330000"): icon_judge_advocate,
    # Land Equipment (15) ----------------------------------------------
    ("15", "000000"): icon_unspecified,
    ("15", "120000"): icon_tank,
    ("15", "120100"): icon_apc,
    ("15", "160000"): icon_helicopter,
    ("15", "160100"): icon_fixed_wing,
    # Land Installation (20) -------------------------------------------
    ("20", "000000"): icon_installation_generic,
    # Air (01) ---------------------------------------------------------
    ("01", "000000"): icon_air_track,
    ("01", "110000"): icon_fighter,
    ("01", "110100"): icon_fighter,            # Air Superiority
    ("01", "110200"): icon_fighter,            # Interceptor
    ("01", "120000"): icon_bomber,
    ("01", "130000"): icon_transport_aircraft,
    ("01", "130100"): icon_tanker_aircraft,
    ("01", "140000"): icon_uav,
    ("01", "140100"): icon_uav,               # Recon UAV
    ("01", "150000"): icon_attack_helicopter,
    ("01", "160000"): icon_helicopter,         # Utility helicopter
    # Air Missile (02) -------------------------------------------------
    ("02", "000000"): icon_air_track,
    # Space (05) -------------------------------------------------------
    ("05", "000000"): icon_satellite,
    ("05", "110000"): icon_satellite,
    ("05", "120000"): icon_space_station,
    # Space Missile (06) -----------------------------------------------
    ("06", "000000"): icon_satellite,
    # Sea Surface (30) -------------------------------------------------
    ("30", "000000"): icon_unspecified,
    ("30", "120000"): icon_surface_ship,
    # Sea Subsurface (35) ----------------------------------------------
    ("35", "000000"): icon_unspecified,
    ("35", "120000"): icon_submarine,
    # Mine Warfare (36) ------------------------------------------------
    ("36", "000000"): icon_mine,
    ("36", "110000"): icon_mine,
    # Activities (40) --------------------------------------------------
    ("40", "000000"): icon_activity_generic,
    # SIGINT (50-54) ---------------------------------------------------
    ("50", "000000"): icon_sigint,
    ("51", "000000"): icon_sigint,
    ("52", "000000"): icon_sigint,
    ("53", "000000"): icon_sigint,
    ("54", "000000"): icon_sigint,
    # Cyberspace (60) --------------------------------------------------
    ("60", "000000"): icon_cyber,
}


def render_icon(symbol_set: str, entity: str) -> str:
    """Return the SVG icon fragment for a given symbol-set and entity code.

    Falls back to ``icon_unspecified`` (empty) for unknown combinations.
    """
    func = _ICON_REGISTRY.get((symbol_set, entity))
    if func is None:
        # Try entity family (first 2 digits + 0000)
        family = entity[:2] + "0000"
        func = _ICON_REGISTRY.get((symbol_set, family), icon_unspecified)
    return func()
