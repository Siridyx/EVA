"""
ConversationEngine — Orchestrateur conversationnel

Responsabilités :
- Orchestrer Memory + Prompt + LLM
- Pipeline : context → prompt → LLM → persist
- Gestion erreurs + observabilité

Architecture :
- Hérite de EvaComponent
- Injection : memory_manager, prompt_manager, llm_client
- API : respond(user_input, overrides)

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Pas d'écriture directe fichiers (délègue à Memory)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.memory.memory_manager import MemoryManager
from eva.prompt.prompt_manager import PromptManager
from eva.llm.llm_client import LLMClient

# Import conditionnel pour éviter dépendance circulaire
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from eva.tools.tool_executor import ToolExecutor

class ConversationEngine(EvaComponent):
    """
    Orchestrateur conversationnel EVA.
    
    Coordonne Memory, Prompt et LLM pour produire des
    conversations contextuelles et cohérentes.
    
    Architecture :
        - Injection explicite des dépendances
        - Pipeline : Memory → Prompt → LLM → Memory
        - Observabilité via EventBus
        - Pas d'écriture directe (délègue à MemoryManager)
    
    Usage:
        memory = MemoryManager(config, bus)
        prompt = PromptManager(config, bus)
        llm = OpenAIProvider(config, bus)
        
        conversation = ConversationEngine(
            config, bus,
            memory_manager=memory,
            prompt_manager=prompt,
            llm_client=llm
        )
        
        conversation.start()
        response = conversation.respond("Bonjour EVA")
        conversation.stop()
    
    Format messages standardisé :
        {
            "role": "system" | "user" | "assistant",
            "content": str,
            "timestamp": str (ISO 8601)
        }
    
    Ce format est utilisé par :
        - MemoryManager (stockage)
        - LLMClient (API OpenAI compatible)
        - ConversationEngine (construction pipeline)
    
    Pas de conversion implicite — format unique end-to-end.
    
    Events émis :
        - conversation_request_received
        - conversation_context_built
        - llm_request_started
        - llm_request_succeeded
        - llm_request_error
        - conversation_reply_ready
        - conversation_error
    """
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        memory_manager: MemoryManager,
        prompt_manager: PromptManager,
        llm_client: LLMClient,
        tool_executor: Optional["ToolExecutor"] = None,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise ConversationEngine.
        
        Args:
            config: Gestionnaire de configuration
            event_bus: Bus d'événements central
            memory_manager: Gestionnaire de mémoire
            prompt_manager: Gestionnaire de prompts
            llm_client: Client LLM
            name: Nom du composant (défaut: "ConversationEngine")
        """
        super().__init__(config, event_bus, name or "ConversationEngine")
        
        # Dépendances injectées
        self._memory: MemoryManager = memory_manager
        self._prompt: PromptManager = prompt_manager
        self._llm: LLMClient = llm_client
        self._tool_executor = tool_executor
        
        # Configuration
        self._environment: str = self.get_config("environment", "development")
        
        # Defaults prompt
        self._prompt_defaults: Dict[str, str] = self.get_config("prompt.defaults", {
            "tone": "professionnel",
            "expertise": "assistant général"
        })
    
    # --- Lifecycle ---
    
    def _do_start(self) -> None:
        """
        Démarre ConversationEngine.
        
        Vérifie que les dépendances sont démarrées.
        
        Raises:
            RuntimeError: Si dépendances pas démarrées
        """
        # Vérifier dépendances
        if not self._memory.is_running:
            raise RuntimeError("MemoryManager must be started before ConversationEngine")
        
        if not self._prompt.is_running:
            raise RuntimeError("PromptManager must be started before ConversationEngine")
        
        if not self._llm.is_running:
            raise RuntimeError("LLMClient must be started before ConversationEngine")
        
        self.emit("conversation_engine_started", {
            "environment": self._environment
        })
    
    def _do_stop(self) -> None:
        """Arrête ConversationEngine."""
        self.emit("conversation_engine_stopped", {})
    
    # --- Message utilities ---
    
    def _build_message(
        self,
        role: str,
        content: str
    ) -> Dict[str, str]:
        """
        Construit un message au format standardisé.
        
        Format :
            {
                "role": "system" | "user" | "assistant",
                "content": str,
                "timestamp": str (ISO 8601)
            }
        
        Args:
            role: Rôle du message
            content: Contenu du message
        
        Returns:
            Message formaté
        
        Raises:
            ValueError: Si rôle invalide
        
        Example:
            >>> msg = self._build_message("user", "Bonjour")
            >>> msg["role"]
            "user"
        """
        # Validation rôle
        valid_roles = ["system", "user", "assistant"]
        if role not in valid_roles:
            raise ValueError(
                f"Invalid role '{role}'. Valid roles: {valid_roles}"
            )
        
        return {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
    
    # --- LLM utilities ---
    
    def _call_llm(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Appelle le LLM (fonction pure).
        
        Args:
            messages: Messages formatés pour LLM (system + context)
        
        Returns:
            Réponse du LLM
        
        Raises:
            RuntimeError: Si erreur LLM (avec fallback)
        
        Note:
            - Profil déterminé depuis environment
            - Timeout depuis config
            - Gestion erreurs + fallback
            - Validation réponse non vide
        """
        import time
        
        # Déterminer profil
        profile = "dev" if self._environment == "development" else "default"
        
        # Timeout depuis config
        timeout = self.get_config("llm.timeout", 30)
        
        # Event avant appel
        start_time = time.time()
        
        self.emit("llm_request_started", {
            "provider": self._llm.name,
            "model": self._llm.default_model,
            "profile": profile,
            "messages_count": len(messages),
            "timeout": timeout
        })
        
        try:
            # Appeler LLM
            reply = self._llm.complete(
                messages=messages,
                profile=profile
            )
            
            # Validation réponse non vide
            if not reply or not reply.strip():
                raise ValueError("LLM returned empty response")
            
            # Event succès
            latency_ms = int((time.time() - start_time) * 1000)
            
            self.emit("llm_request_succeeded", {
                "latency_ms": latency_ms,
                "reply_length": len(reply)
            })
            
            return reply.strip()
            
        except Exception as e:
            # Event erreur (pas de stacktrace, pas de secrets)
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Déterminer stage
            stage = "empty_reply" if isinstance(e, ValueError) else "llm_call"
            
            self.emit("llm_request_error", {
                "stage": stage,
                "error_type": type(e).__name__,
                "error_summary": str(e)[:200],  # Tronqué
                "latency_ms": latency_ms
            })
            
            # Fallback user-safe (pas de stacktrace)
            fallback = (
                "Désolé, je ne peux pas répondre pour le moment. "
                "Le service LLM est temporairement indisponible."
            )
            
            # Re-raise avec message propre
            raise RuntimeError(fallback) from e
    
    # --- API ---

    def _detect_tool_call(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """
        Détecte si réponse LLM est un tool call.
        
        Args:
            llm_response: Réponse du LLM
        
        Returns:
            Dict avec tool_name et arguments si tool call, None sinon
        
        Format attendu (JSON strict une ligne):
            {"action":"tool_call","tool_name":"get_weather","arguments":{"city":"Paris"}}
        """
        import json
        
        # Vérifier si commence par {
        stripped = llm_response.strip()
        if not stripped.startswith("{"):
            return None
        
        # Parser JSON
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        
        # Vérifier structure
        if not isinstance(data, dict):
            return None
        
        if data.get("action") != "tool_call":
            return None
        
        if "tool_name" not in data:
            return None
        
        if "arguments" not in data:
            return None
        
        # Tool call détecté
        return {
            "tool_name": data["tool_name"],
            "arguments": data["arguments"]
        }    
    
    def respond(self, user_message: str, profile: str = "default") -> str:
        """
        Génère une réponse conversationnelle.
        
        Workflow :
        1. Ajouter message user à memory
        2. Récupérer contexte
        3. Render prompt système
        4. Appeler LLM
        5. SI tool call détecté :
            a. Exécuter tool
            b. Ajouter résultat
            c. Rappeler LLM
        6. Persister réponse assistant
        7. Retourner réponse
        
        Args:
            user_message: Message utilisateur
            profile: Profil LLM (dev/default)
        
        Returns:
            Réponse générée
        
        Raises:
            RuntimeError: Si non démarré
            ValueError: Si erreur LLM
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")
        
        if not isinstance(user_message, str):
            raise ValueError("user_message must be str")
    
        if not user_message.strip():
            raise ValueError("user_message cannot be empty")
        
        self.emit("conversation_turn_start", {
            "user_message": user_message[:100]
        })
        
        try:
            # 1. Persister user message
            self._memory.add_message("user", user_message)
            
            # 2. Récupérer contexte
            context = self._memory.get_context()
            
            # 3. Render prompt système
            system_prompt = self._prompt.render(
                "system",
                strict=False,
                tone=self.get_config("prompt.defaults.tone", "professionnel"),
                expertise=self.get_config("prompt.defaults.expertise", "assistant général")
            )
            
            # 4. Construire messages pour LLM
            messages = [{"role": "system", "content": system_prompt}]
            
            for msg in context:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 5. Appeler LLM (première fois)
            llm_response = self._llm.complete(messages, profile=profile)
            
            # 6. Détecter tool call
            tool_call = self._detect_tool_call(llm_response)
            
            if tool_call and self._tool_executor:
                # Tool call détecté !
                self.emit("tool_call_detected", {
                    "tool_name": tool_call["tool_name"],
                    "arguments": list(tool_call["arguments"].keys())
                })
                
                # 6a. Exécuter tool
                tool_result = self._tool_executor.execute(
                    tool_name=tool_call["tool_name"],
                    arguments=tool_call["arguments"]
                )
                
                # 6b. Ajouter tool_call et résultat à messages
                # Message assistant (tool call)
                messages.append({
                    "role": "assistant",
                    "content": llm_response  # Le JSON tool call
                })
                
                # Message tool result
                import json
                tool_result_content = json.dumps(tool_result, ensure_ascii=False)
                
                messages.append({
                    "role": "tool",
                    "content": tool_result_content,
                    "name": tool_call["tool_name"]
                })
                
                # 6c. Rappeler LLM pour réponse finale
                llm_response = self._llm.complete(messages, profile=profile)
                
                # Persister dans memory
                self._memory.add_message("assistant", f"[tool_call: {tool_call['tool_name']}]")
                self._memory.add_message("tool", tool_result_content)
            
            # 7. Persister réponse finale
            self._memory.add_message("assistant", llm_response)
            
            # 8. Events
            self.emit("conversation_turn_complete", {
                "user_message": user_message[:100],
                "assistant_response": llm_response[:200]
            })
            
            return llm_response
            
        except Exception as e:
            self.emit("conversation_error", {
                "error": str(e)
            })
            raise ValueError(f"Conversation error: {e}")
    
    # --- Introspection ---
    
    @property
    def memory_manager(self) -> MemoryManager:
        """Gestionnaire de mémoire."""
        return self._memory
    
    @property
    def prompt_manager(self) -> PromptManager:
        """Gestionnaire de prompts."""
        return self._prompt
    
    @property
    def llm_client(self) -> LLMClient:
        """Client LLM."""
        return self._llm
    
    def __repr__(self) -> str:
        """Représentation string de ConversationEngine."""
        state = "running" if self.is_running else "stopped"
        return (
            f"ConversationEngine(state={state}, "
            f"env={self._environment})"
        )