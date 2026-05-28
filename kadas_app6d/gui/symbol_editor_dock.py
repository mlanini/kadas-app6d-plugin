# -*- coding: utf-8 -*-
"""
Symbol Editor floating dialog – popup editor for military symbols.

Opened from the symbol catalog (right-click → "Edit…") or from
right-clicking a symbol feature on the map canvas.  Allows editing all
SIDC components, text amplifiers and temporal attributes; changes are
applied live to the layer.

Layout (top → bottom)
---------------------
1. **Designation / Comment** text fields
2. **Symbology combos** (Identity, Symbol Set, Entity, Echelon, …)
3. **Preview** – live SVG preview
4. **Temporal** – optional start / end
5. **Place on Map / Apply / Delete** buttons
"""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt, QByteArray, pyqtSignal, QDateTime
from qgis.PyQt.QtGui import QImage, QPainter, QPixmap
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.models import MilSymbol
from ..core.sidc import (
    SIDC as SIDCClass,
    Echelon,
    HqTfDummy,
    STANDARD_IDENTITY_LABELS,
    StandardIdentity,
    Status,
    SymbolSet,
)
from . import DARK_THEME_SS
from ..symbology.catalog_data import (
    SYMBOL_SET_NAMES,
    CatalogEntry,
    entries_by_symbol_set,
)
from ..symbology.renderer import cached_svg
from ..logger import get_logger

LOG = get_logger("kadas_milsymb.gui.symbol_editor_dock")

_PREVIEW_SIZE = 96

