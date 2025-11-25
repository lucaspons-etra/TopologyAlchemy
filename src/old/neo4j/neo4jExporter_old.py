"""
Neo4j Exporter for Topology Alchemy
Exports power system topology to Neo4j graph database using Cypher queries.
"""

from topology import (
    Element, Bus, LineShape, Meter, Switch, Network, UsagePointLocation, 
    VoltageLevel, Substation, TwoWindingsTransformer, ThreeWindingsTransformer, 
    Line, Load, Generator, DanglingLine, ShuntCompensator, Location
)
from Utils import Sanitizer, Transliterate
import json


def escape_cypher_string(value):
    """Escape special characters for Cypher queries."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # Escape backslashes and quotes
    value = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
    return f'"{value}"'


def format_properties(props):
    """Format properties dictionary for Cypher query."""
    prop_strings = []
    for key, value in props.items():
        if value is not None:
            prop_strings.append(f"{key}: {escape_cypher_string(value)}")
    return "{" + ", ".join(prop_strings) + "}"


def exportTopology(topology: Network, file, context, system, defaultLayoutMV, defaultLayoutLV, logger, exportLV=True):
    """
    Export power system topology to Neo4j Cypher format.
    
    Args:
        topology: Network topology object
        file: Output file path
        context: Context identifier
        system: System identifier
        defaultLayoutMV: Default MV layout
        defaultLayoutLV: Default LV layout
        logger: Logger instance
        exportLV: Whether to export LV (Low Voltage) network data (default: True)
    
    Returns:
        bool: True if export successful
    """
    logger.info(f"> Starting Neo4j exporting '{file}' (exportLV={exportLV})")
    
    sanitizer = Sanitizer(system, topology.prefix)
    
    with open(file, 'w', encoding='utf-8') as output:
        # Write header and constraints
        output.write("// Neo4j Cypher Export\n")
        output.write(f"// Context: {context}\n")
        output.write(f"// System: {system}\n\n")
        
        # Create constraints and indexes
        output.write("// Create constraints and indexes\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:System) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Substation) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Bus) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Load) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Generator) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Transformer) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Line) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Switch) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:DanglingLine) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:UsagePoint) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:UsagePointLocation) REQUIRE n.id IS UNIQUE;\n")
        output.write("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Meter) REQUIRE n.id IS UNIQUE;\n\n")
        
        # Delete existing data for this context
        output.write("// Delete existing data for this context\n")
        output.write(f'MATCH (n) WHERE n.context = "{context}" DETACH DELETE n;\n\n')
        
        # Export system
        output.write("// Create System node\n")
        system_cypher = exportSystem(topology, context, system, defaultLayoutMV, defaultLayoutLV, sanitizer)
        output.write(system_cypher + "\n\n")
        
        # Process main topology (MV network) - always export
        logger.info("Exporting MV network...")
        
        export_network_data(topology.elements["subTopologies"][0], system, context, output, sanitizer)
        
        # Process subTopologies (LV networks) - only if exportLV is True
        if exportLV:
            sub_topologies = topology.getElements("subTopologies")
            if sub_topologies:
                logger.info(f"Exporting {len(sub_topologies)} LV networks...")
                for subTopology in sub_topologies:
                    export_network_data(subTopology, system, context, output, sanitizer)
        else:
            logger.info("Skipping LV networks (exportLV=False)")
    
    logger.info("Finished Neo4j exporting!")
    return True


def export_network_data(subTopology, system, context, output, sanitizer):
    """
    Export data for a single network (topology or subTopology).
    
    Args:
        subTopology: Network or subTopology object
        system: System identifier
        context: Context identifier
        output: Output file handle
        sanitizer: Sanitizer instance
    """
    network_id = subTopology.network if hasattr(subTopology, 'network') else system
    
    # Export substations
    for sub in subTopology.getElements("substations"):
        output.write("// Substation\n")
        output.write(exportSubstation(sub, context, system, network_id, sanitizer) + "\n")
        
        # Export buses in substation
        for bus in sub.getElements("buses"):
            output.write(exportBus(bus, sub.id, context, system, network_id, sanitizer) + "\n")
            
            # Export loads
            for load in bus.getElements("loads"):
                output.write(exportLoad(load, sub.id, context, system, network_id, sanitizer) + "\n")
            
            # Export usage point locations
            for upl in bus.getElements("usagePointLocations"):
                output.write(exportUsagePointLocation(upl, sub.id, context, system, network_id, sanitizer) + "\n")
            
            # Export usage points
            for up in bus.getElements("usagePoints"):
                output.write(exportUsagePoint(up, context, system, network_id, sanitizer) + "\n")
                
                # Export meters
                for meter in up.getElements("meters"):
                    output.write(exportMeter(meter, context, system, network_id, sanitizer) + "\n")
            
            # Export generators
            for gen in bus.getElements("generators"):
                output.write(exportGenerator(gen, sub.id, context, system, network_id, sanitizer) + "\n")
            
            # Export dangling lines
            for dl in bus.getElements("danglingLines"):
                output.write(exportDanglingLine(dl, sub.id, context, system, network_id, sanitizer) + "\n")
        
        # Export switches in substation
        for switch in sub.getElements("switches"):
            output.write(exportSwitch(switch, sub.id, context, system, network_id, sanitizer) + "\n")
        
        # Export transformers in substation
        for trafo in sub.getElements("twoWindingsTransformers"):
            output.write(exportTwoWindingsTransformer(trafo, sub.id, context, system, network_id, sanitizer) + "\n")
        
        for trafo in sub.getElements("threeWindingsTransformers"):
            output.write(exportThreeWindingsTransformer(trafo, sub.id, context, system, network_id, sanitizer) + "\n")
        
        # Export lines in substation
        for line in sub.getElements("lines"):
            output.write(exportLine(line, context, system, network_id, sanitizer) + "\n")
    
    # Export standalone buses (not in substations)
    for bus in subTopology.getElements("buses"):
        output.write(exportBus(bus, None, context, system, network_id, sanitizer) + "\n")
        
        # Export loads
        for load in bus.getElements("loads"):
            output.write(exportLoad(load, None, context, system, network_id, sanitizer) + "\n")
        
        # Export usage point locations
        for upl in bus.getElements("usagePointLocations"):
            output.write(exportUsagePointLocation(upl, None, context, system, network_id, sanitizer) + "\n")
        
        # Export usage points
        for up in bus.getElements("usagePoints"):
            output.write(exportUsagePoint(up, context, system, network_id, sanitizer) + "\n")
            
            # Export meters
            for meter in up.getElements("meters"):
                output.write(exportMeter(meter, context, system, network_id, sanitizer) + "\n")
        
        # Export generators
        for gen in bus.getElements("generators"):
            output.write(exportGenerator(gen, None, context, system, network_id, sanitizer) + "\n")
        
        # Export dangling lines
        for dl in bus.getElements("danglingLines"):
            output.write(exportDanglingLine(dl, None, context, system, network_id, sanitizer) + "\n")
    
    # Export standalone switches
    for switch in subTopology.getElements("switches"):
        output.write(exportSwitch(switch, None, context, system, network_id, sanitizer) + "\n")
    
    # Export standalone lines
    for line in subTopology.getElements("lines"):
        output.write(exportLine(line, context, system, network_id, sanitizer) + "\n")


def exportSystem(topology: Network, context, system, defaultLayoutMV, defaultLayoutLV, sanitizer):
    """Export system node."""
    networks = []
    networks.append({
        "name": topology.name,
        "networkId": topology.id,
        "feeder": False,
        "layout": defaultLayoutMV
    })
    
    for t in topology.getElements("subTopologies"):
        networks.append({
            "name": t.name,
            "networkId": t.id,
            "feeder": True,
            "layout": defaultLayoutLV
        })
    
    props = {
        "id": system,
        "name": system,
        "context": context,
        "networks": json.dumps(networks)
    }
    
    return f"CREATE (s:System {format_properties(props)});"


def exportSubstation(sub: Substation, context, system, network, sanitizer):
    """Export substation node."""
    sub_id = sanitizer.sanitizeId(sub.id)
    props = {
        "id": sub_id,
        "mRID": sub.id,
        "name": sub.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "CT",
        "type": "Substation"
    }
    
    if hasattr(sub, 'feeder_num') and sub.feeder_num:
        props["feederNumber"] = sub.feeder_num
    
    # Add geometry if location exists
    if isinstance(sub, Location) and sub.coords:
        props["latitude"] = sub.coords[0]
        props["longitude"] = sub.coords[1]
    
    cypher = f"CREATE (n:Substation {format_properties(props)});"
    
    # Link to system
    cypher += f'\nMATCH (s:System {{id: "{system}"}}), (n:Substation {{id: "{sub_id}"}}) CREATE (s)-[:HAS_SUBSTATION]->(n);'
    
    return cypher


def exportBus(bus: Bus, substation_id, context, system, network, sanitizer):
    """Export bus node."""
    bus_id = sanitizer.sanitizeId(bus.id)
    props = {
        "id": bus_id,
        "mRID": bus.id,
        "name": bus.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "bus",
        "type": "Bus",
        "voltageLevel": bus.voltageLevel.id,
        "nominalVoltage": bus.voltageLevel.nominalV * 1000,  # kV to V
        "voltageLevelType": bus.voltageLevel.type
    }
    
    if hasattr(bus, 'feeder_num') and bus.feeder_num:
        props["feederNumber"] = bus.feeder_num
    
    # Add geometry if location exists
    if isinstance(bus, Location) and bus.coords:
        props["latitude"] = bus.coords[0]
        props["longitude"] = bus.coords[1]
    
    cypher = f"CREATE (n:Bus {format_properties(props)});"
    
    # Link to substation if exists
    if substation_id:
        san_sub_id = sanitizer.sanitizeId(substation_id)
        cypher += f'\nMATCH (s:Substation {{id: "{san_sub_id}"}}), (n:Bus {{id: "{bus_id}"}}) CREATE (s)-[:HAS_BUS]->(n);'
    
    return cypher


def exportLoad(load: Load, substation_id, context, system, network, sanitizer):
    """Export load node."""
    load_id = sanitizer.sanitizeId(load.id)
    bus_id = sanitizer.sanitizeId(load.parent.id)
    
    props = {
        "id": load_id,
        "mRID": load.id,
        "name": load.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "pod",
        "type": "Load",
        "ratedPower": load.p,  # kW
        "referenceReactivePower": load.q  # kvar
    }
    
    if hasattr(load, 'feeder_num') and load.feeder_num:
        props["feederNumber"] = load.feeder_num
    
    # Add geometry if location exists
    if isinstance(load, Location) and load.coords:
        props["latitude"] = load.coords[0]
        props["longitude"] = load.coords[1]
    
    cypher = f"CREATE (n:Load {format_properties(props)});"
    
    # Link to bus
    cypher += f'\nMATCH (b:Bus {{id: "{bus_id}"}}), (n:Load {{id: "{load_id}"}}) CREATE (b)-[:HAS_LOAD]->(n);'
    
    # Link to substation if exists
    if substation_id:
        san_sub_id = sanitizer.sanitizeId(substation_id)
        cypher += f'\nMATCH (s:Substation {{id: "{san_sub_id}"}}), (n:Load {{id: "{load_id}"}}) CREATE (s)-[:CONTAINS]->(n);'
    
    return cypher


def exportUsagePointLocation(upl: UsagePointLocation, substation_id, context, system, network, sanitizer):
    """Export usage point location node."""
    upl_id = sanitizer.sanitizeId(upl.id)
    bus_id = sanitizer.sanitizeId(upl.parent.id)
    
    props = {
        "id": upl_id,
        "mRID": upl.id,
        "name": upl.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "pod",
        "type": "UsagePointLocation"
    }
    
    if hasattr(upl, 'feeder_num') and upl.feeder_num:
        props["feederNumber"] = upl.feeder_num
    
    # Add geometry if location exists
    if isinstance(upl, Location) and upl.coords:
        props["latitude"] = upl.coords[0]
        props["longitude"] = upl.coords[1]
    
    cypher = f"CREATE (n:UsagePointLocation {format_properties(props)});"
    
    # Link to bus
    cypher += f'\nMATCH (b:Bus {{id: "{bus_id}"}}), (n:UsagePointLocation {{id: "{upl_id}"}}) CREATE (b)-[:HAS_USAGE_POINT_LOCATION]->(n);'
    
    # Link to substation if exists
    if substation_id:
        san_sub_id = sanitizer.sanitizeId(substation_id)
        cypher += f'\nMATCH (s:Substation {{id: "{san_sub_id}"}}), (n:UsagePointLocation {{id: "{upl_id}"}}) CREATE (s)-[:CONTAINS]->(n);'
    
    return cypher


def exportUsagePoint(up: Meter, context, system, network, sanitizer):
    """Export usage point node."""
    up_id = sanitizer.sanitizeId(up.id)
    bus_id = sanitizer.sanitizeId(up.parent.id)
    loc_id = sanitizer.sanitizeId(up.location.id)
    
    props = {
        "id": up_id,
        "mRID": up.id,
        "name": up.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "pod",
        "type": "UsagePoint",
        "ratedPower": up.ratedPower if hasattr(up, 'ratedPower') else None,
        "amiBillingReady": 4,
        "connectionState": 1,
        "isSdp": True,
        "isVirtual": False,
        "nominalServiceVoltage": 220.0
    }
    
    if hasattr(up, 'feeder_num') and up.feeder_num:
        props["feederNumber"] = up.feeder_num
    
    cypher = f"CREATE (n:UsagePoint {format_properties(props)});"
    
    # Link to bus
    cypher += f'\nMATCH (b:Bus {{id: "{bus_id}"}}), (n:UsagePoint {{id: "{up_id}"}}) CREATE (b)-[:HAS_USAGE_POINT]->(n);'
    
    # Link to usage point location
    cypher += f'\nMATCH (l:UsagePointLocation {{id: "{loc_id}"}}), (n:UsagePoint {{id: "{up_id}"}}) CREATE (n)-[:LOCATED_AT]->(l);'
    
    return cypher


def exportMeter(meter: Meter, context, system, network, sanitizer):
    """Export meter node."""
    meter_id = sanitizer.sanitizeId(meter.id)
    up_id = sanitizer.sanitizeId(meter.parent.id)
    
    props = {
        "id": meter_id,
        "mRID": meter.id,
        "name": meter.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "meter",
        "type": "Meter",
        "isVirtual": False,
        "installedPower": meter.p if hasattr(meter, 'p') else None,  # kW
        "referenceReactivePower": meter.q if hasattr(meter, 'q') else None  # kvar
    }
    
    if hasattr(meter, 'feeder_num') and meter.feeder_num:
        props["feederNumber"] = meter.feeder_num
    
    cypher = f"CREATE (n:Meter {format_properties(props)});"
    
    # Link to usage point
    cypher += f'\nMATCH (u:UsagePoint {{id: "{up_id}"}}), (n:Meter {{id: "{meter_id}"}}) CREATE (u)-[:HAS_METER]->(n);'
    
    return cypher


def exportGenerator(gen: Generator, substation_id, context, system, network, sanitizer):
    """Export generator node."""
    gen_id = sanitizer.sanitizeId(gen.id)
    bus_id = sanitizer.sanitizeId(gen.parent.id)
    
    props = {
        "id": gen_id,
        "mRID": gen.id,
        "name": gen.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "generator",
        "type": "Generator",
        "controllable": gen.controllable,
        "installedPower": gen.maxP  # kW
    }
    
    if hasattr(gen, 'feeder_num') and gen.feeder_num:
        props["feederNumber"] = gen.feeder_num
    
    # Add geometry if location exists
    if isinstance(gen, Location) and gen.coords:
        props["latitude"] = gen.coords[0]
        props["longitude"] = gen.coords[1]
    
    cypher = f"CREATE (n:Generator {format_properties(props)});"
    
    # Link to bus
    cypher += f'\nMATCH (b:Bus {{id: "{bus_id}"}}), (n:Generator {{id: "{gen_id}"}}) CREATE (b)-[:HAS_GENERATOR]->(n);'
    
    # Link to substation if exists
    if substation_id:
        san_sub_id = sanitizer.sanitizeId(substation_id)
        cypher += f'\nMATCH (s:Substation {{id: "{san_sub_id}"}}), (n:Generator {{id: "{gen_id}"}}) CREATE (s)-[:CONTAINS]->(n);'
    
    return cypher


def exportDanglingLine(dl: DanglingLine, substation_id, context, system, network, sanitizer):
    """Export dangling line node."""
    dl_id = sanitizer.sanitizeId(dl.id)
    bus_id = sanitizer.sanitizeId(dl.parent.id)
    
    props = {
        "id": dl_id,
        "mRID": dl.id,
        "name": dl.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "danglingLine",
        "type": "DanglingLine",
        "lineType": dl.type if hasattr(dl, 'type') else None,
        "controllable": dl.controllable if hasattr(dl, 'controllable') else False
    }
    
    if hasattr(dl, 'feeder_num') and dl.feeder_num:
        props["feederNumber"] = dl.feeder_num
    
    cypher = f"CREATE (n:DanglingLine {format_properties(props)});"
    
    # Link to bus
    cypher += f'\nMATCH (b:Bus {{id: "{bus_id}"}}), (n:DanglingLine {{id: "{dl_id}"}}) CREATE (b)-[:HAS_DANGLING_LINE]->(n);'
    
    # Link to substation if exists
    if substation_id:
        san_sub_id = sanitizer.sanitizeId(substation_id)
        cypher += f'\nMATCH (s:Substation {{id: "{san_sub_id}"}}), (n:DanglingLine {{id: "{dl_id}"}}) CREATE (s)-[:CONTAINS]->(n);'
    
    return cypher


def exportSwitch(switch: Switch, substation_id, context, system, network, sanitizer):
    """Export switch node and relationships."""
    switch_id = sanitizer.sanitizeId(switch.id)
    bus1_id = sanitizer.sanitizeId(switch.bus1.id)
    bus2_id = sanitizer.sanitizeId(switch.bus2.id)
    
    props = {
        "id": switch_id,
        "mRID": switch.id,
        "name": switch.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "switch",
        "type": "Switch"
    }
    
    if hasattr(switch, 'feeder_num') and switch.feeder_num:
        props["feederNumber"] = switch.feeder_num
    
    cypher = f"CREATE (n:Switch {format_properties(props)});"
    
    # Link to buses
    cypher += f'\nMATCH (b1:Bus {{id: "{bus1_id}"}}), (n:Switch {{id: "{switch_id}"}}) CREATE (b1)-[:CONNECTED_TO]->(n);'
    cypher += f'\nMATCH (b2:Bus {{id: "{bus2_id}"}}), (n:Switch {{id: "{switch_id}"}}) CREATE (n)-[:CONNECTED_TO]->(b2);'
    
    # Link to substation if exists
    if substation_id:
        san_sub_id = sanitizer.sanitizeId(substation_id)
        cypher += f'\nMATCH (s:Substation {{id: "{san_sub_id}"}}), (n:Switch {{id: "{switch_id}"}}) CREATE (s)-[:CONTAINS]->(n);'
    
    return cypher


def exportTwoWindingsTransformer(trafo: TwoWindingsTransformer, substation_id, context, system, network, sanitizer):
    """Export two windings transformer node and relationships."""
    trafo_id = sanitizer.sanitizeId(trafo.id)
    sub_id = sanitizer.sanitizeId(trafo.parent.id)
    bus1_id = sanitizer.sanitizeId(trafo.bus1.id)
    bus2_id = sanitizer.sanitizeId(trafo.bus2.id)
    
    props = {
        "id": trafo_id,
        "mRID": trafo.id,
        "name": trafo.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "transformer",
        "type": "Transformer",
        "windingType": "Two",
        "r": trafo.r,
        "x": trafo.x,
        "g": trafo.g,
        "b": trafo.b,
        "ratedApparentPower": trafo.nominal,  # kVA
        "ratedVoltage1": trafo.bus1.voltageLevel.nominalV * 1000,  # kV to V
        "ratedVoltage2": trafo.bus2.voltageLevel.nominalV * 1000,  # kV to V
        "voltageLevel1": trafo.bus1.voltageLevel.id,
        "voltageLevel2": trafo.bus2.voltageLevel.id
    }
    
    if hasattr(trafo, 'feeder_num') and trafo.feeder_num:
        props["feederNumber"] = trafo.feeder_num
    
    cypher = f"CREATE (n:Transformer {format_properties(props)});"
    
    # Link to substation
    cypher += f'\nMATCH (s:Substation {{id: "{sub_id}"}}), (n:Transformer {{id: "{trafo_id}"}}) CREATE (s)-[:HAS_TRANSFORMER]->(n);'
    
    # Link to buses
    cypher += f'\nMATCH (b1:Bus {{id: "{bus1_id}"}}), (n:Transformer {{id: "{trafo_id}"}}) CREATE (b1)-[:CONNECTED_TO]->(n);'
    cypher += f'\nMATCH (b2:Bus {{id: "{bus2_id}"}}), (n:Transformer {{id: "{trafo_id}"}}) CREATE (n)-[:CONNECTED_TO]->(b2);'
    
    return cypher


def exportThreeWindingsTransformer(trafo: ThreeWindingsTransformer, substation_id, context, system, network, sanitizer):
    """Export three windings transformer node and relationships."""
    trafo_id = sanitizer.sanitizeId(trafo.id)
    sub_id = sanitizer.sanitizeId(trafo.parent.id)
    bus1_id = sanitizer.sanitizeId(trafo.bus1.id)
    bus2_id = sanitizer.sanitizeId(trafo.bus2.id)
    bus3_id = sanitizer.sanitizeId(trafo.bus3.id)
    
    props = {
        "id": trafo_id,
        "mRID": trafo.id,
        "name": trafo.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "transformer",
        "type": "Transformer",
        "windingType": "Three",
        "r1": trafo.r1,
        "r2": trafo.r2,
        "r3": trafo.r3,
        "x1": trafo.x1,
        "x2": trafo.x2,
        "x3": trafo.x3,
        "g1": trafo.g1,
        "g2": trafo.g2,
        "g3": trafo.g3,
        "b1": trafo.b1,
        "b2": trafo.b2,
        "b3": trafo.b3,
        "ratedApparentPower1": trafo.ratedS1,  # kVA
        "ratedApparentPower2": trafo.ratedS2,  # kVA
        "ratedApparentPower3": trafo.ratedS3,  # kVA
        "ratedVoltageStarBus": trafo.ratedStar * 1000,  # kV to V
        "ratedVoltage1": trafo.bus1.voltageLevel.nominalV * 1000,  # kV to V
        "ratedVoltage2": trafo.bus2.voltageLevel.nominalV * 1000,  # kV to V
        "ratedVoltage3": trafo.bus3.voltageLevel.nominalV * 1000,  # kV to V
        "voltageLevel1": trafo.bus1.voltageLevel.id,
        "voltageLevel2": trafo.bus2.voltageLevel.id,
        "voltageLevel3": trafo.bus3.voltageLevel.id
    }
    
    if hasattr(trafo, 'feeder_num') and trafo.feeder_num:
        props["feederNumber"] = trafo.feeder_num
    
    cypher = f"CREATE (n:Transformer {format_properties(props)});"
    
    # Link to substation
    cypher += f'\nMATCH (s:Substation {{id: "{sub_id}"}}), (n:Transformer {{id: "{trafo_id}"}}) CREATE (s)-[:HAS_TRANSFORMER]->(n);'
    
    # Link to buses
    cypher += f'\nMATCH (b1:Bus {{id: "{bus1_id}"}}), (n:Transformer {{id: "{trafo_id}"}}) CREATE (b1)-[:CONNECTED_TO]->(n);'
    cypher += f'\nMATCH (b2:Bus {{id: "{bus2_id}"}}), (n:Transformer {{id: "{trafo_id}"}}) CREATE (n)-[:CONNECTED_TO]->(b2);'
    cypher += f'\nMATCH (b3:Bus {{id: "{bus3_id}"}}), (n:Transformer {{id: "{trafo_id}"}}) CREATE (n)-[:CONNECTED_TO]->(b3);'
    
    return cypher


def exportLine(line: Line, context, system, network, sanitizer):
    """Export line node and relationships."""
    line_id = sanitizer.sanitizeId(line.id)
    bus1_id = sanitizer.sanitizeId(line.bus1.id)
    bus2_id = sanitizer.sanitizeId(line.bus2.id)
    
    props = {
        "id": line_id,
        "mRID": line.id,
        "name": line.name,
        "context": context,
        "system": system,
        "network": network,
        "shape": "line",
        "type": "Line",
        "voltageLevel1": line.voltageLevel.id,
        "voltageLevel2": line.voltageLevel.id,
        "length": line.length,
        "lineShape": line.type if hasattr(line, 'type') else None,
        "lineType": line.type if hasattr(line, 'type') else None,
        "cable": str(line.cable) if hasattr(line, 'cable') else None,
        "currentLimit": line.currentLimit if hasattr(line, 'currentLimit') and line.currentLimit and line.currentLimit > 0 else None,
        "r": line.r,
        "x": line.x,
        "g1": line.g1 if hasattr(line, 'g1') else None,
        "g2": line.g2 if hasattr(line, 'g2') else None,
        "b1": line.b1 if hasattr(line, 'b1') else None,
        "b2": line.b2 if hasattr(line, 'b2') else None
    }
    
    if hasattr(line, 'feeder_num') and line.feeder_num:
        props["feederNumber"] = line.feeder_num
    
    # Add line shape geometry if exists
    if isinstance(line, LineShape) and line.line_shape:
        # Convert to GeoJSON-like format
        coords = [[lon, lat] for lat, lon in line.line_shape]
        props["geometry"] = json.dumps({"type": "LineString", "coordinates": coords})
    
    cypher = f"CREATE (n:Line {format_properties(props)});"
    
    # Link to buses
    cypher += f'\nMATCH (b1:Bus {{id: "{bus1_id}"}}), (n:Line {{id: "{line_id}"}}) CREATE (b1)-[:CONNECTED_TO]->(n);'
    cypher += f'\nMATCH (b2:Bus {{id: "{bus2_id}"}}), (n:Line {{id: "{line_id}"}}) CREATE (n)-[:CONNECTED_TO]->(b2);'
    
    return cypher
