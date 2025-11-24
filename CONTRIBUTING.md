# Contributing to Topology Alchemy

Thank you for your interest in contributing to Topology Alchemy! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Creating a New Importer](#creating-a-new-importer)
- [Creating a New Exporter](#creating-a-new-exporter)
- [Creating a New Notifier](#creating-a-new-notifier)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

This project is part of the OPENTUNITY EU research project and adheres to professional research standards. We expect all contributors to:

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other contributors

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/TopologyAlchemy.git
   cd TopologyAlchemy
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/lucaspons-etra/TopologyAlchemy.git
   ```
4. Create a branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Installation for Development

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## How to Contribute

### Areas Where We Need Help

- **New Format Support**: Implement importers/exporters for additional formats
- **Documentation**: Improve documentation, add examples, write tutorials
- **Testing**: Add unit tests, integration tests, and test data
- **Bug Fixes**: Fix reported issues
- **Performance**: Optimize conversion algorithms
- **Validation**: Add data validation and error checking

## Creating a New Importer

To add support for importing a new format:

### 1. Create the Importer File

Create a new Python file in the appropriate subdirectory:
```
src/converters/<format_name>/<FormatName>Importer.py
```

### 2. Implement the Importer Class

```python
"""
<FormatName> Importer

This module implements the importer for <format description>.

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.
"""

import logging
from base_importer import Importer
from topology import Network

class <FormatName>Importer(Importer):
    """
    Importer for <format name> format.
    
    <Detailed description of the format and what this importer does>
    """
    
    @classmethod
    def name(cls) -> str:
        """Return the unique name for this importer."""
        return "<FormatName>Importer"
    
    def required_parameters(self) -> dict:
        """
        Define required parameters and their default values.
        
        Returns:
            dict: Dictionary mapping parameter names to default values.
                  Use None for required parameters without defaults.
        """
        return {
            "input_file": None,  # Required, no default
            "optional_param": "default_value",  # Optional with default
        }
    
    async def _import_topology_impl(self, logger: logging.Logger, params: dict = {}) -> Network:
        """
        Import topology from <format name> format.
        
        Args:
            logger: Logger instance for logging messages
            params: Dictionary of parameters from command line
            
        Returns:
            Network object containing the imported topology
            
        Raises:
            ValueError: If required parameters are missing or invalid
            IOError: If file cannot be read
        """
        # Extract parameters
        input_file = params.get("input_file")
        
        # Implement your import logic here
        network = Network(id="network_id", name="Network Name")
        
        # ... populate network with data ...
        
        return network
```

### 3. Add __init__.py Entry

Ensure the converter directory has an `__init__.py` file that imports your importer:

```python
from .<FormatName>Importer import <FormatName>Importer

__all__ = ['<FormatName>Importer']
```

### 4. Test Your Importer

```bash
python src/main.py --iFormat <FormatName>Importer --input_file test.dat --oFormat JsonExporter --output_file output.json
```

## Creating a New Exporter

To add support for exporting to a new format:

### 1. Create the Exporter File

Create a new Python file:
```
src/converters/<format_name>/<FormatName>Exporter.py
```

### 2. Implement the Exporter Class

```python
"""
<FormatName> Exporter

This module implements the exporter for <format description>.

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.
"""

import logging
from pathlib import Path
from base_exporter import Exporter
from topology import Network

class <FormatName>Exporter(Exporter):
    """
    Exporter for <format name> format.
    
    <Detailed description of the format and what this exporter does>
    """
    
    @classmethod
    def name(cls) -> str:
        """Return the unique name for this exporter."""
        return "<FormatName>Exporter"
    
    def required_parameters(self) -> dict:
        """
        Define required parameters and their default values.
        
        Returns:
            dict: Dictionary mapping parameter names to default values.
                  Use None for required parameters without defaults.
        """
        return {
            "output_file": None,  # Required, no default
            "optional_param": "default_value",  # Optional with default
        }
    
    async def _export_topology_impl(self, network: Network, logger: logging.Logger, 
                                     params: dict = None) -> dict[str, Path]:
        """
        Export topology to <format name> format.
        
        Args:
            network: Network object to export
            logger: Logger instance for logging messages
            params: Dictionary of parameters from command line
            
        Returns:
            Dictionary mapping network IDs to output file paths
            
        Raises:
            ValueError: If required parameters are missing or invalid
            IOError: If file cannot be written
        """
        output_file = params.get("output_file")
        
        # Implement your export logic here
        result = {}
        
        # Export main network
        # ... write data to file ...
        result[network.id] = Path(output_file)
        
        # Optionally export sub-networks
        for sub_network in network.getElements("subTopologies"):
            sub_output = f"{output_file}_{sub_network.id}"
            # ... write sub-network data ...
            result[sub_network.id] = Path(sub_output)
        
        return result
```

## Creating a New Notifier

Notifiers perform post-processing on exported data:

### 1. Create the Notifier File

```
src/notifiers/<NotifierName>Notifier.py
```

### 2. Implement the Notifier Class

```python
"""
<NotifierName> Notifier

This module implements a notifier for <purpose description>.

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.
"""

import logging
from base_notifier import Notifier
from topology import Network

class <NotifierName>Notifier(Notifier):
    """
    Notifier for <purpose>.
    
    <Detailed description>
    """
    
    @classmethod
    def name(cls) -> str:
        """Return the unique name for this notifier."""
        return "<NotifierName>Notifier"
    
    def required_parameters(self) -> dict:
        """Define required parameters."""
        return {
            "param1": None,
        }
    
    async def _notify_impl(self, network: Network, data, logger: logging.Logger, 
                           params: dict = None) -> tuple[bool, any]:
        """
        Process exported data.
        
        Args:
            network: Network object
            data: Exported data (format depends on exporter)
            logger: Logger instance
            params: Dictionary of parameters
            
        Returns:
            Tuple of (success: bool, processed_data: any)
        """
        # Process data here
        processed_data = data
        
        return True, processed_data
```

## Code Style Guidelines

### Python Style

- Follow PEP 8 conventions
- Use type hints for function parameters and return values
- Maximum line length: 120 characters
- Use docstrings for all modules, classes, and functions
- Use meaningful variable and function names

### Naming Conventions

- **Classes**: PascalCase (e.g., `ExcelImporter`)
- **Functions/Methods**: snake_case (e.g., `import_topology`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_VOLTAGE`)
- **Private methods**: Prefix with underscore (e.g., `_internal_method`)

### Documentation

- Add module-level docstrings explaining the purpose
- Document all public methods with:
  - Description
  - Args section
  - Returns section
  - Raises section (if applicable)
- Include usage examples in docstrings for complex functionality

### Example Docstring Format

```python
def process_topology(network: Network, options: dict) -> bool:
    """
    Process a topology network with given options.
    
    This function validates and transforms the network topology
    according to the specified options.
    
    Args:
        network: Network object to process
        options: Dictionary containing processing options:
            - validate: bool, whether to validate (default True)
            - transform: str, transformation type
            
    Returns:
        True if processing succeeded, False otherwise
        
    Raises:
        ValueError: If network is None or invalid
        ProcessingError: If transformation fails
        
    Example:
        >>> network = Network("test", "Test Network")
        >>> options = {"validate": True}
        >>> success = process_topology(network, options)
    """
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_importers.py

# Run with coverage
python -m pytest --cov=src tests/
```

### Writing Tests

Create test files in the `tests/` directory:

```python
import unittest
from src.converters.excel.ExcelImporter import ExcelImporter

class TestExcelImporter(unittest.TestCase):
    def setUp(self):
        self.importer = ExcelImporter()
    
    def test_import_basic_network(self):
        # Test implementation
        pass
    
    def test_import_with_lv(self):
        # Test implementation
        pass
```

## Documentation

### Updating Documentation

- Update README.md if adding new features
- Add docstrings to all new code
- Update CHANGELOG.md with your changes
- Add examples for new importers/exporters

## Pull Request Process

1. **Update your branch** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/master
   ```

2. **Commit your changes** with clear, descriptive messages:
   ```bash
   git commit -m "Add ExcelImporter for tabular topology data"
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference to any related issues
   - Screenshots/examples if applicable

5. **Code Review**: Address any feedback from reviewers

6. **Merge**: Once approved, your PR will be merged

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Commit messages are clear and descriptive

## Reporting Bugs

### Before Reporting

- Check if the bug has already been reported in Issues
- Verify you're using the latest version
- Collect relevant information (error messages, log files, etc.)

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. With input file '...'
3. See error

**Expected Behavior**
What you expected to happen

**Actual Behavior**
What actually happened

**Environment**
- OS: [e.g., Windows 10, Ubuntu 20.04]
- Python version: [e.g., 3.8.5]
- Topology Alchemy version: [e.g., 1.0.0]

**Additional Context**
Any other relevant information, log files, etc.
```

## Feature Requests

We welcome feature requests! Please:

1. Check if the feature has already been requested
2. Provide a clear use case
3. Explain the expected behavior
4. Consider if you could implement it yourself

### Feature Request Template

```markdown
**Feature Description**
Clear description of the proposed feature

**Use Case**
Why is this feature needed? What problem does it solve?

**Proposed Solution**
How you envision this feature working

**Alternatives Considered**
Other approaches you've considered

**Additional Context**
Any other relevant information
```

## Questions?

If you have questions about contributing:

- Check the documentation
- Open a discussion on GitHub
- Contact the maintainers

## License

By contributing to Topology Alchemy, you agree that your contributions will be licensed under the Apache License 2.0.

---

**Thank you for contributing to Topology Alchemy and the OPENTUNITY project!**
