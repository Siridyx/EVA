"""
Tests R-033 — Command Registry.

Couvre :
- CommandResult : structure, valeurs par défaut
- Command : structure, aliases
- CommandRegistry : register, get, execute, completions, list_commands
- Erreurs : duplicate, commande inconnue, handler exception
- Commandes par défaut : cmd_help, cmd_status, cmd_start, cmd_stop,
                         cmd_new, cmd_config, cmd_clear, cmd_quit
- make_default_registry : registry complet
"""

import pytest
from unittest.mock import MagicMock

from eva.ui.command_registry import (
    Command,
    CommandContext,
    CommandRegistry,
    CommandResult,
    DuplicateCommandError,
)
from eva.ui.commands import (
    cmd_clear,
    cmd_config,
    cmd_help,
    cmd_new,
    cmd_quit,
    cmd_start,
    cmd_status,
    cmd_stop,
    make_default_registry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_ok_handler(msg: str = "ok"):
    """Fabrique un handler qui retourne toujours success=True."""

    def handler(args: str, ctx: CommandContext) -> CommandResult:
        return CommandResult(success=True, output=msg)

    return handler


def make_failing_handler():
    """Fabrique un handler qui lève une exception."""

    def handler(args: str, ctx: CommandContext) -> CommandResult:
        raise RuntimeError("handler crash")

    return handler


def empty_ctx() -> CommandContext:
    return CommandContext()


def engine_ctx(is_running: bool = False) -> CommandContext:
    """Contexte avec un engine mocké."""
    engine = MagicMock()
    engine.is_running = is_running
    engine.status.return_value = {
        "name": "EVAEngine",
        "running": is_running,
        "pipeline_mode": "sequential",
        "pipeline_initialized": True,
        "components": {"llm": True, "memory": True, "conversation": True},
    }
    return CommandContext(engine=engine)


def config_ctx() -> CommandContext:
    """Contexte avec un config mocké."""
    config = MagicMock()
    config.version = "0.2.0-p2"
    config.environment = "test"
    config.get.return_value = "30"
    return CommandContext(config=config)


# ---------------------------------------------------------------------------
# TestCommandResult
# ---------------------------------------------------------------------------


class TestCommandResult:
    def test_success_true(self):
        r = CommandResult(success=True, output="ok")
        assert r.success is True
        assert r.output == "ok"

    def test_success_false(self):
        r = CommandResult(success=False, output="nope")
        assert r.success is False

    def test_defaults(self):
        r = CommandResult(success=True, output="")
        assert r.event is None
        assert r.event_payload is None
        assert r.should_quit is False

    def test_event_fields(self):
        r = CommandResult(
            success=True,
            output="bye",
            event="cli_quit",
            event_payload={"source": "user"},
            should_quit=True,
        )
        assert r.event == "cli_quit"
        assert r.event_payload == {"source": "user"}
        assert r.should_quit is True


# ---------------------------------------------------------------------------
# TestCommand
# ---------------------------------------------------------------------------


class TestCommand:
    def test_basic(self):
        h = make_ok_handler()
        cmd = Command(name="test", help="desc", handler=h)
        assert cmd.name == "test"
        assert cmd.help == "desc"
        assert cmd.handler is h
        assert cmd.aliases == []

    def test_aliases(self):
        cmd = Command(name="quit", help="quitter", handler=make_ok_handler(), aliases=["q", "exit"])
        assert "q" in cmd.aliases
        assert "exit" in cmd.aliases

    def test_handler_called(self):
        h = make_ok_handler("réponse")
        cmd = Command(name="x", help="x", handler=h)
        result = cmd.handler("", empty_ctx())
        assert result.output == "réponse"


# ---------------------------------------------------------------------------
# TestCommandRegistry — Register
# ---------------------------------------------------------------------------


class TestCommandRegistryRegister:
    def test_register_single(self):
        registry = CommandRegistry()
        registry.register(Command("help", "aide", make_ok_handler()))
        assert len(registry) == 1

    def test_register_multiple(self):
        registry = CommandRegistry()
        registry.register(Command("a", "a", make_ok_handler()))
        registry.register(Command("b", "b", make_ok_handler()))
        registry.register(Command("c", "c", make_ok_handler()))
        assert len(registry) == 3

    def test_register_duplicate_name_raises(self):
        registry = CommandRegistry()
        registry.register(Command("help", "aide", make_ok_handler()))
        with pytest.raises(DuplicateCommandError):
            registry.register(Command("help", "aide2", make_ok_handler()))

    def test_register_duplicate_alias_raises(self):
        registry = CommandRegistry()
        registry.register(Command("quit", "quitter", make_ok_handler(), aliases=["q"]))
        with pytest.raises(DuplicateCommandError):
            registry.register(Command("exit", "exit", make_ok_handler(), aliases=["q"]))

    def test_register_alias_conflicts_with_name_raises(self):
        registry = CommandRegistry()
        registry.register(Command("help", "aide", make_ok_handler()))
        with pytest.raises(DuplicateCommandError):
            registry.register(Command("autre", "autre", make_ok_handler(), aliases=["help"]))

    def test_register_with_aliases(self):
        registry = CommandRegistry()
        registry.register(Command("quit", "quitter", make_ok_handler(), aliases=["q", "exit"]))
        assert registry.get("q") is not None
        assert registry.get("exit") is not None


# ---------------------------------------------------------------------------
# TestCommandRegistry — Get
# ---------------------------------------------------------------------------


class TestCommandRegistryGet:
    def setup_method(self):
        self.registry = CommandRegistry()
        self.registry.register(
            Command("help", "aide", make_ok_handler(), aliases=["h", "?"])
        )

    def test_get_by_name(self):
        cmd = self.registry.get("help")
        assert cmd is not None
        assert cmd.name == "help"

    def test_get_by_alias(self):
        cmd = self.registry.get("h")
        assert cmd is not None
        assert cmd.name == "help"

    def test_get_by_alias_question_mark(self):
        cmd = self.registry.get("?")
        assert cmd is not None
        assert cmd.name == "help"

    def test_get_unknown_returns_none(self):
        assert self.registry.get("unknown") is None

    def test_get_case_insensitive(self):
        cmd = self.registry.get("HELP")
        assert cmd is not None

    def test_get_alias_case_insensitive(self):
        cmd = self.registry.get("H")
        assert cmd is not None


# ---------------------------------------------------------------------------
# TestCommandRegistry — Execute
# ---------------------------------------------------------------------------


class TestCommandRegistryExecute:
    def setup_method(self):
        self.registry = CommandRegistry()
        self.registry.register(Command("hello", "salut", make_ok_handler("salut!")))
        self.registry.register(
            Command("echo", "echo", lambda args, ctx: CommandResult(True, f"echo:{args}"))
        )
        self.registry.register(Command("boom", "boom", make_failing_handler()))
        self.registry.register(
            Command("quit", "quit", make_ok_handler("bye"), aliases=["q"])
        )

    def test_execute_simple(self):
        result = self.registry.execute("/hello", empty_ctx())
        assert result.success is True
        assert result.output == "salut!"

    def test_execute_without_slash(self):
        result = self.registry.execute("hello", empty_ctx())
        assert result.success is True

    def test_execute_with_args(self):
        result = self.registry.execute("/echo world", empty_ctx())
        assert result.output == "echo:world"

    def test_execute_with_args_multi_word(self):
        result = self.registry.execute("/echo foo bar baz", empty_ctx())
        assert result.output == "echo:foo bar baz"

    def test_execute_empty_returns_error(self):
        result = self.registry.execute("/", empty_ctx())
        assert result.success is False

    def test_execute_unknown_returns_error(self):
        result = self.registry.execute("/unknown", empty_ctx())
        assert result.success is False
        assert "unknown" in result.output

    def test_execute_handler_exception_returns_error(self):
        result = self.registry.execute("/boom", empty_ctx())
        assert result.success is False
        assert "boom" in result.output

    def test_execute_via_alias(self):
        result = self.registry.execute("/q", empty_ctx())
        assert result.success is True
        assert result.output == "bye"

    def test_execute_case_insensitive(self):
        result = self.registry.execute("/HELLO", empty_ctx())
        assert result.success is True


# ---------------------------------------------------------------------------
# TestCommandRegistry — Completions
# ---------------------------------------------------------------------------


class TestCommandRegistryCompletions:
    def setup_method(self):
        self.registry = CommandRegistry()
        self.registry.register(Command("help", "aide", make_ok_handler(), aliases=["h"]))
        self.registry.register(Command("status", "statut", make_ok_handler()))
        self.registry.register(Command("quit", "quitter", make_ok_handler(), aliases=["q"]))

    def test_prefix_slash_h(self):
        results = self.registry.get_completions("/h")
        assert "/help" in results
        assert "/h" in results  # alias

    def test_prefix_no_slash(self):
        results = self.registry.get_completions("h")
        assert "/help" in results

    def test_prefix_empty(self):
        results = self.registry.get_completions("")
        # Toutes les commandes + aliases
        assert "/help" in results
        assert "/status" in results
        assert "/quit" in results

    def test_prefix_s(self):
        results = self.registry.get_completions("/s")
        assert "/status" in results
        assert "/help" not in results

    def test_prefix_no_match(self):
        results = self.registry.get_completions("/zzz")
        assert results == []

    def test_results_sorted(self):
        results = self.registry.get_completions("")
        assert results == sorted(results)

    def test_no_duplicates(self):
        results = self.registry.get_completions("")
        assert len(results) == len(set(results))


# ---------------------------------------------------------------------------
# TestCommandRegistry — list_commands
# ---------------------------------------------------------------------------


class TestCommandRegistryListCommands:
    def test_empty(self):
        registry = CommandRegistry()
        assert registry.list_commands() == []

    def test_lists_all(self):
        registry = CommandRegistry()
        registry.register(Command("a", "a", make_ok_handler()))
        registry.register(Command("b", "b", make_ok_handler()))
        names = [c.name for c in registry.list_commands()]
        assert "a" in names
        assert "b" in names

    def test_no_alias_duplicates(self):
        registry = CommandRegistry()
        registry.register(Command("quit", "quitter", make_ok_handler(), aliases=["q", "exit"]))
        # Doit retourner 1 seul Command, pas 3
        assert len(registry.list_commands()) == 1

    def test_repr(self):
        registry = CommandRegistry()
        registry.register(Command("help", "aide", make_ok_handler(), aliases=["h"]))
        r = repr(registry)
        assert "CommandRegistry" in r
        assert "commands=1" in r
        assert "aliases=1" in r


# ---------------------------------------------------------------------------
# TestCmdHelp
# ---------------------------------------------------------------------------


class TestCmdHelp:
    def test_with_registry(self):
        registry = make_default_registry()
        ctx = CommandContext(registry=registry)
        result = cmd_help("", ctx)
        assert result.success is True
        assert "help" in result.output
        assert "quit" in result.output

    def test_without_registry_fallback(self):
        result = cmd_help("", empty_ctx())
        assert result.success is True
        assert "/help" in result.output

    def test_shows_aliases(self):
        registry = make_default_registry()
        ctx = CommandContext(registry=registry)
        result = cmd_help("", ctx)
        # Les aliases sont inclus dans l'aide
        assert "/h" in result.output or "/q" in result.output


# ---------------------------------------------------------------------------
# TestCmdStatus
# ---------------------------------------------------------------------------


class TestCmdStatus:
    def test_no_engine(self):
        result = cmd_status("", empty_ctx())
        assert result.success is False
        assert "initialisé" in result.output

    def test_engine_running(self):
        ctx = engine_ctx(is_running=True)
        result = cmd_status("", ctx)
        assert result.success is True
        assert "RUNNING" in result.output

    def test_engine_stopped(self):
        ctx = engine_ctx(is_running=False)
        result = cmd_status("", ctx)
        assert result.success is True
        assert "STOPPED" in result.output

    def test_contains_components(self):
        ctx = engine_ctx(is_running=True)
        result = cmd_status("", ctx)
        assert "LLM" in result.output
        assert "Memory" in result.output

    def test_engine_raises(self):
        engine = MagicMock()
        engine.is_running = True
        engine.status.side_effect = RuntimeError("oops")
        ctx = CommandContext(engine=engine)
        result = cmd_status("", ctx)
        assert result.success is False
        assert "Erreur" in result.output


# ---------------------------------------------------------------------------
# TestCmdStart
# ---------------------------------------------------------------------------


class TestCmdStart:
    def test_no_engine(self):
        result = cmd_start("", empty_ctx())
        assert result.success is False

    def test_already_running(self):
        ctx = engine_ctx(is_running=True)
        result = cmd_start("", ctx)
        assert result.success is False
        assert "déjà" in result.output

    def test_starts_engine(self):
        ctx = engine_ctx(is_running=False)
        result = cmd_start("", ctx)
        assert result.success is True
        ctx.engine.start.assert_called_once()

    def test_emits_event(self):
        ctx = engine_ctx(is_running=False)
        result = cmd_start("", ctx)
        assert result.event == "engine_started"
        assert result.event_payload == {"source": "cli"}

    def test_start_raises(self):
        engine = MagicMock()
        engine.is_running = False
        engine.start.side_effect = RuntimeError("no")
        ctx = CommandContext(engine=engine)
        result = cmd_start("", ctx)
        assert result.success is False


# ---------------------------------------------------------------------------
# TestCmdStop
# ---------------------------------------------------------------------------


class TestCmdStop:
    def test_no_engine(self):
        result = cmd_stop("", empty_ctx())
        assert result.success is False

    def test_already_stopped(self):
        ctx = engine_ctx(is_running=False)
        result = cmd_stop("", ctx)
        assert result.success is False
        assert "déjà" in result.output

    def test_stops_engine(self):
        ctx = engine_ctx(is_running=True)
        result = cmd_stop("", ctx)
        assert result.success is True
        ctx.engine.stop.assert_called_once()

    def test_emits_event(self):
        ctx = engine_ctx(is_running=True)
        result = cmd_stop("", ctx)
        assert result.event == "engine_stopped"


# ---------------------------------------------------------------------------
# TestCmdNew
# ---------------------------------------------------------------------------


class TestCmdNew:
    def test_returns_success(self):
        result = cmd_new("", empty_ctx())
        assert result.success is True
        assert "conversation" in result.output.lower()


# ---------------------------------------------------------------------------
# TestCmdConfig
# ---------------------------------------------------------------------------


class TestCmdConfig:
    def test_no_config(self):
        result = cmd_config("", empty_ctx())
        assert result.success is False

    def test_overview(self):
        ctx = config_ctx()
        result = cmd_config("", ctx)
        assert result.success is True
        assert "0.2.0-p2" in result.output

    def test_get_key(self):
        ctx = config_ctx()
        result = cmd_config("get llm.timeout", ctx)
        assert result.success is True
        assert "llm.timeout" in result.output

    def test_get_key_missing_key(self):
        result = cmd_config("get", config_ctx())
        assert result.success is False
        assert "KEY" in result.output

    def test_get_key_not_found(self):
        ctx = config_ctx()
        ctx.config.get.return_value = None
        result = cmd_config("get nonexistent", ctx)
        assert result.success is False
        assert "introuvable" in result.output


# ---------------------------------------------------------------------------
# TestCmdClear
# ---------------------------------------------------------------------------


class TestCmdClear:
    def test_returns_ansi(self):
        result = cmd_clear("", empty_ctx())
        assert result.success is True
        # ANSI clear screen
        assert "\033[2J" in result.output

    def test_no_io(self):
        # Ne crash pas, retourne toujours quelque chose
        result = cmd_clear("anything", empty_ctx())
        assert result.success is True


# ---------------------------------------------------------------------------
# TestCmdQuit
# ---------------------------------------------------------------------------


class TestCmdQuit:
    def test_should_quit(self):
        result = cmd_quit("", empty_ctx())
        assert result.should_quit is True

    def test_success(self):
        result = cmd_quit("", empty_ctx())
        assert result.success is True

    def test_event(self):
        result = cmd_quit("", empty_ctx())
        assert result.event == "cli_quit"
        assert result.event_payload == {"source": "user"}

    def test_farewell_message(self):
        result = cmd_quit("", empty_ctx())
        assert result.output  # Non vide


# ---------------------------------------------------------------------------
# TestMakeDefaultRegistry
# ---------------------------------------------------------------------------


class TestMakeDefaultRegistry:
    def setup_method(self):
        self.registry = make_default_registry()

    def test_has_help(self):
        assert self.registry.get("help") is not None

    def test_has_status(self):
        assert self.registry.get("status") is not None

    def test_has_start(self):
        assert self.registry.get("start") is not None

    def test_has_stop(self):
        assert self.registry.get("stop") is not None

    def test_has_new(self):
        assert self.registry.get("new") is not None

    def test_has_config(self):
        assert self.registry.get("config") is not None

    def test_has_clear(self):
        assert self.registry.get("clear") is not None

    def test_has_quit(self):
        assert self.registry.get("quit") is not None

    def test_aliases_h_for_help(self):
        assert self.registry.get("h") is not None
        assert self.registry.get("h").name == "help"

    def test_aliases_q_for_quit(self):
        assert self.registry.get("q") is not None
        assert self.registry.get("q").name == "quit"

    def test_aliases_exit_for_quit(self):
        assert self.registry.get("exit") is not None
        assert self.registry.get("exit").name == "quit"

    def test_aliases_cls_for_clear(self):
        assert self.registry.get("cls") is not None
        assert self.registry.get("cls").name == "clear"

    def test_aliases_cfg_for_config(self):
        assert self.registry.get("cfg") is not None
        assert self.registry.get("cfg").name == "config"

    def test_execute_help(self):
        ctx = CommandContext(registry=self.registry)
        result = self.registry.execute("/help", ctx)
        assert result.success is True
        assert result.output

    def test_execute_quit_should_quit(self):
        result = self.registry.execute("/quit", empty_ctx())
        assert result.should_quit is True

    def test_execute_quit_via_q(self):
        result = self.registry.execute("/q", empty_ctx())
        assert result.should_quit is True

    def test_execute_clear(self):
        result = self.registry.execute("/clear", empty_ctx())
        assert result.success is True

    def test_execute_unknown(self):
        result = self.registry.execute("/doesnotexist", empty_ctx())
        assert result.success is False

    def test_list_commands_count(self):
        # 8 commandes : help, status, start, stop, new, config, clear, quit
        assert len(self.registry.list_commands()) == 8

    def test_completions_slash_s(self):
        completions = self.registry.get_completions("/s")
        names = [c.lstrip("/") for c in completions]
        assert "status" in names
        assert "start" in names
        assert "stop" in names

    def test_completions_slash_q(self):
        completions = self.registry.get_completions("/q")
        assert "/quit" in completions or "/q" in completions
