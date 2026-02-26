"""
Tests du Terminal UI Textual (R-030).

Stratégie :
- Tests sans UI (purs unitaires) : méthodes de rendu, attributs, TCSS, CLI flag
- Tests avec Textual pilot : compose, dispatch, input (skippés si textual absent)

Standards :
- Python 3.9 strict
- Isolation : mocks pour composants EVA (pas de LLM réel)
- Pas d'accès réseau
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import conditionnel : les tests Textual requièrent textual installé
# ---------------------------------------------------------------------------

try:
    from eva.ui.tui.app import (
        ChatView,
        EvaTuiApp,
        EvaInput,
        MessageWidget,
        StatusSidebar,
        main,
    )

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

requires_textual = pytest.mark.skipif(
    not TEXTUAL_AVAILABLE,
    reason="textual non installé — pip install 'eva-assistant[dev]'",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_engine():
    """EVAEngine mocké pour tests sans LLM réel."""
    engine = MagicMock()
    engine.is_running = True
    engine.status.return_value = {
        "name": "EVAEngine",
        "running": True,
        "started": True,
        "pipeline_mode": "sequential",
        "pipeline_initialized": True,
        "components": {
            "llm": True,
            "memory": True,
            "conversation": True,
        },
    }
    engine.process.return_value = "Réponse de test."
    return engine


@pytest.fixture
def mock_engine_stopped():
    """EVAEngine arrêté."""
    engine = MagicMock()
    engine.is_running = False
    engine.status.return_value = {
        "name": "EVAEngine",
        "running": False,
        "started": False,
        "pipeline_mode": "sequential",
        "pipeline_initialized": False,
        "components": {
            "llm": False,
            "memory": False,
            "conversation": False,
        },
    }
    return engine


# ---------------------------------------------------------------------------
# 1. Tests StatusSidebar — rendu (sans UI)
# ---------------------------------------------------------------------------


@requires_textual
class TestStatusSidebarRender:
    """Tests des méthodes de rendu sans lancer l'UI."""

    def test_render_no_engine_contains_stopped(self):
        sidebar = StatusSidebar()
        result = sidebar._render_no_engine()
        assert "STOPPED" in result

    def test_render_no_engine_contains_statut(self):
        sidebar = StatusSidebar()
        result = sidebar._render_no_engine()
        assert "STATUT" in result

    def test_render_no_engine_contains_help_hint(self):
        sidebar = StatusSidebar()
        result = sidebar._render_no_engine()
        assert "/help" in result

    def test_render_status_running(self, mock_engine):
        sidebar = StatusSidebar()
        result = sidebar._render_status(mock_engine.status())
        assert "RUNNING" in result
        assert "●" in result

    def test_render_status_stopped(self, mock_engine_stopped):
        sidebar = StatusSidebar()
        result = sidebar._render_status(mock_engine_stopped.status())
        assert "STOPPED" in result
        assert "○" in result

    def test_render_status_components_ok(self, mock_engine):
        sidebar = StatusSidebar()
        result = sidebar._render_status(mock_engine.status())
        assert "OK" in result

    def test_render_status_components_na(self, mock_engine_stopped):
        sidebar = StatusSidebar()
        result = sidebar._render_status(mock_engine_stopped.status())
        assert "N/A" in result


# ---------------------------------------------------------------------------
# 2. Tests du fichier TCSS (sans UI)
# ---------------------------------------------------------------------------


