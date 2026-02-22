"""
EVA CLI — Interface en ligne de commande

Point d'entrée principal pour lancer EVA en mode terminal.
Fournit une interface REPL (Read-Eval-Print Loop) basique
pour interagir avec le moteur EVA.

Usage:
    python scripts/eva_cli.py

Commandes:
    /start   - Démarre le moteur EVA
    /stop    - Arrête le moteur EVA
    /status  - Affiche l'état du moteur
    /help    - Affiche l'aide
    /quit    - Quitte l'application

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Gestion d'erreurs robuste
- Pas de crash brutal (Ctrl+C safe)
"""

import sys
import signal
from pathlib import Path
from typing import Optional

from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.core.eva_engine import EVAEngine


class EVACLI:
    """
    Interface CLI pour EVA.
    
    Gère l'initialisation, la boucle REPL et le shutdown propre.
    """
    
    def __init__(self) -> None:
        """Initialise le CLI (sans démarrer le moteur)."""
        self.config: Optional[ConfigManager] = None
        self.event_bus: Optional[EventBus] = None
        self.engine: Optional[EVAEngine] = None
        self.running: bool = False
    
    # --- Initialisation ---
    
    def initialize(self) -> bool:
        """
        Initialise les composants EVA.
        
        Returns:
            True si succès, False sinon
        """
        try:
            print("🔧 Initialisation d'EVA...")
            
            # ConfigManager
            self.config = ConfigManager()
            print(f"   ✓ Configuration chargée (v{self.config.version})")
            
            # EventBus
            self.event_bus = EventBus()
            print(f"   ✓ Bus d'événements initialisé")
            
            # Memory
            from eva.memory.memory_manager import MemoryManager
            memory = MemoryManager(self.config, self.event_bus)
            memory.start()
            print(f"   ✓ Memory activée")
            
            # Prompt
            from eva.prompt.prompt_manager import PromptManager
            prompt = PromptManager(self.config, self.event_bus)
            prompt.start()
            print(f"   ✓ Prompt manager activé")
            
            # LLM (Ollama par défaut)
            from eva.llm.providers.ollama_provider import OllamaProvider
            llm = OllamaProvider(self.config, self.event_bus)
            llm.start()
            print(f"   ✓ LLM (Ollama) connecté")
            
            # ConversationEngine
            from eva.conversation.conversation_engine import ConversationEngine
            conv = ConversationEngine(self.config, self.event_bus, memory, prompt, llm)
            conv.start()
            print(f"   ✓ ConversationEngine opérationnel")
            
            # EVAEngine
            self.engine = EVAEngine(self.config, self.event_bus)
            self.engine.set_conversation_engine(conv)
            print(f"   ✓ Moteur EVA prêt")
            
            print("✅ EVA initialisé avec succès\n")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation : {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # --- REPL ---
    
    def repl(self) -> None:
        """
        Boucle REPL principale.
        
        Lit les entrées utilisateur, traite les commandes
        et envoie les messages au moteur.
        """
        self.running = True
        
        print(f"🤖 EVA CLI - Phase 1 Complete")
        print("Tapez /help pour l'aide, /quit pour quitter\n")
        
        while self.running:
            try:
                # Prompt
                user_input = input("EVA> ").strip()
                
                if not user_input:
                    continue
                
                # Commandes système (commencent par /)
                if user_input.startswith("/"):
                    self.handle_command(user_input)
                else:
                    # Message utilisateur
                    self.handle_message(user_input)
                    
            except KeyboardInterrupt:
                # Ctrl+C → quit gracefully
                print("\n\n👋 Interruption détectée")
                self.handle_command("/quit")
                break
                
            except EOFError:
                # Ctrl+D / EOF
                print("\n")
                self.handle_command("/quit")
                break
                
            except Exception as e:
                print(f"❌ Erreur : {e}")
    
    def handle_command(self, command: str) -> None:
        """
        raite une commande système.
    
        Args:
            command: Commande (ex: "/start", "/quit")
        """
        cmd = command.lower().strip()
        
        if cmd == "/start":
            self.cmd_start()
        elif cmd == "/stop":
            self.cmd_stop()
        elif cmd == "/status":
            self.cmd_status()
        elif cmd == "/new":
            self.cmd_new()
        elif cmd == "/prompt":
            self.cmd_prompt()
        elif cmd == "/config":
            self.cmd_config()
        elif cmd == "/help":
            self.cmd_help()
        elif cmd in ["/quit", "/exit", "/q"]:
            self.cmd_quit()
        else:
            print(f"❌ Commande inconnue : {command}")
            print("   Tapez /help pour voir les commandes disponibles")
    
    def handle_message(self, message: str) -> None:
        """
        Traite un message utilisateur.
        
        Args:
            message: Texte de l'utilisateur
        """
        if not self.engine:
            print("❌ Moteur non initialisé")
            return
        
        if not self.engine.is_running:
            print("❌ Moteur non démarré. Utilisez /start d'abord.")
            return
        
        try:
            # Envoyer au moteur
            response = self.engine.process(message)
            print(f"🤖 {response}")
            
        except Exception as e:
            print(f"❌ Erreur lors du traitement : {e}")
    
    # --- Commandes ---
    
    def cmd_start(self) -> None:
        """Démarre le moteur EVA."""
        if not self.engine:
            print("❌ Moteur non initialisé")
            return
        
        if self.engine.is_running:
            print("⚠️  Moteur déjà démarré")
            return
        
        try:
            self.engine.start()
            print("✅ Moteur EVA démarré")
        except Exception as e:
            print(f"❌ Erreur au démarrage : {e}")
    
    def cmd_stop(self) -> None:
        """Arrête le moteur EVA."""
        if not self.engine:
            print("❌ Moteur non initialisé")
            return
        
        if not self.engine.is_running:
            print("⚠️  Moteur déjà arrêté")
            return
        
        try:
            self.engine.stop()
            print("✅ Moteur EVA arrêté")
        except Exception as e:
            print(f"❌ Erreur à l'arrêt : {e}")
    
    def cmd_status(self) -> None:
        """Affiche l'état du moteur."""
        if not self.engine:
            print("❌ Moteur non initialisé")
            return
        
        status = self.engine.status()
        
        print("\n📊 État d'EVA:")
        print(f"   Nom          : {status['name']}")
        print(f"   État         : {'🟢 Running' if status['running'] else '🔴 Stopped'}")
        print(f"   Mode pipeline: {status['pipeline_mode']}")
        print(f"   Pipeline init: {'✅' if status['pipeline_initialized'] else '❌'}")
        print(f"   Composants   :")
        print(f"      LLM       : {'✅' if status['components']['llm'] else '❌ (P1)'}")
        print(f"      Memory    : {'✅' if status['components']['memory'] else '❌ (P1)'}")
        print(f"      Conversation: {'✅' if status['components']['conversation'] else '❌ (P1)'}")
        print()

    def cmd_new(self) -> None:
        """Démarre une nouvelle conversation (reset memory)."""
        if not self.engine:
            print("❌ Moteur non initialisé")
            return
        
        # TODO: Implémenter reset conversation quand ConversationEngine disponible
        print("💡 Nouvelle conversation")
        print("   Note: Implémentation complète disponible en Phase 2")
        print("   Pour l'instant, redémarrez EVA pour reset la mémoire")

    def cmd_prompt(self) -> None:
        """Affiche le prompt système actuel."""
        if not self.config:
            print("❌ Configuration non chargée")
            return
        
        try:
            # Récupérer config prompt
            prompt_defaults = self.config.get("prompt.defaults", {})
            
            print("\n📝 Configuration Prompt:")
            print(f"   Tone      : {prompt_defaults.get('tone', 'N/A')}")
            print(f"   Expertise : {prompt_defaults.get('expertise', 'N/A')}")
            
            # Afficher chemin prompts
            prompts_path = self.config.get_path("prompts")
            print(f"\n📂 Templates : {prompts_path}")
            
            # Lister fichiers prompts disponibles
            from pathlib import Path
            if Path(prompts_path).exists():
                prompts = list(Path(prompts_path).glob("*.txt"))
                if prompts:
                    print("   Disponibles:")
                    for p in prompts:
                        print(f"      - {p.name}")
                else:
                    print("   Aucun template trouvé")
            print()
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture prompt : {e}")

    def cmd_config(self) -> None:
        """Affiche la configuration active (sans secrets)."""
        if not self.config:
            print("❌ Configuration non chargée")
            return
        
        print("\n⚙️  Configuration EVA:")
        print(f"   Version     : {self.config.version}")
        print(f"   Environment : {self.config.environment}")
        
        # LLM config (sans API key)
        try:
            llm_models = self.config.get("llm.models", {})
            llm_timeout = self.config.get("llm.timeout", "N/A")
            llm_retries = self.config.get("llm.max_retries", "N/A")
            
            print(f"\n🤖 LLM:")
            print(f"   Model dev    : {llm_models.get('dev', 'N/A')}")
            print(f"   Model default: {llm_models.get('default', 'N/A')}")
            print(f"   Timeout      : {llm_timeout}s")
            print(f"   Max retries  : {llm_retries}")
            
            # Vérifier API key présente (sans l'afficher)
            import os
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                print(f"   API Key      : ✅ Configurée (sk-...{api_key[-4:]})")
            else:
                print(f"   API Key      : ❌ Absente")
                print(f"   → Définir OPENAI_API_KEY dans .env")
            
        except Exception as e:
            print(f"   Erreur lecture config LLM : {e}")
        
        # Memory config
        try:
            memory_max = self.config.get("memory.max_messages", "N/A")
            memory_window = self.config.get("memory.context_window", "N/A")
            
            print(f"\n💾 Memory:")
            print(f"   Max messages  : {memory_max}")
            print(f"   Context window: {memory_window}")
            
        except Exception:
            pass
        
        # Paths
        print(f"\n📂 Paths:")
        print(f"   Data   : {self.config.get_path('logs').parent}")
        print(f"   Logs   : {self.config.get_path('logs')}")
        print(f"   Memory : {self.config.get_path('memory')}")
        print(f"   Prompts: {self.config.get_path('prompts')}")
        print()
    
    def cmd_help(self) -> None:
        """Affiche l'aide."""
        print("\n📖 Commandes disponibles:")
        print("   /start   - Démarre le moteur EVA")
        print("   /stop    - Arrête le moteur EVA")
        print("   /status  - Affiche l'état du moteur")
        print("   /new     - Nouvelle conversation (reset memory)")
        print("   /prompt  - Affiche la config prompt active")
        print("   /config  - Affiche la configuration (sans secrets)")
        print("   /help    - Affiche cette aide")
        print("   /quit    - Quitte l'application")
        print("\n💬 Messages:")
        print("   Tapez directement votre message (sans /) pour interagir avec EVA")
        print("   Note: Utilisez /start puis conversez avec EVA\n")
    
    def cmd_quit(self) -> None:
        """Quitte l'application proprement."""
        print("\n👋 Arrêt d'EVA...")
        
        # Arrêter le moteur si running
        if self.engine and self.engine.is_running:
            try:
                self.engine.stop()
                print("   ✓ Moteur arrêté")
            except Exception as e:
                print(f"   ⚠️  Erreur à l'arrêt : {e}")
        
        print("✅ Au revoir !\n")
        self.running = False
    
    # --- Shutdown ---
    
    def shutdown(self) -> None:
        """Shutdown complet (cleanup)."""
        if self.engine:
            try:
                self.engine.shutdown()
            except Exception:
                pass  # Ignore errors during shutdown


# --- Point d'entrée ---

def main() -> int:
    """
    Point d'entrée principal.
    
    Returns:
        Code de sortie (0 = succès)
    """
    # Banner
    version = ConfigManager().version
    print("=" * 50)
    print("  EVA — Assistant IA Personnel")
    print(f"  Version: {version} (Phase 1 ✅)")
    print("=" * 50)
    
    # CLI
    cli = EVACLI()
    
    # Signal handler (Ctrl+C graceful)
    def signal_handler(sig, frame):
        print("\n\n⚠️  Signal d'interruption reçu")
        cli.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialisation
    if not cli.initialize():
        print("\n❌ Échec de l'initialisation. Abandon.\n")
        return 1
    
    # REPL
    try:
        cli.repl()
    except Exception as e:
        print(f"\n❌ Erreur fatale : {e}")
        return 1
    finally:
        cli.shutdown()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())