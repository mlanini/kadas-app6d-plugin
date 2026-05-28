# -*- coding: utf-8 -*-
"""
APP-6(D) Symbol Identification Code (SIDC) parser and data model.

Supports both:
- **APP-6D / MIL-STD-2525D**: 20-character alphanumeric SIDC
- **MIL-STD-2525C (legacy)**: 15-character SIDC with dashes/asterisks

APP-6D positional structure (20 chars):
  Pos  1-2   : Version (e.g. "10" for APP-6D)
  Pos  3     : Context  (0=Reality, 1=Exercise, 2=Simulation)
  Pos  4     : Standard Identity (0-6)
  Pos  5-6   : Symbol Set  (01-99)
  Pos  7     : Status (0=Present, 1=Planned/Anticipated)
  Pos  8     : HQ / Task Force / Dummy  (0-7)
  Pos  9-10  : Amplifier / Descriptor (Echelon, Mobility, Towed Array)
  Pos 11-16  : Entity / Entity Type / Entity Subtype
  Pos 17-18  : Modifier 1 (Sector 1)
  Pos 19-20  : Modifier 2 (Sector 2)

MIL-STD-2525C positional structure (15 chars):
  Pos  1     : Coding scheme (S=Warfighting, I=Intelligence, etc.)
  Pos  2     : Affiliation (F=Friend, H=Hostile, N=Neutral, U=Unknown, etc.)
  Pos  3     : Battle dimension (G=Ground, A=Air, S=Sea, U=Subsurface, P=Space)
  Pos  4     : Status (P=Present, A=Anticipated/Planned)
  Pos  5-10  : Function ID (6 chars)
  Pos 11-12  : Symbol modifier (2 chars)
  Pos 13-14  : Country code (2 chars)
  Pos 15     : Order of Battle (- = none)
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ======================================================================
# Enumerations
# ======================================================================

class Context(Enum):
    """Pos 3 – Operational context."""
    REALITY = "0"
    EXERCISE = "1"
    SIMULATION = "2"


class StandardIdentity(Enum):
    """Pos 4 – Affiliation / Standard Identity."""
    PENDING = "0"
    UNKNOWN = "1"
    ASSUMED_FRIEND = "2"
    FRIEND = "3"
    NEUTRAL = "4"
    SUSPECT_JOKER = "5"
    HOSTILE_FAKER = "6"


# User-friendly display labels for the UI combo boxes
STANDARD_IDENTITY_LABELS: dict[StandardIdentity, str] = {
    StandardIdentity.PENDING: "Pending",
    StandardIdentity.UNKNOWN: "Unknown",
    StandardIdentity.ASSUMED_FRIEND: "Assumed Friend",
    StandardIdentity.FRIEND: "Friend",
    StandardIdentity.NEUTRAL: "Neutral",
    StandardIdentity.SUSPECT_JOKER: "Suspect / Joker",
    StandardIdentity.HOSTILE_FAKER: "Hostile",
}


class SymbolSet(Enum):
    """Pos 5-6 – Symbol Set codes."""
    AIR = "01"
    AIR_MISSILE = "02"
    SPACE = "05"
    SPACE_MISSILE = "06"
    LAND_UNIT = "10"
    LAND_CIVILIAN = "11"
    LAND_EQUIPMENT = "15"
    LAND_INSTALLATION = "20"
    CONTROL_MEASURE = "25"
    SEA_SURFACE = "30"
    SEA_SUBSURFACE = "35"
    MINE_WARFARE = "36"
    ACTIVITIES = "40"
    METOC_ATMOSPHERIC = "45"
    METOC_OCEANOGRAPHIC = "46"
    METOC_SPACE = "47"
    SIGNALS_INTELLIGENCE = "50"    # SIGINT - Space
    SIGNALS_INTELLIGENCE_AIR = "51"
    SIGNALS_INTELLIGENCE_LAND = "52"
    SIGNALS_INTELLIGENCE_SURFACE = "53"
    SIGNALS_INTELLIGENCE_SUBSURFACE = "54"
    CYBERSPACE = "60"


class Status(Enum):
    """Pos 7 – Operational status."""
    PRESENT = "0"
    PLANNED = "1"
    FULLY_CAPABLE = "2"
    DAMAGED = "3"
    DESTROYED = "4"
    FULL_TO_CAPACITY = "5"


class HqTfDummy(Enum):
    """Pos 8 – HQ / Task Force / Dummy indicator."""
    NONE = "0"
    FEINT_DUMMY = "1"
    HQ = "2"
    FEINT_DUMMY_HQ = "3"
    TASK_FORCE = "4"
    FEINT_DUMMY_TF = "5"
    TASK_FORCE_HQ = "6"
    FEINT_DUMMY_TF_HQ = "7"


class Echelon(Enum):
    """Pos 9-10 – Echelon amplifier (when applicable)."""
    NONE = "00"
    TEAM_CREW = "11"
    SQUAD = "12"
    SECTION = "13"
    PLATOON = "14"
    COMPANY = "15"
    BATTALION = "16"
    REGIMENT = "17"
    BRIGADE = "18"
    DIVISION = "21"
    CORPS = "22"
    ARMY = "23"
    ARMY_GROUP = "24"
    REGION = "25"


# Affiliation → frame shape mapping
AFFILIATION_FRAME = {
    StandardIdentity.PENDING: "pending",
    StandardIdentity.UNKNOWN: "unknown",        # cloverleaf / quatrefoil
    StandardIdentity.ASSUMED_FRIEND: "friend",   # rectangle
    StandardIdentity.FRIEND: "friend",           # rectangle
    StandardIdentity.NEUTRAL: "neutral",         # square / diamond
    StandardIdentity.SUSPECT_JOKER: "hostile",   # diamond
    StandardIdentity.HOSTILE_FAKER: "hostile",    # diamond
}

# Affiliation → fill colour
AFFILIATION_FILL = {
    StandardIdentity.PENDING: "#ffff80",       # yellow
    StandardIdentity.UNKNOWN: "#ffff80",       # yellow
    StandardIdentity.ASSUMED_FRIEND: "#80e0ff", # light-blue
    StandardIdentity.FRIEND: "#80e0ff",         # light-blue
    StandardIdentity.NEUTRAL: "#aaffaa",        # green
    StandardIdentity.SUSPECT_JOKER: "#ff8080",  # red
    StandardIdentity.HOSTILE_FAKER: "#ff8080",  # red
}

AFFILIATION_STROKE = {
    StandardIdentity.PENDING: "#000000",
    StandardIdentity.UNKNOWN: "#000000",
    StandardIdentity.ASSUMED_FRIEND: "#000000",
    StandardIdentity.FRIEND: "#000000",
    StandardIdentity.NEUTRAL: "#000000",
    StandardIdentity.SUSPECT_JOKER: "#000000",
    StandardIdentity.HOSTILE_FAKER: "#000000",
}


# ======================================================================
# SIDC data class
# ======================================================================

@dataclass
class SIDC:
    """Parsed APP-6(D) 20-character Symbol Identification Code."""

    version: str = "10"
    context: Context = Context.REALITY
    standard_identity: StandardIdentity = StandardIdentity.FRIEND
    symbol_set: SymbolSet = SymbolSet.LAND_UNIT
    status: Status = Status.PRESENT
    hq_tf_dummy: HqTfDummy = HqTfDummy.NONE
    amplifier: str = "00"          # echelon / mobility
    entity: str = "000000"         # 6-digit entity code
    modifier1: str = "00"
    modifier2: str = "00"

    # Optional human-readable metadata (not part of the code)
    entity_name: str = ""
    entity_description: str = ""

    def __str__(self) -> str:
        """Return the full 20-character SIDC string."""
        return (
            f"{self.version}"
            f"{self.context.value}"
            f"{self.standard_identity.value}"
            f"{self.symbol_set.value}"
            f"{self.status.value}"
            f"{self.hq_tf_dummy.value}"
            f"{self.amplifier}"
            f"{self.entity}"
            f"{self.modifier1}"
            f"{self.modifier2}"
        )

    @classmethod
    def parse(cls, code: str) -> "SIDC":
        """Parse a 20-character SIDC string into a structured object.

        Raises ``ValueError`` if the string is not exactly 20 characters
        or contains invalid field values.
        """
        if len(code) != 20:
            raise ValueError(
                f"SIDC must be exactly 20 characters, got {len(code)}: {code!r}"
            )

        try:
            return cls(
                version=code[0:2],
                context=Context(code[2]),
                standard_identity=StandardIdentity(code[3]),
                symbol_set=SymbolSet(code[4:6]),
                status=Status(code[6]),
                hq_tf_dummy=HqTfDummy(code[7]),
                amplifier=code[8:10],
                entity=code[10:16],
                modifier1=code[16:18],
                modifier2=code[18:20],
            )
        except (ValueError, KeyError) as exc:
            raise ValueError(f"Invalid SIDC {code!r}: {exc}") from exc

    def with_identity(self, si: StandardIdentity) -> "SIDC":
        """Return a copy with a different standard identity."""
        new = copy.copy(self)
        new.standard_identity = si
        return new

    def with_echelon(self, echelon: Echelon) -> "SIDC":
        """Return a copy with a different echelon amplifier."""
        new = copy.copy(self)
        new.amplifier = echelon.value
        return new

    def with_status(self, status: Status) -> "SIDC":
        """Return a copy with a different status."""
        new = copy.copy(self)
        new.status = status
        return new

    @property
    def frame_shape(self) -> str:
        """Return the frame shape name for this symbol's affiliation."""
        return AFFILIATION_FRAME.get(self.standard_identity, "unknown")

    @property
    def fill_color(self) -> str:
        """Return the fill colour hex for this symbol's affiliation."""
        return AFFILIATION_FILL.get(self.standard_identity, "#ffff80")

    @property
    def stroke_color(self) -> str:
        """Return the stroke colour hex."""
        return AFFILIATION_STROKE.get(self.standard_identity, "#000000")

    @property
    def is_land_unit(self) -> bool:
        return self.symbol_set == SymbolSet.LAND_UNIT

    @property
    def is_equipment(self) -> bool:
        return self.symbol_set == SymbolSet.LAND_EQUIPMENT

    @property
    def is_installation(self) -> bool:
        return self.symbol_set == SymbolSet.LAND_INSTALLATION

    @property
    def is_air(self) -> bool:
        return self.symbol_set in (SymbolSet.AIR, SymbolSet.AIR_MISSILE)

    @property
    def is_space(self) -> bool:
        return self.symbol_set in (SymbolSet.SPACE, SymbolSet.SPACE_MISSILE)

    @property
    def is_sea_surface(self) -> bool:
        return self.symbol_set == SymbolSet.SEA_SURFACE

    @property
    def is_sea_subsurface(self) -> bool:
        return self.symbol_set in (SymbolSet.SEA_SUBSURFACE, SymbolSet.MINE_WARFARE)

    @property
    def dimension(self) -> str:
        """Return the symbolic domain / dimension for this SIDC."""
        ss = self.symbol_set
        if ss in (SymbolSet.AIR, SymbolSet.AIR_MISSILE, SymbolSet.SIGNALS_INTELLIGENCE_AIR):
            return "air"
        if ss in (SymbolSet.SPACE, SymbolSet.SPACE_MISSILE):
            return "space"
        if ss == SymbolSet.SEA_SURFACE:
            return "sea_surface"
        if ss in (SymbolSet.SEA_SUBSURFACE, SymbolSet.MINE_WARFARE):
            return "sea_subsurface"
        if ss in (SymbolSet.LAND_UNIT, SymbolSet.LAND_CIVILIAN,
                  SymbolSet.LAND_EQUIPMENT, SymbolSet.LAND_INSTALLATION,
                  SymbolSet.CONTROL_MEASURE, SymbolSet.SIGNALS_INTELLIGENCE_LAND):
            return "land"
        if ss == SymbolSet.ACTIVITIES:
            return "activities"
        if ss == SymbolSet.CYBERSPACE:
            return "cyberspace"
        return "land"

    @property
    def frame_shape_for_dimension(self) -> str:
        """Return the APP-6D dimension-aware frame shape.

        APP-6D specifies different base frame geometries per dimension:
        - Land/Installation/Activities → standard (rect/diamond/etc.)
        - Air/Space → top-arc
        - Sea Surface → flat-bottom
        - Sea Subsurface → trapezoid-bottom
        """
        dim = self.dimension
        base = self.frame_shape  # affiliation-based (friend/hostile/etc.)
        if dim in ("air", "space"):
            return f"{base}_air"
        if dim == "sea_surface":
            return f"{base}_sea"
        if dim == "sea_subsurface":
            return f"{base}_subsurface"
        return base


