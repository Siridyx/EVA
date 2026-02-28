# EVA — Architecture

Documentation de l'architecture globale du projet EVA.

- Version : 0.3.0
- Dernière mise à jour : 2026-02-28
- Phase : P3 ✅ COMPLÈTE (R-033 ✅ — R-030 ✅ — R-031 ✅ — R-032 ✅) | P4 en cours

---

## 📐 Vision Architecturale

EVA est construit autour de 3 principes fondamentaux :

**Modularité**
- Composants découplés, testables, remplaçables
- Chaque module hérite de `EvaComponent`

**Évolutivité**
- P0 = fondations (Config, EventBus, Engine)
- P1 = conversation (LLM, Prompts, Memory, Plugins)
- P2 = intelligence (Tool Calling, Agent ReAct, RAG)
- P3 = interface (CLI avancé, Terminal UI, API REST)
- P4 = qualité & production (CI/CD, Audit, Perf)

**Observabilité**
- `EventBus` (pub/sub) : communication inter-composants
- `LoggingManager` : fichiers dans `data/logs/`
- `status()` sur chaque composant (introspection)

---

## 🏗️ Architecture Globale

```
┌─────────────────────────────────────────────────────────────┐
│                     Interface Utilisateur                   │
│                   eva/cli.py → eva/repl.py                  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              CommandRegistry (R-033)                  │  │
│  │  Command(name, handler(args, ctx) → CommandResult)    │  │
│  │  Partagé : CLI · Terminal UI (R-030) · API (R-031)   │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ input utilisateur
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                        EVAEngine                            │
│                  (eva/core/eva_engine.py)                   │
│              - lifecycle start/stop                         │
│              - process(message) → ConversationEngine        │
│              - status() introspection                       │
└──────┬──────────────────┬────────────────────┬──────────────┘
       │                  │                    │
       ▼                  ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌──────────────────────┐
│ConfigManager│    │  EventBus   │    │    EvaComponent       │
│             │    │ (pub/sub)   │    │ (base universelle)    │
│• get()      │    │• on()       │    │• start() / stop()     │
│• get_path() │    │• emit()     │    │• emit() / get_config()│
│• get_secret │    │• off()      │    │• lifecycle idempotent │
└─────────────┘    └─────────────┘    └──────────────────────┘
                                               │
                           ┌───────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    ConversationEngine                       │
│               Memory → Prompt → LLM → Memory               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │MemoryManager │  │PromptManager │  │    LLMClient      │  │
│  │ JSON + window│  │templates .txt│  │ Ollama · OpenAI   │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Tool Calling Integration (R-020)          │   │
│  │  User → LLM → detect → execute → LLM → response     │   │
│  │  ToolRegistry · ToolExecutor · @tool decorator       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────┐    ┌────────────────────────────────┐
│   Plugin System     │    │       AgentBase (R-021b)       │
│   (eva/plugins/)    │    │       (eva/agents/)            │
│                     │    │  Boucle ReAct autonome         │
│• PluginBase         │    │  Reason → Act → Observe        │
│• PluginRegistry     │    │  AgentResult / AgentStep       │
│• PluginLoader       │    │  max_steps configurable        │
└─────────────────────┘    └────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  VectorMemory / RAG (R-024)                 │
│                      (eva/rag/)                             │
│                                                             │
│  TextChunker → EmbeddingsProvider → CosineSimilarity        │
│  VectorStorage (atomique) → VectorMemory (orchestrateur)    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       Persistence                           │
│                                                             │
│  data/                          plugins/                    │
│  ├── logs/                      ├── example_plugin.py       │
│  ├── memory/                    └── ...                     │
│  ├── cache/                                                 │
│  ├── prompts/                   eva/ui/  (R-033)            │
│  ├── dumps/                     ├── command_registry.py     │
│  └── .version                   └── commands.py            │
└─────────────────────────────────────────────────────────────┘
```

**Légende** :
- `→` : Flux de données principal
- `EventBus` : Cross-cutting (tous les composants émettent/écoutent)
- `EvaComponent` : Base universelle (lifecycle + injection)

---

## 🔧 Composants Core (Phase 0)

### ConfigManager
- Charge `config.yaml` (racine projet)
- `get(key)` avec notation pointée (ex: `llm.models.dev`)
- `get_path(name)` vers `data/`
- `get_secret(key)` depuis `.env` / variables d'environnement
- Création auto des dossiers `data/` manquants

