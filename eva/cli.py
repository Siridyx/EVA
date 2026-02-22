"""
CLI principal pour EVA

Usage:
    eva                 # Lance REPL interactif
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
    
    args = parser.parse_args()
    
    # Lancer REPL
    from eva.repl import main as repl_main
    return repl_main()


if __name__ == "__main__":
    sys.exit(main())