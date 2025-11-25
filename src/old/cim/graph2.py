from lxml import etree as ET
import networkx as nx
from pyvis.network import Network

# Parsear el archivo RDF
#rdf_file = '/home/etraid/prj/topologyAlchemy/tests/data/slovenia/elikan.rdf'
rdf_file = '/home/etraid/prj/topologyAlchemy/tests/data/slovenia/NNO_STARA_VAS_20_0_4__G_319_ELC2040554_2023-06-13-10-57.xml'
tree = ET.parse(rdf_file)
root = tree.getroot()

# Espacios de nombres
ns = {
    'cim': 'http://iec.ch/TC57/2013/CIM-schema-cim16#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'sedms': 'http://www.schneider-electric-dms.com/CIM16v33/2017/extension#'
}

# Crear un grafo dirigido
G = nx.DiGraph()

def get_name(element):
    name_element = element.find('cim:IdentifiedObject.name', namespaces=ns)
    return element.tag.split('}')[1] + ":" + name_element.text if name_element is not None else element.tag.split('}')[1] + ":" + element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')

# Extraer elementos
terminals = root.xpath('.//cim:Terminal', namespaces=ns)
usage_points = root.xpath('.//cim:UsagePoint', namespaces=ns)
connectivity_nodes = root.xpath('.//cim:ConnectivityNode', namespaces=ns)
ac_line_segments = root.xpath('.//cim:ACLineSegment', namespaces=ns)
service_locations = root.xpath('.//cim:ServiceLocation', namespaces=ns)
fuses = root.xpath('.//cim:Fuse', namespaces=ns)
regulating_controls = root.xpath('.//cim:RegulatingControl', namespaces=ns)
distributed_generators = root.xpath('.//cim:DistributedGenerator', namespaces=ns)

# Diccionario para almacenar las conexiones de nodos de conectividad
connectivity_dict = {}
conducting_equipment_dict = {}
composite_switch_dict = {}

# Añadir ConductingEquipment al grafo y crear diccionario de conectividad
for terminal in terminals:
    terminal_id = terminal.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    connectivity_node = terminal.find('cim:Terminal.ConnectivityNode', namespaces=ns).get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
    conducting_equipment = terminal.find('cim:Terminal.ConductingEquipment', namespaces=ns).get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
    
    if conducting_equipment not in conducting_equipment_dict:
        conducting_equipment_dict[conducting_equipment] = []
    conducting_equipment_dict[conducting_equipment].append(terminal_id)
    
    if connectivity_node not in connectivity_dict:
        connectivity_dict[connectivity_node] = []
    connectivity_dict[connectivity_node].append(conducting_equipment)
    
    # Añadir terminales al grafo
    G.add_node(terminal_id, label=get_name(terminal))
    G.add_edge(conducting_equipment, terminal_id)
    G.add_edge(terminal_id, connectivity_node)

# Añadir ConnectivityNodes al grafo
for connectivity_node in connectivity_nodes:
    connectivity_node_id = connectivity_node.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    G.add_node(connectivity_node_id, label=get_name(connectivity_node))

# Añadir ConductingEquipment al grafo
for conducting_equipment in conducting_equipment_dict.keys():
    G.add_node(conducting_equipment, label=get_name(root.xpath(f'.//*[@rdf:ID="{conducting_equipment}"]', namespaces=ns)[0]))

# Conectar ConductingEquipment que comparten el mismo nodo de conectividad
for equipments in connectivity_dict.values():
    for i in range(len(equipments)):
        for j in range(i + 1, len(equipments)):
            G.add_edge(equipments[i], equipments[j])

# Añadir puntos de uso y ubicaciones de servicio al grafo
for usage_point in usage_points:
    usage_point_id = usage_point.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    service_location_id = usage_point.find('cim:UsagePoint.ServiceLocation', namespaces=ns).get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
    usage_point_name = get_name(usage_point)
    
    G.add_node(usage_point_id, label=usage_point_name)
    G.add_node(service_location_id, label=service_location_id)  # Placeholder label
    
    G.add_edge(usage_point_id, service_location_id)

for service_location in service_locations:
    service_location_id = service_location.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    terminal_element = service_location.find('sedms:ServiceLocation.Terminal', namespaces=ns)
    service_location_name = get_name(service_location)
    
    if terminal_element is not None:
        terminal = terminal_element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
        conducting_equipment = root.xpath(f'.//*[@rdf:ID="{terminal}"]/cim:Terminal.ConductingEquipment', namespaces=ns)
        if conducting_equipment:
            conducting_equipment_id = conducting_equipment[0].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
            G.add_node(service_location_id, label=service_location_name)
            G.add_edge(service_location_id, conducting_equipment_id)

for ac_line_segment in ac_line_segments:
    ac_line_segment_id = ac_line_segment.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    ac_line_segment_name = get_name(ac_line_segment)
    G.add_node(ac_line_segment_id, label=ac_line_segment_name)

# Añadir fusibles al grafo
for fuse in fuses:
    fuse_id = fuse.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    terminal_element = fuse.find('cim:Equipment.Terminal', namespaces=ns)
    fuse_name = get_name(fuse)
    
    G.add_node(fuse_id, label=fuse_name)
    if terminal_element is not None:
        terminal = terminal_element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
        conducting_equipment = root.xpath(f'.//*[@rdf:ID="{terminal}"]/cim:Terminal.ConductingEquipment', namespaces=ns)
        if conducting_equipment:
            conducting_equipment_id = conducting_equipment[0].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
            G.add_edge(fuse_id, conducting_equipment_id)

# Añadir controles reguladores al grafo
for regulating_control in regulating_controls:
    regulating_control_id = regulating_control.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    regulating_control_name = get_name(regulating_control)
    G.add_node(regulating_control_id, label=regulating_control_name)

# Añadir generadores distribuidos al grafo
for generator in distributed_generators:
    generator_id = generator.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
    terminal_element = generator.find('cim:Equipment.Terminal', namespaces=ns)
    generator_name = get_name(generator)
    
    G.add_node(generator_id, label=generator_name)
    if terminal_element is not None:
        terminal = terminal_element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
        conducting_equipment = root.xpath(f'.//*[@rdf:ID="{terminal}"]/cim:Terminal.ConductingEquipment', namespaces=ns)
        if conducting_equipment:
            conducting_equipment_id = conducting_equipment[0].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource').replace('#', '')
            G.add_edge(generator_id, conducting_equipment_id)

# Crear una visualización interactiva con pyvis
net = Network(notebook=True)
net.from_nx(G)

# Añadir evento de clic para imprimir el nombre del elemento
for node in net.nodes:
    node['title'] = node['label']
    node['onclick'] = f"console.log('{node['label']}')"

# Guardar y mostrar la visualización
net.show('graph.html')