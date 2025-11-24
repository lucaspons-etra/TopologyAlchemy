import logging
from pathlib import Path
import sys
from venv import logger
import pandapower as pp
import pandas as pd
import json
from typing import Dict, List, Set, Tuple
from base_exporter import Exporter
from topology import Network, Substation, VoltageLevel, Bus, Load, Generator, Line, Switch, TwoWindingsTransformer, UsagePoint
from pandapower.auxiliary import pandapowerNet
from powersystem_analysis.helpers import compute_capacitance
from powersystem_analysis.domain import conversion_factor
import traceback

class PandapowerExporter(Exporter):

    @classmethod
    def name(cls) -> str:
        return "PandapowerExporter"

    def required_parameters(self) -> dict:
        return {
            "output_file": None,
            "line_power_unit": "KW",  # Options: 'W', 'KW', 'MW'
            "load_power_unit": "KW",  # Options: 'W', 'KW', 'MW'
        }
        
    async def _export_topology_impl(self, network: Network, logger: logging.Logger, params: dict = None) -> dict[str, Path]:
        """Export topology Network to pandapower JSON format.
        
        Converts topology elements back to pandapower format:
        - Buses -> pandapower bus table
        - Loads -> pandapower load table
        - Generators -> pandapower gen, sgen, ext_grid tables
        - Lines -> pandapower line table
        - Transformers -> pandapower trafo table
        - Switches -> pandapower switch table
        """
        if params is None:
            params = {}

        result = {}
        self.line_power_unit = params.get("line_power_unit", "KW")
        self.load_power_unit = params.get("load_power_unit", "KW")
        self.line_default_type = params.get("line_default_type", "cable")
        output_file_elems = params.get("output_file").split(".")
        for sub_topology in [network] + network.getElements("subTopologies"):
            if len(output_file_elems) > 1:
                output_file = ".".join(output_file_elems[:-1]) + f"_{sub_topology.id}." + output_file_elems[-1]
            else:
                output_file = f"{output_file_elems[0]}_{sub_topology.id}"

            try:
                pp_net:pandapowerNet = await self._create_all_elements(sub_topology, logger)
                # Save to JSON file
                pp.to_json(pp_net, output_file)
                logger.info(f"Successfully exported pandapower network to: {output_file}")
                
                # Log export statistics
                self._log_export_statistics(pp_net, logger)

                result[sub_topology.id] = Path(output_file)
            except Exception as e:
                logger.error(f"Export failed: {e}")
                traceback.print_exc()
                raise e
        return result

    async def _create_all_elements(self, network, logger) -> pandapowerNet:
        # Create empty pandapower network
        pp_net = pp.create_empty_network(name=network.name if hasattr(network, 'name') else "")
        logger.info("Created empty pandapower network")
        
        # Track mappings between topology and pandapower indices
        bus_mapping: Dict[str, int] = {}  # topology bus ID -> pandapower bus index
        
        # Step 1: Export voltage levels and buses
        self._export_buses(network, pp_net, bus_mapping, logger)
        
        # Step 2: Export loads
        self._export_loads(network, pp_net, bus_mapping, logger)
        
        # Step 3: Export generators
        self._export_generators(network, pp_net, bus_mapping, logger)
        
        # Step 4: Export lines
        self._export_lines(network, pp_net, bus_mapping, logger)
        
        # Step 5: Export transformers
        self._export_transformers(network, pp_net, bus_mapping, logger)
        
        # Step 6: Export switches
        self._export_switches(network, pp_net, bus_mapping, logger)
        
        self._export_dangling_lines(network, pp_net, bus_mapping, logger)
        return pp_net
    
    def _export_buses(self, network: Network, pp_net, bus_mapping: Dict[str, int], logger):
        """Export buses from topology Network to pandapower bus table."""
        bus_count = 0
        system = network.system if hasattr(network, 'system') else ""

        # Export standalone buses
        for bus in network.getElements("buses"):
            pp_bus_idx = self._create_pandapower_bus(pp_net, bus, system, logger)
            bus_mapping[bus.id] = pp_bus_idx
            bus_count += 1
        
        # Export buses from substations
        for substation in network.getElements("substations"):
            for bus in substation.getElements("buses"):
                pp_bus_idx = self._create_pandapower_bus(pp_net, bus, system, logger)
                bus_mapping[bus.id] = pp_bus_idx
                bus_count += 1
        
        logger.info(f"Exported {bus_count} buses")
    
    def _create_pandapower_bus(self, pp_net, bus: Bus, system: str, logger):
        """Create a single pandapower bus from topology Bus."""
        # Get nominal voltage from voltage level
        vn_kv = bus.voltageLevel.nominalV if bus.voltageLevel else 1.0
        
        # Determine bus type based on voltage level
        if vn_kv >= 100:
            bus_type = 'b'  # busbar for HV
        elif vn_kv >= 1:
            bus_type = 'n'  # node for MV
        else:
            bus_type = 'm'  # node for LV
        
        # Create pandapower bus
        pp_bus_idx = pp.create_bus(
            pp_net,
            vn_kv=vn_kv,
            name=(system + "_" if system else "") + bus.getId(bus.id),
            type=bus_type,
            in_service=True
        )
        
        logger.debug(f"Created pandapower bus {system + '_' if system else ''}{bus.getId(bus.id)} for topology bus {bus.id}")
        return pp_bus_idx
    
    def _export_dangling_lines(self, network: Network, pp_net, bus_mapping: Dict[str, int], logger):
        dl_count = 0
        system = network.system if hasattr(network, 'system') else ""

        # Process loads from standalone buses
        for bus in network.getElements("buses"):
            dl_count += self._export_bus_dangling_lines(bus, pp_net, bus_mapping, system, logger)
        
        # Process loads from substation buses
        for substation in network.getElements("substations"):
            for bus in substation.getElements("buses"):
                dl_count += self._export_bus_dangling_lines(bus, pp_net, bus_mapping, system, logger)
        
        logger.info(f"Exported {dl_count} loads")

    def _export_bus_dangling_lines(self, bus: Bus, pp_net, bus_mapping: Dict[str, int], system: str, logger):
        """Export dangling lines from a single bus."""
        dl_count = 0

        if bus.id not in bus_mapping:
            logger.warning(f"Bus {bus.id} not found in mapping for dangling lines")
            return 0

        pp_bus_idx = bus_mapping[bus.id]

        for dl in bus.getElements("danglingLines"):
            pp.create_ext_grid(pp_net, bus=pp_bus_idx, 
                               vm_pu=1.0, 
                               name=(system + "_" if system else "") + dl.getId(dl.id), 
                               in_service=True, controllable=True)
            
            dl_count += 1
            logger.debug(f"Created dangling line {(system + '_' if system else '') + dl.getId(dl.id)} on bus {pp_bus_idx}")

        return dl_count
          
    

    def _export_loads(self, network: Network, pp_net, bus_mapping: Dict[str, int], logger):
        """Export loads from topology Network to pandapower load table."""
        load_count = 0
        system = network.system if hasattr(network, 'system') else ""
        
        # Process loads from standalone buses
        for bus in network.getElements("buses"):
            load_count += self._export_bus_loads(bus, pp_net, bus_mapping, system, logger)
        
        # Process loads from substation buses
        for substation in network.getElements("substations"):
            for bus in substation.getElements("buses"):
                load_count += self._export_bus_loads(bus, pp_net, bus_mapping, system, logger)
        
        logger.info(f"Exported {load_count} loads")
    
    def _export_bus_loads(self, bus: Bus, pp_net, bus_mapping: Dict[str, int], system: str, logger):
        """Export loads from a single bus."""
        load_count = 0
        
        if bus.id not in bus_mapping:
            logger.warning(f"Bus {bus.id} not found in mapping for loads")
            return 0
        
        pp_bus_idx = bus_mapping[bus.id]
        
        load:Load
        for load in bus.getElements("loads"):
            pp.create_load(
                pp_net,
                bus=pp_bus_idx,
                p_mw=load.p,
                q_mvar=load.q,
                name=(system + "_" if system else "") + load.getId(load.id),
                in_service=True,
                type=load.type if hasattr(load, 'type') else 'wye'
            )
            load_count += 1
            logger.debug(f"Created load {system + '_' if system else ''}{load.getId(load.id)} on bus {pp_bus_idx}")
            
        usage_point:UsagePoint = None
        for usage_point in bus.getElements("usagePoints"):
            pp.create_load(
                pp_net,
                bus=pp_bus_idx,
                p_mw=usage_point.ratedPower,
                q_mvar=0,
                name= (system + "_" if system else "") +  usage_point.getId(usage_point.id),
                in_service=True,
                type=usage_point.type if hasattr(usage_point, 'type') else 'wye'
            )
            load_count += 1
            logger.debug(f"Created load (usage point) {system + '_' if system else ''}{usage_point.getId(usage_point.id)} on bus {pp_bus_idx}")

        
        return load_count
    
    def _export_generators(self, network: Network, pp_net, bus_mapping: Dict[str, int], logger):
        """Export generators from topology Network to pandapower generator tables."""
        gen_count = 0
        sgen_count = 0
        ext_grid_count = 0
        system = network.system if hasattr(network, 'system') else ""
        
        # Process generators from standalone buses
        for bus in network.getElements("buses"):
            counts = self._export_bus_generators(bus, pp_net, bus_mapping, system, logger)
            gen_count += counts[0]
            sgen_count += counts[1]
            ext_grid_count += counts[2]
        
        # Process generators from substation buses
        for substation in network.getElements("substations"):
            for bus in substation.getElements("buses"):
                counts = self._export_bus_generators(bus, pp_net, bus_mapping, system, logger)
                gen_count += counts[0]
                sgen_count += counts[1]
                ext_grid_count += counts[2]
        
        logger.info(f"Exported {gen_count} generators, {sgen_count} static generators, {ext_grid_count} external grids")
    
    def _export_bus_generators(self, bus: Bus, pp_net, bus_mapping: Dict[str, int], system: str, logger):
        """Export generators from a single bus."""
        if bus.id not in bus_mapping:
            logger.warning(f"Bus {bus.id} not found in mapping for generators")
            return (0, 0, 0)
        
        pp_bus_idx = bus_mapping[bus.id]
        gen_count = 0
        sgen_count = 0
        ext_grid_count = 0
        
        for generator in bus.getElements("generators"):
            if generator.id.startswith("EXT_GRID_"):
                self._create_external_grid(pp_net, pp_bus_idx, generator, system, logger)
                ext_grid_count += 1
            elif generator.id.startswith("SGEN_") or not generator.controllable:
                self._create_static_generator(pp_net, pp_bus_idx, generator, system, logger)
                sgen_count += 1
            else:
                self._create_standard_generator(pp_net, pp_bus_idx, generator, system, logger)
                gen_count += 1
        
        return (gen_count, sgen_count, ext_grid_count)
    
    def _create_external_grid(self, pp_net, pp_bus_idx, generator, system: str, logger):
        """Create external grid in pandapower."""
        pp.create_ext_grid(
            pp_net,
            bus=pp_bus_idx,
            vm_pu=generator.targetV if generator.targetV else 1.0,
            va_degree=0.0,
            name=(system + "_" if system else "") + generator.getId(generator.id),
            in_service=True
        )
        logger.debug(f"Created external grid {system + '_' if system else ''}{generator.getId(generator.id)} on bus {pp_bus_idx}")

    def _create_static_generator(self, pp_net, pp_bus_idx, generator, system: str, logger):
        """Create static generator in pandapower."""
        pp.create_sgen(
            pp_net,
            bus=pp_bus_idx,
            p_mw=generator.targetP if generator.targetP else 0.0,
            q_mvar=generator.targetQ if generator.targetQ else 0.0,
            name=(system + "_" if system else "") + generator.getId(generator.id),
            type='SGEN',
            in_service=True
        )
        logger.debug(f"Created static generator {system + '_' if system else ''}{generator.getId(generator.id)} on bus {pp_bus_idx}")

    def _create_standard_generator(self, pp_net, pp_bus_idx, generator, system: str, logger):
        """Create standard generator in pandapower."""
        target_p = generator.targetP if generator.targetP else 0.0
        max_p_mw = generator.maxP if generator.maxP else target_p
        
        pp.create_gen(
            pp_net,
            bus=pp_bus_idx,
            p_mw=target_p,
            vm_pu=generator.targetV if generator.targetV else 1.0,
            name=(system + "_" if system else "") + generator.getId(generator.id),
            min_p_mw=generator.minP if generator.minP else 0.0,
            max_p_mw=max_p_mw,
            in_service=True
        )
        logger.debug(f"Created generator {system + '_' if system else ''}{generator.getId(generator.id)} on bus {pp_bus_idx}")
    
    def _export_lines(self, network: Network, pp_net, bus_mapping: Dict[str, int], logger):
        """Export lines from topology Network to pandapower line table."""
        line_count = 0
        system = network.system if hasattr(network, 'system') else ""
        
        for line in network.getElements("lines"):
            if line.bus1.id not in bus_mapping or line.bus2.id not in bus_mapping:
                logger.warning(f"Buses not found for line {line.id}: {line.bus1.id} -> {line.bus2.id}")
                continue
            
            from_bus = bus_mapping[line.bus1.id]
            to_bus = bus_mapping[line.bus2.id]
            
            # Get line parameters for pandapower
            line_params = self._calculate_line_parameters(line)
            
            pp.create_line_from_parameters(
                pp_net,
                from_bus=from_bus,
                to_bus=to_bus,
                length_km=line_params['length_km'],
                name=(system + "_" if system else "") + line.getId(line.id),
                r_ohm_per_km=line_params['r_ohm_per_km'],
                x_ohm_per_km=line_params['x_ohm_per_km'],
                c_nf_per_km=line_params['c_nf_per_km'],
                g_us_per_km=line_params['g_us_per_km'],
                max_i_ka=line_params['max_i_ka'],
                in_service=True
            )
            line_count += 1
            logger.debug(f"Created line {system + '_' if system else ''}{line.getId(line.id)} from bus {from_bus} to bus {to_bus}")
        
        logger.info(f"Exported {line_count} lines")

    def _calculate_line_parameters(self, line: Line):
        """Calculate pandapower line parameters from topology line."""
        length_km = (line.length if hasattr(line, 'length') and line.length else 1.0)/1_000  # Convert m to km
        factor = conversion_factor[self.line_power_unit]
        
        # Calculate per-km parameters (simplified conversion)
        r_ohm_per_km = line.r if length_km > 0 else 0.0
        x_ohm_per_km = line.x if length_km > 0 else 0.0
        c_nf_per_km = compute_capacitance(
                line.voltageLevel.nominalV / factor, "cable" if line.voltageLevel.type=="LV" else "overhead"
            )
        g_us_per_km = 0.0
        max_i_ka = line.currentLimit/factor if hasattr(line, 'currentLimit') and line.currentLimit else 1.0
        
        return {
            'length_km': length_km,
            'r_ohm_per_km': r_ohm_per_km,
            'x_ohm_per_km': x_ohm_per_km,
            'c_nf_per_km': c_nf_per_km,
            'g_us_per_km': g_us_per_km,
            'max_i_ka': max_i_ka
        }
    
    def _export_transformers(self, network: Network, pp_net, bus_mapping: Dict[str, int], logger):
        """Export transformers from topology Network to pandapower trafo table."""
        trafo_count = 0
        system = network.system if hasattr(network, 'system') else ""
        
        for substation in network.getElements("substations"):
            for transformer in substation.getElements("twoWindingsTransformers"):
                if transformer.bus1.id not in bus_mapping or transformer.bus2.id not in bus_mapping:
                    logger.warning(f"Buses not found for transformer {transformer.id}: {transformer.bus1.id} -> {transformer.bus2.id}")
                    continue
                
                # Get transformer parameters for pandapower
                trafo_params = self._calculate_transformer_parameters(transformer, bus_mapping)
                
                pp.create_transformer_from_parameters(
                    pp_net,
                    hv_bus=trafo_params['hv_bus'],
                    lv_bus=trafo_params['lv_bus'],
                    name=(system + "_" if system else "") + transformer.getId(transformer.id),
                    sn_mva=trafo_params['sn_mva'],
                    vn_hv_kv=trafo_params['vn_hv_kv'],
                    vn_lv_kv=trafo_params['vn_lv_kv'],
                    vk_percent=trafo_params['vk_percent'],
                    vkr_percent=trafo_params['vkr_percent'],
                    pfe_kw=trafo_params['pfe_kw'],
                    i0_percent=trafo_params['i0_percent'],
                    in_service=True
                )
                trafo_count += 1
                logger.debug(f"Created transformer {system + '_' if system else ''}{transformer.getId(transformer.id)} from bus {trafo_params['hv_bus']} to bus {trafo_params['lv_bus']}")
        
        logger.info(f"Exported {trafo_count} transformers")
    
    def _calculate_transformer_parameters(self, transformer, bus_mapping):
        """Calculate pandapower transformer parameters from topology transformer."""
        hv_bus = bus_mapping[transformer.bus1.id]
        lv_bus = bus_mapping[transformer.bus2.id]
        
        # Determine HV and LV buses based on voltage levels
        hv_voltage = transformer.bus1.voltageLevel.nominalV
        lv_voltage = transformer.bus2.voltageLevel.nominalV
        
        if lv_voltage > hv_voltage:
            # Swap if voltages are reversed
            hv_bus, lv_bus = lv_bus, hv_bus
            hv_voltage, lv_voltage = lv_voltage, hv_voltage
        
        # Convert topology transformer parameters to pandapower format
        sn_mva = transformer.nominal if hasattr(transformer, 'nominal') and transformer.nominal else 1.0
        
        # Convert impedances back to percentages
        vkr_percent = transformer.vkr_percent if hasattr(
            transformer, 'vkr_percent') and transformer.vkr_percent else (
            transformer.r * 100 if hasattr(transformer, 'r') and transformer.r else 0.0)
        vk_percent = transformer.vk_percent if hasattr(
            transformer, 'vk_percent') and transformer.vk_percent else (
            (transformer.r**2 + transformer.x**2)**0.5 * 100) if hasattr(transformer, 'r') and hasattr(transformer, 'x') else 0.0
        pfe_kw = transformer.pfe_kw if hasattr(
            transformer, 'pfe_kw') and transformer.pfe_kw else (
            transformer.g * sn_mva * 1000 if hasattr(transformer, 'g') and transformer.g else 0.0)
        i0_percent = transformer.i0_percent if hasattr(
            transformer, 'i0_percent') and transformer.i0_percent else (
            transformer.b * 100 if hasattr(transformer, 'b') and transformer.b else 0.0)
        
        return {
            'hv_bus': hv_bus,
            'lv_bus': lv_bus,
            'sn_mva': sn_mva,
            'vn_hv_kv': hv_voltage,
            'vn_lv_kv': lv_voltage,
            'vk_percent': vk_percent,
            'vkr_percent': vkr_percent,
            'pfe_kw': pfe_kw,
            'i0_percent': i0_percent
        }
    
    def _export_switches(self, network: Network, pp_net, bus_mapping: Dict[str, int], logger):
        """Export switches from topology Network to pandapower switch table."""
        switch_count = 0
        system = network.system if hasattr(network, 'system') else ""
        
        for switch in network.getElements("switches"):
            if switch.bus1.id not in bus_mapping or switch.bus2.id not in bus_mapping:
                logger.warning(f"Buses not found for switch {switch.id}: {switch.bus1.id} -> {switch.bus2.id}")
                continue
            
            bus_idx = bus_mapping[switch.bus1.id]
            element_idx = bus_mapping[switch.bus2.id]
            
            # Determine switch state
            closed = not (switch.open == 'True' or switch.open == True)
            
            pp.create_switch(
                pp_net,
                bus=bus_idx,
                element=element_idx,
                et='b',  # bus-to-bus switch
                type='CB',  # circuit breaker
                closed=closed,
                name=(system + "_" if system else "") + switch.getId(switch.id)
            )
            switch_count += 1
            logger.debug(f"Created switch {system + '_' if system else ''}{switch.getId(switch.id)} between buses {bus_idx} and {element_idx}")
        
        logger.info(f"Exported {switch_count} switches")
    
    def _log_export_statistics(self, pp_net, logger):
        """Log statistics about the exported pandapower network."""
        logger.info("=== EXPORT STATISTICS ===")
        
        stats = {
            'buses': len(pp_net.bus),
            'loads': len(pp_net.load) if 'load' in pp_net and not pp_net.load.empty else 0,
            'generators': len(pp_net.gen) if 'gen' in pp_net and not pp_net.gen.empty else 0,
            'static_generators': len(pp_net.sgen) if 'sgen' in pp_net and not pp_net.sgen.empty else 0,
            'external_grids': len(pp_net.ext_grid) if 'ext_grid' in pp_net and not pp_net.ext_grid.empty else 0,
            'lines': len(pp_net.line) if 'line' in pp_net and not pp_net.line.empty else 0,
            'transformers': len(pp_net.trafo) if 'trafo' in pp_net and not pp_net.trafo.empty else 0,
            'switches': len(pp_net.switch) if 'switch' in pp_net and not pp_net.switch.empty else 0
        }
        
        for element_type, count in stats.items():
            logger.info(f"  {element_type}: {count}")
        
        total_elements = sum(stats.values())
        logger.info(f"Total elements: {total_elements}")
    
