"""
EVA API Security — Auth + Rate Limiting (Phase 4(B)).

Modules :
    ApiKeyManager : génère/charge la clé API depuis eva/data/secrets/api_key.txt
    RateLimiter   : 60 req/min par IP, in-memory, fenêtre glissante 60s

Principes de sécurité :
    - secrets.token_hex(32) : clé 64 hex, entropie 256 bits
    - secrets.compare_digest : comparaison constant-time (protection timing attacks)
    - chmod 600 sur le fichier clé (Unix — ignoré silencieusement sous Windows)
    - Dossier eva/data/secrets/ couvert par .gitignore (eva/data/**)
"""

from __future__ import annotations

import os
import secrets
import time
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Optional


# ---------------------------------------------------------------------------
# API Key Manager
# ---------------------------------------------------------------------------


class ApiKeyManager:
    """
    Gestionnaire de la clé API EVA.

    Génère une clé aléatoire au premier lancement et la persiste dans
    eva/data/secrets/api_key.txt. Les lancements suivants rechargent la clé
    existante.

    Usage :
        km = ApiKeyManager(config.get_path("secrets"))
        key = km.load_or_generate()  # À appeler une fois au startup
        if km.verify(provided_key):
            ...  # Clé valide
    """

    KEY_FILENAME = "api_key.txt"
    KEY_BYTES = 32  # 32 bytes → 64 chars hex → 256 bits d'entropie

    def __init__(self, secrets_dir: Path) -> None:
        """
        Args:
            secrets_dir: Répertoire de stockage des secrets (eva/data/secrets/).
        """
        self._secrets_dir: Path = secrets_dir
        self._key_path: Path = secrets_dir / self.KEY_FILENAME
        self._api_key: Optional[str] = None

    def load_or_generate(self) -> str:
        """
        Charge la clé existante depuis le fichier ou en génère une nouvelle.

        Comportement :
            - Premier lancement : génère une clé, l'écrit dans api_key.txt, chmod 600
            - Lancements suivants : lit la clé depuis api_key.txt

        Returns:
            Clé API (hex string 64 chars)
        """
        # Créer le répertoire si nécessaire
        self._secrets_dir.mkdir(parents=True, exist_ok=True)

        # Charger clé existante
        if self._key_path.exists():
            key = self._key_path.read_text(encoding="utf-8").strip()
            if key:
                self._api_key = key
                return key

        # Générer une nouvelle clé
        key = secrets.token_hex(self.KEY_BYTES)
        self._key_path.write_text(key, encoding="utf-8")

        # Restreindre permissions (Unix uniquement)
        try:
            os.chmod(self._key_path, 0o600)
        except OSError:
            # Windows ne supporte pas chmod — ignoré silencieusement
            pass

        self._api_key = key
        return key

    def verify(self, provided: str) -> bool:
        """
        Vérifie une clé fournie de façon constant-time.

        Protection contre les timing attacks : secrets.compare_digest
        garantit un temps d'exécution identique quelle que soit la position
        du premier caractère différent.

        Args:
            provided: Clé à vérifier

        Returns:
            True si la clé correspond, False sinon
        """
        if self._api_key is None:
            return False
        return secrets.compare_digest(provided, self._api_key)

    @property
    def key(self) -> Optional[str]:
        """Clé API courante (None si non chargée)."""
        return self._api_key


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """
    Rate limiter in-memory par IP — fenêtre glissante.

    Algorithme : sliding window avec deque de timestamps.
    Chaque IP dispose d'un bucket (deque) contenant les timestamps
    des requêtes récentes. Les timestamps expirés sont purgés à chaque appel.

    Avantages :
        - Simple, sans dépendance externe (pas Redis)
        - Fenêtre glissante : pas d'effet bord en début de fenêtre
        - Reset automatique si l'API redémarre (acceptable Phase 4)

    Usage :
        rl = RateLimiter(max_per_min=60)
        if not rl.is_allowed(client_ip):
            raise HTTPException(429, ...)
    """

    def __init__(self, max_per_min: int = 60) -> None:
        """
        Args:
            max_per_min: Nombre maximum de requêtes par IP par minute.
        """
        # Pourquoi stocker max_per_min et pas max_per_window :
        # La fenêtre est toujours 60s pour Phase 4 — configurable en Phase 5.
        self._max: int = max_per_min
        self._window: float = 60.0  # secondes
        self._buckets: Dict[str, Deque[float]] = {}

    def is_allowed(self, ip: str) -> bool:
        """
        Vérifie si une requête depuis `ip` est autorisée.

        Purge les timestamps expirés avant la vérification.

        Args:
            ip: Adresse IP du client

        Returns:
            True si sous la limite, False si dépassée (→ HTTP 429)
        """
        now = time.monotonic()
        cutoff = now - self._window

        if ip not in self._buckets:
            self._buckets[ip] = deque()

        bucket = self._buckets[ip]

        # Purger les timestamps hors fenêtre
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        # Vérifier la limite
        if len(bucket) >= self._max:
            return False

        bucket.append(now)
        return True
