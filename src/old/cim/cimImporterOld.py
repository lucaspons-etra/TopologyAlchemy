from rdflib import Graph
from topology import Network
import re

def clean_identifier(identifier):
    # Replace spaces with underscores
    identifier = identifier.replace(' ', '_')
    # Remove non-alphanumeric characters except underscores and colons
    identifier = re.sub(r'[^a-zA-Z0-9_:]', '', identifier)
    return identifier

def process_xml_string(xml_content):
    # Regular expression to find rdf:resource attributes with spaces in the value
    pattern = re.compile(r'rdf:resource="([^"]* [^"]*)"')

    # Replacement function to clean the IDs
    def replace_match(match):
        original_value = match.group(1)
        cleaned_value = clean_identifier(original_value)
        return f'rdf:resource="{cleaned_value}"'

    # Replace the values of the rdf:resource attributes
    cleaned_content = pattern.sub(replace_match, xml_content)
    return cleaned_content

def process_xml_string2(xml_content):
    # Regular expression to find rdf:resource attributes with spaces in the value
    pattern = re.compile(r'rdf:ID="([^"]* [^"]*)"')

    # Replacement function to clean the IDs
    def replace_match(match):
        original_value = match.group(1)
        cleaned_value = clean_identifier(original_value)
        return f'rdf:ID="{cleaned_value}"'

    # Replace the values of the rdf:resource attributes
    cleaned_content = pattern.sub(replace_match, xml_content)
    return cleaned_content

def queryOne(g:Graph, query):
    prefixes = ["PREFIX "+short+": <" + uri + ">" for short,uri in g.namespaces()]
    
    q = """
    """.join(prefixes) + """
    """ +query
    
    results = g.query(q)
    return next(iter(results),None)

def query(g:Graph, query):
    prefixes = ["PREFIX "+short+": <" + uri + ">" for short,uri in g.namespaces()]
    
    q = """
    """.join(prefixes) + """
    """ +query
    
    results = g.query(q)
    return results

def find_feeder_nodes(g:Graph):
    # Inicializar la lista de nodos y la lista de nodos por procesar
    nodes = set()
    equipments = []
    nodes_to_process = set()

    # Encontrar el nodo inicial del alimentador
    query_initial = f"""
    PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
    PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?startNode ?equipment ?f
    WHERE {{
        ?f rdf:type cim:FeederObject .
        ?f cim:IdentifiedObject.name "ELIKAN GRADIŠČE 20/0,4 G-050" .
        ?equipment cim:Equipment.EquipmentContainer ?f .
        ?terminal cim:Terminal.ConductingEquipment ?equipment .
        ?terminal cim:Terminal.ConnectivityNode ?startNode .
    }}
    """
    
    feeder=None
    results_initial = g.query(query_initial)
    for row in results_initial:
        feeder = row.f
        nodes_to_process.add((row.startNode, row.equipment))

    # Iterativamente encontrar todos los equipos conectados
    while nodes_to_process:
        current_node, current_equipment = nodes_to_process.pop()
        if current_equipment not in equipments:
            equipments.append(current_equipment)
            query_recursive = f"""
            PREFIX cim: <http://iec.ch/TC57/2013/CIM-schema-cim16#>    
            PREFIX sedms: <http://www.schneider-electric-dms.com/CIM16v33/2017/extension>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?nextNode ?nextEquipment
            WHERE {{
                ?terminal1 cim:Terminal.ConnectivityNode <{current_node}> .
                ?terminal1 cim:Terminal.ConductingEquipment ?equipment .
                ?terminal2 cim:Terminal.ConductingEquipment ?equipment .
                ?terminal2 cim:Terminal.ConnectivityNode ?nextNode .
                ?nextTerminal cim:Terminal.ConnectivityNode ?nextNode .
                ?nextTerminal cim:Terminal.ConductingEquipment ?nextEquipment .
                ?equipment cim:ConnectivityNode.ConnectivityNodeContainer|cim:Equipment.EquipmentContainer <{feeder}> .
                ?nextEquipment cim:ConnectivityNode.ConnectivityNodeContainer|cim:Equipment.EquipmentContainer <{feeder}> .
                FILTER (?equipment = <{current_equipment}>)
            }}
            """
            results_recursive = g.query(query_recursive)
            for row in results_recursive:
                if row.nextEquipment not in equipments:
                    nodes_to_process.add((row.nextNode, row.nextEquipment))

    return equipments

def importTopology(topology, content: str, id):
    g = Graph()
    content=process_xml_string2(process_xml_string(content))
    #print(content)
    g.parse(data=content, format="xml")

    feeder_nodes = find_feeder_nodes(g)
    print(feeder_nodes)

def importTopology2(topology, content: str, id):
    g = Graph()
    content=process_xml_string2(process_xml_string(content))
    print(content)
    g.parse(data=content, format="xml")
    
    circuit = queryOne(g,"""
    SELECT ?feeder 
    WHERE {
        ?feeder rdf:type cim:FeederObject .
    }""")
    
    topo = Network(id,str(circuit.circuitName))
    
    elements = query(g,"""
    SELECT distinct ?equipment ?type ?equipment2 ?type2
    WHERE {
        ?terminal cim:Terminal.ConductingEquipment ?equipment .
        ?terminal cim:Terminal.ConnectivityNode ?node .
        ?terminal2 cim:Terminal.ConnectivityNode ?node .
        ?terminal2 cim:Terminal.ConductingEquipment ?equipment2 .
        ?equipment rdf:type ?type .
        ?equipment2 rdf:type ?type2 .
    }""")

    # Almacenar las conexiones en una lista
    connections = []
    for row in elements:
        if row.equipment > row.equipment2:
            equipment = str(row.type).split("#")[1] + "-" + str(row.equipment).split("#")[1]
            equipment2 = str(row.type2).split("#")[1] + "-" + str(row.equipment2).split("#")[1]
            connections.append((equipment, equipment2))
        

    for connection in connections:
        print(connection)
    
    return "hello"

