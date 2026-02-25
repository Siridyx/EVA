"""
ConversationEngine — Orchestration conversations

Composant responsable de :
- Orchestrer les interactions user/assistant
- Gérer le contexte conversationnel
- Coordonner Memory, Prompt, LLM
- Détecter et exécuter tool calls (R-020)
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from eva.core.eva_component import EvaComponent

if TYPE_CHECKING:
    from eva.tools.tool_executor import ToolExecutor


class ConversationEngine(EvaComponent):
    """
    Moteur de conversation.

    Coordonne Memory, Prompt, LLM pour générer des réponses contextuelles.
    Supporte tool calling (R-020).

    Workflow :
    1. User message → Memory
    2. Récupérer contexte
    3. Render prompt système
    4. Appeler LLM
    5. Détecter tool call
    6. Si tool call → exécuter → rappeler LLM
    7. Persister réponse
    """

    def __init__(
        self,
        config,
        event_bus,
        memory,
        prompt,
        llm,
        tool_executor: Optional["ToolExecutor"] = None
    ):
        """
        Initialise ConversationEngine.
        ...
        """
        # Assigner AVANT super().__init__ (pour __repr__)
        self._memory = memory
        self._prompt = prompt
        self._llm = llm
        self._tool_executor = tool_executor
        
        super().__init__(config, event_bus, "ConversationEngine")

       
    # --- Propriétés publiques ---

    @property
    def memory_manager(self):
        """MemoryManager injecté."""
        return self._memory

    @property
    def prompt_manager(self):
        """PromptManager injecté."""
        return self._prompt

    @property
    def llm_client(self):
        """LLMClient injecté."""
        return self._llm

    @property
    def _prompt_defaults(self) -> Dict[str, str]:
        """Defaults du prompt système depuis config."""
        return {
            "tone": self.get_config("prompt.defaults.tone", "professionnel"),
            "expertise": self.get_config("prompt.defaults.expertise", "assistant général"),
        }

    # --- Lifecycle ---

    def _do_start(self) -> None:
        """Démarre ConversationEngine (vérifie les dépendances)."""
        if not self._memory.is_running:
            raise RuntimeError("MemoryManager must be started before ConversationEngine")
        if not self._prompt.is_running:
            raise RuntimeError("PromptManager must be started before ConversationEngine")
        if not self._llm.is_running:
            raise RuntimeError("LLMClient must be started before ConversationEngine")
        self.emit("conversation_engine_started", {})

    def _do_stop(self) -> None:
        """Arrête ConversationEngine."""
        self.emit("conversation_engine_stopped", {})

    def respond(self, user_message: str, profile: str = "default") -> str:
        """
        Génère une réponse conversationnelle.

        Workflow :
        1. Ajouter message user à memory
        2. Récupérer contexte
        3. Render prompt système
        4. Construire tools OpenAI si disponibles
        5. Appeler LLM
        6. SI tool call détecté :
            a. Exécuter tool
            b. Ajouter résultat
            c. Rappeler LLM
        7. Persister réponse assistant
        8. Retourner réponse

        Args:
            user_message: Message utilisateur
            profile: Profil LLM (dev/default)

        Returns:
            Réponse générée

        Raises:
            RuntimeError: Si non démarré
            ValueError: Si erreur LLM ou input invalide
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")

        # Validation input
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

            # 3. Render prompt système avec tools
            tools_list = self._build_tools_list()

            system_prompt = self._prompt.render(
                "system",
                strict=False,
                tone=self.get_config("prompt.defaults.tone", "professionnel"),
                expertise=self.get_config("prompt.defaults.expertise", "assistant général"),
                tools_list=tools_list
            )

            # 4. Construire messages pour LLM
            messages = [{"role": "system", "content": system_prompt}]

            for msg in context:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # 5. Construire tools OpenAI si disponibles (R-023)
            tools_openai = None
            if self._tool_executor:
                registry = self._tool_executor._registry
                all_tools = registry.get_all_definitions()
                tools_openai = [tool.to_openai_function() for tool in all_tools]

            # 6. Appeler LLM (première fois)
            llm_response = self._llm.complete(
                messages, 
                profile=profile,
                tools=tools_openai
            )

            # 7. Détecter tool call
            tool_call = self._detect_tool_call(llm_response)

            if tool_call and self._tool_executor:
                # Tool call détecté !
                self.emit("tool_call_detected", {
                    "tool_name": tool_call["tool_name"],
                    "arguments": list(tool_call["arguments"].keys())
                })

                # 7a. Exécuter tool
                tool_result = self._tool_executor.execute(
                    tool_name=tool_call["tool_name"],
                    arguments=tool_call["arguments"]
                )

                # 7b. Ajouter tool_call et résultat à messages
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

                # 7c. Rappeler LLM pour réponse finale
                llm_response = self._llm.complete(
                    messages, 
                    profile=profile,
                    tools=tools_openai  # Même tools que le 1er appel
                )

                # Persister dans memory
                self._memory.add_message("assistant", f"[tool_call: {tool_call['tool_name']}]")
                self._memory.add_message("tool", tool_result_content)

            # 8. Persister réponse finale
            self._memory.add_message("assistant", llm_response)

            # 9. Events
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

    def _detect_tool_call(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """
        Détecte un tool call dans la réponse LLM.

        Format attendu (provider-agnostic) :
        {"action":"tool_call","tool_name":"nom","arguments":{...}}

        Args:
            llm_response: Réponse brute du LLM

        Returns:
            Dict avec tool_name et arguments, ou None

        Example:
            >>> response = '{"action":"tool_call","tool_name":"calc","arguments":{"a":2}}'
            >>> engine._detect_tool_call(response)
            {"tool_name": "calc", "arguments": {"a": 2}}
        """
        import json

        # Doit commencer par {
        if not llm_response.strip().startswith("{"):
            return None

        try:
            # Parser JSON
            data = json.loads(llm_response.strip())

            # Vérifier format
            if not isinstance(data, dict):
                return None

            if data.get("action") != "tool_call":
                return None

            if "tool_name" not in data:
                return None

            if "arguments" not in data:
                return None

            # Retourner format interne
            return {
                "tool_name": data["tool_name"],
                "arguments": data.get("arguments", {})
            }

        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    def _build_tools_list(self) -> str:
        """
        Construit la liste des tools disponibles pour le prompt.

        Returns:
            Description formatée des tools disponibles

        Example:
            >>> tools_list = engine._build_tools_list()
            >>> print(tools_list)
            - get_time(city): Get current time in a specific city
            - calc(expression): Calculate a simple mathematical expression
        """
        if not self._tool_executor:
            return "Aucun outil disponible pour le moment."

        # Récupérer tous les tools du registry
        registry = self._tool_executor._registry
        all_tools = registry.get_all_definitions()

        if not all_tools:
            return "Aucun outil disponible pour le moment."

        # Formater chaque tool
        tools_lines = []
        for tool_def in all_tools:
            # Paramètres
            params = ", ".join(tool_def.parameters.keys()) if tool_def.parameters else ""

            # Ligne formatée
            line = f"- {tool_def.name}({params}): {tool_def.description}"
            tools_lines.append(line)

        return "\n".join(tools_lines)

    def _build_message(self, role: str, content: str) -> Dict[str, Any]:
        """
        Construit un message formaté (role + content + timestamp).

        Args:
            role: Rôle du message ("system", "user", "assistant")
            content: Contenu du message

        Returns:
            Dict avec role, content, timestamp ISO 8601

        Raises:
            ValueError: Si rôle invalide
        """
        from datetime import datetime

        valid_roles = {"system", "user", "assistant", "tool"}
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role!r}. Valid: {sorted(valid_roles)}")

        return {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        """Représentation string."""
        state = "running" if self.is_running else "stopped"
        tools = "with tools" if self._tool_executor else "no tools"
        return f"ConversationEngine(state={state}, {tools})"