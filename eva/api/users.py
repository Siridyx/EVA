"""
EVA Users — Gestion multi-utilisateurs locaux (Phase 6(D)).

Modules :
    UserRole  : enum "admin" | "user"
    User      : dataclass representant un utilisateur
    UserStore : stockage SQLite + hash PBKDF2-HMAC-SHA256

Securite :
    - PBKDF2-HMAC-SHA256, 260 000 iterations (OWASP 2024)
    - Salt 32 bytes aleatoires par mot de passe (os.urandom)
    - Comparaison constant-time (secrets.compare_digest)
    - Hash auto-decrit : "pbkdf2:sha256:260000:<salt_hex>:<hash_hex>"
    - Aucune dependance externe (stdlib uniquement : hashlib, sqlite3, secrets)

Usage :
    store = UserStore(Path("eva/data"))
    admin = store.create_user("admin", "s3cr3t", UserRole.ADMIN)
    user  = store.authenticate("admin", "s3cr3t")  # -> User ou None
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Modele
# ---------------------------------------------------------------------------


class UserRole(str, Enum):
    """Role d'un utilisateur EVA."""

    ADMIN = "admin"
    USER = "user"


@dataclass
class User:
    """Representation d'un utilisateur (sans mot de passe)."""

    id: int
    username: str
    role: UserRole


# ---------------------------------------------------------------------------
# UserStore
# ---------------------------------------------------------------------------


class UserStore:
    """
    Stockage utilisateurs SQLite avec hash PBKDF2-HMAC-SHA256.

    Le fichier users.db est cree automatiquement dans data_root/.
    La table users est cree au premier acces.

    Format hash stocke :
        "pbkdf2:sha256:<iterations>:<salt_hex>:<hash_hex>"
        Exemple : "pbkdf2:sha256:260000:a1b2c3...:d4e5f6..."

    Usage :
        store = UserStore(Path("eva/data"))
        store.create_user("alice", "motdepasse", UserRole.ADMIN)
        user = store.authenticate("alice", "motdepasse")
    """

    DB_FILENAME = "users.db"
    HASH_ALGO = "sha256"
    HASH_ITERATIONS = 260_000   # OWASP 2024 minimum pour PBKDF2-SHA256
    SALT_BYTES = 32             # 256 bits d'entropie

    def __init__(self, data_root: Path) -> None:
        """
        Initialise UserStore.

        Args:
            data_root: Racine du dossier data EVA (ex: Path("eva/data")).
                       Le fichier users.db sera cree dans ce dossier.
        """
        self._db_path = data_root / self.DB_FILENAME
        self._init_db()

    # --- Init ---

    def _init_db(self) -> None:
        """Cree la table users si elle n'existe pas."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    username    TEXT    UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role        TEXT    NOT NULL DEFAULT 'user',
                    created_at  REAL    NOT NULL
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        """Ouvre une connexion SQLite avec foreign keys et WAL."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # --- Hashing ---

    def _make_hash(self, password: str) -> str:
        """
        Hash un mot de passe avec PBKDF2-HMAC-SHA256.

        Returns:
            Chaine auto-decrite "pbkdf2:sha256:<iter>:<salt_hex>:<hash_hex>"
        """
        salt = os.urandom(self.SALT_BYTES)
        dk = hashlib.pbkdf2_hmac(
            self.HASH_ALGO,
            password.encode("utf-8"),
            salt,
            self.HASH_ITERATIONS,
        )
        return f"pbkdf2:{self.HASH_ALGO}:{self.HASH_ITERATIONS}:{salt.hex()}:{dk.hex()}"

    def _verify_hash(self, password: str, stored: str) -> bool:
        """
        Verifie un mot de passe contre un hash stocke.

        Comparaison constant-time pour eviter les timing attacks.

        Args:
            password: Mot de passe en clair
            stored:   Hash au format "pbkdf2:algo:iter:salt_hex:hash_hex"

        Returns:
            True si correspondance, False sinon.
        """
        try:
            _, algo, iterations_str, salt_hex, expected_hex = stored.split(":")
        except ValueError:
            return False

        try:
            iterations = int(iterations_str)
            salt = bytes.fromhex(salt_hex)
        except (ValueError, TypeError):
            return False

        dk = hashlib.pbkdf2_hmac(
            algo,
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return secrets.compare_digest(dk.hex(), expected_hex)

    # --- API publique ---

    def create_user(
        self,
        username: str,
        password: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """
        Cree un nouvel utilisateur.

        Args:
            username: Identifiant (converti en minuscules, sans espaces).
            password: Mot de passe en clair (min 8 caracteres).
            role:     Role (admin ou user).

        Returns:
            User cree.

        Raises:
            ValueError: Si username vide/invalide, password trop court,
                        ou username deja existant.
        """
        username = username.strip().lower()
        if not username:
            raise ValueError("Le nom d'utilisateur ne peut pas etre vide.")
        if len(password) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caracteres.")

        password_hash = self._make_hash(password)

        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash, role, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (username, password_hash, role.value, time.time()),
                )
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"L'utilisateur '{username}' existe deja.")

        return User(id=user_id, username=username, role=role)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authentifie un utilisateur par username + password.

        Timing-safe : execute un faux hash si l'utilisateur n'existe pas
        pour eviter les attaques par enumeration de timing.

        Args:
            username: Identifiant
            password: Mot de passe en clair

        Returns:
            User si credentials valides, None sinon.
        """
        username = username.strip().lower()
        row = self._get_row_by_username(username)

        if row is None:
            # Hash factice pour maintenir le timing constant
            self._make_hash("dummy_password_timing_protection")
            return None

        if not self._verify_hash(password, row["password_hash"]):
            return None

        return User(
            id=row["id"],
            username=row["username"],
            role=UserRole(row["role"]),
        )

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retourne un utilisateur par son ID ou None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, role FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return User(id=row["id"], username=row["username"], role=UserRole(row["role"]))

    def get_by_username(self, username: str) -> Optional[User]:
        """Retourne un utilisateur par son username ou None."""
        row = self._get_row_by_username(username.strip().lower())
        if row is None:
            return None
        return User(id=row["id"], username=row["username"], role=UserRole(row["role"]))

    def has_admin(self) -> bool:
        """Retourne True si au moins un admin existe."""
        with self._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin'"
            ).fetchone()[0]
        return count > 0

    def count(self) -> int:
        """Retourne le nombre total d'utilisateurs."""
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    # --- Internals ---

    def _get_row_by_username(self, username: str) -> Optional[sqlite3.Row]:
        """Retourne la ligne complète (avec password_hash) ou None."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
