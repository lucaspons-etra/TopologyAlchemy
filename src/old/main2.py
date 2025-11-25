import asyncio
import json
import sys
from venv import logger
from Utils import Transliterate, Sanitizer, getLogger
import argparse
import pathlib
import logging
from converters.cim import cimImporter
from converters.excel.ExcelImporter import ExcelImporter
from converters.mongodb.MongodbImporter import MongodbImporter
from converters.powsybl import powSyBlExporter, powsyblImporter
from converters.excel.ExcelImporter import ExcelImporter
from converters.mongodb.mongodbExporter import Mongo_exporter
from converters.mongodb.MongodbImporter import MongodbImporter
from converters.neo4j.neo4jExporter import Neo4jExporter
# from converters.pandapower import pandahubExporter, pandahubmporter

from topology import Network

ALLOWED_EXTENSIONS = {'.rdf', '.cim', '.xml', '.xiidm', '.xlsx', '.json', '.js', '.config','.cdf', '.cypher'}
ALLOWED_INPUTFORMATS = ['cim', 'tabular','pandapower', 'ETER','cdf', 'matpower', 'topologyIdentification']
ALLOWED_OUTPUTFORMATS = ['pandapower', 'ETER', 'neo4j']

logger = None
def excepthook(*args):
  logger.error('Uncaught exception:', exc_info=args)

async def main(argv):
    print("Starting Topology Alchemy...")
    
##########################################################################################       
#  _______                _                              _      _                          
# |__   __|              | |                       /\   | |    | |                         
#    | | ___  _ __   ___ | | ___   __ _ _   _     /  \  | | ___| |__   ___ _ __ ___  _   _ 
#    | |/ _ \| '_ \ / _ \| |/ _ \ / _` | | | |   / /\ \ | |/ __| '_ \ / _ \ '_ ` _ \| | | |
#    | | (_) | |_) | (_) | | (_) | (_| | |_| |  / ____ \| | (__| | | |  __/ | | | | | |_| |
#    |_|\___/| .__/ \___/|_|\___/ \__, |\__, | /_/    \_\_|\___|_| |_|\___|_| |_| |_|\__, |
#            | |                   __/ | __/ |                                        __/ |
#            |_|                  |___/ |___/                                        |___/ 
#
##########################################################################################
    print (argv)
    if len(argv) > 0:
        argv.pop(0)
        #pass
    else:
        return 
    parser = argparse.ArgumentParser(description='This program allows transforming topologies between different formats. It has been developed under the EU research project OPENTUNITY')
    parser.add_argument("--iFormat", help="Input format",
                        action="store", choices=ALLOWED_INPUTFORMATS, required=True)
    parser.add_argument("--input", help="Input file",
                        action="store", type=pathlib.Path, required=False)
    parser.add_argument("--inputUrl", help="Input file",
                        action="store", type=str, required=False)
    parser.add_argument("--oFormat", help="Output format",
                        action="append", choices=ALLOWED_OUTPUTFORMATS, required=True)
    parser.add_argument("--output", help="Output file",
                        action="append", type=pathlib.Path, required=True)
    # parser.add_argument("--preffix", help="Prefix to add to the names",
    #                     action="store", required=True)
    parser.add_argument("--activateTransliterate", help="Transliterate Greek characters",
                        action="store_true", default=False)
    parser.add_argument("--processLV", help="Import LV network",
                        action="store_true", default=False)
    parser.add_argument("--deletePrevious", help="Generate delete commands for previous data",
                        action="store_true", default=False)
    # parser.add_argument("--id", help="Topology id",
    #                     action="store", required=False)
    parser.add_argument("--system", help="System id",
                        action="store", required=False)
    parser.add_argument("--network", help="Network id",
                        action="store", required=False)
    parser.add_argument("--context", help="Context",
                        action="store", required=False)
    parser.add_argument("--verbose", help="Increase output verbosity",
                        action="store_true", default=False)
    parser.add_argument("--log", help="Log level",
                        action="store", default="INFO")
    parser.add_argument("--defaultLayoutMV", help="Default cytoscape layout for MV network",
                        action="store", required=False)
    parser.add_argument("--defaultLayoutLV", help="Default cytoscape layout for LV network",
                        action="store", required=False)
    
    args = parser.parse_args(argv)
    sys.excepthook = excepthook
    global logger
    logger= getLogger(args)
    topology:Network = None
    # logger.info("Starting Topology Alchemy with parameters: " + str(args)
    #                + "\nInput file: " + str(args.input) + "\nOutput files: " + str(args.output))
    # logger.info("Input format: " + str(args.iFormat) + "\nOutput formats: " + str(args.oFormat))
    # logger.info("Starting topology identification analysis...")
    # logger.info("34 smart meters (leaves) in the input file")
    # logger.info("Processing historical record...")
    # logger.info("Process ends after 14 iterations")
    # logger.info("34 smart meters connected from 34 total smart meters")
    # logger.info("Topology conversion to mongodb format starts...")
    # logger.info("Topology conversion ends successfully")
    # logger.info("file 'output.json' saved in the output folder")
    # return 
    try:
        assert args.inputUrl != None or args.input.exists(), "Input file or input url needed. Maybe inout file can't be found"
        #assert args.output.exists(), "Output file '{}' can't be found".format (args.output)
        assert args.inputUrl != None or (args.input.suffix.lower() in ALLOWED_EXTENSIONS) and all(map(lambda x: x.suffix.lower() in ALLOWED_EXTENSIONS, args.output)), "The input or output file extensions are not a known extension file. Known extension files are :" + ','.join([ext for ext in ALLOWED_EXTENSIONS])
        #input = open(args.input,'r', encoding="utf8")
        suffix = args.input.suffix.lower() if args.inputUrl == None else None
        if args.activateTransliterate:
            Transliterate.activateTranslit(translit='greek')
        match args.iFormat:
            case "powsybl":
                topology= powsyblImporter.importTopology(args.input, args.system, logger)
            case "cim" :
                if args.processLV:                
                    topology=cimImporter.importLVTopology(args.input, args.system, logger)
                else:
                    topology=cimImporter.importTopology(args.input, args.system, logger)
            case "ETER":
                importer = MongodbImporter()
                topology = await importer.importTopology(args.inputUrl, args.system, args.network, logger)
            case "tabular":
                match suffix:
                    case ".xlsx":
                        #topology = excelImporter.importTopology(filename=args.input,id=args.id, processLV=args.processLV, logger=logger)
                        importer = ExcelImporter()
                        topology = importer.importTopology(args.input, args.processLV, logger)

        # output = open(args.output,'w', encoding="utf8")
        # match args.output.suffix.lower():
        for i in range(len(args.oFormat)):
            match args.oFormat[i]:
                case "ETER":
                    exporter = Mongo_exporter()
                    ret = exporter.export_topology(topology, args.output[i], args.context, args.system,
                                                         args.defaultLayoutMV, args.defaultLayoutLV, logger)
                case "neo4j":
                    exporter = Neo4jExporter()
                    ret = exporter.export_topology(topology, args.output[i], args.context, args.system,
                                                       args.defaultLayoutMV, args.defaultLayoutLV, logger,
                                                       exportLV=args.processLV)
                # case "pandahub":
                #     ret = pandahubExporter.exportTopology(topology, args.output[i], args.id, logger)    
                #     pass
            
    except Exception as error:
        logger.error(str(error))
        raise error
        
if __name__ == "__main__":
    asyncio.run(main(sys.argv))
