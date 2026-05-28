# -*- coding: utf-8 -*-
"""
Data models for military symbols, ORBAT units and temporal attributes.

All models are plain Python dataclasses – no external dependencies.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

from .sidc import SIDC


# ======================================================================
# Temporal attribute
# ======================================================================

@dataclass
class TemporalExtent:
    """Time validity window for a map feature or ORBAT unit.

    Both *start* and *end* are ISO-8601 strings ("YYYY-MM-DDTHH:MM:SS").
    If *end* is ``None`` the feature is valid from *start* onward.
    """

    start: str = ""
    end: Optional[str] = None

    def contains(self, iso_time: str) -> bool:
        """Return True if *iso_time* falls within [start, end]."""
        if not self.start:
            return True
        t = iso_time
        if t < self.start:
            return False
        if self.end and t > self.end:
            return False
        return True


# ======================================================================
# Military symbol on the map
# ======================================================================

@dataclass
class MilSymbol:
    """A military symbol instance placed on the map.

    This is the authoritative record stored in the project JSON and
    painted via ``KadasItemLayer``.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sidc: str = "10031000000000000000"   # default: friendly land unit
    designation: str = ""               # short name / designator
    higher_formation: str = ""          # parent formation label
    comment: str = ""                   # mapped to multiple fields if necessary, or just general comment
    quantity: str = ""
    staff_comments: str = ""
    additional_information: str = ""
    evaluation_rating: str = ""
    combat_effectiveness: str = ""
    dtg: str = ""
    type_str: str = ""
    speed: str = ""
    altitude_depth: str = ""
    direction: Optional[float] = None
    # Coordinates (EPSG:4326)
    longitude: float = 0.0
    latitude: float = 0.0
    # Temporal
    temporal: TemporalExtent = field(default_factory=TemporalExtent)
    # Optional link to ORBAT unit
    orbat_unit_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MilSymbol":
        temporal = d.pop("temporal", {})
        sym = cls(**d)
        if isinstance(temporal, dict):
            sym.temporal = TemporalExtent(**temporal)
        return sym

    def parsed_sidc(self) -> SIDC:
        """Return a structured SIDC object."""
        return SIDC.parse(self.sidc)


# ======================================================================
# ORBAT Unit (node in the hierarchy)
# ======================================================================

@dataclass
class OrbatUnit:
    """A unit in an Order of Battle tree.

    Each unit has a *parent_id* linking it to its superior.  The root
    unit has ``parent_id = None``.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sidc: str = "10031000000000000000"
    name: str = ""                      # e.g. "1st Battalion, 3rd Infantry"
    short_name: str = ""                # e.g. "1/3 Inf"
    parent_id: Optional[str] = None
    # Temporal
    temporal: TemporalExtent = field(default_factory=TemporalExtent)
    # Location (filled when placed on map)
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    # Link to the corresponding MilSymbol on the map (if any)
    map_symbol_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "OrbatUnit":
        temporal = d.pop("temporal", {})
        unit = cls(**d)
        if isinstance(temporal, dict):
            unit.temporal = TemporalExtent(**temporal)
        return unit


# ======================================================================
# ORBAT (the complete Order of Battle)
# ======================================================================

@dataclass
class Orbat:
    """An Order of Battle – a flat list of :class:`OrbatUnit` nodes
    linked by *parent_id* to form a tree hierarchy."""

    name: str = "New ORBAT"
    units: list[OrbatUnit] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Tree helpers
    # ------------------------------------------------------------------

    def root_units(self) -> list[OrbatUnit]:
        """Return units that have no parent."""
        return [u for u in self.units if u.parent_id is None]

    def children_of(self, unit_id: str) -> list[OrbatUnit]:
        """Return direct children of *unit_id*."""
        return [u for u in self.units if u.parent_id == unit_id]

    def unit_by_id(self, unit_id: str) -> Optional[OrbatUnit]:
        for u in self.units:
            if u.id == unit_id:
                return u
        return None

    def add_unit(self, unit: OrbatUnit) -> None:
        self.units.append(unit)

    def remove_unit(self, unit_id: str) -> None:
        """Remove a unit and re-parent its children to its parent."""
        unit = self.unit_by_id(unit_id)
        if unit is None:
            return
        parent_id = unit.parent_id
        for child in self.children_of(unit_id):
            child.parent_id = parent_id
        self.units = [u for u in self.units if u.id != unit_id]

    def move_unit(self, unit_id: str, new_parent_id: Optional[str]) -> None:
        """Re-parent a unit."""
        unit = self.unit_by_id(unit_id)
        if unit is not None:
            unit.parent_id = new_parent_id

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "units": [u.to_dict() for u in self.units],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Orbat":
        orbat = cls(name=d.get("name", "ORBAT"))
        for ud in d.get("units", []):
            orbat.add_unit(OrbatUnit.from_dict(ud))
        return orbat

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "Orbat":
        return cls.from_dict(json.loads(text))


# ======================================================================
# Symbol layer (named group of symbols)
# ======================================================================

@dataclass
class SymbolLayer:
    """A named collection of :class:`MilSymbol` instances.

    Each layer maps to a separate ``QgsVectorLayer`` on the map canvas.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Default"
    visible: bool = True
    symbols: list[MilSymbol] = field(default_factory=list)

    # -- helpers -------------------------------------------------------

    def symbol_by_id(self, sym_id: str) -> Optional[MilSymbol]:
        for s in self.symbols:
            if s.id == sym_id:
                return s
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "visible": self.visible,
            "symbols": [s.to_dict() for s in self.symbols],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SymbolLayer":
        layer = cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Layer"),
            visible=d.get("visible", True),
        )
        for sd in d.get("symbols", []):
            layer.symbols.append(MilSymbol.from_dict(sd))
        return layer