### EventBus
- Communication découplée inter-composants (pub/sub)
- Synchrone en P0/P1 (interface stable pour migration async)
- Isolation des handlers (un handler en erreur ne bloque pas les autres)
- Payload `Dict[str, Any]` strict
- API : `on()`, `emit()`, `off()`

### EvaComponent
- Classe de base universelle pour tous les composants EVA
- `start()` / `stop()` / `shutdown()` idempotents
- Erreurs observables via events
- Helpers : `emit()`, `get_config()`, `get_path()`, `get_secret()`

### LoggingManager
- Logs techniques dans `data/logs/`
- Rotation automatique (taille + backup count)
- Événement `log_written` pour observabilité
- Règle : l'UI affiche, le Engine décide, le Logging trace

### VersionManager
- Fichier `data/.version` (semver)
- Framework de migration prêt
- Détection de version mismatch

---

## 🔧 Composants Phase 1 (Conversation)

### MemoryManager
- Backend : JSON dans `data/memory/` (session unique par jour)
- `add_message(role, content, metadata?)` + `get_context(window=N)`
- Écriture atomique (temp → rename)
- **Résumé automatique** : `maybe_summarize(llm_fn)` — déclenché si `message_count >= summary_threshold`
  - Remplace les anciens messages par 1 message système `[Resume...]` + `summary_keep_recent` messages récents
  - `llm_fn` injecté depuis `ConversationEngine` (pas de dépendance circulaire)
  - Echec silencieux si LLM indisponible (mémoire intacte)
- Config : `memory.context_window` (10) · `memory.max_messages` (100) · `memory.summary_threshold` (40) · `memory.summary_keep_recent` (10)
- Events : `memory_session_created`, `memory_message_added`, `memory_summarized`, ...

### PromptManager
- Templates dans `data/prompts/` (fichiers `.txt`, placeholders `{{var}}`)
- Auto-création des prompts par défaut si manquants
- `render(vars, strict=True)` avec validation des placeholders

### LLMClient
- Interface abstraite multi-provider : `complete(messages, profile, tools)`
- Providers : Ollama (local) · OpenAI · Anthropic · Groq
- Retry logic + backoff exponentiel + timeout configurable

### ConversationEngine
- Pipeline : `persist user → context → prompt → LLM → persist response`
- `respond(user_input) → str`
- Intégration Tool Calling (workflow 2 appels LLM si tool détecté)
- Events : `conversation_request_received`, `llm_request_started`, `conversation_reply_ready`, ...

### Plugin System
- `PluginBase` : contrat plugin (hérite `EvaComponent`)
- `PluginRegistry` : registry central + isolation erreurs
- `PluginLoader` : auto-discovery (`*_plugin.py` / `*/plugin.py`), import safe

---

## 🔧 Composants Phase 2 (Tool Calling, Agent, RAG)

### Tool System (R-020 à R-023)

Architecture provider-agnostic :
- **Ollama** : prompt engineering + détection JSON custom
- **OpenAI** : function calling natif (paramètre `tools`)

Composants :
- `ToolDefinition` (dataclass) : name, description, function, parameters, returns, `to_openai_function()`
- `ToolRegistry` (EvaComponent) : register, unregister, get, list_tools
- `ToolExecutor` (EvaComponent) : execute safe (timeout 30s, crash isolé)
- `@tool` decorator : création de tool en une ligne

ConversationEngine integration :
- `_detect_tool_call()` : parse JSON `{"action":"tool_call",...}`
- Workflow : User → LLM → detect → execute → LLM → reformulation
- Persistence mémoire des tool calls + results (`role="tool"`)

### AgentBase — Boucle ReAct (R-021b)

```
run(goal)
    │
    ├─→ Prompt système (tools_list injecté)
    │
    └─→ LOOP (step 1..max_steps) :
            LLM.complete(messages)
            _parse_response(raw)
            │
            ├─→ "tool_call"    → _execute_tool() → observation → continuer
            ├─→ "final_answer" → AgentResult(success=True)
            └─→ texte brut     → final_answer implicite
        max_steps atteint → AgentResult(success=False)
```

- `AgentStep` : step_num, action, tool_name, observation, content
- `AgentResult` : success, answer, steps, goal
- Config : `agent.max_steps` (défaut 10)
- Events : `agent_run_start`, `agent_step_complete`, `agent_run_complete`, ...

### VectorMemory / RAG (R-024)

