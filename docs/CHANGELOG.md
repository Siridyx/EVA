# CHANGELOG

Toutes les modifications notables du projet EVA sont documentées ici.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

---

## [Unreleased]

- **Phase 4(F) — Documentation API (R-042)** :
  - `eva/api/app.py` : description OpenAPI enrichie (auth table, rate limit, endpoints, "local only" notice), `openapi_tags` System + Chat
  - `/health` : `summary="Healthcheck public"` + `responses={200}` avec exemple
  - `/status` : `summary="État du moteur EVA"` + `responses={200 (deux exemples running/unavailable), 401}`
  - `/chat` : `summary="Envoyer un message à EVA"` + `responses={200, 401, 422, 429, 500, 503}` avec exemples réalistes
  - `/chat/stream` : déjà enrichi Phase 4(C) — aligné avec les autres
  - `docs/API.md` (nouveau) : guide développeur complet — installation, auth (3 méthodes), curl examples, conversation multi-tours, client Python, SSE avec sseclient-py, rate limit, codes d'erreur, non-goals
  - **515 tests passent**, 0 régression — contrat R-031 LOCKED inchangé

- **Phase 4(E) — Audit sécurité (R-043)** :
  - `docs/SECURITY_AUDIT.md` (nouveau) : threat model + 14 findings + verdict global (9/10)
  - **F-04 FIXED** : `/chat` — exception interne plus jamais exposée dans `detail` HTTP 500
  - **F-05 FIXED** : `/chat/stream` — `str(exc)` dans `event: error` remplacé par message générique
  - 4 nouveaux tests sécurité : `Bearer <espace>` → 401 | `?api_key=` (vide) → 401 | no-leak /chat → 500 générique | no-leak SSE → event:error générique
  - Vérifications OK documentées : XSS impossible (textContent), CORS absent, binding 127.0.0.1 strict, `secrets.compare_digest`, path traversal impossible, `conversation_id` via `json.dumps`

- **Phase 4(D) — Test Hardening (R-045)** :
  - `tests/conftest.py` (nouveau) : network guard session-scoped (autouse) — bloque toute connexion réseau externe
  - Network guard via `socket.getaddrinfo` : point bas niveau, couvre requests/httpx/urllib/asyncio
  - Loopback autorisé : `127.0.0.1`, `localhost`, `::1`, `0.0.0.0`, `testserver` (FastAPI TestClient)
  - Auto-marking : `pytest_collection_modifyitems` — `tests/unit/` → `unit` | `tests/smoke/` → `smoke` | `tests/integration/` → `integration`
  - Zéro annotation `@pytest.mark.xxx` nécessaire dans les fichiers de tests
  - `pyproject.toml` : `asyncio_mode = "strict"`, descriptions markers enrichies, DeprecationWarning pytest-asyncio supprimé
  - `tests/unit/test_network_guard.py` : 7 tests sentinelles (3 blocages prouvés + 4 autorisations)
  - Commandes documentées : `pytest -m unit` (dev rapide) | `pytest -m integration` | `pytest` (CI)
  - **511 tests passent**, 0 régression

- **Phase 4(C) — SSE Streaming + Web UX** :
  - `GET /chat/stream` : endpoint SSE, auth inline (Bearer header OU `?api_key=<key>` pour EventSource)
  - Rate limiting identique à `/chat` — `/health` reste public
  - FAKE STREAM : réponse complète → split mots + délai simulé 40ms/mot (TODO Phase 5 : Ollama natif)
  - Protocole : `event:meta` → `event:token` (N) → `event:done` | `event:error`
  - `eva/web/app.py` : injection clé API dans le HTML à chaque GET / (`__API_KEY__` placeholder)
  - Web UI : EventSource natif → tokens affichés un par un dans le même élément DOM (`thinkingEl`)
  - Web UI : correction polling `/status` → ajout `Authorization: Bearer <key>` (manquait depuis Phase 4(B))
  - 3 nouveaux tests SSE (401, 503, 200+text/event-stream) — 504 tests passent, 0 régression

