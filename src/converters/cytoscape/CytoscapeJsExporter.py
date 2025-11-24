import json
import logging
import os
from pathlib import Path
import aiofiles
from typing import Dict, List, Any, Optional
from .CytoscapeExporter import CytoscapeExporter
from topology import Network, Substation, Bus, Load, Generator, Line, Switch, TwoWindingsTransformer, ThreeWindingsTransformer, DanglingLine, UsagePointLocation, Element
from base_exporter import Exporter


class CytoscapeJsExporter(CytoscapeExporter):
    """Cytoscape JS Exporter for exporting topology to Cytoscape.js format."""

    @classmethod
    def name(cls) -> str:
        return "CytoscapeJsExporter"

    def required_parameters(self) -> dict:
        return {
            "output_file": None,
            "system": "default_system",
            "include_metadata": False,
            "layout": "force_directed"  # Options: hierarchical, circular, grid, force_directed
        }

    async def _export_topology_impl(self, network: Network, logger: logging.Logger, params: dict = None) -> dict[str, Path]:
        """Export topology to Cytoscape JS (.json) format."""
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

            logger.info(f"Starting Cytoscape JS export to '{output_file}' with {layout_type} layout")
            
            # Generate cytoscape elements from network
            elements = self._generate_cytoscape_elements(sub_topology, system)
            
            # Apply layout to position elements
            elements = self._apply_layout(elements, layout_type, logger)
            
            # Convert to JS format
            js_data = self._convert_to_js_format(elements, sub_topology, system, include_metadata)

            # Save JS data
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(js_data, indent=2, ensure_ascii=False))

            logger.info(f"Cytoscape JS file saved to: {output_file}")

            result[sub_topology.id] = Path(output_file)
        return result

    def _convert_to_js_format(self, elements: Dict[str, Dict], network: Network, system: str, include_metadata: bool) -> Any:
        """Convert elements to Cytoscape.js format."""
        js_elements = []
        nodes = []
        edges = []
        # Convert each element to Cytoscape.js format
        for element_id, element in elements.items():
            element_data = element["data"]
            
            # Create Cytoscape.js element structure
            js_element = {
                "data": {
                    "id": element_data["id"],
                    "name": element_data.get("name", element_data["id"]),
                    "type": element_data.get("type", "unknown"),
                    "powsyblId": element_data.get("powsyblId", element_data["id"]),
                    "system": element_data.get("system", system),
                    "network": element_data.get("network", "")
                }
            }
            
            # Add parent relationship if exists
            if element_data.get("parent"):
                js_element["data"]["parent"] = element_data["parent"]
            
            # Add source/target for edges
            if "source" in element_data and "target" in element_data:
                js_element["data"]["source"] = element_data["source"]
                js_element["data"]["target"] = element_data["target"]
            
            # Add element-specific attributes
            if element_data.get("type") == "BUS":
                if element_data.get("nominalVoltage"):
                    js_element["data"]["nominalVoltage"] = element_data["nominalVoltage"]
            
            elif element_data.get("type") == "LOAD":
                if element_data.get("ratedPower"):
                    js_element["data"]["ratedPower"] = element_data["ratedPower"]
            
            elif element_data.get("type") == "GENERATOR":
                if element_data.get("maxPower"):
                    js_element["data"]["maxPower"] = element_data["maxPower"]
            
            elif element_data.get("type") == "LINE":
                line_attrs = ["length", "currentLimit", "r", "x", "nominalVoltage", "typeLine"]
                for attr in line_attrs:
                    if element_data.get(attr) is not None:
                        js_element["data"][attr] = element_data[attr]
            
            elif "TRANSFORMER" in element_data.get("type", ""):
                if element_data.get("ratedApparentPower"):
                    js_element["data"]["ratedApparentPower"] = element_data["ratedApparentPower"]
            
            elif element_data.get("type") == "SWITCH":
                if element_data.get("open") is not None:
                    js_element["data"]["open"] = element_data["open"]
            
            # Add position data if coordinates are available (from layout or original coords)
            lat = element_data.get("lat")
            lon = element_data.get("lon")
            
            # Use layout coordinates if available, with better handling
            if lat is not None and lon is not None and lat >= 0.001 and lon >= 0.001:
                # Check if this is a calculated layout position or original geographic coordinate
                is_layout_position = abs(lat) < 1000 and abs(lon) < 1000  # Layout positions are typically smaller
                
                if not is_layout_position:
                    # Direct use of layout coordinates
                    js_element["position"] = {
                        "x": float(lon),
                        "y": float(lat)
                    }
                else:
                    # Geographic coordinates - scale appropriately
                    js_element["position"] = {
                        "x": lon * 100000,  # Scale for better visualization
                        "y": -lat * 100000  # Invert Y axis for proper orientation
                    }
                
                # Always store original coordinates in data
                js_element["data"]["lat"] = lat
                js_element["data"]["lon"] = lon
                js_element["data"]["hasPosition"] = True
            else:
                # No position data available
                if "parent" in element_data and element_data["parent"]!=None and elements[element_data["parent"]] != None and elements[element_data["parent"]]["data"]["lat"]>0.001:
                    # Inherit position from parent if available
                    js_element["position"] = {
                        "x": elements[element_data["parent"]]["data"]["lon"]*100000,
                        "y": elements[element_data["parent"]]["data"]["lat"]*100000
                    }
                    js_element["data"]["lat"] = elements[element_data["parent"]]["data"]["lat"]
                    js_element["data"]["lon"] = elements[element_data["parent"]]["data"]["lon"]
                    js_element["data"]["hasPosition"] = True
                else:
                    js_element["data"]["hasPosition"] = False

            # Add classes for styling
            js_element["classes"] = element_data.get("type", "").lower()
            
            js_elements.append(js_element)
        
        # If metadata is requested, wrap in container with metadata
        if include_metadata:
            node_count = len([e for e in js_elements if "source" not in e["data"]])
            edge_count = len([e for e in js_elements if "source" in e["data"]])
            positioned_nodes = len([e for e in js_elements if "position" in e])
            
            metadata = {
                "name": network.name or "Network Topology",
                "description": f"Power system network exported from {system}",
                "nodeCount": node_count,
                "edgeCount": edge_count,
                "system": system,
                "positionedNodes": positioned_nodes,
                "hasLayout": positioned_nodes > 0
            }
            
            # Add layout-specific information if positions are available
            if positioned_nodes > 0:
                # Calculate layout bounds
                x_coords = [e["position"]["x"] for e in js_elements if "position" in e]
                y_coords = [e["position"]["y"] for e in js_elements if "position" in e]
                
                if x_coords and y_coords:
                    metadata["layoutBounds"] = {
                        "minX": min(x_coords),
                        "maxX": max(x_coords),
                        "minY": min(y_coords),
                        "maxY": max(y_coords),
                        "width": max(x_coords) - min(x_coords),
                        "height": max(y_coords) - min(y_coords)
                    }
            
            result = {
                "format_version": "1.0",
                "generated_by": "TopologyAlchemy CytoscapeJsExporter",
                "target_cytoscapejs_version": "~3.26",
                "metadata": metadata,
                "elements": {
                    "nodes": [e for e in js_elements if "source" not in e["data"]],
                    "edges": [e for e in js_elements if "source" in e["data"]]
                }
            }
            return result
        else:
            return js_elements

