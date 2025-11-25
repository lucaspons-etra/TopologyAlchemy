from netCDF4 import Dataset
from topology import Network, Substation, VoltageLevel, Bus, Load, Line, Generator

def import_cdf(filename, topology_id, processLV=True,  logger=None):
    logger.info("> Starting CDF processing '{}'".format(str(filename)))
    """
    Import a CDF file and map it to the topology model.
    
    Args:
        filename (str): Path to the CDF file.
        topology_id (str): ID for the topology.
    
    Returns:
        Network: The imported topology.
    """
    # Create a new topology
    topology = Network(topology_id, "Imported Topology")
    
    # Open the CDF file
    with Dataset(filename, "r") as cdf:
        # Example: Extract substations
        if "substations" in cdf.variables:
            for i, substation_id in enumerate(cdf.variables["substations"][:]):
                substation_name = cdf.variables["substation_names"][i]
                coords = cdf.variables["substation_coords"][i] if "substation_coords" in cdf.variables else []
                topology.addSubstation(substation_id, substation_name, coords)
        
        # Example: Extract voltage levels
        if "voltage_levels" in cdf.variables:
            for i, voltage_level_id in enumerate(cdf.variables["voltage_levels"][:]):
                voltage_level_name = cdf.variables["voltage_level_names"][i]
                nominal_voltage = cdf.variables["voltage_level_nominal"][i]
                topology.addVoltageLevel(voltage_level_id, voltage_level_name, nominal_voltage)
        
        # Example: Extract buses
        if "buses" in cdf.variables:
            for i, bus_id in enumerate(cdf.variables["buses"][:]):
                bus_name = cdf.variables["bus_names"][i]
                voltage_level_id = cdf.variables["bus_voltage_levels"][i]
                voltage_level = topology.getVoltageLevel(voltage_level_id)
                topology.addBus(bus_id, bus_name, voltage_level)
        
        # Example: Extract lines
        if "lines" in cdf.variables:
            for i, line_id in enumerate(cdf.variables["lines"][:]):
                line_name = cdf.variables["line_names"][i]
                bus1_id = cdf.variables["line_bus1"][i]
                bus2_id = cdf.variables["line_bus2"][i]
                r = cdf.variables["line_r"][i]
                x = cdf.variables["line_x"][i]
                g1 = cdf.variables["line_g1"][i]
                b1 = cdf.variables["line_b1"][i]
                g2 = cdf.variables["line_g2"][i]
                b2 = cdf.variables["line_b2"][i]
                length = cdf.variables["line_length"][i]
                cable = cdf.variables["line_cable"][i]
                bus1 = topology.getBus(bus1_id)
                bus2 = topology.getBus(bus2_id)
                topology.addLine(line_id, line_name, bus1, bus2, r, x, g1, b1, g2, b2, length=length, cable=cable)
        
        # Example: Extract generators
        if "generators" in cdf.variables:
            for i, generator_id in enumerate(cdf.variables["generators"][:]):
                generator_name = cdf.variables["generator_names"][i]
                bus_id = cdf.variables["generator_bus"][i]
                minP = cdf.variables["generator_minP"][i]
                maxP = cdf.variables["generator_maxP"][i]
                targetP = cdf.variables["generator_targetP"][i]
                targetQ = cdf.variables["generator_targetQ"][i]
                bus = topology.getBus(bus_id)
                bus.addGenerator(generator_id, generator_name, minP=minP, maxP=maxP, targetP=targetP, targetQ=targetQ)
        
        # Example: Extract loads
        if "loads" in cdf.variables:
            for i, load_id in enumerate(cdf.variables["loads"][:]):
                load_name = cdf.variables["load_names"][i]
                bus_id = cdf.variables["load_bus"][i]
                p = cdf.variables["load_p"][i]
                q = cdf.variables["load_q"][i]
                bus = topology.getBus(bus_id)
                bus.addLoad(load_id, load_name, p=p, q=q)
    
    logger.info("Finished excel processing!")
    return topology