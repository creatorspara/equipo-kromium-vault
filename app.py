"""
Kromium Vault - Main Application Entry Point (app.py)
======================================================
Senior Security Engineer Implementation

Usage:
    python app.py                    # Launches the Desktop GUI application (Default)
    python app.py --cli              # Launches the interactive Terminal / Dialog workflow
    python app.py -e <file>          # Encrypts <file> directly via CLI
    python app.py -d <kromium_file>  # Decrypts <kromium_file> directly via CLI
    python app.py -i <kromium_file>  # Displays container metadata
"""

import sys
import os

# Add package directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    # If explicit CLI flags are provided, redirect to CLI handler
    cli_flags = {
        "--cli", "-t", "--text", "-e", "--encrypt", "-d", "--decrypt",
        "-i", "--info", "--help", "-h", "--interactive", "--view", "--keep-source"
    }
    if any(arg in cli_flags for arg in sys.argv[1:]):
        from cli import handle_cli_arguments
        # Strip --cli if present so argparse doesn't reject it
        if "--cli" in sys.argv:
            sys.argv.remove("--cli")
            if len(sys.argv) == 1:
                sys.argv.append("--interactive")
        handle_cli_arguments()
        return

    # Default: Launch Desktop GUI
    try:
        from ui import run_gui
        run_gui()
    except Exception as e:
        print(f"[!] Graphical Desktop Environment failed to launch ({e}).")
        print("[*] Automatically falling back to interactive console workflow...\n")
        from cli import interactive_workflow
        interactive_workflow()


if __name__ == "__main__":
    main()
