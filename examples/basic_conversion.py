#!/usr/bin/env python3
"""
Basic Conversion Example

This example demonstrates a simple topology conversion using Topology Alchemy.
It converts an Excel file to PandaPower format.

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from alchemist import Alchemist
from base_importer import Importer
from base_exporter import Exporter


async def convert_topology():
    """
    Perform a basic topology conversion from Excel to PandaPower format.
    """
    # Configuration
    input_file = "data/sample_network.xlsx"
    output_file = "output/sample_network.json"
    network_id = "sample_network"
    
    print("=" * 70)
    print("Topology Alchemy - Basic Conversion Example")
    print("=" * 70)
    print()
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print(f"Network ID: {network_id}")
    print()
    
    # Create output directory if it doesn't exist
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Get importer and exporter
    importer = Importer.get_importer("ExcelImporter")
    exporter = Exporter.get_exporter("PandapowerExporter")
    
    if not importer:
        print("ERROR: ExcelImporter not found")
        return False
    
    if not exporter:
        print("ERROR: PandapowerExporter not found")
        return False
    
    # Prepare parameters
    params = {
        "input_file": input_file,
        "output_file": output_file,
        "network_id": network_id,
        "process_lv": False,
        "system": "Example System",
    }
    
    # Create Alchemist and perform conversion
    alchemist = Alchemist(log_level="INFO")
    
    print("Starting conversion...")
    print()
    
    success = await alchemist.process(
        base_importer=importer,
        base_exporter=exporter,
        base_notifiers=None,
        params=params
    )
    
    print()
    if success:
        print("[SUCCESS] Conversion completed successfully!")
        print(f"  Output saved to: {output_file}")
    else:
        print("[FAILED] Conversion failed!")
    
    print()
    print("=" * 70)
    
    return success


if __name__ == "__main__":
    # Run the conversion
    result = asyncio.run(convert_topology())
    sys.exit(0 if result else 1)