# ======================================================================
# Legacy MIL-STD-2525C SIDC support
# ======================================================================

# Regex patterns for SIDC format detection
APP6D_PATTERN = re.compile(r"^[A-Za-z0-9]{20}$")
MS2525C_PATTERN = re.compile(r"^[A-Za-z0-9\-\*]{10,15}$")


@dataclass
class SIDCValidation:
    """Result of SIDC format validation."""
    valid: bool
    format: Optional[str] = None   # "APP-6D" or "2525C" or None
    error: Optional[str] = None


def validate_sidc(code: str) -> SIDCValidation:
    """Validate an SIDC string and determine its format."""
    if not code:
        return SIDCValidation(valid=False, error="Empty SIDC")
    if APP6D_PATTERN.match(code):
        return SIDCValidation(valid=True, format="APP-6D")
    if MS2525C_PATTERN.match(code):
        return SIDCValidation(valid=True, format="2525C")
    return SIDCValidation(
        valid=False,
        error=f"Invalid SIDC format: '{code}'. "
              f"Expected APP-6D (20 alphanumeric) or 2525C (10-15 chars with dashes)"
    )


# 2525C affiliation → APP-6D Standard Identity mapping
_2525C_AFFILIATION_MAP = {
    "P": StandardIdentity.PENDING,
    "U": StandardIdentity.UNKNOWN,
    "A": StandardIdentity.ASSUMED_FRIEND,
    "F": StandardIdentity.FRIEND,
    "N": StandardIdentity.NEUTRAL,
    "S": StandardIdentity.SUSPECT_JOKER,
    "H": StandardIdentity.HOSTILE_FAKER,
    "J": StandardIdentity.SUSPECT_JOKER,
    "K": StandardIdentity.HOSTILE_FAKER,
    "G": StandardIdentity.PENDING,      # Exercise Pending
    "W": StandardIdentity.UNKNOWN,       # Exercise Unknown
    "D": StandardIdentity.FRIEND,        # Exercise Friend
    "M": StandardIdentity.ASSUMED_FRIEND,# Exercise Assumed Friend
    "L": StandardIdentity.NEUTRAL,       # Exercise Neutral
    "O": StandardIdentity.UNKNOWN,       # Not specified → Unknown
    "-": StandardIdentity.UNKNOWN,
    "*": StandardIdentity.UNKNOWN,
}