- **Phase 4(B) — Sécurité API REST** :
  - `eva/api/security.py` (nouveau) : `ApiKeyManager` + `RateLimiter`
    - Clé API 256 bits (`secrets.token_hex(32)`) — générée au 1er lancement dans `eva/data/secrets/api_key.txt`
    - `secrets.compare_digest` — protection timing attack
    - `RateLimiter` : fenêtre glissante 60s, par IP, in-memory (reset au redémarrage)
  - `GET /health` reste **public** (aucune auth requise)
  - `GET /status` : désormais protégé — `401` sans clé valide
  - `POST /chat` : protégé + rate limited — `401` sans clé, `429` si > 60 req/min
  - Auth acceptée : `Authorization: Bearer <key>` (principal) + `X-EVA-Key: <key>` (fallback)
  - `eva --print-api-key` : nouvelle commande CLI — affiche (ou génère) la clé
  - `eva --api` : affiche la clé dans le terminal avant le démarrage uvicorn
  - `api.rate_limit_per_min: 60` et `paths.secrets` ajoutés dans `config.yaml`
  - Sécurité non bloquante : erreur d'init → mode dégradé, API toujours accessible
  - 10 tests API (4 existants mis à jour + 6 nouveaux) — 501 passent au total

- **Packaging hardening Phase 4(A)** :
  - `requires-python = ">=3.9,<3.13"` — compat validée 3.9 (baseline) + 3.11 (LTS)
  - Optional extras séparés : `[api]`, `[tui]`, `[rag]`, `[all]`, `[dev]` — core minimal sans deps lourdes
  - Versioning PEP 440 strict : `0.3.0` (MINOR = Phase complète) — politique hotfix documentée
  - Source de vérité version : `pyproject.toml` → `importlib.metadata` → `eva.__version__`
  - `LICENSE` propriétaire ajouté — mention README + `license = {file = "LICENSE"}` dans pyproject.toml
  - CI GitHub Actions : matrix Python 3.9 + 3.11, lint flake8 (E9/F63/F7/F82) + pytest full
  - Smoke CI : `eva --version` + `import eva` avant la suite de tests

