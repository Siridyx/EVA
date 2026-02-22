# CHANGELOG

Toutes les modifications notables du projet EVA sont documentées ici.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

---

## [Unreleased]

### Added

- **Provider Ollama (R-012b)** : Support LLM local gratuit
  - OllamaProvider pour conversations sans API key
  - Endpoint `http://localhost:11434/api/generate`
  - Conversion messages OpenAI → prompt Ollama
  - Modèles supportés : llama3, llama3.2, mistral, gemma, etc.
  - Configuration par défaut : `llama3.2:latest`

- **Packaging release-ready (R-017b)** :
  - Entry point CLI `eva` installable globalement
  - Build wheel distribuable (49 KB)
  - CLI polish avec 8 commandes (/start, /stop, /status, /new, /prompt, /config, /help, /quit)
  - config.yaml inclus dans package
  - Installation propre validée
  - Version 0.1.0-p1 (Phase 1 MVP complete)

- **Plugin System (R-015)** :
  - PluginBase abstract class (inherits EvaComponent)
  - PluginRegistry lifecycle + tools + services
  - PluginLoader auto-discovery and loading
  - Auto-discovery (2 patterns: _\_plugin.py, _/plugin.py)
  - Convention get_plugin(config, event_bus) → PluginBase
  - Complete error isolation (plugin crash ≠ EVA crash)
  - Observability events (11 different events)
  - Example plugin functional (tool "greet")
  - API: register_tool(), register_service(), list_plugins()
  - Safe import via importlib.util (no sys.path modification)
  - 32 tests (31 unit + 1 smoke)

- **ConversationEngine (R-014)** :
  - Pipeline complet Memory → Prompt → LLM
  - Gestion mémoire conversationnelle
  - Rendu prompt avec variables
  - Intégration LLM (OpenAI/Ollama)
  - Events observabilité (5 events)
  - 48 tests unitaires

- **PromptManager (R-013)** :
  - Templates .txt avec variables {{var}}
  - Auto-création prompts par défaut
  - Cache avec reload optionnel
  - Validation stricte post-render
  - 14 tests unitaires

- **LLMClient + OpenAI Provider (R-012)** :
  - Interface abstraite pour providers LLM
  - OpenAI provider avec retry logic
  - Gestion timeout et backoff exponentiel
  - Transport injectable (mockable)
  - Profils dev/default
  - 10 tests unitaires

- **MemoryManager (R-011)** :
  - Mémoire conversationnelle JSON
  - Session unique (fichier du jour)
  - Context window configurable (10 messages)
  - Écriture atomique (temp → rename)
  - Schema versioning
  - 14 tests unitaires

### Changed

- **Default provider** : Ollama (au lieu de OpenAI)
  - EVA fonctionne maintenant sans API key par défaut
  - OpenAI reste disponible (switch via config)

- **EVA REPL initialization** : Configure automatiquement ConversationEngine complet
  - Memory + Prompt + LLM + ConversationEngine + EVAEngine
  - Démarrage en une commande (`eva`)

- **EVAEngine.process()** : Appelle ConversationEngine.respond() si configuré, sinon fallback explicite (R-014)

- **ConfigManager** : Support `EVA_DATA_DIR` env var pour isolation tests (R-014)

- **Tests** : Isolation tmp_path via EVA_DATA_DIR (29min → 11s, gain 162x) (R-014)

- **Tests hardening** : Isolation I/O complète + test mode (R-018)
  - tmp_path global via fixture autouse
  - EVA_TEST_MODE=1 pour tous les tests
  - Timeouts courts (0.5s) et retries=0 en mode test
  - 216 tests passent en 10.35s

### Fixed

- **Tests isolation** : Résolution incidents I/O (29min → 10s, gain 162x)
  - tmp_path global via fixture autouse
  - EVA_TEST_MODE pour timeouts courts
  - Pas d'écriture dans data/ réel durant tests

- **MemoryManager** : Fix mkdir parent directory avant mkstemp (R-018)

---

## [0.1.0-p1] - 2026-02-21

### Summary

**Phase 1 + 1.1 Complete** : EVA converse naturellement avec Ollama local !

**Métriques** :

- 216 tests en 10.35s
- Coverage ~95%
- Wheel 49 KB
- 0 dette P0/P1

**Capacités** :

- ✅ Conversation multi-tours avec mémoire
- ✅ LLM local gratuit (Ollama)
- ✅ Plugins extensibles
- ✅ CLI professionnel
- ✅ Packaging pip

---

## [0.1.0-dev] - 2026-02-19

### Added - Phase 0 (Fondations)

- **ConfigManager (R-002a)** :
  - Configuration YAML centralisée
  - Support dotenv (.env)
  - Secrets management (python-dotenv)
  - Notation pointée (ex: llm.models.dev)
  - Paths helpers (get_path, get_secret)

- **EventBus (R-003)** :
  - Communication découplée (pub/sub)
  - Synchrone P0 (async P1+)
  - Isolation erreurs handlers
  - API: on(), emit(), off()

- **LoggingManager (R-004)** :
  - Logs structurés (data/logs/)
  - Rotation automatique (taille + backup)
  - Émission events (log_written)
  - Niveaux configurables

- **EvaComponent (R-005)** :
  - Classe de base universelle
  - Lifecycle : start(), stop(), shutdown()
  - Injection explicite (config + event_bus)
  - Idempotence garantie
  - Utilitaires : emit(), get_config(), get_path()

- **EVAEngine (R-006)** :
  - Orchestrateur central
  - Pipeline modes (sequential P0, parallel P1+)
  - API : process(), status(), introspection
  - Integration ConversationEngine (P1)

- **VersionManager (R-007)** :
  - Versioning data/ (data/.version)
  - Migration schema future
  - Détection version mismatch

- **Packaging (R-002b)** :
  - pyproject.toml (PEP 517/518)
  - Dependencies core + dev
  - pip install -e . support
  - Black + Flake8 + MyPy + Pytest

### Technical

- **Tests** : 96 tests P0 passent en 2.5s
- **Coverage** : ~95% sur core
- **Python** : 3.9 strict
- **Standards** : PEP8, type hints, docstrings

---

**Convention versioning** : [MAJOR.MINOR.PATCH]-[PHASE]

- 0.1.0-dev = Phase 0
- 0.1.0-p1 = Phase 1 complete
- 0.2.0 = Phase 2
