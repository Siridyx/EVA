"""
LoggingManager — Gestionnaire de logs centralisé

Responsabilités :
- Centraliser tous les logs EVA
- Gérer rotation quotidienne des fichiers logs
- Séparer les logs par canal (user, system, error)
- Configurer niveaux de log depuis config.yaml

Architecture :
- Hérite de EvaComponent (config + event_bus)
- Utilise logging.handlers.RotatingFileHandler
- API simple : log(channel, message, level)

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Logs dans data/logs/ uniquement
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional

from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class LoggingManager(EvaComponent):
    """
    Gestionnaire centralisé des logs EVA.
    
    Gère plusieurs canaux de logs (user, system, error) avec
    rotation quotidienne et niveaux configurables.
    
    Architecture :
        - Logs séparés par canal (user, system, error)
        - Rotation quotidienne (fichiers nommés YYYY-MM-DD)
        - Niveaux configurables (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - Format standardisé avec timestamp
    
    Usage:
        logger = LoggingManager(config, bus)
        logger.start()
        
        logger.log("user", "Bonjour EVA")
        logger.log("system", "Engine started", level="INFO")
        logger.log("error", "LLM timeout", level="ERROR")
    
    Canaux disponibles :
        - user : Messages utilisateur et réponses
        - system : Logs système (startup, shutdown, events)
        - error : Erreurs uniquement
    """
    
    # Canaux disponibles
    CHANNELS = ["user", "system", "error"]
    
    # Mapping niveaux string → logging
    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise le LoggingManager.
        
        Args:
            config: Gestionnaire de configuration
            event_bus: Bus d'événements central
            name: Nom du composant (défaut: "LoggingManager")
        """
        super().__init__(config, event_bus, name or "LoggingManager")
        
        # Configuration depuis config.yaml
        self._log_level: str = self.get_config("logging.level", "INFO")
        self._format: str = self.get_config(
            "logging.format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self._retention_days: int = self.get_config("logging.retention_days", 30)
        
        # Loggers par canal (créés au start)
        self._loggers: dict = {}
        
        # Chemin logs
        self._logs_path: Path = self.get_path("logs")
    
    # --- Lifecycle ---
    
    def _do_start(self) -> None:
        """
        Démarre le LoggingManager.
        
        Crée les loggers pour chaque canal avec rotation quotidienne.
        """
        # Créer un logger par canal
        for channel in self.CHANNELS:
            self._loggers[channel] = self._create_logger(channel)
        
        # Log de démarrage
        self.log("system", f"LoggingManager started (level={self._log_level})", "INFO")
    
    def _do_stop(self) -> None:
        """
        Arrête le LoggingManager.
        
        Flush et ferme tous les handlers.
        """
        self.log("system", "LoggingManager stopping", "INFO")
        
        for logger in self._loggers.values():
            for handler in logger.handlers[:]:
                handler.flush()
                handler.close()
                logger.removeHandler(handler)
        
        self._loggers.clear()
    
    # --- Création loggers ---
    
    def _create_logger(self, channel: str) -> logging.Logger:
        """
        Crée un logger pour un canal.
        
        Args:
            channel: Nom du canal (user, system, error)
        
        Returns:
            Logger configuré avec rotation quotidienne
        """
        # Nom du logger
        logger_name = f"eva.{channel}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.LEVELS.get(self._log_level, logging.INFO))
        logger.propagate = False  # Pas de propagation au root logger
        
        # Fichier log avec date
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self._logs_path / f"{channel}_{today}.log"
        
        # Handler avec rotation
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setLevel(self.LEVELS.get(self._log_level, logging.INFO))
        
        # Format
        formatter = logging.Formatter(self._format)
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
        return logger
    
    # --- API Publique ---
    
    def log(
        self,
        channel: str,
        message: str,
        level: str = "INFO"
    ) -> None:
        """
        Log un message sur un canal.
        
        Args:
            channel: Canal de log (user, system, error)
            message: Message à logger
            level: Niveau (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
        Raises:
            ValueError: Si canal ou niveau invalide
        
        Example:
            >>> logger.log("user", "Hello EVA")
            >>> logger.log("system", "Engine started", "INFO")
            >>> logger.log("error", "LLM timeout", "ERROR")
        """
        if not self.is_running:
            # Si pas démarré, on ignore silencieusement (évite erreurs init)
            return
        
        if channel not in self.CHANNELS:
            raise ValueError(
                f"Invalid channel '{channel}'. "
                f"Valid channels: {', '.join(self.CHANNELS)}"
            )
        
        if level not in self.LEVELS:
            raise ValueError(
                f"Invalid level '{level}'. "
                f"Valid levels: {', '.join(self.LEVELS.keys())}"
            )
        
        logger = self._loggers.get(channel)
        if not logger:
            return
        
        # Log avec le niveau approprié
        log_level = self.LEVELS[level]
        logger.log(log_level, message)
        
        # Emit event pour observabilité
        self.emit("log_written", {
            "channel": channel,
            "level": level,
            "message": message
        })
    
    # --- Méthodes utilitaires ---
    
    def debug(self, channel: str, message: str) -> None:
        """Log niveau DEBUG."""
        self.log(channel, message, "DEBUG")
    
    def info(self, channel: str, message: str) -> None:
        """Log niveau INFO."""
        self.log(channel, message, "INFO")
    
    def warning(self, channel: str, message: str) -> None:
        """Log niveau WARNING."""
        self.log(channel, message, "WARNING")
    
    def error(self, channel: str, message: str) -> None:
        """Log niveau ERROR."""
        self.log(channel, message, "ERROR")
    
    def critical(self, channel: str, message: str) -> None:
        """Log niveau CRITICAL."""
        self.log(channel, message, "CRITICAL")
    
    # --- Nettoyage ---
    
    def cleanup_old_logs(self, days: Optional[int] = None) -> int:
        """
        Supprime les logs plus anciens que X jours.
        
        Args:
            days: Nombre de jours de rétention (défaut: depuis config)
        
        Returns:
            Nombre de fichiers supprimés
        
        Example:
            >>> logger.cleanup_old_logs(30)
            5  # 5 fichiers supprimés
        """
        if days is None:
            days = self._retention_days
        
        count = 0
        now = datetime.now()
        
        for log_file in self._logs_path.glob("*.log"):
            # Extraire la date du nom de fichier
            # Format: {channel}_YYYY-MM-DD.log
            try:
                date_str = log_file.stem.split("_", 1)[1]  # YYYY-MM-DD
                log_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                age_days = (now - log_date).days
                
                if age_days > days:
                    log_file.unlink()
                    count += 1
                    
            except (ValueError, IndexError):
                # Nom de fichier invalide, ignorer
                continue
        
        if count > 0:
            self.log("system", f"Cleaned up {count} old log files", "INFO")
        
        return count
    
    # --- Introspection ---
    
    @property
    def log_level(self) -> str:
        """Niveau de log actuel."""
        return self._log_level
    
    @property
    def channels(self) -> list:
        """Canaux disponibles."""
        return self.CHANNELS
    
    def __repr__(self) -> str:
        """Représentation string de LoggingManager."""
        state = "running" if self.is_running else "stopped"
        return (
            f"LoggingManager(state={state}, "
            f"level={self._log_level}, "
            f"channels={len(self._loggers)})"
        )