```
add_document(text, metadata)
    ├─→ TextChunker.chunk(text)         → List[str]
    ├─→ EmbeddingsProvider.embed(chunk) → np.ndarray (normalisé L2)
    ├─→ VectorStorage.save()            → index.json + index.npz (atomique)
    └─→ emit("vector_document_added")

search(query, top_k)
    ├─→ EmbeddingsProvider.embed(query) → np.ndarray
    ├─→ CosineSimilarity.compute()      → scores [num_docs]
    ├─→ np.argsort(scores)[::-1][:k]   → top-k indices
    └─→ emit("vector_search_performed")
```

- `TextChunker` : sliding window par caractères (chunk_size + overlap)
- `EmbeddingsProvider` : interface abstraite — `FakeEmbeddingProvider` (offline, déterministe) + `LocalEmbeddingProvider` (sentence-transformers)
- `CosineSimilarity` : dot product sur vecteurs L2-normalisés (O(n×dim))
- `VectorStorage` : persistence atomique `.tmp → rename`

---

## 🔧 Composants Phase 3 (Interface)

### API REST / FastAPI (R-031 + Phase 4(B) + Phase 4(C))

Interface HTTP pour EVA. Lancement : `eva --api` (http://localhost:8000).

```
FastAPI(lifespan)
    │
    ├─→ lifespan() : asyncio.to_thread(_init_eva) au startup
    │                engine.stop() au shutdown
    │
    ├─→ GET /health       → HealthResponse                           # PUBLIC — 200 toujours
    ├─→ GET /status       → StatusResponse(**engine.status())        # auth requise — 200 toujours
    ├─→ POST /chat        → asyncio.to_thread(engine.process, msg)   # auth + rate limit
    └─→ GET /chat/stream  → StreamingResponse (SSE)                  # auth + rate limit — FAKE STREAM Phase 4(C)
```

**Sécurité Phase 4(B)** (`eva/api/security.py`) :
- `ApiKeyManager` : clé 256 bits dans `eva/data/secrets/api_key.txt`, `secrets.compare_digest`
- `RateLimiter` : fenêtre glissante 60s par IP, in-memory
- Auth acceptée : `Authorization: Bearer <key>` (header) | `X-EVA-Key: <key>` (fallback) | `?api_key=<key>` (SSE)
- `EvaState` : + `key_manager`, `rate_limiter`

**SSE Phase 4(C)** (`GET /chat/stream`) :
- FAKE STREAM : `engine.process()` bloquant → split mots + `asyncio.sleep(0.04)` par mot
- Protocole : `event:meta` → `event:token*` → `event:done` | `event:error`
- TODO Phase 5 : streaming natif OllamaProvider (`"stream": True`)

**Convention obligatoire tout endpoint SSE futur** :
```python
@app.get("/route/stream", response_class=StreamingResponse, summary="...",
    responses={200: {"content": {"text/event-stream": {...}}}, 401: ..., 429: ..., 503: ...})
```
Vérification : `assert "text/event-stream" in app.openapi()["paths"]["/route/stream"]["get"]["responses"]["200"]["content"]`

- `EvaState` dataclass module-level : engine, config, event_bus, registry, ctx, key_manager, rate_limiter
- Schémas Pydantic : `ChatRequest`, `ChatResponse`, `StatusResponse`, `HealthResponse`
- Lifespan : init EVA au startup (asyncio.to_thread), cleanup au shutdown
- Docs auto : `/docs` (Swagger UI) + `/redoc`
- **Note** : `api_module = sys.modules["eva.api.app"]` dans tests (conflit `eva.api.app` avec objet FastAPI)

### Terminal UI / Textual (R-030)

Interface graphique en terminal. Lancement : `eva --tui`.

```
EvaTuiApp(App)
    │
    ├─→ compose() : Header | Horizontal(ChatView + StatusSidebar) | EvaInput | Footer
    │
    ├─→ on_mount() : _init_eva() → composants EVA complets
    │
    ├─→ on_input_submitted() : dispatch commande vs message
    │   ├─→ /cmd → _run_command() → CommandRegistry.execute()
    │   └─→ msg  → _run_message() → run_worker(_llm_worker)
    │
    └─→ _llm_worker() : asyncio.to_thread(engine.process) → call_from_thread()
```

- `ChatView` : messages scrollables, `add_message()`, `replace_thinking()` (LLM non-bloquant)
- `StatusSidebar` : statut RUNNING/STOPPED + LLM/Mémoire/Conv
- `EvaInput` : Tab autocomplete via `CommandRegistry.get_completions()`
- Bindings : `Ctrl+Q` quit, `F1` help, `Ctrl+L` clear chat
- TCSS : `styles.tcss` (thème sombre #0a0a1a / cyan #00d4ff)
- **Note** : `_cmd_registry` (pas `_registry` — réservé par Textual)

### Command Registry (R-033)

Contrat unique partagé par CLI, Terminal UI (R-030) et API REST (R-031) :

```
Command(name, help, handler(args: str, ctx: CommandContext) → CommandResult)

CommandResult(success, output, event, event_payload, should_quit)
    └─→ Zéro I/O dans les handlers — l'UI affiche output

CommandContext(engine, config, event_bus, registry)
    └─→ Injection explicite, pas de singleton global
```

`CommandRegistry` :
- `register(command)` — avec détection des doublons (nom + alias)
- `get(name)` — résolution par nom ou alias, insensible à la casse
- `execute(raw_input, ctx)` — parse le slash, dispatch, isole les exceptions
- `get_completions(prefix)` — pour Tab autocomplete readline
- `list_commands()` — sans doublons alias (utilisé par `/help` dynamique)

8 commandes par défaut : `/help`, `/status`, `/start`, `/stop`, `/new`, `/config`, `/clear`, `/quit`

REPL (eva/repl.py) :
- Couche I/O mince au-dessus du CommandRegistry
- Readline : historique haut/bas + Tab autocomplete (fallback gracieux)

---

## 📂 Structure des Fichiers

```
EVA/
├── eva/                        # Package principal
│   ├── agents/                 # Agents autonomes (ReAct)
│   │   └── agent_base.py
│   ├── conversation/           # Pipeline conversationnel
│   │   └── conversation_engine.py
│   ├── core/                   # Fondations
│   │   ├── config_manager.py
│   │   ├── event_bus.py
│   │   ├── eva_component.py
│   │   ├── eva_engine.py
│   │   ├── logging_manager.py
│   │   └── version_manager.py
│   ├── llm/                    # Clients LLM + providers
│   │   ├── llm_client.py
│   │   └── providers/          # ollama, openai, anthropic, groq
│   ├── memory/                 # Mémoire conversationnelle
│   │   └── memory_manager.py
│   ├── plugins/                # Système de plugins
│   ├── prompt/                 # Templates de prompts
│   ├── rag/                    # Mémoire vectorielle (RAG)
│   │   ├── chunker.py
│   │   ├── embeddings_provider.py
│   │   ├── similarity_engine.py
│   │   ├── storage.py
│   │   └── vector_memory.py
│   ├── tools/                  # Tool calling system
│   │   ├── tool_definition.py
│   │   ├── tool_registry.py
│   │   ├── tool_executor.py
│   │   ├── decorator.py
│   │   └── demo_tools.py
│   ├── api/                    # API REST FastAPI (R-031)
│   │   ├── __init__.py
│   │   └── app.py              # EvaState, lifespan, /health /status /chat
│   ├── ui/                     # Contrat Command Registry (R-033) + TUI
│   │   ├── command_registry.py # Command, CommandResult, CommandContext
│   │   ├── commands.py         # Handlers par défaut (zero I/O)
│   │   └── tui/                # Terminal UI Textual (R-030)
│   │       ├── app.py          # EvaTuiApp, ChatView, StatusSidebar, EvaInput
│   │       └── styles.tcss     # Thème sombre cyan/bleu
│   ├── cli.py                  # Point d'entrée `eva` (argparse + --api --tui)
│   └── repl.py                 # REPL : readline + dispatch registry
├── plugins/                    # Plugins tiers / custom
├── data/                       # Runtime (logs, memory, cache, prompts)
├── tests/                      # Suite de tests (unit + smoke)
└── docs/                       # Documentation
```

---

## 🧪 Tests

Stratégie :
- `tests/unit/` : composants isolés (mocks, no I/O réel)
- `tests/smoke/` : intégration stack minimale

Isolation :
- `EVA_DATA_DIR` forcé vers `tmp_path` (conftest autouse)
- `EVA_TEST_MODE=1` : timeouts courts, retries=0
- Aucun accès réseau réel en tests unitaires

Métriques actuelles :
- **524 tests** passent en **~27s**
- Coverage : ~95%

---

## ⚠️ Limitations Connues

- Session unique (multi-conversation = Phase 4+)
- SSE Phase 4(C) : FAKE STREAM (split mots) — streaming natif Ollama = Phase 5
- EventBus synchrone (async prévu Phase 4 — DEBT-001)
- Pipeline séquentiel uniquement (parallèle = DEBT-002)
- CosineSimilarity O(n×dim) — FAISS prévu si index > 100k chunks
- TUI : pas de support natif du streaming (replace_thinking post-hoc)
