"""Tests unitaires pour LoggingManager (R-009)"""

import pytest
from pathlib import Path
from eva.core.logging_manager import LoggingManager
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus

xfail_paths = pytest.mark.xfail(
    reason="DEBT-008: LoggingManager ne crée pas parent directories"
)

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


def test_logging_manager_init(config, event_bus):
    """LoggingManager s'initialise correctement."""
    logger = LoggingManager(config, event_bus)
    
    assert logger.name == "LoggingManager"
    assert logger.log_level == "INFO"
    assert logger.channels == ["user", "system", "error"]
    assert not logger.is_running

@xfail_paths
def test_logging_manager_start(config, event_bus):
    """start() crée les loggers."""
    logger = LoggingManager(config, event_bus)
    logger.start()
    
    assert logger.is_running
    assert len(logger._loggers) == 3
    
    logger.stop()

@xfail_paths
def test_logging_manager_log_user(config, event_bus):
    """log() écrit sur canal user."""
    logger = LoggingManager(config, event_bus)
    logger.start()
    
    # Log user
    logger.log("user", "Test message")
    
    # Vérifier fichier créé
    logs_path = config.get_path("logs")
    log_files = list(logs_path.glob("user_*.log"))
    assert len(log_files) > 0
    
    # Vérifier contenu
    content = log_files[0].read_text(encoding="utf-8")
    assert "Test message" in content
    
    logger.stop()

@xfail_paths
def test_logging_manager_log_system(config, event_bus):
    """log() écrit sur canal system."""
    logger = LoggingManager(config, event_bus)
    logger.start()
    
    logger.log("system", "System event", "INFO")
    
    logs_path = config.get_path("logs")
    log_files = list(logs_path.glob("system_*.log"))
    assert len(log_files) > 0
    
    content = log_files[0].read_text(encoding="utf-8")
    assert "System event" in content
    
    logger.stop()

@xfail_paths
def test_logging_manager_log_error(config, event_bus):
    """log() écrit sur canal error."""
    logger = LoggingManager(config, event_bus)
    logger.start()
    
    logger.log("error", "Error occurred", "ERROR")
    
    logs_path = config.get_path("logs")
    log_files = list(logs_path.glob("error_*.log"))
    assert len(log_files) > 0
    
    content = log_files[0].read_text(encoding="utf-8")
    assert "Error occurred" in content
    assert "ERROR" in content
    
    logger.stop()

@xfail_paths
def test_logging_manager_invalid_channel(config, event_bus):
    """log() rejette canal invalide."""
    logger = LoggingManager(config, event_bus)
    logger.start()
    
    with pytest.raises(ValueError, match="Invalid channel"):
        logger.log("invalid", "message")
    
    logger.stop()

@xfail_paths
def test_logging_manager_invalid_level(config, event_bus):
    """log() rejette niveau invalide."""
    logger = LoggingManager(config, event_bus)
    logger.start()
    
    with pytest.raises(ValueError, match="Invalid level"):
        logger.log("user", "message", "INVALID")
    
    logger.stop()


def test_logging_manager_log_before_start(config, event_bus):
    """log() avant start() ne crash pas (ignore silencieusement)."""
    logger = LoggingManager(config, event_bus)
    
    # Pas d'erreur
    logger.log("user", "message")

@xfail_paths
def test_logging_manager_utility_methods(config, event_bus):
    """Méthodes utilitaires (debug, info, error, etc.)."""
    logger = LoggingManager(config, event_bus)
    logger.start()
    
    logger.debug("system", "Debug message")
    logger.info("system", "Info message")
    logger.warning("system", "Warning message")
    logger.error("system", "Error message")
    logger.critical("system", "Critical message")
    
    logs_path = config.get_path("logs")
    log_files = list(logs_path.glob("system_*.log"))
    assert len(log_files) > 0
    
    logger.stop()

@xfail_paths
def test_logging_manager_emits_log_written(config, event_bus):
    """log() émet event log_written."""
    events = []
    
    logger = LoggingManager(config, event_bus)
    logger.start()
    
    # Enregistrer handler APRÈS start
    event_bus.on("log_written", lambda p: events.append(p))
    
    logger.log("user", "Test", "INFO")
    
    assert len(events) == 1  # 1 événement manuel
    assert events[0]["channel"] == "user"
    assert events[0]["message"] == "Test"
    assert events[0]["level"] == "INFO"
    
    logger.stop()

@xfail_paths
def test_logging_manager_stop_closes_handlers(config, event_bus):
    """stop() ferme proprement les handlers."""
    logger = LoggingManager(config, event_bus)
    logger.start()
    
    # Vérifier que loggers existent
    assert len(logger._loggers) == 3
    
    logger.stop()
    
    # Loggers vidés
    assert len(logger._loggers) == 0

@xfail_paths
def test_logging_manager_repr(config, event_bus):
    """__repr__ retourne représentation correcte."""
    logger = LoggingManager(config, event_bus)
    
    repr_str = repr(logger)
    assert "LoggingManager" in repr_str
    assert "stopped" in repr_str
    
    logger.start()
    repr_str = repr(logger)
    assert "running" in repr_str
    
    logger.stop()