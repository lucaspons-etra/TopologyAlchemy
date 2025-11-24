import math
import logging
from os import system

import warnings
import pandas as pd
from sympy import Ne
from topology import Bus, Load, MvGenerator, Generator, Network, UsagePoint, UsagePointLocation, VoltageLevel, Substation
from base_importer import Importer

# Suppress openpyxl data validation warnings
warnings.filterwarnings("ignore", message="Data Validation extension is not supported and will be removed", category=UserWarning, module="openpyxl.worksheet._reader")


class ExcelImporter(Importer):
    """
    Excel importer that reads topology data from Excel (.xlsx) files.
    
    Inherits from Importer base class and implements the importTopology interface.
    Supports importing both Medium Voltage (MV) and Low Voltage (LV) networks.
    """

    def required_parameters(self) -> dict:
        return {
            "input_file": None,
            "process_lv": False,
            "network_id": None,
            "lv_network_id": "",
            "system": None
        }

    @classmethod
    def name(cls) -> str:
        return "ExcelImporter"

    async def _import_topology_impl(self, logger: logging.Logger, params: dict = {}) -> Network:
        """
        Import topology from an Excel file.
        
        Args:
            filename: Path to the Excel file
            process_lv: Whether to process Low Voltage (LV) networks
            logger: Logger instance for logging messages
            
        Returns:
            Network object containing the imported topology
        """
        # Extract process_lv parameter with proper type handling
        process_lv_param = params.get("process_lv")
        if isinstance(process_lv_param, bool):
            process_lv = process_lv_param
        else:
            process_lv = True if process_lv_param.lower() == "true" else False
        
        # Extract network_id parameter
        network_id = params.get("network_id") if len(params.get("network_id")) > 0 else None
        
        # Extract lv_network_id parameter
        lv_network_id = params.get("lv_network_id") if len(params.get("lv_network_id")) > 0 else None
        
        system = params.get("system") if len(params.get("system","")) > 0 else None

        return self.import_topology_full(params.get("input_file"), process_lv, network_id, lv_network_id, system, logger)

    def import_topology_full(self, input_file: str, process_lv: bool, network_id: str, lv_network_id:str, system: str, logger: logging.Logger) -> Network:
        """
        Import topology from an Excel file with full parameter names.
        
        Args:
            input_file: Path to the Excel file
            process_lv: Whether to process Low Voltage (LV) networks (matches legacy param name)
            logger: Logger instance for logging messages
            
        Returns:
            Network object containing the imported topology
        """
        logger.info("> Starting excel processing '{}'".format(str(input_file)))
        network = self._process_common(input_file, network_id, system, logger)
        self._process_mv_topology(network, input_file, logger)
        if process_lv:
            network:Network = self._process_lv_topology(network, input_file, lv_network_id=lv_network_id, logger=logger)
        logger.info("Finished excel processing!")
        return network

    def _process_common(self, input_file: str, network_id: str, system: str, logger: logging.Logger) -> Network:
        """
        Process common network elements (NETWORKS, SUBSTATIONS, BUSES sheets).
        
        Args:
            input_file: Path to the Excel file
            logger: Logger instance for logging messages
            
        Returns:
            Network object with base topology structure
        """
        network:Network = None
        # assume fields ["ID","NAME","TYPE"]
        df = pd.read_excel(input_file, sheet_name='NETWORKS')
        for index, row in df.iterrows():
            if str(row['EXTERNAL'])=='0' and network_id is None or row['ID']==network_id:
                network = Network(row['ID'],name=row['NAME'], network=row['ID'], system=system)
                break # process first internal network
        
        if network==None:
            logger.error("Error: There is no network defined in the EXCEL file")
            return None
        
        # assume fields ["ID","NAME","LATITUDE","LONGITUDE"]
        df = pd.read_excel(input_file, sheet_name='SUBSTATIONS')
        for index, row in df.iterrows():
            if network_id!=None and row['NETWORK']!=network_id:
                continue
            coords=[]
            if 'LATITUDE' in row and 'LONGITUDE' in row and not math.isnan(row['LATITUDE']) and not math.isnan(row['LONGITUDE']):
                coords = [row['LATITUDE'], row['LONGITUDE']]
            network.addSubstation(row['ID'], row['NAME'] if not pd.isna(row['NAME']) else None, coords=coords)
        
        # assume fields ["ID","NAME","SUBSTATION","U"]
        df = pd.read_excel(input_file, sheet_name='BUSES')
        for index, row in df.iterrows():
            substation:Substation = network.getSubstation(row['SUBSTATION'])
            if substation is None:
                continue
            voltageLevel:VoltageLevel= network.getVoltageLevel("VL"+str(row['U']))
            if voltageLevel is None:
                voltageLevel = network.addVoltageLevel("VL"+str(row['U']),"VL"+str(row['U']), nominalV= row['U'], type="MV")
            coords=[]
            if not math.isnan(row.get('LATITUDE', math.nan)) and not math.isnan(row.get('LONGITUDE', math.nan)):
                coords = [row.get('LATITUDE',math.nan), row.get('LONGITUDE',math.nan)]
            substation.addBus(row['ID'], row['NAME'],voltageLevel=voltageLevel, coords=coords)

        df = pd.read_excel(input_file, sheet_name='NETWORKS')
        for index, row in df.iterrows():
            if str(row['EXTERNAL'])=='1':
                bus:Bus = network.getBus(row['BUS'])
                if bus is not None:
                    bus.addDanglingLine(row['ID'], row['NAME'], type=row['TYPE'], controllable=True)
                    
        return network

    def _process_mv_topology(self, mv_network: Network, input_file: str, logger: logging.Logger) -> None:
        """
        Process Medium Voltage (MV) topology elements.
        
        Reads TRANSFORMERS, TRI-TRANSFORMERS, LOADS, GENERATORS, SWITCHES, LINES sheets
        and adds corresponding elements to the network.
        
        Args:
            MVNetwork: Network object to populate with MV elements
            filename: Path to the Excel file
            logger: Logger instance for logging messages
        """
        # assume fields ["ID", "NAME", "BUS1", "BUS2","R","X","G","B","NOMINALPOWER",
        #                "i0_percent","pfe_kw","shift_degree","std_type","tap_max","tap_min",
        #                "tap_neutral","tap_pos","tap_side","tap_step_degree","tap_step_percent",
        #                "vk_percent","vkr_percent"]

        df = pd.read_excel(input_file, sheet_name='TRANSFORMERS')
        for index, row in df.iterrows():
            bus1:Bus = mv_network.getBus(row["BUS1"])
            bus2:Bus = mv_network.getBus(row["BUS2"])
            if bus1 is None or bus2 is None:
                continue
            if bus1.parent.id != bus2.parent.id:
                logger.error(f"Transformer connecting buses in different substations")
                continue
            sub:Substation = bus1.parent
            
            coords=[]
            if not math.isnan(row.get('LATITUDE', math.nan)) and not math.isnan(row.get('LONGITUDE', math.nan)):
                coords = [row.get('LATITUDE',math.nan), row.get('LONGITUDE',math.nan)]
            sub.addTransformer(row["ID"],row['NAME'],bus1,bus2,r=row['R'],x=row['X'],g=row['G'],b=row['B'],nominal=row['NOMINALPOWER'],
                               i0_percent=row['i0_percent'],pfe_kw=row['pfe_kw'],shift_degree=row['shift_degree'],std_type=row['std_type'],
                               tap_max=row['tap_max'],tap_min=row['tap_min'],tap_neutral=row['tap_neutral'],tap_pos=row['tap_pos'],
                               tap_side=row['tap_side'],tap_step_degree=row['tap_step_degree'],tap_step_percent=row['tap_step_percent'],
                               vk_percent=row['vk_percent'],vkr_percent=row['vkr_percent'],coords=coords)

        df = pd.read_excel(input_file, sheet_name='TRI-TRANSFORMERS')
        for index, row in df.iterrows():
            bus1:Bus = mv_network.getBus(row["BUS1"])
            bus2:Bus = mv_network.getBus(row["BUS2"])
            bus3:Bus = mv_network.getBus(row["BUS3"])
            if bus1 is None or bus2 is None or bus3 is None:
                continue
            
            if bus1.parent.id != bus2.parent.id or bus1.parent.id != bus3.parent.id:
                logger.error(f"Transformer connecting buses in different substations")
                continue
            sub:Substation = bus1.parent
            coords=[]
            if 'LATITUDE' in row and 'LONGITUDE' in row and not math.isnan(row['LATITUDE']) and not math.isnan(row['LONGITUDE']):
                coords = [row['LATITUDE'], row['LONGITUDE']]
            sub.addTriTransformer(row["ID"],row['NAME'],bus1,bus2,bus3,r1=row['R1'],x1=row['X1'],g1=row['G1'],b1=row['B1'],
                                r2=row['R2'],x2=row['X2'],g2=row['G2'],b2=row['B2'],
                                r3=row['R3'],x3=row['X3'],g3=row['G3'],b3=row['B3'],
                                ratedS1=row['RATEDS1'], ratedS2=row['RATEDS2'], ratedS3=row['RATEDS3'],
                                ratedStar=row['RATEDUSTAR'], coords=coords)


        df = pd.read_excel(input_file, sheet_name='LOADS')
        for index, row in df.iterrows():
            bus:Bus = mv_network.getBus(row["BUS"])
            if bus is None:
                continue
            bus.addLoad(row["ID"],row['NAME'],p=row['P'],q=row['Q'], coords=(row['LATITUDE'], row['LONGITUDE']))

        df = pd.read_excel(input_file, sheet_name='GENERATORS')
        for index, row in df.iterrows():
            bus:Bus = mv_network.getBus(row["BUS"])
            if bus is None:
                continue
            bus.addMvGenerator(row["ID"], row['NAME'], minP=row['MINP'], maxP=row['MAXP'], targetP=row['TARGETP'], targetV=row['TARGETV'], targetQ=row['TARGETQ'], minQ=row['MINQ'], maxQ=row['MAXQ'], controllable=row['CONTROLLABLE'], coords=(row['LATITUDE'], row['LONGITUDE']))

        df = pd.read_excel(input_file, sheet_name='SWITCHES')
        for index, row in df.iterrows():
            bus1:Bus = mv_network.getBus(row["BUS1"])
            bus2:Bus = mv_network.getBus(row["BUS2"])
            if bus1 is None:
                continue
            if bus2 is None:
                continue
            coords=[]
            if 'LATITUDE' in row and 'LONGITUDE' in row and not math.isnan(row['LATITUDE']) and not math.isnan(row['LONGITUDE']):
                coords = [row['LATITUDE'], row['LONGITUDE']]
            mv_network.addSwitch(row["ID"], row['NAME'], bus1, bus2, row['OPEN'], coords=coords)

        df = pd.read_excel(input_file, sheet_name='LINES')
        for index, row in df.iterrows():
            bus1:Bus = mv_network.getBus(row["BUS1"])
            bus2:Bus = mv_network.getBus(row["BUS2"])
            if bus1 is None:
                #print(f"Bus1 not found: {row["BUS1"]}")
                continue
            if bus2 is None:
                #print(f"Bus2 not found: {row["BUS2"]}")
                continue
            
            line_shape=[]
            index=list(row.keys()).index('COORDS')
            while index<len(row.values):
                if math.isnan(row.values[index]):
                    break
                line_shape.append([row.values[index],row.values[index+1]])
                index+=2                    
            mv_network.addLine(row["ID"],row['NAME'],bus1=bus1,bus2=bus2,r=row['R'],x=row['X'],g1=row['G1'],b1=row['B1'],g2=row["G2"],b2=row["B2"],currentLimit=row['CURRENTLIMIT'],cable=row['WIREINFO'], length=row['LENGTH'],line_shape=line_shape) 

    def _process_lv_topology(self, mv_network: Network, filename: str, lv_network_id: str, logger: logging.Logger) -> Network:
        """
        Process Low Voltage (LV) topology elements.
        
        Reads LINESEGMENTS, PROTECTIONS, USAGEPOINTLOCATIONS, USAGEPOINTS, DERS, METERS sheets
        and adds corresponding elements to LV subtopologies.
        
        Args:
            MVNetwork: Network object containing MV network and LV subtopologies
            filename: Path to the Excel file
            logger: Logger instance for logging messages
        """
        # assume fields ["ID","NAME","FEEDER","FEEDER_NUM","LENGTH", "WIREINFO","NODE1","NODE2","R","X","G1","B1","G2","B2","CURRENTLIMIT","COORDS"]
        df = pd.read_excel(filename, sheet_name='LINESEGMENTS')
        actual_network: Network = mv_network
        for index, row in df.iterrows():
            if lv_network_id is not None and row['FEEDER'] != lv_network_id:
                continue
                
            lv_network:Network = mv_network.getSubTopology(row['FEEDER'])
            if lv_network is None:
                lv_network = mv_network.addSubTopology(row['FEEDER'], row['FEEDER'])
                if lv_network_id is not None:
                    actual_network = lv_network

            feeder_num = (str(int(row["FEEDER_NUM"])) if 'FEEDER_NUM' in row and not pd.isna(row["FEEDER_NUM"]) else None)

            # This replicates the MV part in the LV part
            mv_bus: Bus = mv_network.getBus(row['FEEDER'])
            if mv_bus is None:
                logger.error("Bus '{}' not found in MVNetwork".format(row['FEEDER']))
                continue

            feeder_bus: Bus = lv_network.getBus(row['FEEDER'])
            if feeder_bus is None:
                mv_substation: Substation = mv_bus.parent
                if mv_substation is None:
                    logger.error("Substation not found for bus '{}'".format(row['FEEDER']))
                    continue
                substation:Substation = lv_network.addSubstation(id=mv_substation.id, name=mv_substation.name, coords=mv_substation.coords)

                # # Options to change the ID of the subtopologies (e.g. for tab labels)
                # LVNetwork.name += f" ({mv_substation.name})"
                # LVNetwork.name = f"{mv_substation.id} {LVNetwork.name}"
                
                mv_voltageLevel:VoltageLevel = mv_bus.voltageLevel            
                voltageLevel:VoltageLevel = lv_network.getVoltageLevel(mv_voltageLevel.id)
                if not voltageLevel:
                    voltageLevel=lv_network.addVoltageLevel(mv_voltageLevel.id,mv_voltageLevel.name, mv_voltageLevel.nominalV, type="LV")
                feeder_bus = substation.addBus(row['FEEDER'],row['FEEDER'], voltageLevel=voltageLevel, feeder_num=feeder_num) # , coords=mv_bus.coords)
                feeder_bus.addDanglingLine(mv_network.id, mv_network.name, type="MV", feeder_num=feeder_num)
            
            
            if mv_bus.getElement("danglingLines", mv_bus.id + "_" + lv_network.id+ (("_" + feeder_num) if feeder_num is not None else "") ) is None:
                mv_bus.addDanglingLine(mv_bus.id + (("_" + feeder_num) if feeder_num is not None else ""), lv_network.name, type="LV", feeder_num=feeder_num)

            voltageLevel:VoltageLevel =  feeder_bus.voltageLevel
            bus1:Bus= lv_network.getBus(row['NODE1'])
            if bus1 is None:
                bus1 = lv_network.addBus(row['NODE1'], row['NODE1'],voltageLevel=voltageLevel, feeder_num=feeder_num)
                
            bus2:Bus= lv_network.getBus(row['NODE2'])
            if bus2 is None:
                bus2 = lv_network.addBus(row['NODE2'], row['NODE2'],voltageLevel=voltageLevel, feeder_num=feeder_num)
            
            line_shape=[]
            index=list(row.keys()).index('COORDS')
            while index<len(row.values):
                if math.isnan(row.values[index]):
                    break
                line_shape.append([row.values[index],row.values[index+1]])
                index+=2                    
            
            lv_network.addLine(row['ID'], row['NAME'], bus1=bus1, bus2= bus2, length=row['LENGTH'], r=row['R'], x=row['X'], b1=row['B1'], g1=row['G1'],b2=row['B2'], g2=row['G2'], currentLimit=row['CURRENTLIMIT'],cable=row['WIREINFO'], line_shape=line_shape, feeder_num=feeder_num)

        # assume fields ["ID","NAME","FEEDER","FEEDER_NUM","BUS1","BUS2","TYPE","OPERATINGCURRENT","NORMALLYOPEN","LATITUDE","LONGITUDE"]
        df = pd.read_excel(filename, sheet_name='PROTECTIONS')
        for index, row in df.iterrows():
            if lv_network_id is not None and row['FEEDER'] != lv_network_id:
                continue

            lv_network:Network = mv_network.getSubTopology(row['FEEDER'])
            if lv_network:
                bus1:Bus = lv_network.getBus(str(row["BUS1"]).replace(".0",""))
                bus2:Bus = lv_network.getBus(str(row["BUS2"]).replace(".0",""))
                feeder_num = (str(int(row["FEEDER_NUM"])) if 'FEEDER_NUM' in row and not pd.isna(row["FEEDER_NUM"]) else None)
                if bus1 is None and bus2 is None:
                    # print(f"Bus1 and Bus2 not found: {row["BUS1"]} {row["BUS2"]}")
                    # continue
                    feeder_bus: Bus = lv_network.getBus(row['FEEDER'])
                    bus1 = lv_network.addBus(str(row["BUS1"]).replace(".0",""), str(row["BUS1"]).replace(".0",""), voltageLevel=feeder_bus.voltageLevel,feeder_num=feeder_num)
                    bus2 = lv_network.addBus(str(row["BUS2"]).replace(".0",""), str(row["BUS2"]).replace(".0",""), voltageLevel=feeder_bus.voltageLevel,feeder_num=feeder_num)
                    lv_network.addSwitch(row["ID"], row['NAME'], bus1, bus2, row['NORMALLYOPEN'], coords=(row['LATITUDE'], row['LONGITUDE']) if 'LATITUDE' in row and 'LONGITUDE' in row else None , feeder_num=feeder_num)
                elif bus1 is None:
                    find_buses = [e for e in [e.getBus(str(row["BUS1"]).replace(".0","")) for e in mv_network.getElements("subTopologies")] if e is not None]
                    bus1 = find_buses[0] if len(find_buses) > 0 else None
                    dl_type = "LV"
                    if bus1 is None:
                        # if not present in a subtopology, check in the MV network
                        bus1 = mv_network.getBus(str(row["BUS1"]).replace(".0",""))
                        dl_type = "MV"
                        if bus1 is None:
                            # if not found, add to current network and continue
                            bus1 = lv_network.addBus(str(row["BUS1"]).replace(".0",""), str(row["BUS1"]).replace(".0",""), voltageLevel=bus2.voltageLevel,feeder_num=feeder_num)
                            lv_network.addSwitch(row["ID"], row['NAME'], bus1, bus2, row['NORMALLYOPEN'], coords=(row['LATITUDE'], row['LONGITUDE']), feeder_num=feeder_num)
                            continue
                    # buses in different networks, add dangling line to bus in other network
                    bus1.addDanglingLine(lv_network.id + "_" + bus2.name, lv_network.name, type="LV")
                    # add dangling line to current network
                    other_network = bus1.parent
                    bus2.addDanglingLine(other_network.id + "_" + bus1.name, other_network.name, type=dl_type)
                    # add fictitious bus to current network
                    new_bus_name = str(row["BUS2"]).replace(".0","") + "_" + str(row["BUS1"]).replace(".0","")
                    new_bus = lv_network.addBus(new_bus_name, new_bus_name, voltageLevel=bus2.voltageLevel,feeder_num=feeder_num)
                    # add switch to current network with fictitious bus
                    lv_network.addSwitch(row["ID"], row['NAME'], new_bus, bus2, row['NORMALLYOPEN'], coords=(row['LATITUDE'], row['LONGITUDE']), feeder_num=feeder_num)
                elif bus2 is None:
                    find_buses = [e for e in [e.getBus(str(row["BUS2"]).replace(".0","")) for e in mv_network.getElements("subTopologies")] if e is not None]
                    bus2 = find_buses[0] if len(find_buses) > 0 else None
                    dl_type = "LV"
                    if bus2 is None:
                        # if not present in a subtopology, check in the MV network
                        bus2 = mv_network.getBus(str(row["BUS2"]).replace(".0",""))
                        dl_type = "MV"
                        if bus2 is None:
                            # if not found, add to current network and continue
                            bus2 = lv_network.addBus(str(row["BUS2"]).replace(".0",""), str(row["BUS2"]).replace(".0",""), voltageLevel=bus1.voltageLevel,feeder_num=feeder_num)
                            lv_network.addSwitch(row["ID"], row['NAME'], bus1, bus2, row['NORMALLYOPEN'], coords=(row['LATITUDE'], row['LONGITUDE']) if 'LATITUDE' in row and 'LONGITUDE' in row else None, feeder_num=feeder_num)
                            continue
                    # buses in different networks, add dangling line to bus in other network
                    bus2.addDanglingLine(lv_network.id + "_" + bus1.name, lv_network.name, type="LV")
                    # add dangling line to current network
                    other_network = bus2.parent
                    bus1.addDanglingLine(other_network.id + "_" + bus2.name, other_network.name, type=dl_type)
                    # add fictitious bus to current network
                    new_bus_name = str(row["BUS1"]).replace(".0","") + "_" + str(row["BUS2"]).replace(".0","")
                    new_bus = lv_network.addBus(new_bus_name, new_bus_name, voltageLevel=bus1.voltageLevel,feeder_num=feeder_num)
                    # add switch to current network with fictitious bus
                    lv_network.addSwitch(row["ID"], row['NAME'], bus1, new_bus, row['NORMALLYOPEN'], coords=(row['LATITUDE'], row['LONGITUDE']), feeder_num=feeder_num)
                else:
                    lv_network.addSwitch(row["ID"], row['NAME'], bus1, bus2, row['NORMALLYOPEN'], coords=(row['LATITUDE'], row['LONGITUDE']) if 'LATITUDE' in row and 'LONGITUDE' in row else None, feeder_num=feeder_num)

        # assume fields ["ID","NAME","FEEDER","FEEDER_NUM","BUS","P","Q","U"]
        df = pd.read_excel(filename, sheet_name='USAGEPOINTLOCATIONS')
        for index, row in df.iterrows():
            if lv_network_id is not None and row['FEEDER'] != lv_network_id:
                continue

            lv_network:Network = mv_network.getSubTopology(str(row['FEEDER']))
            if lv_network is None:
                continue
            bus: Bus = lv_network.getBus(str(row['ID']))
            if bus is None:
                logger.error("NODE '{}' not found in LINESEGMENTS".format(row['ID']))
                continue
            feeder_num = (str(int(row["FEEDER_NUM"])) if 'FEEDER_NUM' in row and not pd.isna(row["FEEDER_NUM"]) else None)
            bus.addUsagePointLocation(row['ID'], row['NAME'], [row['LATITUDE'], row['LONGITUDE']] if 'LATITUDE' in row and 'LONGITUDE' in row else None, feeder_num=feeder_num)

        # assume fields ["ID","NAME","FEEDER","FEEDER_NUM","USAGEPOINTLOCATION","RATEDPOWER"]
        df = pd.read_excel(filename, sheet_name='USAGEPOINTS')
        for index, row in df.iterrows():
            if lv_network_id is not None and row['FEEDER'] != lv_network_id:
                continue

            lv_network:Network = mv_network.getSubTopology(str(row['FEEDER']))
            if lv_network is None:
                continue
            usagePointLocation:UsagePointLocation = lv_network.getUsagePointLocation(str(row['USAGEPOINTLOCATION']).replace(".0",""))
            if usagePointLocation is None:
                logger.error("USAGEPOINTLOCATION '{}' not found in USAGEPOINTLOCATIONS".format(row['USAGEPOINTLOCATION']).replace(".0",""))
                continue
            bus:Bus = usagePointLocation.parent
            feeder_num = (str(int(row["FEEDER_NUM"])) if 'FEEDER_NUM' in row and not pd.isna(row["FEEDER_NUM"]) else None)
            up:UsagePoint = bus.addUsagePoint(row['ID'], row['NAME'], usagePointLocation=usagePointLocation, ratedPower=row["RATEDPOWER"], feeder_num=feeder_num)
            usagePointLocation.linkUsagePoint(up)
            
        # assume fields ["ID","NAME","FEEDER","FEEDER_NUM","USAGEPOINTLOCATION","MINP","MAXP","TARGETP","TARGETV","TARGETQ","MINQ","MAXQ","CONTROLLABLE","LATITUDE","LONGITUDE"
        df = pd.read_excel(filename, sheet_name='DERS')
        for index, row in df.iterrows():
            if lv_network_id is not None and row['FEEDER'] != lv_network_id:
                continue

            lv_network:Network = mv_network.getSubTopology(str(row['FEEDER']))
            if lv_network is None:
                continue

            usagePointLocation:UsagePointLocation = lv_network.getUsagePointLocation(str(row['USAGEPOINTLOCATION']).replace(".0",""))
            if usagePointLocation is None:
                logger.error("USAGEPOINTLOCATION '{}' not found in USAGEPOINTLOCATIONS".format(row['USAGEPOINTLOCATION']).replace(".0",""))
                continue
            bus:Bus = usagePointLocation.parent
            feeder_num = (str(int(row["FEEDER_NUM"])) if 'FEEDER_NUM' in row and not pd.isna(row["FEEDER_NUM"]) else None)
            gen:Generator = bus.addGenerator(row['ID'], row['NAME'], usagePointLocation=usagePointLocation, maxP=row["MAXP"], minP=row["MINP"],
                                            targetP=row["TARGETP"], targetV=row["TARGETV"], targetQ=row["TARGETQ"], minQ=row["MINQ"], maxQ=row["MAXQ"],
                                            controllable=row["CONTROLLABLE"] if 'CONTROLLABLE' in row else None, coords=(row['LATITUDE'], row['LONGITUDE']) if 'LATITUDE' in row and 'LONGITUDE' in row else None, feeder_num=feeder_num)
            usagePointLocation.linkUsagePoint(gen)

        # assume fields ["ID","NAME","FEEDER","FEEDER_NUM","USAGEPOINTLOCATION","P","Q"]
        df = pd.read_excel(filename, sheet_name='METERS')
        for index, row in df.iterrows():
            if lv_network_id is not None and row['FEEDER'] != lv_network_id:
                continue

            lv_network:Network = mv_network.getSubTopology(row['FEEDER'])
            if lv_network is None:
                load:Load = mv_network.getLoad(str(row['USAGEPOINT']).replace(".0",""))
                if load is None:
                    mvGen:MvGenerator = mv_network.getGenerator(str(row['USAGEPOINT']).replace(".0",""))
                    if mvGen is None:
                        logger.error("METER '{}' not found in LOADS nor GENERATORS".format(row['ID']).replace(".0",""))
                        continue
                    mvGen.addMeter(row['ID'], row['NAME'], p=row['P'], q=row['Q'])
                else:
                    load.addMeter(row['ID'], row['NAME'], p=row['P'], q=row['Q'])
            else:
                feeder_num = (str(int(row["FEEDER_NUM"])) if 'FEEDER_NUM' in row and not pd.isna(row["FEEDER_NUM"]) else None)
                usagePoint:UsagePoint = lv_network.getUsagePoint(str(row['USAGEPOINT']).replace(".0",""))
                if usagePoint is None:
                    gen:Generator = lv_network.getGenerator(str(row['USAGEPOINT']).replace(".0",""))
                    if gen is None:
                        logger.error("METER '{}' not found in USAGEPOINTS nor DERS".format(row['ID']).replace(".0",""))
                        continue
                    else:
                        gen.addMeter(row['ID'], row['NAME'], p=row['P'], q=row['Q'], feeder_num=feeder_num)
                else:
                    usagePoint.addMeter(row['ID'], row['NAME'], p=row['P'], q=row['Q'], feeder_num=feeder_num)
        return actual_network
