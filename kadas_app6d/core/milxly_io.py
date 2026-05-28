# -*- coding: utf-8 -*-
"""
MilX-Layer (*.milxly) import / export for the KADAS APP-6(D) plugin.

Format description
------------------
The ``.milxly`` format is an XML dialect defined by the MilX/MSSO library
(gs-soft.com) used by swisstopo KADAS installations and third-party tools.
One file = one ``MilXLayer`` containing a ``GraphicList`` of ``MilXGraphic``
elements.

Each ``MilXGraphic`` contains:
* ``MssStringXML``  – XML-escaped ``<Symbol ID="..."><Attribute .../>`` block.
  The symbol ID is an **APP-6B / MIL-STD-2525B 15-char** SIDC.
* ``Name``          – human-readable label.
* ``PointList``     – one ``<Point>`` per node (single point for unit symbols);
  X=longitude, Y=latitude in WGS-84.

APP-6B <-> APP-6D SIDC conversion
---------------------------------
The plugin uses the **APP-6D 20-char** format internally.  This module
provides best-effort bidirectional conversion keeping:

  * Standard Identity (affiliation)
  * Symbol Set (derived from Battle Dimension)
  * Status (Present / Planned)
  * Echelon (from modifier char at pos 11)

Function ID → entity code mapping is not possible in general, so on import
the entity code is left as ``000000`` (generic) and the original APP-6B SIDC
is saved in ``MilSymbol.additional_information`` for lossless round-tripping.

MilX Attribute IDs used
-----------------------
  T     – Unique Designation  → MilSymbol.designation
  M     – Higher Formation    → MilSymbol.higher_formation
  H     – Additional Info     → MilSymbol.comment
  N     – Hostile Name        → MilSymbol.designation (fallback)
  W     – DTG                 → MilSymbol.dtg
  Z     – Speed               → MilSymbol.speed
  X     – Altitude/Depth      → MilSymbol.altitude_depth
  AG    – Staff Comments      → MilSymbol.staff_comments
  Q     – Direction           → MilSymbol.direction
  APP6D – Full 20-char APP-6D SIDC (written by this plugin for lossless
          round-tripping; not part of the MilX standard)
"""

from __future__ import annotations

import html
import re
import uuid
import xml.etree.ElementTree as ET
from typing import Optional

from .models import MilSymbol

# ---------------------------------------------------------------------------
# Lazy lookup: (symset, entity_code) -> APP-6B 6-char function code
# Built once from catalog_data on first use.
# ---------------------------------------------------------------------------
_ENTITY_FUNCCODE_MAP: dict[tuple[str, str], str] = {}

def _get_entity_funccode_map() -> dict[tuple[str, str], str]:
    global _ENTITY_FUNCCODE_MAP
    if _ENTITY_FUNCCODE_MAP:
        return _ENTITY_FUNCCODE_MAP
    try:
        from ..symbology.catalog_data import (
            LAND_UNIT_ENTRIES, LAND_EQUIPMENT_ENTRIES,
            AIR_ENTRIES, SEA_SURFACE_ENTRIES, SEA_SUBSURFACE_ENTRIES,
        )
        for entries in (LAND_UNIT_ENTRIES, LAND_EQUIPMENT_ENTRIES,
                        AIR_ENTRIES, SEA_SURFACE_ENTRIES, SEA_SUBSURFACE_ENTRIES):
            for entry in entries:
                key = (entry.symbol_set, entry.entity_code)
                # First match wins – earlier entries have priority
                if key not in _ENTITY_FUNCCODE_MAP:
                    _ENTITY_FUNCCODE_MAP[key] = entry.app6b_func
    except Exception:
        pass
    return _ENTITY_FUNCCODE_MAP

# ---------------------------------------------------------------------------
# Namespace used in .milxly files
# ---------------------------------------------------------------------------
_MILX_NS = "http://gs-soft.com/MilX/V3.1"
_NS = {"m": _MILX_NS}

# Tag for the original APP-6B SIDC stored during import (for lossless export)
_MILX_ORIG_SIDC_TAG = "milxly_orig_sidc"

