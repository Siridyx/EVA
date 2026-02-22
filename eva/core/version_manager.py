"""
VersionManager — Gestionnaire de versions et migrations

Responsabilités :
- Gérer la version du projet EVA
- Détecter les incompatibilités entre code et data
- Exécuter les migrations data/ automatiquement
- Tracker la version dans data/.version

Architecture :
- Hérite de EvaComponent (config + event_bus)
- Utilise semver (MAJOR.MINOR.PATCH)
- Migrations incrémentales
- API simple : check(), migrate()

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Fichier version dans data/.version
"""

from pathlib import Path
from typing import Optional, Tuple, Callable, List
import re

from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class VersionManager(EvaComponent):
    """
    Gestionnaire de versions et migrations EVA.
    
    Gère la version du projet, détecte les incompatibilités
    entre le code et les données, et exécute les migrations
    automatiques si nécessaire.
    
    Architecture :
        - Version code depuis config.yaml
        - Version data depuis data/.version
        - Migrations incrémentales (0.1.0 → 0.2.0 → ...)
        - Semver (MAJOR.MINOR.PATCH)
    
    Usage:
        vm = VersionManager(config, bus)
        vm.start()
        
        # Vérifier compatibilité
        compatible, code_v, data_v = vm.check()
        
        # Migrer si nécessaire
        if not compatible:
            vm.migrate()
    
    Format version : X.Y.Z[-suffix]
        - X (MAJOR) : Breaking changes
        - Y (MINOR) : Nouvelles features (backward compatible)
        - Z (PATCH) : Bug fixes
        - suffix : dev, alpha, beta, rc
    """
    
    # Regex semver
    VERSION_PATTERN = re.compile(
        r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        r"(?:-(?P<suffix>[a-z]+))?$"
    )
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise le VersionManager.
        
        Args:
            config: Gestionnaire de configuration
            event_bus: Bus d'événements central
            name: Nom du composant (défaut: "VersionManager")
        """
        super().__init__(config, event_bus, name or "VersionManager")
        
        # Version du code (depuis config.yaml)
        self._code_version: str = self.get_config("version", "0.1.0-dev")
        
        # Chemin fichier version data
        self._version_file: Path = self.config.project_root / "data" / ".version"
        
        # Migrations enregistrées (remplies au start)
        self._migrations: List[Tuple[str, Callable]] = []
    
    # --- Lifecycle ---
    
    def _do_start(self) -> None:
        """
        Démarre le VersionManager.
        
        Enregistre les migrations disponibles.
        """
        # Enregistrer migrations (pour l'instant aucune)
        # self._register_migrations()
        
        # Vérifier compatibilité
        compatible, code_v, data_v = self.check()
        
        if not compatible:
            self.emit("version_mismatch", {
                "code_version": code_v,
                "data_version": data_v
            })
    
    # --- Version parsing ---
    
    def parse_version(self, version: str) -> Optional[Tuple[int, int, int, str]]:
        """
        Parse une version semver.
        
        Args:
            version: Version string (ex: "0.1.0-dev")
        
        Returns:
            Tuple (major, minor, patch, suffix) ou None si invalide
        
        Example:
            >>> vm.parse_version("0.1.0-dev")
            (0, 1, 0, "dev")
            >>> vm.parse_version("1.2.3")
            (1, 2, 3, "")
        """
        match = self.VERSION_PATTERN.match(version)
        if not match:
            return None
        
        major = int(match.group("major"))
        minor = int(match.group("minor"))
        patch = int(match.group("patch"))
        suffix = match.group("suffix") or ""
        
        return (major, minor, patch, suffix)
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare deux versions semver.
        
        Args:
            v1: Première version
            v2: Deuxième version
        
        Returns:
            -1 si v1 < v2
             0 si v1 == v2
             1 si v1 > v2
        
        Raises:
            ValueError: Si version invalide
        
        Example:
            >>> vm.compare_versions("0.1.0", "0.2.0")
            -1
            >>> vm.compare_versions("1.0.0", "0.9.0")
            1
        """
        parsed_v1 = self.parse_version(v1)
        parsed_v2 = self.parse_version(v2)
        
        if not parsed_v1:
            raise ValueError(f"Invalid version format: {v1}")
        if not parsed_v2:
            raise ValueError(f"Invalid version format: {v2}")
        
        # Comparer major, minor, patch
        for i in range(3):
            if parsed_v1[i] < parsed_v2[i]:
                return -1
            elif parsed_v1[i] > parsed_v2[i]:
                return 1
        
        # Versions identiques (ignorer suffix pour compatibilité)
        return 0
    
    # --- Version I/O ---
    
    def read_data_version(self) -> Optional[str]:
        """
        Lit la version depuis data/.version.
        
        Returns:
            Version string ou None si fichier absent
        
        Example:
            >>> vm.read_data_version()
            "0.1.0-dev"
        """
        if not self._version_file.exists():
            return None
        
        try:
            version = self._version_file.read_text(encoding="utf-8").strip()
            return version if version else None
        except Exception:
            return None
    
    def write_data_version(self, version: str) -> None:
        """
        Écrit la version dans data/.version.
        
        Args:
            version: Version à écrire
        
        Raises:
            ValueError: Si version invalide
        
        Example:
            >>> vm.write_data_version("0.1.0-dev")
        """
        # Valider format
        if not self.parse_version(version):
            raise ValueError(f"Invalid version format: {version}")
        
        # Créer dossier data si nécessaire
        self._version_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Écrire
        self._version_file.write_text(version, encoding="utf-8")
        
        self.emit("version_written", {"version": version})
    
    # --- Compatibility check ---
    
    def check(self) -> Tuple[bool, str, Optional[str]]:
        """
        Vérifie la compatibilité code/data.
        
        Returns:
            Tuple (compatible, code_version, data_version)
            - compatible : True si versions compatibles
            - code_version : Version du code
            - data_version : Version data (None si pas de data/)
        
        Règles compatibilité :
            - Pas de data/.version → compatible (première exécution)
            - MAJOR différent → incompatible (breaking changes)
            - MINOR/PATCH différents → compatible (mais migration conseillée)
        
        Example:
            >>> vm.check()
            (True, "0.1.0-dev", None)  # Première exec
            >>> vm.check()
            (False, "1.0.0", "0.5.0")  # Breaking change
        """
        code_version = self._code_version
        data_version = self.read_data_version()
        
        # Pas de data/.version → première exécution, compatible
        if data_version is None:
            # Écrire version code
            self.write_data_version(code_version)
            return (True, code_version, None)
        
        # Comparer versions
        try:
            parsed_code = self.parse_version(code_version)
            parsed_data = self.parse_version(data_version)
            
            if not parsed_code or not parsed_data:
                # Version invalide → incompatible par sécurité
                return (False, code_version, data_version)
            
            # MAJOR différent → incompatible (breaking changes)
            if parsed_code[0] != parsed_data[0]:
                return (False, code_version, data_version)
            
            # MINOR/PATCH → compatible (migrations possibles)
            return (True, code_version, data_version)
            
        except Exception:
            # Erreur parsing → incompatible par sécurité
            return (False, code_version, data_version)
    
    # --- Migrations ---
    
    def migrate(self, from_version: Optional[str] = None) -> bool:
        """
        Exécute les migrations nécessaires.
        
        Args:
            from_version: Version de départ (défaut: data_version actuelle)
        
        Returns:
            True si migrations réussies, False sinon
        
        Example:
            >>> vm.migrate()  # Migre depuis data/.version vers code
            True
        
        Note:
            En Phase 0, aucune migration n'est définie.
            Le framework est prêt pour Phase 1+.
        """
        if from_version is None:
            from_version = self.read_data_version()
        
        if from_version is None:
            # Pas de version data → pas de migration
            self.write_data_version(self._code_version)
            return True
        
        to_version = self._code_version
        
        # Pas de migrations enregistrées en P0
        if not self._migrations:
            # Juste mettre à jour la version
            self.write_data_version(to_version)
            
            self.emit("migration_completed", {
                "from_version": from_version,
                "to_version": to_version,
                "migrations_count": 0
            })
            
            return True
        
        # P1+ : Exécuter migrations incrémentales
        # (code non implémenté en P0, structure prête)
        
        return True
    
    def register_migration(
        self,
        version: str,
        migration_func: Callable[[], None]
    ) -> None:
        """
        Enregistre une migration.
        
        Args:
            version: Version cible de la migration
            migration_func: Fonction de migration
        
        Example:
            >>> def migrate_0_1_0_to_0_2_0():
            ...     # Migration logic
            ...     pass
            >>> vm.register_migration("0.2.0", migrate_0_1_0_to_0_2_0)
        
        Note:
            Non utilisé en P0, prêt pour P1+.
        """
        self._migrations.append((version, migration_func))
        self._migrations.sort(key=lambda x: x[0])  # Trier par version
    
    # --- Introspection ---
    
    @property
    def code_version(self) -> str:
        """Version du code."""
        return self._code_version
    
    @property
    def data_version(self) -> Optional[str]:
        """Version des données."""
        return self.read_data_version()
    
    def __repr__(self) -> str:
        """Représentation string de VersionManager."""
        data_v = self.data_version or "none"
        return (
            f"VersionManager(code={self._code_version}, "
            f"data={data_v})"
        )