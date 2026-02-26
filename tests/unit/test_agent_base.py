"""
Tests unitaires pour AgentBase (R-021)

Couvre :
- Lifecycle (start/stop/validation dépendances)
- run() → final_answer direct
- run() → tool_call → observation → final_answer
- run() → max_steps atteint (success=False)
- _parse_response() : JSON valide, JSON invalide, texte brut
- _execute_tool() : succès, erreur tool, pas de ToolExecutor
- _build_tools_description() : avec et sans tools
- Validation : goal vide, agent non démarré
- Events émis
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from eva.agents.agent_base import AgentBase, AgentResult, AgentStep


# --- Helpers / Mocks ---

def make_mock_llm(responses):
    """
    Crée un LLMClient mocké qui retourne les réponses dans l'ordre.

    Args:
        responses: Liste de strings retournées à chaque appel complete()
    """
    mock = MagicMock()
    mock.is_running = True
    mock.complete = MagicMock(side_effect=responses)
    return mock


def make_mock_executor(tool_results=None):
    """
    Crée un ToolExecutor mocké.

    Args:
        tool_results: dict {tool_name: result_value} ou None
    """
    mock = MagicMock()
    mock.is_running = True

    if tool_results:
        def execute(tool_name, arguments):
            if tool_name in tool_results:
                return {"success": True, "result": tool_results[tool_name], "tool_name": tool_name}
            return {"success": False, "error": f"Tool '{tool_name}' not found", "tool_name": tool_name}
        mock.execute = MagicMock(side_effect=execute)
    else:
        mock.execute = MagicMock(return_value={"success": True, "result": "ok", "tool_name": "test"})

    # Mock registry
    mock._registry = MagicMock()
    mock._registry.get_all_definitions.return_value = []

    return mock


# --- Fixtures ---

@pytest.fixture
def agent(config, event_bus):
    """AgentBase basique sans tools."""
    llm = make_mock_llm([])
    a = AgentBase(config, event_bus, llm=llm)
    a.start()
    yield a
    a.stop()


@pytest.fixture
def agent_with_tools(config, event_bus):
    """AgentBase avec ToolExecutor mocké."""
    llm = make_mock_llm([])
    executor = make_mock_executor()
    a = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
    a.start()
    yield a
    a.stop()


# ============================================================
# LIFECYCLE
# ============================================================

class TestAgentLifecycle:
    """Tests du cycle de vie start/stop."""

    def test_start_stop(self, config, event_bus):
        """start() puis stop() sans erreur."""
        llm = make_mock_llm([])
        agent = AgentBase(config, event_bus, llm=llm)

        agent.start()
        assert agent.is_running
        assert agent.is_started

        agent.stop()
        assert not agent.is_running
        assert not agent.is_started

    def test_start_idempotent(self, config, event_bus):
        """Appels multiples start() sans erreur."""
        llm = make_mock_llm([])
        agent = AgentBase(config, event_bus, llm=llm)
        agent.start()
        agent.start()  # idempotent
        assert agent.is_running
        agent.stop()

    def test_start_requires_llm_running(self, config, event_bus):
        """start() échoue si LLM non démarré."""
        llm = make_mock_llm([])
        llm.is_running = False  # LLM non démarré

        agent = AgentBase(config, event_bus, llm=llm)

        with pytest.raises(RuntimeError, match="LLMClient must be started"):
            agent.start()

    def test_start_requires_executor_running(self, config, event_bus):
        """start() échoue si ToolExecutor non démarré."""
        llm = make_mock_llm([])
        executor = make_mock_executor()
        executor.is_running = False  # Executor non démarré

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)

        with pytest.raises(RuntimeError, match="ToolExecutor must be started"):
            agent.start()

    def test_default_name(self, config, event_bus):
        """Nom par défaut est 'AgentBase'."""
        llm = make_mock_llm([])
        agent = AgentBase(config, event_bus, llm=llm)
        assert agent.name == "AgentBase"

    def test_custom_name(self, config, event_bus):
        """Nom personnalisé est respecté."""
        llm = make_mock_llm([])
        agent = AgentBase(config, event_bus, llm=llm, name="MyAgent")
        assert agent.name == "MyAgent"

    def test_repr(self, agent):
        """__repr__ retourne une string descriptive."""
        r = repr(agent)
        assert "AgentBase" in r
        assert "running" in r

    def test_has_tools_false(self, agent):
        """has_tools est False sans ToolExecutor."""
        assert agent.has_tools is False

    def test_has_tools_true(self, agent_with_tools):
        """has_tools est True avec ToolExecutor."""
        assert agent_with_tools.has_tools is True

    def test_max_steps_default(self, agent):
        """max_steps par défaut est 10."""
        assert agent.max_steps == 10


# ============================================================
# VALIDATION INPUT
# ============================================================

class TestRunValidation:
    """Tests de validation des inputs de run()."""

    def test_run_not_started_raises(self, config, event_bus):
        """run() sur agent non démarré lève RuntimeError."""
        llm = make_mock_llm([])
        agent = AgentBase(config, event_bus, llm=llm)

        with pytest.raises(RuntimeError, match="not started"):
            agent.run("goal")

    def test_run_empty_goal_raises(self, agent):
        """run() avec goal vide lève ValueError."""
        with pytest.raises(ValueError, match="goal cannot be empty"):
            agent.run("")

    def test_run_whitespace_goal_raises(self, agent):
        """run() avec goal espaces lève ValueError."""
        with pytest.raises(ValueError, match="goal cannot be empty"):
            agent.run("   ")


# ============================================================
# RUN — FINAL ANSWER DIRECT
# ============================================================

class TestRunFinalAnswer:
    """Tests du chemin direct final_answer sans tool call."""

    def test_run_final_answer_json(self, config, event_bus):
        """LLM retourne final_answer JSON → AgentResult.success=True."""
        response = json.dumps({"action": "final_answer", "content": "La réponse est 42."})
        llm = make_mock_llm([response])
        agent = AgentBase(config, event_bus, llm=llm)
        agent.start()

        result = agent.run("Quel est le sens de la vie ?")

        assert result.success is True
        assert result.answer == "La réponse est 42."
        assert result.goal == "Quel est le sens de la vie ?"
        assert len(result.steps) == 1
        assert result.steps[0].action == "final_answer"

        agent.stop()

    def test_run_plain_text_response(self, config, event_bus):
        """LLM retourne texte brut → traité comme final_answer."""
        llm = make_mock_llm(["Bonjour, comment puis-je vous aider ?"])
        agent = AgentBase(config, event_bus, llm=llm)
        agent.start()

        result = agent.run("Bonjour")

        assert result.success is True
        assert result.answer == "Bonjour, comment puis-je vous aider ?"
        assert len(result.steps) == 1

        agent.stop()

    def test_run_result_contains_goal(self, config, event_bus):
        """AgentResult.goal est égal au goal passé."""
        response = json.dumps({"action": "final_answer", "content": "ok"})
        llm = make_mock_llm([response])
        agent = AgentBase(config, event_bus, llm=llm)
        agent.start()

        result = agent.run("  goal avec espaces  ")
        assert result.goal == "goal avec espaces"  # strippé

        agent.stop()

    def test_run_step_has_raw_response(self, config, event_bus):
        """AgentStep.raw_response contient la réponse brute."""
        raw = json.dumps({"action": "final_answer", "content": "réponse"})
        llm = make_mock_llm([raw])
        agent = AgentBase(config, event_bus, llm=llm)
        agent.start()

        result = agent.run("goal")
        assert result.steps[0].raw_response == raw

        agent.stop()


# ============================================================
# RUN — TOOL CALL → FINAL ANSWER
# ============================================================

class TestRunToolCall:
    """Tests du chemin tool_call → observation → final_answer."""

    def _make_tool_response(self, tool_name, args):
        return json.dumps({
            "action": "tool_call",
            "tool_name": tool_name,
            "arguments": args
        })

    def _make_final_response(self, content):
        return json.dumps({"action": "final_answer", "content": content})

    def test_tool_call_then_final_answer(self, config, event_bus):
        """tool_call suivi de final_answer → 2 steps, success=True."""
        tool_response = self._make_tool_response("calc", {"expression": "2+2"})
        final_response = self._make_final_response("Le résultat est 4.")

        llm = make_mock_llm([tool_response, final_response])
        executor = make_mock_executor(tool_results={"calc": 4})

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        result = agent.run("Combien fait 2+2 ?")

        assert result.success is True
        assert result.answer == "Le résultat est 4."
        assert len(result.steps) == 2

        # Step 1 : tool_call
        step1 = result.steps[0]
        assert step1.action == "tool_call"
        assert step1.tool_name == "calc"
        assert step1.tool_args == {"expression": "2+2"}
        assert "4" in step1.observation

        # Step 2 : final_answer
        step2 = result.steps[1]
        assert step2.action == "final_answer"
        assert step2.content == "Le résultat est 4."

        agent.stop()

    def test_tool_call_executor_called_with_correct_args(self, config, event_bus):
        """ToolExecutor.execute() appelé avec les bons arguments."""
        tool_response = self._make_tool_response("get_time", {"city": "Tokyo"})
        final_response = self._make_final_response("Il est 09:30 à Tokyo.")

        llm = make_mock_llm([tool_response, final_response])
        executor = make_mock_executor(tool_results={"get_time": "09:30"})

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        agent.run("Heure à Tokyo ?")

        executor.execute.assert_called_once_with(
            tool_name="get_time",
            arguments={"city": "Tokyo"}
        )

        agent.stop()

    def test_tool_call_missing_tool_name(self, config, event_bus):
        """tool_call sans tool_name → traité comme final_answer."""
        malformed = json.dumps({"action": "tool_call", "arguments": {}})
        llm = make_mock_llm([malformed])
        executor = make_mock_executor()

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        result = agent.run("goal")
        assert result.success is True
        assert len(result.steps) == 1

        agent.stop()

    def test_tool_error_observation(self, config, event_bus):
        """Si tool échoue, l'observation contient le message d'erreur."""
        tool_response = self._make_tool_response("unknown_tool", {})
        final_response = self._make_final_response("Désolé, l'outil n'est pas disponible.")

        llm = make_mock_llm([tool_response, final_response])
        executor = make_mock_executor()  # retourne success=True par défaut

        # Forcer l'erreur
        executor.execute.return_value = {
            "success": False,
            "error": "Tool 'unknown_tool' not found",
            "tool_name": "unknown_tool"
        }

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        result = agent.run("goal")
        step1 = result.steps[0]
        assert "Erreur" in step1.observation
        assert "unknown_tool" in step1.observation

        agent.stop()

    def test_tool_result_dict_serialized(self, config, event_bus):
        """Résultat dict du tool est sérialisé en JSON dans l'observation."""
        tool_response = self._make_tool_response("get_info", {})
        final_response = self._make_final_response("Info reçue.")

        llm = make_mock_llm([tool_response, final_response])
        executor = make_mock_executor(tool_results={"get_info": {"key": "value"}})

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        result = agent.run("goal")
        obs = result.steps[0].observation
        assert '"key"' in obs  # dict sérialisé en JSON

        agent.stop()


