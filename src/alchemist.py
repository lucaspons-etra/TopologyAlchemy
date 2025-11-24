"""
Alchemist - Topology Conversion Orchestration Engine

This module provides the main orchestration engine for the Topology Alchemy framework.
The Alchemist class coordinates the entire topology conversion pipeline:

1. Import topology data from source format (using Importer plugins)
2. Transform/validate the internal topology representation
3. Export topology data to target format (using Exporter plugins)
4. Post-process exported data (using optional Notifier plugins)

The Alchemist supports asynchronous operations and provides comprehensive logging
throughout the conversion process. It handles multiple sub-networks and manages
the flow of data between different format handlers.

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.

Classes:
    Alchemist: Main orchestration engine for topology conversions

Functions:
    get_logger: Create a well-configured colored logger instance
"""

import json
import coloredlogs
from base_importer import Importer
from base_exporter import Exporter
from base_notifier import Notifier
from topology import Network
from pathlib import Path
import logging
from typing import List

def get_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """Create a well-configured colored logger.
    
    Args:
        name: Logger name
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    
    Returns:
        Configured logger with colored output
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Set logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Install coloredlogs with custom formatting
    coloredlogs.install(
        level=numeric_level,
        logger=logger,
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level_styles={
            'debug': {'color': 'cyan'},
            'info': {'color': 'green'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red'},
            'critical': {'color': 'red', 'bold': True}
        },
        field_styles={
            'asctime': {'color': 'blue'},
            'name': {'color': 'magenta'},
            'levelname': {'bold': True}
        }
    )
    
    logger.debug(f"Logger '{name}' initialized with level {level}")
    return logger

class Alchemist():
    def __init__(self, log_level: str = 'INFO'):
        """Initialize Alchemist with a properly configured logger.
        
        Args:
            log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        self.logger = get_logger('Alchemist', log_level)
        self.logger.info("Alchemist initialized successfully")

    async def process(self, base_importer: Importer, base_exporter: Exporter, base_notifiers: List[Notifier] | None ,
                params: dict) -> bool:
        try:
            cloned_input_params = params.copy()
            cloned_output_params = params.copy()
            cloned_notifier_params = params.copy()
            # Import topology
            self.logger.info(f"Initializing importer {base_importer.name()}...")
            topology: Network = await base_importer.import_topology(logger=self.logger, params=cloned_input_params)

            # Export topology
            self.logger.info(f"Initializing exporter {base_exporter.name()}...")
            # Export topology: exporters now return (True, Path) consistently
            (ret, exported_path_dict) = await base_exporter.export_topology(topology, logger=self.logger, params=cloned_output_params)

            if not ret:
                self.logger.error(f"Exporter {base_exporter.name()} failed.")
                return False

            for network_id, exported_path in exported_path_dict.items():
                self.logger.info(f"Processing exported file for network ID '{network_id}': {exported_path}")
                data = ""
                try:
                    exported_path = Path(exported_path)
                    # Read the file content (synchronously) since exporters write to disk
                    with exported_path.open("r", encoding="utf-8") as f:
                        data = f.read()
                except Exception as e:
                    self.logger.error(f"Error reading exported file {exported_path}: {e}")
                    return False

                index_params = 0
                try:
                    data = json.loads(data)
                    orig_data = data.copy()
                except json.JSONDecodeError:
                    orig_data = data
                notifier_params = json.loads(params.get("notifier_params","[]"))
                if base_notifiers is not None:
                    for notifier in base_notifiers:
                        self.logger.info(f"Initializing notifier {notifier.name()}...")
                        net = topology if topology.id == network_id else topology.getSubTopology(network_id)

                        ret,data = await notifier.notify(net, data, logger=self.logger, params={**(notifier_params[index_params] if index_params < len(notifier_params) else {}), "orig_path": exported_path, "orig_data": orig_data})
                        if not ret:
                            self.logger.error(f"Notifier {notifier.name()} failed.")
                            return False
                        index_params += 1

            self.logger.info("Alchemist process completed successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Alchemist process failed: {e}")
            import traceback
            traceback.print_exc()
            return False    