# ======================================================================
# Project data container
# ======================================================================

@dataclass
class MilSymbProject:
    """Top-level container holding all plugin data for a KADAS project.

    Symbols are organised into named *layers*.  Legacy project files
    that stored a flat ``"symbols"`` list are automatically migrated
    into a single ``"Default"`` layer on load.
    """

    layers: list[SymbolLayer] = field(default_factory=lambda: [SymbolLayer()])
    orbats: list[Orbat] = field(default_factory=list)

    # -- convenience: flat view of all symbols across layers -----------

    @property
    def symbols(self) -> list[MilSymbol]:
        """Flat list of every symbol across all layers (read-only view)."""
        result: list[MilSymbol] = []
        for lyr in self.layers:
            result.extend(lyr.symbols)
        return result

    # -- layer helpers -------------------------------------------------

    def layer_by_id(self, layer_id: str) -> Optional[SymbolLayer]:
        for lyr in self.layers:
            if lyr.id == layer_id:
                return lyr
        return None

    def layer_by_name(self, name: str) -> Optional[SymbolLayer]:
        for lyr in self.layers:
            if lyr.name == name:
                return lyr
        return None

    def default_layer(self) -> SymbolLayer:
        """Return the first layer, creating one if the list is empty."""
        if not self.layers:
            self.layers.append(SymbolLayer())
        return self.layers[0]

    def add_layer(self, name: str = "New Layer") -> SymbolLayer:
        lyr = SymbolLayer(name=name)
        self.layers.append(lyr)
        return lyr

    def remove_layer(self, layer_id: str) -> bool:
        before = len(self.layers)
        self.layers = [lyr for lyr in self.layers if lyr.id != layer_id]
        return len(self.layers) < before

    def rename_layer(self, layer_id: str, new_name: str) -> bool:
        lyr = self.layer_by_id(layer_id)
        if lyr is None:
            return False
        lyr.name = new_name
        return True

    # -- symbol lookup -------------------------------------------------

    def symbol_by_id(self, sym_id: str) -> Optional[MilSymbol]:
        for lyr in self.layers:
            s = lyr.symbol_by_id(sym_id)
            if s is not None:
                return s
        return None

    def layer_of_symbol(self, sym_id: str) -> Optional[SymbolLayer]:
        """Return the layer that contains the symbol with *sym_id*."""
        for lyr in self.layers:
            if lyr.symbol_by_id(sym_id) is not None:
                return lyr
        return None

    # -- serialisation -------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {
                "kadas_milsymb_version": "0.2.0",
                "layers": [lyr.to_dict() for lyr in self.layers],
                "orbats": [o.to_dict() for o in self.orbats],
            },
            indent=indent,
            ensure_ascii=False,
        )

    def layer_to_json(self, layer_id: str, indent: int = 2) -> Optional[str]:
        """Serialise a single layer to JSON (for per-layer export)."""
        lyr = self.layer_by_id(layer_id)
        if lyr is None:
            return None
        return json.dumps(
            {
                "kadas_milsymb_version": "0.2.0",
                "layer": lyr.to_dict(),
            },
            indent=indent,
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, text: str) -> "MilSymbProject":
        d = json.loads(text)
        proj = cls(layers=[])

        # --- v0.2+ format: "layers" list ---
        if "layers" in d:
            for ld in d["layers"]:
                proj.layers.append(SymbolLayer.from_dict(ld))
        # --- legacy v0.1 format: flat "symbols" list ---
        elif "symbols" in d:
            default = SymbolLayer(name="Default")
            for sd in d["symbols"]:
                default.symbols.append(MilSymbol.from_dict(sd))
            proj.layers.append(default)
        # --- single-layer import ---
        elif "layer" in d:
            proj.layers.append(SymbolLayer.from_dict(d["layer"]))

        # Ensure at least one layer exists
        if not proj.layers:
            proj.layers.append(SymbolLayer())

        for od in d.get("orbats", []):
            proj.orbats.append(Orbat.from_dict(od))
        return proj