# ============================================================
# RUN — MAX STEPS
# ============================================================

class TestRunMaxSteps:
    """Tests du comportement quand max_steps est atteint."""

    def test_max_steps_returns_failure(self, config, event_bus):
        """Atteindre max_steps → AgentResult.success=False."""
        # LLM répond toujours tool_call (jamais final_answer)
        tool_response = json.dumps({
            "action": "tool_call",
            "tool_name": "loop_tool",
            "arguments": {}
        })
        llm = make_mock_llm([tool_response] * 5)  # 5 réponses
        executor = make_mock_executor(tool_results={"loop_tool": "ok"})

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor, name="TestAgent")
        # Forcer max_steps = 3
        agent._max_steps = 3
        agent.start()

        result = agent.run("Boucle infinie ?")

        assert result.success is False
        assert "3" in result.answer  # mentionne le nombre d'étapes
        assert len(result.steps) == 3

        agent.stop()

    def test_max_steps_one_final_answer(self, config, event_bus):
        """Avec max_steps=1 et final_answer → success=True."""
        response = json.dumps({"action": "final_answer", "content": "ok"})
        llm = make_mock_llm([response])

        agent = AgentBase(config, event_bus, llm=llm)
        agent._max_steps = 1
        agent.start()

        result = agent.run("goal")
        assert result.success is True

        agent.stop()


