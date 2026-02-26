"""
Command Registry — Contrat central des commandes EVA.

Ce module définit le contrat partagé par :
- R-033 : CLI avancé (readline, autocomplete)
- R-030 : Terminal UI (Textual)
- R-031 : API REST (FastAPI)

Principe : Zéro I/O dans les handlers.
Les handlers retournent CommandResult — l'UI affiche.

Standards :
- Python 3.9 strict
- PEP8 strict
- Dataclasses immutables
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Types publics du contrat
# ---------------------------------------------------------------------------


@dataclass
class CommandContext:
    """
    Contexte d'exécution passé à chaque handler de commande.

    Contient les références aux composants EVA dont le handler
    peut avoir besoin. Les handlers ne doivent PAS muter le contexte.

    Attributes:
        engine:    EVAEngine (accès process(), status(), is_running)
        config:    ConfigManager (accès get(), get_path())
        event_bus: EventBus (accès emit())
        registry:  CommandRegistry (pour aide dynamique)
    """

    engine: Optional[Any] = None
    config: Optional[Any] = None
    event_bus: Optional[Any] = None
    registry: Optional[Any] = None  # CommandRegistry


@dataclass
class CommandResult:
    """
    Résultat d'une commande. Zéro I/O — l'UI affiche output.

    Contract : le handler ne fait jamais de print/input.
    Il retourne CommandResult et l'UI est responsable de l'affichage.

    Attributes:
        success:       True si la commande a réussi
        output:        Texte à afficher à l'utilisateur (peut être vide)
        event:         Nom de l'événement EventBus à émettre (optionnel)
        event_payload: Payload de l'événement (optionnel)
        should_quit:   True si le REPL doit se terminer
    """

    success: bool
    output: str
    event: Optional[str] = None
    event_payload: Optional[Dict[str, Any]] = None
    should_quit: bool = False


@dataclass
class Command:
    """
    Définition d'une commande EVA.

    Contrat du handler :
        handler(args: str, ctx: CommandContext) -> CommandResult
        - args : tout ce qui suit le nom de la commande (peut être vide)
        - ctx  : contexte d'exécution (engine, config, event_bus, registry)
        - Retourne CommandResult — Zéro I/O dans le handler

    Attributes:
        name:    Nom principal (sans slash, ex: "help")
        help:    Description courte affichée dans /help
        handler: Callable[[str, CommandContext], CommandResult]
        aliases: Noms alternatifs (ex: ["exit", "q"] pour "quit")
    """

    name: str
    help: str
    handler: Callable[[str, "CommandContext"], "CommandResult"]
    aliases: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DuplicateCommandError(Exception):
    """Levée lors d'un enregistrement en doublon (nom ou alias)."""


class UnknownCommandError(Exception):
    """Levée quand une commande demandée est inconnue."""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class CommandRegistry:
    """
    Registry central des commandes EVA.

    Source de vérité unique pour CLI, Terminal UI et API REST.
    Gère l'enregistrement, la résolution d'alias, l'exécution
    et l'autocomplétion des commandes.

    Usage:
        registry = CommandRegistry()
        registry.register(Command("help", "Affiche l'aide", help_handler))
        result = registry.execute("/help", ctx)
        print(result.output)
    """

    def __init__(self) -> None:
        self._commands: Dict[str, Command] = {}
        self._aliases: Dict[str, str] = {}  # alias → nom canonique

    # ------------------------------------------------------------------
    # Enregistrement
    # ------------------------------------------------------------------

    def register(self, command: Command) -> None:
        """
        Enregistre une commande dans le registry.

        Args:
            command: Commande à enregistrer

        Raises:
            DuplicateCommandError: Si le nom ou un alias est déjà utilisé
        """
        self._check_not_taken(command.name)
        for alias in command.aliases:
            self._check_not_taken(alias)

        self._commands[command.name] = command
        for alias in command.aliases:
            self._aliases[alias] = command.name

    def _check_not_taken(self, name: str) -> None:
        if name in self._commands or name in self._aliases:
            raise DuplicateCommandError(
                f"'{name}' est déjà enregistré dans le registry"
            )

    # ------------------------------------------------------------------
    # Résolution
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Command]:
        """
        Récupère une commande par nom ou alias (insensible à la casse).

        Args:
            name: Nom ou alias de la commande (sans slash)

        Returns:
            Command si trouvée, None sinon
        """
        key = name.lower()

        if key in self._commands:
            return self._commands[key]

        canonical = self._aliases.get(key)
        if canonical:
            return self._commands.get(canonical)

        return None

    # ------------------------------------------------------------------
    # Exécution
    # ------------------------------------------------------------------

    def execute(self, raw_input: str, ctx: CommandContext) -> CommandResult:
        """
        Parse et exécute une commande depuis l'input brut.

        Le slash initial est optionnel ("/help" et "help" sont équivalents).
        Les arguments sont tout ce qui suit le premier token.

        Args:
            raw_input: Input utilisateur (ex: "/config get llm.timeout")
            ctx:       Contexte d'exécution (engine, config, event_bus, registry)

        Returns:
            CommandResult — l'appelant est responsable de l'affichage
        """
        text = raw_input.lstrip("/").strip()

        if not text:
            return CommandResult(
                success=False,
                output="Commande vide. Tapez /help pour l'aide.",
            )

        parts = text.split(maxsplit=1)
        name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        command = self.get(name)
        if command is None:
            return CommandResult(
                success=False,
                output=(
                    f"Commande inconnue : /{name}\n"
                    "Tapez /help pour voir les commandes disponibles."
                ),
            )

        try:
            return command.handler(args, ctx)
        except Exception as exc:
            return CommandResult(
                success=False,
                output=f"Erreur lors de l'exécution de /{name} : {exc}",
            )

    # ------------------------------------------------------------------
    # Autocomplétion
    # ------------------------------------------------------------------

    def get_completions(self, prefix: str) -> List[str]:
        """
        Retourne les commandes correspondant au préfixe donné.

        Les noms et alias sont inclus. Le résultat est trié.

        Args:
            prefix: Préfixe (ex: "/h" → ["/help"], "c" → ["/clear", "/config"])

        Returns:
            Liste triée de commandes avec slash (ex: ["/clear", "/config"])
        """
        clean = prefix.lstrip("/").lower()

        seen: set = set()
        matches: List[str] = []

        for name in self._commands:
            if name.startswith(clean) and name not in seen:
                matches.append(f"/{name}")
                seen.add(name)

        for alias in self._aliases:
            if alias.startswith(clean) and alias not in seen:
                matches.append(f"/{alias}")
                seen.add(alias)

        return sorted(matches)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_commands(self) -> List[Command]:
        """
        Retourne toutes les commandes enregistrées (sans doublons alias).

        Returns:
            Liste dans l'ordre d'enregistrement
        """
        return list(self._commands.values())

    def __len__(self) -> int:
        return len(self._commands)

    def __repr__(self) -> str:
        return (
            f"CommandRegistry("
            f"commands={len(self._commands)}, "
            f"aliases={len(self._aliases)})"
        )
