"""
MemoryManager — Gestionnaire de mémoire conversationnelle

Responsabilités :
- Stocker l'historique des conversations
- Gérer la fenêtre de contexte (N derniers messages)
- Persister dans data/memory/ (JSON)
- Fournir contexte pour LLM

Architecture :
- Hérite de EvaComponent (config + event_bus)
- Backend JSON simple (P1)
- Session unique (P1)
- Écriture atomique (temp → rename)
- Schema versioning

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Écriture atomique obligatoire
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import tempfile
import os

from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class MemoryManager(EvaComponent):
    """
    Gestionnaire de mémoire conversationnelle.
    
    Stocke l'historique des conversations en JSON avec
    fenêtre de contexte configurable.
    
    Architecture :
        - Backend JSON (data/memory/)
        - Session unique (P1)
        - Écriture atomique (temp → rename)
        - Schema versioning pour migrations futures
        - Context window configurable
    
    Usage:
        memory = MemoryManager(config, bus)
        memory.start()
        
        # Ajouter messages
        memory.add_message("user", "Bonjour EVA")
        memory.add_message("assistant", "Bonjour ! Comment puis-je vous aider ?")
        
        # Récupérer contexte pour LLM
        context = memory.get_context()
    
    Format JSON :
        {
            "schema_version": 1,
            "conversation_id": "uuid",
            "created_at": "ISO timestamp",
            "updated_at": "ISO timestamp",
            "messages": [
                {
                    "role": "user",
                    "content": "...",
                    "timestamp": "ISO timestamp"
                }
            ]
        }
    """
    
    # Schema version (pour migrations futures)
    SCHEMA_VERSION = 1
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise le MemoryManager.
        
        Args:
            config: Gestionnaire de configuration
            event_bus: Bus d'événements central
            name: Nom du composant (défaut: "MemoryManager")
        """
        super().__init__(config, event_bus, name or "MemoryManager")
        
        # Configuration
        self._max_messages: int = self.get_config("memory.max_messages", 100)
        self._context_window: int = self.get_config("memory.context_window", 10)
        self._backend: str = self.get_config("memory.backend", "json")
        self._summary_threshold: int = self.get_config("memory.summary_threshold", 40)
        self._summary_keep_recent: int = self.get_config("memory.summary_keep_recent", 10)
        
        # Chemin mémoire
        self._memory_path: Path = self.get_path("memory")
        
        # Session actuelle (chargée au start)
        self._conversation_id: Optional[str] = None
        self._messages: List[Dict[str, Any]] = []
        self._session_file: Optional[Path] = None
    
    # --- Lifecycle ---
    
    def _do_start(self) -> None:
        """
        Démarre le MemoryManager.
        
        Charge ou crée une session de conversation.
        """
        # Chercher session existante du jour
        today = datetime.now().strftime("%Y-%m-%d")
        session_file = self._memory_path / f"conversation_{today}.json"
        
        if session_file.exists():
            # Charger session existante
            self._load_session(session_file)
            self.emit("memory_session_loaded", {
                "conversation_id": self._conversation_id,
                "messages_count": len(self._messages)
            })
        else:
            # Créer nouvelle session
            self._create_session(session_file)
            self.emit("memory_session_created", {
                "conversation_id": self._conversation_id
            })
    
    def _do_stop(self) -> None:
        """
        Arrête le MemoryManager.
        
        Sauvegarde la session en cours.
        """
        if self._session_file and self._conversation_id:
            self._save_session()
            self.emit("memory_session_saved", {
                "conversation_id": self._conversation_id,
                "messages_count": len(self._messages)
            })
    
    # --- Session management ---
    
    def _create_session(self, session_file: Path) -> None:
        """
        Crée une nouvelle session.
        
        Args:
            session_file: Chemin du fichier de session
        """
        self._conversation_id = str(uuid.uuid4())
        self._messages = []
        self._session_file = session_file
        
        # Sauvegarder immédiatement
        self._save_session()
    
    def _load_session(self, session_file: Path) -> None:
        """
        Charge une session existante.
        
        Args:
            session_file: Chemin du fichier de session
        
        Raises:
            ValueError: Si format JSON invalide ou schema incompatible
        """
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Vérifier schema version
            schema_version = data.get("schema_version", 0)
            if schema_version != self.SCHEMA_VERSION:
                raise ValueError(
                    f"Incompatible schema version: {schema_version} "
                    f"(expected {self.SCHEMA_VERSION})"
                )
            
            # Charger données
            self._conversation_id = data["conversation_id"]
            self._messages = data["messages"]
            self._session_file = session_file
            
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid session file format: {e}")
    
    def _save_session(self) -> None:
        """
        Sauvegarde la session (écriture atomique).
        
        Utilise temp file → rename pour éviter corruption.
        """
        if not self._session_file or not self._conversation_id:
            return
        
        now = datetime.now().isoformat()
        
        # Données à sauvegarder
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "conversation_id": self._conversation_id,
            "created_at": self._messages[0]["timestamp"] if self._messages else now,
            "updated_at": now,
            "messages": self._messages
        }
        
        temp_path = None  # Initialize pour except block
        try:
            # Assurer que le dossier parent existe
            self._session_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Créer temp file dans même dossier (même filesystem)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self._session_file.parent,
                prefix=".tmp_",
                suffix=".json"
            )
            
            # Écrire dans temp file
            # R-044 perf: compact JSON (pas d'indent) — fichier interne, pas lu à la main
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            
            # Rename atomique (POSIX garantit atomicité)
            # Sur Windows, besoin de supprimer d'abord si existe
            if os.name == 'nt' and self._session_file.exists():
                self._session_file.unlink()
            
            os.replace(temp_path, self._session_file)
            
        except Exception as e:
            # Cleanup temp file si erreur
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise RuntimeError(f"Failed to save session: {e}")
    
    # --- Message management ---
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Ajoute un message à l'historique.
        
        Args:
            role: Rôle (user, assistant, system)
            content: Contenu du message
            metadata: Métadonnées optionnelles
        
        Raises:
            RuntimeError: Si MemoryManager pas démarré
            ValueError: Si rôle invalide
        
        Example:
            >>> memory.add_message("user", "Bonjour")
            >>> memory.add_message("assistant", "Bonjour !")
        """
        if not self.is_running:
            raise RuntimeError("MemoryManager not started")
        
        if role not in ["user", "assistant", "system", "tool"]:
            raise ValueError(f"Invalid role: {role}")
        
        # Créer message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            message["metadata"] = metadata
        
        # Ajouter à l'historique
        self._messages.append(message)
        
        # Trim si dépasse max_messages
        if len(self._messages) > self._max_messages:
            removed = self._messages.pop(0)
            self.emit("memory_message_trimmed", {
                "conversation_id": self._conversation_id,
                "removed_message": removed
            })
        
        # Sauvegarder immédiatement (écriture atomique)
        self._save_session()
        
        # Event
        self.emit("memory_message_added", {
            "conversation_id": self._conversation_id,
            "role": role,
            "content_length": len(content)
        })
    
    def get_context(self, window: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère le contexte pour le LLM.
        
        Args:
            window: Nombre de messages (défaut: config context_window)
        
        Returns:
            Liste des N derniers messages
        
        Example:
            >>> context = memory.get_context(window=10)
            >>> # Envoyer au LLM
        """
        if not self.is_running:
            return []
        
        if window is None:
            window = self._context_window
        
        # Retourner les N derniers messages
        return self._messages[-window:] if window > 0 else self._messages
    
    def maybe_summarize(self, llm_fn) -> bool:
        """
        Declenche un resume automatique si message_count >= summary_threshold.

        Remplace les anciens messages par un message systeme de resume,
        en conservant les summary_keep_recent messages les plus recents.
        En cas d'echec du LLM, la memoire reste intacte (echec silencieux).

        Args:
            llm_fn: Callable[[List[Dict]], str] — genere le resume a partir
                    d'une liste de messages (meme signature que llm.complete()).

        Returns:
            True si le resume a ete effectue, False sinon.
        """
        if len(self._messages) < self._summary_threshold:
            return False

        old = self._messages[:-self._summary_keep_recent]
        recent = self._messages[-self._summary_keep_recent:]

        # Prompt de resume
        summary_messages = [
            {
                "role": "system",
                "content": (
                    "Resume cette conversation de facon concise, "
                    "en conservant les informations importantes."
                )
            }
        ] + old

        try:
            summary_text = llm_fn(summary_messages)
        except Exception:
            return False  # Echec silencieux — memoire intacte

        now = datetime.now().isoformat()
        summary_msg: Dict[str, Any] = {
            "role": "system",
            "content": f"[Resume de la conversation precedente] {summary_text}",
            "timestamp": now,
            "metadata": {
                "summary": True,
                "summarized_count": len(old)
            }
        }

        self._messages = [summary_msg] + list(recent)
        self._save_session()

        self.emit("memory_summarized", {
            "conversation_id": self._conversation_id,
            "summarized_count": len(old),
            "summary_length": len(summary_text)
        })
        return True

    def get_all_messages(self) -> List[Dict[str, Any]]:
        """
        Récupère tous les messages de la session.
        
        Returns:
            Liste complète des messages
        """
        return self._messages.copy()
    
    def clear(self) -> None:
        """
        Efface l'historique de la session courante.
        
        Crée une nouvelle session.
        """
        if not self.is_running:
            return
        
        old_conv_id = self._conversation_id
        
        # Créer nouvelle session
        today = datetime.now().strftime("%Y-%m-%d")
        session_file = self._memory_path / f"conversation_{today}_new.json"
        self._create_session(session_file)
        
        self.emit("memory_cleared", {
            "old_conversation_id": old_conv_id,
            "new_conversation_id": self._conversation_id
        })
    
    # --- Introspection ---
    
    @property
    def conversation_id(self) -> Optional[str]:
        """ID de la conversation courante."""
        return self._conversation_id
    
    @property
    def message_count(self) -> int:
        """Nombre de messages dans l'historique."""
        return len(self._messages)
    
    @property
    def context_window(self) -> int:
        """Taille de la fenêtre de contexte."""
        return self._context_window

    @property
    def summary_threshold(self) -> int:
        """Seuil declenchement resume automatique."""
        return self._summary_threshold

    def __repr__(self) -> str:
        """Représentation string de MemoryManager."""
        state = "running" if self.is_running else "stopped"
        return (
            f"MemoryManager(state={state}, "
            f"messages={len(self._messages)}, "
            f"window={self._context_window})"
        )