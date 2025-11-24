import logging as logging
import pandapower as pp
import pandas as pd
from typing import Dict, Set, List, Tuple
from base_importer import Importer
from topology import Network, Substation, VoltageLevel, Bus, Load, Generator, Line, Switch, TwoWindingsTransformer

class PandapowerImporter(Importer):

    @classmethod
    def name(cls) -> str:
        return "PandapowerImporter"

    def required_parameters(self) -> dict:
        return {
            "input_file": None,
            "system_id": None,
            "network_id": None
        }
        
    async def _import_topology_impl(self, logger: logging.Logger, params: dict = {}) -> Network:
        """Import pandapower network and convert to topology Network format.
        
        Converts all pandapower elements:
        - Buses -> Bus objects with voltage levels
        - Loads -> Load objects 
        - Generators (gen, sgen, ext_grid) -> Generator objects
        - Lines -> Line objects
        - Transformers -> TwoWindingsTransformer objects
        - Switches -> Switch objects
        
        Infers substations from transformer connections and voltage grouping.
        """
        input_file = params.get("input_file")
        system_id = params.get("system_id")
        network_id = params.get("network_id")

        # Load the pandapower network from JSON file
        pandapower_net = pp.from_json(input_file)
        logger.info(f"Loaded pandapower network from: {input_file}")
        
        # Create topology Network
        topology = Network(system_id, network_id)
        
        # Track created voltage levels and substations
        voltage_levels: Dict[float, VoltageLevel] = {}
        substations: Dict[str, Substation] = {}
        buses_dict: Dict[int, Bus] = {}
        bus_to_substation: Dict[int, str] = {}  # Maps bus index to substation ID
        
        # Step 1: Create voltage levels based on unique nominal voltages
        self._create_voltage_levels(pandapower_net, topology, voltage_levels, logger)
        
        # Step 2: Infer substations from transformers and voltage grouping
        self._infer_substations(pandapower_net, topology, substations, bus_to_substation, logger)
        
        # Step 3: Create buses
        self._create_buses(pandapower_net, topology, voltage_levels, substations, buses_dict, bus_to_substation, logger)
        
        # Step 4: Create loads
        self._create_loads(pandapower_net, buses_dict, logger)
        
        # Step 5: Create generators (including sgen and ext_grid)
        self._create_generators(pandapower_net, buses_dict, logger)
        
        # Step 6: Create lines
        self._create_lines(pandapower_net, topology, buses_dict, logger)
        
        # Step 7: Create transformers
        self._create_transformers(pandapower_net, substations, buses_dict, logger)
        
        # Step 8: Create switches
        self._create_switches(pandapower_net, topology, buses_dict, logger)
        
        logger.info(f"Imported topology from Pandapower file: {input_file}")
        logger.info(f"Created {len(buses_dict)} buses, {len(substations)} substations, {len(voltage_levels)} voltage levels")
        
        return topology
    
    def _create_voltage_levels(self, pp_net, topology: Network, voltage_levels: Dict[float, VoltageLevel], logger):
        """Create voltage levels based on unique nominal voltages in the network."""
        if 'bus' not in pp_net or pp_net.bus.empty:
            logger.warning("No buses found in pandapower network")
            return
            
        unique_voltages = pp_net.bus['vn_kv'].unique()
        
        for vn_kv in unique_voltages:
            if pd.isna(vn_kv):
                continue
                
            # Determine voltage level type
            if vn_kv >= 100:
                vl_type = 'HV'  # High Voltage
            elif vn_kv >= 1:
                vl_type = 'MV'  # Medium Voltage  
            else:
                vl_type = 'LV'  # Low Voltage
                
            vl_id = f"VL_{vn_kv}kV"
            vl_name = f"Voltage Level {vn_kv} kV"
            
            voltage_level = topology.addVoltageLevel(vl_id, vl_name, vn_kv, vl_type)
            voltage_levels[vn_kv] = voltage_level
            logger.debug(f"Created voltage level: {vl_id} ({vl_type})")
    
    def _infer_substations(self, pp_net, topology: Network, substations: Dict[str, Substation], 
                          bus_to_substation: Dict[int, str], logger):
        """Infer substations from transformer connections and voltage grouping."""
        # Group buses by transformers - each transformer defines a substation
        if 'trafo' in pp_net and not pp_net.trafo.empty:
            for idx, trafo in pp_net.trafo.iterrows():
                if not trafo.get('in_service', True):
                    continue
                    
                hv_bus = int(trafo['hv_bus'])
                lv_bus = int(trafo['lv_bus'])
                
                # Create substation ID based on transformer
                sub_id = f"SUB_T{idx}_{hv_bus}_{lv_bus}"
                
                # Create substation if it doesn't exist
                if sub_id not in substations:
                    sub_name = f"Substation {sub_id}"
                    substation = topology.addSubstation(sub_id, sub_name)
                    substations[sub_id] = substation
                    logger.info(f"Created substation {sub_id}")
                
                # Map buses to this substation
                bus_to_substation[hv_bus] = sub_id
                bus_to_substation[lv_bus] = sub_id
                logger.debug(f"Added buses {hv_bus}, {lv_bus} to substation {sub_id}")
    
    def _create_buses(self, pp_net, topology: Network, voltage_levels: Dict[float, VoltageLevel],
                     substations: Dict[str, Substation], buses_dict: Dict[int, Bus], 
                     bus_to_substation: Dict[int, str], logger):
        """Create Bus objects from pandapower buses."""
        if 'bus' not in pp_net or pp_net.bus.empty:
            logger.warning("No buses found in pandapower network")
            return
            
        for idx, bus_data in pp_net.bus.iterrows():
            if not bus_data.get('in_service', True):
                continue
                
            bus_id = str(idx)
            bus_name = bus_data.get('name', f"Bus {idx}")
            vn_kv = bus_data['vn_kv']
            
            # Get voltage level
            voltage_level = voltage_levels.get(vn_kv)
            if voltage_level is None:
                logger.warning(f"No voltage level found for bus {idx} with {vn_kv} kV")
                continue
            
            # Determine if bus belongs to a substation
            if idx in bus_to_substation:
                sub_id = bus_to_substation[idx]
                substation = substations[sub_id]
                # Add bus to substation
                bus = substation.addBus(bus_id, bus_name, voltage_level)
                logger.debug(f"Created bus {bus_id} in substation {sub_id}")
            else:
                # Add bus directly to network
                bus = topology.addBus(bus_id, bus_name, voltage_level)
                logger.debug(f"Created standalone bus {bus_id}")
            
            buses_dict[idx] = bus
    
    def _create_loads(self, pp_net, buses_dict: Dict[int, Bus], logger):
        """Create Load objects from pandapower loads."""
        if 'load' not in pp_net or pp_net.load.empty:
            logger.info("No loads found in pandapower network")
            return
            
        load_count = 0
        for idx, load_data in pp_net.load.iterrows():
            if not load_data.get('in_service', True):
                continue
                
            bus_idx = int(load_data['bus'])
            if bus_idx not in buses_dict:
                logger.warning(f"Bus {bus_idx} not found for load {idx}")
                continue
                
            bus = buses_dict[bus_idx]
            load_id = str(idx)
            load_name = load_data.get('name', f"Load {idx}")
            p_mw = load_data.get('p_mw', 0.0)
            q_mvar = load_data.get('q_mvar', 0.0)
            load_type = load_data.get('type', 'wye')
            
            bus.addLoad(load_id, load_name, p=p_mw, q=q_mvar, type=load_type)
            load_count += 1
            
        logger.info(f"Created {load_count} loads")
    
    def _create_generators(self, pp_net, buses_dict: Dict[int, Bus], logger):
        """Create Generator objects from pandapower generators (gen, sgen, ext_grid)."""
        gen_count = 0
        
        # Create standard generators
        gen_count += self._create_standard_generators(pp_net, buses_dict, logger)
        
        # Create static generators (renewable, etc.)
        gen_count += self._create_static_generators(pp_net, buses_dict, logger)
        
        # Create external grids (slack buses)
        gen_count += self._create_external_grids(pp_net, buses_dict, logger)
                
        logger.info(f"Created {gen_count} generators")
    
    def _create_standard_generators(self, pp_net, buses_dict: Dict[int, Bus], logger):
        """Create standard generators from 'gen' table."""
        gen_count = 0
        if 'gen' in pp_net and not pp_net.gen.empty:
            for idx, gen_data in pp_net.gen.iterrows():
                if not gen_data.get('in_service', True):
                    continue
                    
                bus_idx = int(gen_data['bus'])
                if bus_idx not in buses_dict:
                    logger.warning(f"Bus {bus_idx} not found for generator {idx}")
                    continue
                    
                bus = buses_dict[bus_idx]
                gen_id = f"GEN_{idx}"
                gen_name = gen_data.get('name', f"Generator {idx}")
                
                p_mw = gen_data.get('p_mw', 0.0)
                vm_pu = gen_data.get('vm_pu', 1.0)
                min_p_mw = gen_data.get('min_p_mw', 0.0)
                max_p_mw = gen_data.get('max_p_mw', p_mw)
                
                bus.addMvGenerator(gen_id, gen_name, minP=min_p_mw, maxP=max_p_mw, 
                                 targetP=p_mw, targetV=vm_pu, controllable=True)
                gen_count += 1
        return gen_count
    
    def _create_static_generators(self, pp_net, buses_dict: Dict[int, Bus], logger):
        """Create static generators from 'sgen' table."""
        gen_count = 0
        if 'sgen' in pp_net and not pp_net.sgen.empty:
            for idx, sgen_data in pp_net.sgen.iterrows():
                if not sgen_data.get('in_service', True):
                    continue
                    
                bus_idx = int(sgen_data['bus'])
                if bus_idx not in buses_dict:
                    logger.warning(f"Bus {bus_idx} not found for static generator {idx}")
                    continue
                    
                bus = buses_dict[bus_idx]
                sgen_id = f"SGEN_{idx}"
                sgen_name = sgen_data.get('name', f"Static Generator {idx}")
                
                p_mw = sgen_data.get('p_mw', 0.0)
                q_mvar = sgen_data.get('q_mvar', 0.0)
                
                bus.addMvGenerator(sgen_id, sgen_name, targetP=p_mw, targetQ=q_mvar,
                                 controllable=False, coords=None)
                gen_count += 1
        return gen_count
    
    def _create_external_grids(self, pp_net, buses_dict: Dict[int, Bus], logger):
        """Create external grids from 'ext_grid' table.""" 
        gen_count = 0
        if 'ext_grid' in pp_net and not pp_net.ext_grid.empty:
            for idx, ext_grid_data in pp_net.ext_grid.iterrows():
                if not ext_grid_data.get('in_service', True):
                    continue
                    
                bus_idx = int(ext_grid_data['bus'])
                if bus_idx not in buses_dict:
                    logger.warning(f"Bus {bus_idx} not found for external grid {idx}")
                    continue
                    
                bus = buses_dict[bus_idx]
                ext_grid_id = f"EXT_GRID_{idx}"
                ext_grid_name = ext_grid_data.get('name', f"External Grid {idx}")
                
                vm_pu = ext_grid_data.get('vm_pu', 1.0)
                
                bus.addMvGenerator(ext_grid_id, ext_grid_name, targetV=vm_pu,
                                 controllable=True, coords=None)
                gen_count += 1
        return gen_count
    
    def _create_lines(self, pp_net, topology: Network, buses_dict: Dict[int, Bus], logger):
        """Create Line objects from pandapower lines."""
        if 'line' not in pp_net or pp_net.line.empty:
            logger.info("No lines found in pandapower network")
            return
            
        line_count = 0
        for idx, line_data in pp_net.line.iterrows():
            if not line_data.get('in_service', True):
                continue
                
            from_bus_idx = int(line_data['from_bus'])
            to_bus_idx = int(line_data['to_bus'])
            
            if from_bus_idx not in buses_dict or to_bus_idx not in buses_dict:
                logger.warning(f"Buses not found for line {idx}: {from_bus_idx} -> {to_bus_idx}")
                continue
                
            from_bus = buses_dict[from_bus_idx]
            to_bus = buses_dict[to_bus_idx]
            
            line_id = str(idx)
            line_name = line_data.get('name', f"Line {idx}")
            
            # Line parameters
            length_km = line_data.get('length_km', 0.0)
            r_ohm_per_km = line_data.get('r_ohm_per_km', 0.0)
            x_ohm_per_km = line_data.get('x_ohm_per_km', 0.0)
            c_nf_per_km = line_data.get('c_nf_per_km', 0.0)
            g_us_per_km = line_data.get('g_us_per_km', 0.0)
            max_i_ka = line_data.get('max_i_ka', 0.0)
            
            # Calculate total impedances
            r_total = r_ohm_per_km * length_km / 1000  # Convert to per unit or appropriate scale
            x_total = x_ohm_per_km * length_km / 1000
            g_total = g_us_per_km * length_km / 1000000  # Convert microsiemens
            b_total = c_nf_per_km * length_km / 1000000  # Convert nanofarads
            
            topology.addLine(line_id, line_name, from_bus, to_bus,
                           r=r_total, x=x_total, g1=g_total/2, b1=b_total/2,
                           g2=g_total/2, b2=b_total/2, currentLimit=max_i_ka,
                           length=length_km)
            line_count += 1
            
        logger.info(f"Created {line_count} lines")
    
    def _create_transformers(self, pp_net, substations: Dict[str, Substation], buses_dict: Dict[int, Bus], logger):
        """Create TwoWindingsTransformer objects from pandapower transformers."""
        if 'trafo' not in pp_net or pp_net.trafo.empty:
            logger.info("No transformers found in pandapower network")
            return
            
        trafo_count = 0
        for idx, trafo_data in pp_net.trafo.iterrows():
            if not trafo_data.get('in_service', True):
                continue
                
            transformer = self._create_single_transformer(idx, trafo_data, substations, buses_dict, logger)
            if transformer:
                trafo_count += 1
                
        logger.info(f"Created {trafo_count} transformers")
    
    def _create_single_transformer(self, idx, trafo_data, substations: Dict[str, Substation], 
                                   buses_dict: Dict[int, Bus], logger):
        """Create a single transformer from pandapower data."""
        hv_bus_idx = int(trafo_data['hv_bus'])
        lv_bus_idx = int(trafo_data['lv_bus'])
        
        if hv_bus_idx not in buses_dict or lv_bus_idx not in buses_dict:
            logger.warning(f"Buses not found for transformer {idx}: {hv_bus_idx} -> {lv_bus_idx}")
            return None
            
        hv_bus = buses_dict[hv_bus_idx]
        lv_bus = buses_dict[lv_bus_idx]
        
        # Find or create substation
        substation = self._get_or_create_substation(idx, hv_bus_idx, lv_bus_idx, substations, hv_bus)
        
        trafo_id = str(idx)
        trafo_name = trafo_data.get('name', f"Transformer {idx}")
        
        # Calculate transformer impedances
        impedances = self._calculate_transformer_impedances(trafo_data)
        
        return substation.addTransformer(trafo_id, trafo_name, hv_bus, lv_bus, **impedances)
    
    def _get_or_create_substation(self, idx, hv_bus_idx, lv_bus_idx, substations, hv_bus):
        """Get existing substation or create new one for transformer."""
        sub_id = f"SUB_T{idx}_{hv_bus_idx}_{lv_bus_idx}"
        if sub_id in substations:
            return substations[sub_id]
        
        # Create a new substation for this transformer
        sub_name = f"Substation T{idx}"
        if substations:
            parent_network = list(substations.values())[0].parent
        else:
            parent_network = hv_bus.parent
        substation = parent_network.addSubstation(sub_id, sub_name)
        substations[sub_id] = substation
        return substation
    
    def _calculate_transformer_impedances(self, trafo_data):
        """Calculate transformer impedances from pandapower parameters."""
        sn_mva = trafo_data.get('sn_mva', 1.0)
        vk_percent = trafo_data.get('vk_percent', 0.0)
        vkr_percent = trafo_data.get('vkr_percent', 0.0)
        pfe_kw = trafo_data.get('pfe_kw', 0.0)
        i0_percent = trafo_data.get('i0_percent', 0.0)
        
        # Calculate transformer impedances (simplified)
        r = vkr_percent / 100.0
        x = (vk_percent**2 - vkr_percent**2)**0.5 / 100.0 if vk_percent > vkr_percent else 0.0
        g = pfe_kw / (sn_mva * 1000) if sn_mva > 0 else 0.0
        b = i0_percent / 100.0
        
        return {'r': r, 'x': x, 'g': g, 'b': b, 'nominal': sn_mva}
    
    def _create_switches(self, pp_net, topology: Network, buses_dict: Dict[int, Bus], logger):
        """Create Switch objects from pandapower switches."""
        if 'switch' not in pp_net or pp_net.switch.empty:
            logger.info("No switches found in pandapower network")
            return
            
        switch_count = 0
        for idx, switch_data in pp_net.switch.iterrows():
            if switch_data.get('et') != 'b':  # Only bus-to-bus switches
                continue
                
            bus_idx = int(switch_data['bus'])
            element_idx = int(switch_data['element'])
            
            if bus_idx not in buses_dict or element_idx not in buses_dict:
                logger.warning(f"Buses not found for switch {idx}: {bus_idx} -> {element_idx}")
                continue
                
            bus1 = buses_dict[bus_idx]
            bus2 = buses_dict[element_idx]
            
            switch_id = str(idx)
            switch_name = switch_data.get('name', f"Switch {idx}")
            closed = switch_data.get('closed', True)
            
            topology.addSwitch(switch_id, switch_name, bus1, bus2, 
                             open=not closed, retained=False)
            switch_count += 1
            
        logger.info(f"Created {switch_count} switches")
