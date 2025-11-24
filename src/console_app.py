"""
Topology Alchemy Interactive Console Application

This module provides an interactive command-line interface for using Topology Alchemy
without needing to remember complex command-line arguments. It guides users through
the process of:

1. Selecting an input format (importer)
2. Configuring import parameters
3. Selecting an output format (exporter)
4. Configuring export parameters
5. Optionally selecting and configuring notifiers
6. Executing the conversion

Features:
- Interactive file selection from project directories
- Intelligent parameter type detection and parsing
- JSON/boolean/numeric value parsing
- Colored output for better readability
- Parameter validation
- Confirmation before execution

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.

Usage:
    python console_app.py
"""

import asyncio
import json
import os
import pkgutil
import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

from alchemist import Alchemist
from base_importer import Importer
from base_exporter import Exporter
from base_notifier import Notifier

# Try to import colorama for cross-platform colored output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # Fallback if colorama not available
    class Fore:
        GREEN = RED = YELLOW = CYAN = BLUE = MAGENTA = ''
    class Style:
        BRIGHT = RESET_ALL = ''
    HAS_COLOR = False


def load_classes_from_package(package):
    loaded_classes = []
    for loader, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            module = importlib.import_module(module_name)
        except Exception:
            # ignore import errors for optional modules
            continue

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module_name:
                loaded_classes.append(obj)

    return loaded_classes


