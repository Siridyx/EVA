## EVA — Architecture

Documentation de l'architecture globale du projet EVA.

- Version : 0.1.0-dev
- Dernière mise à jour : 2026-02-19
- Phase : P1 (Intelligence de base)

---

## 📐 Vision Architecturale

EVA est construit autour de 3 principes fondamentaux :

Modularité

- composants découplés
- testables
- remplaçables

Évolutivité

- P1 = conversation de base
- P2 = agents / tools / RAG
- P3 = UI avancée
- P4 = qualité & production

Observabilité

- EventBus (pub/sub)
- LoggingManager (fichiers data/logs/)
- status() partout (introspection)

---

## 🏗️ Architecture Globale (Phase 1)

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                       │
│                     (scripts/eva_cli.py)                    │
│                    REPL + Commands (/start)                 │
│                    - affichage user-facing                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ user input
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       EVAEngine                             │
│                  (eva/core/eva_engine.py)                   │
│              - lifecycle start/stop                         │
│              - process(message) -> ConversationEngine       │
│              - status() introspection                       │
│              - décisions user-facing (via UI)               │
└──────┬──────────────────┬────────────────────┬──────────────┘
       │                  │                    │ response ↑
       │                  │                    └──────────┘
       ▼                  ▼
┌─────────────┐    ┌─────────────┐             ┌──────────────┐
│ConfigManager│    │  EventBus   │             │ EvaComponent │
│             │    │ (pub/sub)   │             │    (base)    │
│• get()      │    │• on()       │             │              │
│• get_path() │    │• emit()     │             │• start()     │
│• get_secret │    │• off()      │             │• stop()      │
└─────┬───────┘    └──────┬──────┘             └──────┬───────┘
      │                   │                           │
      │                   │      (cross-cutting:      │
      │                   │      all components)      │
      │                   │                           │
      ▼                   ▼                           ▼
