"""
ConfigManager — Gestionnaire de configuration centralisé

Responsabilités :
- Charger config.yaml depuis la racine du projet
- Charger variables d'environnement depuis .env
- Fournir accès typé à la configuration
- Gérer les chemins data/ de façon centralisée
- Créer automatiquement les dossiers manquants
- Valider la structure de configuration

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Gestion d'erreurs explicite
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import os


class ConfigManager:
    """
    Gestionnaire centralisé de la configuration EVA.
    
    Charge config.yaml depuis la racine du projet et expose
    les paramètres de façon structurée. Gère les chemins data/
    et crée automatiquement les dossiers nécessaires.
    Charge aussi les secrets depuis .env.
    
    Usage:
        config = ConfigManager()
        log_path = config.get_path("logs")
        llm_model = config.get("llm.default_model")
        api_key = config.get_secret("OPENAI_API_KEY")
    """
    
    # --- Configuration paths ---
    
    _DEFAULT_CONFIG_FILE = "config.yaml"
    _REQUIRED_PATHS = ["logs", "memory", "cache", "prompts", "dumps"]
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialise ConfigManager.
        
        Args:
            config_path: Chemin vers config.yaml (défaut: config.yaml à la racine)
        
        Note:
            Supporte EVA_DATA_DIR env var pour override data root (tests).
        """
        # Charger config.yaml
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        else:
            config_path = Path(config_path)
        
        self._config_path: Path = config_path
        
        # AJOUTE CETTE LIGNE ↓
        self._project_root: Path = config_path.parent
        
        self._data: Dict[str, Any] = self._load_config()
        
        # Override data root si EVA_DATA_DIR présent (mode test)
        if "EVA_DATA_DIR" in os.environ:
            data_root = Path(os.environ["EVA_DATA_DIR"])
            # Reconstruire tous les paths
            for key in ["logs", "memory", "cache", "prompts", "dumps"]:
                self._data["paths"][key] = str(data_root / key)
    
    # --- Initialisation ---
    
    def _find_project_root(self) -> Path:
        """
        Trouve la racine du projet EVA.
        
        Cherche le premier dossier parent contenant config.yaml
        ou pyproject.toml.
        
        Returns:
            Path absolu vers la racine du projet
        
        Raises:
            RuntimeError: Si racine introuvable
        """
        current = Path(__file__).resolve()
        
        # Remonter depuis eva/core/config_manager.py
        # vers Eva/ (2 niveaux)
        for parent in current.parents:
            if (parent / "config.yaml").exists() or \
               (parent / "pyproject.toml").exists():
                return parent
        
        # Fallback : 2 niveaux au-dessus de ce fichier
        # eva/core/config_manager.py -> eva/core -> eva -> Eva/
        return current.parent.parent.parent
    
    def _load_env(self) -> None:
        """
        Charge les variables d'environnement depuis .env.
        
        Cherche .env à la racine du projet. Si absent, continue
        sans erreur (dev peut fonctionner sans secrets).
        
        Note:
            .env est optionnel en développement.
            En production, les variables doivent être définies.
        """
        env_path = self._project_root / ".env"
        
        if env_path.exists():
            load_dotenv(env_path)
        # Si .env absent, on continue (pas bloquant pour P0)
    
    def _resolve_config_path(self, config_path: Optional[str]) -> Path:
        """
        Résout le chemin vers config.yaml.
        
        Args:
            config_path: Chemin custom (optionnel)
        
        Returns:
            Path absolu vers config.yaml
        
        Raises:
            FileNotFoundError: Si fichier introuvable
        """
        if config_path:
            path = Path(config_path)
            if not path.is_absolute():
                path = self._project_root / path
        else:
            path = self._project_root / self._DEFAULT_CONFIG_FILE
        
        if not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {path}\n"
                f"Project root detected: {self._project_root}"
            )
        
        return path
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Charge et parse config.yaml.
        
        Returns:
            Dictionnaire de configuration
        
        Raises:
            yaml.YAMLError: Si YAML invalide
        """
        with open(self._config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not isinstance(config, dict):
            raise ValueError(
                f"Invalid config format in {self._config_path}: "
                f"expected dict, got {type(config)}"
            )
        
        return config
    
    def _ensure_data_directories(self) -> None:
        """
        Crée les dossiers data/ s'ils n'existent pas.
        
        Crée automatiquement tous les chemins définis dans
        paths.* de la configuration.
        """
        paths_config = self._data.get("paths", {})
        
        for key in self._REQUIRED_PATHS:
            path_str = paths_config.get(key)
            if path_str:
                full_path = self._project_root / path_str
                full_path.mkdir(parents=True, exist_ok=True)
    
    # --- Accès public ---
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de config (notation pointée).
        
        Args:
            key: Clé en notation pointée (ex: "llm.default_model")
            default: Valeur par défaut si clé absente
        
        Returns:
            Valeur de configuration ou default
        
        Example:
            >>> config.get("llm.default_model")
            "gpt-4"
            >>> config.get("unknown.key", "fallback")
            "fallback"
        """
        keys = key.split(".")
        value = self._data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_path(self, path_key: str) -> Path:
        """
        Récupère un chemin absolu depuis paths.*.
        
        Args:
            path_key: Clé du chemin (ex: "logs", "memory")
        
        Returns:
            Path absolu vers le dossier
        
        Raises:
            KeyError: Si path_key absent de la config
        
        Example:
            >>> config.get_path("logs")
            Path("C:/Users/Sirid/Desktop/EVA/data/logs")
        """
        path_str = self.get(f"paths.{path_key}")
        
        if not path_str:
            raise KeyError(
                f"Path '{path_key}' not found in configuration. "
                f"Available paths: {list(self._data.get('paths', {}).keys())}"
            )
        
        return self._project_root / path_str
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Récupère une variable d'environnement (secret).
        
        Args:
            key: Nom de la variable (ex: "OPENAI_API_KEY")
            default: Valeur par défaut si absente
        
        Returns:
            Valeur de la variable ou default
        
        Example:
            >>> config.get_secret("OPENAI_API_KEY")
            "sk-..."
            >>> config.get_secret("MISSING_KEY", "fallback")
            "fallback"
        
        Note:
            Les secrets ne sont JAMAIS loggés ni exposés dans __repr__.
        """
        return os.getenv(key, default)
    
    @property
    def project_root(self) -> Path:
        """Racine du projet EVA."""
        return self._project_root
    
    @property
    def config_path(self) -> Path:
        """Chemin vers config.yaml."""
        return self._config_path
    
    @property
    def version(self) -> str:
        """Version EVA depuis la config."""
        return self.get("version", "unknown")
    
    @property
    def environment(self) -> str:
        """Environnement (development/production)."""
        return self.get("environment", "development")
    
    def __repr__(self) -> str:
        """Représentation string du ConfigManager."""
        return (
            f"ConfigManager(version={self.version}, "
            f"env={self.environment}, "
            f"root={self.project_root})"
        )