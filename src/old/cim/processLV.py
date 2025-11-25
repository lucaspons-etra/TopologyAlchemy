import xml.etree.ElementTree as ET
import networkx as nx
from pyvis.network import Network

# Parsear el archivo RDF
rdf_file = '/home/etraid/prj/topologyAlchemy/tests/data/slovenia/elikan.rdf'
#rdf_file = '/home/etraid/prj/topologyAlchemy/tests/data/NNO_STARA_VAS_20_0_4__G_319_ELC2040554_2023-06-13-10-57.xml'
tree = ET.parse(rdf_file)
root = tree.getroot()

# Crear un grafo dirigido
G = nx.DiGraph()

# Espacios de nombres
ns = {
    'cim': 'http://iec.ch/TC57/2013/CIM-schema-cim16#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'sedms': 'http://www.schneider-electric-dms.com/CIM16v33/2017/extension#'
}

# Diccionario para almacenar las conexiones directas
direct_connections = {}

# Extraer terminales, puntos de uso, nodos de conectividad, segmentos de línea, ubicaciones de servicio, fusibles y generadores distribuidos
terminals = root.findall('.//cim:Terminal', ns)
usage_points = root.findall('.//cim:UsagePoint', ns)
connectivity_nodes = root.findall('.//cim:ConnectivityNode', ns)
ac_line_segments = root.findall('.//cim:ACLineSegment', ns)
service_locations = root.findall('.//cim:ServiceLocation', ns)
fuses = root.findall('.//cim:Fuse', ns)
distributed_generators = root.findall('.//cim:DistributedGenerator', ns)

for terminal in terminals:
    terminal_id = terminal.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    G.add_node(terminal_id, label='Terminal')


# # Procesar terminales para crear conexiones directas
# for terminal in terminals:
#     terminal_id = terminal.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
#     connectivity_node = terminal.find('cim:Terminal.ConnectivityNode', ns).get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
#     conducting_equipment = terminal.find('cim:Terminal.ConductingEquipment', ns).get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
    
#     if connectivity_node not in direct_connections:
#         direct_connections[connectivity_node] = []
#     direct_connections[connectivity_node].append(conducting_equipment)

# # Añadir nodos y aristas directas al grafo
# for connectivity_node, equipments in direct_connections.items():
#     for i in range(len(equipments)):
#         for j in range(i + 1, len(equipments)):
#             G.add_node(equipments[i], label='Equipment')
#             G.add_node(equipments[j], label='Equipment')
#             G.add_edge(equipments[i], equipments[j])

for usage_point in usage_points:
    usage_point_id = usage_point.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    service_location = usage_point.find('cim:UsagePoint.ServiceLocation', ns).get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
    
    G.add_node(usage_point_id, label='UsagePoint')
    G.add_node(service_location, label='ServiceLocation')
    
    G.add_edge(usage_point_id, service_location)

for service_location in service_locations:
    service_location_id = service_location.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    terminal_element = service_location.find('sedms:ServiceLocation.Terminal', ns)
    
    if terminal_element is not None:
        terminal = terminal_element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
        
        G.add_node(service_location_id, label='ServiceLocation')
        
        G.add_edge(service_location_id, terminal)

for ac_line_segment in ac_line_segments:
    ac_line_segment_id = ac_line_segment.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    G.add_node(ac_line_segment_id, label='ACLineSegment')

# Añadir fusibles al grafo
for fuse in fuses:
    fuse_id = fuse.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    terminal_element = fuse.find('cim:Equipment.Terminal', ns)
    
    G.add_node(fuse_id, label='Fuse')
    if terminal_element is not None:
        terminal = terminal_element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
        G.add_edge(fuse_id, terminal)

# Añadir generadores distribuidos al grafo
for generator in distributed_generators:
    generator_id = generator.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    terminal_element = generator.find('cim:Equipment.Terminal', ns)
    
    G.add_node(generator_id, label='DistributedGenerator')
    if terminal_element is not None:
        terminal = terminal_element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
        G.add_edge(generator_id, terminal)

# Eliminar nodos sin etiqueta
nodes_to_remove = [node for node, data in G.nodes(data=True) if 'label' not in data or not data['label']]
G.remove_nodes_from(nodes_to_remove)

# Crear una red interactiva usando pyvis
net = Network(notebook=True, cdn_resources='in_line')
net.from_nx(G)

# Guardar y mostrar la red
net.show('network.html')