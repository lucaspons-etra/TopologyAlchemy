from abc import ABC, abstractmethod
import logging
from pathlib import Path
from topology import  Network

class Notifier(ABC):
    notifiers: dict = {}
    def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            Notifier.notifiers[cls.name()] = cls

    async def notify(self, network:Network, data, logger: logging.Logger, params: dict = None) -> (bool, object):
        if params is None:
            params = {}

        if not self._check_required_parameters(logger, params):
            return False, None

        return await self._notify_impl(network, data, logger, params)
    
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
    async def _notify_impl(self, network: Network, path: Path, logger: logging.Logger, params: dict = {}) -> (bool,object):
        pass

    @abstractmethod
    def required_parameters(self) -> dict:
        return {}
    
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        pass

    @classmethod
    def get_notifier(cls, name: str):
        """Get an instance of the notifier class by name.

        Args:
            name: The name of the notifier to retrieve

        Returns:
            An instance of the notifier class, or None if not found
        """
        notifier_class = cls.notifiers.get(name, None)
        if notifier_class is not None:
            return notifier_class()
        return None