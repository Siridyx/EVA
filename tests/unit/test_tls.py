"""Tests unitaires pour CertManager (Phase 6(B))."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eva.api.tls import CertManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_data(tmp_path):
    """Répertoire data temporaire."""
    return tmp_path


@pytest.fixture
def mgr(tmp_data):
    """CertManager pointant sur un dossier temporaire."""
    return CertManager(tmp_data)


# ---------------------------------------------------------------------------
# Tests — initialisation
# ---------------------------------------------------------------------------


def test_init_paths(tmp_data):
    """cert_path et key_path pointent vers le bon dossier."""
    mgr = CertManager(tmp_data)
    assert mgr.cert_path == tmp_data / "certs" / "server.crt"
    assert mgr.key_path == tmp_data / "certs" / "server.key"


def test_init_not_generated(mgr):
    """Sans generate, is_generated() retourne False."""
    assert not mgr.is_generated()


# ---------------------------------------------------------------------------
# Tests — is_valid (via _is_valid interne)
# ---------------------------------------------------------------------------


def test_not_valid_when_files_missing(mgr):
    """Pas valide si les fichiers n'existent pas."""
    assert not mgr._is_valid()


def test_not_valid_when_only_cert(mgr):
    """Pas valide si seulement le cert existe (pas la cle)."""
    mgr._dir.mkdir(parents=True)
    mgr.cert_path.write_text("fake cert")
    assert not mgr._is_valid()


# ---------------------------------------------------------------------------
# Tests — generate (réel via openssl)
# ---------------------------------------------------------------------------


def test_ensure_creates_files(mgr):
    """ensure() crée cert et key."""
    cert, key = mgr.ensure()
    assert cert.exists()
    assert key.exists()


def test_ensure_returns_correct_paths(mgr):
    """ensure() retourne les chemins corrects."""
    cert, key = mgr.ensure()
    assert cert == mgr.cert_path
    assert key == mgr.key_path


def test_ensure_cert_is_pem(mgr):
    """Le cert généré est au format PEM."""
    cert, _ = mgr.ensure()
    content = cert.read_text()
    assert "-----BEGIN CERTIFICATE-----" in content
    assert "-----END CERTIFICATE-----" in content


def test_ensure_key_is_pem(mgr):
    """La clé générée est au format PEM."""
    _, key = mgr.ensure()
    content = key.read_text()
    assert "-----BEGIN" in content  # PRIVATE KEY ou RSA PRIVATE KEY


def test_ensure_idempotent(mgr):
    """Deux appels à ensure() retournent le même cert (pas de regénération)."""
    cert1, key1 = mgr.ensure()
    mtime1 = cert1.stat().st_mtime
    cert2, key2 = mgr.ensure()
    mtime2 = cert2.stat().st_mtime
    assert mtime1 == mtime2  # fichier non modifié


def test_ensure_creates_certs_subdir(tmp_data):
    """ensure() crée le sous-dossier certs/ si absent."""
    mgr = CertManager(tmp_data)
    assert not (tmp_data / "certs").exists()
    mgr.ensure()
    assert (tmp_data / "certs").exists()


def test_is_generated_after_ensure(mgr):
    """is_generated() retourne True après ensure()."""
    assert not mgr.is_generated()
    mgr.ensure()
    assert mgr.is_generated()


# ---------------------------------------------------------------------------
# Tests — erreurs
# ---------------------------------------------------------------------------


def test_ensure_raises_if_openssl_missing(mgr):
    """ensure() lève RuntimeError si openssl n'est pas disponible."""
    with patch("subprocess.run", side_effect=FileNotFoundError("openssl not found")):
        with pytest.raises(RuntimeError, match="openssl introuvable"):
            mgr.ensure()


def test_ensure_raises_if_openssl_fails(mgr):
    """ensure() lève RuntimeError si openssl retourne un code d'erreur."""
    failed_result = MagicMock()
    failed_result.returncode = 1
    failed_result.stderr = b"some openssl error"

    # Premier run (checkend) : fichier absent -> FileNotFoundError (pas openssl, fichier)
    # On simule : checkend absent -> invalide -> _generate -> openssl echoue
    with patch("subprocess.run", return_value=failed_result):
        with pytest.raises(RuntimeError, match="Echec generation"):
            mgr.ensure()