# ---------------------------------------------------------------------------
# APP-6B position 2 → APP-6D Standard Identity value
# ---------------------------------------------------------------------------
_AFFIL_6B_TO_6D: dict[str, str] = {
    "F": "3",   # Friend           → FRIEND
    "A": "2",   # Assumed Friend   → ASSUMED_FRIEND
    "N": "4",   # Neutral          → NEUTRAL
    "H": "6",   # Hostile          → HOSTILE_FAKER
    "U": "1",   # Unknown          → UNKNOWN
    "P": "0",   # Pending          → PENDING
    "S": "5",   # Suspect          → SUSPECT_JOKER
    "J": "5",   # Joker            → SUSPECT_JOKER
    "K": "6",   # Faker            → HOSTILE_FAKER
}

_AFFIL_6D_TO_6B: dict[str, str] = {
    "0": "P",   # Pending
    "1": "U",   # Unknown
    "2": "A",   # Assumed Friend
    "3": "F",   # Friend
    "4": "N",   # Neutral
    "5": "S",   # Suspect
    "6": "H",   # Hostile
}

# ---------------------------------------------------------------------------
# APP-6B position 3 (Battle Dimension) → APP-6D Symbol Set (2 digits)
# ---------------------------------------------------------------------------
_BATDIM_TO_SYMSET: dict[str, str] = {
    "G": "10",  # Ground → Land Unit
    "A": "01",  # Air    → Air
    "S": "30",  # Sea Surface → Sea Surface
    "U": "35",  # Subsurface  → Sea Subsurface
    "P": "05",  # Space
    "F": "10",  # SOF → Land Unit
    "Z": "10",  # Unknown dimension → default Land Unit
}

_SYMSET_TO_BATDIM: dict[str, str] = {
    "01": "A",
    "02": "A",
    "05": "P",
    "06": "P",
    "10": "G",
    "11": "G",
    "15": "G",
    "20": "G",
    "25": "G",
    "30": "S",
    "35": "U",
    "36": "U",
    "40": "Z",
    "45": "Z",
    "46": "Z",
    "47": "P",
    "50": "Z",
    "51": "A",
    "52": "G",
    "53": "S",
    "54": "U",
    "60": "G",
}

# ---------------------------------------------------------------------------
# APP-6B pos 4 (Status) → APP-6D status digit
# ---------------------------------------------------------------------------
_STATUS_6B_TO_6D: dict[str, str] = {
    "P": "0",   # Present
    "A": "1",   # Anticipated/Planned
}
_STATUS_6D_TO_6B: dict[str, str] = {"0": "P", "1": "A"}

# ---------------------------------------------------------------------------
# APP-6B echelon char (pos 11) → APP-6D amplifier (2 digits)
# ---------------------------------------------------------------------------
_ECHELON_6B_TO_6D: dict[str, str] = {
    "-": "00", "*": "00",
    "A": "11",  # Team/Crew
    "B": "12",  # Squad
    "C": "13",  # Section
    "D": "14",  # Platoon/Detachment
    "E": "15",  # Company/Battery/Troop
    "F": "16",  # Battalion/Squadron
    "G": "17",  # Regiment/Group
    "H": "18",  # Brigade
    "I": "21",  # Division
    "J": "22",  # Corps/MEF
    "K": "23",  # Army
    "L": "24",  # Army Group/Front
    "M": "25",  # Region
    "N": "00",  # Command (no direct equivalent)
}

_ECHELON_6D_TO_6B: dict[str, str] = {
    "00": "-",
    "11": "A",
    "12": "B",
    "13": "C",
    "14": "D",
    "15": "E",
    "16": "F",
    "17": "G",
    "18": "H",
    "21": "I",
    "22": "J",
    "23": "K",
    "24": "L",
    "25": "M",
}


# ===========================================================================
# SIDC conversion helpers
# ===========================================================================

def milx_sidc_to_app6d(milx_sidc: str) -> str:
    """Convert an APP-6B 15-char SIDC to an APP-6D 20-char SIDC.

    Preserves: affiliation, battle-dimension→symbol-set, status, echelon.
    Entity code is set to "000000" (generic) – the original SIDC should be
    stored separately for lossless export.
    """
    s = milx_sidc.replace("-", "-").upper()
    # Pad / normalise to 15 chars
    s = (s + "---------------")[:15]

    affil   = _AFFIL_6B_TO_6D.get(s[1], "1")          # pos 2 → identity
    batdim  = s[2]
    symset  = _BATDIM_TO_SYMSET.get(batdim, "10")      # pos 3 → symbol set
    status  = _STATUS_6B_TO_6D.get(s[3], "0")          # pos 4 → status

    # MSS/MilX SIDC convention:
    #   pos 11 (index 10) = HQ/TF modifier  (space/A/B)
    #   pos 12 (index 11) = echelon letter  (A-N)
    hq_char = s[10] if len(s) > 10 else "-"
    echelon = _ECHELON_6B_TO_6D.get(s[11], "00")       # pos 12 → amplifier

    hqtf = "0"
    if hq_char == "A":
        hqtf = "2"   # HQ
    elif hq_char == "B":
        hqtf = "4"   # Task Force

    return f"10{0}{affil}{symset}{status}{hqtf}{echelon}0000000000"