┌─────────────────────────────────────────────────────────────┐
│                        Core Services                        │
│  ┌─────────────────────┐          ┌──────────────────────┐  │
│  │    LoggingManager   │          │    VersionManager    │  │
│  │ - data/logs/        │          │- data/.version       │  │
│  │ - event log_written │          │- events migrate/check│  │
│  └─────────────────────┘          └──────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      ConversationEngine                     │
│                     (eva/conversation/)                     │
│                                                             │
│   - pipeline : Memory -> Prompt -> LLM -> Memory            │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐     │
│  │MemoryManager │   │ PromptManager│   │  LLMClient   │     │
│  │- JSON        │   │ - templates  │   │ - provider   │     │
│  │- context win │   │ - render vars│   │ - complete() │     │
│  └──────────────┘   └──────────────┘   └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                         Plugin System                       │
│                        (eva/plugins/)                       │
│                                                             │
│   ┌──────────────┐ ┌───────────────┐ ┌──────────────────┐   │
│   │  PluginBase  │ │Plugin Registry│ │   PluginLoader   │   │
│   │contrat plugin│ │  Registry     │ │Scan + Import safe│   │
│   └──────────────┘ └───────────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Persistence                            │
│                                                             │
│  data/                          plugins/                    │
│  ├── logs/                      ├── example_plugin.py       │
│  ├── memory/                    ├── weather_plugin.py       │
│  ├── cache/                     └── ...                     │
│  ├── prompts/                                               │
│  ├── dumps/                                                 │
│  └── .version                                               │
└─────────────────────────────────────────────────────────────┘
```

**Légende** :

- `→` : Flux de données principal
- `↑` : Retour de réponse
- EventBus : Cross-cutting (tous les composants)
- Core Services : LoggingManager + VersionManager

---

## 🔧 Composants Core

# ConfigManager

ConfigManager

- responsabilité
  - charger config.yaml (racine projet)
  - fournir get() avec notation pointée
  - fournir get_path() vers data/
  - fournir get_secret() depuis .env / env vars
- points clés
  - création auto des dossiers data/ manquants
  - aucun secret exposé dans repr

# EventBus

- responsabilité
  - communication découplée inter-composants
- design
  - synchrone en P0/P1 (interface stable pour async plus tard)
  - isolation des handlers (un handler en erreur ne casse pas les autres)
  - payload dict strict

# EvaComponent

- responsabilité
  - base universelle pour standardiser tous les composants EVA
- garanties
  - start/stop idempotents
  - erreurs observables via events
  - helpers : emit(), get_config(), get_path(), get_secret()

# LoggingManager

- responsabilité
  - logs techniques dans data/logs/
  - séparation des canaux (ex: user/system/error)
  - rotation journalière
  - event log_written pour observabilité
- règle importante (alignée “contrat”)
  - pas de “messages utilisateur” ici
  - UI affiche, Engine décide, Logging trace

# VersionManager

- responsabilité
  - semver + compat
  - fichier data/.version
  - migrations framework (prêt)

## Composants P1

# MemoryManager

- backend
  - JSON dans data/memory/
  - session unique (du jour)
  - écriture atomique (temp -> replace)
- comportement
  - add_message(role, content)
  - get_context(window=N)
  - max_messages (trim)
  - events : memory_session_created, memory_message_added, ...

# PromptManager

- backend
  - templates dans data/prompts/
  - placeholders style {{var}}
- comportement
  - auto-create prompts par défaut si manquants
  - render(vars) avec validation placeholders
- point important (post-incident)
  - prompts en UTF-8 propre
  - tests isolés via EVA_DATA_DIR/tmp_path

# LLMClient

- responsabilité
  - abstraction provider
  - complete(messages, profile, timeout, retries)
- note provider
  - l’architecture supporte plusieurs providers
  - le choix “Ollama/Groq/OpenAI” est une décision de config/implémentation, pas un blocage d’archi

# ConversationEngine

- pipeline
  - persist user -> context -> system prompt -> call llm -> persist assistant
- API
  - respond(user_input: str, overrides: Optional[dict] = None) -> str
- events (observabilité)
  - conversation_request_received
  - conversation_context_built
  - llm_request_started / llm_request_succeeded / llm_request_error
  - conversation_reply_ready

# Plugin system (P1)

- objectifs
  - scan dossier plugins/
  - import safe (try/except)
  - registry central
- limites P1
  - plugins simples (pas d’agent planning, pas de tool calling avancé)
  - agent/tool orchestration = P2

## Persistance

- tout runtime dans Eva/data/
  - logs/
  - memory/
  - cache/
  - prompts/
  - dumps/
  - .version
- plugins tiers dans Eva/plugins/
  - pas de persistance directe dans plugins/
  - si un plugin persiste, il passe par config.get_path()

## Tests

- stratégie
  - unit : composants isolés
  - smoke : intégration stack
- post-incident (tests lents)
  - EVA_DATA_DIR forcé vers tmp_path en tests
  - prompts/memory/logs isolés par test run
  - objectif : tests rapides + déterministes
- métriques (indicatif)
  - tests totaux : ~200+ (selon état exact du repo)
  - durée : ~10–12s (après isolation I/O)

## Limitations connues

- P1
  - session unique (multi-conv = P2)
  - pas de streaming
  - pas de tool calling
  - pas de RAG
- qualité
  - network guard global pytest : optionnel (peut aller en DEBT si non bloquant)
  - markers pytest unit/integration : optionnel

## 🌊 Flux de Données (Phase 1 — complet)

```
User Input (CLI)
    │
    ▼
EVAEngine.process(message)
    │
    ▼
ConversationEngine.respond(message)
    │
    ├─→ [1] Validation + normalisation
    │   emit: conversation_request_received
    │
    ├─→ [2] MemoryManager.add_message("user", message)
    │
    ├─→ [3] context = MemoryManager.get_context()
    │   emit: conversation_context_built
    │
    ├─→ [4] prompt = PromptManager.render("system", **defaults)
    │
    ├─→ [5] messages = [system] + context
    │
    ├─→ [6] response = LLMClient.complete(messages, profile)
    │   emit: llm_request_started
    │   emit: llm_request_succeeded | llm_request_error
    │
    ├─→ [7] MemoryManager.add_message("assistant", response)
    │   emit: conversation_reply_ready
    │
    └─→ return response
```