class TestTheme:
    """Tests du fichier de styles TCSS."""

    def test_tcss_file_exists(self):
        tcss_path = Path(__file__).parent.parent.parent / "eva" / "ui" / "tui" / "styles.tcss"
        assert tcss_path.exists(), f"styles.tcss introuvable : {tcss_path}"

    def test_tcss_contains_chat_id(self):
        tcss_path = Path(__file__).parent.parent.parent / "eva" / "ui" / "tui" / "styles.tcss"
        content = tcss_path.read_text(encoding="utf-8")
        assert "#chat" in content

    def test_tcss_contains_sidebar_id(self):
        tcss_path = Path(__file__).parent.parent.parent / "eva" / "ui" / "tui" / "styles.tcss"
        content = tcss_path.read_text(encoding="utf-8")
        assert "#sidebar" in content

    def test_tcss_contains_msg_eva_class(self):
        tcss_path = Path(__file__).parent.parent.parent / "eva" / "ui" / "tui" / "styles.tcss"
        content = tcss_path.read_text(encoding="utf-8")
        assert ".msg-eva" in content

    def test_tcss_contains_cyan_color(self):
        tcss_path = Path(__file__).parent.parent.parent / "eva" / "ui" / "tui" / "styles.tcss"
        content = tcss_path.read_text(encoding="utf-8")
        assert "#00d4ff" in content

    def test_tcss_contains_dark_background(self):
        tcss_path = Path(__file__).parent.parent.parent / "eva" / "ui" / "tui" / "styles.tcss"
        content = tcss_path.read_text(encoding="utf-8")
        assert "#0a0a1a" in content


# ---------------------------------------------------------------------------
# 3. Tests EvaTuiApp attributs initiaux (sans lancer l'UI)
# ---------------------------------------------------------------------------


@requires_textual
class TestEvaTuiAppInit:
    """Tests des attributs initiaux sans lancer l'UI."""

    def test_app_instanciable(self):
        app = EvaTuiApp()
        assert app is not None

    def test_initial_engine_none(self):
        app = EvaTuiApp()
        assert app.engine is None

    def test_initial_config_none(self):
        app = EvaTuiApp()
        assert app.config is None

    def test_registry_initialized(self):
        app = EvaTuiApp()
        assert app._cmd_registry is not None

    def test_registry_has_default_commands(self):
        app = EvaTuiApp()
        commands = app._cmd_registry.list_commands()
        names = [cmd.name for cmd in commands]
        assert "help" in names
        assert "quit" in names
        assert "status" in names

    def test_title_contains_version(self):
        from eva import __version__
        assert __version__ in EvaTuiApp.TITLE

    def test_css_path_is_tcss(self):
        css_path = EvaTuiApp.CSS_PATH
        assert str(css_path).endswith("styles.tcss")


# ---------------------------------------------------------------------------
# 4. Tests CLI flag --tui (sans UI)
# ---------------------------------------------------------------------------


class TestCLITuiFlag:
    """Tests du flag --tui dans argparse."""

    def test_cli_has_tui_flag(self):
        import argparse
        from eva.cli import main as cli_main

        # On ne peut pas tester main() directement sans le lancer,
        # mais on peut vérifier que le module s'importe correctement
        import eva.cli
        source = Path(eva.cli.__file__).read_text(encoding="utf-8")
        assert "--tui" in source

    def test_cli_imports_tui_conditionally(self):
        import eva.cli
        source = Path(eva.cli.__file__).read_text(encoding="utf-8")
        assert "tui_main" in source
        assert "repl_main" in source

    def test_tui_docstring_updated(self):
        import eva.cli
        assert eva.cli.__doc__ is not None
        assert "--tui" in eva.cli.__doc__


# ---------------------------------------------------------------------------
# 5. Tests de la logique de dispatch (sans UI)
# ---------------------------------------------------------------------------


