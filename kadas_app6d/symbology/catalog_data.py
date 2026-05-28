# -*- coding: utf-8 -*-
"""
APP-6(D) symbol catalog data.

Provides a structured registry of known entities, organised by
**Symbol Set**, for use by the catalog browser GUI (Step 3) and the
rendering engine.

Each entry is a plain ``dict`` with the following keys:

* ``code``  – 6-digit entity code (positions 11-16 of the SIDC)
* ``name``  – human-readable name (English)
* ``name_de`` – name in German (for Swiss regulation 52.002.04 alignment)
* ``category`` – grouping label for the tree view
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ======================================================================
# Lightweight catalog entry
# ======================================================================

@dataclass
class CatalogEntry:
    """One entry in the symbol catalog."""

    symbol_set: str          # 2-digit code, e.g. "10"
    entity_code: str         # 6-digit code, e.g. "121100"
    name: str                # English name
    name_de: str = ""        # German name
    name_fr: str = ""        # French name
    name_it: str = ""        # Italian name
    category: str = ""       # Grouping label
    description: str = ""    # Optional tooltip / description
    modifier_1: str = "00"   # 2-digit Modifier 1 code
    modifier_2: str = "00"   # 2-digit Modifier 2 code
    app6b_func: str = "------"  # 6-char APP-6B function ID (pos 5-10)

    def sidc_template(self, identity: str = "3", status: str = "0") -> str:
        """Build a full 20-char SIDC with defaults for version/context etc.

        The resulting SIDC uses:
        * Version 10 (APP-6D)
        * Context 0 (Reality)
        * Given *identity* (default 3 = Friend)
        * This entry's symbol set + entity
        * Given *status* (default 0 = Present)
        * No HQ/TF/Dummy, no amplifier
        * Entry-specific modifiers (M1, M2)

        Activities (symbol set "40") override the default identity to
        "1" (Unknown) because they use a neutral cloverleaf frame that
        does not carry an affiliation.
        """
        # Activities have no affiliation → always use Unknown frame
        if self.symbol_set == "40" and identity == "3":
            identity = "1"
        return (
            f"10"                      # version
            f"0"                       # context = Reality
            f"{identity}"              # standard identity
            f"{self.symbol_set}"       # symbol set
            f"{status}"                # status
            f"0"                       # HQ/TF/Dummy = none
            f"00"                      # amplifier = none
            f"{self.entity_code}"      # entity (6 digits)
            f"{self.modifier_1}"       # modifier 1
            f"{self.modifier_2}"       # modifier 2
        )


# ======================================================================
# Catalog registry
# ======================================================================

# -- Land Unit (10) ----------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 landunit.js mappings
# (src/numbersidc/sidc/landunit.js)

LAND_UNIT_ENTRIES: list[CatalogEntry] = [
    # -- Command & Control --
    CatalogEntry("10", "110000", "Command and Control",  "Kommandoposten",     category="Command & Control",   app6b_func="U-----"),
    CatalogEntry("10", "110500", "Liaison",              "Verbindung",         category="Command & Control",   app6b_func="UCR---"),
    CatalogEntry("10", "111000", "Signal",               "Übermittlung",       category="Command & Control",   app6b_func="UCS---"),
    CatalogEntry("10", "111400", "Special Troops",       "Spezialtruppen",     category="Command & Control",   app6b_func="U-----"),

    # -- Combat Arms --
    CatalogEntry("10", "121100", "Infantry",             "Infanterie",         category="Combat Arms",         app6b_func="UCI---"),
    CatalogEntry("10", "121100", "Light Infantry",       "Leichte Infanterie", category="Combat Arms",         app6b_func="UCI---",
                 modifier_2="19"),  # M2=19 → Light
    CatalogEntry("10", "121104", "Motorized Infantry",   "Mot Infanterie",     category="Combat Arms",         app6b_func="UCIM--"),
    CatalogEntry("10", "121102", "Mechanized Infantry",  "Mech Infanterie",    category="Combat Arms",         app6b_func="UCIZ--"),
    CatalogEntry("10", "121100", "Mountain Infantry",    "Geb Infanterie",     category="Combat Arms",         app6b_func="UCI---",
                 modifier_2="27"),  # M2=27 → Mountain
    CatalogEntry("10", "121100", "Airborne Infantry",    "Fallschirminfanterie", category="Combat Arms",       app6b_func="UCI---",
                 modifier_2="01"),  # M2=01 → Airborne
    CatalogEntry("10", "120100", "Air Assault",          "Luftlandeinfanterie", category="Combat Arms",        app6b_func="UCAA--"),
    CatalogEntry("10", "120500", "Armor",                "Panzer",             category="Combat Arms",         app6b_func="UCAC--"),
    CatalogEntry("10", "120500", "Light Armor",          "Leichte Panzer",     category="Combat Arms",         app6b_func="UCAC--",
                 modifier_2="19"),  # M2=19 → Light
    CatalogEntry("10", "120501", "Armored Reconnaissance", "Panzeraufklärung", category="Combat Arms",         app6b_func="UCAR--"),
    CatalogEntry("10", "121000", "Combined Arms",        "Verbundene Waffen",  category="Combat Arms",         app6b_func="UCN---"),
    CatalogEntry("10", "121300", "Reconnaissance",       "Aufklärung",         category="Combat Arms",         app6b_func="UCAR--"),
    CatalogEntry("10", "121700", "Special Forces",       "Spezialkräfte",      category="Combat Arms",         app6b_func="UUSF--"),
    CatalogEntry("10", "121800", "Special Operations Forces", "SOF",           category="Combat Arms",         app6b_func="UUSOF-"),

    # -- Fire Support --
    CatalogEntry("10", "130100", "Air Defence",          "Fliegerabwehr",      category="Fire Support",         app6b_func="UCAAD-"),
    CatalogEntry("10", "130300", "Field Artillery",      "Artillerie",         category="Fire Support",         app6b_func="UCFH--"),
    CatalogEntry("10", "130301", "SP Artillery",         "Pz Artillerie",      category="Fire Support",         app6b_func="UCFHS-"),
    CatalogEntry("10", "130300", "Rocket Artillery",     "Raketenartillerie",  category="Fire Support",         app6b_func="UCFH--",
                 modifier_1="41"),  # M1=41 → Multiple Rocket Launcher
    CatalogEntry("10", "130700", "Missile",              "Lenkwaffe",          category="Fire Support",         app6b_func="UCFAM-"),
    CatalogEntry("10", "130800", "Mortar",               "Minenwerfer",        category="Fire Support",         app6b_func="UCFM--"),

    # -- UAS / Drone --
    # Entity 121900 = Unmanned Systems (GR.IC.UNMANNED SYSTEMS) in APP-6D Land Unit.
    # UCVU-- = Unmanned Systems; UCVUF- = Fixed Wing + UAV modifier.
    # M1 modifiers (APP-6D Land Unit sIdm1): 03=Attack, 47=UAV, 69=Utility.
    CatalogEntry("10", "121900", "Unmanned Aerial Vehicle (UAS)", "Unbemanntes Luftfahrzeug (UAS)", category="UAS / Drone", app6b_func="UCVU--"),
    CatalogEntry("10", "121900", "UAS \u2013 Attack",           "UAS \u2013 Angriff",     category="UAS / Drone", app6b_func="UCVUF-",
                 modifier_1="03"),   # M1=03 \u2192 Attack
    CatalogEntry("10", "121900", "UAS \u2013 Reconnaissance",   "UAS \u2013 Aufkl\u00e4rung", category="UAS / Drone", app6b_func="UCVUF-",
                 modifier_1="47"),   # M1=47 \u2192 Unmanned Aerial Vehicle (APP-6D)
    CatalogEntry("10", "121900", "UAS \u2013 Logistics / Cargo", "UAS \u2013 Logistik",   category="UAS / Drone", app6b_func="UCVU--",
                 modifier_1="69"),   # M1=69 \u2192 Utility

    # -- Combat Support --
    CatalogEntry("10", "120600", "Aviation (Rotary Wing)", "Heeresflieger",    category="Combat Support",       app6b_func="UCAAH-"),
    CatalogEntry("10", "120800", "Aviation (Fixed Wing)",  "Starrflügler",     category="Combat Support",       app6b_func="UCAAF-"),
    CatalogEntry("10", "140700", "Engineer",             "Genie",              category="Combat Support",       app6b_func="UCE---"),
    CatalogEntry("10", "151000", "Military Intelligence", "Militärischer Nachrichtendienst", category="Combat Support", app6b_func="UCMI--"),
    CatalogEntry("10", "150500", "Electronic Warfare",   "Elektronische Kriegsführung", category="Combat Support",  app6b_func="UCJ---"),
    CatalogEntry("10", "140100", "CBRN",                 "ABC Abwehr",         category="Combat Support",       app6b_func="UCBC--"),
    CatalogEntry("10", "141200", "Military Police",      "Militärpolizei",     category="Combat Support",       app6b_func="UCMP--"),
    CatalogEntry("10", "142200", "Air and Missile Defense", "Luft- und Raketenabwehr", category="Combat Support", app6b_func="UCAAA-"),

    # -- Combat Service Support --
    CatalogEntry("10", "161300", "Medical",              "Sanitätsdienst",     category="Combat Service Support", app6b_func="UH----"),
    CatalogEntry("10", "163400", "Supply",               "Nachschub",          category="Combat Service Support", app6b_func="USS---"),
    CatalogEntry("10", "163600", "Transportation",       "Transport",          category="Combat Service Support", app6b_func="USST--"),
    CatalogEntry("10", "161100", "Maintenance",          "Instandhaltung",     category="Combat Service Support", app6b_func="USM---"),
    CatalogEntry("10", "160000", "Sustainment",          "Logistik",           category="Combat Service Support", app6b_func="USS---"),
]

# -- Land Equipment (15) -----------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 landequipment.js mappings

LAND_EQUIPMENT_ENTRIES: list[CatalogEntry] = [
    # -- Weapons --
    CatalogEntry("15", "110000", "Weapon",              "Waffe",              category="Weapons"),
    CatalogEntry("15", "110900", "Howitzer",             "Haubitze",           category="Weapons"),
    CatalogEntry("15", "111000", "Missile Launcher",     "Raketenwerfer",     category="Weapons"),
    CatalogEntry("15", "111400", "Mortar",               "Mörser",            category="Weapons"),
    CatalogEntry("15", "111600", "Multiple Rocket Launcher", "Mehrfachraketenwerfer", category="Weapons"),

    # -- Armored Vehicles --
    CatalogEntry("15", "120200", "Tank",                "Kampfpanzer",        category="Armored Vehicles"),
    CatalogEntry("15", "120103", "APC",                 "Schützenpanzer",     category="Armored Vehicles"),
    CatalogEntry("15", "120101", "Armored Fighting Vehicle", "Kampffahrzeug",  category="Armored Vehicles"),
    CatalogEntry("15", "120105", "Main Battle Tank",    "Kampfpanzer (MBT)",  category="Armored Vehicles"),

    # -- Engineering --
    CatalogEntry("15", "130100", "Bridge",              "Brücke",             category="Engineering"),
    CatalogEntry("15", "130800", "Earthmover",          "Erdbaugerät",        category="Engineering"),
    CatalogEntry("15", "130900", "Mine Clearing",       "Minenräumgerät",     category="Engineering"),

    # -- Utility Vehicles --
    CatalogEntry("15", "140100", "Utility Vehicle",     "Nutzfahrzeug",       category="Utility Vehicles"),
    CatalogEntry("15", "140600", "Semi-Trailer Truck",  "Sattelzug",          category="Utility Vehicles"),

    # -- Mines --
    CatalogEntry("15", "210100", "Land Mine",           "Landmine",           category="Mines"),
    CatalogEntry("15", "210400", "IED",                 "IED",                category="Mines"),

    # -- Sensors --
    CatalogEntry("15", "220300", "Radar",               "Radar",              category="Sensors"),

    # -- Aviation --
    CatalogEntry("15", "250000", "Helicopter",          "Helikopter",         category="Aviation"),
]

# -- Air (01) -----------------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 air.js

AIR_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("01", "110000", "Military Air Track",         "Militärisches Luftfahrzeug",  category="Military"),
    CatalogEntry("01", "110100", "Fixed Wing",                 "Starrflügler",                category="Military – Fixed Wing"),
    CatalogEntry("01", "110101", "Medical Evacuation (FW)",    "Sanitätsevakuierung (Starrfl.)", category="Military – Fixed Wing"),
    CatalogEntry("01", "110102", "Attack/Strike",              "Angriff/Schlag",              category="Military – Fixed Wing"),
    CatalogEntry("01", "110103", "Bomber",                     "Bomber",                      category="Military – Fixed Wing"),
    CatalogEntry("01", "110104", "Fighter",                    "Jäger",                       category="Military – Fixed Wing"),
    CatalogEntry("01", "110105", "Fighter/Bomber",             "Jagdbomber",                  category="Military – Fixed Wing"),
    CatalogEntry("01", "110107", "Cargo (FW)",                 "Transportflugzeug",           category="Military – Fixed Wing"),
    CatalogEntry("01", "110108", "Jammer / ECM",               "Störflugzeug / ECM",          category="Military – Fixed Wing"),
    CatalogEntry("01", "110109", "Tanker",                     "Tankflugzeug",                category="Military – Fixed Wing"),
    CatalogEntry("01", "110110", "Patrol",                     "Überwachungsflugzeug",        category="Military – Fixed Wing"),
    CatalogEntry("01", "110111", "Reconnaissance (FW)",        "Aufklärungsflugzeug",         category="Military – Fixed Wing"),
    CatalogEntry("01", "110112", "Trainer (FW)",               "Schulflugzeug",               category="Military – Fixed Wing"),
    CatalogEntry("01", "110113", "Utility (FW)",               "Verbindungsflugzeug",         category="Military – Fixed Wing"),
    CatalogEntry("01", "110114", "VSTOL",                      "VSTOL",                       category="Military – Fixed Wing"),
    CatalogEntry("01", "110115", "Airborne Command Post",      "Luftgestützter Gefechtsstand",category="Military – Fixed Wing"),
    CatalogEntry("01", "110116", "Airborne Early Warning",     "Luftgestützte Frühwarnung",   category="Military – Fixed Wing"),
    CatalogEntry("01", "110117", "Antisurface Warfare",        "Antischiffkriegsführung",     category="Military – Fixed Wing"),
    CatalogEntry("01", "110118", "Antisubmarine Warfare (FW)", "U-Boot-Abwehr (Starrfl.)",    category="Military – Fixed Wing"),
    CatalogEntry("01", "110119", "Communications",             "Kommunikation",               category="Military – Fixed Wing"),
    CatalogEntry("01", "110120", "Combat Search and Rescue",   "Kampfrettung",                category="Military – Fixed Wing"),
    CatalogEntry("01", "110121", "Electronic Support",         "Elektronische Unterstützung", category="Military – Fixed Wing"),
    CatalogEntry("01", "110122", "Government",                 "Regierungsflugzeug",          category="Military – Fixed Wing"),
    CatalogEntry("01", "110123", "Mine Countermeasures (FW)",  "Minenabwehr (Starrfl.)",      category="Military – Fixed Wing"),
    CatalogEntry("01", "110124", "Personnel Recovery",         "Personalrettung",             category="Military – Fixed Wing"),
    CatalogEntry("01", "110125", "Search and Rescue",          "Such- und Rettungsflugzeug",  category="Military – Fixed Wing"),
    CatalogEntry("01", "110126", "Special Operations Forces",  "Spezialkräfte",               category="Military – Fixed Wing"),
    CatalogEntry("01", "110127", "Ultra Light",                "Ultraleichtflugzeug",         category="Military – Fixed Wing"),
    CatalogEntry("01", "110128", "Photographic Reconnaissance","Fotoaufklärung",              category="Military – Fixed Wing"),
    CatalogEntry("01", "110129", "VIP",                        "VIP-Flugzeug",                category="Military – Fixed Wing"),
    CatalogEntry("01", "110130", "SEAD",                       "SEAD",                        category="Military – Fixed Wing"),
    CatalogEntry("01", "110131", "Passenger",                  "Passagierflugzeug",           category="Military – Fixed Wing"),
    CatalogEntry("01", "110132", "Escort",                     "Eskorte",                     category="Military – Fixed Wing"),
    CatalogEntry("01", "110133", "Electronic Attack",          "Elektronischer Angriff",      category="Military – Fixed Wing"),
    CatalogEntry("01", "110200", "Rotary Wing",                "Drehflügler",                 category="Military – Rotary Wing"),
    CatalogEntry("01", "110201", "Medical Evacuation (RW)",    "Sanitätsevakuierung (Drehfl.)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110202", "Attack (RW)",                "Kampfhubschrauber",           category="Military – Rotary Wing"),
    CatalogEntry("01", "110203", "Cargo (RW)",                 "Transporthubschrauber",       category="Military – Rotary Wing"),
    CatalogEntry("01", "110204", "Utility (RW)",               "Verbindungshubschrauber",     category="Military – Rotary Wing"),
    CatalogEntry("01", "110205", "Antisubmarine Warfare (RW)", "U-Boot-Abwehr (Drehfl.)",     category="Military – Rotary Wing"),
    CatalogEntry("01", "110206", "C2 (RW)",                    "Führungshubschrauber",        category="Military – Rotary Wing"),
    CatalogEntry("01", "110207", "Mine Countermeasures (RW)",  "Minenabwehr (Drehfl.)",       category="Military – Rotary Wing"),
    CatalogEntry("01", "110208", "Search and Rescue (RW)",     "SAR-Hubschrauber",            category="Military – Rotary Wing"),
    CatalogEntry("01", "110209", "Reconnaissance (RW)",        "Aufklärungshubschrauber",     category="Military – Rotary Wing"),
    CatalogEntry("01", "110210", "Special Operations Forces (RW)", "SOF-Hubschrauber",        category="Military – Rotary Wing"),
    CatalogEntry("01", "110211", "VIP (RW)",                   "VIP-Hubschrauber",            category="Military – Rotary Wing"),
    CatalogEntry("01", "110300", "Unmanned Aerial Vehicle",    "Drohne (UAV)",                category="Military – UAV"),
    CatalogEntry("01", "110301", "UAV – Fixed Wing",           "Drohne – Starrflügler",       category="Military – UAV"),
    CatalogEntry("01", "110302", "UAV – Rotary Wing",          "Drohne – Drehflügler",        category="Military – UAV"),
    CatalogEntry("01", "110303", "UAV – Attack",               "Kampfdrohne",                 category="Military – UAV"),
    CatalogEntry("01", "110304", "UAV – Cargo",                "Transportdrohne",             category="Military – UAV"),
    CatalogEntry("01", "110305", "UAV – Reconnaissance",       "Aufklärungsdrohne",           category="Military – UAV"),
    CatalogEntry("01", "110400", "Vertical-Takeoff UAV",       "Senkrechtstartdrohne",        category="Military – UAV"),
    CatalogEntry("01", "110500", "Military Balloon",           "Militärballon",               category="Military – LTA"),
    CatalogEntry("01", "110600", "Military Airship",           "Militärluftschiff",           category="Military – LTA"),
    CatalogEntry("01", "110700", "Tethered Lighter Than Air",  "Fesselballon",                category="Military – LTA"),

    # -- Civilian --
    CatalogEntry("01", "120000", "Civilian Air Track",         "Ziviles Luftfahrzeug",        category="Civilian"),
    CatalogEntry("01", "120100", "Civilian Fixed Wing",        "Ziviler Starrflügler",        category="Civilian"),
    CatalogEntry("01", "120200", "Civilian Rotary Wing",       "Ziviler Drehflügler",         category="Civilian"),
    CatalogEntry("01", "120300", "Civilian UAV",               "Zivile Drohne",               category="Civilian"),
    CatalogEntry("01", "120400", "Civilian Balloon",           "Zivilballon",                 category="Civilian"),
    CatalogEntry("01", "120500", "Civilian Airship",           "Ziviles Luftschiff",          category="Civilian"),
    CatalogEntry("01", "120600", "Civilian Tethered LTA",      "Ziviler Fesselballon",        category="Civilian"),
    CatalogEntry("01", "120700", "Civilian Medical Evacuation","Zivile Sanitätsevakuierung",  category="Civilian"),

    # -- Weapon --
    CatalogEntry("01", "130000", "Weapon",                     "Waffe",                       category="Weapon"),
    CatalogEntry("01", "130100", "Bomb",                       "Bombe",                       category="Weapon"),
    CatalogEntry("01", "130200", "Underwater Decoy",           "Unterwasserköder",            category="Weapon"),

    # -- Manual Track --
    CatalogEntry("01", "140000", "Manual Track",               "Manuelle Spur",               category="Manual Track"),
]


# -- Air Missile (02) ---------------------------------------------------

AIR_MISSILE_ENTRIES: list[CatalogEntry] = [
    CatalogEntry("02", "110000", "Air Missile",                "Luft-Flugkörper",             category="Missile"),
    # Operational variants via M1 modifiers
    CatalogEntry("02", "110000", "Air-to-Air Missile",         "Luft-Luft-Flugkörper",        category="Missile", modifier_1="01"),
    CatalogEntry("02", "110000", "Air-to-Surface Missile",     "Luft-Boden-Flugkörper",       category="Missile", modifier_1="02"),
    CatalogEntry("02", "110000", "Air-to-Subsurface Missile",  "Luft-Unterwasser-FK",         category="Missile", modifier_1="03"),
    CatalogEntry("02", "110000", "Anti-Ballistic Missile",     "Abfang-Flugkörper (ABM)",     category="Missile", modifier_1="05"),
    CatalogEntry("02", "110000", "Ballistic Missile",          "Ballistische Rakete",         category="Missile", modifier_1="06"),
    CatalogEntry("02", "110000", "Cruise Missile",             "Marschflugkörper",            category="Missile", modifier_1="07"),
    CatalogEntry("02", "110000", "Interceptor",                "Abfangjäger",                 category="Missile", modifier_1="08"),
]


# -- Space (05) ----------------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 space.js

SPACE_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("05", "110000", "Military Space Track",       "Militärisches Weltraumobjekt", category="Military"),
    CatalogEntry("05", "110100", "Space Vehicle",              "Raumfahrzeug",                category="Military"),
    CatalogEntry("05", "110200", "Re-entry Vehicle",           "Wiedereintrittsflugkörper",    category="Military"),
    CatalogEntry("05", "110300", "Planet Lander",              "Planetenlander",              category="Military"),
    CatalogEntry("05", "110400", "Orbiter Shuttle",            "Orbiter / Shuttle",           category="Military"),
    CatalogEntry("05", "110500", "Capsule",                    "Kapsel",                      category="Military"),
    CatalogEntry("05", "110600", "Satellite (General)",        "Satellit (allgemein)",         category="Military – Satellite"),
    CatalogEntry("05", "110700", "Satellite",                  "Satellit",                    category="Military – Satellite"),
    CatalogEntry("05", "110800", "Antisatellite Weapon",       "Antisatellitenwaffe",         category="Military"),
    CatalogEntry("05", "110900", "Astronomical Satellite",     "Astronomie-Satellit",         category="Military – Satellite"),
    CatalogEntry("05", "111000", "Biosatellite",               "Biosatellit",                 category="Military – Satellite"),
    CatalogEntry("05", "111100", "Communications Satellite",   "Kommunikationssatellit",      category="Military – Satellite"),
    CatalogEntry("05", "111200", "Earth Observation Satellite","Erdbeobachtungssatellit",     category="Military – Satellite"),
    CatalogEntry("05", "111300", "Miniaturized Satellite",     "Kleinsatellit",               category="Military – Satellite"),
    CatalogEntry("05", "111400", "Navigational Satellite",     "Navigationssatellit",         category="Military – Satellite"),
    CatalogEntry("05", "111500", "Reconnaissance Satellite",   "Aufklärungssatellit",         category="Military – Satellite"),
    CatalogEntry("05", "111600", "Space Station",              "Raumstation",                 category="Military – Satellite"),
    CatalogEntry("05", "111700", "Tethered Satellite",         "Angeleinter Satellit",        category="Military – Satellite"),
    CatalogEntry("05", "111800", "Weather Satellite",          "Wettersatellit",              category="Military – Satellite"),
    CatalogEntry("05", "111900", "Space Launch Vehicle",       "Trägerrakete",                category="Military"),

    # -- Civilian --
    CatalogEntry("05", "120000", "Civilian Space Track",       "Ziviles Weltraumobjekt",      category="Civilian"),
    CatalogEntry("05", "120100", "Civilian Orbiter Shuttle",   "Ziviler Orbiter / Shuttle",   category="Civilian"),
    CatalogEntry("05", "120200", "Civilian Capsule",           "Zivile Kapsel",               category="Civilian"),
    CatalogEntry("05", "120300", "Civilian Satellite",         "Ziviler Satellit",            category="Civilian – Satellite"),
    CatalogEntry("05", "120400", "Civilian Astronomical Sat.", "Ziviler Astronomie-Sat.",     category="Civilian – Satellite"),
    CatalogEntry("05", "120500", "Civilian Biosatellite",      "Ziviler Biosatellit",         category="Civilian – Satellite"),
    CatalogEntry("05", "120600", "Civilian Comms Satellite",   "Ziviler Komm.-Satellit",      category="Civilian – Satellite"),
    CatalogEntry("05", "120700", "Civilian Earth Obs. Sat.",   "Ziviler Erdbeob.-Sat.",       category="Civilian – Satellite"),
    CatalogEntry("05", "120800", "Civilian Miniaturized Sat.", "Ziviler Kleinsatellit",       category="Civilian – Satellite"),
    CatalogEntry("05", "120900", "Civilian Navigational Sat.", "Ziviler Navigations-Sat.",    category="Civilian – Satellite"),
    CatalogEntry("05", "121000", "Civilian Space Station",     "Zivile Raumstation",          category="Civilian – Satellite"),
    CatalogEntry("05", "121100", "Civilian Tethered Sat.",     "Ziviler angel. Satellit",     category="Civilian – Satellite"),
    CatalogEntry("05", "121200", "Civilian Weather Sat.",      "Ziviler Wettersatellit",      category="Civilian – Satellite"),
    CatalogEntry("05", "121300", "Civilian Planet Lander",     "Ziviler Planetenlander",      category="Civilian"),
    CatalogEntry("05", "121400", "Civilian Space Vehicle",     "Ziviles Raumfahrzeug",        category="Civilian"),

    # -- Manual Track --
    CatalogEntry("05", "130000", "Manual Track (Space)",       "Manuelle Spur (Weltraum)",    category="Manual Track"),
]


# -- Space Missile (06) --------------------------------------------------

SPACE_MISSILE_ENTRIES: list[CatalogEntry] = [
    CatalogEntry("06", "110000", "Space Missile",              "Weltraum-Flugkörper",         category="Missile"),
    CatalogEntry("06", "110000", "Ballistic Missile (Space)",  "Ballistische Rakete (Weltr.)",category="Missile", modifier_1="02"),
    CatalogEntry("06", "110000", "Space Launch Vehicle (Missile)", "Trägerrakete (FK)",       category="Missile", modifier_1="04"),
]


# -- Land Civilian (11) -------------------------------------------------

LAND_CIVILIAN_ENTRIES: list[CatalogEntry] = [
    CatalogEntry("11", "110000", "Civilian",                   "Zivilperson",                 category="Civilian"),
    CatalogEntry("11", "110100", "Environmental Protection",   "Umweltschutz",                category="Civilian"),
    CatalogEntry("11", "110200", "Government Organization",    "Regierungsorganisation",      category="Civilian"),
    CatalogEntry("11", "110300", "Individual",                 "Einzelperson",                category="Civilian"),
    CatalogEntry("11", "110400", "Group/Team",                 "Gruppe/Team",                 category="Civilian"),
    CatalogEntry("11", "110500", "Killing Victim",             "Opfer (Tötung)",              category="Civilian"),
    CatalogEntry("11", "110600", "Kidnapping Victim",          "Entführungsopfer",            category="Civilian"),
    CatalogEntry("11", "110700", "Religious Leader",           "Religionsführer",             category="Civilian"),
    CatalogEntry("11", "110800", "Displaced Person",           "Vertriebene Person",          category="Civilian"),
    CatalogEntry("11", "110900", "Composite Loss",             "Gemischter Verlust",          category="Civilian"),
]


# -- Land Installation (20) --------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 landinstallation.js

LAND_INSTALLATION_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("20", "110000", "Military Installation",      "Militärische Anlage",         category="Military"),
    CatalogEntry("20", "110100", "Aerial/Satellite",           "Luft/Satellit",               category="Military"),
    CatalogEntry("20", "110200", "Aircraft Production/Assembly","Flugzeugproduktion",         category="Military"),
    CatalogEntry("20", "110300", "Ammunition Cache",           "Munitionslager",              category="Military"),
    CatalogEntry("20", "110400", "Ammunition and Explosives",  "Munition und Sprengstoff",    category="Military"),
    CatalogEntry("20", "110500", "C3I",                        "C3I-Anlage",                  category="Military"),
    CatalogEntry("20", "110600", "CBRN",                       "ABC-Anlage",                  category="Military"),
    CatalogEntry("20", "110700", "Construction/Engineering",   "Bau/Genie",                   category="Military"),
    CatalogEntry("20", "110800", "Corrosion",                  "Korrosion",                   category="Military"),
    CatalogEntry("20", "110900", "Dam",                        "Damm/Staudamm",               category="Military"),
    CatalogEntry("20", "111000", "Disposal/Contamination",     "Entsorgung/Kontamination",    category="Military"),
    CatalogEntry("20", "111100", "Emergency Collection Point", "Notsammelstelle",             category="Military"),
    CatalogEntry("20", "111200", "Equipment Manufacture",      "Geräteherstellung",           category="Military"),
    CatalogEntry("20", "111300", "Mine",                       "Mine (Anlage)",               category="Military"),
    CatalogEntry("20", "111400", "Missile/Rocket Launcher",    "Raketen-/FK-Werfer",          category="Military"),
    CatalogEntry("20", "111500", "Nuclear Facility",           "Kernanlage",                  category="Military"),
    CatalogEntry("20", "111501", "Nuclear Research Facility",  "Kernforschungsanlage",        category="Military"),
    CatalogEntry("20", "111502", "Nuclear Reactor",            "Kernreaktor",                 category="Military"),
    CatalogEntry("20", "111600", "Petroleum/Gas/Oil",          "Erdöl/Gas/Öl",                category="Military"),
    CatalogEntry("20", "111700", "Radar",                      "Radaranlage",                 category="Military"),
    CatalogEntry("20", "111800", "Research",                   "Forschungsanlage",            category="Military"),
    CatalogEntry("20", "111900", "Sea Vehicle Production",     "Schiffbau",                   category="Military"),
    CatalogEntry("20", "112000", "Technical Maintenance",      "Technische Wartung",          category="Military"),
    CatalogEntry("20", "112100", "Telecommunications",         "Fernmeldeanlage",             category="Military"),
    CatalogEntry("20", "112200", "Training",                   "Ausbildungsanlage",           category="Military"),
    CatalogEntry("20", "112300", "Vehicle Production",         "Fahrzeugproduktion",          category="Military"),
    CatalogEntry("20", "112400", "Warehouse/Storage",          "Lager/Depot",                 category="Military"),

    # -- Infrastructure – Agriculture --
    CatalogEntry("20", "120100", "Agriculture/Food Infrastructure", "Landwirtschaft/Lebensmittel", category="Infrastructure – Agriculture"),
    CatalogEntry("20", "120101", "Agricultural Laboratory",    "Landwirtschaftslabor",        category="Infrastructure – Agriculture"),
    CatalogEntry("20", "120102", "Animal Feedlot",             "Viehfutterstelle",            category="Infrastructure – Agriculture"),
    CatalogEntry("20", "120103", "Commercial/Institutional Farm", "Gewerbe-/Inst.-Hof",       category="Infrastructure – Agriculture"),
    CatalogEntry("20", "120104", "Grain Storage",              "Getreidespeicher",            category="Infrastructure – Agriculture"),

    # -- Infrastructure – Banking/Finance --
    CatalogEntry("20", "120200", "Banking, Finance & Insurance", "Bank/Finanz/Versicherung",  category="Infrastructure – Banking"),
    CatalogEntry("20", "120201", "ATM",                        "Geldautomat",                 category="Infrastructure – Banking"),
    CatalogEntry("20", "120202", "Bank",                       "Bankgebäude",                 category="Infrastructure – Banking"),
    CatalogEntry("20", "120203", "Financial Exchange",         "Finanzbörse",                 category="Infrastructure – Banking"),

    # -- Infrastructure – Commercial --
    CatalogEntry("20", "120300", "Commercial Infrastructure",  "Gewerbeinfrastruktur",        category="Infrastructure – Commercial"),
    CatalogEntry("20", "120301", "Chemical Plant",             "Chemiefabrik",                category="Infrastructure – Commercial"),
    CatalogEntry("20", "120302", "Firearms Manufacturer",      "Waffenhersteller",            category="Infrastructure – Commercial"),
    CatalogEntry("20", "120303", "Firearms Retailer",          "Waffenhändler",               category="Infrastructure – Commercial"),
    CatalogEntry("20", "120304", "Hazardous Material Production", "Gefahrstoffproduktion",    category="Infrastructure – Commercial"),
    CatalogEntry("20", "120305", "Industrial Site",            "Industriegelände",            category="Infrastructure – Commercial"),
    CatalogEntry("20", "120306", "Landfill",                   "Deponie",                     category="Infrastructure – Commercial"),
    CatalogEntry("20", "120307", "Pharmaceutical Manufacturer","Pharmahersteller",            category="Infrastructure – Commercial"),
    CatalogEntry("20", "120308", "Contaminated Hazardous Waste Site", "Kont. Abfallgelände",  category="Infrastructure – Commercial"),
    CatalogEntry("20", "120309", "Toxic Release Inventory",    "Schadstofffreisetzungsreg.",  category="Infrastructure – Commercial"),

    # -- Infrastructure – Education --
    CatalogEntry("20", "120400", "Educational Facilities",     "Bildungseinrichtungen",       category="Infrastructure – Education"),
    CatalogEntry("20", "120401", "College/University",         "Universität/Hochschule",      category="Infrastructure – Education"),
    CatalogEntry("20", "120402", "School",                     "Schule",                      category="Infrastructure – Education"),

    # -- Infrastructure – Electric Power --
    CatalogEntry("20", "120500", "Electric Power",             "Elektrizitätsversorgung",     category="Infrastructure – Electric"),
    CatalogEntry("20", "120501", "Electric Power Generation Station", "Kraftwerk",            category="Infrastructure – Electric"),
    CatalogEntry("20", "120502", "Electric Power Substation",  "Umspannwerk",                 category="Infrastructure – Electric"),
    CatalogEntry("20", "120503", "Natural Gas Facility",       "Erdgasanlage",                category="Infrastructure – Electric"),
    CatalogEntry("20", "120504", "Propane Facility",           "Propananlage",                category="Infrastructure – Electric"),

    # -- Infrastructure – Government --
    CatalogEntry("20", "120600", "Government Site",            "Regierungsgebäude",           category="Infrastructure – Government"),
    CatalogEntry("20", "120601", "Courthouse",                 "Gerichtsgebäude",             category="Infrastructure – Government"),
    CatalogEntry("20", "120602", "Embassy",                    "Botschaft",                   category="Infrastructure – Government"),
    CatalogEntry("20", "120603", "Government Building",        "Regierungsgebäude",           category="Infrastructure – Government"),
    CatalogEntry("20", "120604", "Prison/Jail",                "Gefängnis",                   category="Infrastructure – Government"),

    # -- Infrastructure – Medical --
    CatalogEntry("20", "120700", "Medical Infrastructure",     "Medizinische Infrastruktur",  category="Infrastructure – Medical"),
    CatalogEntry("20", "120701", "Hospital",                   "Spital",                      category="Infrastructure – Medical"),
    CatalogEntry("20", "120702", "Medical Treatment Facility", "Sanitätsstelle",              category="Infrastructure – Medical"),
    CatalogEntry("20", "120703", "Pharmacy",                   "Apotheke",                    category="Infrastructure – Medical"),

    # -- Infrastructure – Military Base --
    CatalogEntry("20", "120800", "Military Infrastructure",    "Militärische Infrastruktur",  category="Infrastructure – Military"),
    CatalogEntry("20", "120801", "Military Base",              "Militärbasis",                category="Infrastructure – Military"),
    CatalogEntry("20", "120802", "Airfield/Airport",           "Flugplatz",                   category="Infrastructure – Military"),

    # -- Infrastructure – Postal --
    CatalogEntry("20", "120900", "Postal Service",             "Postdienst",                  category="Infrastructure – Postal"),
    CatalogEntry("20", "120901", "Post Office",                "Postamt",                     category="Infrastructure – Postal"),

    # -- Infrastructure – Public Venues --
    CatalogEntry("20", "121000", "Public Venues",              "Öffentliche Einrichtungen",   category="Infrastructure – Public"),
    CatalogEntry("20", "121001", "Enclosed Facility",          "Geschlossene Anlage",         category="Infrastructure – Public"),
    CatalogEntry("20", "121002", "Open Facility",              "Offene Anlage",               category="Infrastructure – Public"),
    CatalogEntry("20", "121003", "Recreational Area",          "Erholungsgebiet",             category="Infrastructure – Public"),
    CatalogEntry("20", "121004", "Religious Institution",      "Religiöse Einrichtung",       category="Infrastructure – Public"),

    # -- Infrastructure – Special Needs --
    CatalogEntry("20", "121100", "Special Needs",              "Besondere Bedürfnisse",       category="Infrastructure – Special Needs"),
    CatalogEntry("20", "121101", "Adult Day Care",             "Tagespflege",                 category="Infrastructure – Special Needs"),
    CatalogEntry("20", "121102", "Child Day Care",             "Kinderbetreuung",             category="Infrastructure – Special Needs"),
    CatalogEntry("20", "121103", "Elder Care",                 "Altenpflege",                 category="Infrastructure – Special Needs"),

    # -- Infrastructure – Telecommunications --
    CatalogEntry("20", "121200", "Telecommunications",         "Telekommunikation",           category="Infrastructure – Telecom"),
    CatalogEntry("20", "121201", "Broadcast Transmitter",      "Sendeanlage",                 category="Infrastructure – Telecom"),
    CatalogEntry("20", "121202", "Telecommunications Tower",   "Sendemast",                   category="Infrastructure – Telecom"),
    CatalogEntry("20", "121203", "Internet Service Provider",  "Internetanbieter",            category="Infrastructure – Telecom"),

    # -- Infrastructure – Transportation --
    CatalogEntry("20", "121300", "Transportation Infrastructure", "Verkehrsinfrastruktur",    category="Infrastructure – Transport"),
    CatalogEntry("20", "121301", "Airport",                    "Flughafen",                   category="Infrastructure – Transport"),
    CatalogEntry("20", "121302", "Air Traffic Control",        "Flugsicherung",               category="Infrastructure – Transport"),
    CatalogEntry("20", "121303", "Bus Station",               "Busbahnhof",                  category="Infrastructure – Transport"),
    CatalogEntry("20", "121304", "Ferry Terminal",             "Fährterminal",                category="Infrastructure – Transport"),
    CatalogEntry("20", "121305", "Helicopter Landing Site",    "Hubschrauberlandeplatz",      category="Infrastructure – Transport"),
    CatalogEntry("20", "121306", "Maintenance Facility",       "Wartungsanlage",              category="Infrastructure – Transport"),
    CatalogEntry("20", "121307", "Port/Harbor",                "Hafen",                       category="Infrastructure – Transport"),
    CatalogEntry("20", "121308", "Railroad Station/Depot",     "Bahnhof/Depot",               category="Infrastructure – Transport"),
    CatalogEntry("20", "121309", "Rest Area",                  "Rastplatz",                   category="Infrastructure – Transport"),
    CatalogEntry("20", "121310", "Seaport",                    "Seehafen",                    category="Infrastructure – Transport"),
    CatalogEntry("20", "121311", "Toll Facility",              "Mautstelle",                  category="Infrastructure – Transport"),
    CatalogEntry("20", "121312", "Traffic Inspection Facility","Verkehrskontrollstelle",      category="Infrastructure – Transport"),
    CatalogEntry("20", "121313", "Tunnel",                     "Tunnel",                      category="Infrastructure – Transport"),

    # -- Infrastructure – Water --
    CatalogEntry("20", "121400", "Water Supply",               "Wasserversorgung",            category="Infrastructure – Water"),
    CatalogEntry("20", "121401", "Controlled Water",           "Kontrolliertes Wasser",       category="Infrastructure – Water"),
    CatalogEntry("20", "121402", "Water Treatment",            "Wasseraufbereitung",          category="Infrastructure – Water"),
    CatalogEntry("20", "121403", "Well",                       "Brunnen",                     category="Infrastructure – Water"),
]


# -- Sea Surface (30) ---------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 sea.js

SEA_SURFACE_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("30", "110000", "Military Sea Surface Track", "Militärisches Überwasserziel",category="Military"),

    # -- Combatant --
    CatalogEntry("30", "120000", "Combatant",                  "Kampfschiff",                 category="Combatant"),
    CatalogEntry("30", "120100", "Carrier",                    "Flugzeugträger",              category="Combatant"),
    CatalogEntry("30", "120200", "Surface Combatant, Line",    "Überwasser-Kampfschiff",      category="Combatant – Line"),
    CatalogEntry("30", "120201", "Battleship",                 "Schlachtschiff",              category="Combatant – Line"),
    CatalogEntry("30", "120202", "Cruiser",                    "Kreuzer",                     category="Combatant – Line"),
    CatalogEntry("30", "120203", "Destroyer",                  "Zerstörer",                   category="Combatant – Line"),
    CatalogEntry("30", "120204", "Frigate",                    "Fregatte",                    category="Combatant – Line"),
    CatalogEntry("30", "120205", "Corvette",                   "Korvette",                    category="Combatant – Line"),
    CatalogEntry("30", "120206", "Littoral Combatant Ship",    "Küstenkampfschiff",           category="Combatant – Line"),
    CatalogEntry("30", "120300", "Amphibious Warfare Ship",    "Amphibisches Kampfschiff",    category="Combatant – Amphibious"),
    CatalogEntry("30", "120301", "Amphibious Assault Ship, General","Amphib. Angriffsschiff",  category="Combatant – Amphibious"),
    CatalogEntry("30", "120302", "Amphibious Assault Ship, Helicopter","Amphib. Hubschr.-Träger", category="Combatant – Amphibious"),
    CatalogEntry("30", "120303", "Amphibious Transport Dock",  "Amphib. Transportdock",       category="Combatant – Amphibious"),
    CatalogEntry("30", "120304", "Landing Ship",               "Landungsschiff",              category="Combatant – Amphibious"),
    CatalogEntry("30", "120305", "Landing Craft",              "Landungsboot",                category="Combatant – Amphibious"),
    CatalogEntry("30", "120400", "Mine Warfare Vessel",        "Minenkriegsfahrzeug",         category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120401", "Minelayer",                  "Minenleger",                  category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120402", "Minesweeper",                "Minensucher",                 category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120403", "Minehunter",                 "Minenjäger",                  category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120404", "Mine Countermeasures (MCM)", "Minenabwehr",                 category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120405", "MCM Support",                "Minenabwehr-Uboot",           category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120500", "Patrol Boat",                "Patrouillenboot",             category="Combatant"),
    CatalogEntry("30", "120501", "Patrol Anti-Submarine",      "U-Boot-Jagd-Patrouillenboot", category="Combatant"),
    CatalogEntry("30", "120502", "Patrol Coastal",             "Küstenpatrouillenboot",       category="Combatant"),
    CatalogEntry("30", "120600", "Decoy",                      "Täuschkörper",                category="Combatant"),
    CatalogEntry("30", "120700", "Unmanned Surface Vehicle",   "Überwasser-Drohne (USV)",     category="Combatant"),
    CatalogEntry("30", "120800", "Military Speedboat",         "Militärisches Schnellboot",   category="Combatant"),
    CatalogEntry("30", "120801", "Speedboat, Armed",           "Schnellboot, bewaffnet",      category="Combatant"),
    CatalogEntry("30", "120900", "Military Jet Ski",           "Militärischer Jet-Ski",       category="Combatant"),
    CatalogEntry("30", "121000", "Navy Task Organization Unit","Marine-Verband",              category="Combatant – Task Org"),
    CatalogEntry("30", "121001", "Task Force",                 "Kampfgruppe",                 category="Combatant – Task Org"),
    CatalogEntry("30", "121002", "Task Group",                 "Einsatzgruppe",               category="Combatant – Task Org"),
    CatalogEntry("30", "121003", "Task Unit",                  "Einsatzeinheit",              category="Combatant – Task Org"),
    CatalogEntry("30", "121004", "Task Element",               "Einsatzelement",              category="Combatant – Task Org"),
    CatalogEntry("30", "121005", "Convoy",                     "Konvoi",                      category="Combatant – Task Org"),
    CatalogEntry("30", "121100", "Radar (Sea Surface)",        "Radar (Überwasser)",          category="Combatant"),

    # -- Noncombatant --
    CatalogEntry("30", "130000", "Noncombatant",               "Nichtkampfschiff",            category="Noncombatant"),
    CatalogEntry("30", "130100", "Auxiliary Ship",             "Hilfsschiff",                 category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130101", "Ammunition Ship",            "Munitionsschiff",             category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130102", "Combat Stores Ship",         "Versorgungsschiff",           category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130103", "Fast Combat Support Ship",   "Schnelles Versorgungsschiff", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130104", "Hospital Ship",              "Lazarettschiff",              category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130105", "Intelligence Collector",     "Aufklärungsschiff",           category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130106", "Oiler",                      "Tanker (Marine)",             category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130107", "Repair Ship",                "Reparaturschiff",             category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130108", "Research Ship",              "Forschungsschiff",            category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130109", "Salvage Ship",               "Bergungs-/Rettungsschiff",    category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130110", "Submarine Tender",           "U-Boot-Tender",               category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130111", "Survey Ship",                "Vermessungsschiff",           category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130112", "Tug",                        "Schlepper",                   category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130113", "Transport",                  "Transportschiff",             category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130200", "Service Craft/Vessel",       "Dienstfahrzeug",              category="Noncombatant – Service"),
    CatalogEntry("30", "130201", "Barge",                      "Prahm/Leichter",              category="Noncombatant – Service"),
    CatalogEntry("30", "130202", "Diving Vessel",              "Tauchfahrzeug",               category="Noncombatant – Service"),
    CatalogEntry("30", "130203", "Dredge",                     "Baggerschiff",                category="Noncombatant – Service"),
    CatalogEntry("30", "130204", "Launch",                     "Barkasse",                    category="Noncombatant – Service"),

    # -- Civilian --
    CatalogEntry("30", "140000", "Civilian Ship",              "Zivilschiff",                 category="Civilian"),
    CatalogEntry("30", "140100", "Merchant Ship",              "Handelsschiff",               category="Civilian – Merchant"),
    CatalogEntry("30", "140101", "Cargo Vessel",               "Frachtschiff",                category="Civilian – Merchant"),
    CatalogEntry("30", "140102", "Container Ship",             "Containerschiff",             category="Civilian – Merchant"),
    CatalogEntry("30", "140103", "Dredger (Civ.)",             "Baggerschiff (Zivil)",        category="Civilian – Merchant"),
    CatalogEntry("30", "140104", "Ferry",                      "Fähre",                       category="Civilian – Merchant"),
    CatalogEntry("30", "140105", "Heavy Lift Ship",            "Schwergutschiff",             category="Civilian – Merchant"),
    CatalogEntry("30", "140106", "Hovercraft",                 "Luftkissenfahrzeug",          category="Civilian – Merchant"),
    CatalogEntry("30", "140107", "Merchant Marine Oiler/Tanker", "Handels-Tanker",            category="Civilian – Merchant"),
    CatalogEntry("30", "140108", "LNG Carrier",                "LNG-Tanker",                  category="Civilian – Merchant"),
    CatalogEntry("30", "140109", "Oil Rig",                    "Ölplattform",                 category="Civilian – Merchant"),
    CatalogEntry("30", "140110", "Passenger Vessel",           "Passagierschiff",             category="Civilian – Merchant"),
    CatalogEntry("30", "140111", "Roll-on/Roll-off",           "Ro-Ro-Schiff",                category="Civilian – Merchant"),
    CatalogEntry("30", "140112", "Tug (Civilian)",             "Schlepper (Zivil)",           category="Civilian – Merchant"),
    CatalogEntry("30", "140113", "Yacht",                      "Yacht",                       category="Civilian – Merchant"),
    CatalogEntry("30", "140200", "Fishing Vessel",             "Fischereifahrzeug",           category="Civilian"),
    CatalogEntry("30", "140201", "Drift Netter",               "Treibnetzfischer",            category="Civilian"),
    CatalogEntry("30", "140202", "Trawler",                    "Trawler",                     category="Civilian"),
    CatalogEntry("30", "140203", "Dory/Whaler",                "Walfangboot",                 category="Civilian"),
    CatalogEntry("30", "140300", "Law Enforcement Vessel",     "Polizeischiff",               category="Civilian"),
    CatalogEntry("30", "140400", "Sailing Vessel",             "Segelschiff",                 category="Civilian – Leisure"),
    CatalogEntry("30", "140500", "Motorized Vessel (Leisure)", "Motorboot (Freizeit)",        category="Civilian – Leisure"),
    CatalogEntry("30", "140600", "Jet Ski (Civilian)",         "Jet-Ski (Zivil)",             category="Civilian – Leisure"),
    CatalogEntry("30", "140700", "Unmanned Surface Vehicle (Civ.)", "USV (Zivil)",            category="Civilian"),

    # -- Own Ship / Fused / Manual --
    CatalogEntry("30", "150000", "Own Ship",                   "Eigenes Schiff",              category="Own Ship"),
    CatalogEntry("30", "160000", "Fused Track (Sea Surface)",  "Fusionierte Spur",            category="Fused Track"),
    CatalogEntry("30", "170000", "Manual Track (Sea Surface)", "Manuelle Spur",               category="Manual Track"),
]


# -- Sea Subsurface (35) ------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 subsurface.js

SEA_SUBSURFACE_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("35", "110000", "Military Subsurface Track",  "Militärisches Unterwasserziel",category="Military"),
    CatalogEntry("35", "110100", "Submarine",                  "U-Boot",                      category="Military – Submarine"),
    CatalogEntry("35", "110101", "Submarine, Surfaced",        "U-Boot, aufgetaucht",         category="Military – Submarine"),
    CatalogEntry("35", "110102", "Submarine, Snorkeling",      "U-Boot, Schnorchelfahrt",     category="Military – Submarine"),
    CatalogEntry("35", "110103", "Submarine, Bottomed",        "U-Boot, auf Grund",           category="Military – Submarine"),
    CatalogEntry("35", "110200", "Other Submersible",          "Anderes Tauchfahrzeug",       category="Military"),
    CatalogEntry("35", "110300", "Non-Submarine",              "Nicht-U-Boot",                category="Military"),
    CatalogEntry("35", "110400", "Autonomous Underwater Vehicle", "AUV/UUV",                  category="Military"),
    CatalogEntry("35", "110500", "Military Diver",             "Militärtaucher",              category="Military"),

    # -- Civilian --
    CatalogEntry("35", "120000", "Civilian Subsurface Track",  "Ziviles Unterwasserziel",     category="Civilian"),
    CatalogEntry("35", "120100", "Civilian Submersible",       "Ziviles Tauchfahrzeug",       category="Civilian"),
    CatalogEntry("35", "120200", "Civilian AUV/UUV",           "Ziviles AUV/UUV",             category="Civilian"),
    CatalogEntry("35", "120300", "Civilian Diver",             "Ziviltaucher",                category="Civilian"),

    # -- Underwater Weapon --
    CatalogEntry("35", "130000", "Underwater Weapon",          "Unterwasserwaffe",            category="Weapon"),
    CatalogEntry("35", "130100", "Torpedo",                    "Torpedo",                     category="Weapon"),
    CatalogEntry("35", "130200", "Improvised Explosive Device","IED (Unterwasser)",           category="Weapon"),
    CatalogEntry("35", "130300", "Underwater Decoy",           "Unterwasserköder",            category="Weapon"),

    # -- Echo / Fused / Manual --
    CatalogEntry("35", "140000", "Echo Tracker Classifier",    "Echo / Klasse",               category="Echo"),
    CatalogEntry("35", "150000", "Fused Track (Subsurface)",   "Fusionierte Spur",            category="Fused Track"),
    CatalogEntry("35", "160000", "Manual Track (Subsurface)",  "Manuelle Spur",               category="Manual Track"),

    # -- Seabed Installation --
    CatalogEntry("35", "200000", "Seabed Installation, Military", "Seebodeninstallation (Mil.)",category="Seabed Installation"),
    CatalogEntry("35", "210000", "Seabed Installation, Non-Military", "Seebodeninstall. (Ziv.)",category="Seabed Installation"),
]


# -- Mine Warfare (36) --------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 minewarfare.js

MINE_WARFARE_ENTRIES: list[CatalogEntry] = [
    # -- Sea Mine (General) --
    CatalogEntry("36", "110000", "Sea Mine (General)",         "Seemine (allgemein)",          category="Sea Mine"),

    # -- Bottom Mine --
    CatalogEntry("36", "110100", "Sea Mine – Bottom",          "Grundmine",                    category="Sea Mine – Bottom"),
    CatalogEntry("36", "110101", "Bottom Mine – General",      "Grundmine – allgemein",        category="Sea Mine – Bottom"),

    # -- Moored Mine --
    CatalogEntry("36", "110200", "Sea Mine – Moored",          "Ankermine",                    category="Sea Mine – Moored"),
    CatalogEntry("36", "110201", "Moored Mine – General",      "Ankermine – allgemein",        category="Sea Mine – Moored"),

    # -- Floating Mine --
    CatalogEntry("36", "110300", "Sea Mine – Floating",        "Treibmine",                    category="Sea Mine – Floating"),
    CatalogEntry("36", "110301", "Floating Mine – General",    "Treibmine – allgemein",        category="Sea Mine – Floating"),

    # -- Rising Mine --
    CatalogEntry("36", "110400", "Sea Mine – Rising",          "Steigmine",                    category="Sea Mine – Rising"),

    # -- Other Mine Types --
    CatalogEntry("36", "110500", "Sea Mine – Other Position",  "Seemine – andere Position",    category="Sea Mine"),
    CatalogEntry("36", "110600", "Kingfisher",                 "Kingfisher",                   category="Sea Mine"),
    CatalogEntry("36", "110700", "Small Object – Mine",        "Kleines Objekt – Mine",        category="Sea Mine"),

    # -- Exercise Mine --
    CatalogEntry("36", "110800", "Exercise Mine – General",    "Übungsmine – allgemein",       category="Exercise Mine"),
    CatalogEntry("36", "110801", "Exercise Mine – Bottom",     "Übungs-Grundmine",             category="Exercise Mine"),
    CatalogEntry("36", "110802", "Exercise Mine – Moored",     "Übungs-Ankermine",             category="Exercise Mine"),
    CatalogEntry("36", "110803", "Exercise Mine – Floating",   "Übungs-Treibmine",             category="Exercise Mine"),
    CatalogEntry("36", "110804", "Exercise Mine – Rising",     "Übungs-Steigmine",             category="Exercise Mine"),

    # -- Neutralized Mine --
    CatalogEntry("36", "110900", "Neutralized Mine – General", "Neutralisierte Mine",          category="Neutralized Mine"),
    CatalogEntry("36", "110901", "Neutralized Mine – Bottom",  "Neutralisierte Grundmine",     category="Neutralized Mine"),
    CatalogEntry("36", "110902", "Neutralized Mine – Moored",  "Neutralisierte Ankermine",     category="Neutralized Mine"),
    CatalogEntry("36", "110903", "Neutralized Mine – Floating","Neutralisierte Treibmine",     category="Neutralized Mine"),
    CatalogEntry("36", "110904", "Neutralized Mine – Rising",  "Neutralisierte Steigmine",     category="Neutralized Mine"),

    # -- Mine-Like Contact (MILCO) --
    CatalogEntry("36", "111000", "MILCO – General",            "MILCO – allgemein",            category="MILCO"),
    CatalogEntry("36", "111100", "MILCO – Low Confidence",     "MILCO – geringe Sicherheit",   category="MILCO"),
    CatalogEntry("36", "111200", "MILCO – High Confidence",    "MILCO – hohe Sicherheit",      category="MILCO"),

    # -- Mine-Like Echo (MILEC) --
    CatalogEntry("36", "111300", "MILEC – General",            "MILEC – allgemein",            category="MILEC"),
    CatalogEntry("36", "111301", "MILEC – Low Confidence",     "MILEC – geringe Sicherheit",   category="MILEC"),
    CatalogEntry("36", "111302", "MILEC – High Confidence",    "MILEC – hohe Sicherheit",      category="MILEC"),

    # -- Decoy/Obstructor --
    CatalogEntry("36", "111400", "Decoy – General",            "Täuschkörper – allgemein",     category="Decoy"),
    CatalogEntry("36", "111500", "Mine Anchor",                "Minenanker",                   category="Mine Anchor"),

    # -- Unexploded Ordnance --
    CatalogEntry("36", "120000", "Unexploded Explosive Ordnance", "Blindgänger",              category="UXO"),
]


# -- Activities (40) ----------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 activites.js

ACTIVITY_ENTRIES: list[CatalogEntry] = [
    # -- Incident --
    CatalogEntry("40", "110000", "Incident",                   "Vorfall",                     category="Incident"),

    # -- Criminal Activity --
    CatalogEntry("40", "110100", "Criminal Activity Incident", "Krimineller Vorfall",         category="Incident – Criminal"),
    CatalogEntry("40", "110101", "Arrest",                     "Festnahme",                   category="Incident – Criminal"),
    CatalogEntry("40", "110102", "Arson",                      "Brandstiftung",               category="Incident – Criminal"),
    CatalogEntry("40", "110103", "Attempted Criminal Activity","Versuchter krim. Vorfall",    category="Incident – Criminal"),
    CatalogEntry("40", "110104", "Drive-by Shooting",          "Fahrschiesserei",             category="Incident – Criminal"),
    CatalogEntry("40", "110105", "Drug Related",               "Drogendelikt",                category="Incident – Criminal"),
    CatalogEntry("40", "110106", "Extortion",                  "Erpressung",                  category="Incident – Criminal"),
    CatalogEntry("40", "110107", "Graffiti",                   "Graffiti",                    category="Incident – Criminal"),
    CatalogEntry("40", "110108", "Killing",                    "Tötung",                      category="Incident – Criminal"),
    CatalogEntry("40", "110109", "Kidnapping",                 "Entführung",                  category="Incident – Criminal"),
    CatalogEntry("40", "110110", "Piracy",                     "Piraterie",                   category="Incident – Criminal"),
    CatalogEntry("40", "110111", "Poisoning",                  "Vergiftung",                  category="Incident – Criminal"),
    CatalogEntry("40", "110112", "Robbery",                    "Raub",                        category="Incident – Criminal"),
    CatalogEntry("40", "110113", "Theft",                      "Diebstahl",                   category="Incident – Criminal"),

    # -- Bombing --
    CatalogEntry("40", "110200", "Bomb/Bombing",               "Bombe/Bombardierung",         category="Incident – Bombing"),
    CatalogEntry("40", "110201", "Bomb Threat",                "Bombendrohung",               category="Incident – Bombing"),
    CatalogEntry("40", "110202", "Booby Trap",                 "Sprengfalle",                 category="Incident – Bombing"),
    CatalogEntry("40", "110203", "VBIED (Detonated)",          "VBIED (detonierd)",           category="Incident – Bombing"),
    CatalogEntry("40", "110204", "IED – Detonated",            "IED – detoniert",             category="Incident – Bombing"),
    CatalogEntry("40", "110205", "IED – Premature Detonation", "IED – Frühdetonation",        category="Incident – Bombing"),
    CatalogEntry("40", "110206", "IED – Suspected",            "IED – vermutet",              category="Incident – Bombing"),
    CatalogEntry("40", "110207", "VBIED (Suspected)",          "VBIED (vermutet)",            category="Incident – Bombing"),

    # -- Shooting / Sniping --
    CatalogEntry("40", "110300", "IED (General)",              "IED (allgemein)",             category="Incident – IED"),
    CatalogEntry("40", "110400", "Shooting",                   "Schiesserei",                 category="Incident"),
    CatalogEntry("40", "110500", "Sniping",                    "Heckenschütze",               category="Incident"),

    # -- Drug-related / Explosion --
    CatalogEntry("40", "110600", "Explosion/Bang",             "Explosion/Knall",             category="Incident"),

    # -- Civil Disturbance --
    CatalogEntry("40", "120000", "Civil Disturbance",          "Zivile Unruhe",               category="Civil Disturbance"),
    CatalogEntry("40", "120100", "Demonstration",              "Demonstration",               category="Civil Disturbance"),
    CatalogEntry("40", "120200", "Riot",                       "Aufruhr",                     category="Civil Disturbance"),

    # -- Operation --
    CatalogEntry("40", "130000", "Operation",                  "Einsatz",                     category="Operation"),
    CatalogEntry("40", "130100", "Patrol (Activity)",          "Patrouille (Aktivität)",      category="Operation"),
    CatalogEntry("40", "130200", "Reconnaissance (Activity)",  "Aufklärung (Aktivität)",      category="Operation"),
    CatalogEntry("40", "130300", "Surveillance",               "Überwachung",                 category="Operation"),
    CatalogEntry("40", "130400", "Engagement",                 "Gefecht",                     category="Operation"),
    CatalogEntry("40", "130500", "Interdiction",               "Abriegelung",                 category="Operation"),
    CatalogEntry("40", "130600", "Ambush",                     "Hinterhalt",                  category="Operation"),
    CatalogEntry("40", "130700", "Cordon and Search",          "Absperren & Durchsuchen",     category="Operation"),
    CatalogEntry("40", "130800", "Security",                   "Sicherung",                   category="Operation"),

    # -- Fire Event --
    CatalogEntry("40", "140000", "Fire Event",                 "Brandereignis",               category="Fire Event"),
    CatalogEntry("40", "140100", "Wildfire",                   "Waldbrand",                   category="Fire Event"),
    CatalogEntry("40", "140200", "Fire – Origin",              "Brand – Ursprung",            category="Fire Event"),
    CatalogEntry("40", "140300", "Hot Spot",                   "Brandnest",                   category="Fire Event"),
    CatalogEntry("40", "140400", "Non-Residential Fire",       "Brand (nicht Wohn-)",         category="Fire Event"),
    CatalogEntry("40", "140500", "Residential Fire",           "Wohnungsbrand",               category="Fire Event"),
    CatalogEntry("40", "140600", "School Fire",                "Schulbrand",                  category="Fire Event"),
    CatalogEntry("40", "140700", "Smoke",                      "Rauch",                       category="Fire Event"),
    CatalogEntry("40", "140800", "Special Needs Fire",         "Brand Sondereinrichtung",     category="Fire Event"),

    # -- HAZMAT --
    CatalogEntry("40", "150000", "HAZMAT",                     "Gefahrgut",                   category="HAZMAT"),
    CatalogEntry("40", "150100", "Chemical Agent",             "Chemischer Kampfstoff",       category="HAZMAT"),
    CatalogEntry("40", "150200", "Combustible",                "Brennstoff",                  category="HAZMAT"),
    CatalogEntry("40", "150300", "Corrosive Material",         "Ätzmittel",                   category="HAZMAT"),
    CatalogEntry("40", "150400", "Explosive",                  "Sprengstoff",                 category="HAZMAT"),
    CatalogEntry("40", "150500", "Flammable Gas",              "Brennbares Gas",              category="HAZMAT"),
    CatalogEntry("40", "150600", "Flammable Liquid",           "Brennbare Flüssigkeit",       category="HAZMAT"),
    CatalogEntry("40", "150700", "Flammable Solid",            "Brennbarer Feststoff",        category="HAZMAT"),
    CatalogEntry("40", "150800", "Non-Flammable Gas",          "Nicht brennbares Gas",        category="HAZMAT"),
    CatalogEntry("40", "150900", "Organic Peroxide",           "Organisches Peroxid",         category="HAZMAT"),
    CatalogEntry("40", "151000", "Oxidizer",                   "Oxidationsmittel",            category="HAZMAT"),
    CatalogEntry("40", "151100", "Radioactive Material",       "Radioaktives Material",       category="HAZMAT"),
    CatalogEntry("40", "151200", "Spontaneously Combustible",  "Selbstentzündlich",           category="HAZMAT"),
    CatalogEntry("40", "151300", "Toxic/Infectious",           "Giftig/Infektiös",            category="HAZMAT"),
    CatalogEntry("40", "151400", "Unexploded Ordnance (Act.)", "Blindgänger (Aktivität)",     category="HAZMAT"),
    CatalogEntry("40", "151500", "Water w/ Calcium Hypochlorite", "Wasser m/ Calciumhypochlorit", category="HAZMAT"),

    # -- Transportation Incident --
    CatalogEntry("40", "160000", "Transportation Incident",    "Verkehrsunfall",              category="Transportation"),
    CatalogEntry("40", "160100", "Air Incident",               "Flugunfall",                  category="Transportation"),
    CatalogEntry("40", "160200", "Marine Incident",            "Seeunfall",                   category="Transportation"),
    CatalogEntry("40", "160300", "Rail Incident",              "Bahnunfall",                  category="Transportation"),
    CatalogEntry("40", "160400", "Vehicle Incident",           "Verkehrsunfall (Strasse)",     category="Transportation"),

    # -- Natural Event --
    CatalogEntry("40", "170000", "Natural Event",              "Naturereignis",               category="Natural Event"),
    CatalogEntry("40", "170100", "Avalanche",                  "Lawine",                      category="Natural Event"),
    CatalogEntry("40", "170200", "Earthquake",                 "Erdbeben",                    category="Natural Event"),
    CatalogEntry("40", "170300", "Flood",                      "Überschwemmung",              category="Natural Event"),
    CatalogEntry("40", "170400", "Infestation",                "Plage",                       category="Natural Event"),
    CatalogEntry("40", "170500", "Landslide/Mudslide",         "Erdrutsch",                   category="Natural Event"),
    CatalogEntry("40", "170600", "Tornado",                    "Tornado",                     category="Natural Event"),
    CatalogEntry("40", "170700", "Tsunami",                    "Tsunami",                     category="Natural Event"),
    CatalogEntry("40", "170800", "Volcanic Eruption",          "Vulkanausbruch",              category="Natural Event"),

    # -- Emergency –-
    CatalogEntry("40", "180000", "Emergency Medical Operations", "Notfall-Sanitätseinsatz",   category="Emergency"),
    CatalogEntry("40", "180100", "Emergency Collection Point (Act.)", "Notsammelstelle (Akt.)",category="Emergency"),
    CatalogEntry("40", "180200", "Emergency Incident CP",      "Notfall-Einsatzposten",       category="Emergency"),
    CatalogEntry("40", "180300", "Emergency Operations Center","Notrufzentrale",              category="Emergency"),
    CatalogEntry("40", "180400", "Emergency Shelter",          "Notunterkunft",               category="Emergency"),
    CatalogEntry("40", "180500", "Emergency Staging Area",     "Notfall-Bereitstellungsraum", category="Emergency"),
    CatalogEntry("40", "180600", "Emergency Food Distribution","Lebensmittelverteilung",      category="Emergency"),
    CatalogEntry("40", "180700", "Emergency Water Distribution", "Wasserverteilung",          category="Emergency"),
]


# -- SIGINT – shared entity codes for sets 50-54 ------------------------
# Entity codes aligned with milsymbol v3.0.4 signalsintelligence.js

def _sigint_entries(symbol_set: str) -> list[CatalogEntry]:
    """Build SIGINT catalog entries for a given symbol set (50–54)."""
    return [
        CatalogEntry(symbol_set, "110000", "Signal Intercept",           "Signalaufklärung",     category="SIGINT"),
        CatalogEntry(symbol_set, "110100", "Communications",            "Kommunikation",        category="SIGINT"),
        CatalogEntry(symbol_set, "110200", "Jammer / ECM",              "Störer / ECM",         category="SIGINT"),
        CatalogEntry(symbol_set, "110300", "Radar",                     "Radar",                category="SIGINT"),
    ]


SIGINT_SPACE_ENTRIES:      list[CatalogEntry] = _sigint_entries("50")
SIGINT_AIR_ENTRIES:        list[CatalogEntry] = _sigint_entries("51")
SIGINT_LAND_ENTRIES:       list[CatalogEntry] = _sigint_entries("52")
SIGINT_SURFACE_ENTRIES:    list[CatalogEntry] = _sigint_entries("53")
SIGINT_SUBSURFACE_ENTRIES: list[CatalogEntry] = _sigint_entries("54")


# -- Cyberspace (60) ----------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 cyberspace.js

CYBERSPACE_ENTRIES: list[CatalogEntry] = [
    # -- Botnet --
    CatalogEntry("60", "110000", "Botnet",                     "Botnetz",                     category="Botnet"),
    CatalogEntry("60", "110100", "C2 / Command and Control",   "C2 / Führung",                category="Botnet"),
    CatalogEntry("60", "110200", "Herder",                     "Herder",                      category="Botnet"),
    CatalogEntry("60", "110300", "Callback Domain",            "Callback-Domäne",             category="Botnet"),
    CatalogEntry("60", "110400", "Zombie",                     "Zombie",                      category="Botnet"),

    # -- Infection --
    CatalogEntry("60", "120000", "Infection",                  "Infektion",                   category="Infection"),
    CatalogEntry("60", "120100", "Advanced Persistent Threat", "APT",                         category="Infection"),
    CatalogEntry("60", "120200", "Non-Advanced Persistent Threat", "Nicht-APT",               category="Infection"),

    # -- Health & Status --
    CatalogEntry("60", "130000", "Health and Status",          "Zustand & Status",            category="Health & Status"),
    CatalogEntry("60", "130100", "Normal",                     "Normal",                      category="Health & Status"),
    CatalogEntry("60", "130200", "Network Outage",             "Netzwerkausfall",             category="Health & Status"),
    CatalogEntry("60", "130300", "Known Intrusion",            "Bekannte Intrusion",          category="Health & Status"),
    CatalogEntry("60", "130400", "Known Compromised",          "Bekannter Kompromiss",        category="Health & Status"),

    # -- Device Type --
    CatalogEntry("60", "140000", "Device Type",                "Gerätetyp",                   category="Device"),
    CatalogEntry("60", "140100", "Core Router",                "Core-Router",                 category="Device"),
    CatalogEntry("60", "140200", "Router",                     "Router",                      category="Device"),
    CatalogEntry("60", "140300", "Cross Domain Solution",      "Cross-Domain-Lösung",         category="Device"),
    CatalogEntry("60", "140400", "Mail Server",               "Mail-Server",                  category="Device"),
    CatalogEntry("60", "140500", "Web Server",                "Web-Server",                   category="Device"),
    CatalogEntry("60", "140600", "Peer-to-Peer Node",         "Peer-to-Peer-Knoten",          category="Device"),
    CatalogEntry("60", "140700", "Firewall",                  "Firewall",                     category="Device"),
    CatalogEntry("60", "140800", "Switch",                    "Switch",                       category="Device"),
    CatalogEntry("60", "140900", "Host",                      "Host",                         category="Device"),
    CatalogEntry("60", "141000", "Virtual Private Network",   "VPN",                          category="Device"),

    # -- Device Domain --
    CatalogEntry("60", "150000", "Device Domain",             "Gerätedomäne",                 category="Device Domain"),
    CatalogEntry("60", "150100", "Department of Defense (DoD)","DoD-Domäne",                  category="Device Domain"),
    CatalogEntry("60", "150200", "Government",               "Regierungsdomäne",              category="Device Domain"),
    CatalogEntry("60", "150300", "Contractor",               "Auftragnehmerdomäne",           category="Device Domain"),
    CatalogEntry("60", "150400", "Supervisory Control/SCADA", "SCADA-Domäne",                 category="Device Domain"),
    CatalogEntry("60", "150500", "Non-Government",           "Nichtstaatliche Domäne",        category="Device Domain"),

    # -- Effect --
    CatalogEntry("60", "160000", "Effect",                   "Wirkung",                       category="Effect"),
    CatalogEntry("60", "160100", "Achieve",                  "Erreichen",                     category="Effect"),
    CatalogEntry("60", "160200", "Block",                    "Blockieren",                    category="Effect"),
    CatalogEntry("60", "160300", "Degrade",                  "Beeinträchtigen",               category="Effect"),
    CatalogEntry("60", "160400", "Deny",                     "Verweigern",                    category="Effect"),
    CatalogEntry("60", "160500", "Destroy",                  "Zerstören",                     category="Effect"),
    CatalogEntry("60", "160600", "Disrupt",                  "Stören",                        category="Effect"),
    CatalogEntry("60", "160700", "Locate",                   "Orten",                         category="Effect"),
    CatalogEntry("60", "160800", "Manipulate",              "Manipulieren",                   category="Effect"),
    CatalogEntry("60", "160900", "Neutralize",              "Neutralisieren",                 category="Effect"),

    # -- Large --
    CatalogEntry("60", "170000", "Large",                    "Gross",                         category="Large"),
    CatalogEntry("60", "170100", "Server",                   "Server",                        category="Large"),
    CatalogEntry("60", "170200", "Desktop Workstation",      "Desktop-Arbeitsstation",        category="Large"),

    # -- Network --
    CatalogEntry("60", "180000", "Network",                  "Netzwerk",                      category="Network"),

    # -- Small --
    CatalogEntry("60", "190000", "Small",                    "Klein",                         category="Small"),
    CatalogEntry("60", "190100", "Handheld",                 "Handgerät",                     category="Small"),
    CatalogEntry("60", "190200", "Laptop",                   "Laptop",                        category="Small"),
    CatalogEntry("60", "190300", "Cellular Phone",           "Mobiltelefon",                  category="Small"),
    CatalogEntry("60", "190400", "Tablet",                   "Tablet",                        category="Small"),

    # -- Persona / Organization --
    CatalogEntry("60", "200000", "Persona Type",             "Personentyp",                   category="Persona"),
    CatalogEntry("60", "200100", "Online Persona",           "Online-Persona",                category="Persona"),
    CatalogEntry("60", "200200", "Organization",             "Organisation",                  category="Persona"),
]


# ======================================================================
# Swiss conventional signs (Reg. 52.002.04) – placeholders
# ======================================================================

SWISS_CONVENTIONAL_ENTRIES: list[CatalogEntry] = [
    CatalogEntry("10", "310000", "Civil Protection",    "Zivilschutz",        category="Swiss Conventional", name_fr="Protection civile", name_it="Protezione civile"),
    CatalogEntry("10", "320000", "Fire Brigade",        "Feuerwehr",          category="Swiss Conventional", name_fr="Pompiers",           name_it="Pompieri"),
    CatalogEntry("10", "330000", "Police",              "Polizei",            category="Swiss Conventional", name_fr="Police",             name_it="Polizia"),
    CatalogEntry("10", "340000", "Border Guard",        "Grenzwachtkorps",    category="Swiss Conventional", name_fr="Cgfr",               name_it="Cgcf"),
    CatalogEntry("10", "350000", "Customs",             "Zoll",               category="Swiss Conventional", name_fr="Douane",             name_it="Dogana"),
    CatalogEntry("10", "360000", "Health Service",      "Gesundheitsdienst",  category="Swiss Conventional", name_fr="Service sanitaire",  name_it="Servizio sanitario"),
]


# ======================================================================
# Aggregate catalog
# ======================================================================

ALL_ENTRIES: list[CatalogEntry] = (
    AIR_ENTRIES
    + AIR_MISSILE_ENTRIES
    + SPACE_ENTRIES
    + SPACE_MISSILE_ENTRIES
    + LAND_UNIT_ENTRIES
    + LAND_CIVILIAN_ENTRIES
    + LAND_EQUIPMENT_ENTRIES
    + LAND_INSTALLATION_ENTRIES
    + SEA_SURFACE_ENTRIES
    + SEA_SUBSURFACE_ENTRIES
    + MINE_WARFARE_ENTRIES
    + ACTIVITY_ENTRIES
    + SIGINT_SPACE_ENTRIES
    + SIGINT_AIR_ENTRIES
    + SIGINT_LAND_ENTRIES
    + SIGINT_SURFACE_ENTRIES
    + SIGINT_SUBSURFACE_ENTRIES
    + CYBERSPACE_ENTRIES
    + SWISS_CONVENTIONAL_ENTRIES
)


# -- Symbol-Set human-readable names ------------------------------------

SYMBOL_SET_NAMES: dict[str, str] = {
    "01": "Air",
    "02": "Air Missile",
    "05": "Space",
    "06": "Space Missile",
    "10": "Land Unit",
    "11": "Land Civilian",
    "15": "Land Equipment",
    "20": "Land Installation",
    "25": "Control Measure",
    "30": "Sea Surface",
    "35": "Sea Subsurface",
    "36": "Mine Warfare",
    "40": "Activities",
    "45": "METOC – Atmospheric",
    "46": "METOC – Oceanographic",
    "47": "METOC – Space",
    "50": "SIGINT – Space",
    "51": "SIGINT – Air",
    "52": "SIGINT – Land",
    "53": "SIGINT – Surface",
    "54": "SIGINT – Subsurface",
    "60": "Cyberspace",
}


# -- Lookup helpers -----------------------------------------------------

_INDEX_BY_SET: dict[str, list[CatalogEntry]] | None = None


def entries_by_symbol_set(symbol_set: str) -> list[CatalogEntry]:
    """Return all catalog entries for a given symbol-set code."""
    global _INDEX_BY_SET
    if _INDEX_BY_SET is None:
        _INDEX_BY_SET = {}
        for e in ALL_ENTRIES:
            _INDEX_BY_SET.setdefault(e.symbol_set, []).append(e)
    return _INDEX_BY_SET.get(symbol_set, [])


def find_entry(symbol_set: str, entity_code: str) -> Optional[CatalogEntry]:
    """Find a catalog entry by symbol set and entity code."""
    for e in entries_by_symbol_set(symbol_set):
        if e.entity_code == entity_code:
            return e
    return None


def search_catalog(query: str) -> list[CatalogEntry]:
    """Full-text search across name / name_de / category.

    Returns entries whose name, German name, or category contains
    *query* (case-insensitive).
    """
    q = query.lower()
    return [
        e
        for e in ALL_ENTRIES
        if q in e.name.lower()
        or q in e.name_de.lower()
        or q in e.category.lower()
    ]
