#!/usr/bin/env python3
"""
Programmatic Topology Creation Example

This example demonstrates how to create a topology from scratch using
the Topology Alchemy data model and then export it to various formats.

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from topology import Network, Substation, VoltageLevel, Bus
from alchemist import get_logger
from base_exporter import Exporter


def create_sample_network():
    """
    Create a simple sample network with substations, buses, and lines.
    
    Returns:
        Network: A configured network object
    """
    print("Creating sample network...")
    
    # Create main network
    network = Network(
        id="sample_network",
        name="Sample Distribution Network",
        system="Example Utility"
    )
    
    # Create voltage levels
    vl_20kv = network.addVoltageLevel(
        id="VL_20000",
        name="20 kV",
        nominalV=20.0,
        type="MV"
    )
    
    vl_400v = network.addVoltageLevel(
        id="VL_400",
        name="400 V",
        nominalV=0.4,
        type="LV"
    )
    
    # Create substation 1
    substation1 = network.addSubstation(
        id="SS_001",
        name="Main Substation",
        coords=[40.7128, -74.0060]  # Example coordinates (NYC)
    )
    
    # Add buses to substation 1
    bus1 = substation1.addBus(
        id="BUS_001",
        name="Bus 1",
        voltageLevel=vl_20kv,
        coords=[40.7128, -74.0060]
    )
    
    bus2 = substation1.addBus(
        id="BUS_002",
        name="Bus 2",
        voltageLevel=vl_20kv,
        coords=[40.7138, -74.0050]
    )
    
    # Create substation 2
    substation2 = network.addSubstation(
        id="SS_002",
        name="Secondary Substation",
        coords=[40.7158, -74.0040]
    )
    
    # Add bus to substation 2
    bus3 = substation2.addBus(
        id="BUS_003",
        name="Bus 3",
        voltageLevel=vl_20kv,
        coords=[40.7158, -74.0040]
    )
    
    # Add transformer
    transformer = substation1.addTransformer(
        id="TRAFO_001",
        name="Transformer 1",
        bus1=bus1,
        bus2=bus2,
        r=0.01,
        x=0.05,
        g=0.0,
        b=0.0,
        nominal=1.0,
        coords=[40.7128, -74.0060]
    )
    
    # Add line between substations
    line = network.addLine(
        id="LINE_001",
        name="Line 1-3",
        bus1=bus2,
        bus2=bus3,
        r=0.5,
        x=0.3,
        g1=0.0,
        b1=0.0,
        g2=0.0,
        b2=0.0,
        currentLimit=400.0,
        length=2000.0,
        cable="ACSR 150"
    )
    
    # Add loads
    load1 = bus2.addLoad(
        id="LOAD_001",
        name="Load 1",
        p=0.5,
        q=0.1,
        coords=[40.7138, -74.0050]
    )
    
    load2 = bus3.addLoad(
        id="LOAD_002",
        name="Load 2",
        p=0.3,
        q=0.08,
        coords=[40.7158, -74.0040]
    )
    
    # Add generator
    generator = bus1.addMvGenerator(
        id="GEN_001",
        name="Generator 1",
        targetP=2.0,
        targetV=1.0,
        minP=0.0,
        maxP=5.0,
        coords=[40.7128, -74.0060]
    )
    
    print(f"Created network '{network.name}' with:")
    print(f"  - {len(network.getElements('substations'))} substations")
    print(f"  - {len(network.getElements('buses'))} buses")
    print(f"  - {len(network.getElements('lines'))} lines")
    print()
    
    return network


async def export_network(network, format_name, output_file):
    """
    Export the network to a specific format.
    
    Args:
        network: Network object to export
        format_name: Name of the exporter to use
        output_file: Path to output file
    """
    print(f"Exporting to {format_name}...")
    
    # Get exporter
    exporter = Exporter.get_exporter(format_name)
    
    if not exporter:
        print(f"  [ERROR] Exporter '{format_name}' not found")
        return False
    
    # Create logger
    logger = get_logger("ExportExample", "INFO")
    
    # Prepare parameters
    params = {"output_file": output_file}
    
    # Export
    success, paths = await exporter.export_topology(
        network=network,
        logger=logger,
        params=params
    )
    
    if success:
        print(f"  [SUCCESS] Exported successfully to: {output_file}")
    else:
        print(f"  [FAILED] Export failed")
    
    return success


async def main():
    """
    Main function to create and export a sample network.
    """
    print("=" * 70)
    print("Topology Alchemy - Programmatic Topology Creation Example")
    print("=" * 70)
    print()
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample network
    network = create_sample_network()
    
    # Export to multiple formats
    exports = [
        ("JsonExporter", "output/sample_network.json"),
        ("PandapowerExporter", "output/sample_network_pp.json"),
    ]
    
    print("Exporting to multiple formats...")
    print()
    
    results = []
    for format_name, output_file in exports:
        success = await export_network(network, format_name, output_file)
        results.append(success)
        print()
    
    # Summary
    print("=" * 70)
    print("Summary:")
    print(f"  Total exports: {len(results)}")
    print(f"  Successful: {sum(results)}")
    print(f"  Failed: {len(results) - sum(results)}")
    print("=" * 70)
    
    return all(results)


if __name__ == "__main__":
    # Run the example
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
