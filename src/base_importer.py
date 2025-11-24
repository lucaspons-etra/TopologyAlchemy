"""
Base Importer Abstract Class

This module defines the abstract base class for all topology importers in the
Topology Alchemy framework. Importers are responsible for reading topology data
from various source formats and converting them into the internal topology data model.

The plugin system uses Python metaclasses to automatically register all importer
subclasses, making them available for dynamic loading by the Alchemist engine.

To create a new importer:
1. Inherit from the Importer base class
2. Implement the abstract methods: name(), required_parameters(), _import_topology_impl()
3. The importer will automatically register itself

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.

Classes:
    Importer: Abstract base class for all topology importers
"""

from abc import ABC, abstractmethod
import logging
from topology import  Network

class Importer(ABC):
    importers: dict = {}
    def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            Importer.importers[cls.name()] = cls

    async def import_topology(self, logger: logging.Logger, params: dict = None) -> Network:
        if params is None:
            params = {}

        if not self._check_required_parameters(logger, params):
            return None

        return await self._import_topology_impl(logger, params)
    
    def _check_required_parameters(self, logger, params):
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
    async def _import_topology_impl(self, logger: logging.Logger, params: dict = {}) -> Network:
        pass

    @abstractmethod
    def required_parameters(self) -> dict:
        return {}
    
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        pass

    @classmethod
    def get_importer(cls, name: str):
        """Get an instance of the importer class by name.
        
        Args:
            name: The name of the importer to retrieve
            
        Returns:
            An instance of the importer class, or None if not found
        """
        importer_class = cls.importers.get(name, None)
        if importer_class is not None:
            return importer_class()
        return None
