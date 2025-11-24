"""
Topology Alchemy - Main Entry Point

This is the command-line interface (CLI) entry point for the Topology Alchemy framework.
It provides a flexible command-line tool for converting electrical grid topology data
between various formats.

The main function:
1. Dynamically loads all available importers, exporters, and notifiers
2. Parses command-line arguments
3. Instantiates the requested importer and exporter
4. Invokes the Alchemist engine to perform the conversion
5. Returns success/failure status

Command-line usage:
    python main.py --iFormat <importer> --oFormat <exporter> [OPTIONS]

Required arguments:
    --iFormat: Input format (importer class name)
    --oFormat: Output format (exporter class name)

Optional arguments:
    --nFormat: Notifier format(s) - can be specified multiple times
    --logLevel: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    Plus any format-specific parameters required by the importer/exporter

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.
Developed as part of the EU Horizon 2020 research and innovation programme.
"""

import argparse
from alchemist import Alchemist
import sys
import asyncio

from base_importer import Importer
from base_exporter import Exporter
import pkgutil
import importlib
import inspect
from base_notifier import Notifier
import converters  # your top-level package
import notifiers  # your top-level package

def load_classes_from_package(package):
    loaded_classes = []

    for loader, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        module = importlib.import_module(module_name)

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module_name:
                loaded_classes.append(obj)

    return loaded_classes


async def main(argc, argv ):
    
    classes = load_classes_from_package(converters)
    classes = classes + load_classes_from_package(notifiers)
    for cls in classes:
        print(f"Loaded class: {cls.__name__}")
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║  _______                _                              _      _                     ║
║ |__   __|              | |                       /\\   | |    | |                    ║
║    | | ___  _ __   ___ | | ___   __ _ _   _     /  \\  | | ___| |__   ___ _ __ ___  ║
║    | |/ _ \\| '_ \\ / _ \\| |/ _ \\ / _` | | | |   / /\\ \\ | |/ __| '_ \\ / _ \\ '_ ` _ \\ ║
║    | | (_) | |_) | (_) | | (_) | (_| | |_| |  / ____ \\| | (__| | | |  __/ | | | | |║
║    |_|\\___/| .__/ \\___/|_|\\___/ \\__, |\\__, | /_/    \\_\\_|\\___|_| |_|\\___|_| |_| |_|║
║            | |                   __/ | __/ |                                        ║
║            |_|                  |___/ |___/                                         ║
║                                                                                      ║
║  Starting Topology Alchemy...                                                       ║
║  EU Project OPENTUNITY                                                              ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
""")

    parser = argparse.ArgumentParser(description='This program allows transforming topologies between different formats. It has been developed under the EU research project OPENTUNITY')
    parser.add_argument("--iFormat", help="Input format",
                        action="store", choices=Importer.importers.keys(), required=True)
    parser.add_argument("--oFormat", help="Output format",
                        action="store", choices=Exporter.exporters.keys(), required=True)
    parser.add_argument("--nFormat", help="Notifier format (can be repeated or comma-separated)",
                        action="append", choices=Notifier.notifiers.keys(), required=False)
    parser.add_argument("--logLevel", help="Logging level",
                        action="store", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO')
    
    
    try:
        args, unknown_args = parser.parse_known_args(argv)
        
        # Process unknown arguments and add them to args
        unknown_dict = {}
        i = 0
        while i < len(unknown_args):
            if unknown_args[i].startswith('--'):
                key = unknown_args[i][2:]  # Remove '--' prefix
                if i + 1 < len(unknown_args) and not unknown_args[i + 1].startswith('--'):
                    # Next argument is the value
                    unknown_dict[key] = unknown_args[i + 1]
                    i += 2
                else:
                    # Flag without value (set to True)
                    unknown_dict[key] = True
                    i += 1
            else:
                i += 1
        
        # Merge known and unknown arguments
        all_args = {**args.__dict__, **unknown_dict}
        
        importer = Importer.get_importer(args.iFormat)
        exporter = Exporter.get_exporter(args.oFormat)
        # Support multiple --nFormat flags and comma-separated lists
        nformats = []
        if getattr(args, 'nFormat', None):
            for nf in args.nFormat:
                if isinstance(nf, str):
                    # allow comma-separated values inside each occurrence
                    nformats.extend([s for s in (nf.split(",") if nf else []) if s])
        notifiers_ = [Notifier.get_notifier(x) for x in nformats] if nformats else None
        alchemist = Alchemist(args.logLevel)
        ret = await alchemist.process(importer, exporter, notifiers_, all_args)
    except Exception as e:
        print(f"Error occurred: {e}")
        raise e
    if ret:
        print("Topology Alchemy completed successfully.")
    else:
        print("Topology Alchemy failed.")
    return ret    

if __name__ == "__main__":
    asyncio.run(main(sys.argv[0], sys.argv[1:]))
