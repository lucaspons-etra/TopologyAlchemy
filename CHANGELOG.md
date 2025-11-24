# Changelog

All notable changes to Topology Alchemy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-11-24

### Added
- Initial public release as part of the OPENTUNITY EU Project
- Comprehensive README with project overview and documentation
- Professional project structure and documentation
- CONTRIBUTING.md with detailed contribution guidelines
- setup.py for pip package installation
- .gitignore for Python projects
- Comprehensive module-level docstrings for all core modules

### Core Features
- **Multi-Format Support**: Import and export between Excel, PandaPower, PowSyBl, CGMES, CIM, JSON, MongoDB
- **Plugin Architecture**: Extensible importer/exporter/notifier system
- **Data Model**: Rich topology representation supporting MV and LV networks
- **CLI Interface**: Flexible command-line tool with extensive parameter support
- **Logging**: Colored logging with configurable verbosity levels
- **Validation**: Built-in data validation and error checking

### Importers
- ExcelImporter: Tabular format with predefined sheet structure
- PandapowerImporter: Native PandaPower JSON format
- CGMESImporter: Common Grid Model Exchange Standard (IEC 61970-552)
- CIMImporter: Common Information Model (IEC 61970)
- IEEEImporter: IEEE standard formats
- PowsyblImporter: PowSyBl XIIDM format
- MongodbImporter: MongoDB database import
- SmartMeterDataImporter: Smart meter data integration

### Exporters
- PandapowerExporter: Export to PandaPower JSON format
- PowsyblExporter: Export to PowSyBl XIIDM format
- JsonExporter: Generic JSON export
- MongoExporter: Export to MongoDB database
- CGMESExporter: Export to CGMES format
- CIMExporter: Export to CIM RDF/XML
- CytoscapeExporter: Export for Cytoscape visualization
- CytoscapeJsExporter: Web-based visualization with Cytoscape.js

### Notifiers
- CytoscapeJsExporter: Generate interactive web visualizations
- VisualizerNotifier: Custom visualization pipelines
- PandapowerVisualizerNotifier: PandaPower-specific visualizations
- ApiNotifier: Send results to REST APIs
- JsonpathNgNotifier: JSONPath-based data transformation

### Documentation
- Comprehensive README with usage examples
- Contributing guidelines for developers
- Apache 2.0 License
- Module and class docstrings throughout codebase

## [Unreleased]

### Planned
- Additional test coverage
- Performance optimizations
- More format converters
- Enhanced validation rules
- API documentation
- Tutorial videos and examples

---

## Version History Notes

### Version Numbering
- **Major version** (X.0.0): Incompatible API changes
- **Minor version** (0.X.0): Backward-compatible functionality additions
- **Patch version** (0.0.X): Backward-compatible bug fixes

### Categories
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes

---

**Project**: Topology Alchemy
**Organization**: OPENTUNITY Consortium
**License**: Apache License 2.0
**Website**: https://opentunity.eu