# ============================================================
# _parse_response
# ============================================================

class TestParseResponse:
    """Tests unitaires de _parse_response()."""

    def test_final_answer_json(self, agent):
        """JSON final_answer valide."""
        raw = json.dumps({"action": "final_answer", "content": "réponse"})
        parsed = agent._parse_response(raw)
        assert parsed["action"] == "final_answer"
        assert parsed["content"] == "réponse"

    def test_tool_call_json(self, agent):
        """JSON tool_call valide."""
        raw = json.dumps({"action": "tool_call", "tool_name": "calc", "arguments": {"n": 1}})
        parsed = agent._parse_response(raw)
        assert parsed["action"] == "tool_call"
        assert parsed["tool_name"] == "calc"
        assert parsed["arguments"] == {"n": 1}

    def test_plain_text(self, agent):
        """Texte brut → final_answer implicite."""
        parsed = agent._parse_response("Bonjour !")
        assert parsed["action"] == "final_answer"
        assert parsed["content"] == "Bonjour !"

    def test_invalid_json(self, agent):
        """JSON invalide → final_answer avec texte brut."""
        parsed = agent._parse_response("{ceci n'est pas du json}")
        assert parsed["action"] == "final_answer"

    def test_unknown_action(self, agent):
        """Action inconnue → final_answer."""
        raw = json.dumps({"action": "unknown_action", "data": "x"})
        parsed = agent._parse_response(raw)
        assert parsed["action"] == "final_answer"

    def test_not_a_dict(self, agent):
        """JSON array → final_answer."""
        raw = json.dumps(["item1", "item2"])
        parsed = agent._parse_response(raw)
        assert parsed["action"] == "final_answer"

    def test_whitespace_stripped(self, agent):
        """Espaces autour du JSON ignorés."""
        raw = "  " + json.dumps({"action": "final_answer", "content": "ok"}) + "  "
        parsed = agent._parse_response(raw)
        assert parsed["action"] == "final_answer"


