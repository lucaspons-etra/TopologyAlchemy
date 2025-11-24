"""
Base Exporter Abstract Class

This module defines the abstract base class for all topology exporters in the
Topology Alchemy framework. Exporters are responsible for converting the internal
topology data model into various output formats and writing them to files or databases.

The plugin system uses Python metaclasses to automatically register all exporter
subclasses, making them available for dynamic loading by the Alchemist engine.

Exporters return a dictionary mapping network IDs to output file paths, supporting
the export of multiple sub-networks to separate files.

To create a new exporter:
1. Inherit from the Exporter base class
2. Implement the abstract methods: name(), required_parameters(), _export_topology_impl()
3. The exporter will automatically register itself

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.

Classes:
    Exporter: Abstract base class for all topology exporters
"""

from abc import ABC, abstractmethod
import logging
import warnings
from pathlib import Path

from topology import  Network

# Suppress openpyxl data validation warnings
warnings.filterwarnings("ignore", message="Data Validation extension is not supported and will be removed", category=UserWarning, module="openpyxl.worksheet._reader")

class Exporter(ABC):
    exporters: dict = {}
    def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            Exporter.exporters[cls.name()] = cls

    async def export_topology(self, network: Network, logger: logging.Logger, params: dict = None) -> tuple[bool, dict[str, Path]]:
        if params is None:
            params = {}

        if not self._check_required_parameters(logger, params):
            return False, {}

        try:
            return (True, await self._export_topology_impl(network, logger, params))
        except Exception as e:
            logger.error(f"Error exporting topology: {e}")
            return False, {}

    def _check_required_parameters(self, logger, params)->bool:
        """Handle missing parameters by setting defaults or raising errors."""
        fail = False
        for key, default_value in self.required_parameters().items():
            if key not in params:
                if default_value is None:
                    logger.error(f" - {key} (no default value)")
                    fail = True
                else:
                    params[key] = default_value
        if fail:
            raise ValueError("Missing required parameters.")
        return True 
    
    @abstractmethod
    async def _export_topology_impl(self, network: Network, logger: logging.Logger, params: dict = None) -> dict[str, Path]:
        pass

    @abstractmethod
    def required_parameters(self) -> dict:
        pass
    
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        pass

    @classmethod
    def get_exporter(cls, name: str):
        """Get an instance of the importer class by name.
        
        Args:
            name: The name of the importer to retrieve
            
        Returns:
            An instance of the importer class, or None if not found
        """
        exporter_class = cls.exporters.get(name, None)
        if exporter_class is not None:
            return exporter_class()
        return None