@requires_textual
class TestDispatchLogic:
    """Tests de la logique de dispatch commande vs message, sans UI."""

    def test_handle_input_command_prefix(self):
        """Vérifier que /commande est détecté comme commande."""
        app = EvaTuiApp()
        # Patch _run_command et _run_message pour vérifier le dispatch
        called_command = []
        called_message = []

        app._run_command = lambda raw: called_command.append(raw)
        app._run_message = lambda text: called_message.append(text)

        app._handle_input("/help")
        assert len(called_command) == 1
        assert len(called_message) == 0
        assert called_command[0] == "/help"

    def test_handle_input_message_no_prefix(self):
        """Vérifier qu'un message sans / est envoyé au LLM."""
        app = EvaTuiApp()
        called_command = []
        called_message = []

        app._run_command = lambda raw: called_command.append(raw)
        app._run_message = lambda text: called_message.append(text)

        app._handle_input("Bonjour EVA")
        assert len(called_command) == 0
        assert len(called_message) == 1
        assert called_message[0] == "Bonjour EVA"

    def test_run_command_quit_should_exit(self):
        """Vérifier que /quit appelle self.exit()."""
        app = EvaTuiApp()
        from eva.ui.command_registry import CommandContext
        app._ctx = CommandContext(
            engine=None,
            config=None,
            event_bus=None,
            registry=app._cmd_registry,
        )
        # Mocker chat pour éviter les erreurs de widgets non montés
        app._chat = MagicMock()
        app._sidebar = MagicMock()

        exit_called = []
        app.exit = lambda: exit_called.append(True)

        app._run_command("/quit")
        assert len(exit_called) == 1

    def test_run_command_unknown_shows_error(self):
        """Vérifier qu'une commande inconnue produit un message d'erreur."""
        app = EvaTuiApp()
        from eva.ui.command_registry import CommandContext
        app._ctx = CommandContext(
            engine=None,
            config=None,
            event_bus=None,
            registry=app._cmd_registry,
        )
        messages = []
        chat_mock = MagicMock()
        chat_mock.add_message = lambda sender, text, style: messages.append(text)
        app._chat = chat_mock
        app._sidebar = MagicMock()

        app._run_command("/unknowncommand")
        assert len(messages) == 1
        assert "inconnue" in messages[0] or "Commande" in messages[0]

    def test_run_command_clear_ansi_stripped(self):
        """/clear ne doit pas afficher les séquences ANSI dans le TUI."""
        app = EvaTuiApp()
        from eva.ui.command_registry import CommandContext
        app._ctx = CommandContext(
            engine=None,
            config=None,
            event_bus=None,
            registry=app._cmd_registry,
        )
        messages = []
        chat_mock = MagicMock()
        chat_mock.add_message = lambda sender, text, style: messages.append(text)
        app._chat = chat_mock
        app._sidebar = MagicMock()

        app._run_command("/clear")
        # Aucun message ne doit contenir les escape ANSI
        for msg in messages:
            assert "\033[2J" not in msg


# ---------------------------------------------------------------------------
# 6. Tests EvaInput autocomplete (sans UI)
# ---------------------------------------------------------------------------


@requires_textual
class TestEvaInput:
    """Tests de EvaInput."""

    def test_eva_input_instanciable(self):
        registry = MagicMock()
        inp = EvaInput(registry_ref=registry)
        assert inp is not None

    def test_eva_input_no_registry(self):
        inp = EvaInput(registry_ref=None)
        assert inp._registry_ref is None


# ---------------------------------------------------------------------------
# 7. Tests smoke Textual (requiert textual installé + pilot)
# ---------------------------------------------------------------------------


