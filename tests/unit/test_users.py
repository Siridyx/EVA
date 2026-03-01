"""Tests unitaires pour UserStore et SessionManager (Phase 6(D))."""

import pytest
from pathlib import Path

from eva.api.users import User, UserRole, UserStore
from eva.api.security import SessionManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    """UserStore pointant sur un dossier temporaire."""
    return UserStore(tmp_path)


@pytest.fixture
def admin(store):
    """Admin pre-cree."""
    return store.create_user("admin", "MotdePasse1!", UserRole.ADMIN)


# ---------------------------------------------------------------------------
# Tests — creation utilisateur
# ---------------------------------------------------------------------------


def test_create_user_returns_user(store):
    user = store.create_user("alice", "password123")
    assert isinstance(user, User)
    assert user.username == "alice"
    assert user.role == UserRole.USER
    assert user.id > 0


def test_create_user_admin_role(store):
    user = store.create_user("bob", "password123", UserRole.ADMIN)
    assert user.role == UserRole.ADMIN


def test_create_user_lowercases_username(store):
    user = store.create_user("Alice", "password123")
    assert user.username == "alice"


def test_create_user_duplicate_raises(store):
    store.create_user("alice", "password123")
    with pytest.raises(ValueError, match="existe deja"):
        store.create_user("alice", "autrepass1")


def test_create_user_empty_username_raises(store):
    with pytest.raises(ValueError, match="ne peut pas etre vide"):
        store.create_user("", "password123")


def test_create_user_short_password_raises(store):
    with pytest.raises(ValueError, match="8 caracteres"):
        store.create_user("alice", "court")


# ---------------------------------------------------------------------------
# Tests — hash + verify password
# ---------------------------------------------------------------------------


def test_hash_is_pbkdf2_format(store):
    """Le hash stocke est au format pbkdf2:sha256:iter:salt:hash."""
    h = store._make_hash("monpassword")
    parts = h.split(":")
    assert len(parts) == 5
    assert parts[0] == "pbkdf2"
    assert parts[1] == "sha256"
    assert int(parts[2]) >= 100_000  # iterations OWASP minimum


def test_verify_correct_password(store):
    h = store._make_hash("monpassword")
    assert store._verify_hash("monpassword", h) is True


def test_verify_wrong_password(store):
    h = store._make_hash("monpassword")
    assert store._verify_hash("mauvaispass", h) is False


def test_two_hashes_same_password_differ(store):
    """Deux hashs du meme password doivent etre differents (salt aleatoire)."""
    h1 = store._make_hash("monpassword")
    h2 = store._make_hash("monpassword")
    assert h1 != h2


# ---------------------------------------------------------------------------
# Tests — login incorrect
# ---------------------------------------------------------------------------


def test_authenticate_valid(store, admin):
    user = store.authenticate("admin", "MotdePasse1!")
    assert user is not None
    assert user.username == "admin"
    assert user.role == UserRole.ADMIN


def test_authenticate_wrong_password(store, admin):
    result = store.authenticate("admin", "mauvaispass")
    assert result is None


def test_authenticate_unknown_user(store):
    result = store.authenticate("inconnu", "nimportequoi")
    assert result is None


def test_authenticate_case_insensitive_username(store, admin):
    user = store.authenticate("ADMIN", "MotdePasse1!")
    assert user is not None


# ---------------------------------------------------------------------------
# Tests — isolation / separation donnees par user_id
# ---------------------------------------------------------------------------


def test_get_by_id(store, admin):
    found = store.get_by_id(admin.id)
    assert found is not None
    assert found.username == "admin"


def test_get_by_id_unknown(store):
    assert store.get_by_id(9999) is None


def test_get_by_username(store, admin):
    found = store.get_by_username("admin")
    assert found is not None
    assert found.id == admin.id


def test_get_by_username_unknown(store):
    assert store.get_by_username("inconnu") is None


def test_multiple_users_isolated(store):
    """Deux utilisateurs ont des IDs distincts et ne se melangent pas."""
    u1 = store.create_user("user1", "password_u1")
    u2 = store.create_user("user2", "password_u2")
    assert u1.id != u2.id

    # Chaque user authentifie avec ses propres credentials
    r1 = store.authenticate("user1", "password_u1")
    r2 = store.authenticate("user2", "password_u2")
    assert r1 is not None and r1.id == u1.id
    assert r2 is not None and r2.id == u2.id

    # Credentials croises echouent
    assert store.authenticate("user1", "password_u2") is None
    assert store.authenticate("user2", "password_u1") is None


def test_has_admin_false_initially(store):
    assert not store.has_admin()


def test_has_admin_true_after_create(store, admin):
    assert store.has_admin()


def test_count(store):
    assert store.count() == 0
    store.create_user("a", "password_a1")
    assert store.count() == 1
    store.create_user("b", "password_b1")
    assert store.count() == 2


# ---------------------------------------------------------------------------
# Tests — SessionManager avec user_id (Phase 6(D))
# ---------------------------------------------------------------------------


def test_session_create_with_user_id():
    mgr = SessionManager()
    sid = mgr.create(user_id=42)
    assert mgr.verify(sid)
    assert mgr.get_user_id(sid) == 42


def test_session_create_anonymous():
    """create() sans user_id reste backward-compat (user_id=None)."""
    mgr = SessionManager()
    sid = mgr.create()
    assert mgr.verify(sid)
    assert mgr.get_user_id(sid) is None


def test_session_get_user_id_invalid():
    mgr = SessionManager()
    assert mgr.get_user_id("session_inexistante") is None


def test_session_revoke_clears_user_id():
    mgr = SessionManager()
    sid = mgr.create(user_id=1)
    mgr.revoke(sid)
    assert not mgr.verify(sid)
    assert mgr.get_user_id(sid) is None


def test_session_user_ids_isolated():
    """Deux sessions ont des user_ids independants."""
    mgr = SessionManager()
    sid1 = mgr.create(user_id=1)
    sid2 = mgr.create(user_id=2)
    assert mgr.get_user_id(sid1) == 1
    assert mgr.get_user_id(sid2) == 2
