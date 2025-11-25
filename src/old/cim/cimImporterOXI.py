from pyoxigraph import Store
from pyoxigraph.sparql import prepareQuery
from topology import Substation, Network, VoltageLevel, Bus, Load
import re
import json

def clean_identifier(identifier):
    # Replace spaces with underscores
    identifier = identifier.replace(' ', '_')
    # Remove non-alphanumeric characters except underscores and colons
    identifier = re.sub(r'[^a-zA-Z0-9_:]', '', identifier)
    return identifier

def clean_xml(xml_content):
    # Regular expression to find rdf:resource attributes with spaces in the value
    pattern = re.compile(r'rdf:ID="([^"]* [^"]*)"')

    # Replacement function to clean the IDs
    def replace_match(match):
        original_value = match.group(1)
        cleaned_value = clean_identifier(original_value)
        return f'rdf:ID="{cleaned_value}"'

    # Replace the values of the rdf:resource attributes
    cleaned_content = pattern.sub(replace_match, xml_content)
    cleaned_content = cleaned_content.replace('xmlns:sedms="http://www.schneider-electric-dms.com/CIM16v33/2017/extension"', 'xmlns:sedms="http://www.schneider-electric-dms.com/CIM16v33/2017/extension#"')
    return cleaned_content

def add_mv_substation(store: Store, topology: Network):
    query_feeders = prepareQuery("""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT *
    WHERE {
        ?feeder sedms:Circuit.circuitType "LVNetwork" .
        ?feeder cim:IdentifiedObject.description ?description .
        ?feeder cim:IdentifiedObject.name ?name .
        ?feeder cim:IdentifiedObject.mRID ?mRID
    }
    """)
    results = store.query(query_feeders)
    if len(results) != 1:
        raise Exception("There should be only one LVNetwork in the CIM file")
    for row in results:
        s: Substation = topology.addSubstation(str(row['mRID']), str(row['name']))
        voltageLevel: VoltageLevel = s.addVoltageLevel(str(row['mRID']), 400, 'LV')
        bus: Bus = voltageLevel.addBus(str(row['mRID']))
        return s, voltageLevel, bus, str(row['mRID'])

def add_buses(store: Store, topology: Network, voltageLevelSubstation: VoltageLevel, voltageLevel: VoltageLevel, feeder):
    query_connectivityNodes = prepareQuery("""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?connectivityNode ?connectedCircuits ?btpBay
    WHERE { 
        ?connectivityNode rdf:type cim:ConnectivityNode .
        ?connectivityNode cim:ConnectivityNode.ConnectivityNodeContainer ?circuit .
        ?circuit sedms:Circuit.btpBay ?btpBay
        OPTIONAL { ?connectivityNode sedms:ConnectivityNode.connectedCircuits ?connectedCircuits } .
    }
    """)
    results = store.query(query_connectivityNodes)
    for row in results:
        b: Bus = None
        if row['connectedCircuits']:
            b = voltageLevelSubstation.addBus(str(row['connectivityNode']), None, None)
        else:
            b = voltageLevel.addBus(str(row['connectivityNode']), feeder, str(row['btpBay']))
        addBusElements(store, topology, b, feeder)

def add_loads(store: Store, topology: Network):
    query_connectedServiceLocations = prepareQuery("""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT *
    WHERE {
        ?sl rdf:type cim:ServiceLocation .
        ?sl cim:IdentifiedObject.mRID ?serviceLocationmRID .
        ?sl sedms:ServiceLocation.Terminal ?t . 
        ?t cim:Terminal.ConnectivityNode ?cn .
        ?cn cim:IdentifiedObject.name ?cnName .
        ?cn cim:IdentifiedObject.mRID ?cnmRID .
        ?up cim:UsagePoint.ServiceLocation ?sl .
        ?up cim:IdentifiedObject.mRID ?upmRID .
        ?up cim:IdentifiedObject.name ?upName .
        ?up sedms:UsagePoint.p ?p .
        ?up sedms:UsagePoint.q ?q .
    }
    """)
    results = store.query(query_connectedServiceLocations)
    for row in results:
        bus: Bus = topology.getBus(str(row['cn']))
        load: Load = bus.addLoad(str(row['serviceLocationmRID']), bus.id, float(row['p']), float(row['q']), str(row['upName']))

def addGenerator(store: Store, bus: Bus, topology: Network, generatorId, feeder):
    query_connectedElements = prepareQuery("""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT *
    WHERE {
        ?gen rdf:type cim:DistributedGenerator .
        ?gen cim:IdentifiedObject.mRID  ?generatorId .
    }
    """)
    results = store.query(query_connectedElements, initBindings={'generatorId': generatorId})
    for row in results:
        if not topology.getGenerator(generatorId):
            bus.addGenerator(generatorId, bus.id, 0, 0, 0, 0, 0, 0, 0, True, [])