def prompt_choice(prompt: str, choices: list, allow_cancel: bool = False) -> int:
    """
    Display a numbered menu and get user selection.
    
    Args:
        prompt: The prompt message to display
        choices: List of choices to present
        allow_cancel: If True, user can type 'q' to quit
        
    Returns:
        Index of selected choice (0-based)
    """
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{prompt}{Style.RESET_ALL}")
    for i, c in enumerate(choices, start=1):
        print(f"  {Fore.GREEN}{i}{Style.RESET_ALL}) {c}")
    if allow_cancel:
        print(f"  {Fore.YELLOW}q{Style.RESET_ALL}) Quit")
    
    while True:
        try:
            sel = input(f"{Fore.CYAN}Select number{' (or q to quit)' if allow_cancel else ''}: {Style.RESET_ALL}").strip()
            if not sel:
                continue
            if allow_cancel and sel.lower() in ('q', 'quit', 'exit'):
                print(f"{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
                sys.exit(0)
            idx = int(sel) - 1
            if 0 <= idx < len(choices):
                return idx
        except ValueError:
            pass
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Cancelled by user.{Style.RESET_ALL}")
            sys.exit(0)
        print(f"{Fore.RED}Invalid selection, try again.{Style.RESET_ALL}")


def parse_value_from_input(raw: str, default: Any) -> Any:
    """
    Parse user input into appropriate Python type.
    
    Attempts to intelligently parse the input as:
    1. Default value if empty
    2. JSON (for numbers, lists, dicts, booleans)
    3. Boolean (for y/n, yes/no, true/false)
    4. Numeric values
    5. String as fallback
    
    Args:
        raw: Raw input string from user
        default: Default value to return if input is empty
        
    Returns:
        Parsed value in appropriate type
    """
    # If user left blank: return default
    if raw is None or raw.strip() == "":
        return default

    text = raw.strip()
    
    # Try to parse JSON (covers numbers, lists, dicts, booleans)
    try:
        return json.loads(text)
    except Exception:
        pass
    
    # Fallback for booleans like 'y'/'n' or 'yes'/'no'
    low = text.lower()
    if low in ("y", "yes", "true", "t", "1"):
        return True
    if low in ("n", "no", "false", "f", "0"):
        return False
    
    # Try to parse as number
    try:
        if '.' in text:
            return float(text)
        return int(text)
    except ValueError:
        pass
    
    # Otherwise return raw string
    return text


def list_files_in_cwd(pattern: str | None = None, limit: int = 200):
    root = Path.cwd()
    search_dir = root / "tests" / "data"
    
    # Fallback to root if tests/data doesn't exist
    if not search_dir.exists():
        search_dir = root
    
    if pattern:
        files = [p for p in search_dir.rglob(pattern) if p.is_file()]
    else:
        files = [p for p in search_dir.rglob('*') if p.is_file()]
    files = sorted(files)
    if len(files) > limit:
        return files[:limit]
    return files


def prompt_file_selection(key: str, default: Any):
    """Interactive file chooser: lists files under tests/data/ and lets user pick one or type custom path."""
    ext = ''
    try:
        ext = Path(str(default)).suffix if default else ''
    except Exception:
        ext = ''

    pattern = f'**/*{ext}' if ext else None
    files = list_files_in_cwd(pattern)
    root = Path.cwd()
    search_dir = root / "tests" / "data"
    if not search_dir.exists():
        search_dir = root

    if files:
        print(f"Select file for parameter '{key}' (from {search_dir.relative_to(root) if search_dir != root else 'current directory'}):")
        for i, p in enumerate(files[:200], start=1):
            try:
                display = str(p.relative_to(root))
            except Exception:
                display = str(p)
            print(f"  {i}) {display}")
        print("  0) Enter custom path")
        print("  c) Cancel / accept default")

        while True:
            sel = input("Select number (or 0 for custom, c to cancel): ").strip()
            if sel.lower() == 'c':
                return default
            if sel == '':
                return default
            if sel == '0':
                custom = input("Enter file path: ").strip()
                return custom if custom else default
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(files):
                    return str(files[idx])
            except Exception:
                pass
            print("Invalid selection, try again.")
    else:
        custom = input(f"No files found in {search_dir}. Enter path for '{key}' (or Enter to accept default): ").strip()
        return custom if custom else default


def prompt_for_params(required: Dict[str, Any]) -> Dict[str, Any]:
    params = {}
    if not required:
        return params
    print("Enter parameters (press Enter to accept default shown in brackets)")
    for key, default in required.items():
        # detect file/path-like parameter names
        is_file_param = any(x in key.lower() for x in ("file", "path", "dir", "folder"))
        # also consider Path defaults
        if isinstance(default, (str, Path)) and default and (os.path.exists(str(default)) or os.path.splitext(str(default))[1]):
            is_file_param = True

        display_default = json.dumps(default) if isinstance(default, (dict, list)) else str(default)
        if default is None:
            prompt = f"  {key} [REQUIRED]: "
        else:
            prompt = f"  {key} [{display_default}]: "

        # If this looks like a file/path parameter, offer an interactive file selector
        if is_file_param:
            val = prompt_file_selection(key, default)
            if default is None and (val is None or (isinstance(val, str) and val.strip() == "")):
                print(f"Parameter '{key}' is required. Please provide a value.")
                # fall back to text prompt
            else:
                params[key] = val
                continue

        while True:
            raw = input(prompt)
            val = parse_value_from_input(raw, default)
            if default is None and (val is None or (isinstance(val, str) and val.strip() == "")):
                print(f"Parameter '{key}' is required. Please provide a value.")
                continue
            params[key] = val
            break

    return params


async def run_alchemist(importer_name: str, importer_params: dict, exporter_name: str, exporter_params: dict, notifier_name: str, notifier_params: dict, log_level: str = 'INFO') -> bool:
    importer = Importer.get_importer(importer_name)
    exporter = Exporter.get_exporter(exporter_name)
    notifier = Notifier.get_notifier(notifier_name) if notifier_name else None

    if importer is None:
        print(f"Importer '{importer_name}' not found")
        return False
    if exporter is None:
        print(f"Exporter '{exporter_name}' not found")
        return False

    al = Alchemist(log_level)

    # Build flat params dict similar to CLI: merge all parameters
    all_params = {**importer_params, **exporter_params}
    # alchemist expects notifier_params as a JSON string (list)
    all_params['notifier_params'] = json.dumps([notifier_params]) if notifier else '[]'

    base_notifiers = [notifier] if notifier else None

    return await al.process(importer, exporter, base_notifiers, all_params)


def main():
    print(f"""{Fore.CYAN}{Style.BRIGHT}
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║  _______                _                              _      _                     ║
║ |__   __|              | |                       /\   | |    | |                    ║
║    | | ___  _ __   ___ | | ___   __ _ _   _     /  \  | | ___| |__   ___ _ __ ___  ║
║    | |/ _ \| '_ \ / _ \| |/ _ \ / _` | | | |   / /\ \ | |/ __| '_ \ / _ \ '_ ` _ \ ║
║    | | (_) | |_) | (_) | | (_) | (_| | |_| |  / ____ \| | (__| | | |  __/ | | | | |║
║    |_|\___/| .__/ \___/|_|\___/ \__, |\__, | /_/    \_\_|\___|_| |_|\___|_| |_| |_|║
║            | |                   __/ | __/ |                                        ║
║            |_|                  |___/ |___/                                         ║
║                                                                                      ║
║  {Fore.YELLOW}Interactive Console - OPENTUNITY EU Project{Fore.CYAN}                                  ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}""")
    print(f"{Fore.YELLOW}{Style.BRIGHT}Welcome to Topology Alchemy Interactive Console{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}This tool guides you through topology conversion operations.{Style.RESET_ALL}")
    print(f"{Fore.RED}WARNING: This tool may overwrite existing files. Use with caution.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Press Ctrl+C at any time to cancel.{Style.RESET_ALL}\n")

    # Ensure converters and notifiers packages are imported so classes register
    try:
        import converters  # noqa: F401
    except Exception:
        pass
    try:
        import notifiers  # noqa: F401
    except Exception:
        pass

    # Load packages to ensure submodules are imported
    try:
        import converters as conv_pkg
        load_classes_from_package(conv_pkg)
    except Exception:
        pass
    try:
        import notifiers as notif_pkg
        load_classes_from_package(notif_pkg)
    except Exception:
        pass

    # Present importers
    importers = sorted(Importer.importers.keys())
    if not importers:
        print(f"{Fore.RED}No importers found. Make sure converters package is available.{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}Step 1/5: Select Input Format{Style.RESET_ALL}")
    idx = prompt_choice("Select input format (importer):", importers, allow_cancel=True)
    importer_name = importers[idx]
    importer_inst = Importer.get_importer(importer_name)
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}Step 2/5: Configure Importer{Style.RESET_ALL}")
    importer_params = prompt_for_params(importer_inst.required_parameters())

    # Exporter
    exporters = sorted(Exporter.exporters.keys())
    if not exporters:
        print(f"{Fore.RED}No exporters found. Make sure converters package is available.{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}Step 3/5: Select Output Format{Style.RESET_ALL}")
    idx = prompt_choice("Select output format (exporter):", exporters)
    exporter_name = exporters[idx]
    exporter_inst = Exporter.get_exporter(exporter_name)
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}Step 4/5: Configure Exporter{Style.RESET_ALL}")
    exporter_params = prompt_for_params(exporter_inst.required_parameters())

    # Notifier
    notifiers_list = sorted(Notifier.notifiers.keys())
    notifier_name = None
    notifier_params = {}
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}Step 5/5: Optional Post-Processing{Style.RESET_ALL}")
    if notifiers_list:
        choices = ["None (skip post-processing)"] + notifiers_list
        idx = prompt_choice("Select notifier (optional):", choices)
        if idx > 0:
            notifier_name = choices[idx]
            notifier_inst = Notifier.get_notifier(notifier_name)
            notifier_params = prompt_for_params(notifier_inst.required_parameters())
    else:
        print(f"{Fore.YELLOW}No notifiers available.{Style.RESET_ALL}")

    # Optional log level
    print(f"\n{Fore.CYAN}Additional Settings:{Style.RESET_ALL}")
    log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    log_level = input(f"Log level {Fore.GREEN}[INFO]{Style.RESET_ALL}: ").strip().upper() or 'INFO'
    if log_level not in log_levels:
        print(f"{Fore.YELLOW}Invalid log level, using INFO{Style.RESET_ALL}")
        log_level = 'INFO'

    # Print summary
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}Configuration Summary{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Importer:{Style.RESET_ALL} {Fore.GREEN}{importer_name}{Style.RESET_ALL}")
    print("  Parameters:")
    for k, v in importer_params.items():
        print(f"    {k}: {Fore.CYAN}{v}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}Exporter:{Style.RESET_ALL} {Fore.GREEN}{exporter_name}{Style.RESET_ALL}")
    print("  Parameters:")
    for k, v in exporter_params.items():
        print(f"    {k}: {Fore.CYAN}{v}{Style.RESET_ALL}")
    
    if notifier_name:
        print(f"\n{Fore.YELLOW}Notifier:{Style.RESET_ALL} {Fore.GREEN}{notifier_name}{Style.RESET_ALL}")
        print("  Parameters:")
        for k, v in notifier_params.items():
            print(f"    {k}: {Fore.CYAN}{v}{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}Notifier:{Style.RESET_ALL} {Fore.CYAN}None{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}Log Level:{Style.RESET_ALL} {Fore.CYAN}{log_level}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}{Style.RESET_ALL}\n")
    
    confirm = input(f"{Fore.YELLOW}{Style.BRIGHT}Execute Alchemist process now? (y/N): {Style.RESET_ALL}").strip().lower()
    if confirm not in ('y', 'yes'):
        print(f"{Fore.YELLOW}Aborted by user.{Style.RESET_ALL}")
        return

    # Run
    print(f"\n{Fore.CYAN}{Style.BRIGHT}Starting Topology Alchemy process...{Style.RESET_ALL}\n")
    try:
        ok = asyncio.run(run_alchemist(
            importer_name, importer_params, 
            exporter_name, exporter_params, 
            notifier_name, notifier_params, 
            log_level
        ))
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*80}{Style.RESET_ALL}")
        if ok:
            print(f"{Fore.GREEN}{Style.BRIGHT}Process completed successfully!{Style.RESET_ALL}")
            if 'output_file' in exporter_params:
                print(f"{Fore.CYAN}Output saved to: {Fore.GREEN}{exporter_params['output_file']}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{Style.BRIGHT}Process failed. Check logs above for details.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}{Style.RESET_ALL}\n")
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Cancelled by user.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}{Style.BRIGHT}Error executing process:{Style.RESET_ALL}")
        print(f"{Fore.RED}{e}{Style.RESET_ALL}")
        import traceback
        if log_level == 'DEBUG':
            print(f"\n{Fore.YELLOW}Full traceback:{Style.RESET_ALL}")
            traceback.print_exc()


if __name__ == '__main__':
    main()
