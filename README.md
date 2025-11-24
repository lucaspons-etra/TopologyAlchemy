# Topology Alchemy

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![EU Project](https://img.shields.io/badge/EU%20Project-OPENTUNITY-green.svg)](https://opentunity.eu)

**Topology Alchemy** is a powerful and flexible toolkit for converting, manipulating, and exchanging electrical grid topology data between multiple formats. Developed as part of the EU Horizon 2020 **OPENTUNITY** research project, this tool facilitates interoperability between different power system analysis tools and data sources.

## About OPENTUNITY

This project is part of the [OPENTUNITY](https://opentunity.eu) (OPtimisation of Emerging, New and Existing grid Technologies to Unlock the potential of the smartgrid, flexibilitY and storage) research project, funded by the European Union's Horizon 2020 research and innovation programme. OPENTUNITY aims to accelerate the energy transition by optimizing grid technologies and enabling flexibility through innovative digital tools.

## Key Features

- **Multi-Format Support**: Convert between Excel, PandaPower, PowSyBl, CGMES, CIM, JSON, MongoDB, and more
- **Flexible Architecture**: Plugin-based system for easy extension with new importers and exporters
- **Smart Topology Processing**: Handles both Medium Voltage (MV) and Low Voltage (LV) networks
- **Data Validation**: Built-in validation and error checking during conversion
- **Notification System**: Extensible notification framework for post-processing
- **Rich Data Model**: Comprehensive representation of electrical grid components (buses, lines, transformers, loads, generators, switches, etc.)
- **Command-Line Interface**: Easy-to-use CLI with extensive parameter support
- **Logging & Debugging**: Colored logging with configurable verbosity levels

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Interactive Console](#interactive-console-recommended-for-beginners)
  - [Command-Line Interface](#command-line-interface)
- [Supported Formats](#supported-formats)
- [Usage](#usage)
- [Interactive Console Features](#interactive-console-features)
- [Architecture](#architecture)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install from Source

```bash
# Clone the repository
git clone https://github.com/lucaspons-etra/TopologyAlchemy.git
cd TopologyAlchemy

# Install dependencies
pip install -r requirements.txt

# Optional: Install in development mode
pip install -e .
```

### Dependencies

Main dependencies include:
- `pandapower` - Power system analysis
- `pypowsybl` - PowSyBl Python bindings
- `openpyxl` - Excel file handling
- `networkx` - Graph algorithms
- `rdflib` - RDF/XML processing for CIM
- `coloredlogs` - Enhanced logging
- `marshmallow` - Object serialization

See `requirements.txt` for the complete list.

## Quick Start

### Interactive Console (Recommended for Beginners)

The easiest way to use Topology Alchemy is through the interactive console application:

```bash
python src/console_app.py
```

The console will guide you step-by-step through:
1. Selecting an input format (importer)
2. Configuring import parameters with intelligent file selection
3. Selecting an output format (exporter)
4. Configuring export parameters
5. Optionally selecting post-processing notifiers

Features:
- Interactive file browser for easy file selection
- Smart parameter type detection and validation
- Colored output for better readability
- Confirmation before execution
- Progress indicators and detailed error messages

### Command-Line Interface

For automation and scripting, use the CLI:

#### Basic Conversion

Convert an Excel topology to PandaPower format:

```bash
python src/main.py --iFormat ExcelImporter --input_file data/topology.xlsx --oFormat PandapowerExporter --output_file results/topology.json --network_id my_network
```

#### With Low Voltage Processing

Process both MV and LV networks:

```bash
python src/main.py --iFormat ExcelImporter --input_file data/topology.xlsx --process_lv true --oFormat PandapowerExporter --output_file results/topology.json --network_id my_network
```

#### Advanced Usage with Notifications

Export to JSON and visualize with Cytoscape:

```bash
python src/main.py --iFormat ExcelImporter --input_file data/topology.xlsx --oFormat JsonExporter --output_file results/topology.json --nFormat CytoscapeJsExporter --network_id my_network
```

## Supported Formats

### Importers

| Format | Class Name | Description |
|--------|-----------|-------------|
| **Excel** | `ExcelImporter` | Tabular format with predefined sheet structure for networks, buses, lines, transformers, etc. |
| **PandaPower** | `PandapowerImporter` | Native PandaPower JSON format |
| **CGMES** | `CGMESImporter` | Common Grid Model Exchange Standard (IEC 61970-552) |
| **CIM** | `CIMImporter` | Common Information Model (IEC 61970) |
| **IEEE** | `IEEEImporter` | IEEE standard formats |
| **PowSyBl** | `PowsyblImporter` | PowSyBl XIIDM format |
| **MongoDB** | `MongodbImporter` | MongoDB database import |
| **Smart Meters** | `SmartMeterDataImporter` | Smart meter data integration |

### Exporters

| Format | Class Name | Description |
|--------|-----------|-------------|
| **PandaPower** | `PandapowerExporter` | Export to PandaPower JSON format |
| **PowSyBl** | `PowsyblExporter` | Export to PowSyBl XIIDM format |
| **JSON** | `JsonExporter` | Generic JSON export |
| **MongoDB** | `MongoExporter` | Export to MongoDB database |
| **CGMES** | `CGMESExporter` | Export to CGMES format |
| **CIM** | `CIMExporter` | Export to CIM RDF/XML |
| **Cytoscape** | `CytoscapeExporter` | Export for Cytoscape visualization |
| **Cytoscape.js** | `CytoscapeJsExporter` | Web-based visualization with Cytoscape.js |

### Notifiers

Notifiers perform post-processing on exported data:

- **CytoscapeJsExporter**: Generate interactive web visualizations
- **VisualizerNotifier**: Custom visualization pipelines
- **PandapowerVisualizerNotifier**: PandaPower-specific visualizations
- **ApiNotifier**: Send results to REST APIs
- **JsonpathNgNotifier**: JSONPath-based data transformation

## Usage

### Command-Line Interface

```bash
python src/main.py [OPTIONS]
```

### Required Parameters

- `--iFormat`: Input format (e.g., `ExcelImporter`, `PandapowerImporter`)
- `--oFormat`: Output format (e.g., `PandapowerExporter`, `JsonExporter`)

### Common Optional Parameters

- `--nFormat`: Notifier format(s) - can be specified multiple times
- `--logLevel`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `--input_file` / `--input`: Input file path
- `--output_file` / `--output`: Output file path
- `--network_id` / `--id`: Network identifier
- `--system`: System name/identifier
- `--process_lv` / `--processLV`: Process Low Voltage networks (boolean)
- `--prefix` / `--preffix`: Prefix for element identifiers

### Format-Specific Parameters

Each importer and exporter may require additional parameters. Use the plugin's documentation or check the source code for details.

## Interactive Console Features

The **Interactive Console** (`console_app.py`) provides a user-friendly alternative to the command-line interface, perfect for users who are new to the tool or prefer guided workflows.

### Key Features

**Guided Step-by-Step Workflow**
- Clear 5-step process: Input Format → Configure Import → Output Format → Configure Export → Optional Post-Processing
- Progress indicators show your current step
- Cancel anytime with Ctrl+C

**Intelligent File Selection**
- Automatically scans project directories (`tests/data/`, `examples/data/`, etc.)
- Interactive file browser with numbered selections
- Filters files by extension when applicable
- Highlights default values
- Custom path entry option

**Smart Parameter Handling**
- Automatic type detection (strings, numbers, booleans, JSON objects)
- Boolean shortcuts: accepts `y/n`, `yes/no`, `true/false`
- Numeric parsing for integers and floats
- JSON parsing for complex data structures (lists, dictionaries)
- Required parameter validation

**Enhanced User Experience**
- Colored output for better readability (cross-platform support)
- Clear error messages with suggestions
- Configuration summary before execution
- Confirmation prompt to prevent accidental execution
- Output file path display upon completion

**Professional Interface**
- ASCII art banner with project branding
- Organized menu system with sorted options
- Keyboard shortcuts for quick navigation
- Graceful handling of user cancellation

### Example Console Session

```text
╔══════════════════════════════════════════════════════════════════════════════════════╗
║  _______                _                              _      _                     ║
║ |__   __|              | |                       /\   | |    | |                    ║
║    | | ___  _ __   ___ | | ___   __ _ _   _     /  \  | | ___| |__   ___ _ __ ___  ║
║    | |/ _ \| '_ \ / _ \| |/ _ \ / _` | | | |   / /\ \ | |/ __| '_ \ / _ \ '_ ` _ \ ║
║    | | (_) | |_) | (_) | | (_) | (_| | |_| |  / ____ \| | (__| | | |  __/ | | | | |║
║    |_|\___/| .__/ \___/|_|\___/ \__, |\__, | /_/    \_\_|\___|_| |_|\___|_| |_| |_|║
║            | |                   __/ | __/ |                                        ║
║            |_|                  |___/ |___/                                         ║
║  Interactive Console - OPENTUNITY EU Project                                       ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

Step 1/5: Select Input Format
Select input format (importer):
  1) CIMImporter
  2) ExcelImporter
  3) IEEEImporter
  4) MongodbImporter
  q) Quit
Select number: 2

Step 2/5: Configure Importer
Select file for parameter 'input_file':
  1) tests/data/sample_network.xlsx
  2) tests/data/another_topology.xlsx
  0) Enter custom path
  [Enter]) Use default: tests/data/sample_network.xlsx
Select: 1
Selected: tests/data/sample_network.xlsx

Step 3/5: Select Output Format
Select output format (exporter):
  1) JsonExporter
  2) PandapowerExporter
  ...

Configuration Summary
================================================================================
Importer: ExcelImporter
  Parameters:
    input_file: tests/data/sample_network.xlsx
    network_id: my_network

Exporter: PandapowerExporter
  Parameters:
    output_file: output/network.json

Notifier: None
Log Level: INFO
================================================================================

Execute Alchemist process now? (y/N): y

Starting Topology Alchemy process...
[Conversion logs...]

Process completed successfully!
Output saved to: output/network.json
```

### Usage Tips

1. **First-time users**: Start with the interactive console to understand the workflow
2. **Frequent operations**: Create shell scripts with the CLI for repeatability
3. **File selection**: Use relative paths from project root for portability
4. **Parameter validation**: The console will warn you about missing required parameters
5. **Logging**: Set log level to DEBUG for troubleshooting conversion issues

## Architecture

### Core Components

```
TopologyAlchemy/
├── src/
│   ├── main.py              # CLI entry point
│   ├── alchemist.py         # Main orchestration engine
│   ├── topology.py          # Data model (Network, Bus, Line, etc.)
│   ├── base_importer.py     # Abstract importer base class
│   ├── base_exporter.py     # Abstract exporter base class
│   ├── base_notifier.py     # Abstract notifier base class
│   ├── Utils.py             # Utility functions
│   └── converters/          # Format-specific implementations
│       ├── excel/
│       ├── pandapower/
│       ├── json/
│       ├── mongodb/
│       ├── cytoscape/
│       └── others/
└── notifiers/               # Post-processing plugins
```

### Data Model

The topology data model includes:

- **Network**: Top-level container with optional sub-topologies
- **Substation**: Physical location with buses and equipment
- **VoltageLevel**: Voltage-specific grouping
- **Bus**: Connection point for equipment
- **Line**: Transmission/distribution line with electrical parameters
- **Transformer**: Two-winding and three-winding transformers
- **Switch**: Switching equipment
- **Load**: Consumption point
- **Generator**: Generation unit
- **UsagePoint**: Consumer/prosumer connection point
- **Meter**: Measurement device

### Plugin System

Topology Alchemy uses a plugin-based architecture:

1. **Importers** inherit from `Importer` base class
2. **Exporters** inherit from `Exporter` base class
3. **Notifiers** inherit from `Notifier` base class
4. Plugins auto-register via Python metaclasses
5. New plugins can be added by creating subclasses in the appropriate directory

## Examples

### Example 1: Excel to PandaPower

```bash
python src/main.py \
  --iFormat ExcelImporter \
  --input_file data/network.xlsx \
  --oFormat PandapowerExporter \
  --output_file results/network.json \
  --network_id test_network \
  --system DSO_A
```

### Example 2: PandaPower to PowSyBl with LV Processing

```bash
python src/main.py \
  --iFormat PandapowerImporter \
  --input_file data/pandapower.json \
  --oFormat PowsyblExporter \
  --output_file results/network.xiidm \
  --network_id network_1 \
  --process_lv true
```

### Example 3: Excel to MongoDB with Visualization

```bash
python src/main.py \
  --iFormat ExcelImporter \
  --input_file data/topology.xlsx \
  --oFormat MongoExporter \
  --output_file results/topology.json \
  --nFormat CytoscapeJsExporter \
  --network_id feeder_42 \
  --system Utility_X \
  --process_lv true
```

### Example 4: CGMES to JSON

```bash
python src/main.py \
  --iFormat CGMESImporter \
  --input_file data/cgmes_model.xml \
  --oFormat JsonExporter \
  --output_file results/network.json \
  --network_id cgmes_network
```

## Contributing

We welcome contributions from the community! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Reporting bugs
- Suggesting features
- Creating new importers/exporters
- Submitting pull requests
- Code style and standards

### Adding a New Importer

1. Create a new Python file in `src/converters/<format>/`
2. Inherit from `Importer` base class
3. Implement required methods: `name()`, `required_parameters()`, `_import_topology_impl()`
4. The importer will auto-register

### Adding a New Exporter

1. Create a new Python file in `src/converters/<format>/`
2. Inherit from `Exporter` base class
3. Implement required methods: `name()`, `required_parameters()`, `_export_topology_impl()`
4. The exporter will auto-register

## License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement No. [Project Number].

**OPENTUNITY Consortium Partners:**
- [List key partners here]

## Contact

- **Project Website**: [https://opentunity.eu](https://opentunity.eu)
- **Repository**: [https://github.com/lucaspons-etra/TopologyAlchemy](https://github.com/lucaspons-etra/TopologyAlchemy)
- **Issues**: [https://github.com/lucaspons-etra/TopologyAlchemy/issues](https://github.com/lucaspons-etra/TopologyAlchemy/issues)

## Documentation

For more detailed documentation, please visit the [Wiki](https://github.com/lucaspons-etra/TopologyAlchemy/wiki) or check the docstrings in the source code.

## Version History

See [CHANGELOG.md](CHANGELOG.md) for a detailed version history.

---

**Made with love by the OPENTUNITY Team**
