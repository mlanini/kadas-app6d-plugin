# KADAS APP-6(D) Military Symbols Plugin

[![KADAS](https://img.shields.io/badge/KADAS-2.x-blue.svg)](https://kadas.org)
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.8-orange.svg)](kadas_app6d/metadata.txt)

A **KADAS Albireo 2** plugin providing a complete NATO **APP-6(D)** military symbol library,
an ORBAT (Order of Battle) manager, and temporal layer filtering.

> **Compatibility:** KADAS Albireo 2 (QGIS 3.x engine). Tested on KADAS 2.2+.

---

## Features

- **APP-6(D) Symbol Catalog** — browse and search all NATO symbols by name or SIDC;
  drag-and-drop onto the map canvas
- **Full 20-character SIDC** — complete APP-6(D) standard encoding
- **Built-in SVG/PNG rendering server** — local HTTP server renders symbols on demand
  via [milsymbol.js](https://github.com/spatialillusions/milsymbol)
- **Symbol Editor** — create and edit symbols with text modifiers (designation, higher
  formation, DTG, equipment, …)
- **ORBAT Manager** — hierarchical Order of Battle editor; import/export `.orbat.json`
- **Temporal filtering** — integrates with the QGIS Temporal Controller to show/hide
  symbols by their DTG extent
- **Layer Manager** — manage named symbol layers; export to JSON or KMZ

## Screenshots

_Coming soon._

## Installation

### From ZIP (recommended)

1. Download the latest `kadas_app6d-<version>.zip` from
   [Releases](https://github.com/mlanini/kadas-app6d-plugin/releases)
2. Open KADAS → **Plugins → Manage and Install Plugins → Install from ZIP**
3. Select the downloaded ZIP and click **Install Plugin**

### From source

```bash
git clone https://github.com/mlanini/kadas-app6d-plugin.git
cd kadas-app6d-plugin
python package_plugin.py           # → dist/kadas_app6d-0.1.8.zip
```

Then install the generated ZIP via the Plugin Manager.

Or copy / symlink the `kadas_app6d/` folder directly into your KADAS plugin directory:

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\KADAS\KADAS2\profiles\default\python\plugins\` |
| Linux | `~/.local/share/KADAS/KADAS2/profiles/default/python\plugins\` |

## Usage

After enabling the plugin a new **APP-6(D)** toolbar appears.

| Button | Action |
|---|---|
| Symbol Catalog | Open/close the symbol browser dock |
| Symbol Editor | Create or edit a symbol (SIDC, text modifiers, temporal extent) |
| ORBAT Manager | Manage the Order of Battle hierarchy |
| Layer Manager | Manage named symbol layers; export to JSON / KMZ |
| Settings | Plugin preferences |

### Placing symbols

- **Drag** a symbol from the Catalog onto the map canvas
- **Click** a symbol in the Catalog to sync it in the Symbol Editor
- **Double-click** an existing symbol on the canvas to open it in the editor
- **Right-click** a canvas symbol for context menu (edit / move / delete)

### Temporal filtering

Set start/end DTG in the Symbol Editor, then enable the
**Temporal Controller** (`View → Panels → Temporal Controller`).
The plugin filters visible symbols automatically.

## Development

### Requirements

- Python 3.9+
- KADAS Albireo 2 (QGIS 3.16+ engine)
- No additional Python packages required at runtime

### Running the lint checker

```bash
python lint_check.py
```

### Building the release ZIP

```bash
python package_plugin.py                   # → dist/kadas_app6d-<version>.zip
python package_plugin.py --bump 0.2.0      # bump version + build
python package_plugin.py --dry-run         # list files without creating ZIP
```

## Contributing

Contributions are welcome! Please open an issue or a pull request on
[GitHub](https://github.com/mlanini/kadas-app6d-plugin).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Acknowledgements

This plugin builds on the shoulders of:

- **[qgis-app6d-plugin](https://github.com/intelligeo/qgis-app6d-plugin)** by
  [INTELLIGEO.ch](https://intelligeo.ch/) — the original QGIS APP-6(D) plugin that
  inspired this KADAS port.
- **[milsymbol](https://github.com/spatialillusions/milsymbol)** by
  [Spatial Illusions](https://www.spatialillusions.com/) — the JavaScript military
  symbol rendering engine powering SVG/PNG generation.

## License

[GNU General Public License v2.0 or later](LICENSE)

© 2026 Michael Lanini
