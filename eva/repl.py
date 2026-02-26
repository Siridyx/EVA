"""
EVA REPL — Interface en ligne de commande (R-033 : CLI avancé)

Fonctionnalités Phase 3 :
- Historique des commandes (touches haut/bas via readline)
- Autocomplétion des commandes /... (touche Tab)
- Command Registry unifié (CLI, Textual, API REST partagent le même contrat)
- Zéro I/O dans les handlers : l'UI est seule responsable de l'affichage

Architecture :
- EVACLI est une fine couche I/O au-dessus du CommandRegistry
- Les handlers retournent CommandResult, le REPL affiche output
- readline activé si disponible (Linux/Mac) ou via pyreadline3 (Windows optionnel)

Standards :
- Python 3.9 strict
- PEP8 strict
- Pas de crash brutal (Ctrl+C / Ctrl+D safe)
"""

import sys
import signal
from typing import Any, Optional

from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.core.eva_engine import EVAEngine
from eva.ui.command_registry import CommandContext, CommandRegistry
from eva.ui.commands import make_default_registry


# ---------------------------------------------------------------------------
# Readline (optionnel — graceful fallback si absent)
# ---------------------------------------------------------------------------


def _try_import_readline() -> Optional[Any]:
    """
    Tente d'importer readline (Linux/Mac) ou pyreadline3 (Windows optionnel).

    Returns:
        Module readline si disponible, None sinon (mode dégradé)
    """
    try:
        import readline  # type: ignore[import]

        return readline
    except ImportError:
        try:
            import pyreadline3 as readline  # type: ignore[import]

            return readline
        except ImportError:
            return None


# ---------------------------------------------------------------------------
# REPL principal
# ---------------------------------------------------------------------------


