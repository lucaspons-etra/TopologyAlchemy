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

class PandapowerVisualizerNotifier(Notifier):
    """
    PandaPower-based Interactive Network Visualization Notifier.
    
    Specialized visualizer that creates interactive HTML representations of electrical
    networks using PandaPower's advanced plotting capabilities. This notifier serves as
    the final step in the conversion pipeline, providing immediate visual feedback of
    the exported network structure.
    
    This notifier is optimized for power system networks and leverages PandaPower's
    native visualization features to provide:
    
    Visualization Features:
    - Single-line diagram representation of the power network
    - Color-coded elements (buses, lines, transformers, loads, generators)
    - Interactive zoom and pan for detailed inspection
    - Voltage level differentiation through color schemes
    - Load and generation indicators
    - Line impedance and capacity visualization
    - Geographic or schematic layout options
    
    Use Cases:
    - Post-conversion validation: Verify that topology was correctly exported
    - Network analysis preparation: Quick visual check before running load flow
    - Documentation: Generate visual reports for network documentation
    - Debugging: Identify missing connections or misplaced elements
    - Stakeholder presentations: Create clear, professional network diagrams
    - Educational purposes: Visualize example networks for teaching
    
    Technical Details:
    - Converts Network topology to PandaPower format internally
    - Generates self-contained HTML file (no external dependencies)
    - Automatic browser launching with cross-platform support
    - WSL environment detection and proper Windows path handling
    - Graceful fallback if browser opening fails
    
    Required Parameters:
        notifier_file (str): Path where HTML visualization will be saved
            Example: "output/network_visualization.html"
        
        open_browser (bool, optional): Automatically open in default browser
            Default: True
            Set to False for automated/headless environments
    
    Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.
    
    Example Usage:
        # Via command line
        python main.py --iFormat ExcelImporter --input_file grid.xlsx \
               --oFormat PandapowerExporter --output_file grid.json \
               --nFormat PandapowerVisualizerNotifier --notifier_file viz.html
        
        # Programmatic usage
        notifier = PandapowerVisualizerNotifier()
        success, path = await notifier.notify(
            network=my_network,
            path=Path("output.json"),
            logger=logger,
            params={"notifier_file": "visualization.html", "open_browser": True}
        )
    """
    @classmethod
    def name(cls) -> str:
        return "PandapowerVisualizerNotifier"
    
    def required_parameters(self) -> dict:
        return {
            "notifier_file": None,
            "open_browser": True  # Default to opening in browser
        }

    async def _notify_impl(self, network: Network, path: Path, logger: logging.Logger, params: dict = {}) -> tuple[bool, object]:
        """
        Generate PandaPower-based HTML visualization and display in browser.
        
        This method orchestrates the visualization process:
        1. Converts the Network topology to PandaPower's internal format
        2. Generates an interactive HTML file using PandaPower's plotting library
        3. Saves the visualization to the specified file path
        4. Optionally opens the file in the default web browser
        
        The visualization includes all network elements (buses, lines, transformers,
        loads, generators) with proper color coding and interactive features.
        
        Args:
            network (Network): The electrical network topology to visualize
            path (Path): Reference to the export path (for logging)
            logger (logging.Logger): Logger instance for tracking progress
            params (dict): Visualization parameters:
                - notifier_file (str): Output HTML file path (required)
                - open_browser (bool): Auto-open in browser (default: True)
        
        Returns:
            tuple[bool, object]: (success_status, export_path)
                - success_status: True if visualization was generated successfully
                - export_path: Path object pointing to the exported file
        
        Raises:
            ValueError: If notifier_file parameter is missing
            IOError: If unable to write HTML file to specified path
        
        Notes:
            - Handles WSL environments by converting to Windows paths
            - Gracefully handles browser opening failures (logs warning)
            - Generated HTML is self-contained with embedded JavaScript
            - Tables are hidden by default for cleaner visualization
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
