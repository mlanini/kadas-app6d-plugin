# -*- coding: utf-8 -*-
"""
KMZ / KML import / export for the KADAS APP-6(D) plugin.

Format description
------------------
A ``.kmz`` file is a ZIP archive containing a ``doc.kml`` root document
plus optional inline resources (e.g. PNG icons).

Each military symbol is represented as a KML ``<Placemark>``:

* ``<name>``           – MilSymbol.designation
* ``<description>``    – MilSymbol.comment (CDATA)
* ``<Point><coordinates>`` – lon,lat,0
* ``<ExtendedData>``   – plugin-specific fields encoded as ``<Data>`` elements:

    APP6D_SIDC             full 20-char APP-6D SIDC  (required for lossless round-trip)
    HIGHER_FORMATION
    QUANTITY
    STAFF_COMMENTS
    ADDITIONAL_INFO
    EVALUATION_RATING
    COMBAT_EFFECTIVENESS
    DTG
    TYPE_STR
    SPEED
    ALTITUDE_DEPTH
    DIRECTION              float degrees (omitted when None)
    TEMPORAL_START
    TEMPORAL_END
    ORBAT_UNIT_ID

On **import** the ``APP6D_SIDC`` field is used when present; otherwise the
``<styleUrl>`` or ``<description>`` is scanned for a 20-char hex string that
looks like an APP-6D SIDC.  If none is found the symbol defaults to a generic
friendly land-unit SIDC.

On **export** each Placemark additionally gets:
* a ``<Style>`` with an ``<IconStyle>`` pointing to an inline PNG rendered from
  the SVG symbology (64 × 64 px, stored as ``icons/<sym_id>.png`` inside the
  KMZ archive).  Falls back silently if Qt or the renderer is unavailable.
"""

from __future__ import annotations

import os
import re
import zipfile
import xml.etree.ElementTree as ET

from .models import MilSymbol, TemporalExtent

# ---------------------------------------------------------------------------
# KML namespace
# ---------------------------------------------------------------------------
_KML_NS = "http://www.opengis.net/kml/2.2"
_XKML_NS = "http://www.google.com/kml/ext/2.2"
ET.register_namespace("", _KML_NS)
ET.register_namespace("gx", _XKML_NS)

_KML_TAG = f"{{{_KML_NS}}}"

# Regex that matches a 20-char APP-6D SIDC (all hex digits)
_SIDC_RE = re.compile(r"\b[0-9A-Fa-f]{20}\b")

# Default SIDC: version=10, context=0, identity=3(Friend), symset=10(LandUnit),
# status=0(Present), hq=0, echelon=0(none), entity=000000, mod1=00, mod2=00
_DEFAULT_SIDC = "10031000000000000000"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _kml_text(elem: ET.Element, tag: str, ns: str = _KML_NS) -> str:
    """Return stripped text of first matching child, or ''."""
    child = elem.find(f"{{{ns}}}{tag}")
    return (child.text or "").strip() if child is not None else ""


def _extended_data_map(placemark: ET.Element) -> dict[str, str]:
    """Return {name -> value} from <ExtendedData><Data name=...><value>."""
    result: dict[str, str] = {}
    ed = placemark.find(f"{_KML_TAG}ExtendedData")
    if ed is None:
        return result
    for data in ed.findall(f"{_KML_TAG}Data"):
        name = data.get("name", "")
        val_el = data.find(f"{_KML_TAG}value")
        if name and val_el is not None:
            result[name] = (val_el.text or "").strip()
    return result


def _find_sidc(placemark: ET.Element, ext: dict[str, str]) -> str:
    """Best-effort SIDC extraction from a Placemark."""
    # 1. Explicit APP-6D field
    sidc = ext.get("APP6D_SIDC", "")
    if sidc and len(sidc) == 20:
        return sidc
    # 2. Scan name / description / styleUrl for a 20-char hex token
    for tag in ("name", "description", "styleUrl"):
        text = _kml_text(placemark, tag)
        m = _SIDC_RE.search(text)
        if m:
            return m.group(0)
    return _DEFAULT_SIDC


