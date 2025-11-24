import logging
from pathlib import Path
from base_notifier import Notifier
from converters.pandapower.ppExporter import PandapowerExporter
from topology import Network
from pandapower.auxiliary import pandapowerNet
import pandapower
import webbrowser
import os
import shutil
import subprocess

class VisualizerNotifier(Notifier):
    """
    Interactive Network Visualization Notifier.
    
    This notifier generates an interactive HTML visualization of the electrical network
    topology as a final post-processing step after export. It provides a graphical
    representation of the network structure, showing:
    
    - Substations and voltage levels
    - Buses and their connections
    - Lines and transformers with electrical parameters
    - Loads and generators
    - Network topology in an interactive, zoomable format
    
    The visualization is generated using PandaPower's plotting capabilities and can be
    automatically opened in a web browser for immediate inspection. This is particularly
    useful for:
    
    - Validating conversion results visually
    - Presenting network topology to stakeholders
    - Debugging topology issues
    - Creating documentation and reports
    - Quality assurance of imported/exported networks
    
    Features:
    - Interactive pan and zoom capabilities
    - Color-coded elements by type and voltage level
    - Hover tooltips showing element properties
    - Automatic browser opening (configurable)
    - Cross-platform support (including WSL environments)
    - Clean, professional HTML output
    
    Required Parameters:
        notifier_file (str): Path where the HTML visualization will be saved
        open_browser (bool): Whether to automatically open in browser (default: True)
    
    Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.
    
    Example:
        python main.py --iFormat ExcelImporter --input_file network.xlsx \
               --oFormat JsonExporter --output_file network.json \
               --nFormat VisualizerNotifier --notifier_file viz.html
    """
    @classmethod
    def name(cls) -> str:
        return "VisualizerNotifier"
    
    def required_parameters(self) -> dict:
        return {
            "notifier_file": None,
            "open_browser": True  # Default to opening in browser
        }

    async def _notify_impl(self, network: Network, path: Path, logger: logging.Logger, params: dict = {}) -> tuple[bool, object]:
        """
        Generate and display interactive HTML visualization of the network.
        
        Converts the network topology to PandaPower format and generates an interactive
        HTML file with graphical representation. Optionally opens the visualization
        in the default web browser.
        
        Args:
            network: The Network topology to visualize
            path: Export path (for reference)
            logger: Logger for tracking visualization process
            params: Parameters including:
                - notifier_file: Output HTML file path
                - open_browser: Whether to open in browser automatically
        
        Returns:
            Tuple of (success: bool, path: Path) indicating completion status
        
        Note:
            The visualization includes automatic handling for WSL environments,
            converting paths appropriately for Windows browser opening.
        """
        pp_exp = PandapowerExporter()
        pp_net:pandapowerNet =  await pp_exp._create_all_elements(network=network, logger=logger)

        notifier_file = params.get("notifier_file")
        open_browser = params.get("open_browser", True)
        
        # Generate the HTML visualization
        pandapower.plotting.to_html(pp_net, filename=notifier_file, show_tables=False)
        logger.info(f"Pandapower visualization saved to: {notifier_file}")
        
        # Open in browser if requested
        if open_browser:
            try:
                # Convert to absolute path for proper browser opening
                abs_path = os.path.abspath(notifier_file)
                
                # Check for WSL environment with explorer.exe available
                if shutil.which("explorer.exe") and shutil.which("wslpath"):
                    # Convert to Windows path
                    result = subprocess.run(['wslpath', '-w', abs_path], capture_output=True, text=True)
                    if result.returncode == 0:
                        win_path = result.stdout.strip()
                        subprocess.run(['explorer.exe', win_path])
                        logger.info(f"Opened visualization in Windows explorer: {win_path}")
                        return (True, path)

                file_url = f"file://{abs_path}"
                webbrowser.open(file_url)
                logger.info(f"Opened visualization in browser: {file_url}")
                
            except Exception as e:
                logger.warning(f"Could not open browser: {e}")

        return (True, path)