# ============================================================
# _execute_tool
# ============================================================

class TestExecuteTool:
    """Tests unitaires de _execute_tool()."""

    def test_no_executor_returns_error(self, agent):
        """Sans ToolExecutor → message d'erreur."""
        obs = agent._execute_tool("calc", {"n": 1})
        assert "Erreur" in obs
        assert "calc" in obs

    def test_success_string_result(self, config, event_bus):
        """Résultat string retourné tel quel."""
        llm = make_mock_llm([])
        executor = make_mock_executor(tool_results={"tool": "hello"})
        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        obs = agent._execute_tool("tool", {})
        assert obs == "hello"

        agent.stop()

    def test_success_int_result(self, config, event_bus):
        """Résultat int converti en string."""
        llm = make_mock_llm([])
        executor = make_mock_executor(tool_results={"calc": 42})
        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        obs = agent._execute_tool("calc", {})
        assert obs == "42"

        agent.stop()

    def test_success_dict_result(self, config, event_bus):
        """Résultat dict sérialisé en JSON."""
        llm = make_mock_llm([])
        executor = make_mock_executor(tool_results={"info": {"status": "ok"}})
        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        obs = agent._execute_tool("info", {})
        data = json.loads(obs)
        assert data["status"] == "ok"

        agent.stop()

    def test_tool_error(self, config, event_bus):
        """Tool en erreur → message d'erreur dans l'observation."""
        llm = make_mock_llm([])
        executor = make_mock_executor()
        executor.execute.return_value = {
            "success": False,
            "error": "Division by zero",
            "tool_name": "calc"
        }

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        obs = agent._execute_tool("calc", {"n": 0})
        assert "Division by zero" in obs

        agent.stop()


