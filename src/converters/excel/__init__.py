"""Excel converter package.

This package contains importers and exporters for Excel-based power system data formats.
"""

from .ExcelImporter import ExcelImporter

# Conservative approach - only expose when dependencies are available
__all__ = ['ExcelImporter']