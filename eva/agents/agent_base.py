"""
AgentBase — Classe de base pour agents autonomes EVA

Implémente la boucle ReAct (Reason → Act → Observe) :
1. L'agent reçoit un goal
2. Raisonne sur la meilleure action (LLM)
3. Exécute un outil si nécessaire (Act)
4. Observe le résultat (Observe)
5. Répète jusqu'à réponse finale ou max_steps

Architecture :
- Hérite de EvaComponent (lifecycle + events)
- Injection LLMClient + ToolExecutor (optionnel)
- Config-driven (max_steps depuis config)
- Stateless entre run() appels (pas de state persisté)
- Events pour observabilité complète

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus

if TYPE_CHECKING:
    from eva.llm.llm_client import LLMClient
    from eva.tools.tool_executor import ToolExecutor


# --- Modèles de données ---

@dataclass
class AgentStep:
    """
    Représente une étape d'exécution de l'agent.

    Attributes:
        step_num: Numéro de l'étape (1-based)
        action: Type d'action ("tool_call" ou "final_answer")
        tool_name: Nom du tool appelé (si action == "tool_call")
        tool_args: Arguments du tool (si action == "tool_call")
        observation: Résultat du tool (si action == "tool_call")
        content: Contenu de la réponse finale (si action == "final_answer")
        raw_response: Réponse brute du LLM
    """
    step_num: int
    action: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    content: Optional[str] = None
    raw_response: str = ""


@dataclass
class AgentResult:
    """
    Résultat complet d'une exécution d'agent.

    Attributes:
        success: True si goal accompli, False si max_steps ou erreur
        answer: Réponse finale (ou message d'erreur)
        steps: Liste des étapes exécutées
        goal: Goal original
    """
    success: bool
    answer: str
    steps: List[AgentStep] = field(default_factory=list)
    goal: str = ""


# --- Agent de base ---

class AgentBase(EvaComponent):
    """
    Agent autonome EVA — boucle ReAct (Reason → Act → Observe).

    Reçoit un goal, raisonne, exécute des tools si nécessaire,
    et produit une réponse finale de manière autonome.

    Architecture :
        - LLM pour le raisonnement à chaque étape
        - ToolExecutor pour exécuter les actions (optionnel)
        - Boucle limitée à max_steps pour éviter les boucles infinies
        - Steps traçables via AgentResult.steps

    Usage:
        agent = AgentBase(config, bus, llm=llm_client, tool_executor=executor)
        agent.start()

        result = agent.run("Quelle heure est-il à Tokyo ?")
        print(result.answer)   # "Il est 09:30 à Tokyo."
        print(len(result.steps))  # 2 (tool_call + final_answer)
    """

    # Prompt système injecté dans chaque run()
    # Les {{ }} évitent les conflits avec str.format()
    _SYSTEM_PROMPT_TEMPLATE = """Tu es EVA Agent, un assistant autonome capable de raisonner et d'agir.
Ton objectif : accomplir le goal donné en utilisant les outils disponibles.

## Outils disponibles
{tools_list}

## Format de réponse STRICT — JSON sur une seule ligne, rien d'autre

Pour appeler un outil :
{{"action":"tool_call","tool_name":"nom_outil","arguments":{{"param":"valeur"}}}}

Pour donner ta réponse finale :
{{"action":"final_answer","content":"ta réponse ici"}}

## Règles impératives
- Réponds UNIQUEMENT avec le JSON demandé, une seule ligne
- Pas de texte avant ou après le JSON
- Utilise les outils pour obtenir les données nécessaires
- Quand tu as toutes les informations, utilise "final_answer"
- Si aucun outil n'est nécessaire, réponds directement avec "final_answer"
"""

    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        llm: "LLMClient",
        tool_executor: Optional["ToolExecutor"] = None,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise AgentBase.

        Args:
            config: ConfigManager
            event_bus: EventBus
            llm: Client LLM pour le raisonnement (requis)
            tool_executor: Executeur de tools (optionnel)
            name: Nom du composant
        """
        super().__init__(config, event_bus, name or "AgentBase")

        self._llm = llm
        self._tool_executor = tool_executor

        # Limite de sécurité contre les boucles infinies
        self._max_steps: int = self.get_config("agent.max_steps", 10)

    # --- Lifecycle ---

    def _do_start(self) -> None:
        """Démarre l'agent (vérifie les dépendances)."""
        if not self._llm.is_running:
            raise RuntimeError("LLMClient must be started before AgentBase")

        if self._tool_executor and not self._tool_executor.is_running:
            raise RuntimeError("ToolExecutor must be started before AgentBase")

        self.emit("agent_started", {
            "agent": self.name,
            "max_steps": self._max_steps,
            "has_tools": self._tool_executor is not None
        })

    def _do_stop(self) -> None:
        """Arrête l'agent."""
        self.emit("agent_stopped", {"agent": self.name})

    # --- API publique ---

    def run(self, goal: str, profile: str = "default") -> AgentResult:
        """
        Exécute un goal via la boucle ReAct.

        Workflow à chaque itération :
        1. Appeler LLM avec messages courants
        2. Parser la réponse JSON (tool_call ou final_answer)
        3a. tool_call → exécuter → ajouter observation → continuer
        3b. final_answer → retourner AgentResult(success=True)
        4. Si max_steps atteint → AgentResult(success=False)

        Args:
            goal: Objectif à accomplir (non vide)
            profile: Profil LLM ("dev" ou "default")

        Returns:
            AgentResult avec réponse finale et historique des steps

        Raises:
            RuntimeError: Si agent non démarré
            ValueError: Si goal vide

        Example:
            >>> result = agent.run("Combien fait 42 * 17 ?")
            >>> result.success
            True
            >>> result.answer
            "Le résultat de 42 × 17 est 714."
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")

        if not goal or not goal.strip():
            raise ValueError("goal cannot be empty")

        goal = goal.strip()

        self.emit("agent_run_start", {
            "agent": self.name,
            "goal": goal[:100]
        })

        # Construire le prompt système avec la liste des tools
        tools_list = self._build_tools_description()
        system_prompt = self._SYSTEM_PROMPT_TEMPLATE.format(
            tools_list=tools_list
        )

        # Historique des messages (croît à chaque step)
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": goal}
        ]

        steps: List[AgentStep] = []

        try:
            for step_num in range(1, self._max_steps + 1):

                self.emit("agent_step_start", {
                    "agent": self.name,
                    "step": step_num
                })

                # Appel LLM
                raw_response = self._llm.complete(messages, profile=profile)

                # Parser la réponse
                parsed = self._parse_response(raw_response)
                action = parsed.get("action", "")

                if action == "final_answer":
                    answer = parsed.get("content", raw_response)

                    step = AgentStep(
                        step_num=step_num,
                        action="final_answer",
                        content=answer,
                        raw_response=raw_response
                    )
                    steps.append(step)

                    self.emit("agent_run_complete", {
                        "agent": self.name,
                        "goal": goal[:50],
                        "steps": step_num,
                        "success": True
                    })

                    return AgentResult(
                        success=True,
                        answer=answer,
                        steps=steps,
                        goal=goal
                    )

                elif action == "tool_call":
                    tool_name = parsed.get("tool_name", "")
                    tool_args = parsed.get("arguments", {})

                    # Réponse tool_call malformée → traiter comme final_answer
                    if not tool_name:
                        step = AgentStep(
                            step_num=step_num,
                            action="final_answer",
                            content=raw_response,
                            raw_response=raw_response
                        )
                        steps.append(step)
                        return AgentResult(
                            success=True,
                            answer=raw_response,
                            steps=steps,
                            goal=goal
                        )

                    # Exécuter le tool et récupérer l'observation
                    observation = self._execute_tool(tool_name, tool_args)

                    step = AgentStep(
                        step_num=step_num,
                        action="tool_call",
                        tool_name=tool_name,
                        tool_args=tool_args,
                        observation=observation,
                        raw_response=raw_response
                    )
                    steps.append(step)

                    self.emit("agent_step_complete", {
                        "agent": self.name,
                        "step": step_num,
                        "action": "tool_call",
                        "tool_name": tool_name
                    })

                    # Ajouter l'échange tool dans l'historique
                    messages.append({
                        "role": "assistant",
                        "content": raw_response
                    })
                    messages.append({
                        "role": "tool",
                        "content": observation,
                        "name": tool_name
                    })

                else:
                    # Réponse non structurée → final_answer implicite
                    step = AgentStep(
                        step_num=step_num,
                        action="final_answer",
                        content=raw_response,
                        raw_response=raw_response
                    )
                    steps.append(step)

                    self.emit("agent_run_complete", {
                        "agent": self.name,
                        "goal": goal[:50],
                        "steps": step_num,
                        "success": True
                    })

                    return AgentResult(
                        success=True,
                        answer=raw_response,
                        steps=steps,
                        goal=goal
                    )

            # max_steps atteint sans final_answer
            self.emit("agent_max_steps_reached", {
                "agent": self.name,
                "goal": goal[:50],
                "max_steps": self._max_steps
            })

            return AgentResult(
                success=False,
                answer=f"Goal non accompli après {self._max_steps} étapes.",
                steps=steps,
                goal=goal
            )

        except Exception as e:
            self.emit("agent_run_error", {
                "agent": self.name,
                "goal": goal[:50],
                "error": str(e)
            })
            raise

    # --- Méthodes internes ---

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse la réponse JSON du LLM.

        Formats attendus :
        - {"action":"tool_call","tool_name":"xxx","arguments":{...}}
        - {"action":"final_answer","content":"..."}

        Si le JSON est invalide ou l'action inconnue, retourne
        action="final_answer" avec le texte brut comme content.

        Args:
            raw_response: Réponse brute du LLM

        Returns:
            Dict avec au moins la clé "action"
        """
        text = raw_response.strip()

        # Seul le JSON commence par {
        if not text.startswith("{"):
            return {"action": "final_answer", "content": text}

        try:
            data = json.loads(text)

            if not isinstance(data, dict):
                return {"action": "final_answer", "content": text}

            action = data.get("action", "")

            # Action inconnue → final_answer
            if action not in ("tool_call", "final_answer"):
                return {"action": "final_answer", "content": text}

            return data

        except json.JSONDecodeError:
            return {"action": "final_answer", "content": text}

    def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> str:
        """
        Exécute un tool et retourne l'observation sous forme de string.

        Args:
            tool_name: Nom du tool à exécuter
            tool_args: Arguments du tool

        Returns:
            Résultat du tool formaté comme string, ou message d'erreur.

        Note:
            Ne lève jamais d'exception : les erreurs sont retournées
            comme strings pour que l'agent puisse les observer.
        """
        if not self._tool_executor:
            return f"Erreur : aucun ToolExecutor disponible pour '{tool_name}'"

        result = self._tool_executor.execute(
            tool_name=tool_name,
            arguments=tool_args
        )

        if result.get("success"):
            tool_result = result.get("result", "")
            # Sérialiser dict/list en JSON lisible
            if isinstance(tool_result, (dict, list)):
                return json.dumps(tool_result, ensure_ascii=False)
            return str(tool_result)
        else:
            error = result.get("error", "Erreur inconnue")
            return f"Erreur tool '{tool_name}' : {error}"

    def _build_tools_description(self) -> str:
        """
        Construit la liste des tools disponibles pour le prompt système.

        Returns:
            Texte formaté des tools, ou "Aucun outil disponible."

        Example:
            >>> agent._build_tools_description()
            "- get_time(city): Get current time in a specific city\\n..."
        """
        if not self._tool_executor:
            return "Aucun outil disponible."

        registry = self._tool_executor._registry
        all_tools = registry.get_all_definitions()

        if not all_tools:
            return "Aucun outil disponible."

        lines = []
        for tool_def in all_tools:
            params = ", ".join(tool_def.parameters.keys()) if tool_def.parameters else ""
            lines.append(f"- {tool_def.name}({params}): {tool_def.description}")

        return "\n".join(lines)

    # --- Introspection ---

    @property
    def max_steps(self) -> int:
        """Nombre maximum d'étapes par run()."""
        return self._max_steps

    @property
    def has_tools(self) -> bool:
        """L'agent dispose-t-il d'un ToolExecutor ?"""
        return self._tool_executor is not None

    def __repr__(self) -> str:
        """Représentation string."""
        state = "running" if self.is_running else "stopped"
        return (
            f"AgentBase(state={state}, "
            f"has_tools={self.has_tools}, "
            f"max_steps={self._max_steps})"
        )
