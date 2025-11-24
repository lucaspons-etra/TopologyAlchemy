import logging

from powersystem_analysis import EterPowerNetwork
from sympy import false
from base_importer import Importer
from topology import Bus, Network, Substation, UsagePointLocation, VoltageLevel


class MongodbImporter(Importer):
    
    @classmethod
    def name(cls) -> str:
        return "MongodbImporter"

    async def _import_topology_impl(self, logger: logging.Logger, params: dict = {}) -> Network:
        # Implementation for importing topology from MongoDB
        self.eter = EterPowerNetwork(mongo_uri=params.get("mongo_uri"))
        await self.eter.create_network(
            bus_query={"system":params.get("system_id"),"network":params.get("network_id")},
        )
        topology:Network = Network(params.get("system_id"),params.get("network_id"))  # Use id as both id and name

        for bus in self.eter.power_network.buses.values():
            if "voltageLevel" in bus[1]:
                topology.addVoltageLevel(id=bus[1]["voltageLevel"],name=bus[1]["voltageLevel"], nominalV=int(bus[1]["nominalV"]) if "nominalV" in bus[1] else 0,type=bus[1]["type"])
            if "substation" in bus[1]:
                sub:Substation = topology.addSubstation(id=bus[1]["substation"],name=bus[1]["substation"])
                sub.addBus(bus[1]["_id"], bus[1]["name"], topology.getElement("voltageLevels", bus[1]["voltageLevel"]))
            else:
                bus:Bus = topology.addBus(bus[1]["_id"], bus[1]["name"], topology.getElement("voltageLevels", bus[1]["voltageLevel"]))

        for trafo in self.eter.power_network.trafos.values(): 
            substation:Substation =  topology.getSubstation(trafo[1]["substation"])
            substation.addTransformer(trafo[1]["_id"],trafo[1]["name"],topology.getElement("voltageLevels", trafo[1]["voltageLevel1"]),substation.getElement("voltageLevels", trafo[1]["voltageLevel2"]),
                                      r= trafo[1]["r"], x= trafo[1]["x"], g= trafo[1]["g"], b= trafo[1]["b"], nominal= trafo[1]["ratedApparentPower"])
        for trafo3 in self.eter.power_network.trafos3w.values(): 
            substation:Substation =  topology.getSubstation(trafo3[1]["substation"])
            substation.addTriTransformer(trafo3[1]["_id"],trafo3[1]["name"],
                                       topology.getBus(trafo3[1]["bus1"]),
                                       substation.getBus(trafo3[1]["bus2"]),
                                       substation.getBus(trafo3[1]["bus3"]),
                                      r1= trafo3[1]["r1"], x1= trafo3[1]["x1"],g1= trafo3[1]["g1"], b1= trafo3[1]["b1"],
                                      r2= trafo3[1]["r2"], x2= trafo3[1]["x2"],g2= trafo3[1]["g2"], b2= trafo3[1]["b2"],
                                      r3= trafo3[1]["r3"], x3= trafo3[1]["x3"],g3= trafo3[1]["g3"], b3= trafo3[1]["b3"],
                                      g= trafo3[1]["g"], b= trafo3[1]["b"],
                                      nominal= trafo3[1]["ratedApparentPower"])
        for line in self.eter.power_network.lines.values(): 
            bus1:Bus = topology.getBus(line[1]["bus1"])
            bus2:Bus = topology.getBus(line[1]["bus2"])
            topology.addLine(line[1]["_id"],line[1]["name"],bus1,bus2,
                          r= line[1]["r"], x= line[1]["x"], b1= line[1]["b1"], 
                          b2=line[1]["b2"], g1= line[1]["g1"], g2= line[1]["g2"], 
                          length= line[1]["length"], cable= line[1]["cable"], 
                          feeder_num= line[1]["feederNumber"], currentLimit= line[1]["currentLimit"],  )
        for switch in self.eter.power_network.switches.values(): 
            topology.addSwitch(switch[1]["_id"],switch[1]["name"],topology.getBus(line[1]["bus1"]),
                               topology.getBus(switch[1]["bus2"]))
        for usage_point in self.eter.power_network.usage_points.values(): 
            bus:Bus = topology.getBus(usage_point[1]["bus"])
            upl:UsagePointLocation = bus.addUsagePointLocation(usage_point[1]["_id"], usage_point[1]["name"], feeder_num=usage_point[1]["feederNumber"] if "feederNumber" in usage_point[1] else None)
            bus.addUsagePoint(usage_point[1]["_id"], usage_point[1]["name"], usagePointLocation=upl, ratedPower=usage_point[1]["ratedPower"] if "ratedPower" in usage_point[1] else None, feeder_num=usage_point[1]["feederNumber"] if "feederNumber" in usage_point[1] else None   )
        
        for generator in self.eter.power_network.generators.values(): 
            bus:Bus = topology.getBus(generator[1]["bus"])
            upl:UsagePointLocation = bus.addUsagePointLocation(generator[1]["_id"], generator[1]["name"], feeder_num=generator[1]["feederNumber"] if "feederNumber" in generator[1] else None)
            bus.addGenerator(generator[1]["_id"], generator[1]["name"], usagePointLocation=upl, ratedPower=generator[1]["installedPower"] if "installedPower" in generator[1] else None, feeder_num=generator[1]["feederNumber"] if "feederNumber" in generator[1] else None   )
        logger.info("> MongoDB topology import completed successfully")
        return topology
    
    def required_parameters(self) -> dict:
        return {
            "mongo_uri": None,  # MongoDB connection string
            "system_id": None,   # System identifier
            "network_id": None   # Network identifier
        }