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
    @classmethod
    def name(cls) -> str:
        return "PandapowerVisualizerNotifier"
    
    def required_parameters(self) -> dict:
        return {
            "notifier_file": None,
            "open_browser": True  # Default to opening in browser
        }

    async def _notify_impl(self, network: Network, path: Path, logger: logging.Logger, params: dict = {}) -> tuple[bool, object]:
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
