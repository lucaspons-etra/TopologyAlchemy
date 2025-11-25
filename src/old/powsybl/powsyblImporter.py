import pypowsybl as pp
from topology import Substation, Network, VoltageLevel
import topology

def import_xiidm_to_topology(network:pp.network,id):
    topology: Network = Network(id)
    # Parse Substations and Voltage Levels
    for _, substation in network.get_substations().iterrows():
        substation_id = substation.name
        substation_name = substation.name
        coords = []  # Add parsing for coordinates if available
        topology.addSubstation(substation_id, substation_name, coords)
        
        for _, voltage_level in network.get_voltage_levels(substation_id==substation_id).iterrows():
            vl_id = voltage_level.name
            nominalV = voltage_level['nominal_v']
            substation_obj = topology.getSubstation(substation_id)
            substation_obj.addVoltageLevel(vl_id, nominalV)
            
            for _, busbar_section in network.get_buses(voltage_level_id==vl_id).iterrows():
                bus_id = busbar_section.name
                substation_obj.getVoltageLevel(vl_id).addBus(bus_id)

    # Parse Loads
    for _, load in network.get_loads().iterrows():
        load_id = load.name
        bus_id = load['bus']
        p0 = load['p0']
        q0 = load['q0']
        name = load['name']
        bus = topology.getBus(bus_id)
        if bus:
            bus.addLoad(load_id, bus_id, p0, q0, name, [])

    # Parse Generators
    for _, generator in network.get_generators().iterrows():
        gen_id = generator.name
        bus_id = generator['bus']
        minP = generator['min_p']
        maxP = generator['max_p']
        targetP = generator['target_p']
        targetV = generator['target_v']
        targetQ = generator['target_q']
        minQ = generator['min_q']
        maxQ = generator['max_q']
        voltageRegulatorOn = generator['voltage_regulator_on']
        bus = topology.getBus(bus_id)
        if bus:
            bus.addGenerator(gen_id, bus_id, minP, maxP, targetP, targetV, targetQ, minQ, maxQ, voltageRegulatorOn, [])

    # Parse Lines
    for _, line in network.get_lines().iterrows():
        line_id = line.name
        bus1 = line['bus1']
        bus2 = line['bus2']
        r = line['r']
        x = line['x']
        g1 = line['g1']
        b1 = line['b1']
        g2 = line['g2']
        b2 = line['b2']
        currentLimit = line['current_limit']
        coords = []  # Add parsing for coordinates if available
        topology.addLine(line_id, bus1, bus2, r, x, g1, b1, g2, b2, currentLimit, coords, "LV")

    # Parse Transformers
    for _, transformer in network.get_two_windings_transformers().iterrows():
        trafo_id = transformer.name
        bus1 = transformer['hv_bus']
        bus2 = transformer['lv_bus']
        r = transformer['r']
        x = transformer['x']
        g = transformer['g']
        b = transformer['b']
        ratedU1 = transformer['rated_u1']
        ratedU2 = transformer['rated_u2']
        nominal = transformer['nominal_power']
        substation = topology.getSubstationFromBus(bus1)
        if substation:
            substation.addTransformer(trafo_id, bus1, bus2, r, x, g, b, ratedU1, ratedU2, nominal)

    return topology

def importTopology(filename, id, logger):
    logger.info("> Starting powsybl processing '{}'".format(str(filename)))
    #linsGeometry, linsLVGeometry = getLocations(filename,logger)
    network = pp.network.load(filename)
    
       
    #for sub in network.get_substations():
    #    topology.addSubstation( importSubstation(sub))
    
    topology:Network = import_xiidm_to_topology(network,id)
    
    logger.info("Finished powsybl processing!")
    return topology

def importSubstation(substation):
    return Substation(substation.id,substation.name, substation.coords)