# ============================================================
# _build_tools_description
# ============================================================

class TestBuildToolsDescription:
    """Tests de _build_tools_description()."""

    def test_no_executor(self, agent):
        """Sans ToolExecutor → 'Aucun outil disponible.'"""
        desc = agent._build_tools_description()
        assert "Aucun" in desc

    def test_empty_registry(self, agent_with_tools):
        """Registry vide → 'Aucun outil disponible.'"""
        agent_with_tools._tool_executor._registry.get_all_definitions.return_value = []
        desc = agent_with_tools._build_tools_description()
        assert "Aucun" in desc

    def test_tools_listed(self, config, event_bus):
        """Tools enregistrés → liste formatée."""
        llm = make_mock_llm([])
        executor = make_mock_executor()

        # Créer des mocks de ToolDefinition
        tool1 = MagicMock()
        tool1.name = "get_time"
        tool1.description = "Get time"
        tool1.parameters = {"city": {}}

        tool2 = MagicMock()
        tool2.name = "calc"
        tool2.description = "Calculate"
        tool2.parameters = {"expression": {}}

        executor._registry.get_all_definitions.return_value = [tool1, tool2]

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent.start()

        desc = agent._build_tools_description()
        assert "get_time" in desc
        assert "calc" in desc
        assert "Get time" in desc

        agent.stop()


# ============================================================
# EVENTS
# ============================================================

class TestAgentEvents:
    """Tests que les événements sont émis correctement."""

    def test_run_start_event(self, config, event_bus):
        """agent_run_start est émis au début de run()."""
        response = json.dumps({"action": "final_answer", "content": "ok"})
        llm = make_mock_llm([response])
        agent = AgentBase(config, event_bus, llm=llm)
        agent.start()

        events = []
        event_bus.on("agent_run_start", lambda e: events.append(e))

        agent.run("goal")
        assert len(events) == 1
        assert events[0]["goal"] == "goal"

        agent.stop()

    def test_run_complete_event(self, config, event_bus):
        """agent_run_complete est émis à la fin d'un run réussi."""
        response = json.dumps({"action": "final_answer", "content": "ok"})
        llm = make_mock_llm([response])
        agent = AgentBase(config, event_bus, llm=llm)
        agent.start()

        events = []
        event_bus.on("agent_run_complete", lambda e: events.append(e))

        agent.run("goal")
        assert len(events) == 1
        assert events[0]["success"] is True

        agent.stop()

    def test_agent_started_event(self, config, event_bus):
        """agent_started est émis au démarrage."""
        llm = make_mock_llm([])
        agent = AgentBase(config, event_bus, llm=llm)

        events = []
        event_bus.on("agent_started", lambda e: events.append(e))

        agent.start()
        assert len(events) == 1
        assert events[0]["max_steps"] == 10

        agent.stop()

    def test_max_steps_event(self, config, event_bus):
        """agent_max_steps_reached est émis quand max_steps atteint."""
        tool_response = json.dumps({"action": "tool_call", "tool_name": "t", "arguments": {}})
        llm = make_mock_llm([tool_response] * 3)
        executor = make_mock_executor(tool_results={"t": "ok"})

        agent = AgentBase(config, event_bus, llm=llm, tool_executor=executor)
        agent._max_steps = 2
        agent.start()

        events = []
        event_bus.on("agent_max_steps_reached", lambda e: events.append(e))

        agent.run("goal")
        assert len(events) == 1

        agent.stop()
