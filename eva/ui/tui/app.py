"""
EVA Terminal UI — Application Textual (R-030).

Interface graphique en terminal construite sur le contrat R-033.
Layout split : chat 70% gauche / sidebar status 30% droite.

Fonctionnalités :
- Chat scrollable avec historique
- Sidebar statut (moteur, LLM, mémoire, tools)
- Tab autocomplétion des commandes /...
- Appels LLM non-bloquants (worker thread)
- Thème sombre cyan/bleu

Bindings :
- Ctrl+Q : Quitter
- F1     : Aide
- Ctrl+L : Effacer le chat

Standards :
- Python 3.9 strict
- PEP8 strict
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.widgets import Footer, Header, Input, Static

from eva import __version__
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.core.eva_engine import EVAEngine
from eva.ui.command_registry import CommandContext
from eva.ui.commands import make_default_registry


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


class MessageWidget(Static):
    """
    Affiche un message dans le chat.

    Gère le formatage et la couleur selon le type d'expéditeur.
    """

    def __init__(self, sender: str, text: str, style_class: str) -> None:
        prefix = f"[{sender}] " if sender else ""
        super().__init__(f"{prefix}{text}", classes=style_class)


class ChatView(Vertical):
    """
    Zone de chat scrollable.

    Affiche les messages dans l'ordre chronologique.
    Supporte le remplacement du message "thinking" par la réponse LLM.
    """

    DEFAULT_CSS = """
    ChatView {
        overflow-y: auto;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__(id="chat")
        self._thinking_widget: Optional[MessageWidget] = None

    def add_message(self, sender: str, text: str, style_class: str = "msg-sys") -> None:
        """
        Ajoute un message et scrolle vers le bas.

        Args:
            sender:      Expéditeur affiché (ex: "EVA", "Toi", "")
            text:        Contenu du message
            style_class: Classe CSS (msg-eva, msg-user, msg-sys, msg-err)
        """
        widget = MessageWidget(sender, text, style_class)

        if sender == "EVA" and text.startswith("···"):
            self._thinking_widget = widget

        self.mount(widget)
        self.scroll_end(animate=False)

    def replace_thinking(self, response: str) -> None:
        """
        Remplace le message "··· EVA réfléchit…" par la vraie réponse.

        Args:
            response: Réponse LLM finale
        """
        if self._thinking_widget is not None:
            self._thinking_widget.update(f"[EVA] {response}")
            self._thinking_widget.remove_class("msg-sys")
            self._thinking_widget.add_class("msg-eva")
            self._thinking_widget = None
            self.scroll_end(animate=False)
        else:
            self.add_message("EVA", response, "msg-eva")


class StatusSidebar(Static):
    """
    Sidebar affichant l'état du système EVA.

    Mise à jour via refresh_status() après chaque action.
    """

    def __init__(self) -> None:
        super().__init__(id="sidebar")

    def refresh_status(self, engine: Optional[EVAEngine] = None) -> None:
        """
        Met à jour l'affichage du statut.

        Args:
            engine: EVAEngine pour introspection, ou None si non disponible
        """
        if engine is None:
            self.update(self._render_no_engine())
            return

        try:
            status = engine.status()
            self.update(self._render_status(status))
        except Exception as exc:
            self.update(f"Erreur statut :\n{exc}")

    def _render_no_engine(self) -> str:
        return (
            "STATUT\n"
            "──────────────────\n"
            "Moteur   ○ STOPPED\n"
            "\n"
            "/help  commandes\n"
            "Tab    compléter\n"
        )

    def _render_status(self, status: dict) -> str:
        running = status.get("running", False)
        state_icon = "●" if running else "○"
        state_str = "RUNNING" if running else "STOPPED"

        components = status.get("components", {})
        llm_ok = components.get("llm", False)
        mem_ok = components.get("memory", False)
        conv_ok = components.get("conversation", False)

        llm_icon = "●" if llm_ok else "○"
        mem_icon = "●" if mem_ok else "○"
        conv_icon = "●" if conv_ok else "○"

        return (
            f"STATUT\n"
            f"──────────────────\n"
            f"Moteur   {state_icon} {state_str}\n"
            f"LLM      {llm_icon} {'OK' if llm_ok else 'N/A'}\n"
            f"Mémoire  {mem_icon} {'OK' if mem_ok else 'N/A'}\n"
            f"Conv.    {conv_icon} {'OK' if conv_ok else 'N/A'}\n"
            f"\n"
            f"/help  commandes\n"
            f"Tab    compléter\n"
        )


class EvaInput(Input):
    """
    Champ de saisie avec autocomplétion Tab pour les commandes /...

    Délègue la complétion au CommandRegistry.
    """

    def __init__(self, registry_ref: Optional[object] = None) -> None:
        super().__init__(placeholder="Tapez votre message ou /commande...", id="eva-input")
        self._registry_ref = registry_ref

    def on_key(self, event: Key) -> None:
        """Gère Tab pour l'autocomplétion des commandes."""
        if event.key != "tab":
            return

        if self._registry_ref is None:
            return

        text = self.value
        if not text.startswith("/"):
            return

        completions = self._registry_ref.get_completions(text)
        if len(completions) == 1:
            self.value = completions[0] + " "
            self.cursor_position = len(self.value)
            event.prevent_default()
        elif len(completions) > 1:
            # Plusieurs correspondances : ne pas compléter, laisser la touche
            event.prevent_default()


# ---------------------------------------------------------------------------
# Application principale
# ---------------------------------------------------------------------------


class EvaTuiApp(App):
    """
    Application Terminal UI d'EVA (R-030).

    Construit sur le contrat CommandRegistry (R-033).
    """

    TITLE = f"EVA v{__version__} — Assistant IA Personnel"
    CSS_PATH = Path(__file__).parent / "styles.tcss"

    BINDINGS = [
        Binding("ctrl+q", "quit_app", "Quitter", show=True),
        Binding("f1", "show_help", "Aide", show=True),
        Binding("ctrl+l", "clear_chat", "Effacer", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()

        # Composants EVA (initialisés dans on_mount)
        self.config: Optional[ConfigManager] = None
        self.event_bus: Optional[EventBus] = None
        self.engine: Optional[EVAEngine] = None
        self._cmd_registry = make_default_registry()
        self._ctx: Optional[CommandContext] = None

        # Widgets (référencés après compose)
        self._chat: Optional[ChatView] = None
        self._sidebar: Optional[StatusSidebar] = None
        self._input_widget: Optional[EvaInput] = None

    def compose(self) -> ComposeResult:
        """Construit le layout : Header / Split(Chat + Sidebar) / Input / Footer."""
        yield Header()
        with Horizontal(id="main-layout"):
            chat = ChatView()
            self._chat = chat
            yield chat

            sidebar = StatusSidebar()
            self._sidebar = sidebar
            yield sidebar

        input_widget = EvaInput(registry_ref=self._cmd_registry)
        self._input_widget = input_widget
        yield input_widget

        yield Footer()

    def on_mount(self) -> None:
        """Initialise EVA et affiche le message de bienvenue."""
        self._init_eva()

        if self._chat:
            self._chat.add_message(
                "EVA",
                f"Bonjour ! EVA v{__version__} prête. "
                "Tapez votre message ou /help pour les commandes.",
                "msg-eva",
            )

        if self._sidebar and self.engine:
            self._sidebar.refresh_status(self.engine)

        # Focus sur l'input
        if self._input_widget:
            self._input_widget.focus()

    def _init_eva(self) -> None:
        """
        Initialise tous les composants EVA.

        Erreurs non-bloquantes : le TUI reste utilisable même si LLM absent.
        """
        try:
            self.config = ConfigManager()
            self.event_bus = EventBus()

            from eva.memory.memory_manager import MemoryManager

            memory = MemoryManager(self.config, self.event_bus)
            memory.start()

            from eva.prompt.prompt_manager import PromptManager

            prompt = PromptManager(self.config, self.event_bus)
            prompt.start()

            from eva.llm.providers.ollama_provider import OllamaProvider

            llm = OllamaProvider(self.config, self.event_bus)
            llm.start()

            from eva.conversation.conversation_engine import ConversationEngine

            conv = ConversationEngine(
                self.config, self.event_bus, memory, prompt, llm
            )
            conv.start()

            self.engine = EVAEngine(self.config, self.event_bus)
            self.engine.set_conversation_engine(conv)

            # Mise à jour registry ref dans l'input
            if self._input_widget:
                self._input_widget._registry_ref = self._cmd_registry

            self._ctx = CommandContext(
                engine=self.engine,
                config=self.config,
                event_bus=self.event_bus,
                registry=self._cmd_registry,
            )

        except Exception as exc:
            if self._chat:
                self._chat.add_message(
                    "",
                    f"Avertissement : initialisation partielle — {exc}",
                    "msg-err",
                )
            # Contexte minimal sans engine
            self._ctx = CommandContext(
                engine=None,
                config=self.config,
                event_bus=self.event_bus,
                registry=self._cmd_registry,
            )

    # ------------------------------------------------------------------
    # Gestion de l'input
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Dispatch : commande /... ou message LLM."""
        text = event.value.strip()

        # Vider l'input
        if self._input_widget:
            self._input_widget.value = ""

        if not text:
            return

        self._handle_input(text)

    def _handle_input(self, text: str) -> None:
        """
        Dispatch l'input utilisateur.

        /commande → CommandRegistry
        message   → Worker LLM async
        """
        if text.startswith("/"):
            self._run_command(text)
        else:
            self._run_message(text)

    def _run_command(self, raw: str) -> None:
        """Exécute une commande via le registry et met à jour l'UI."""
        if self._ctx is None:
            return

        result = self._cmd_registry.execute(raw, self._ctx)

        if result.output and self._chat:
            # Masquer les escape ANSI clear-screen — pas pertinent en TUI
            clean_output = result.output.replace("\033[2J\033[H", "").strip()
            if clean_output:
                self._chat.add_message("", clean_output, "msg-sys")

        if result.event and self.event_bus:
            self.event_bus.emit(result.event, result.event_payload or {})

        if result.should_quit:
            self.exit()
            return

        # Rafraîchir la sidebar après chaque commande
        if self._sidebar:
            self._sidebar.refresh_status(self.engine)

    def _run_message(self, text: str) -> None:
        """Envoie un message au LLM via un worker thread."""
        if self._chat:
            self._chat.add_message("Toi", text, "msg-user")
            self._chat.add_message("EVA", "··· réfléchit…", "msg-sys")

        self.run_worker(self._llm_worker(text), exclusive=False)

    async def _llm_worker(self, text: str) -> None:
        """
        Worker async : appel LLM dans un thread séparé (non-bloquant).

        Args:
            text: Message utilisateur à traiter
        """
        if self.engine is None or not self.engine.is_running:
            self.call_from_thread(
                self._chat.replace_thinking if self._chat else lambda r: None,
                "Moteur non démarré. Utilisez /start d'abord.",
            )
            return

        try:
            response = await asyncio.to_thread(self.engine.process, text)
            if self._chat:
                self.call_from_thread(self._chat.replace_thinking, response)
        except Exception as exc:
            if self._chat:
                self.call_from_thread(
                    self._chat.replace_thinking,
                    f"Erreur : {exc}",
                )

    # ------------------------------------------------------------------
    # Actions (bindings)
    # ------------------------------------------------------------------

    def action_quit_app(self) -> None:
        """Ctrl+Q — Quitter proprement."""
        if self._ctx:
            self._cmd_registry.execute("/quit", self._ctx)
        self.exit()

    def action_show_help(self) -> None:
        """F1 — Affiche l'aide dans le chat."""
        if self._ctx and self._chat:
            result = self._cmd_registry.execute("/help", self._ctx)
            if result.output:
                self._chat.add_message("", result.output, "msg-sys")

    def action_clear_chat(self) -> None:
        """Ctrl+L — Efface tous les messages du chat."""
        if self._chat:
            for widget in list(self._chat.children):
                widget.remove()
            self._chat._thinking_widget = None
            self._chat.add_message(
                "EVA",
                "Chat effacé. Comment puis-je vous aider ?",
                "msg-eva",
            )


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------


def main() -> int:
    """
    Lance le Terminal UI EVA.

    Returns:
        Code de sortie (0 = normal, 1 = erreur)
    """
    try:
        app = EvaTuiApp()
        app.run()
        return 0
    except Exception as exc:
        print(f"Erreur TUI : {exc}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