def app6d_sidc_to_milx(sidc20: str, orig_milx_sidc: str = "") -> str:
    """Convert an APP-6D 20-char SIDC to an APP-6B 15-char MilX SIDC.

    If *orig_milx_sidc* is provided (stored from a previous import) and the
    affiliation/status still matches, it is returned directly for lossless
    round-tripping.
    """
    if len(sidc20) != 20:
        return "SUGPU---------"

    identity  = sidc20[3]
    symset    = sidc20[4:6]
    status_d  = sidc20[6]
    hqtf      = sidc20[7]
    echelon_d = sidc20[8:10]

    # If the original MilX SIDC is stored and still represents the same
    # affiliation + status, prefer it (preserves function ID).
    if orig_milx_sidc and len(orig_milx_sidc) == 15:
        orig_affil  = _AFFIL_6B_TO_6D.get(orig_milx_sidc[1].upper(), "?")
        orig_status = _STATUS_6B_TO_6D.get(orig_milx_sidc[3].upper(), "?")
        if orig_affil == identity and orig_status == status_d:
            # Patch echelon and HQ/TF back into the original APP-6B SIDC
            # MSS convention: pos 11 (index 10) = HQ/TF, pos 12 (index 11) = echelon
            echelon_c = _ECHELON_6D_TO_6B.get(echelon_d, "-")
            s = list(orig_milx_sidc.upper())
            s[11] = echelon_c          # echelon at pos 12 (index 11)
            # Patch HQ/TF modifier at pos 11 (index 10)
            if hqtf == "2":
                s[10] = "A"
            elif hqtf == "4":
                s[10] = "B"
            else:
                s[10] = "-"
            return "".join(s)

    # Build from scratch
    affil_c   = _AFFIL_6D_TO_6B.get(identity, "U")
    batdim_c  = _SYMSET_TO_BATDIM.get(symset, "G")
    status_c  = _STATUS_6D_TO_6B.get(status_d, "P")
    echelon_c = _ECHELON_6D_TO_6B.get(echelon_d, "-")
    hq_c      = "A" if hqtf == "2" else ("B" if hqtf == "4" else "-")

    # Look up APP-6B function code from entity code
    entity_code = sidc20[10:16]
    func_map = _get_entity_funccode_map()
    func_code = func_map.get((symset, entity_code), "------")

    # Pos 1=S(Warfighting), 2=affil, 3=batdim, 4=status, 5-10=func,
    # 11=hq (MSS convention), 12=echelon, 13-15=country/OOB (---)
    return f"S{affil_c}{batdim_c}{status_c}{func_code}{hq_c}{echelon_c}---"


# ===========================================================================
# MssStringXML helpers
# ===========================================================================

def _parse_mss_string(mss_xml_escaped: str) -> tuple[str, dict[str, str]]:
    """Parse the MssStringXML text content.

    ElementTree already unescapes the text node, so *mss_xml_escaped* is
    actually the raw inner XML (e.g. ``<Symbol ID="SFGP...">``).
    The ``html.unescape`` call is kept as a safety net for edge cases.
    Returns ``(symbol_id, {attr_id: attr_value, ...})``.
    """
    raw = html.unescape(mss_xml_escaped.strip())
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return "", {}

    symbol_id = root.get("ID", "")
    attrs: dict[str, str] = {}
    for attr_el in root.findall("Attribute"):
        aid = attr_el.get("ID", "")
        if aid:
            attrs[aid] = (attr_el.text or "").strip()
    return symbol_id, attrs