- **Interface web légère (R-032)** : UI browser pour EVA — `eva --web`
  - Module-plugin `eva/web/app.py` : enregistre `GET /` sur l'app FastAPI R-031 (sans la modifier)
  - HTML/CSS/JS vanilla entièrement embarqués dans le module Python — zéro dépendance supplémentaire, zéro CDN
  - Chat history scrollable avec indicateur "EVA réfléchit…" pendant appel LLM
  - Polling `GET /status` toutes les 5s → badge RUNNING/STOPPED/UNAVAILABLE dans le header
  - `conversation_id` maintenu côté client entre les échanges (contrat R-031)
  - Désactivation automatique de la saisie si engine UNAVAILABLE
  - Thème dark cyan/bleu cohérent avec le TUI (`#0a0a1a` / `#00d4ff`)
  - Lancement : `eva --web` (http://localhost:8000) — API docs toujours sur /docs
  - `eva --api` inchangé (R-031 LOCKED)
  - 4 tests essentiels (index 200, chat input, CLI flag, référence /chat)

- **API REST FastAPI (R-031) — LOCKED** : Interface HTTP pour EVA — `eva --api`
  - `GET /health` : healthcheck 200 OK (toujours, même mode dégradé)
  - `GET /status` : toujours HTTP 200 — `{engine: "RUNNING"|"STOPPED"|"UNAVAILABLE", provider, components}`
  - `POST /chat` : `{message, conversation_id?}` → `{response, conversation_id, metadata{provider, latency_ms}}`
  - Validation Pydantic `message` : vide → 422 ; engine non démarré → 503
  - `asyncio.to_thread` pour appel LLM non-bloquant (FastAPI async → EVA sync)
  - `EvaState` dataclass : état partagé module-level (même pattern init que REPL/TUI)
  - Lifespan FastAPI : init EVA au startup, arrêt propre au shutdown
  - Docs auto Swagger UI : `http://localhost:8000/docs` + `/redoc`
  - `fastapi[standard]>=0.104.0` (uvicorn + httpx inclus) dans dépendances
  - `eva --api` flag dans cli.py (`host=127.0.0.1` strict Phase 3 — pas d'auth)
  - 4 tests essentiels (TestClient Starlette, mock engine via sys.modules)

- **Terminal UI Textual (R-030)** : Interface graphique en terminal — `eva --tui`
  - `EvaTuiApp(App)` : application Textual, layout split chat 70% / sidebar 30%
  - `ChatView(Vertical)` : messages scrollables, `add_message()`, `replace_thinking()` pour réponse LLM non-bloquante
  - `MessageWidget(Static)` : rendu coloré par sender (EVA cyan, Toi blanc, système gris, erreur rouge)
  - `StatusSidebar(Static)` : statut moteur RUNNING/STOPPED + composants LLM/Mémoire/Conv
  - `EvaInput(Input)` : Tab autocomplete sur commandes /... via `CommandRegistry.get_completions()`
  - Worker async : `asyncio.to_thread(engine.process, text)` — LLM non-bloquant, UI toujours réactive
  - Bindings : `Ctrl+Q` quitter, `F1` aide dans chat, `Ctrl+L` effacer chat
  - Thème sombre cyan/bleu (`#0a0a1a` fond, `#00d4ff` couleur principale)
  - TCSS : `styles.tcss` — 11 sélecteurs (Screen, Header, Footer, #chat, #sidebar, EvaInput, 5 classes msg)
  - Zéro I/O en dehors de l'UI : contrat R-033 respecté (CommandRegistry partagé)
  - `textual>=0.65.0` ajouté aux dépendances + `pytest-asyncio>=0.23.0` en dev
  - `eva/cli.py` : flag `--tui` (REPL reste le défaut sans flag)
  - 42 tests unitaires (rendu sidebar, TCSS, attributs, dispatch, smoke Textual avec pilot)

- **Command Registry + CLI avancé (R-033)** : Phase 3 démarrée — contrat commandes unifié
  - `Command(name, help, handler(args, ctx) → CommandResult)` — contrat partagé CLI / Textual / API REST
  - `CommandResult(success, output, event, event_payload, should_quit)` — zéro I/O dans les handlers
  - `CommandContext(engine, config, event_bus, registry)` — contexte injectable
  - `CommandRegistry` : register, get (alias + insensible à la casse), execute, completions triées, list_commands
  - `DuplicateCommandError` / `UnknownCommandError`
  - 8 commandes par défaut : `/help` (h,?), `/status` (stat), `/start`, `/stop`, `/new`, `/config` (cfg), `/clear` (cls), `/quit` (exit,q)
  - Aide dynamique depuis le registry (`/help` auto-généré à partir des commandes enregistrées)
  - `/config get KEY` : lecture d'une clé de config (ex: `/config get llm.timeout`)
  - Readline : historique haut/bas + Tab autocomplete sur `/commandes`
  - Fallback gracieux si readline absent (Windows sans pyreadline3)
  - REPL refactorisé (`eva/repl.py`) : couche I/O mince, dispatch via registry
  - Émission EventBus des events définis dans CommandResult (`engine_started`, `engine_stopped`, `cli_quit`)
  - 89 tests unitaires

- **AgentBase — Boucle ReAct (R-021)** : Agent autonome capable de raisonner et d'agir
  - Boucle `Reason → Act → Observe` (max_steps configurable, défaut 10)
  - `AgentBase(EvaComponent)` : hérite du lifecycle standard EVA
  - `AgentResult` : résultat complet (success, answer, steps, goal)
  - `AgentStep` : trace d'une étape (action, tool_name, observation, content)
  - `run(goal)` : exécution autonome jusqu'à `final_answer` ou `max_steps`
  - `_parse_response()` : JSON `tool_call` / `final_answer` / fallback texte brut
  - `_execute_tool()` : délègue à `ToolExecutor`, retourne observation string
  - `_build_tools_description()` : liste tools pour le prompt système
  - Config-driven : `agent.max_steps` dans config.yaml
  - Events observabilité : `agent_started`, `agent_run_start`, `agent_step_start`,
    `agent_step_complete`, `agent_run_complete`, `agent_max_steps_reached`, `agent_run_error`
  - 43 tests unitaires (lifecycle, run, tool_call, max_steps, parse, execute, events)

- **Mémoire vectorielle RAG (R-024)** : Pipeline RAG complet (chunk → embed → store → search)
  - `TextChunker` : découpage texte par caractères avec overlap configurable
  - `EmbeddingsProvider` : interface abstraite multi-provider
  - `FakeEmbeddingProvider` : embeddings déterministes via RNG seedé (SHA256 → seed) — 100% offline pour tests
  - `LocalEmbeddingProvider` : sentence-transformers (all-MiniLM-L6-v2, lazy load)
  - `CosineSimilarity` : dot product sur vecteurs L2-normalisés (O(n) MVP)
  - `VectorStorage` : persistence atomique (index.json + index.npz, write-tmp-then-rename)
  - `VectorMemory` : orchestrateur complet, hérite EvaComponent, lifecycle + events
  - Events observabilité : `vector_document_added`, `vector_search_performed`, `vector_index_loaded`, `vector_index_cleared`
  - 55 tests unitaires RAG actifs (9 chunker + 12 embeddings + 7 similarity + 10 storage + 13 vector_memory + 4 integration)

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

- **FakeEmbeddingProvider** : Fix NaN/Inf dans vecteurs générés — `np.frombuffer` remplacé par `np.random.default_rng(seed)` seedé via SHA256 (R-024)

- **VectorMemory.__repr__** : Fix `AttributeError: 'VectorMemory' object has no attribute 'state'` — calcul état via `_running`/`_started` (R-024)

- **tests/unit/conftest.py** : Fix `FileNotFoundError` chemin config.yaml — `parent.parent` → `parent.parent.parent / "eva"` (R-024)

- **test_vector_memory_events** : Fix handler EventBus signature `(event, payload)` → `(payload)` via lambdas — les handlers crashaient silencieusement (R-024)

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

**Convention versioning** : MAJOR.MINOR.PATCH (PEP 440 strict — Phase 4)

- MINOR = numéro de Phase complète
- 0.1.0 = Phase 1 complète
- 0.2.0 = Phase 2 complète
- 0.3.0 = Phase 3 complète  <- version actuelle
- 0.4.0 = Phase 4 complète (en cours)
- 0.X.0.devN = travail en cours sur Phase X
- Source unique : pyproject.toml -> importlib.metadata -> eva.__version__

## [0.3.0] - 2026-02-28

### Summary

**Phase 3 (R-033 a R-032) : Interfaces Utilisateur Completes**

Quatre interfaces livrees : CLI avance, Terminal UI, API REST, Interface web legere.

**Metriques** :
- 495 tests en ~15s (+139 tests Phase 3)
- Coverage ~95%
- 4/4 items Phase 3 (100%)

### Added

- **Phase 4(A) — Packaging + CI/CD** :
  - `pyproject.toml` : version PEP 440 (`0.3.0`), strategie versioning documentee
  - `eva/__init__.py` : `importlib.metadata` — source unique (`pyproject.toml`)
  - `package-data` : ajout `**/*.tcss` (styles TUI Textual)
  - `.github/workflows/ci.yml` : lint (flake8 E9/F7/F82) + tests Python 3.9
  - CI smokes : `eva --version` + `import eva` + `pytest`

- **Interface web legere (R-032)** : UI browser pour EVA — `eva --web`
  - HTML/CSS/JS vanilla inline — zero dependance, zero CDN, zero build
  - Module-plugin `eva/web/app.py` : etend l'app FastAPI R-031 sans la modifier

- **API REST FastAPI (R-031) — LOCKED** : `eva --api`
  - Contrat `/chat` : request+conversation_id -> response+conversation_id+metadata
  - `/status` toujours HTTP 200

- **Terminal UI Textual (R-030)** : `eva --tui` — layout split, worker LLM async

- **Command Registry + CLI avance (R-033)** : contrat partage CLI/TUI/API

### Fixed

- `hideThinking(null)` : affichait `"null"` en string — corrige: suppression DOM
- Code mort `if (thinkingEl === null) {}` supprime (`eva/web/app.py`)

### Chores

- `.gitignore` : `eva/data/**`, `.claude/`, `*.png/jpg/gif/webp` exclus du tracking
- Version `0.2.0-p2` -> `0.3.0` (PEP 440 compliance)

---

## [0.2.0-p2] - 2026-02-24

### Summary

**Phase 2 (R-020 à R-023) : Tool Calling Complete** : EVA peut maintenant appeler des fonctions !

**Métriques** :

- 356 tests en ~26s (+145 tests Phase 2 : 49 tools + 55 RAG + 43 AgentBase)
- Coverage ~95%
- 6/6 items Phase 2 (100%)
- 0 dette P0/P1

**Capacités** :

- ✅ Tool calling end-to-end (Ollama + OpenAI)
- ✅ @tool decorator pour créer tools simplement
- ✅ 4 demo tools (get_time, calc, list_plugins, get_status)
- ✅ Provider-agnostic architecture
- ✅ Memory persistence tool calls
- ✅ Reformulation langage naturel

### Added - Phase 2 (Tool Calling)

- **Tool Calling System (R-020)** :
  - ToolDefinition dataclass (name, description, function, parameters, returns)
  - ToolRegistry avec lifecycle (register, unregister, get, list, get_all_definitions)
  - ToolExecutor avec validation et execution safe (timeout, error handling)
  - @tool decorator pour création simple (`@tool(name, description, parameters)`)
  - ConversationEngine integration (workflow 2 LLM calls)
  - Events observabilité (tool_call_detected, tool_called, tool_result, tool_error)
  - Memory persistence (tool calls + results avec role="tool")
  - 45 tests tools (ToolDefinition 10, ToolRegistry 9, Decorator 7, ToolExecutor 7, Integration 4, Demo 8)

- **Demo Tools (R-020)** :
  - get_time(city) : Get current time in city (demo UTC)
  - calc(expression) : Safe calculator (no eval, supports +,-,\*,/)
  - list_plugins() : List registered plugins
  - get_status() : Get EVA system status
  - register_demo_tools() helper function

- **Prompt Engineering Tool Calling (R-021)** :
  - Instructions tool calling dans system prompt (data/prompts/system.txt)
  - Format JSON strict documenté ({"action":"tool_call","tool_name":"...","arguments":{...}})
  - Exemples concrets (get_time Tokyo, calc 25\*4, list_plugins)
  - Injection dynamique tools list dans prompt
  - Règles claires LLM : JSON strict une ligne, pas de texte autour, reformuler après result

- **Test End-to-End Ollama (R-022)** :
  - Workflow complet validé avec Ollama réel (llama3:8b)
  - Test calc(42\*17) : "Le résultat du calcul est : 714."
  - Test get_time(Tokyo) : "Il est actuellement 09:06:24 à Tokyo."
  - Test question directe : Répond sans tool call
  - Reformulation langage naturel après tool result
  - Script test manuel (test_ollama_tools.py)

- **OpenAI Function Calling Adapter (R-023)** :
  - ToolDefinition.to_openai_function() conversion vers OpenAI schema
  - OpenAIProvider native function calling (tools parameter)
  - LLMClient.complete(tools=...) parameter
  - OllamaProvider.complete(tools=...) parameter (ignored, uses prompt engineering)
  - Conversion réponse OpenAI tool_calls → format EVA interne
  - Architecture provider-agnostic (JSON custom Ollama, native OpenAI)
  - Backward compatible

### Changed

- **ConversationEngine.respond()** :
  - Détection tool call JSON (`_detect_tool_call()`)
  - Workflow 2 LLM calls si tool détecté (call → execute → call → response)
  - Injection tools_openai dans complete() si ToolExecutor présent
  - Memory persistence tool calls (role="assistant" tool_call + role="tool" result)
  - Event tool_call_detected émis

- **PromptManager.render()** :
  - Parameter strict (bool) ajouté (default True)
  - strict=False : Laisse placeholders non résolus (pour tests)
  - strict=True : Raise ValueError si placeholder non résolu
  - Event prompt_rendered émis

- **LLMClient.complete()** :
  - Parameter tools (List[Dict]) ajouté (optionnel)
  - Passé à \_do_complete() pour providers
  - OpenAIProvider utilise tools pour function calling natif
  - OllamaProvider ignore tools (utilise prompt engineering)

- **MemoryManager** :
  - Role "tool" ajouté à la validation (ligne 272)
  - Support persistence tool results

### Fixed

- **LLMClient retry logic** :
  - Fix max_retries=0 en test mode (changé à 1 minimum)
  - Fix raise None → RuntimeError si pas d'exception
  - Test mode : max_retries=1, retry_delay=0.01s

- **EvaComponent.**init**** :
  - Fix ordre paramètres (config, event_bus, name) vs (name, config, event_bus)
  - ConversationEngine appelle super().**init**(config, event_bus, "ConversationEngine")

- **Tests suite** :
  - 356 passed, 2 skipped, 27 xfailed
  - +145 tests Phase 2 (49 tools + 55 RAG + 43 AgentBase)

### Technical

- **Tests** : 356 passed (+140 depuis Phase 1.1)
- **Durée** : ~26s
- **Coverage** : ~95%
- **Architecture** : Provider-agnostic tool calling
- **Compatibility** : Ollama (JSON) + OpenAI (native)

---