def _coords_from_placemark(placemark: ET.Element) -> tuple[float, float] | None:
    """Return (lon, lat) from the first <Point><coordinates> found."""
    point = placemark.find(f".//{_KML_TAG}Point")
    if point is None:
        return None
    coords_el = point.find(f"{_KML_TAG}coordinates")
    if coords_el is None or not coords_el.text:
        return None
    parts = coords_el.text.strip().split(",")
    if len(parts) < 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Icon rendering helper (optional – requires Qt + symbology)
# ---------------------------------------------------------------------------

def _render_icon_png(sidc: str, size: int = 64) -> bytes | None:
    """Render a symbol to PNG bytes.  Returns None on any failure."""
    try:
        from ..symbology.renderer import cached_svg
        from qgis.PyQt.QtCore import QByteArray
        from qgis.PyQt.QtGui import QImage, QPainter, QPixmap
        from qgis.PyQt.QtSvg import QSvgRenderer

        svg_str = cached_svg(sidc)
        renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
        if not renderer.isValid():
            return None
        image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()

        pixmap = QPixmap.fromImage(image)
        ba = QByteArray()
        from qgis.PyQt.QtCore import QBuffer, QIODevice
        buffer = QBuffer(ba)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        return bytes(ba)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def import_kmz(path: str) -> tuple[str, list[MilSymbol]]:
    """Import all Placemarks from a KMZ or KML file.

    Parameters
    ----------
    path : str
        Path to ``.kmz`` or ``.kml`` file.

    Returns
    -------
    layer_name : str
        Suggested layer name (basename without extension).
    symbols : list[MilSymbol]
        Parsed symbols.  Non-Point placemarks are silently skipped.
    """
    layer_name = os.path.splitext(os.path.basename(path))[0]

    # Read raw KML text
    if path.lower().endswith(".kmz"):
        with zipfile.ZipFile(path, "r") as zf:
            # Find the root KML document (usually doc.kml)
            kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not kml_names:
                raise ValueError("No .kml file found inside the KMZ archive.")
            # Prefer doc.kml at root level, else first match
            root_kml = next(
                (n for n in kml_names if n.lower() == "doc.kml"),
                kml_names[0],
            )
            kml_text = zf.read(root_kml).decode("utf-8", errors="replace")
    elif path.lower().endswith(".kml"):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            kml_text = fh.read()
    else:
        raise ValueError(f"Unsupported file extension: {os.path.basename(path)}")

    root = ET.fromstring(kml_text)

    symbols: list[MilSymbol] = []

    for placemark in root.iter(f"{_KML_TAG}Placemark"):
        coords = _coords_from_placemark(placemark)
        if coords is None:
            continue  # skip non-Point features

        lon, lat = coords
        ext = _extended_data_map(placemark)
        sidc = _find_sidc(placemark, ext)
        name = _kml_text(placemark, "name") or _kml_text(placemark, "description")
        description = _kml_text(placemark, "description")

        sym = MilSymbol(
            sidc=sidc,
            designation=name,
            higher_formation=ext.get("HIGHER_FORMATION", ""),
            comment=description,
            quantity=ext.get("QUANTITY", ""),
            staff_comments=ext.get("STAFF_COMMENTS", ""),
            additional_information=ext.get("ADDITIONAL_INFO", ""),
            evaluation_rating=ext.get("EVALUATION_RATING", ""),
            combat_effectiveness=ext.get("COMBAT_EFFECTIVENESS", ""),
            dtg=ext.get("DTG", ""),
            type_str=ext.get("TYPE_STR", ""),
            speed=ext.get("SPEED", ""),
            altitude_depth=ext.get("ALTITUDE_DEPTH", ""),
            direction=float(ext["DIRECTION"]) if ext.get("DIRECTION") else None,
            longitude=lon,
            latitude=lat,
            temporal=TemporalExtent(
                start=ext.get("TEMPORAL_START", ""),
                end=ext.get("TEMPORAL_END") or None,
            ),
            orbat_unit_id=ext.get("ORBAT_UNIT_ID") or None,
        )
        symbols.append(sym)

    return layer_name, symbols


