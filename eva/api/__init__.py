"""
EVA API — REST FastAPI (R-031).

Interface HTTP construite sur le contrat R-033.
Lancement : eva --api
Docs : http://localhost:8000/docs
"""

from eva.api.app import EvaState, app, main

__all__ = [
    "app",
    "main",
    "EvaState",
]
