"""
Commandes par défaut EVA — Handlers zero I/O.

Toutes les fonctions cmd_* reçoivent (args: str, ctx: CommandContext)
et retournent CommandResult. Aucun print/input dans ces handlers.
L'UI (REPL, Textual, API REST) est seule responsable de l'affichage.

Standards :
- Python 3.9 strict
- PEP8 strict
- Zéro I/O dans les handlers
"""

from __future__ import annotations

import os
from typing import List

from eva.ui.command_registry import (
    Command,
    CommandContext,
    CommandRegistry,
    CommandResult,
)


# ---------------------------------------------------------------------------
# Handlers (zero I/O)
# ---------------------------------------------------------------------------


def cmd_help(args: str, ctx: CommandContext) -> CommandResult:
    """Affiche l'aide dynamiquement depuis le registry."""
    registry = ctx.registry
    if registry is not None:
        lines: List[str] = ["", "Commandes disponibles :"]
        for cmd in registry.list_commands():
            aliases_str = ""
            if cmd.aliases:
                aliases_str = "  (" + ", ".join(f"/{a}" for a in cmd.aliases) + ")"
            lines.append(f"  /{cmd.name:<12} {cmd.help}{aliases_str}")
        lines += [
            "",
            "Messages :",
            "  Tapez directement votre message (sans /) pour interagir avec EVA",
            "",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    # Fallback statique si registry absent
    return CommandResult(
        success=True,
        output=(
            "\nCommandes disponibles :\n"
            "  /help         Affiche cette aide\n"
            "  /status       Statut du système EVA\n"
            "  /start        Démarre le moteur EVA\n"
            "  /stop         Arrête le moteur EVA\n"
            "  /new          Nouvelle conversation\n"
            "  /config       Configuration\n"
            "  /clear        Efface l'écran\n"
            "  /quit         Quitter (/exit, /q)\n"
            "\nMessages :\n"
            "  Tapez directement votre message (sans /) pour interagir avec EVA\n"
        ),
    )


def cmd_status(args: str, ctx: CommandContext) -> CommandResult:
    """Retourne le statut du système EVA."""
    if ctx.engine is None:
        return CommandResult(success=False, output="Moteur non initialisé.")

    try:
        status = ctx.engine.status()
        running = status.get("running", False)
        state_str = "RUNNING" if running else "STOPPED"

        lines: List[str] = [
            "",
            f"Etat EVA : {state_str}",
            f"  Nom          : {status.get('name', 'N/A')}",
            f"  Pipeline     : {status.get('pipeline_mode', 'N/A')}",
            f"  Init         : {'OK' if status.get('pipeline_initialized') else 'NON'}",
        ]

        components = status.get("components", {})
        if components:
            lines.append("  Composants :")
            lines.append(
                f"    LLM          : {'OK' if components.get('llm') else 'N/A'}"
            )
            lines.append(
                f"    Memory       : {'OK' if components.get('memory') else 'N/A'}"
            )
            lines.append(
                f"    Conversation : {'OK' if components.get('conversation') else 'N/A'}"
            )

        lines.append("")
        return CommandResult(success=True, output="\n".join(lines))
    except Exception as exc:
        return CommandResult(success=False, output=f"Erreur statut : {exc}")


def cmd_start(args: str, ctx: CommandContext) -> CommandResult:
    """Démarre le moteur EVA."""
    if ctx.engine is None:
        return CommandResult(success=False, output="Moteur non initialisé.")

    if getattr(ctx.engine, "is_running", False):
        return CommandResult(success=False, output="Moteur déjà démarré.")

    try:
        ctx.engine.start()
        return CommandResult(
            success=True,
            output="Moteur EVA démarré.",
            event="engine_started",
            event_payload={"source": "cli"},
        )
    except Exception as exc:
        return CommandResult(success=False, output=f"Erreur au démarrage : {exc}")


def cmd_stop(args: str, ctx: CommandContext) -> CommandResult:
    """Arrête le moteur EVA."""
    if ctx.engine is None:
        return CommandResult(success=False, output="Moteur non initialisé.")

    if not getattr(ctx.engine, "is_running", False):
        return CommandResult(success=False, output="Moteur déjà arrêté.")

    try:
        ctx.engine.stop()
        return CommandResult(
            success=True,
            output="Moteur EVA arrêté.",
            event="engine_stopped",
            event_payload={"source": "cli"},
        )
    except Exception as exc:
        return CommandResult(success=False, output=f"Erreur à l'arrêt : {exc}")


def cmd_new(args: str, ctx: CommandContext) -> CommandResult:
    """Démarre une nouvelle conversation."""
    return CommandResult(
        success=True,
        output=(
            "Nouvelle conversation.\n"
            "  Note : reset mémoire complet disponible en R-030 (Terminal UI)."
        ),
    )


def cmd_config(args: str, ctx: CommandContext) -> CommandResult:
    """Affiche ou lit la configuration (sans secrets)."""
    if ctx.config is None:
        return CommandResult(success=False, output="Configuration non disponible.")

    parts = args.strip().split(maxsplit=1)
    subcommand = parts[0].lower() if parts and parts[0] else ""
    key = parts[1] if len(parts) > 1 else ""

    # /config get KEY
    if subcommand == "get":
        if not key:
            return CommandResult(
                success=False,
                output="/config get KEY — KEY manquant (ex: /config get llm.timeout)",
            )
        try:
            value = ctx.config.get(key)
            if value is None:
                return CommandResult(
                    success=False, output=f"Clé introuvable : {key}"
                )
            return CommandResult(success=True, output=f"{key} = {value}")
        except Exception as exc:
            return CommandResult(
                success=False, output=f"Erreur lecture config : {exc}"
            )

    # /config (sans argument) → aperçu général
    try:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        api_status = f"configurée (...{api_key[-4:]})" if api_key else "absente"

        lines: List[str] = [
            "",
            "Configuration EVA :",
            f"  Version     : {getattr(ctx.config, 'version', 'N/A')}",
            f"  Environment : {getattr(ctx.config, 'environment', 'N/A')}",
            f"  API OpenAI  : {api_status}",
            "",
            "Usage : /config get KEY  (ex: /config get llm.timeout)",
            "",
        ]
        return CommandResult(success=True, output="\n".join(lines))
    except Exception as exc:
        return CommandResult(success=False, output=f"Erreur config : {exc}")


def cmd_clear(args: str, ctx: CommandContext) -> CommandResult:
    """Efface l'écran (ANSI escape)."""
    return CommandResult(
        success=True,
        output="\033[2J\033[H",
    )


def cmd_quit(args: str, ctx: CommandContext) -> CommandResult:
    """Quitte EVA proprement."""
    return CommandResult(
        success=True,
        output="\nAu revoir !\n",
        should_quit=True,
        event="cli_quit",
        event_payload={"source": "user"},
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def make_default_registry() -> CommandRegistry:
    """
    Construit le CommandRegistry avec toutes les commandes par défaut.

    Returns:
        CommandRegistry prêt à l'emploi
    """
    registry = CommandRegistry()

    registry.register(
        Command(
            name="help",
            help="Affiche l'aide",
            handler=cmd_help,
            aliases=["h", "?"],
        )
    )
    registry.register(
        Command(
            name="status",
            help="Statut du système EVA",
            handler=cmd_status,
            aliases=["stat"],
        )
    )
    registry.register(
        Command(
            name="start",
            help="Démarre le moteur EVA",
            handler=cmd_start,
        )
    )
    registry.register(
        Command(
            name="stop",
            help="Arrête le moteur EVA",
            handler=cmd_stop,
        )
    )
    registry.register(
        Command(
            name="new",
            help="Nouvelle conversation (reset mémoire)",
            handler=cmd_new,
        )
    )
    registry.register(
        Command(
            name="config",
            help="Configuration (get KEY | aperçu)",
            handler=cmd_config,
            aliases=["cfg"],
        )
    )
    registry.register(
        Command(
            name="clear",
            help="Efface l'écran",
            handler=cmd_clear,
            aliases=["cls"],
        )
    )
    registry.register(
        Command(
            name="quit",
            help="Quitter EVA",
            handler=cmd_quit,
            aliases=["exit", "q"],
        )
    )

    return registry
