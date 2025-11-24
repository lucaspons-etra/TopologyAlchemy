import json
import logging
import os
from pathlib import Path
import aiofiles
import math
from typing import Dict, List, Any, Optional

from topology import Network, Substation, Bus, Load, Generator, Line, Switch, TwoWindingsTransformer, ThreeWindingsTransformer, DanglingLine, UsagePointLocation, Element
from base_exporter import Exporter


class CytoscapeExporter(Exporter):
    """Cytoscape Exporter for exporting topology to Cytoscape format."""

    @classmethod
    def name(cls) -> str:
        return "CytoscapeExporter"

    def required_parameters(self) -> dict:
        return {
            "output_file": None,
            "system": "default_system",
            "open_browser": False,  # CX format doesn't auto-open in browser
            "include_metadata": True,
            "layout": "None"  # Options: hierarchical, circular, grid, force_directed
        }

    async def _export_topology_impl(self, network: Network, logger: logging.Logger, params: dict = None) -> dict[str, Path]:
        """Export topology to Cytoscape Exchange (.cx) format."""
        output_file_elems = params.get("output_file").split(".")
        system = params.get("system")
        include_metadata = params.get("include_metadata")
        layout_type = params.get("layout")
        self.default_network = network.id
        result = {}

        for sub_topology in [network] + network.getElements("subTopologies"):
            if len(output_file_elems) > 1:
                output_file = ".".join(output_file_elems[:-1]) + f"_{sub_topology.id}." + output_file_elems[-1]
            else:
                output_file = f"{output_file_elems[0]}_{sub_topology.id}"

            logger.info(f"Starting Cytoscape CX export to '{output_file}' with {layout_type} layout")
            
            # Generate cytoscape elements from network
            elements = self._generate_cytoscape_elements(sub_topology, system)
            
            # Apply layout to position elements
            elements = self._apply_layout(elements, layout_type, logger)
            
            # Convert to CX format
            cx_data = self._convert_to_cx_format(elements, sub_topology, system, include_metadata)
            
            # Save CX data
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(cx_data, indent=2, ensure_ascii=False))
            
            logger.info(f"Cytoscape CX file saved to: {output_file}")

            result[sub_topology.id] = Path(output_file)
        return result

    def _generate_cytoscape_elements(self, network: Network, system: str) -> Dict[str, Dict]:
        """Generate cytoscape elements from Network topology (direct elements only, not subtopologies)."""
        elements = {}
        
        # Process only the current network (not subtopologies)
        # Add substations
        for substation in network.getElements("substations"):
            self._add_substation(elements, substation, system, network.id)
            
            # Add buses within substations
            for bus in substation.getElements("buses"):
                self._add_bus(elements, bus, system, network.id, substation.id)
                self._add_bus_connected_elements(elements, bus, system, network.id, substation.id)
            
            # Add transformers within substations
            for transformer in substation.getElements("twoWindingsTransformers"):
                self._add_two_windings_transformer(elements, transformer, system, network.id, substation.id)
            
            for transformer in substation.getElements("threeWindingsTransformers"):
                self._add_three_windings_transformer(elements, transformer, system, network.id, substation.id)
            
            # Add switches within substations
            for switch in substation.getElements("switches"):
                self._add_switch(elements, switch, system, network.id, substation.id)
            
            # Add lines within substations
            for line in substation.getElements("lines"):
                self._add_line(elements, line, system, network.id)
        
        # Add standalone buses (not in substations)
        for bus in network.getElements("buses"):
            self._add_bus(elements, bus, system, network.id, None)
            self._add_bus_connected_elements(elements, bus, system, network.id, None)
        
        # Add standalone lines
        for line in network.getElements("lines"):
            self._add_line(elements, line, system, network.id)
        
        # Add standalone switches
        for switch in network.getElements("switches"):
            self._add_switch(elements, switch, system, network.id, None)
        
        return elements

    def _create_prefixed_id(self, element_type: str, element_id: str, system: str) -> str:
        """Create a prefixed ID using system prefix if defined."""
        if system and system != "default_system":
            return f"{element_type}@{system}_{element_id}"
        else:
            return f"{element_type}@{element_id}"

    def _add_substation(self, elements: Dict, substation: Substation, system: str, network_id: str):
        """Add substation to cytoscape elements."""
        substation_id = self._create_prefixed_id("SUBSTATION", substation.id, system)
        coords = self._get_coordinates(substation)
        
        elements[substation_id] = {
            "data": {
                "id": substation_id,
                "name": substation.name or substation.id,
                "type": "SUBSTATION",
                "powsyblId": (f"{system}_{substation.id}" if network_id==self.default_network else f"{system}_{network_id}_{substation.id}" ) if system != "default_system" else substation.id,
                "system": system,
                "network": network_id,
                "lat": coords[1] if coords else 0,
                "lon": coords[0] if coords else 0,
                "fict": 0 if substation.name else 1
            }
        }

    def _add_bus(self, elements: Dict, bus: Bus, system: str, network_id: str, substation_id: Optional[str]):
        """Add bus to cytoscape elements."""
        bus_id = self._create_prefixed_id("BUS", bus.id, system)
        coords = self._get_coordinates(bus)
        
        elements[bus_id] = {
            "data": {
                "id": bus_id,
                "name": bus.name or bus.id,
                "type": "BUS",
                "powsyblId": (f"{system}_{bus.id}" if network_id==self.default_network else f"{system}_{network_id}_{bus.id}" ) if system != "default_system" else bus.id,
                "system": system,
                "network": network_id,
                "parent": self._create_prefixed_id("SUBSTATION", substation_id, system) if substation_id else None,
                "nominalVoltage": bus.voltageLevel.nominalV * 1000 if bus.voltageLevel else 0,  # kV to V
                "lat": coords[1] if coords else 0,
                "lon": coords[0] if coords else 0
            }
        }

    def _add_bus_connected_elements(self, elements: Dict, bus: Bus, system: str, network_id: str, substation_id: Optional[str]):
        """Add all elements connected to a bus."""
        bus_id = self._create_prefixed_id("BUS", bus.id, system)
        parent = self._create_prefixed_id("SUBSTATION", substation_id, system) if substation_id else None
        
        # Add loads
        for load in bus.getElements("loads"):
            load_id = self._create_prefixed_id("LOAD", load.id, system)
            line_id = self._create_prefixed_id("LOAD_LINE", load.id, system)
            coords = self._get_coordinates(load)
            
            elements[load_id] = {
                "data": {
                    "id": load_id,
                    "name": load.name or load.id,
                    "type": "LOAD",
                    "powsyblId": (f"{system}_{load.id}" if network_id==self.default_network else f"{system}_{network_id}_{load.id}" ) if system != "default_system" else load.id,
                    "system": system,
                    "network": network_id,
                    "parent": parent,
                    "ratedPower": getattr(load, 'p', 0),
                    "lat": coords[1] if coords else 0,
                    "lon": coords[0] if coords else 0
                }
            }
            
            elements[line_id] = {
                "data": {
                    "id": line_id,
                    "source": bus_id,
                    "target": load_id,
                    "type": "LOAD_LINE"
                }
            }
        
        # Add generators
        for generator in bus.getElements("generators"):
            generator_id = self._create_prefixed_id("GENERATOR", generator.id, system)
            line_id = self._create_prefixed_id("GENERATOR_LINE", generator.id, system)
            coords = self._get_coordinates(generator)
            
            elements[generator_id] = {
                "data": {
                    "id": generator_id,
                    "name": generator.name or generator.id,
                    "type": "GENERATOR",
                    "powsyblId": (f"{system}_{generator.id}" if network_id==self.default_network else f"{system}_{network_id}_{generator.id}" ) if system != "default_system" else  generator.id,
                    "system": system,
                    "network": network_id,
                    "parent": parent,
                    "maxPower": getattr(generator, 'maxP', 0),
                    "lat": coords[1] if coords else 0,
                    "lon": coords[0] if coords else 0
                }
            }
            
            elements[line_id] = {
                "data": {
                    "id": line_id,
                    "source": bus_id,
                    "target": generator_id,
                    "type": "GENERATOR_LINE"
                }
            }
        
        # Add dangling lines
        for dangling_line in bus.getElements("danglingLines"):
            dangling_line_id = self._create_prefixed_id("DANGLINGLINE", dangling_line.id, system)
            line_id = self._create_prefixed_id("DANGLINGLINE_LINE", dangling_line.id, system)
            coords = self._get_coordinates(dangling_line)
            
            elements[dangling_line_id] = {
                "data": {
                    "id": dangling_line_id,
                    "name": dangling_line.name or dangling_line.id,
                    "type": "DANGLINGLINE",
                    "powsyblId": (f"{system}_{dangling_line.id}" if network_id==self.default_network else f"{system}_{network_id}_{dangling_line.id}" ) if system != "default_system" else  dangling_line.id,
                    "system": system,
                    "network": network_id,
                    "parent": parent,
                    "lat": coords[1] if coords else 0,
                    "lon": coords[0] if coords else 0
                }
            }
            
            elements[line_id] = {
                "data": {
                    "id": line_id,
                    "source": bus_id,
                    "target": dangling_line_id,
                    "type": "DANGLINGLINE_LINE"
                }
            }
        
        # Add usage point locations
        for upl in bus.getElements("usagePointLocations"):
            upl_id = self._create_prefixed_id("USAGE_POINT_LOCATION", upl.id, system)
            line_id = self._create_prefixed_id("USAGE_POINT_LOCATION_LINE", upl.id, system)
            coords = self._get_coordinates(upl)
            
            elements[upl_id] = {
                "data": {
                    "id": upl_id,
                    "name": upl.name or upl.id,
                    "type": "USAGE_POINT_LOCATION",
                    "powsyblId": (f"{system}_{upl.id}" if network_id==self.default_network else f"{system}_{network_id}_{upl.id}" ) if system != "default_system" else  upl.id,
                    "system": system,
                    "network": network_id,
                    "parent": parent,
                    "lat": coords[1] if coords else 0,
                    "lon": coords[0] if coords else 0
                }
            }
            
            elements[line_id] = {
                "data": {
                    "id": line_id,
                    "source": bus_id,
                    "target": upl_id,
                    "type": "USAGE_POINT_LOCATION_LINE"
                }
            }

    def _add_two_windings_transformer(self, elements: Dict, transformer: TwoWindingsTransformer, system: str, network_id: str, substation_id: str):
        """Add two windings transformer to cytoscape elements."""
        transformer_id = self._create_prefixed_id("2WINDINGSTRANSFORMER", transformer.id, system)
        line1_id = self._create_prefixed_id("TRANSFORMER_LINE1", transformer.id, system)
        line2_id = self._create_prefixed_id("TRANSFORMER_LINE2", transformer.id, system)
        coords = self._get_coordinates(transformer)
        
        elements[transformer_id] = {
            "data": {
                "id": transformer_id,
                "name": transformer.name or transformer.id,
                "type": "2WINDINGSTRANSFORMER",
                "powsyblId": (f"{system}_{transformer.id}" if network_id==self.default_network else f"{system}_{network_id}_{transformer.id}" ) if system != "default_system" else  transformer.id,
                "system": system,
                "network": network_id,
                "parent": self._create_prefixed_id("SUBSTATION", substation_id, system),
                "ratedApparentPower": getattr(transformer, 'nominal', 0),
                "lat": coords[1] if coords else 0,
                "lon": coords[0] if coords else 0
            }
        }
        
        elements[line1_id] = {
            "data": {
                "id": line1_id,
                "source": self._create_prefixed_id("BUS", transformer.bus1.id, system),
                "target": transformer_id,
                "type": "TRANSFORMER_LINE"
            }
        }
        
        elements[line2_id] = {
            "data": {
                "id": line2_id,
                "source": self._create_prefixed_id("BUS", transformer.bus2.id, system),
                "target": transformer_id,
                "type": "TRANSFORMER_LINE"
            }
        }

    def _add_three_windings_transformer(self, elements: Dict, transformer: ThreeWindingsTransformer, system: str, network_id: str, substation_id: str):
        """Add three windings transformer to cytoscape elements."""
        transformer_id = self._create_prefixed_id("3WINDINGSTRANSFORMER", transformer.id, system)
        line1_id = self._create_prefixed_id("TRANSFORMER_LINE1", transformer.id, system)
        line2_id = self._create_prefixed_id("TRANSFORMER_LINE2", transformer.id, system)
        line3_id = self._create_prefixed_id("TRANSFORMER_LINE3", transformer.id, system)
        coords = self._get_coordinates(transformer)
        
        elements[transformer_id] = {
            "data": {
                "id": transformer_id,
                "name": transformer.name or transformer.id,
                "type": "3WINDINGSTRANSFORMER",
                "powsyblId": (f"{system}_{transformer.id}" if network_id==self.default_network else f"{system}_{network_id}_{transformer.id }" ) if system != "default_system" else  transformer.id,
                "system": system,
                "network": network_id,
                "parent": self._create_prefixed_id("SUBSTATION", substation_id, system),
                "lat": coords[1] if coords else 0,
                "lon": coords[0] if coords else 0
            }
        }
        
        elements[line1_id] = {
            "data": {
                "id": line1_id,
                "source": self._create_prefixed_id("BUS", transformer.bus1.id, system),
                "target": transformer_id,
                "type": "TRANSFORMER_LINE"
            }
        }
        
        elements[line2_id] = {
            "data": {
                "id": line2_id,
                "source": self._create_prefixed_id("BUS", transformer.bus2.id, system),
                "target": transformer_id,
                "type": "TRANSFORMER_LINE"
            }
        }
        
        elements[line3_id] = {
            "data": {
                "id": line3_id,
                "source": self._create_prefixed_id("BUS", transformer.bus3.id, system),
                "target": transformer_id,
                "type": "TRANSFORMER_LINE"
            }
        }

    def _add_switch(self, elements: Dict, switch: Switch, system: str, network_id: str, substation_id: Optional[str]):
        """Add switch to cytoscape elements."""
        switch_id = self._create_prefixed_id("SWITCH", switch.id, system)
        line1_id = self._create_prefixed_id("SWITCH_LINE1", switch.id, system)
        line2_id = self._create_prefixed_id("SWITCH_LINE2", switch.id, system)
        coords = self._get_coordinates(switch)
        
        elements[switch_id] = {
            "data": {
                "id": switch_id,
                "name": switch.name or switch.id,
                "type": "SWITCH",
                "powsyblId": (f"{system}_{switch.id}" if network_id==self.default_network else f"{system}_{network_id}_{switch.id}" ) if system != "default_system" else switch.id,
                "system": system,
                "network": network_id,
                "parent": self._create_prefixed_id("SUBSTATION", substation_id, system) if substation_id else None,
                "open": 0,  # Default to closed
                "lat": coords[1] if coords else 0,
                "lon": coords[0] if coords else 0
            }
        }
        
        elements[line1_id] = {
            "data": {
                "id": line1_id,
                "source": self._create_prefixed_id("BUS", switch.bus1.id, system),
                "target": switch_id,
                "type": "SWITCH_LINE"
            }
        }
        
        elements[line2_id] = {
            "data": {
                "id": line2_id,
                "source": self._create_prefixed_id("BUS", switch.bus2.id, system),
                "target": switch_id,
                "type": "SWITCH_LINE"
            }
        }

    def _add_line(self, elements: Dict, line: Line, system: str, network_id: str):
        """Add line to cytoscape elements."""
        line_id = self._create_prefixed_id("LINE", line.id, system)
        
        elements[line_id] = {
            "data": {
                "id": line_id,
                "name": line.name or line.id,
                "type": "LINE",
                "powsyblId": f"{system}_{line.id}" if system != "default_system" else line.id,
                "system": system,
                "network": network_id,
                "source": self._create_prefixed_id("BUS", line.bus1.id, system),
                "target": self._create_prefixed_id("BUS", line.bus2.id, system),
                "typeLine": f"LINE_{getattr(line, 'type', 'UNKNOWN')}",
                "length": getattr(line, 'length', 0),
                "currentLimit": getattr(line, 'currentLimit', None),
                "r": getattr(line, 'r', 0),
                "x": getattr(line, 'x', 0),
                "nominalVoltage": line.bus1.voltageLevel.nominalV * 1000 if line.bus1.voltageLevel else 0
            }
        }

    def _convert_to_cx_format(self, elements: Dict[str, Dict], network: Network, system: str, include_metadata: bool) -> List[Dict]:
        """Convert elements to Cytoscape Exchange (CX) format."""
        cx_data = []
        
        # Add metadata if requested
        if include_metadata:
            cx_data.append({
                "metaData": [
                    {"name": "nodes", "elementCount": len([e for e in elements.values() if "source" not in e["data"]])},
                    {"name": "edges", "elementCount": len([e for e in elements.values() if "source" in e["data"]])},
                    {"name": "networkAttributes", "elementCount": 3},
                    {"name": "nodeAttributes", "elementCount": 8},
                    {"name": "edgeAttributes", "elementCount": 3}
                ]
            })
        
        # Network attributes
        cx_data.append({
            "networkAttributes": [
                {"n": "name", "v": network.name or "Network Topology"},
                {"n": "description", "v": f"Power system network exported from {system}"},
                {"n": "version", "v": "1.0"}
            ]
        })
        
        # Separate nodes and edges
        nodes = []
        edges = []
        node_id_map = {}  # Map from string IDs to numeric IDs
        current_node_id = 0
        current_edge_id = 0
        
        # Process nodes first
        for element_id, element in elements.items():
            if "source" not in element["data"]:  # This is a node
                node_id_map[element["data"]["id"]] = current_node_id
                nodes.append({
                    "@id": current_node_id,
                    "n": element["data"]["name"],
                    "r": element["data"]["id"]  # Use 'r' for represents (original ID)
                })
                current_node_id += 1
        
        # Process edges
        for element_id, element in elements.items():
            if "source" in element["data"]:  # This is an edge
                source_id = node_id_map.get(element["data"]["source"])
                target_id = node_id_map.get(element["data"]["target"])
                
                if source_id is not None and target_id is not None:
                    edges.append({
                        "@id": current_edge_id,
                        "s": source_id,
                        "t": target_id,
                        "i": element["data"].get("type", "unknown")
                    })
                    current_edge_id += 1
        
        # Add nodes to CX
        if nodes:
            cx_data.append({"nodes": nodes})
        
        # Add edges to CX
        if edges:
            cx_data.append({"edges": edges})
        
        # Node attributes
        node_attributes = []
        
        for element_id, element in elements.items():
            if "source" not in element["data"]:  # This is a node
                node_numeric_id = node_id_map[element["data"]["id"]]
                data = element["data"]
                
                # Add various node attributes
                attributes_to_add = [
                    ("type", data.get("type")),
                    ("powsyblId", data.get("powsyblId")),
                    ("system", data.get("system")),
                    ("network", data.get("network")),
                    ("nominalVoltage", data.get("nominalVoltage")),
                    ("lat", data.get("lat")),
                    ("lon", data.get("lon")),
                    ("parent", data.get("parent"))
                ]
                
                for attr_name, attr_value in attributes_to_add:
                    if attr_value is not None:
                        node_attributes.append({
                            "po": node_numeric_id,
                            "n": attr_name,
                            "v": attr_value
                        })
        
        if node_attributes:
            cx_data.append({"nodeAttributes": node_attributes})
        
        # Edge attributes
        edge_attributes = []
        edge_idx = 0
        
        for element_id, element in elements.items():
            if "source" in element["data"]:  # This is an edge
                source_id = node_id_map.get(element["data"]["source"])
                target_id = node_id_map.get(element["data"]["target"])
                
                if source_id is not None and target_id is not None:
                    data = element["data"]
                    
                    # Add edge attributes
                    attributes_to_add = [
                        ("interaction", data.get("type", "unknown")),
                        ("length", data.get("length")),
                        ("currentLimit", data.get("currentLimit"))
                    ]
                    
                    for attr_name, attr_value in attributes_to_add:
                        if attr_value is not None:
                            edge_attributes.append({
                                "po": edge_idx,
                                "n": attr_name,
                                "v": attr_value
                            })
                    
                    edge_idx += 1
        
        if edge_attributes:
            cx_data.append({"edgeAttributes": edge_attributes})

        # Add position data for layout
        cartesian_layout = []
        for element_id, element in elements.items():
            if "source" not in element["data"]:  # This is a node
                node_numeric_id = node_id_map[element["data"]["id"]]
                x = element["data"].get("lon", 0)  # longitude as x
                y = element["data"].get("lat", 0)  # latitude as y
                if x != 0 and y != 0:
                    element["data"]["position"] = {"x": x, "y": y}
                
                # if x != 0 and y != 0:
                #     cartesian_layout.append({
                #         "node": node_numeric_id,
                #         "x": float(x),
                #         "y": float(y)
                #     })

        # if cartesian_layout:
        #     cx_data.append({"cartesianLayout": cartesian_layout})
        
        # Add status (required for CX format)
        cx_data.append({
            "status": [
                {"error": "", "success": True}
            ]
        })
        
        return cx_data

    def _apply_layout(self, elements: Dict[str, Dict], layout_type: str, logger: logging.Logger) -> Dict[str, Dict]:
        """Apply layout algorithm to position elements."""
        logger.info(f"Applying {layout_type} layout to {len(elements)} elements")
        
        # Separate nodes and edges
        nodes = {k: v for k, v in elements.items() if "source" not in v["data"]}
        edges = {k: v for k, v in elements.items() if "source" in v["data"]}
        
        # Apply layout based on type
        if layout_type == "hierarchical":
            positioned_nodes = self._apply_hierarchical_layout(nodes, edges)
        elif layout_type == "circular":
            positioned_nodes = self._apply_circular_layout(nodes)
        elif layout_type == "grid":
            positioned_nodes = self._apply_grid_layout(nodes)
        elif layout_type == "force_directed":
            positioned_nodes = self._apply_force_directed_layout(nodes, edges)
        else:
            return elements  # No layout applied
        
        # Update elements with new positions
        for node_id, position in positioned_nodes.items():
            if node_id in elements:
                elements[node_id]["data"]["lat"] = position["y"]
                elements[node_id]["data"]["lon"] = position["x"]
        
        logger.info(f"Layout applied successfully to {len(positioned_nodes)} nodes")
        return elements

    def _apply_hierarchical_layout(self, nodes: Dict, edges: Dict) -> Dict[str, Dict]:
        """Apply hierarchical layout based on element types."""
        positioned_nodes = {}
        
        # Group nodes by type
        node_groups = {}
        for node_id, node in nodes.items():
            node_type = node["data"]["type"]
            if node_type not in node_groups:
                node_groups[node_type] = []
            node_groups[node_type].append(node_id)
        
        # Define hierarchy levels and spacing
        hierarchy = {
            "SUBSTATION": {"level": 0, "spacing": 300},
            "BUS": {"level": 1, "spacing": 150},
            "GENERATOR": {"level": 2, "spacing": 100},
            "LOAD": {"level": 2, "spacing": 100},
            "2WINDINGSTRANSFORMER": {"level": 1.5, "spacing": 120},
            "3WINDINGSTRANSFORMER": {"level": 1.5, "spacing": 120},
            "SWITCH": {"level": 1.2, "spacing": 80},
            "LINE": {"level": 1.8, "spacing": 100},
            "DANGLINGLINE": {"level": 2.2, "spacing": 90},
            "USAGE_POINT_LOCATION": {"level": 2.5, "spacing": 80}
        }
        
        # Position nodes by hierarchy level
        level_counters = {}
        for node_type, info in hierarchy.items():
            if node_type in node_groups:
                level = info["level"]
                spacing = info["spacing"]
                
                if level not in level_counters:
                    level_counters[level] = 0
                
                for i, node_id in enumerate(node_groups[node_type]):
                    x = (i % 5) * spacing + (level_counters[level] * 50)
                    y = level * 200 + (i // 5) * 100
                    
                    positioned_nodes[node_id] = {"x": x, "y": y}
                
                level_counters[level] += len(node_groups[node_type])
        
        return positioned_nodes

    def _apply_circular_layout(self, nodes: Dict) -> Dict[str, Dict]:
        """Apply circular layout positioning nodes in concentric circles."""
        positioned_nodes = {}
        node_list = list(nodes.keys())
        node_count = len(node_list)
        
        if node_count == 0:
            return positioned_nodes
        
        # Group nodes by type for different circle radii
        node_groups = {}
        for node_id, node in nodes.items():
            node_type = node["data"]["type"]
            if node_type not in node_groups:
                node_groups[node_type] = []
            node_groups[node_type].append(node_id)
        
        # Define circle radii for different types
        type_radii = {
            "SUBSTATION": 100,
            "BUS": 200,
            "GENERATOR": 300,
            "LOAD": 350,
            "2WINDINGSTRANSFORMER": 250,
            "3WINDINGSTRANSFORMER": 250,
            "SWITCH": 180,
            "LINE": 280,
            "DANGLINGLINE": 320,
            "USAGE_POINT_LOCATION": 380
        }
        
        center_x, center_y = 0, 0
        
        for node_type, type_nodes in node_groups.items():
            radius = type_radii.get(node_type, 300)
            angle_step = 2 * math.pi / len(type_nodes) if len(type_nodes) > 0 else 0
            
            for i, node_id in enumerate(type_nodes):
                angle = i * angle_step
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                
                positioned_nodes[node_id] = {"x": x, "y": y}
        
        return positioned_nodes

    def _apply_grid_layout(self, nodes: Dict) -> Dict[str, Dict]:
        """Apply grid layout positioning nodes in a regular grid."""
        positioned_nodes = {}
        node_list = list(nodes.keys())
        node_count = len(node_list)
        
        if node_count == 0:
            return positioned_nodes
        
        # Calculate grid dimensions
        cols = math.ceil(math.sqrt(node_count))
        rows = math.ceil(node_count / cols)
        
        spacing_x = 150
        spacing_y = 150
        
        for i, node_id in enumerate(node_list):
            row = i // cols
            col = i % cols
            
            x = col * spacing_x
            y = row * spacing_y
            
            positioned_nodes[node_id] = {"x": x, "y": y}
        
        return positioned_nodes

    def _apply_force_directed_layout(self, nodes: Dict, edges: Dict) -> Dict[str, Dict]:
        """Apply simple force-directed layout algorithm."""
        positioned_nodes = {}
        node_list = list(nodes.keys())
        node_count = len(node_list)
        
        if node_count == 0:
            return positioned_nodes
        
        # Initialize random positions
        import random
        positions = {}
        for node_id in node_list:
            positions[node_id] = {
                "x": random.uniform(-200, 200),
                "y": random.uniform(-200, 200)
            }
        
        # Build adjacency list
        adjacency = {node_id: [] for node_id in node_list}
        for edge in edges.values():
            source = edge["data"]["source"]
            target = edge["data"]["target"]
            if source in adjacency and target in adjacency:
                adjacency[source].append(target)
                adjacency[target].append(source)
        
        # Force-directed algorithm parameters
        iterations = 50
        spring_length = 100
        spring_strength = 0.1
        repulsion_strength = 1000
        damping = 0.9
        
        for iteration in range(iterations):
            forces = {node_id: {"x": 0, "y": 0} for node_id in node_list}
            
            # Calculate repulsive forces
            for i, node1 in enumerate(node_list):
                for j, node2 in enumerate(node_list):
                    if i != j:
                        dx = positions[node1]["x"] - positions[node2]["x"]
                        dy = positions[node1]["y"] - positions[node2]["y"]
                        distance = math.sqrt(dx*dx + dy*dy) or 1
                        
                        force = repulsion_strength / (distance * distance)
                        forces[node1]["x"] += force * dx / distance
                        forces[node1]["y"] += force * dy / distance
            
            # Calculate attractive forces (springs)
            for node1 in node_list:
                for node2 in adjacency[node1]:
                    dx = positions[node2]["x"] - positions[node1]["x"]
                    dy = positions[node2]["y"] - positions[node1]["y"]
                    distance = math.sqrt(dx*dx + dy*dy) or 1
                    
                    force = spring_strength * (distance - spring_length)
                    forces[node1]["x"] += force * dx / distance
                    forces[node1]["y"] += force * dy / distance
            
            # Apply forces with damping
            for node_id in node_list:
                positions[node_id]["x"] += forces[node_id]["x"] * damping
                positions[node_id]["y"] += forces[node_id]["y"] * damping
        
        return positions

    def _get_coordinates(self, element: Element) -> Optional[List[float]]:
        """Extract coordinates from element if available."""
        if hasattr(element, 'coords') and element.coords:
            return element.coords
        if hasattr(element, 'geometry') and element.geometry:
            if hasattr(element.geometry, 'coordinates'):
                return element.geometry.coordinates
        return None