class EVACLI:
    """
    Interface CLI pour EVA — Phase 3 (R-033).

    Couche I/O mince au-dessus du CommandRegistry.
    Tout le dispatch de commandes passe par registry.execute().
    """

    def __init__(self) -> None:
        self.config: Optional[ConfigManager] = None
        self.event_bus: Optional[EventBus] = None
        self.engine: Optional[EVAEngine] = None
        self.registry: Optional[CommandRegistry] = None
        self._ctx: Optional[CommandContext] = None
        self.running: bool = False

        # Readline (historique + autocomplete)
        self._readline = _try_import_readline()
        if self._readline:
            self._readline.set_history_length(100)

    # ------------------------------------------------------------------
    # Readline — autocomplétion
    # ------------------------------------------------------------------

    def _completer(self, text: str, state: int) -> Optional[str]:
        """Compléteur readline pour les commandes /..."""
        if not self.registry:
            return None
        if not text.startswith("/"):
            return None
        options = self.registry.get_completions(text)
        if state < len(options):
            return options[state]
        return None

    def _setup_completer(self) -> None:
        """Active l'autocomplétion readline si disponible."""
        if self._readline is None:
            return
        try:
            self._readline.set_completer(self._completer)
            self._readline.parse_and_bind("tab: complete")
        except Exception:
            pass  # readline partiel — pas bloquant

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        """
        Initialise tous les composants EVA.

        Returns:
            True si succès, False sinon
        """
        try:
            print("Initialisation d'EVA...")

            self.config = ConfigManager()
            print(f"   OK Configuration (v{self.config.version})")

            self.event_bus = EventBus()
            print("   OK Bus d'événements")

            from eva.memory.memory_manager import MemoryManager

            memory = MemoryManager(self.config, self.event_bus)
            memory.start()
            print("   OK Memory")

            from eva.prompt.prompt_manager import PromptManager

            prompt = PromptManager(self.config, self.event_bus)
            prompt.start()
            print("   OK Prompt manager")

            from eva.llm.providers.ollama_provider import OllamaProvider

            llm = OllamaProvider(self.config, self.event_bus)
            llm.start()
            print("   OK LLM (Ollama)")

            from eva.conversation.conversation_engine import ConversationEngine

            conv = ConversationEngine(
                self.config, self.event_bus, memory, prompt, llm
            )
            conv.start()
            print("   OK ConversationEngine")

            self.engine = EVAEngine(self.config, self.event_bus)
            self.engine.set_conversation_engine(conv)
            print("   OK Moteur EVA")

            # Command Registry (R-033)
            self.registry = make_default_registry()
            self._ctx = CommandContext(
                engine=self.engine,
                config=self.config,
                event_bus=self.event_bus,
                registry=self.registry,
            )
            print("   OK Command Registry")

            # Activer autocomplétion readline
            self._setup_completer()
            readline_status = "OK" if self._readline else "absent (mode dégradé)"
            print(f"   OK Readline : {readline_status}")

            print("EVA initialisé.\n")
            return True

        except Exception as exc:
            print(f"Erreur lors de l'initialisation : {exc}")
            import traceback

            traceback.print_exc()
            return False

    # ------------------------------------------------------------------
    # REPL principal
    # ------------------------------------------------------------------

    def repl(self) -> None:
        """Boucle REPL principale."""
        self.running = True

        version = getattr(self.config, "version", "?") if self.config else "?"
        print(f"EVA {version} — Tapez /help pour l'aide, /quit pour quitter\n")

        while self.running:
            try:
                user_input = input("EVA> ").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    self._dispatch_command(user_input)
                else:
                    self._dispatch_message(user_input)

            except KeyboardInterrupt:
                print()
                self._dispatch_command("/quit")
                break

            except EOFError:
                print()
                self._dispatch_command("/quit")
                break

            except Exception as exc:
                print(f"Erreur : {exc}")

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dispatch_command(self, raw: str) -> None:
        """Exécute une commande via le registry et affiche le résultat."""
        if self.registry is None or self._ctx is None:
            print("Registry non initialisé.")
            return

        result = self.registry.execute(raw, self._ctx)
        if result.output:
            print(result.output)

        # Émettre l'événement si demandé
        if result.event and self.event_bus:
            self.event_bus.emit(result.event, result.event_payload or {})

        # Signal de fin de REPL
        if result.should_quit:
            self._shutdown_engine()
            self.running = False

    def _dispatch_message(self, message: str) -> None:
        """Traite un message utilisateur et l'envoie au moteur."""
        if not self.engine:
            print("Moteur non initialisé.")
            return

        if not self.engine.is_running:
            print("Moteur non démarré. Utilisez /start d'abord.")
            return

        try:
            response = self.engine.process(message)
            print(f"EVA : {response}")
        except Exception as exc:
            print(f"Erreur traitement : {exc}")

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _shutdown_engine(self) -> None:
        """Arrête le moteur proprement si running."""
        if self.engine and self.engine.is_running:
            try:
                self.engine.stop()
            except Exception:
                pass

    def shutdown(self) -> None:
        """Shutdown complet — appelé à la fin du processus."""
        if self.engine:
            try:
                self.engine.shutdown()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------


def main() -> int:
    """
    Point d'entrée principal.

    Returns:
        Code de sortie (0 = succès, 1 = erreur)
    """
    try:
        version = ConfigManager().version
    except Exception:
        version = "?"

    print("=" * 50)
    print("  EVA — Assistant IA Personnel")
    print(f"  Version: {version} (Phase 3 — CLI avancé)")
    print("=" * 50)
    print()

    cli = EVACLI()

    # Signal handler (Ctrl+C graceful)
    def signal_handler(sig: Any, frame: Any) -> None:
        print("\nSignal d'interruption — arrêt propre...")
        cli.running = False

    signal.signal(signal.SIGINT, signal_handler)

    # Initialisation
    if not cli.initialize():
        print("Echec de l'initialisation. Abandon.")
        return 1

    # REPL
    try:
        cli.repl()
    except Exception as exc:
        print(f"Erreur fatale : {exc}")
        return 1
    finally:
        cli.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
