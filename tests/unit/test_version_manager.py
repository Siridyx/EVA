"""Tests unitaires pour VersionManager (R-010)"""

import pytest
from pathlib import Path
from eva.core.version_manager import VersionManager
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


@pytest.fixture
def config():
    """Fixture ConfigManager."""
    return ConfigManager()


@pytest.fixture
def event_bus():
    """Fixture EventBus."""
    bus = EventBus()
    bus.clear()
    return bus


@pytest.fixture
def version_file(config):
    """Fixture pour nettoyer le fichier .version."""
    version_file = config.project_root / "data" / ".version"
    
    # Backup si existe
    backup = None
    if version_file.exists():
        backup = version_file.read_text()
        version_file.unlink()
    
    yield version_file
    
    # Restore
    if backup:
        version_file.write_text(backup)
    elif version_file.exists():
        version_file.unlink()


def test_version_manager_init(config, event_bus):
    """VersionManager s'initialise correctement."""
    vm = VersionManager(config, event_bus)
    
    assert vm.name == "VersionManager"
    assert vm.code_version == "0.1.0-dev"
    assert not vm.is_running


def test_parse_version_valid(config, event_bus):
    """parse_version() parse correctement."""
    vm = VersionManager(config, event_bus)
    
    result = vm.parse_version("0.1.0-dev")
    assert result == (0, 1, 0, "dev")
    
    result = vm.parse_version("1.2.3")
    assert result == (1, 2, 3, "")


def test_parse_version_invalid(config, event_bus):
    """parse_version() retourne None si invalide."""
    vm = VersionManager(config, event_bus)
    
    assert vm.parse_version("invalid") is None
    assert vm.parse_version("1.2") is None
    assert vm.parse_version("") is None


def test_compare_versions(config, event_bus):
    """compare_versions() compare correctement."""
    vm = VersionManager(config, event_bus)
    
    assert vm.compare_versions("0.1.0", "0.2.0") == -1
    assert vm.compare_versions("1.0.0", "0.9.0") == 1
    assert vm.compare_versions("1.2.3", "1.2.3") == 0
    assert vm.compare_versions("0.1.0-dev", "0.1.0-alpha") == 0  # Ignore suffix


def test_compare_versions_invalid(config, event_bus):
    """compare_versions() raise si version invalide."""
    vm = VersionManager(config, event_bus)
    
    with pytest.raises(ValueError):
        vm.compare_versions("invalid", "0.1.0")


def test_write_read_data_version(config, event_bus, version_file):
    """write/read data version."""
    vm = VersionManager(config, event_bus)
    
    vm.write_data_version("0.1.0-dev")
    
    assert version_file.exists()
    assert vm.read_data_version() == "0.1.0-dev"


def test_write_invalid_version(config, event_bus, version_file):
    """write_data_version() rejette version invalide."""
    vm = VersionManager(config, event_bus)
    
    with pytest.raises(ValueError):
        vm.write_data_version("invalid")


def test_check_first_run(config, event_bus, version_file):
    """check() première exécution (pas de .version)."""
    vm = VersionManager(config, event_bus)
    
    compatible, code_v, data_v = vm.check()
    
    assert compatible is True
    assert code_v == "0.1.0-dev"
    assert data_v is None
    
    # Fichier .version créé
    assert version_file.exists()


def test_check_compatible_same_version(config, event_bus, version_file):
    """check() avec même version."""
    vm = VersionManager(config, event_bus)
    
    # Écrire même version
    vm.write_data_version("0.1.0-dev")
    
    compatible, code_v, data_v = vm.check()
    
    assert compatible is True
    assert code_v == "0.1.0-dev"
    assert data_v == "0.1.0-dev"


def test_check_compatible_minor_diff(config, event_bus, version_file):
    """check() compatible si MINOR différent."""
    vm = VersionManager(config, event_bus)
    
    # Data version plus ancienne (MINOR)
    vm.write_data_version("0.0.1")
    
    compatible, code_v, data_v = vm.check()
    
    # Compatible (même MAJOR)
    assert compatible is True


def test_check_incompatible_major_diff(config, event_bus, version_file):
    """check() incompatible si MAJOR différent."""
    vm = VersionManager(config, event_bus)
    
    # Data version MAJOR différent
    vm.write_data_version("1.0.0")
    
    compatible, code_v, data_v = vm.check()
    
    # Incompatible (breaking changes)
    assert compatible is False
    assert code_v == "0.1.0-dev"
    assert data_v == "1.0.0"


def test_migrate_no_data_version(config, event_bus, version_file):
    """migrate() sans .version crée le fichier."""
    vm = VersionManager(config, event_bus)
    
    result = vm.migrate()
    
    assert result is True
    assert version_file.exists()
    assert vm.read_data_version() == "0.1.0-dev"


def test_migrate_updates_version(config, event_bus, version_file):
    """migrate() met à jour .version."""
    vm = VersionManager(config, event_bus)
    
    # Version ancienne
    vm.write_data_version("0.0.1")
    
    result = vm.migrate()
    
    assert result is True
    assert vm.read_data_version() == "0.1.0-dev"


def test_migrate_emits_event(config, event_bus, version_file):
    """migrate() émet migration_completed."""
    events = []
    event_bus.on("migration_completed", lambda p: events.append(p))
    
    vm = VersionManager(config, event_bus)
    vm.write_data_version("0.0.1")
    
    vm.migrate()
    
    assert len(events) == 1
    assert events[0]["from_version"] == "0.0.1"
    assert events[0]["to_version"] == "0.1.0-dev"


def test_version_manager_start(config, event_bus, version_file):
    """start() vérifie compatibilité."""
    vm = VersionManager(config, event_bus)
    
    vm.start()
    
    assert vm.is_running
    assert version_file.exists()
    
    vm.stop()


def test_version_manager_repr(config, event_bus, version_file):
    """__repr__ retourne représentation correcte."""
    vm = VersionManager(config, event_bus)
    
    repr_str = repr(vm)
    assert "VersionManager" in repr_str
    assert "0.1.0-dev" in repr_str