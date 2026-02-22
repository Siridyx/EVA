"""
Point d'entrée principal pour `python -m eva`
"""

import sys
from eva.cli import main

if __name__ == "__main__":
    sys.exit(main())