def addFuses(store: Store, voltageLevel: VoltageLevel, feeder):
    query_connectedElements = prepareQuery("""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT DISTINCT *
    WHERE {
        ?fuse rdf:type cim:Fuse .
        ?fuse cim:IdentifiedObject.mRID ?fuseId .
        ?fuse cim:Switch.normalOpen ?normalOpen .
        ?t1 rdf:type cim:Terminal .
        ?t2 rdf:type cim:Terminal .
        ?t1 cim:Terminal.ConductingEquipment ?fuse .
        ?t2 cim:Terminal.ConductingEquipment ?fuse .
        ?fuse cim:IdentifiedObject.mRID ?linemRID .
        ?t1 cim:Terminal.ConnectivityNode ?cn1 .
        ?t2 cim:Terminal.ConnectivityNode ?cn2 .
        FILTER (str(?t1) < str(?t2))
    }
    """)
    results = store.query(query_connectedElements)
    for row in results:
        voltageLevel.addSwitch(str(row['fuseId']), str(row['cn1']), str(row['cn2']), json.loads(str(row['normalOpen']).lower()))

def addBusElements(store: Store, topology: Network, bus: Bus, feeder):
    query_connectedElements = prepareQuery("""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT *
    WHERE {
        ?connectivityNode rdf:type cim:ConnectivityNode .
        ?connectivityNode cim:ConnectivityNode.ConnectivityNodeContainer ?circuit .
        ?circuit sedms:Circuit.btpBay ?btpBay .
        ?t cim:Terminal.ConnectivityNode ?connectivityNode .
        ?t cim:Terminal.ConductingEquipment ?ce .
        ?ce rdf:type ?type .
        ?ce cim:IdentifiedObject.mRID ?ceId
    }
    """)
    results = store.query(query_connectedElements)
    for row in results:
        t = str(row['type'])
        match t.split('#')[1]:
            case 'DistributedGenerator':
                addGenerator(store, bus, topology, str(row['ceId']), feeder)

def add_line_segments(store: Store, topology: Network, feeder):
    query_connectivityNodes = prepareQuery("""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT DISTINCT *
    WHERE {
        ?lineSegment rdf:type cim:ACLineSegment .
        ?t1 rdf:type cim:Terminal .
        ?t2 rdf:type cim:Terminal .
        ?t1 cim:Terminal.ConductingEquipment ?lineSegment .
        ?t2 cim:Terminal.ConductingEquipment ?lineSegment .
        ?lineSegment cim:IdentifiedObject.mRID ?linemRID .
        ?lineSegment cim:Conductor.length ?lineLength .
        ?lineSegment cim:ACLineSegment.PerLengthImpedance ?pli .
        ?pli cim:PerLengthSequenceImpedance.r ?r .
        ?pli cim:PerLengthSequenceImpedance.x ?x .
        ?pli cim:PerLengthSequenceImpedance.r0 ?g1 .
        ?pli cim:PerLengthSequenceImpedance.bch ?b1 .
        ?pli cim:PerLengthSequenceImpedance.x0 ?g2 .
        ?pli cim:PerLengthSequenceImpedance.b0ch ?b2 .
        ?lineSegment cim:PowerSystemResource.AssetDatasheet ?cable .
        ?cable cim:IdentifiedObject.name ?cableName .
        ?t1 cim:Terminal.ConnectivityNode ?cn1 .
        ?t2 cim:Terminal.ConnectivityNode ?cn2 .
        FILTER (str(?t1) < str(?t2))
    }
    """)
    results = store.query(query_connectivityNodes)
    for row in results:
        topology.addLine(row['linemRID'], row['cn1'], row['cn2'], r=float(row['r']), x=float(row['x']), g1=float(row['g1']), b1=float(row['b1']), g2=float(row['g2']), b2=float(row['b2']), length=row['lineLength'], cable=row['cableName'])

def importTopology(filename, id, logger):
    logger.info("> Starting CIM processing (MV) '{}'".format(str(filename)))
    topology: Network = Network(id)
    
    with open(filename, 'r') as file:
        xml_content = file.read()
    
    store = Store()
    content = clean_xml(xml_content)
    store.bulk_load(content, format="application/rdf+xml")
    
    # add_buses(store, voltageLevel, feeder)
    logger.info("Finished CIM processing!")
    return topology

def importLVTopology(filename, id, logger):
    logger.info("> Starting CIM processing (LV) '{}'".format(str(filename)))
    topology: Network = Network(id)
    
    with open(filename, 'r') as file:
        xml_content = file.read()
    
    store = Store()
    content = clean_xml(xml_content)
    store.bulk_load(content, format="application/rdf+xml")
    
    substation: Substation = None
    voltageLevel: VoltageLevel = None
    bus: Bus = None
    substation, voltageLevel, bus, feeder = add_mv_substation(store, topology)
    lvTopology: Network = topology.addSubTopology(feeder)
    substationLV: Substation = lvTopology.addSubstation(substation.id, substation.name)
    lvSubstationVoltageLevel: VoltageLevel = substationLV.addVoltageLevel(voltageLevel.id, voltageLevel.nominalV, 'LV')
    lvVoltageLevel: VoltageLevel = lvTopology.addVoltageLevel(voltageLevel.id, voltageLevel.nominalV, type='LV')
    
    add_buses(store, lvTopology, lvSubstationVoltageLevel, lvVoltageLevel, feeder)
    add_loads(store, lvTopology)
    add_line_segments(store, lvTopology, feeder)
    addFuses(store, lvVoltageLevel, feeder)
    logger.info("Finished CIM processing!")
    return topology