"""
EVA API TLS — Gestionnaire de certificat auto-signe (Phase 6(B))

Genere un certificat TLS auto-signe pour eva --api --tls.
Stocke cert + cle dans eva/data/certs/ (couvert par .gitignore).

Usage :
    manager = CertManager(Path("eva/data"))
    cert, key = manager.ensure()
    uvicorn.run(app, ssl_certfile=cert, ssl_keyfile=key)

Dependances :
    - openssl CLI (present par defaut sur Linux/macOS/Windows avec Git)
    - Aucune dependance Python supplementaire
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class CertManager:
    """
    Gestionnaire de certificat TLS auto-signe pour EVA.

    Genere un certificat RSA 2048 bits valide 365 jours pour localhost.
    Re-genere automatiquement si le cert est absent ou expire sous 24h.

    Usage :
        cert_mgr = CertManager(data_root)
        cert_path, key_path = cert_mgr.ensure()
    """

    CERT_DIR = "certs"
    CERT_FILE = "server.crt"
    KEY_FILE = "server.key"
    VALIDITY_DAYS = 365

    def __init__(self, data_root: Path) -> None:
        """
        Initialise CertManager.

        Args:
            data_root: Racine du dossier data EVA (ex: eva/data/).
                       Le sous-dossier 'certs/' sera cree si absent.
        """
        self._dir = data_root / self.CERT_DIR

    # --- Chemins ---

    @property
    def cert_path(self) -> Path:
        """Chemin vers le fichier certificat (.crt)."""
        return self._dir / self.CERT_FILE

    @property
    def key_path(self) -> Path:
        """Chemin vers la cle privee (.key)."""
        return self._dir / self.KEY_FILE

    # --- API publique ---

    def ensure(self) -> tuple:
        """
        Garantit l'existence d'un certificat valide.

        Si le cert est absent ou expire dans moins de 24h, en genere un nouveau.

        Returns:
            Tuple (cert_path, key_path) — chemins vers les fichiers PEM.

        Raises:
            RuntimeError: Si openssl n'est pas disponible ou echoue.
        """
        if not self._is_valid():
            self._generate()
        return self.cert_path, self.key_path

    def is_generated(self) -> bool:
        """Retourne True si cert et key existent sur disque."""
        return self.cert_path.exists() and self.key_path.exists()

    # --- Internals ---

    def _is_valid(self) -> bool:
        """
        Verifie que cert + key existent et que le cert expire dans plus de 24h.

        Returns:
            True si valide, False sinon.
        """
        if not self.cert_path.exists() or not self.key_path.exists():
            return False
        try:
            # openssl x509 -checkend N : retourne 0 si cert expire dans > N secondes
            result = subprocess.run(
                [
                    "openssl", "x509",
                    "-checkend", "86400",  # 24h en secondes
                    "-noout",
                    "-in", str(self.cert_path),
                ],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def _generate(self) -> None:
        """
        Genere un certificat auto-signe RSA 2048 bits.

        Utilise openssl req en one-shot (cert + cle en une commande).
        SAN (subjectAltName) pour localhost + 127.0.0.1 — evite les warnings
        navigateur sur les champs CN uniquement.

        Raises:
            RuntimeError: Si openssl absent ou echec de generation.
        """
        self._dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "openssl", "req",
            "-x509",
            "-newkey", "rsa:2048",
            "-keyout", str(self.key_path),
            "-out", str(self.cert_path),
            "-days", str(self.VALIDITY_DAYS),
            "-nodes",   # pas de passphrase (serveur non-interactif)
            "-subj", "/CN=localhost/O=EVA/C=FR",
            "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "openssl introuvable. Installez OpenSSL et assurez-vous "
                "qu'il est dans votre PATH pour utiliser --tls."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Timeout lors de la generation du certificat TLS.")

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Echec generation certificat TLS (openssl exit {result.returncode}):\n{stderr}"
            )

        # Restreindre permissions sur la cle privee (best-effort — silencieux sous Windows)
        try:
            self.key_path.chmod(0o600)
        except OSError:
            pass
