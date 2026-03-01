"""
CLI principal pour EVA

Usage:
    eva                     # Lance REPL interactif
    eva --tui               # Lance le Terminal UI (Textual)
    eva --api               # Lance l'API REST JSON (FastAPI — localhost:8000)
    eva --api --tls         # Lance l'API REST en HTTPS (cert auto-signé)
    eva --web               # Lance l'interface web (FastAPI + UI browser — localhost:8000)
    eva --web --tls         # Lance l'interface web en HTTPS
    eva --print-api-key     # Affiche (ou génère) la clé API EVA
    eva --version           # Affiche version
    eva --help              # Aide
"""

import sys
import argparse
import getpass
from pathlib import Path

from eva import __version__


def main():
    """Point d'entrée principal CLI."""
    parser = argparse.ArgumentParser(
        prog="eva",
        description="EVA - Assistant IA Personnel",
        epilog="Pour plus d'infos: https://github.com/siridyx/eva"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"EVA {__version__}"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Chemin vers config.yaml personnalisé"
    )

    parser.add_argument(
        "--api",
        action="store_true",
        help="Lance l'API REST JSON (FastAPI — http://localhost:8000)"
    )

    parser.add_argument(
        "--web",
        action="store_true",
        help="Lance l'interface web (FastAPI + UI browser — http://localhost:8000)"
    )

    parser.add_argument(
        "--tui",
        action="store_true",
        help="Lance le Terminal UI (Textual)"
    )

    parser.add_argument(
        "--tls",
        action="store_true",
        help="Active HTTPS avec certificat auto-signé (pour --api ou --web)"
    )

    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="Crée l'utilisateur admin initial (bootstrap Phase 6(D))"
    )

    parser.add_argument(
        "--print-api-key",
        action="store_true",
        help="Affiche (ou génère) la clé API EVA pour l'API REST"
    )

    args = parser.parse_args()

    if args.create_admin:
        return _bootstrap_admin()

    if args.print_api_key:
        from eva.api.security import ApiKeyManager
        from eva.core.config_manager import ConfigManager
        _cfg = ConfigManager()
        _km = ApiKeyManager(_cfg.get_path("secrets"))
        print(_km.load_or_generate())
        return 0

    if args.api:
        from eva.api.app import main as api_main
        return api_main(tls=args.tls)
    elif args.web:
        import eva.web.app  # enregistre GET / sur l'app FastAPI
        from eva.web.app import main as web_main
        return web_main(tls=args.tls)
    elif args.tui:
        from eva.ui.tui.app import main as tui_main
        return tui_main()
    else:
        from eva.repl import main as repl_main
        return repl_main()


def _bootstrap_admin() -> int:
    """Crée le premier utilisateur admin de façon interactive."""
    from eva.core.config_manager import ConfigManager
    from eva.api.users import UserStore, UserRole

    cfg = ConfigManager()
    store = UserStore(cfg.get_path("data_root"))

    if store.has_admin():
        print("Un administrateur existe déjà. Utilisez /auth/register pour créer d'autres comptes.")
        return 1

    print("=== Création du compte administrateur EVA ===")
    username = input("Nom d'utilisateur : ").strip()
    if not username:
        print("Erreur : le nom d'utilisateur ne peut pas être vide.")
        return 1

    password = getpass.getpass("Mot de passe (min 8 caractères) : ")
    password2 = getpass.getpass("Confirmer le mot de passe : ")

    if password != password2:
        print("Erreur : les mots de passe ne correspondent pas.")
        return 1

    try:
        user = store.create_user(username, password, UserRole.ADMIN)
        print(f"Admin '{user.username}' créé avec succès.")
        print("Vous pouvez maintenant vous connecter via POST /auth/login")
        return 0
    except ValueError as exc:
        print(f"Erreur : {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
