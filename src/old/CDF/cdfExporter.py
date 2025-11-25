from netCDF4 import Dataset
from topology import Network

def export_to_cdf(topology: Network, output_file: str, logger=None):
    """
    Export the topology model to a CDF file.

    Args:
        topology (Network): The topology model to export.
        output_file (str): Path to the output CDF file.
        logger: Logger instance for logging messages.
    """
    if logger:
        logger.info(f"Exporting topology to CDF: {output_file}")

    # Create a new CDF file
    with Dataset(output_file, "w", format="NETCDF4") as cdf:
        # Create dimensions
        cdf.createDimension("substations", len(topology.getElements("substations")))
        cdf.createDimension("voltage_levels", len(topology.getElements("voltageLevels")))
        cdf.createDimension("buses", len(topology.getElements("buses")))
        cdf.createDimension("lines", len(topology.getElements("lines")))
        cdf.createDimension("generators", len(topology.getElements("generators")))
        cdf.createDimension("loads", len(topology.getElements("loads")))

        # Create variables for substations
        substation_ids = cdf.createVariable("substations", "S1", ("substations",))
        substation_names = cdf.createVariable("substation_names", "S1", ("substations",))
        substation_coords = cdf.createVariable("substation_coords", "f4", ("substations", 2))

        # Populate substation data
        for i, substation in enumerate(topology.getElements("substations")):
            substation_ids[i] = substation.id
            substation_names[i] = substation.name
            substation_coords[i] = substation.coords if substation.coords else [0.0, 0.0]

        # Create variables for voltage levels
        voltage_level_ids = cdf.createVariable("voltage_levels", "S1", ("voltage_levels",))
        voltage_level_names = cdf.createVariable("voltage_level_names", "S1", ("voltage_levels",))
        voltage_level_nominal = cdf.createVariable("voltage_level_nominal", "f4", ("voltage_levels",))

        # Populate voltage level data
        for i, voltage_level in enumerate(topology.getElements("voltageLevels")):
            voltage_level_ids[i] = voltage_level.id
            voltage_level_names[i] = voltage_level.name
            voltage_level_nominal[i] = voltage_level.nominalV

        # Create variables for buses
        bus_ids = cdf.createVariable("buses", "S1", ("buses",))
        bus_names = cdf.createVariable("bus_names", "S1", ("buses",))
        bus_voltage_levels = cdf.createVariable("bus_voltage_levels", "S1", ("buses",))

        # Populate bus data
        for i, bus in enumerate(topology.getElements("buses")):
            bus_ids[i] = bus.id
            bus_names[i] = bus.name
            bus_voltage_levels[i] = bus.parent.id

        # Create variables for lines
        line_ids = cdf.createVariable("lines", "S1", ("lines",))
        line_names = cdf.createVariable("line_names", "S1", ("lines",))
        line_bus1 = cdf.createVariable("line_bus1", "S1", ("lines",))
        line_bus2 = cdf.createVariable("line_bus2", "S1", ("lines",))
        line_r = cdf.createVariable("line_r", "f4", ("lines",))
        line_x = cdf.createVariable("line_x", "f4", ("lines",))
        line_g1 = cdf.createVariable("line_g1", "f4", ("lines",))
        line_b1 = cdf.createVariable("line_b1", "f4", ("lines",))
        line_g2 = cdf.createVariable("line_g2", "f4", ("lines",))
        line_b2 = cdf.createVariable("line_b2", "f4", ("lines",))
        line_length = cdf.createVariable("line_length", "f4", ("lines",))
        line_cable = cdf.createVariable("line_cable", "S1", ("lines",))

        # Populate line data
        for i, line in enumerate(topology.getElements("lines")):
            line_ids[i] = line.id
            line_names[i] = line.name
            line_bus1[i] = line.bus1.id
            line_bus2[i] = line.bus2.id
            line_r[i] = line.r
            line_x[i] = line.x
            line_g1[i] = line.g1
            line_b1[i] = line.b1
            line_g2[i] = line.g2
            line_b2[i] = line.b2
            line_length[i] = line.length
            line_cable[i] = line.cable

        # Create variables for generators
        generator_ids = cdf.createVariable("generators", "S1", ("generators",))
        generator_names = cdf.createVariable("generator_names", "S1", ("generators",))
        generator_bus = cdf.createVariable("generator_bus", "S1", ("generators",))
        generator_minP = cdf.createVariable("generator_minP", "f4", ("generators",))
        generator_maxP = cdf.createVariable("generator_maxP", "f4", ("generators",))
        generator_targetP = cdf.createVariable("generator_targetP", "f4", ("generators",))
        generator_targetQ = cdf.createVariable("generator_targetQ", "f4", ("generators",))

        # Populate generator data
        for i, generator in enumerate(topology.getElements("generators")):
            generator_ids[i] = generator.id
            generator_names[i] = generator.name
            generator_bus[i] = generator.parent.id
            generator_minP[i] = generator.minP
            generator_maxP[i] = generator.maxP
            generator_targetP[i] = generator.targetP
            generator_targetQ[i] = generator.targetQ

        # Create variables for loads
        load_ids = cdf.createVariable("loads", "S1", ("loads",))
        load_names = cdf.createVariable("load_names", "S1", ("loads",))
        load_bus = cdf.createVariable("load_bus", "S1", ("loads",))
        load_p = cdf.createVariable("load_p", "f4", ("loads",))
        load_q = cdf.createVariable("load_q", "f4", ("loads",))

        # Populate load data
        for i, load in enumerate(topology.getElements("loads")):
            load_ids[i] = load.id
            load_names[i] = load.name
            load_bus[i] = load.parent.id
            load_p[i] = load.p
            load_q[i] = load.q

    if logger:
        logger.info(f"Export completed: {output_file}")