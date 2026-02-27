"""
CLI principal pour EVA

Usage:
    eva                 # Lance REPL interactif
    eva --tui           # Lance le Terminal UI (Textual)
    eva --api           # Lance l'API REST (FastAPI — localhost:8000)
    eva --version       # Affiche version
    eva --help          # Aide
"""

import sys
import argparse
from pathlib import Path

from eva import __version__


def main():
    """Point d'entrée principal CLI."""
    parser = argparse.ArgumentParser(
        prog="eva",
        description="EVA - Assistant IA Personnel",
        epilog="Pour plus d'infos: https://github.com/siridyx/eva"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"EVA {__version__}"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Chemin vers config.yaml personnalisé"
    )

    parser.add_argument(
        "--tui",
        action="store_true",
        help="Lance le Terminal UI (Textual)"
    )

    parser.add_argument(
        "--api",
        action="store_true",
        help="Lance l'API REST (FastAPI — http://localhost:8000)"
    )

    args = parser.parse_args()

    if args.api:
        from eva.api.app import main as api_main
        return api_main()
    elif args.tui:
        from eva.ui.tui.app import main as tui_main
        return tui_main()
    else:
        from eva.repl import main as repl_main
        return repl_main()


if __name__ == "__main__":
    sys.exit(main())