# 2525C battle dimension → APP-6D symbol set mapping (simplified)
_2525C_DIMENSION_MAP = {
    "P": SymbolSet.SPACE,
    "A": SymbolSet.AIR,
    "G": SymbolSet.LAND_UNIT,
    "S": SymbolSet.SEA_SURFACE,
    "U": SymbolSet.SEA_SUBSURFACE,
    "F": SymbolSet.ACTIVITIES,       # SOF → Activities approximation
    "X": SymbolSet.ACTIVITIES,       # Other
    "-": SymbolSet.LAND_UNIT,
    "*": SymbolSet.LAND_UNIT,
}


def convert_2525c_to_app6d(sidc_15: str) -> str:
    """Convert a 15-character MIL-STD-2525C SIDC to a 20-character APP-6D SIDC.

    This is a best-effort mapping; not all 2525C codes have
    exact APP-6D equivalents.  Unknown fields map to '0' / '00'.
    """
    # Pad to 15 chars if shorter
    sidc_15 = sidc_15.ljust(15, "-")

    affiliation = sidc_15[1].upper()
    dimension = sidc_15[2].upper()
    status_c = sidc_15[3].upper()
    func_id = sidc_15[4:10]

    # Map affiliation
    si = _2525C_AFFILIATION_MAP.get(affiliation, StandardIdentity.UNKNOWN)

    # Map dimension to symbol set
    ss = _2525C_DIMENSION_MAP.get(dimension, SymbolSet.LAND_UNIT)

    # Map status
    status = "1" if status_c == "A" else "0"

    # Function ID → entity code (best-effort: strip dashes/asterisks)
    entity_raw = func_id.replace("-", "0").replace("*", "0")
    entity = entity_raw.ljust(6, "0")[:6]

    return (
        f"10"                       # version = APP-6D
        f"0"                        # context = Reality
        f"{si.value}"               # standard identity
        f"{ss.value}"               # symbol set
        f"{status}"                 # status
        f"0"                        # HQ/TF/Dummy = none
        f"00"                       # amplifier = none
        f"{entity}"                 # entity
        f"00"                       # modifier 1
        f"00"                       # modifier 2
    )


def parse_any_sidc(code: str) -> SIDC:
    """Parse an SIDC in either APP-6D or 2525C format.

    If 2525C is detected it is converted to APP-6D first.
    """
    validation = validate_sidc(code)
    if not validation.valid:
        raise ValueError(validation.error)

    if validation.format == "2525C":
        code = convert_2525c_to_app6d(code)

    return SIDC.parse(code)
