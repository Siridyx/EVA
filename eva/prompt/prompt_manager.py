"""
PromptManager — Gestionnaire de templates de prompts

Responsabilités :
- Charger templates depuis data/prompts/
- Render avec variables ({{var}})
- Auto-création prompts par défaut
- Validation placeholders résolus

Architecture :
- Hérite de EvaComponent (config + event_bus)
- Format .txt simple
- Regex pour variables {{var}}
- Scope system only (P1)

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Validation stricte (erreur si placeholders non résolus)
"""

import re
from pathlib import Path
from typing import Dict, Optional, Any

from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class PromptManager(EvaComponent):
    """
    Gestionnaire de templates de prompts.
    
    Charge et render des templates de prompts depuis
    data/prompts/ avec support variables {{var}}.
    
    Architecture :
        - Format .txt simple
        - Variables avec {{var}} (regex-based)
        - Auto-création prompts par défaut si absents
        - Validation : erreur si placeholders non résolus
        - Scope system only (P1)
    
    Usage:
        pm = PromptManager(config, bus)
        pm.start()
        
        # Render avec variables
        prompt = pm.render("system", tone="amical", expertise="Python")
        
        # Get sans variables
        prompt = pm.get("system")
    
    Templates par défaut :
        - system.txt : Prompt système principal
        - system_concise.txt : Variante concise
    """
    
    # Regex pour détecter placeholders {{var}}
    PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")
    
    # Prompts par défaut (créés automatiquement si absents)
    DEFAULT_PROMPTS = {
        "system": """Tu es EVA, un assistant IA personnel intelligent et serviable.

Ton rôle :
- Aider l'utilisateur avec ses questions et tâches
- Être {{tone}} dans tes réponses
- Utiliser ton expertise en {{expertise}}
- Fournir des réponses claires et précises

Comportement :
- Toujours courtois et professionnel
- Demander des clarifications si besoin
- Admettre quand tu ne sais pas quelque chose
""",
        "system_concise": """Tu es EVA, assistant IA {{tone}}.
Expertise : {{expertise}}.
Réponds de façon concise et précise.
"""
    }
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise le PromptManager.
        
        Args:
            config: Gestionnaire de configuration
            event_bus: Bus d'événements central
            name: Nom du composant (défaut: "PromptManager")
        """
        super().__init__(config, event_bus, name or "PromptManager")
        
        # Chemin prompts
        self._prompts_path: Path = self.get_path("prompts")
        
        # Cache prompts chargés
        self._prompts: Dict[str, str] = {}
    
    # --- Lifecycle ---
    
    def _do_start(self) -> None:
        """
        Démarre le PromptManager.
        
        Crée les prompts par défaut si absents et charge tous les prompts.
        """
        # Créer prompts par défaut si absents
        self._ensure_default_prompts()
        
        # Charger tous les prompts
        self._load_all_prompts()
        
        self.emit("prompt_manager_started", {
            "prompts_count": len(self._prompts)
        })
    
    def _do_stop(self) -> None:
        """Arrête le PromptManager et vide le cache."""
        self._prompts.clear()
    
    # --- Prompts par défaut ---
    
    def _ensure_default_prompts(self) -> None:
        """
        Crée les prompts par défaut si absents.
        
        Crée data/prompts/ et les fichiers .txt par défaut.
        """
        # Créer dossier si nécessaire
        self._prompts_path.mkdir(parents=True, exist_ok=True)
        
        # Créer chaque prompt par défaut si absent
        for name, content in self.DEFAULT_PROMPTS.items():
            prompt_file = self._prompts_path / f"{name}.txt"
            
            if not prompt_file.exists():
                prompt_file.write_text(content.strip(), encoding="utf-8")
                
                self.emit("prompt_created", {
                    "name": name,
                    "path": str(prompt_file)
                })
    
    # --- Chargement ---
    
    def _load_all_prompts(self) -> None:
        """
        Charge tous les prompts depuis data/prompts/.
        
        Charge uniquement les fichiers .txt.
        """
        for prompt_file in self._prompts_path.glob("*.txt"):
            name = prompt_file.stem  # Nom sans extension
            content = prompt_file.read_text(encoding="utf-8").strip()
            self._prompts[name] = content

    def _create_default_prompts(self) -> None:
        """
        Crée les prompts par défaut si absents.
        
        Prompts créés :
            - system.txt : Prompt système principal
            - system_concise.txt : Variante concise
        """
        # System prompt principal
        system_prompt = self.prompts_path / "system.txt"
        if not system_prompt.exists():
            default_content = """Tu es EVA, un assistant IA personnel intelligent et serviable.