# Per-symbol-set APP-6D Modifier label dictionaries.
# Keys are SymbolSet.value strings; each entry has "m1" and "m2" sub-dicts
# mapping two-digit code strings to human-readable labels.
_MOD_LABELS: dict[str, dict[str, dict[str, str]]] = {
    "01": {  # Air
        "m1": {
            "00": "None",
            "01": "Attack", "02": "Bomber", "03": "Cargo", "04": "Fighter",
            "05": "Interceptor", "06": "Tanker", "07": "Utility", "08": "VSTOL",
            "09": "Passenger", "10": "Ultra Light", "11": "Airborne Command Post",
            "12": "Airborne Early Warning", "13": "Government", "14": "Medevac",
            "15": "Escort", "16": "Jammer/ECM", "17": "Patrol",
            "18": "Reconnaissance", "19": "Trainer", "20": "Photographic",
            "21": "Personnel Recovery", "22": "ASW", "23": "Communications",
            "24": "Electronic Support", "25": "Mine Countermeasures", "26": "SAR",
            "27": "SOF", "28": "Surface Warfare", "29": "VIP",
            "30": "Combat SAR", "31": "SEAD", "32": "Antisurface Warfare",
            "33": "Fighter/Bomber", "34": "Intensive Care",
            "35": "Electronic Attack", "36": "Multimission",
            "37": "Hijacking", "38": "ASW LAMPS", "39": "ASW SH-60R",
            "40": "Hijacker", "41": "Cyberspace",
        },
        "m2": {
            "00": "None",
            "01": "Heavy", "02": "Medium", "03": "Light",
            "04": "Boom-Only", "05": "Drogue-Only", "06": "Boom and Drogue",
            "07": "Close Range", "08": "Short Range", "09": "Medium Range",
            "10": "Long Range", "11": "Downlinked", "12": "Cyberspace",
        },
    },
    "02": {  # Air Missile
        "m1": {
            "00": "None",
            "01": "Air", "02": "Surface", "03": "Subsurface", "04": "Space",
            "05": "Anti-Ballistic", "06": "Ballistic", "07": "Cruise",
            "08": "Interceptor", "09": "Hypersonic",
        },
        "m2": {
            "00": "None",
            "01": "Air", "02": "Surface", "03": "Subsurface", "04": "Space",
            "05": "Launched", "06": "Missile", "07": "Patriot", "08": "SM-2",
            "09": "SM-6", "10": "ESSM", "11": "RAM",
            "12": "Short Range", "13": "Medium Range",
            "14": "Intermediate Range", "15": "Long Range",
            "16": "Intercontinental",
        },
    },
    "06": {  # Space Missile
        "m1": {
            "00": "None",
            "01": "Ballistic", "02": "Space", "03": "Interceptor",
            "04": "Hypersonic",
        },
        "m2": {
            "00": "None",
            "01": "Short Range", "02": "Medium Range",
            "03": "Intermediate Range", "04": "Long Range",
            "05": "Intercontinental", "06": "Arrow", "07": "GBI",
            "08": "Patriot", "09": "SM-T", "10": "SM-3", "11": "THAAD",
            "12": "Space", "13": "Close Range", "14": "Debris",
            "15": "Unknown",
        },
    },
    "10": {  # Land Unit
        "m1": {
            "00": "None",
            "01": "Airmobile/Air Assault", "02": "Area", "03": "Attack",
            "04": "Biological", "05": "Border", "06": "Bridging",
            "07": "Chemical", "08": "Close Protection", "09": "Combat",
            "10": "Command and Control",
            "11": "Communications Contingency Package",
            "12": "Construction", "13": "Cross Cultural Communication",
            "14": "Crowd and Riot Control", "15": "Decontamination",
            "16": "Detention", "17": "Direct Communications",
            "18": "Diving", "19": "Division", "20": "Dog",
            "21": "Drilling", "22": "Electro-Optical", "23": "Enhanced",
            "24": "Explosive Ordnance Disposal",
            "25": "Fire Direction Centre", "26": "Force", "27": "Forward",
            "28": "Ground Station Module", "29": "Landing Support",
            "30": "Large Extension Node", "31": "Maintenance",
            "32": "Meteorological", "33": "Mine Countermeasure",
            "34": "Missile", "35": "(Mobile) Advisor and Support",
            "36": "Mobile Subscriber Equipment", "37": "Mobility Support",
            "38": "Movement Control Centre", "39": "Multinational",
            "40": "Multinational Specialized Unit",
            "41": "Multiple Rocket Launcher",
            "42": "NATO Medical Role 1", "43": "NATO Medical Role 2",
            "44": "NATO Medical Role 3", "45": "NATO Medical Role 4",
            "46": "Naval", "47": "Node Centre", "48": "Nuclear",
            "49": "Operations", "50": "Radar",
            "51": "RFID Interrogator/Sensor", "52": "Radiological",
            "53": "Search and Rescue", "54": "Security", "55": "Sensor",
            "56": "Sensor Control Module", "57": "Signals Intelligence",
            "58": "Single Shelter Switch", "59": "Single Rocket Launcher",
            "60": "Smoke", "61": "Sniper", "62": "Sound Ranging",
            "63": "Special Operations Forces (SOF)",
            "64": "Special Weapons and Tactics",
            "65": "Survey", "66": "Tactical Exploitation",
            "67": "Target Acquisition", "68": "Topographic",
            "69": "Utility", "70": "Video Imagery",
            "71": "Accident", "72": "Other", "73": "Civilian",
            "74": "Antisubmarine Warfare", "75": "Medevac",
            "76": "Ranger", "77": "Support", "78": "Aviation",
            "79": "Route, Reconnaissance and Clearance",
            "80": "Tilt-Rotor", "81": "Command Post Node",
            "82": "Joint Network Node", "83": "Retransmission Site",
            "84": "Assault", "85": "Weapons",
            "86": "Criminal Investigation Division", "87": "Digital",
            "88": "Network Operations", "89": "Airfield/Aerial Port",
            "90": "Pipeline", "91": "Postal", "92": "Water",
            "93": "Independent Command", "94": "Theatre",
            "95": "Army", "96": "Corps", "97": "Brigade",
            "98": "HQ Element", "99": "Multi-Domain",
        },
        "m2": {
            "00": "None",
            "01": "Airborne", "02": "Arctic", "03": "Battle Damage Repair",
            "04": "Bicycle Equipped", "05": "Casualty Staging",
            "06": "Clearing", "07": "Close Range", "08": "Control",
            "09": "Decontamination", "10": "Demolition", "11": "Dental",
            "12": "Digital", "13": "EPLRS", "14": "Equipment",
            "15": "Heavy", "16": "High Altitude", "17": "Intermodal",
            "18": "Intensive Care", "19": "Light", "20": "Laboratory",
            "21": "Launcher", "22": "Long Range", "23": "Low Altitude",
            "24": "Medium", "25": "Medium Altitude", "26": "Medium Range",
            "27": "Mountain", "28": "High to Medium Altitude",
            "29": "Multi-Channel", "30": "Optical", "31": "Pack Animal",
            "32": "Patient Evacuation Coordination",
            "33": "Preventive Maintenance", "34": "Psychological",
            "35": "Radio Relay LOS", "36": "Railroad",
            "37": "Recovery (Unmanned Systems)", "38": "Recovery (Maintenance)",
            "39": "Rescue Coordination Centre", "40": "Riverine",
            "41": "Single Channel", "42": "Ski", "43": "Short Range",
            "44": "Strategic", "45": "Support", "46": "Tactical",
            "47": "Towed", "48": "Troop", "49": "VSTOL",
            "50": "Veterinary", "51": "Wheeled",
            "52": "High to Low Altitude", "53": "Medium to Low Altitude",
            "54": "Attack", "55": "Refuel", "56": "Utility",
            "57": "Combat Search and Rescue", "58": "Guerilla",
            "59": "Air Assault", "60": "Amphibious", "61": "Very Heavy",
            "62": "Supply", "63": "Cyberspace",
            "74": "Composite", "75": "Shelter",
            "76": "Light and Medium", "77": "Self-Propelled",
            "78": "Security Force Assistance",
            "81": "Surgical", "82": "Blood",
            "83": "Combat Stress Control", "84": "Jamming",
            "86": "Optometry", "87": "Preventive Medicine",
            "89": "Air Defence",
        },
    },
    "11": {  # Land Civilian
        "m1": {
            "00": "None",
            "22": "Combat", "23": "Other", "24": "Loot",
            "25": "Hijacker", "26": "Cyberspace",
        },
        "m2": {
            "00": "None",
            "01": "Leader/Leadership", "02": "Cyberspace",
        },
    },
    "15": {  # Land Equipment
        "m1": {
            "00": "None",
            "10": "Tilt-Rotor", "12": "Multi-Purpose Blade",
            "13": "Tank-Width Mine Plow", "14": "Bridging",
            "15": "Cyberspace", "16": "Armored", "17": "Attack",
            "18": "Cargo", "19": "Maintenance", "20": "Medevac",
            "21": "Petroleum", "22": "Utility", "23": "Water",
            "24": "Robotic",
        },
        "m2": {
            "00": "None",
            "01": "Cyberspace", "02": "Light", "03": "Medium",
            "04": "Railroad", "05": "Tracked", "06": "Tractor Trailer",
            "07": "Wheeled Limited",
        },
    },
    "20": {  # Land Installation
        "m1": {
            "00": "None",
            "01": "Biological", "02": "Chemical", "03": "Nuclear",
            "04": "Radiological", "05": "Decontamination",
            "06": "Coal", "07": "Geothermal", "08": "Hydroelectric",
            "09": "Natural Gas", "10": "Petroleum", "11": "Civilian",
            "12": "Civilian Telephone", "13": "Civilian Television",
            "14": "Cyberspace",
        },
        "m2": {"00": "None"},
    },
    "30": {  # Sea Surface
        "m1": {
            "00": "None",
            "01": "Antisubmarine Warfare", "02": "Auxiliary",
            "03": "Command and Control", "04": "ISR",
            "05": "Mine Countermeasures", "06": "Mine Warfare",
            "07": "Surface Warfare", "08": "Missile Defense",
            "09": "Medical", "10": "Mine Warfare (Remote)",
            "12": "SOF", "13": "Surface Warfare (Alternate)",
            "14": "Ballistic Missile", "15": "Guided Missile",
            "16": "Other Guided Missile", "17": "Torpedo",
            "18": "Drone-Equipped", "19": "Helicopter-Equipped",
            "20": "BMD Shooter", "21": "BMD LRS&T",
            "22": "Sea-Base X-Band", "23": "Hijacking",
            "25": "Cyberspace",
        },
        "m2": {"00": "None"},
    },
    "35": {  # Sea Subsurface
        "m1": {"00": "None"},
        "m2": {"00": "None"},
    },
}