def export_kmz(
    symbols: list[MilSymbol],
    layer_name: str,
    path: str,
    *,
    render_icons: bool = True,
) -> None:
    """Export a list of MilSymbol instances to a KMZ file.

    Parameters
    ----------
    symbols : list[MilSymbol]
        Symbols to export.
    layer_name : str
        Used as the KML ``<Document><name>``.
    path : str
        Output path (should end in ``.kmz``).
    render_icons : bool
        If True (default) renders PNG icons from SVG symbology and embeds
        them inside the KMZ.  Set to False to skip icon rendering (faster,
        but Google Earth will show a default pin icon).
    """
    # Build KML document tree
    kml_root = ET.Element(f"{{{_KML_NS}}}kml")
    doc = ET.SubElement(kml_root, f"{{{_KML_NS}}}Document")
    ET.SubElement(doc, f"{{{_KML_NS}}}name").text = layer_name

    # Collect icon PNG bytes: sym_id -> bytes
    icon_data: dict[str, bytes] = {}

    for sym in symbols:
        pm = ET.SubElement(doc, f"{{{_KML_NS}}}Placemark")
        ET.SubElement(pm, f"{{{_KML_NS}}}name").text = sym.designation or sym.sidc

        if sym.comment:
            ET.SubElement(pm, f"{{{_KML_NS}}}description").text = sym.comment

        # Icon style
        if render_icons:
            png_bytes = _render_icon_png(sym.sidc)
            if png_bytes:
                icon_data[sym.id] = png_bytes
                style = ET.SubElement(pm, f"{{{_KML_NS}}}Style")
                icon_style = ET.SubElement(style, f"{{{_KML_NS}}}IconStyle")
                icon_el = ET.SubElement(icon_style, f"{{{_KML_NS}}}Icon")
                ET.SubElement(icon_el, f"{{{_KML_NS}}}href").text = (
                    f"icons/{sym.id}.png"
                )

        # Geometry
        point = ET.SubElement(pm, f"{{{_KML_NS}}}Point")
        ET.SubElement(point, f"{{{_KML_NS}}}coordinates").text = (
            f"{sym.longitude},{sym.latitude},0"
        )

        # Extended data
        ed = ET.SubElement(pm, f"{{{_KML_NS}}}ExtendedData")

        def _add(name: str, value: str | None) -> None:
            if value is None or value == "":
                return
            d = ET.SubElement(ed, f"{{{_KML_NS}}}Data", name=name)
            ET.SubElement(d, f"{{{_KML_NS}}}value").text = str(value)

        _add("APP6D_SIDC",           sym.sidc)
        _add("HIGHER_FORMATION",     sym.higher_formation)
        _add("QUANTITY",             sym.quantity)
        _add("STAFF_COMMENTS",       sym.staff_comments)
        _add("ADDITIONAL_INFO",      sym.additional_information)
        _add("EVALUATION_RATING",    sym.evaluation_rating)
        _add("COMBAT_EFFECTIVENESS", sym.combat_effectiveness)
        _add("DTG",                  sym.dtg)
        _add("TYPE_STR",             sym.type_str)
        _add("SPEED",                sym.speed)
        _add("ALTITUDE_DEPTH",       sym.altitude_depth)
        if sym.direction is not None:
            _add("DIRECTION", str(sym.direction))
        _add("TEMPORAL_START",  sym.temporal.start)
        _add("TEMPORAL_END",    sym.temporal.end)
        _add("ORBAT_UNIT_ID",   sym.orbat_unit_id)

    # Serialise KML
    ET.indent(kml_root)
    kml_bytes = ET.tostring(kml_root, encoding="utf-8", xml_declaration=True)

    # Write KMZ (ZIP)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_bytes)
        for sym_id, png_bytes in icon_data.items():
            zf.writestr(f"icons/{sym_id}.png", png_bytes)