def _build_mss_string(milx_sidc: str, attrs: dict[str, str]) -> str:
    """Build the raw (unescaped) XML content for MssStringXML.

    The returned string is raw XML, e.g.::

        <Symbol ID="SFGP------K----"><Attribute ID="T">CHE AF</Attribute></Symbol>

    ElementTree will correctly single-escape it (``<`` → ``&lt;``, etc.)
    when serialising the outer XML document.  Do NOT pre-escape here —
    that would produce double-escaped output (``&amp;lt;``) which MSS
    cannot parse.
    """
    attr_parts = "".join(
        f'<Attribute ID="{k}">{html.escape(v)}</Attribute>'
        for k, v in attrs.items()
        if v
    )
    return f'<Symbol ID="{milx_sidc}">{attr_parts}</Symbol>'


# ===========================================================================
# Public API
# ===========================================================================

def import_milxly(path: str) -> tuple[str, list[MilSymbol]]:
    """Parse a ``.milxly`` file and return ``(layer_name, [MilSymbol, ...])``.

    Parameters
    ----------
    path : str
        Absolute path to the ``.milxly`` file.

    Returns
    -------
    tuple[str, list[MilSymbol]]
        The layer name from the XML and all imported symbols.

    Raises
    ------
    ValueError
        If the file is not a valid MilXDocument_Layer.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    # Handle namespace prefix
    tag = root.tag
    if tag not in (f"{{{_MILX_NS}}}MilXDocument_Layer", "MilXDocument_Layer"):
        raise ValueError(f"Not a MilXDocument_Layer file (root tag: {tag!r})")

    def _find(el, *names):
        for name in names:
            child = el.find(f"{{{_MILX_NS}}}{name}")
            if child is None:
                child = el.find(name)
            if child is not None:
                el = child
            else:
                return None
        return el

    layer_el = _find(root, "MilXLayer")
    if layer_el is None:
        raise ValueError("No <MilXLayer> element found")

    name_el = _find(layer_el, "Name")
    layer_name = name_el.text.strip() if name_el is not None and name_el.text else "MilX Import"

    gl_el = _find(layer_el, "GraphicList")
    if gl_el is None:
        return layer_name, []

    symbols: list[MilSymbol] = []

    for g_el in (gl_el.findall(f"{{{_MILX_NS}}}MilXGraphic") or gl_el.findall("MilXGraphic")):
        # -- MssStringXML --
        mss_el = _find(g_el, "MssStringXML")
        milx_sidc = ""
        milx_attrs: dict[str, str] = {}
        if mss_el is not None and mss_el.text:
            milx_sidc, milx_attrs = _parse_mss_string(mss_el.text)

        # -- Graphic name --
        gname_el = _find(g_el, "Name")
        graphic_name = gname_el.text.strip() if gname_el is not None and gname_el.text else ""

        # -- PointList (first point) --
        pl_el = _find(g_el, "PointList")
        lon, lat = 0.0, 0.0
        if pl_el is not None:
            first_pt = (
                pl_el.find(f"{{{_MILX_NS}}}Point") or pl_el.find("Point")
            )
            if first_pt is not None:
                x_el = _find(first_pt, "X")
                y_el = _find(first_pt, "Y")
                try:
                    lon = float(x_el.text) if x_el is not None else 0.0
                    lat = float(y_el.text) if y_el is not None else 0.0
                except (ValueError, TypeError):
                    pass

        # -- Convert SIDC --
        # If the file was written by this plugin it carries the full 20-char
        # APP-6D SIDC in a custom APP6D attribute → use it directly so that
        # entity codes, modifiers and echelon are perfectly preserved.
        app6d_attr = milx_attrs.get("APP6D", "").strip()
        if app6d_attr and len(app6d_attr) == 20 and app6d_attr.isalnum():
            sidc20 = app6d_attr
            orig_for_export = milx_sidc   # keep APP-6B SIDC for MSS round-trip
        else:
            sidc20 = milx_sidc_to_app6d(milx_sidc) if milx_sidc else "10031000000000000000"
            orig_for_export = milx_sidc   # store original MSS SIDC

        # -- Build MilSymbol --
        sym = MilSymbol(
            id=str(uuid.uuid4()),
            sidc=sidc20,
            designation=milx_attrs.get("T", "") or graphic_name,
            higher_formation=milx_attrs.get("M", ""),
            comment=milx_attrs.get("H", ""),
            staff_comments=milx_attrs.get("AG", ""),
            dtg=milx_attrs.get("W", ""),
            speed=milx_attrs.get("Z", ""),
            altitude_depth=milx_attrs.get("X", ""),
            additional_information=orig_for_export,   # store original for lossless export
            longitude=lon,
            latitude=lat,
        )
        # Direction (Q attribute, degrees)
        q_val = milx_attrs.get("Q", "")
        if q_val:
            try:
                sym.direction = float(q_val)
            except ValueError:
                pass

        symbols.append(sym)

    return layer_name, symbols


def export_milxly(
    symbols: list[MilSymbol],
    layer_name: str,
    path: str,
    *,
    symbol_size: float = 12.0,
    coord_system: str = "WGS84",
    library_version: str = "2025.02.20",
) -> None:
    """Write *symbols* to a ``.milxly`` file.

    Parameters
    ----------
    symbols : list[MilSymbol]
        Symbols to export.
    layer_name : str
        Name written into the ``<MilXLayer><Name>`` element.
    path : str
        Output file path (will be overwritten if exists).
    symbol_size : float
        Hint for rendering tools; written into ``<SymbolSize>``.
    coord_system : str
        Written into ``<CoordSystemType>``; should be "WGS84".
    library_version : str
        Written into ``<MssLibraryVersionTag>``.
    """
    root = ET.Element("MilXDocument_Layer", xmlns=_MILX_NS)
    ver_el = ET.SubElement(root, "MssLibraryVersionTag")
    ver_el.text = library_version

    layer_el = ET.SubElement(root, "MilXLayer")
    name_el = ET.SubElement(layer_el, "Name")
    name_el.text = layer_name
    type_el = ET.SubElement(layer_el, "LayerType")
    type_el.text = "Normal"

    gl_el = ET.SubElement(layer_el, "GraphicList")

    for sym in symbols:
        # Retrieve original MilX SIDC if available
        orig_milx = sym.additional_information or ""
        milx_sidc = app6d_sidc_to_milx(sym.sidc, orig_milx)

        # Build MilX attributes
        attrs: dict[str, str] = {}
        if sym.designation:
            attrs["T"] = sym.designation
        if sym.higher_formation:
            attrs["M"] = sym.higher_formation
        if sym.comment:
            attrs["H"] = sym.comment
        if sym.staff_comments:
            attrs["AG"] = sym.staff_comments
        if sym.dtg:
            attrs["W"] = sym.dtg
        if sym.speed:
            attrs["Z"] = sym.speed
        if sym.altitude_depth:
            attrs["X"] = sym.altitude_depth
        if sym.direction is not None:
            attrs["Q"] = str(sym.direction)
        # Always embed the full 20-char APP-6D SIDC so that re-importing
        # into this plugin recovers entity codes and modifiers exactly.
        if sym.sidc and len(sym.sidc) == 20:
            attrs["APP6D"] = sym.sidc

        g_el = ET.SubElement(gl_el, "MilXGraphic")

        mss_el = ET.SubElement(g_el, "MssStringXML")
        mss_el.text = _build_mss_string(milx_sidc, attrs)

        gname_el = ET.SubElement(g_el, "Name")
        gname_el.text = sym.designation or milx_sidc

        pl_el = ET.SubElement(g_el, "PointList")
        pt_el = ET.SubElement(pl_el, "Point")
        x_el = ET.SubElement(pt_el, "X")
        x_el.text = f"{sym.longitude:.6f}"
        y_el = ET.SubElement(pt_el, "Y")
        y_el.text = f"{sym.latitude:.6f}"

        off_el = ET.SubElement(g_el, "Offset")
        ET.SubElement(off_el, "FactorX").text = "0"
        ET.SubElement(off_el, "FactorY").text = "0"

    coord_el = ET.SubElement(layer_el, "CoordSystemType")
    coord_el.text = coord_system
    size_el = ET.SubElement(layer_el, "SymbolSize")
    size_el.text = str(symbol_size)

    _indent_tree(root)
    tree = ET.ElementTree(root)
    ET.register_namespace("", _MILX_NS)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
        tree.write(fh, encoding="unicode", xml_declaration=False)


# ---------------------------------------------------------------------------
# Pretty-print helper (Python < 3.9 compatible)
# ---------------------------------------------------------------------------

def _indent_tree(elem: ET.Element, level: int = 0) -> None:
    """Add indentation whitespace to an ElementTree in-place."""
    indent = "\n" + "\t" * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "\t"
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            _indent_tree(child, level + 1)
        if not child.tail or not child.tail.strip():  # noqa: F821
            child.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent
