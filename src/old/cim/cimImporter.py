from rdflib import Graph
from topology import Substation, Network, VoltageLevel
import re

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

def add_substation(g:Graph, topology:Network):
    query_feeders = f"""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT *
    {{
        ?feeder sedms:Circuit.circuitType "LVNetwork" .
        ?feeder cim:IdentifiedObject.description ?description .
        ?feeder cim:IdentifiedObject.name ?name.
        ?feeder cim:IdentifiedObject.mRID ?mRID

    }}
    """
    results = g.query(query_feeders)
    if len(results) != 1:
        raise Exception("There should be only one LVNetwork in the CIM file")
    for row in results:
        s:Substation =  topology.addSubstation(row.mRID,row.name)
        voltageLevel:VoltageLevel = s.addVoltageLevel(row.mRID,400,'LV')
        return s,voltageLevel,row.mRID
        
    
    
def add_buses(g:Graph, voltageLevel:VoltageLevel, feeder): 
    # Encontrar el nodo inicial del alimentador
    query_connectivityNodes = f"""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?connectivityNode
    {{ 
        ?connectivityNode rdf:type cim:ConnectivityNode 
    }}
    """
    results = g.query(query_connectivityNodes)
    for row in results:
        feeder = row.f
        voltageLevel.addbus(row.connectivityNode, feeder) 
  
  
def process_rdf(topology:Network,xml_content):
    g = Graph()
    content=clean_xml(xml_content)
    g.parse(data=content, format="xml")
    substation, voltageLevel, feeder = add_substation(g,topology) 
    
    add_buses(g,voltageLevel,feeder)

def importTopology(filename, id, logger):
    logger.info("> Starting CIM processing '{}'".format(str(filename)))
    topology:Network = Network(id, id)  # Use id as both id and name
    
    # Read the file content
    with open(filename, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    process_rdf(topology, xml_content)
    logger.info("Finished CIM processing!")
    return topology