Ton role :
- Aider l'utilisateur avec ses questions et taches
- Etre {{tone}} dans tes reponses
- Utiliser ton expertise en {{expertise}}
- Fournir des reponses claires et precises

Comportement :
- Toujours courtois et professionnel
- Demander des clarifications si besoin
- Admettre quand tu ne sais pas quelque chose"""
            
            system_prompt.write_text(default_content, encoding="utf-8")
            
            self.emit("prompt_created", {
                "name": "system",
                "path": str(system_prompt)
            })
        
        # System prompt concis
        system_concise = self.prompts_path / "system_concise.txt"
        if not system_concise.exists():
            concise_content = """Tu es EVA. Sois {{tone}} et utilise ton expertise {{expertise}}. Reponds de maniere claire et concise."""
            
            system_concise.write_text(concise_content, encoding="utf-8")
            
            self.emit("prompt_created", {
                "name": "system_concise",
                "path": str(system_concise)
            })
    
    def _load_prompt(self, name: str) -> str:
        """
        Charge un prompt spécifique.
        
        Args:
            name: Nom du prompt (sans .txt)
        
        Returns:
            Contenu du prompt
        
        Raises:
            FileNotFoundError: Si prompt n'existe pas
        """
        prompt_file = self._prompts_path / f"{name}.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt '{name}' not found at {prompt_file}")
        
        return prompt_file.read_text(encoding="utf-8").strip()
    
    # --- API Publique ---
    
    def get(self, name: str, reload: bool = False) -> str:
        """
        Récupère un prompt (sans render).
        
        Args:
            name: Nom du prompt
            reload: Recharger depuis disque (ignorer cache)
        
        Returns:
            Template brut (avec placeholders)
        
        Raises:
            RuntimeError: Si PromptManager pas démarré
            FileNotFoundError: Si prompt n'existe pas
        
        Example:
            >>> template = pm.get("system")
            >>> print(template)
            "Tu es EVA... {{tone}} ..."
        """
        if not self.is_running:
            raise RuntimeError("PromptManager not started")
        
        # Recharger si demandé ou absent du cache
        if reload or name not in self._prompts:
            self._prompts[name] = self._load_prompt(name)
        
        return self._prompts[name]
    
    def render(
        self,
        name: str,
        strict: bool = True,
        **variables: Any
    ) -> str:
        """
        Render un prompt avec variables.
        
        Args:
            name: Nom du prompt
            strict: Si True, erreur sur placeholder non résolu. Si False, laisse tel quel.
            **variables: Variables à injecter
        
        Returns:
            Prompt rendu
        
        Raises:
            ValueError: Si placeholders non résolus ET strict=True
        """
        if not self.is_running:
            raise RuntimeError("PromptManager not started")
        
        # Charger template
        template = self.get(name)
        
        # Render variables
        rendered = template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        
        # Validation stricte optionnelle
        if strict:
            unresolved = self.PLACEHOLDER_PATTERN.findall(rendered)
            if unresolved:
                raise ValueError(
                    f"Unresolved placeholders in prompt '{name}': {unresolved}. "
                    f"Provided variables: {list(variables.keys())}"
                )
        
        # Émettre event (NOUVEAU)
        self.emit("prompt_rendered", {
            "name": name,
            "variables": list(variables.keys())
        })
        
        return rendered
    
    def list_prompts(self) -> list:
        """
        Liste tous les prompts disponibles.
        
        Returns:
            Liste des noms de prompts
        
        Example:
            >>> pm.list_prompts()
            ["system", "system_concise"]
        """
        if not self.is_running:
            return []
        
        return list(self._prompts.keys())
    
    def extract_variables(self, name: str) -> list:
        """
        Extrait les variables nécessaires d'un prompt.
        
        Args:
            name: Nom du prompt
        
        Returns:
            Liste des variables (ex: ["tone", "expertise"])
        
        Example:
            >>> pm.extract_variables("system")
            ["tone", "expertise"]
        """
        template = self.get(name)
        return self.PLACEHOLDER_PATTERN.findall(template)
    
    # --- Introspection ---
    
    @property
    def prompts_path(self) -> Path:
        """Chemin du dossier prompts."""
        return self._prompts_path
    
    @property
    def prompt_count(self) -> int:
        """Nombre de prompts chargés."""
        return len(self._prompts)
    
    def __repr__(self) -> str:
        """Représentation string de PromptManager."""
        state = "running" if self.is_running else "stopped"
        return (
            f"PromptManager(state={state}, "
            f"prompts={len(self._prompts)})"
        )