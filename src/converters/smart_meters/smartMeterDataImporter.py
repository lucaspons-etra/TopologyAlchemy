
import logging
from base_importer import Importer
from converters.pandapower.ppImporter import PandapowerImporter
from topology import Network


class smartMeterDataImporter(Importer):
    """
    Importer for smart meter data.
    """
    def required_parameters(self) -> dict:
        return {
            "input_folder": None,
            "network_id": None,
            "system": None
        }

    @classmethod
    def name(cls) -> str:
        return "SmartMeterDataImporter"

    async def _import_topology_impl(self, logger: logging.Logger, params: dict = {}) -> Network:
        
        print ("Importing smart meter data from folder " + str(params.get("input_folder")) + "...")
        
        ppImp =PandapowerImporter() 
        network = await ppImp.import_topology(logger=logger, params={
            "input_file": "./tests/results/swisszerlandPP.json",
            "system_id": params.get("system"),
            "network_id": params.get("network_id")
        })
        
        #network = Network(id=params.get("network_id"), name=params.get("network_id"), system=params.get("system"))
        
        print("Smart meter data imported successfully.")
        return network