@requires_textual
class TestEvaTuiSmoke:
    """Smoke tests Textual avec app.run_test() et pilot."""

    @pytest.mark.asyncio
    async def test_app_compose_no_crash(self):
        """L'application se compose sans erreur (engine mocké)."""
        app = EvaTuiApp()
        # Mocker _init_eva pour éviter l'initialisation réelle
        app._init_eva = lambda: None

        async with app.run_test(size=(120, 40)) as pilot:
            assert pilot.app is not None

    @pytest.mark.asyncio
    async def test_chat_widget_present(self):
        """ChatView est présent dans le layout."""
        app = EvaTuiApp()
        app._init_eva = lambda: None

        async with app.run_test(size=(120, 40)) as pilot:
            chat = pilot.app.query_one(ChatView)
            assert chat is not None

    @pytest.mark.asyncio
    async def test_sidebar_widget_present(self):
        """StatusSidebar est présent dans le layout."""
        app = EvaTuiApp()
        app._init_eva = lambda: None

        async with app.run_test(size=(120, 40)) as pilot:
            sidebar = pilot.app.query_one(StatusSidebar)
            assert sidebar is not None

    @pytest.mark.asyncio
    async def test_input_widget_present(self):
        """EvaInput est présent dans le layout."""
        app = EvaTuiApp()
        app._init_eva = lambda: None

        async with app.run_test(size=(120, 40)) as pilot:
            inp = pilot.app.query_one(EvaInput)
            assert inp is not None

    @pytest.mark.asyncio
    async def test_welcome_message_displayed(self):
        """Le message de bienvenue EVA est affiché au démarrage."""
        app = EvaTuiApp()
        app._init_eva = lambda: None

        async with app.run_test(size=(120, 40)) as pilot:
            messages = pilot.app.query(MessageWidget)
            assert len(messages) > 0

    @pytest.mark.asyncio
    async def test_command_help_in_chat(self):
        """Appeler _run_command('/help') ajoute un message d'aide dans le chat."""
        app = EvaTuiApp()
        app._init_eva = lambda: None

        async with app.run_test(size=(120, 40)) as pilot:
            from eva.ui.command_registry import CommandContext
            if pilot.app._ctx is None:
                pilot.app._ctx = CommandContext(
                    engine=None,
                    config=None,
                    event_bus=None,
                    registry=pilot.app._cmd_registry,
                )

            initial_count = len(list(pilot.app.query(MessageWidget)))
            pilot.app._run_command("/help")
            await pilot.pause()

            messages = list(pilot.app.query(MessageWidget))
            assert len(messages) > initial_count

    @pytest.mark.asyncio
    async def test_quit_command_exits_app(self):
        """Taper /quit ferme l'application."""
        app = EvaTuiApp()
        app._init_eva = lambda: None
        exit_called = []
        original_exit = app.exit
        app.exit = lambda *a, **kw: exit_called.append(True)

        async with app.run_test(size=(120, 40)) as pilot:
            from eva.ui.command_registry import CommandContext
            if pilot.app._ctx is None:
                pilot.app._ctx = CommandContext(
                    engine=None,
                    config=None,
                    event_bus=None,
                    registry=pilot.app._cmd_registry,
                )
            pilot.app._run_command("/quit")

        assert len(exit_called) == 1

    @pytest.mark.asyncio
    async def test_message_adds_to_chat(self):
        """Envoyer un message (non-commande) ajoute des widgets au chat."""
        app = EvaTuiApp()
        app._init_eva = lambda: None

        async with app.run_test(size=(120, 40)) as pilot:
            # Mocker _run_message pour éviter l'appel LLM
            messages_sent = []
            pilot.app._run_message = lambda text: messages_sent.append(text)

            inp = pilot.app.query_one(EvaInput)
            await pilot.click(EvaInput)
            await pilot.press(*list("Bonjour"))
            await pilot.press("enter")
            await pilot.pause()

            assert len(messages_sent) == 1
            assert messages_sent[0] == "Bonjour"

    @pytest.mark.asyncio
    async def test_empty_input_ignored(self):
        """Soumettre un input vide ne produit pas de message."""
        app = EvaTuiApp()
        app._init_eva = lambda: None

        async with app.run_test(size=(120, 40)) as pilot:
            initial_count = len(list(pilot.app.query(MessageWidget)))
            await pilot.click(EvaInput)
            await pilot.press("enter")
            await pilot.pause()

            final_count = len(list(pilot.app.query(MessageWidget)))
            assert final_count == initial_count

    @pytest.mark.asyncio
    async def test_action_clear_chat(self):
        """Ctrl+L efface les messages du chat."""
        app = EvaTuiApp()
        app._init_eva = lambda: None

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("ctrl+l")
            await pilot.pause()

            messages = list(pilot.app.query(MessageWidget))
            # Après clear, 1 message de bienvenue post-clear
            assert len(messages) <= 1


# ---------------------------------------------------------------------------
# 8. Tests du module __init__.py TUI (sans UI)
# ---------------------------------------------------------------------------


class TestTuiInit:
    """Tests du module eva.ui.tui."""

    def test_tui_module_importable(self):
        if not TEXTUAL_AVAILABLE:
            pytest.skip("textual non installé")
        import eva.ui.tui
        assert eva.ui.tui is not None

    def test_tui_exports_app(self):
        if not TEXTUAL_AVAILABLE:
            pytest.skip("textual non installé")
        from eva.ui.tui import EvaTuiApp, main
        assert EvaTuiApp is not None
        assert main is not None