# ======================================================================
# Helpers
# ======================================================================

def _svg_to_pixmap(svg_str: str, size: int) -> QPixmap | None:
    """Convert an SVG string to a QPixmap preserving SVG aspect ratio.

    The rendered image fits inside a ``size × size`` bounding box,
    so rectangular frames (e.g. APP-6 Friend) look proportionally correct.
    """
    try:
        from qgis.PyQt.QtSvg import QSvgRenderer
    except ImportError:
        return None
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    if not renderer.isValid():
        return None
    natural = renderer.defaultSize()
    if natural.width() > 0 and natural.height() > 0:
        ratio = natural.width() / natural.height()
    else:
        ratio = 1.0
    if ratio >= 1.0:
        w = size
        h = max(1, round(size / ratio))
    else:
        h = size
        w = max(1, round(size * ratio))
    image = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return QPixmap.fromImage(image)


# ======================================================================
# SymbolEditorDockWidget
# ======================================================================

class SymbolEditorDockWidget(QDockWidget):
    """Dock widget editor for a single :class:`MilSymbol` or catalogue entry.

    Signals
    -------
    symbol_updated(str)
        Emitted with the symbol id after the user applies changes.
    symbol_deleted(str)
        Emitted with the symbol id after the user deletes the symbol.
    symbol_placed(object)
        Emitted when the user places a new symbol on the map.
    """

    symbol_updated = pyqtSignal(str)
    symbol_deleted = pyqtSignal(str)
    symbol_placed = pyqtSignal(object)
    # Emitted after the user applies changes to an ORBAT unit (not a map symbol)
    orbat_unit_updated = pyqtSignal(object)  # OrbatUnit

    def __init__(self, iface, action=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Symbol Editor")
        self.setMinimumWidth(340)
        self._iface = iface
        self._action = action

        # Container widget wrapped in a scroll area so content is
        # always accessible even when the dock is shorter than its contents.
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._container)
        self.setWidget(self._scroll)

        # External bindings
        self._layer_manager = None

        # Currently edited symbol (None = nothing selected)
        self._symbol: MilSymbol | None = None

        # If editing an ORBAT unit (no map symbol yet), keep a reference here
        self._orbat_unit = None

        # Map tool reference for placement
        self._map_tool = None

        self._build_ui()
        self._set_editing_enabled(False)
        LOG.debug("SymbolEditorDockWidget created")

    def closeEvent(self, event):  # noqa: N802
        """Uncheck the ribbon action when the dock is closed by the user."""
        if self._action is not None:
            self._action.setChecked(False)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # External bindings / lifecycle helpers
    # ------------------------------------------------------------------

    def reset_to_new_symbol_mode(self) -> None:
        """Switch the editor to 'new symbol' mode (Place button visible, no current symbol)."""
        self._symbol = None
        self._orbat_unit = None
        self.setWindowTitle("Symbol Editor")
        self._set_editing_enabled(True)
        self._place_btn.setVisible(True)
        self._apply_btn.setVisible(False)
        self._delete_btn.setVisible(False)

    def set_layer_manager(self, mgr) -> None:
        self._layer_manager = mgr

    def sync_symbol(self, sym: MilSymbol) -> None:
        """Load *sym* into the editor and switch to edit mode.

        Called on single left-click on a map symbol.  Always populates
        the editor regardless of dock visibility state.
        Does not replace an unsaved ORBAT-unit edit in progress.
        """
        # Don't replace an unsaved ORBAT-unit edit
        if self._orbat_unit is not None:
            return
        self._orbat_unit = None
        self._symbol = sym
        self._populate_from_symbol(sym)
        self._set_editing_enabled(True)
        self._place_btn.setVisible(False)
        self._apply_btn.setVisible(True)
        self._delete_btn.setVisible(True)
        label = sym.designation or sym.sidc[:10]
        self.setWindowTitle(f"Symbol Editor  –  {label}")
        LOG.debug("Editor synced to sym %s", sym.id[:8])

    # ------------------------------------------------------------------
    # Public – load a symbol for editing
    # ------------------------------------------------------------------

    def edit_orbat_unit(self, unit) -> None:
        """Open the editor to edit an :class:`OrbatUnit` that has no map symbol.

        Builds a temporary :class:`MilSymbol` from the unit's data so the
        full APP-6(D) editor is reused.  On Apply the changes are written
        back to *unit* and the :pyqtSignal:`orbat_unit_updated` signal is emitted.
        """
        from ..core.models import MilSymbol

        # Build a transient MilSymbol that mirrors the unit
        tmp = MilSymbol(
            id=unit.id,          # same id so update_symbol is a no-op (not in layer)
            sidc=unit.sidc,
            designation=unit.name,
            higher_formation=unit.short_name,
            temporal=unit.temporal,
        )
        self.edit_symbol(tmp)
        # Re-set after edit_symbol (which resets _orbat_unit to None)
        self._orbat_unit = unit
        # Hide place/delete buttons – we only allow Apply for ORBAT units
        self._delete_btn.setVisible(False)
        self.setWindowTitle(f"Symbol Editor  –  {unit.name or 'Unit'}")

    def edit_symbol(self, sym: MilSymbol) -> None:
        """Populate all fields from *sym* and enable editing."""
        self._orbat_unit = None  # entering normal map-symbol edit mode
        self._symbol = sym
        self._populate_from_symbol(sym)
        self._set_editing_enabled(True)
        # In editing mode the Place button is hidden (symbol already on map)
        self._place_btn.setVisible(False)
        self._apply_btn.setVisible(True)
        self._delete_btn.setVisible(True)
        LOG.debug("Editing symbol %s (SIDC=%s)", sym.id[:8], sym.sidc)

    def load_from_catalog(self, entry: CatalogEntry,
                          identity: StandardIdentity | None = None,
                          echelon: Echelon | None = None) -> None:
        """Initialise the editor from a catalog entry (new symbol mode).

        Parameters
        ----------
        entry : CatalogEntry
            The catalog entry to load.
        identity : StandardIdentity or None
            If given, set the Identity combo to this value.
        echelon : Echelon or None
            If given, set the Echelon combo to this value.

        In this mode the *Apply / Delete* buttons are hidden and the
        *Place on Map* button is shown instead.
        """
        self._symbol = None  # not editing an existing symbol

        self._block_combos(True)

        #  clear text fields
        self._designation_edit.clear()
        self._higher_edit.clear()
        self._comment_edit.clear()
        self._quantity_edit.clear()
        self._staff_comments_edit.clear()
        self._additional_info_edit.clear()
        self._eval_rating_edit.clear()
        self._combat_eff_edit.clear()
        self._dtg_edit.clear()
        self._type_edit.clear()
        self._speed_edit.clear()
        self._altitude_edit.clear()
        self._direction_edit.clear()

        # Identity – carry over from catalog dock
        if identity is not None:
            self._select_combo_data(self._identity_combo, identity)

        # Echelon – carry over from catalog dock
        if echelon is not None:
            self._select_combo_data(self._echelon_combo, echelon)

        # Symbol set
        for i in range(self._symbol_set_combo.count()):
            if self._symbol_set_combo.itemData(i).value == entry.symbol_set:
                self._symbol_set_combo.setCurrentIndex(i)
                break

        # Refresh entity list for the chosen symbol set
        self._refresh_entity_combo()

        # Rebuild modifier combos and pre-select from catalog entry
        self._refresh_mod_combos(
            restore_m1=entry.modifier_1 or "00",
            restore_m2=entry.modifier_2 or "00",
        )

        # Select the matching entity (match by code + modifiers)
        for i in range(self._entity_combo.count()):
            data = self._entity_combo.itemData(i)
            if (data
                    and data.entity_code == entry.entity_code
                    and data.modifier_1 == entry.modifier_1
                    and data.modifier_2 == entry.modifier_2):
                self._entity_combo.setCurrentIndex(i)
                break

        self._t_start_check.setChecked(False)
        self._t_end_check.setChecked(False)
        self._coord_label.setText("")

        self._block_combos(False)

        # Switch UI mode: show Place, hide Apply/Delete
        self._set_editing_enabled(True)
        self._place_btn.setVisible(True)
        self._apply_btn.setVisible(False)
        self._delete_btn.setVisible(False)

        self._update_preview()
        LOG.info("Editor loaded from catalog: %s", entry.name)

    def clear_editor(self) -> None:
        """Clear all fields and disable editing."""
        self._symbol = None
        self._designation_edit.clear()
        self._higher_edit.clear()
        self._comment_edit.clear()
        self._quantity_edit.clear()
        self._staff_comments_edit.clear()
        self._additional_info_edit.clear()
        self._eval_rating_edit.clear()
        self._combat_eff_edit.clear()
        self._dtg_edit.clear()
        self._type_edit.clear()
        self._speed_edit.clear()
        self._altitude_edit.clear()
        self._direction_edit.clear()
        self._sidc_label.setText("")
        self._preview_label.clear()
        self._preview_label.setText("No symbol selected")
        self._set_editing_enabled(False)
        self._place_btn.setVisible(False)
        self._apply_btn.setVisible(False)
        self._delete_btn.setVisible(False)

    def set_show_text_modifiers(self, show: bool) -> None:
        pass # Disabilitato: la visibilità è gestita dal collapse interno.

    def _toggle_text_modifiers(self, checked: bool) -> None:
        """Toggle inner widgets of the modifier group to expand/collapse."""
        layout = self._mod_group.layout()
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(checked)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = self._container_layout
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        container = QWidget()
        container.setStyleSheet(DARK_THEME_SS)
        container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ---- Text fields ----
        txt_group = QGroupBox("Core Text")
        txt_layout = QFormLayout(txt_group)

        self._designation_edit = QLineEdit()
        self._designation_edit.setPlaceholderText("Unique Designation (T)")
        txt_layout.addRow("Designation:", self._designation_edit)

        self._higher_edit = QLineEdit()
        self._higher_edit.setPlaceholderText("Higher Formation (M)")
        txt_layout.addRow("Higher form.:", self._higher_edit)

        self._comment_edit = QLineEdit()
        self._comment_edit.setPlaceholderText("General Comment")
        txt_layout.addRow("Comment:", self._comment_edit)

        layout.addWidget(txt_group)

        # ---- Extended Text Modifiers ----
        self._mod_group = QGroupBox("Text Modifiers")
        self._mod_group.setCheckable(True)
        self._mod_group.setChecked(False)
        self._mod_group.toggled.connect(self._toggle_text_modifiers)
        mod_layout = QFormLayout(self._mod_group)

        self._quantity_edit = QLineEdit()
        self._quantity_edit.setPlaceholderText("Quantity (C)")
        mod_layout.addRow("Quantity:", self._quantity_edit)

        self._staff_comments_edit = QLineEdit()
        self._staff_comments_edit.setPlaceholderText("Staff Comments (G)")
        mod_layout.addRow("Staff Cmds:", self._staff_comments_edit)

        self._additional_info_edit = QLineEdit()
        self._additional_info_edit.setPlaceholderText("Additional Info (H)")
        mod_layout.addRow("Add. Info:", self._additional_info_edit)

        self._eval_rating_edit = QLineEdit()
        self._eval_rating_edit.setPlaceholderText("Eval Rating (J)")
        mod_layout.addRow("Eval Rating:", self._eval_rating_edit)

        self._combat_eff_edit = QLineEdit()
        self._combat_eff_edit.setPlaceholderText("Combat Effectiveness (K)")
        mod_layout.addRow("Combat Eff:", self._combat_eff_edit)

        self._dtg_edit = QLineEdit()
        self._dtg_edit.setPlaceholderText("Date-Time Group (W)")
        mod_layout.addRow("DTG:", self._dtg_edit)

        self._type_edit = QLineEdit()
        self._type_edit.setPlaceholderText("Type (V)")
        mod_layout.addRow("Type:", self._type_edit)

        self._speed_edit = QLineEdit()
        self._speed_edit.setPlaceholderText("Speed/Velocity (Z)")
        mod_layout.addRow("Speed:", self._speed_edit)

        self._altitude_edit = QLineEdit()
        self._altitude_edit.setPlaceholderText("Altitude/Depth (X)")
        mod_layout.addRow("Alt/Depth:", self._altitude_edit)

        self._direction_edit = QLineEdit()
        self._direction_edit.setPlaceholderText("Direction in degrees (Q)")
        mod_layout.addRow("Direction:", self._direction_edit)

        # Connect text changes to preview
        self._designation_edit.textChanged.connect(self._on_sym_changed)
        self._higher_edit.textChanged.connect(self._on_sym_changed)
        self._comment_edit.textChanged.connect(self._on_sym_changed)
        self._quantity_edit.textChanged.connect(self._on_sym_changed)
        self._staff_comments_edit.textChanged.connect(self._on_sym_changed)
        self._additional_info_edit.textChanged.connect(self._on_sym_changed)
        self._eval_rating_edit.textChanged.connect(self._on_sym_changed)
        self._combat_eff_edit.textChanged.connect(self._on_sym_changed)
        self._dtg_edit.textChanged.connect(self._on_sym_changed)
        self._type_edit.textChanged.connect(self._on_sym_changed)
        self._speed_edit.textChanged.connect(self._on_sym_changed)
        self._altitude_edit.textChanged.connect(self._on_sym_changed)
        self._direction_edit.textChanged.connect(self._on_sym_changed)

        # ---- Symbology combos ----
        sym_group = QGroupBox("Symbology (APP-6D)")
        sym_layout = QFormLayout(sym_group)

        self._frame_combo = QComboBox()
        self._frame_combo.addItem("Reality (Solid)", "0")
        self._frame_combo.addItem("Exercise (Dashed)", "1")
        self._frame_combo.addItem("Simulation (Dotted)", "2")
        self._frame_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Context/Frame:", self._frame_combo)

        self._identity_combo = QComboBox()
        for si in StandardIdentity:
            label = STANDARD_IDENTITY_LABELS.get(
                si, si.name.replace("_", " ").title()
            )
            self._identity_combo.addItem(label, si)
        self._identity_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Identity:", self._identity_combo)

        self._symbol_set_combo = QComboBox()
        for ss in SymbolSet:
            label = SYMBOL_SET_NAMES.get(ss.value, ss.name)
            self._symbol_set_combo.addItem(label, ss)
        self._symbol_set_combo.currentIndexChanged.connect(
            self._on_symbol_set_changed
        )
        sym_layout.addRow("Symbol Set:", self._symbol_set_combo)

        self._entity_combo = QComboBox()
        self._entity_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Entity:", self._entity_combo)

        self._mod1_combo = QComboBox()
        self._mod1_combo.addItem("00 - None", "00")  # populated by _refresh_mod_combos
        self._mod1_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Modifier 1:", self._mod1_combo)

        self._mod2_combo = QComboBox()
        self._mod2_combo.addItem("00 - None", "00")  # populated by _refresh_mod_combos
        self._mod2_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Modifier 2:", self._mod2_combo)

        self._echelon_combo = QComboBox()
        for ech in Echelon:
            self._echelon_combo.addItem(
                ech.name.replace("_", " ").title(), ech
            )
        self._echelon_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Echelon:", self._echelon_combo)

        self._hqtf_combo = QComboBox()
        for h in HqTfDummy:
            self._hqtf_combo.addItem(
                h.name.replace("_", " ").title(), h
            )
        self._hqtf_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("HQ/TF/Dummy:", self._hqtf_combo)

        self._status_combo = QComboBox()
        for st in Status:
            self._status_combo.addItem(st.name.replace("_", " ").title(), st)
        self._status_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Status:", self._status_combo)

        # Preview
        preview_row = QHBoxLayout()
        self._preview_label = QLabel("No symbol selected")
        self._preview_label.setFixedSize(_PREVIEW_SIZE, _PREVIEW_SIZE)
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setStyleSheet(
            "QLabel { background: white; border: 1px solid #ccc; }"
        )
        preview_row.addStretch()
        preview_row.addWidget(self._preview_label)
        preview_row.addStretch()
        sym_layout.addRow(preview_row)

        self._sidc_label = QLabel("")
        self._sidc_label.setAlignment(Qt.AlignCenter)
        self._sidc_label.setStyleSheet(
            "font-family: monospace; font-size: 11px; color: #666;"
        )
        sym_layout.addRow(self._sidc_label)

        layout.addWidget(sym_group)
        layout.addWidget(self._mod_group)

        # Initialise modifier combos for the default symbol set
        self._refresh_mod_combos()

        # ---- Temporal ----
        temp_group = QGroupBox("Temporal Validity (optional)")
        temp_layout = QFormLayout(temp_group)

        self._t_start_edit = QDateTimeEdit()
        self._t_start_edit.setCalendarPopup(True)
        self._t_start_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._t_start_edit.setDateTime(
            QDateTime(QDateTime.currentDateTime().date().year(), 1, 1, 0, 0, 0)
        )
        self._t_start_check = self._make_optional_datetime(
            self._t_start_edit, temp_layout, "Start:"
        )

        self._t_end_edit = QDateTimeEdit()
        self._t_end_edit.setCalendarPopup(True)
        self._t_end_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        _now = QDateTime.currentDateTime()
        _end_month = _now.date().month() + 6
        _end_year = _now.date().year() + (_end_month - 1) // 12
        _end_month = (_end_month - 1) % 12 + 1
        self._t_end_edit.setDateTime(
            QDateTime(_end_year, _end_month, _now.date().day(), 23, 59, 59)
        )
        self._t_end_check = self._make_optional_datetime(
            self._t_end_edit, temp_layout, "End:"
        )

        layout.addWidget(temp_group)

        # ---- Buttons ----
        btn_row = QHBoxLayout()

        self._place_btn = QPushButton("Place on Map")
        self._place_btn.setToolTip("Place this symbol on the map")
        self._place_btn.setStyleSheet(
            "QPushButton { font-weight: bold; }"
        )
        self._place_btn.clicked.connect(self._on_place_on_map)
        self._place_btn.setVisible(False)
        btn_row.addWidget(self._place_btn)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setToolTip("Save changes to this symbol")
        self._apply_btn.clicked.connect(self._on_apply)
        self._apply_btn.setVisible(False)
        btn_row.addWidget(self._apply_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setToolTip("Remove this symbol from the map")
        self._delete_btn.setStyleSheet("QPushButton { color: #ffffff; background: #cc3333; }")
        self._delete_btn.clicked.connect(self._on_delete)
        self._delete_btn.setVisible(False)
        btn_row.addWidget(self._delete_btn)

        layout.addLayout(btn_row)

        # ---- Coordinate info ----
        self._coord_label = QLabel("")
        self._coord_label.setStyleSheet(
            "font-size: 10px; color: #666; padding: 2px;"
        )
        layout.addWidget(self._coord_label)

        layout.addStretch()

        outer.addWidget(container)

    @staticmethod
    def _make_optional_datetime(dt_edit, form_layout, label):
        cb = QCheckBox()
        cb.setChecked(False)
        dt_edit.setEnabled(False)
        cb.toggled.connect(dt_edit.setEnabled)
        row = QHBoxLayout()
        row.addWidget(cb)
        row.addWidget(dt_edit, 1)
        form_layout.addRow(label, row)
        return cb

    # ------------------------------------------------------------------
    # Enable / disable all fields
    # ------------------------------------------------------------------

    def _set_editing_enabled(self, enabled: bool) -> None:
        for w in (
            self._designation_edit,
            self._higher_edit,
            self._comment_edit,
            self._quantity_edit,
            self._staff_comments_edit,
            self._additional_info_edit,
            self._eval_rating_edit,
            self._combat_eff_edit,
            self._dtg_edit,
            self._type_edit,
            self._speed_edit,
            self._altitude_edit,
            self._direction_edit,
            self._identity_combo,
            self._symbol_set_combo,
            self._entity_combo,
            self._echelon_combo,
            self._hqtf_combo,
            self._status_combo,
            self._t_start_check,
            self._t_start_edit,
            self._t_end_check,
            self._t_end_edit,
            self._place_btn,
            self._apply_btn,
            self._delete_btn,
        ):
            w.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Populate from MilSymbol
    # ------------------------------------------------------------------

    def _populate_from_symbol(self, sym: MilSymbol) -> None:
        # Block signals to avoid recursive updates during population
        self._block_combos(True)

        self._designation_edit.setText(sym.designation)
        self._higher_edit.setText(sym.higher_formation)
        self._comment_edit.setText(sym.comment)
        self._quantity_edit.setText(getattr(sym, 'quantity', ''))
        self._staff_comments_edit.setText(getattr(sym, 'staff_comments', ''))
        self._additional_info_edit.setText(getattr(sym, 'additional_information', ''))
        self._eval_rating_edit.setText(getattr(sym, 'evaluation_rating', ''))
        self._combat_eff_edit.setText(getattr(sym, 'combat_effectiveness', ''))
        self._dtg_edit.setText(getattr(sym, 'dtg', ''))
        self._type_edit.setText(getattr(sym, 'type_str', ''))
        self._speed_edit.setText(getattr(sym, 'speed', ''))
        self._altitude_edit.setText(getattr(sym, 'altitude_depth', ''))
        
        dr = getattr(sym, 'direction', None)
        self._direction_edit.setText(str(dr) if dr is not None else '')

        # Parse SIDC
        try:
            sidc = SIDCClass.parse(sym.sidc)
        except ValueError:
            sidc = SIDCClass()

        # Identity
        self._select_combo_data(self._identity_combo, sidc.standard_identity)

        # Context/Frame string matching
        for i in range(self._frame_combo.count()):
            if self._frame_combo.itemData(i) == sidc.context.value:
                self._frame_combo.setCurrentIndex(i)
                break

        # Symbol set (must be set before rebuilding modifier combos)
        self._select_combo_data(self._symbol_set_combo, sidc.symbol_set)

        # Rebuild modifier combos for this symbol set and pre-select codes
        self._refresh_mod_combos(
            restore_m1=sidc.modifier1, restore_m2=sidc.modifier2
        )

        # Populate entities then select
        self._refresh_entity_combo()
        entity_code = sidc.entity
        for i in range(self._entity_combo.count()):
            data = self._entity_combo.itemData(i)
            if data and data.entity_code == entity_code:
                self._entity_combo.setCurrentIndex(i)
                break

        # Echelon – compare .value strings
        for i in range(self._echelon_combo.count()):
            if self._echelon_combo.itemData(i).value == sidc.amplifier:
                self._echelon_combo.setCurrentIndex(i)
                break

        # HQ/TF/Dummy
        self._select_combo_data(self._hqtf_combo, sidc.hq_tf_dummy)

        # Status
        self._select_combo_data(self._status_combo, sidc.status)

        # Temporal
        self._t_start_check.setChecked(False)
        self._t_end_check.setChecked(False)
        if sym.temporal.start:
            from qgis.PyQt.QtCore import QDateTime
            self._t_start_check.setChecked(True)
            self._t_start_edit.setDateTime(
                QDateTime.fromString(sym.temporal.start, Qt.ISODate)
            )
        if sym.temporal.end:
            from qgis.PyQt.QtCore import QDateTime
            self._t_end_check.setChecked(True)
            self._t_end_edit.setDateTime(
                QDateTime.fromString(sym.temporal.end, Qt.ISODate)
            )

        # Coordinate info
        self._coord_label.setText(
            f"Location: {sym.longitude:.6f}, {sym.latitude:.6f}"
        )

        self._block_combos(False)
        self._update_preview()

    @staticmethod
    def _select_combo_data(combo: QComboBox, value) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _block_combos(self, block: bool) -> None:
        for w in (
            self._identity_combo,
            self._symbol_set_combo,
            self._entity_combo,
            self._echelon_combo,
            self._hqtf_combo,
            self._status_combo,
        ):
            w.blockSignals(block)

    # ------------------------------------------------------------------
    # Entity combo refresh
    # ------------------------------------------------------------------

    def _on_symbol_set_changed(self, _idx: int = 0) -> None:
        self._refresh_entity_combo()
        self._refresh_mod_combos()
        self._on_sym_changed()

    def _refresh_mod_combos(self, restore_m1: str = "", restore_m2: str = "") -> None:
        """Rebuild modifier combos for the currently selected symbol set.

        If *restore_m1* / *restore_m2* are given those codes are pre-selected
        after the rebuild; otherwise the previously selected codes are kept.
        """
        ss: SymbolSet | None = self._symbol_set_combo.currentData()
        ss_val = ss.value if ss else ""
        entry = _MOD_LABELS.get(ss_val)
        m1_labels: dict[str, str] = entry["m1"] if entry else {"00": "None"}
        m2_labels: dict[str, str] = entry["m2"] if entry else {"00": "None"}

        cur_m1 = restore_m1 or self._mod1_combo.currentData() or "00"
        cur_m2 = restore_m2 or self._mod2_combo.currentData() or "00"

        self._mod1_combo.blockSignals(True)
        self._mod1_combo.clear()
        for code, label in m1_labels.items():
            self._mod1_combo.addItem(f"{code} - {label}", code)
        # If the active code was not in the symbol-set dict, append it anyway
        if cur_m1 not in m1_labels:
            self._mod1_combo.addItem(f"{cur_m1} - (code {cur_m1})", cur_m1)
        for i in range(self._mod1_combo.count()):
            if self._mod1_combo.itemData(i) == cur_m1:
                self._mod1_combo.setCurrentIndex(i)
                break
        self._mod1_combo.blockSignals(False)

        self._mod2_combo.blockSignals(True)
        self._mod2_combo.clear()
        for code, label in m2_labels.items():
            self._mod2_combo.addItem(f"{code} - {label}", code)
        if cur_m2 not in m2_labels:
            self._mod2_combo.addItem(f"{cur_m2} - (code {cur_m2})", cur_m2)
        for i in range(self._mod2_combo.count()):
            if self._mod2_combo.itemData(i) == cur_m2:
                self._mod2_combo.setCurrentIndex(i)
                break
        self._mod2_combo.blockSignals(False)

    def _refresh_entity_combo(self) -> None:
        ss: SymbolSet = self._symbol_set_combo.currentData()
        self._entity_combo.blockSignals(True)
        self._entity_combo.clear()
        self._entity_combo.addItem("(generic)", None)

        entries = entries_by_symbol_set(ss.value)
        for entry in entries:
            self._entity_combo.addItem(entry.name, entry)

        self._entity_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # SIDC builder & preview
    # ------------------------------------------------------------------

    def _build_sidc(self) -> str:
        identity: StandardIdentity = self._identity_combo.currentData()
        ss: SymbolSet = self._symbol_set_combo.currentData()
        echelon: Echelon = self._echelon_combo.currentData()
        hqtf: HqTfDummy = self._hqtf_combo.currentData()
        status: Status = self._status_combo.currentData()

        entry: CatalogEntry | None = self._entity_combo.currentData()
        entity_code = entry.entity_code if entry else "000000"
        
        ctx = self._frame_combo.currentData() or "0"
        m1 = self._mod1_combo.currentData() or "00"
        m2 = self._mod2_combo.currentData() or "00"

        return (
            f"10"
            f"{ctx}"
            f"{identity.value}"
            f"{ss.value}"
            f"{status.value}"
            f"{hqtf.value}"
            f"{echelon.value}"
            f"{entity_code}"
            f"{m1}"
            f"{m2}"
        )

    def _on_sym_changed(self, _idx: int = 0) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        sidc = self._build_sidc()
        self._sidc_label.setText(sidc)
        try:
            val_dir = self._direction_edit.text().strip()
            direction_float = float(val_dir) if val_dir else None
        except ValueError:
            direction_float = None

        try:
            svg = cached_svg(
                sidc_code=sidc,
                designation=self._designation_edit.text().strip(),
                higher_formation=self._higher_edit.text().strip(),
                quantity=self._quantity_edit.text().strip(),
                staff_comments=self._staff_comments_edit.text().strip(),
                additional_information=self._additional_info_edit.text().strip(),
                evaluation_rating=self._eval_rating_edit.text().strip(),
                combat_effectiveness=self._combat_eff_edit.text().strip(),
                dtg=self._dtg_edit.text().strip(),
                type_str=self._type_edit.text().strip(),
                speed=self._speed_edit.text().strip(),
                altitude_depth=self._altitude_edit.text().strip(),
                direction=direction_float
            )
            pm = _svg_to_pixmap(svg, _PREVIEW_SIZE)
            if pm:
                self._preview_label.setPixmap(pm)
            else:
                self._preview_label.setText("?")
        except ValueError:
            self._preview_label.setText("?")

    # ------------------------------------------------------------------
    # Apply changes
    # ------------------------------------------------------------------

    def _on_apply(self) -> None:
        sym = self._symbol
        if sym is None:
            return

        sym.sidc = self._build_sidc()
        sym.designation = self._designation_edit.text().strip()
        sym.higher_formation = self._higher_edit.text().strip()
        sym.comment = self._comment_edit.text().strip()
        sym.quantity = self._quantity_edit.text().strip()
        sym.staff_comments = self._staff_comments_edit.text().strip()
        sym.additional_information = self._additional_info_edit.text().strip()
        sym.evaluation_rating = self._eval_rating_edit.text().strip()
        sym.combat_effectiveness = self._combat_eff_edit.text().strip()
        sym.dtg = self._dtg_edit.text().strip()
        sym.type_str = self._type_edit.text().strip()
        sym.speed = self._speed_edit.text().strip()
        sym.altitude_depth = self._altitude_edit.text().strip()

        try:
            val_dir = self._direction_edit.text().strip()
            sym.direction = float(val_dir) if val_dir else None
        except ValueError:
            sym.direction = None

        # Temporal
        if self._t_start_check.isChecked():
            sym.temporal.start = (
                self._t_start_edit.dateTime().toString(Qt.ISODate)
            )
        else:
            sym.temporal.start = ""
        if self._t_end_check.isChecked():
            sym.temporal.end = (
                self._t_end_edit.dateTime().toString(Qt.ISODate)
            )
        else:
            sym.temporal.end = None

        # If this is an ORBAT unit edit, write back to the unit and signal
        if self._orbat_unit is not None:
            unit = self._orbat_unit
            unit.sidc = sym.sidc
            unit.name = sym.designation or unit.name
            unit.short_name = sym.higher_formation or unit.short_name
            unit.temporal = sym.temporal
            # If the unit also has a live map symbol, update the layer too
            if self._layer_manager is not None:
                self._layer_manager.update_symbol(sym)
                self.symbol_updated.emit(sym.id)
            self._update_preview()
            self.orbat_unit_updated.emit(unit)
            self.setWindowTitle("Symbol Editor")
            LOG.info("ORBAT unit %s updated via editor (SIDC=%s)", unit.name, unit.sidc)
            return

        # Persist to layer (symbol without ORBAT link)
        if self._layer_manager is not None:
            self._layer_manager.update_symbol(sym)

        self._update_preview()
        self.symbol_updated.emit(sym.id)
        LOG.info("Symbol %s updated (SIDC=%s)", sym.id[:8], sym.sidc)

    # ------------------------------------------------------------------
    # Delete symbol
    # ------------------------------------------------------------------

    def _on_delete(self) -> None:
        sym = self._symbol
        if sym is None:
            return

        reply = QMessageBox.question(
            self,
            "Delete Symbol",
            f"Delete symbol '{sym.designation or sym.sidc}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        sym_id = sym.id
        if self._layer_manager is not None:
            self._layer_manager.remove_symbol(sym_id)

        self.clear_editor()
        self.symbol_deleted.emit(sym_id)
        LOG.info("Symbol %s deleted", sym_id[:8])

    # ------------------------------------------------------------------
    # Place on Map (new symbol from editor)
    # ------------------------------------------------------------------

    def _on_place_on_map(self) -> None:
        """Activate the placement map tool with the current editor SIDC."""
        # Refuse if no symbol layers exist
        if self._layer_manager is None or not self._layer_manager.symbol_layers():
            QMessageBox.warning(
                self,
                "No Symbol Layer",
                "Please create a symbol layer first via the Layer Manager "
                "before placing a symbol on the map.",
            )
            return
        sidc = self._build_sidc()
        designation = self._designation_edit.text().strip()
        higher_formation = self._higher_edit.text().strip()

        from .map_tool import SymbolPlacementTool

        canvas = self._iface.mapCanvas()
        self._map_tool = SymbolPlacementTool(
            canvas=canvas,
            sidc=sidc,
            designation=designation,
            higher_formation=higher_formation,
        )
        self._map_tool.symbol_placed.connect(self._on_symbol_placed)
        canvas.setMapTool(self._map_tool)
        LOG.info("Editor placement tool activated for SIDC=%s", sidc)

    def _on_symbol_placed(self, sym: MilSymbol) -> None:
        """Handle the symbol_placed signal from the map tool."""
        # Apply extra data from the editor to the new symbol
        if self._t_start_check.isChecked():
            sym.temporal.start = (
                self._t_start_edit.dateTime().toString(Qt.ISODate)
            )
        if self._t_end_check.isChecked():
            sym.temporal.end = (
                self._t_end_edit.dateTime().toString(Qt.ISODate)
            )
        
        sym.comment = self._comment_edit.text().strip()
        sym.quantity = self._quantity_edit.text().strip()
        sym.staff_comments = self._staff_comments_edit.text().strip()
        sym.additional_information = self._additional_info_edit.text().strip()
        sym.evaluation_rating = self._eval_rating_edit.text().strip()
        sym.combat_effectiveness = self._combat_eff_edit.text().strip()
        sym.dtg = self._dtg_edit.text().strip()
        sym.type_str = self._type_edit.text().strip()
        sym.speed = self._speed_edit.text().strip()
        sym.altitude_depth = self._altitude_edit.text().strip()

        try:
            val_dir = self._direction_edit.text().strip()
            sym.direction = float(val_dir) if val_dir else None
        except ValueError:
            sym.direction = None

        if self._layer_manager is not None:
            self._layer_manager.add_symbol(sym)

        # Keep the new symbol loaded in the editor for further edits
        self._symbol = sym
        self._set_editing_enabled(True)
        self._place_btn.setVisible(False)
        self._delete_btn.setVisible(True)
        self._coord_label.setText(
            f"Location: {sym.longitude:.6f}, {sym.latitude:.6f}"
        )

        self.symbol_placed.emit(sym)
        LOG.info("Symbol placed from editor: %s", sym.id)
