# EVA — ROADMAP

Feuille de route du projet EVA (Assistant IA Personnel).

**Version** : 0.3.0
**Dernière mise à jour** : 2026-03-01
**Phase actuelle** : Phase 6 (Sécurité & Distribution) — 75% complétée

---

## 🎯 Vision

Créer un assistant IA personnel :

- **Intelligent** : Conversations naturelles avec mémoire
- **Extensible** : Plugins tiers sans modification core
- **Local-first** : Fonctionne sans cloud (Ollama)
- **Professionnel** : Code propre, testé, documenté

---

## 📊 Progression Globale

| Phase     | Statut      | Progression  | Tests | Durée  |
| --------- | ----------- | ------------ | ----- | ------ |
| Phase 0   | ✅ DONE     | 100% (8/8)   | 96    | 2.5s   |
| Phase 1   | ✅ DONE     | 100% (7/7)   | 216   | 10.35s |
| Phase 1.1 | ✅ DONE     | 100% (4/4)   | 216   | 10.35s |
| Phase 2   | ✅ DONE     | 100% (6/6)   | 356   | ~26s   |
| Phase 3   | ✅ DONE     | 100% (4/4)   | 495   | ~15s   |
| Phase 4   | ✅ DONE     | 100% (10/10) | 515   | ~8min  |
| Phase 5   | ✅ DONE     | 100% (4/4)   | 560   | ~8min  |
| Phase 6   | 🔄 EN COURS | 75% (3/4)    | 738   | ~8min  |
| Phase 7   | ⏳ VISION   | 0% (0/4)     | —     | —      |
| Phase 8   | ⏳ VISION   | 0% (0/4)     | —     | —      |
| Phase 9   | ⏳ VISION   | 0% (0/4)     | —     | —      |
| Phase 10  | ⏳ VISION   | 0% (0/4)     | —     | —      |
| Phase 11  | ⏳ VISION   | 0% (0/4)     | —     | —      |

**Total items complétés** : 47/68 (69%) — 21 items restants jusqu'à la vision complète

---

## PHASE 0 — FONDATIONS (P0) ✅ (100% complété)

Objectif : Architecture solide, testable, maintenable.

- [x] [P0][S][done] R-001 — Setup projet (structure, .gitignore, README) ✅ VALIDÉ
- [x] [P0][S][done] R-002a — ConfigManager (YAML + dotenv) ✅ VALIDÉ
- [x] [P0][S][done] R-002b — Packaging pip (pyproject.toml) ✅ VALIDÉ
- [x] [P0][M][done] R-003 — EventBus (découplage composants) ✅ VALIDÉ
- [x] [P0][S][done] R-004 — LoggingManager (logs structurés + rotation) ✅ VALIDÉ
- [x] [P0][M][done] R-005 — EvaComponent (classe de base universelle) ✅ VALIDÉ
- [x] [P0][M][done] R-006 — EVAEngine (pipeline orchestrator) ✅ VALIDÉ
- [x] [P0][XS][done] R-007 — VersionManager (data/.version) ✅ VALIDÉ

**Statut** : 8/8 items (100%) ✅  
**Tests** : 96 passent en 2.5s  
**Dépendances** : Aucune

**Livrables** :

- ConfigManager (YAML + dotenv + secrets)
- EventBus (pub/sub synchrone)
- LoggingManager (rotation + events)
- EvaComponent (lifecycle + injection)
- EVAEngine (orchestrateur central)
- VersionManager (migration data)

---

## PHASE 1 — INTELLIGENCE DE BASE (P1) ✅ (100% MVP complété)

Objectif : EVA devient réellement utile.

- [x] [P1][M][done] R-011 — MemoryManager (deps: R-003, R-006) ✅ VALIDÉ
- [x] [P1][M][done] R-012 — LLMClient abstrait (deps: R-003, R-006) ✅ VALIDÉ
- [x] [P1][M][done] R-013 — PromptManager (deps: R-003, R-012) ✅ VALIDÉ
- [x] [P1][L][done] R-014 — ConversationEngine (deps: R-011, R-012, R-013) ✅ VALIDÉ
- [x] [P1][M][done] R-015 — Plugin system (loader + registry) (deps: R-004, R-005, R-006) ✅ VALIDÉ
- [x] [P1][S][done] R-017b — Packaging release-ready (deps: R-002b) ✅ VALIDÉ
- [x] [P1][S][done] R-018 — Tests unitaires P1 MVP (deps: R-011, R-012, R-013, R-014, R-015) ✅ VALIDÉ

**Statut** : 7/7 items MVP (100%) ✅  
**Tests** : 216 passent en 10.35s  
**Dépendances** : Phase 0 complète ✅

**Note R-017b** :

- Entry point `eva` fonctionnel
- Build wheel distribuable (49 KB)
- CLI polish (8 commandes)
- config.yaml inclus dans package
- Installation propre validée

**Note R-018** :

- Isolation I/O complète (tmp_path + EVA_DATA_DIR)
- EVA_TEST_MODE pour timeouts/retries courts
- Network guard + markers → DEBT-004/005 (R-045, P2)
- Version MVP validée, optimisations en dette P2

**MVP Phase 1 = COMPLET** ✅

- Pipeline conversationnel opérationnel
- Plugin system extensible
- Packaging professionnel
- Tests rapides et isolés

---

## PHASE 1.1 — PROVIDER LOCAL (OLLAMA) ✅ (100% complété)

**Objectif** : Provider local gratuit par défaut (sans API key)

**Scope** :

- Provider Ollama comme défaut
- Conversation réelle sans frais
- Tests complets validés

**DoD (Definition of Done)** :

- [x] `eva` fonctionne sans API key ✅
- [x] Conversation réelle via Ollama OK ✅
- [x] Logs + memory OK ✅
- [x] Tests suite complète OK ✅

**Tâches** :

- [x] [S][done] R-012b — OllamaProvider implementation ✅
- [x] [S][done] Intégration EVAEngine + ConversationEngine ✅
- [x] [S][done] Config ollama par défaut ✅
- [x] [S][done] Test conversation multi-tours ✅

**Statut** : 4/4 items (100%) ✅  
**Tests** : 216 passent (aucune régression)  
**Provider** : Ollama local (gratuit)

**Note** :

- Modèle par défaut : `llama3.2:latest` (2 GB, rapide)
- Endpoint : `http://localhost:11434`
- Format API : `/api/generate` (prompt-based)
- Conversion messages → prompt incluse
- Pas besoin d'API key

**Résultat** : EVA converse naturellement en local ! 🎉

---

## 🎊 PHASE 1 + 1.1 ! 🎊 ✅ (100% complété)

**Date de clôture** : 2026-02-21  
**Tag conceptuel** : v0.1.0-p1-ollama

### Résumé Phase 1 + 1.1

**EVA est maintenant** :

- ✅ Capable de converser avec mémoire et contexte
- ✅ Utilise Ollama local (gratuit, sans API key)
- ✅ Extensible via système de plugins
- ✅ Packagé proprement (wheel distribuable)
- ✅ Testé à 95% (216 tests en 10.35s)
- ✅ Documenté (JOURNAL, ROADMAP, CHANGELOG, ARCHITECTURE)
- ✅ Installable via pip (`pip install eva_assistant-*.whl`)
- ✅ CLI professionnel (8 commandes)

### Livrables Phase 1 + 1.1

1. **MemoryManager** : Mémoire conversationnelle (JSON, session unique)
2. **LLMClient** : Interface abstraite + OpenAI provider
3. **PromptManager** : Templates avec variables
4. **ConversationEngine** : Pipeline complet Memory → Prompt → LLM
5. **Plugin System** : PluginBase + Registry + Loader
6. **Packaging** : Entry point + wheel + CLI polish
7. **Tests hardening** : Isolation I/O + test mode
8. **OllamaProvider** : LLM local gratuit par défaut

### Métriques Finales

- Items complétés : 11/11 (100% Phase 1 + 1.1)
- Tests : 216 (10.35s)
- Coverage : ~95%
- Dettes P2 : 7 (non bloquantes)
- Gain performance tests : 162x (29min → 11s)
- Wheel size : 49 KB
- Provider : Ollama local (gratuit)

### Conversation Test Réussie

```
EVA> Bonjour EVA !
🤖 Bonjour ! Je suis ravi de vous voir...

EVA> Raconte-moi une blague courte
🤖 Pourquoi l'ordinateur est-il allé au docteur ?
    Parce qu'il avait un virus ! (rires)

EVA> Merci !
🤖 Je suis heureux d'avoir pu vous faire sourire...
```

### Dettes P2 (Quality of Life)

- DEBT-004 : Network guard pytest (R-045) ✅ DONE (Phase 4(D))
- DEBT-005 : Pytest markers unit/integration (R-045) ✅ DONE (Phase 4(D))
- DEBT-006 : Provider Groq (cloud gratuit) ✅ DONE (Phase 5 ext.)
- DEBT-007 : Provider Anthropic (Claude) ✅ DONE (Phase 5 ext.)
- DEBT-003 : Test hardening avancé ✅ DONE (Phase 4(D))

---

## PHASE 2 — TOOL CALLING, AGENTS & RAG (P2) ✅ (100% complété)

Objectif : EVA appelle des fonctions, raisonne de façon autonome et retrouve des informations pertinentes.

- [x] [P2][L][done] R-020 — Tool Calling System (deps: R-014) ✅ VALIDÉ
  - ToolDefinition, ToolRegistry, ToolExecutor
  - @tool decorator avec auto-schema
  - ConversationEngine integration (workflow 2 LLM calls)
  - 4 demo tools (get_time, calc, list_plugins, get_status)
  - 45 tests tools (100% pass)
  - Events : tool_call_detected, tool_called, tool_result, tool_error
- [x] [P2][S][done] R-021 — Prompt Engineering Tool Calling (deps: R-020) ✅ VALIDÉ
  - Instructions tool calling dans system prompt
  - Format JSON strict documenté (`{"action":"tool_call",...}`)
  - Exemples concrets (Tokyo, calc, list_plugins)
  - Injection dynamique tools list
  - Règles claires : JSON strict, une ligne, pas de texte autour

- [x] [P2][S][done] R-022 — Test End-to-End Ollama (deps: R-020, R-021) ✅ VALIDÉ
  - Workflow complet validé avec Ollama réel
  - calc(42\*17) → "Le résultat du calcul est : 714."
  - get_time(Tokyo) → "Il est actuellement 09:06:24 à Tokyo."
  - Tests multi-tours conversation
  - Reformulation langage naturel après tool result

- [x] [P2][M][done] R-023 — OpenAI Function Calling Adapter (deps: R-020) ✅ VALIDÉ
  - ToolDefinition.to_openai_function() conversion schema
  - OpenAIProvider native function calling support
  - LLMClient.complete(tools=...) parameter
  - Provider-agnostic architecture (Ollama JSON + OpenAI native)
  - Backward compatible (OllamaProvider ignore tools parameter)
  - Conversion réponse OpenAI → format EVA interne

- [x] [P2][XL][done] R-024 — Mémoire vectorielle (RAG) (deps: R-011) ✅ VALIDÉ
  - TextChunker : découpage par caractères avec overlap configurable
  - EmbeddingsProvider : interface abstraite + FakeEmbeddingProvider (offline, déterministe) + LocalEmbeddingProvider (sentence-transformers)
  - CosineSimilarity : dot product sur vecteurs L2-normalisés
  - VectorStorage : persistence atomique (index.json + index.npz)
  - VectorMemory : orchestrateur complet, hérite EvaComponent, lifecycle + events
  - 55 tests unitaires actifs (9+12+7+10+13+4)

- [x] [P2][L][done] R-021b — AgentBase (boucle ReAct) (deps: R-020) ✅ VALIDÉ
  - AgentBase(EvaComponent) : boucle Reason → Act → Observe
  - AgentResult / AgentStep : dataclasses de traçabilité
  - run(goal) : exécution autonome jusqu'à final_answer ou max_steps
  - \_parse_response(), \_execute_tool(), \_build_tools_description()
  - 43 tests unitaires (lifecycle, run, tool_call, max_steps, parse, execute, events)

**Statut** : 6/6 items (100%) ✅
**Tests** : 356 passed (~26s)
**Dépendances** : Phase 1 complète ✅

**Note R-024** :

- Pipeline RAG complet opérationnel (chunk → embed → store → search)
- Tests 100% offline via FakeEmbeddingProvider (RNG seedé, déterministe)
- Persistence atomique : write .tmp → rename (cohérence garantie)
- 4 bugs corrigés durant développement (NaN embeddings, repr, conftest chemin, handler signature)
- Prêt pour intégration ConversationEngine (retrieve_context → inject dans prompt)

**Livrables Phase 2** :

- Tool system complet (definition, registry, executor)
- @tool decorator pour création simple
- 4 demo tools fonctionnels
- Prompt engineering tool calling
- Test end-to-end validé avec Ollama
- OpenAI function calling adapter
- Provider-agnostic architecture
- Module RAG complet (TextChunker + Embeddings + Similarity + Storage + VectorMemory)
- AgentBase (boucle ReAct autonome)
- 145 nouveaux tests (49 tools + 55 RAG + 43 AgentBase)

**Capacités EVA Phase 2** :

- ✅ Tool calling end-to-end (Ollama + OpenAI)
- ✅ @tool decorator pour créer tools simplement
- ✅ Provider-agnostic architecture
- ✅ Memory persistence tool calls
- ✅ Reformulation langage naturel
- ✅ Mémoire vectorielle (chunking + embeddings + search)
- ✅ RAG integration ConversationEngine
- ✅ Tests offline déterministes (FakeProvider)
- ✅ Agent autonome (boucle ReAct, max_steps configurable)

---

## PHASE 3 — INTERFACE UTILISATEUR (P3) ✅ (100% complété)

Objectif : UX agréable et accessible.

- [x] [P3][S][done] R-033 — CLI avancé (historique, autocomplete, Command Registry) (deps: R-006) ✅ VALIDÉ
  - `Command(name, help, handler(args, ctx) → CommandResult)` — contrat central
  - `CommandRegistry` : register, get (alias + insensible à la casse), execute, completions, list_commands
  - `CommandResult(success, output, event, event_payload, should_quit)` — zéro I/O dans handlers
  - `CommandContext(engine, config, event_bus, registry)` — contexte d'exécution
  - 8 commandes par défaut : help, status, start, stop, new, config, clear, quit
  - Readline : historique haut/bas + Tab autocomplete (fallback gracieux Windows)
  - REPL refactorisé : couche I/O mince, dispatch via registry
  - Contrat partagé CLI / Textual (R-030) / API REST (R-031)
  - 89 tests unitaires
- [x] [P3][M][done] R-030 — Terminal UI Textual (deps: R-033) ✅ VALIDÉ
  - `EvaTuiApp(App)` : layout split chat 70% / sidebar 30%
  - `ChatView` : messages scrollables, replace_thinking pour réponse LLM
  - `StatusSidebar` : statut moteur (RUNNING/STOPPED), LLM, mémoire, conv
  - `EvaInput` : Tab autocomplete sur commandes /... via CommandRegistry
  - Worker async (`asyncio.to_thread`) — appels LLM non-bloquants
  - Bindings : Ctrl+Q (quitter), F1 (aide), Ctrl+L (effacer chat)
  - Thème sombre cyan/bleu (#0a0a1a / #00d4ff)
  - Lancement : `eva --tui`
  - Dépendance : `textual>=0.65.0`
  - 42 tests unitaires (rendu, TCSS, attributs, dispatch, smoke Textual)
- [x] [P3][M][done] R-031 — API REST locale (FastAPI) (deps: R-033) ✅ VALIDÉ — LOCKED
  - FastAPI app avec lifespan (init EVA au startup, cleanup au shutdown)
  - `EvaState` dataclass : état partagé module-level (engine, config, event_bus, registry, ctx)
  - `GET /health` : healthcheck 200 toujours (même mode dégradé)
  - `GET /status` : toujours HTTP 200 — `{engine: "RUNNING"|"STOPPED"|"UNAVAILABLE", provider, components}`
  - `POST /chat` : `{message, conversation_id?}` → `{response, conversation_id, metadata{provider, latency_ms}}`
  - Validation Pydantic : message vide → 422 ; engine non démarré → 503
  - `asyncio.to_thread` pour appel LLM non-bloquant
  - Docs auto : `/docs` (Swagger UI) + `/redoc`
  - Lancement : `eva --api` (localhost:8000 — host=127.0.0.1 strict Phase 3)
  - `fastapi[standard]>=0.104.0` (uvicorn + httpx inclus) + `httpx>=0.25.0` dev
  - 4 tests essentiels (health, status, chat, validation)
- [x] [P3][S][done] R-032 — Interface web légère (deps: R-031) ✅ VALIDÉ
  - `eva/web/app.py` : module-plugin — enregistre `GET /` sur l'app FastAPI R-031
  - `eva/api/app.py` non modifié (R-031 reste LOCKED)
  - HTML/CSS/JS entièrement embarqués dans le module Python — zéro dépendance supplémentaire
  - Thème dark cyan/bleu cohérent avec TUI (`#0a0a1a` / `#00d4ff`)
  - Chat history scrollable + indicateur "EVA réfléchit…" pendant appel LLM
  - Polling `GET /status` toutes les 5s → badge RUNNING/STOPPED/UNAVAILABLE
  - `conversation_id` maintenu côté client (contrat R-031)
  - Désactivation UI automatique si engine UNAVAILABLE
  - Lancement : `eva --web` (http://localhost:8000)
  - Docs API toujours disponibles : http://localhost:8000/docs
  - 4 tests essentiels (index 200, chat input, CLI flag, référence /chat)

**Statut** : 4/4 items (100%) ✅
**Tests** : 495 passed (~15s)
**Dépendances** : Phase 1 + Phase 2

---

## PHASE 4 — QUALITÉ & PRODUCTION (P4)

Objectif : projet publiable.

### Phase 4(A) — Packaging + CI/CD ✅ HARDENED (2026-02-28)

- [x] [P4][S][done] R-040a — Packaging PEP 440 + importlib.metadata ✅ VALIDÉ
  - `version = "0.3.0"` (MINOR = Phase complète — convention documentée)
  - Source unique : `pyproject.toml` → `importlib.metadata` → `eva.__version__`
  - Politique hotfix documentée : `0.3.x` (fix) | `0.4.0.devN` (en cours) | `0.4.0` (Phase stable)
- [x] [P4][S][done] R-040b — Optional extras séparés ✅ VALIDÉ
  - Core minimal : `pyyaml + python-dotenv + requests`
  - `[api]` : `fastapi[standard]` | `[tui]` : `textual` | `[rag]` : `numpy + sentence-transformers`
  - `[all]` : raccourci `api+tui+rag` | `[dev]` : tests + lint + mypy
  - `requires-python = ">=3.9,<3.13"` (3.9 baseline + 3.11 LTS validés)
- [x] [P4][S][done] R-041 — CI/CD GitHub Actions ✅ VALIDÉ
  - Pipeline : `lint → core-smoke → test (3.9 + 3.11)`
  - `lint` : flake8 `--select=E9,F63,F7,F82` (erreurs critiques, Python 3.11)
  - `core-smoke` : `pip install -e .` seul → vérifie install minimal
  - `test` : `pip install -e ".[dev,api,tui,rag]"` + smokes + pytest (matrix 3.9+3.11)
- [x] [P4][XS][done] R-041b — LICENSE propriétaire ✅ VALIDÉ
  - Fichier `LICENSE` : Copyright Siridyx, All rights reserved
  - `license = {file = "LICENSE"}` dans `pyproject.toml`

### Phase 4(B) — Sécurité API ✅ VALIDÉ (2026-02-28)

- [x] [P4][M][done] R-042b — API Key Auth + Rate Limiting (deps: R-031) ✅ VALIDÉ
  - `eva/api/security.py` : `ApiKeyManager` (clé 256 bits, `secrets.token_hex`, chmod 600) + `RateLimiter` (fenêtre glissante 60s, in-memory, par IP)
  - `GET /health` : **public** (200 sans auth)
  - `GET /status` : protégé — 401 sans clé valide
  - `POST /chat` : protégé + rate limited — 401 sans clé, 429 si > 60 req/min
  - Auth : `Authorization: Bearer <key>` (principal) + `X-EVA-Key: <key>` (fallback)
  - Clé générée au 1er lancement → `eva/data/secrets/api_key.txt` (couvert `.gitignore`)
  - `eva --print-api-key` : affiche (ou génère) la clé sans démarrer le serveur
  - Affichage clé dans `eva --api` avant uvicorn (lisible dans terminal)
  - Sécurité non bloquante : erreur init → mode dégradé, API toujours accessible
  - `secrets.compare_digest` : protection timing attack
  - `api.rate_limit_per_min: 60` dans `config.yaml`
  - 6 nouveaux tests (health public, status 401, chat 401, chat 401 invalide, chat 200 valide, 429 rate limit)
  - Total tests API : 10 (4 existants mis à jour + 6 nouveaux)

### Phase 4(C) — Streaming SSE ✅ VALIDÉ (2026-02-28)

- [x] [P4][M][done] R-042c — SSE Streaming + Web UX (deps: R-031, R-042b) ✅ VALIDÉ
  - `GET /chat/stream` : endpoint SSE, auth inline (Bearer header + query param `api_key` pour EventSource)
  - Rate limit appliqué identiquement à `/chat`
  - FAKE STREAM : `engine.process()` → split mots + délai 40ms/mot (documenté TODO Phase 5)
  - Protocole SSE : `event:meta` → `event:token` (N) → `event:done` | `event:error`
  - Web UI (`eva/web/app.py`) : injection clé dans la page HTML à la requête GET /
  - Web UI : EventSource navigateur natif (`/chat/stream?api_key=<key>`) — token par token
  - Web UI : correction polling `/status` (ajout header `Authorization: Bearer <key>`)
  - 3 nouveaux tests SSE (401 sans auth, 503 engine absent, 200 + text/event-stream)

### Phase 4(D) — Test Hardening ✅ VALIDÉ (2026-02-28)

- [x] [P4][M][done] R-045 — Test Hardening avancé (deps: R-018) ✅ VALIDÉ
  - `tests/conftest.py` (nouveau) : network guard autouse session (`socket.getaddrinfo`)
  - Loopback autorisé : 127.0.0.1 / localhost / ::1 / testserver
  - Auto-marking : `pytest_collection_modifyitems` — chemin → marker (unit/integration/smoke)
  - `asyncio_mode = "strict"` ajouté dans `pyproject.toml`
  - 7 tests sentinelles (`test_network_guard.py`) — 3 blocages prouvés + 4 autorisations
  - DEBT-004 ✅ (network guard) + DEBT-005 ✅ (markers)
  - Commandes : `pytest -m unit` | `pytest -m integration` | `pytest`

### Phase 4(E) — Audit sécurité ✅ VALIDÉ (2026-02-28)

- [x] [P4][S][done] R-043 — Audit sécurité (deps: R-041) ✅ VALIDÉ
  - `docs/SECURITY_AUDIT.md` : threat model + 14 findings + verdict 9/10
  - F-04 FIXED : `/chat` — exception leak supprimé (detail générique)
  - F-05 FIXED : `/chat/stream` — `str(exc)` → message générique dans SSE error
  - 4 tests sécurité : Bearer vide, api_key vide, no-leak /chat, no-leak SSE
  - Vérifications OK documentées : XSS, CORS, binding, timing-safe, path traversal

### Phase 4(F) — Documentation API ✅ VALIDÉ (2026-02-28)

- [x] [P4][M][done] R-042 — Documentation API complète (deps: R-031) ✅ VALIDÉ
  - `eva/api/app.py` : OpenAPI enrichi — description complète auth + rate limit + endpoints table, `openapi_tags` System/Chat
  - Endpoints enrichis : `summary` + `responses` avec exemples réalistes sur `/health`, `/status`, `/chat`, `/chat/stream`
  - `docs/API.md` (nouveau) : guide développeur complet — installation, auth, curl examples, SSE, rate limit, non-goals
  - 0 régression — contrat R-031 LOCKED inchangé

### Phase 4(G) — Profiling Performance ✅ VALIDÉ (2026-02-28)

- [x] [P4][M][done] R-044 — Profiling performance (deps: R-006, R-020) ✅ VALIDÉ
  - `tools/bench_api.py` (nouveau) : bench black-box API — p50/p95/max pour /health, /status, /chat, /chat/stream
  - `tools/profile_engine.py` (nouveau) : profiling cProfile interne — pipeline EVA avec mock LLM
  - `docs/PROFILING.md` (nouveau) : rapport complet avec vrais chiffres cProfile + analyse + 3 optimisations
  - **Opt 1 appliquée** : `memory_manager.py` — JSON compact (separators vs indent=2) → gain 0.3-0.6ms/appel
  - **Opt 2 appliquée** : `ollama_provider.py` — `requests.Session()` lazy → TCP keepalive, ~1-3ms/appel
  - Résultats : pipeline CPU = 3.79ms/appel (sans LLM) — `_save_session()` = 96.8% dominant

**Statut** : 10/10 items (100%) ✅ — Phase 4(A) + 4(B) + 4(C) + 4(D) + 4(E) + 4(F) + 4(G)
**Tests** : 515 passed (~8min)
**Dépendances** : Toutes phases précédentes

---

## PHASE 5 — STREAMING, MÉMOIRE & OBSERVABILITÉ (P5) ✅ (100% complété)

Objectif : EVA en production locale — streaming natif, mémoire intelligente, métriques temps réel.

### Phase 5(A) — Streaming natif Ollama ✅ VALIDÉ

- [x] [P5][M][done] R-050 — Streaming natif Ollama (deps: R-031, R-042c) ✅ VALIDÉ
  - `process_stream()` dans `EVAEngine` : génération token par token via Ollama API (`stream=True`)
  - Bridge `asyncio.Queue` : thread-safe entre thread requests et coroutine FastAPI
  - `GET /chat/stream` : vrai streaming Ollama (remplace le FAKE STREAM de Phase 4(C))
  - Protocole SSE inchangé : `event:meta` → `event:token` (N) → `event:done` | `event:error`
  - Backward compat : `/chat` (non-streaming) inchangé — R-031 LOCKED respecté

### Phase 5(B) — Mémoire enrichie ✅ VALIDÉ

- [x] [P5][M][done] R-051 — Résumé automatique mémoire (deps: R-011, R-014) ✅ VALIDÉ
  - `maybe_summarize(llm_fn)` dans `MemoryManager` : résumé automatique déclenché à seuil configurable
  - Seuil configurable : `memory.summarize_threshold` dans `config.yaml`
  - `llm_fn` injecté : aucun couplage MemoryManager → LLMClient (injection explicite ADR-006)

### Phase 5(C) — Observabilité R-052 ✅ VALIDÉ

- [x] [P5][M][done] R-052 — Métriques & observabilité (deps: R-031, R-050) ✅ VALIDÉ
  - `MetricsCollector` : compteurs in-memory (requêtes, tokens, erreurs, latences p50/p95/p99)
  - `GET /metrics` : endpoint public — format JSON — métriques temps réel
  - `event:done` enrichi : `tokens`, `latency_ms`, `ttft_ms` (Time To First Token)
  - `EvaState.metrics_collector` : état partagé module-level (pattern identique key_manager)

### Phase 5(D) — UX Clients ✅ VALIDÉ

- [x] [P5][S][done] R-053 — UX / Clients web (deps: R-052, R-032) ✅ VALIDÉ
  - Badge perf dans header web : latence p95 actualisée toutes les 30s via `pollMetrics()`
  - `.msg-meta` : TTFT + latence totale affichés sous chaque réponse EVA
  - Styles CSS cohérents avec thème dark cyan

### Phase 5 (ext.) — Providers LLM supplémentaires ✅ VALIDÉ

- [x] [P5][M][done] GeminiProvider — Google Gemini REST v1beta ✅ VALIDÉ
  - API REST `generativelanguage.googleapis.com/v1beta`, env `GEMINI_API_KEY`
  - `gemini-2.0-flash` / `gemini-1.5-pro` / `gemini-1.5-flash` configurables
  - Commit : `9a34cf9`
- [x] [P5][M][done] GroqProvider — Groq Cloud (OpenAI-compatible) ✅ VALIDÉ
  - API OpenAI-compatible `api.groq.com/openai/v1`, env `GROQ_API`
  - `llama3-8b-8192` / `llama3-70b-8192` / `mixtral-8x7b-32768`
  - 17 tests (smoke, streaming, invalid model, network guard)
  - Commit : `951bfe0`
- [x] [P5][M][done] AnthropicProvider — Anthropic Messages API ✅ VALIDÉ
  - Messages API `api.anthropic.com/v1/messages`, env `ANTHROPIC_API_KEY`
  - `claude-3-5-sonnet-20241022` / `claude-3-haiku-20240307`
  - SSE streaming via `content_block_delta`
  - 21 tests
  - Commit : `951bfe0`
- [x] [P5][XS][done] OpenAIProvider fix — model override + stream() + validation ✅ VALIDÉ
  - Commit : `86adfb4`

**Statut** : 4/4 items (100%) ✅ + 4 providers extra ✅
**Tests** : 624 passed (~8min)
**Dépendances** : Phase 4 complète

---

## PHASE 6 — SÉCURITÉ & DISTRIBUTION (P6) 🔄 (en cours)

Objectif : EVA sécurisé pour usage réseau — sessions, TLS, exposition contrôlée, multi-utilisateurs.

### Phase 6(A) — Session HttpOnly Cookie Auth ✅ VALIDÉ (2026-03-01)

- [x] [P6][M][done] R-060 — Session HttpOnly Cookie Auth (deps: R-042b) ✅ VALIDÉ
  - **Problème corrigé** : clé API exposée en clair dans HTML (`__API_KEY__`) et URLs (`?api_key=`)
  - `SessionManager` dans `eva/api/security.py` : sessions TTL 24h, `secrets.token_urlsafe(32)`, cleanup paresseux
  - `POST /auth/login` : valide la clé API, émet cookie `eva_session` (HttpOnly, SameSite=Strict)
  - `POST /auth/logout` : révoque la session, supprime le cookie
  - `require_api_key` : cookie d'abord → Bearer → X-EVA-Key (backward compat API clients)
  - `chat_stream` (SSE) : EventSource navigateur envoie les cookies automatiquement → clé jamais en URL
  - Web UI : login overlay, `tryAutoLogin()` via GET /status 200, `startApp()` après authentification
  - `_SECURITY_HEADERS` : `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store`
  - 7 nouveaux tests (login valide/invalide/503, session cookie accepté, logout, overlay, pas d'injection clé)
  - Commit : `9f7c009`

### Phase 6(B) — HTTPS / TLS ✅ VALIDÉ (2026-03-01)

- [x] [P6][M][done] R-061 — HTTPS / TLS local (deps: R-060) ✅ VALIDÉ
  - `CertManager` : certificat auto-signé (RSA 2048) généré au 1er lancement dans `eva/data/certs/`
  - `eva --api --tls` + `eva --web --tls` : uvicorn avec `ssl_keyfile` + `ssl_certfile`
  - Cookie `eva_session` : `Secure=True` activé automatiquement en mode TLS
  - Boot output : URL HTTPS affichée (`https://127.0.0.1:8000`)
  - Commit : `acbff6a`

### Phase 6(C) — Exposition réseau ⏳ (prévu)

- [ ] [P6][S][todo] R-062 — Exposition réseau 0.0.0.0 (deps: R-061) ⏳ PRÉVU
  - `eva --api --host 0.0.0.0` : écoute toutes les interfaces (LAN/VPN)
  - CORS configurable : `api.allowed_origins` dans `config.yaml`
  - Avertissement si 0.0.0.0 sans TLS
  - Rate limit par IP maintenu (`RateLimiter` déjà en place)
  - Désactivation Swagger UI en mode production (Phase 6(C))

### Phase 6(D) — Multi-utilisateurs ✅ VALIDÉ (2026-03-01)

- [x] [P6][L][done] R-063 — Multi-utilisateurs (deps: R-060) ✅ VALIDÉ
  - `UserStore` (SQLite `data/users/users.db`) : PBKDF2-HMAC-SHA256 + sel 256 bits
  - `POST /auth/register` : création de compte (admin uniquement après bootstrap)
  - `GET /me` : infos compte authentifié
  - `eva --create-admin` : bootstrap premier admin en mode interactif
  - Sessions enrichies : `SessionManager.get_user_id()` retourne l'ID utilisateur
  - Permissions : `admin` (gestion comptes) | `user` (chat)
  - Commit : `cfdaa31`

### Phase 6(D.1) — Hardening multi-user ✅ VALIDÉ (2026-03-01)

- [x] [P6][M][done] R-063b — Hardening (deps: R-063) ✅ VALIDÉ
  - **Rate limit sur endpoints auth** : `check_rate_limit` sur `POST /auth/login` et `POST /auth/register`
  - **Isolation conversations** : `_resolve_conv_id()` — namespacing `user:<id>:<uuid>`, 403 si ID inter-utilisateur
  - **Politique register** : après bootstrap, api-key-only refuse la création (requiert session admin authentifiée)
  - **Boot output** : plus d'URL `/docs`/`/redoc` au démarrage ; `eva --print-api-urls` pour dev
  - **Secret hors stdout** : clé API affichée `(set)` au lieu de la valeur en clair ; `eva --print-api-key` pour voir la clé
  - 7 tests (rate limit login/register, policy register, isolation conversations)
  - 17 tests boot output (no /docs URL, no /redoc URL, no secret in stdout)
  - Commits : `659fb79` `6098a0d` `75981a3`

**Statut** : 3/4 items (75%) 🔄 — Phase 6(A) ✅ Phase 6(B) ✅ Phase 6(D) ✅ Phase 6(D.1) ✅ | Phase 6(C) ⏳
**Tests** : 738 passed (~8min)
**Dépendances** : Phase 5 complète

---

## PHASE 7 — AUTONOMIE (P7) ⏳ VISION

Objectif : EVA agit sans que tu tapes — planifie, observe, exécute, notifie.

### Phase 7(A) — Scheduler + triggers ⏳

- [ ] [P7][M][todo] R-070 — Scheduler de tâches (deps: R-006) ⏳
  - `eva/scheduler/` : stockage tâches (JSON dans `data/scheduler/`)
  - Déclencheurs : temporel (cron-like), événement (EventBus), seuil (métriques)
  - `eva --scheduler` : démarrage du worker background
  - API : `POST /tasks` (créer), `GET /tasks` (lister), `DELETE /tasks/{id}` (supprimer)

### Phase 7(B) — Context probes ⏳

- [ ] [P7][M][todo] R-071 — Probes de contexte (deps: R-070) ⏳
  - `eva/probes/` : modules d'observation passifs
  - GitProbe : surveille les commits, branches, diff
  - MetricsProbe : seuils sur `GET /metrics` (latence, erreurs)
  - FileProbe : surveille des fichiers/dossiers (changements)
  - Probes injectées dans le scheduler comme déclencheurs

### Phase 7(C) — Background worker ⏳

- [ ] [P7][M][todo] R-072 — Worker autonome (deps: R-070, R-071) ⏳
  - Worker asyncio long-running : exécute les tâches planifiées
  - Appelle `EVAEngine.process()` avec un prompt généré automatiquement
  - Résultat stocké dans `data/scheduler/results/`
  - Reprise sur erreur : retry configurable, max_retries

### Phase 7(D) — Notifications push ⏳

- [ ] [P7][S][todo] R-073 — Notifications (deps: R-072) ⏳
  - SSE push vers la web UI ouverte : `event:notification`
  - Résumé quotidien généré par EVA (ex : "Voici ce que j'ai fait aujourd'hui")
  - Webhook optionnel (Discord / Slack / HTTP) configurable dans `config.yaml`

**Statut** : 0/4 items — VISION
**Dépendances** : Phase 6 complète

---

## PHASE 8 — INTELLIGENCE AVANCÉE (P8) ⏳ VISION

Objectif : EVA devient plus smart — choisit ses outils, retient plus, se connaît elle-même.

### Phase 8(A) — Multi-model routing ⏳

- [ ] [P8][M][todo] R-080 — Routing intelligent (deps: R-012) ⏳
  - Sélection du modèle selon la tâche (chat léger vs code vs analyse)
  - `router.yaml` : règles de routing (mots-clés, longueur, type)
  - Fallback automatique si modèle indisponible

### Phase 8(B) — Mémoire long-terme persistante ⏳

- [ ] [P8][L][todo] R-081 — Mémoire persistante cross-session (deps: R-011, R-024) ⏳
  - Survit aux redémarrages : SQLite dans `data/memory/longterm.db`
  - Fusion mémoire vectorielle + mémoire conversationnelle
  - `MemoryManager.persist()` / `MemoryManager.restore()` au lifecycle

### Phase 8(C) — Auto-analyse ⏳

- [ ] [P8][M][todo] R-082 — EVA analyse ses propres logs (deps: R-071, R-072) ⏳
  - EVA lit ses logs d'erreur et propose des corrections
  - Rapport hebdomadaire auto-généré : patterns d'usage, anomalies
  - Base pour auto-amélioration future

### Phase 8(D) — Planning multi-étapes ⏳

- [ ] [P8][L][todo] R-083 — AgentBase étendu (deps: R-021b, R-070) ⏳
  - Plans persistants multi-jours (goal + étapes stockées)
  - Integration scheduler : chaque étape = une tâche planifiée
  - `GET /agent/plan` : état du plan courant

**Statut** : 0/4 items — VISION
**Dépendances** : Phase 7 complète

---

## PHASE 9 — IDENTITÉ & UX (P9) ⏳ VISION

Objectif : EVA a une personnalité, une belle interface, une voix.

### Phase 9(A) — Personnalité configurable ⏳

- [ ] [P9][M][todo] R-090 — Identité EVA (deps: R-013) ⏳
  - Nom, ton, valeurs configurables dans `config.yaml`
  - Persona injectée dans le system prompt
  - EVA peut se présenter, expliquer ses capacités

### Phase 9(B) — Interface web riche ⏳

- [ ] [P9][L][todo] R-091 — Web UI 2.0 (deps: R-032) ⏳
  - Settings panel (modèle, personnalité, thème)
  - Historique des conversations (liste + recherche)
  - Vue tâches planifiées (scheduler Phase 7)
  - Thèmes : dark cyan (actuel) + light + custom

### Phase 9(C) — Interface vocale ⏳

- [ ] [P9][L][todo] R-092 — Voice I/O optionnel (deps: R-091) ⏳
  - STT : Whisper local (via Ollama ou whisper.cpp)
  - TTS : pyttsx3 ou Coqui TTS local
  - Push-to-talk dans la web UI
  - Désactivable — jamais obligatoire

### Phase 9(D) — CLI enrichi ⏳

- [ ] [P9][S][todo] R-093 — CLI avancé P9 (deps: R-033) ⏳
  - `eva task add "..."` : créer une tâche planifiée
  - `eva memory search "..."` : chercher dans la mémoire
  - `eva agent start "goal"` : lancer un agent autonome
  - Autocomplétion étendue

**Statut** : 0/4 items — VISION
**Dépendances** : Phase 8 complète

---

## PHASE 10 — DISTRIBUTION (P10) ⏳ VISION

Objectif : EVA quitte ton PC — app installable, accessible de partout.

### Phase 10(A) — App installable ⏳

- [ ] [P10][XL][todo] R-100 — Packaging GUI (deps: Phase 9) ⏳
  - PyInstaller / Nuitka : binaire standalone (Windows + Linux)
  - Installeur (NSIS / .deb) : EVA s'installe comme une vraie app
  - Icône, splash screen, intégration OS

### Phase 10(B) — Cloud tunnel ⏳

- [ ] [P10][M][todo] R-101 — Exposition cloud intégrée (deps: R-062) ⏳
  - `eva --tunnel` : tunnel Cloudflare ou ngrok intégré (zero-config)
  - URL publique stable (avec auth session EVA)
  - QR code affiché au démarrage pour accès mobile

### Phase 10(C) — Sync multi-device ⏳

- [ ] [P10][L][todo] R-102 — Sync mémoire (deps: R-081) ⏳
  - Mémoire long-terme optionnellement synced (S3 / Backblaze / self-hosted)
  - Même EVA sur PC, phone, tablet — même mémoire
  - Chiffrement côté client avant upload

### Phase 10(D) — Marketplace plugins ⏳

- [ ] [P10][XL][todo] R-103 — Ecosystem plugins (deps: R-015) ⏳
  - Store plugins EVA : catalogue + installation en 1 commande
  - API plugins : contrat versionné stable
  - Plugin signature (sécurité)

**Statut** : 0/4 items — VISION
**Dépendances** : Phase 9 complète

---

## PHASE 11 — COMMERCIALISATION (P11) ⏳ VISION

Objectif : EVA devient un produit que d'autres peuvent utiliser et payer.

### Phase 11(A) — Infrastructure SaaS ⏳

- [ ] [P11][XL][todo] R-110 — Déploiement serveur (deps: Phase 10) ⏳
  - Dockerfile + docker-compose : EVA containerisée
  - Déploiement VPS (Hetzner / OVH) ou PaaS (Railway / Fly.io)
  - Health checks, restart policies, monitoring

### Phase 11(B) — Licences & billing ⏳

- [ ] [P11][XL][todo] R-111 — Système de licences (deps: R-110) ⏳
  - Clé de licence (activation offline ou online)
  - Plans : Personal (gratuit) / Pro (payant) / Enterprise
  - Stripe ou LemonSqueezy pour paiements

### Phase 11(C) — Dashboard admin commercial ⏳

- [ ] [P11][L][todo] R-112 — Dashboard admin (deps: R-111) ⏳
  - Interface admin web : gestion utilisateurs, métriques, licences
  - Alertes : usage anormal, expiration licence
  - Export données (RGPD)

### Phase 11(D) — Support & documentation utilisateur ⏳

- [ ] [P11][M][todo] R-113 — Docs + support (deps: R-112) ⏳
  - Site documentation public (MkDocs ou Docusaurus)
  - Guide d'installation, FAQ, tutoriels vidéo
  - Canal support (Discord ou email)

**Statut** : 0/4 items — VISION
**Dépendances** : Phase 10 complète

---

## 📊 Métriques Globales

| Métrique           | Valeur   | Objectif          |
| ------------------ | -------- | ----------------- |
| **Tests totaux**   | 567      | 200+ (P2 complet) |
| **Durée tests**    | ~8min    | <10min            |
| **Coverage**       | ~95%     | > 90%             |
| **Dettes P0**      | 0        | 0                 |
| **Dettes P1**      | 0        | 0                 |
| **Dettes P2**      | 0        | 0                 |
| **Phase actuelle** | P6 (25%) | P6 (100%)         |

---

## 🔄 Conventions

### Tailles d'items (Effort)

- **XS** : < 1h (tiny fix, config)
- **S** : 1-3h (feature simple)
- **M** : 3-8h (feature moyenne)
- **L** : 1-2j (feature complexe)
- **XL** : 2-5j (feature majeure)

### Priorités

- **P0** : Fondations (architecture, infra)
- **P1** : Intelligence de base (MVP utilisable)
- **P2** : Agents + Production (qualité pro)

### Statuts

- **todo** : Pas commencé
- **wip** : En cours
- **done** : Terminé et validé
- **blocked** : Bloqué (attente dépendances)

---

## 📚 Références

- **JOURNAL.md** : Détails implémentation (décisions, lessons learned)
- **CHANGELOG.md** : Modifications user-facing
- **ARCHITECTURE.md** : Design global + composants
- **DEBT.md** : Dettes techniques tracées

---

## 🎯 Prochaines Étapes

**Phases complètes** : 0 + 1 + 1.1 + 2 + 3 + 4 + 5 ✅

**Horizon immédiat — Phase 6 (en cours)** :

| Étape | Focus | Statut |
|-------|-------|--------|
| 6(A)  | Session HttpOnly Cookie Auth | ✅ DONE |
| 6(B)  | HTTPS / TLS local | ⏳ NEXT |
| 6(C)  | Exposition réseau 0.0.0.0 | ⏳ |
| 6(D)  | Multi-utilisateurs | ⏳ |

**Horizon moyen — Phase 7 (Autonomie)** :

EVA agit sans que tu tapes.
Scheduler → probes contexte → worker background → notifications.

**Horizon long — Phases 8 à 11** :

| Phase | Nom | Essence |
|-------|-----|---------|
| 8 | Intelligence Avancée | EVA choisit, retient, s'analyse |
| 9 | Identité & UX | EVA a une personnalité et une belle interface |
| 10 | Distribution | EVA quitte ton PC |
| 11 | Commercialisation | EVA devient un produit |

**Principe** : on ne saute aucune étape. Chaque phase est le prérequis de la suivante.

---

**Dernière modification** : 2026-03-01 (Phase 6(A) — Session HttpOnly Cookie Auth — commit 9f7c009)

## 🏗️ Principes Fondamentaux

### Standards techniques

- Python 3.9 strict
- Typage : `Optional[...]` uniquement (pas `| None`)
- PEP8 strict
- Racine : `Eva/`
- Toute persistance → `Eva/data/`
- Logs centralisés uniquement
- Tous les composants héritent de `EvaComponent`

### Règle "Code Annoté"

Chaque fichier important doit contenir :

- Docstring module (rôle global)
- Docstrings classes/fonctions
- Commentaires sur le "pourquoi"
- Sections `# ---` pour structurer

**Objectif** : Compréhension en autonomie dans 6 mois.

## 3. CHANGE CONTROL / GOUVERNANCE

- Toute feature = ajout roadmap
- Toute modif majeure = ADR
- Pas de refactor global sans validation
- Toute dette technique → `DEBT.md` (max 3 en parallèle)
- Pas de quick fix non documenté

### Definition of Ready

Avant “doing”, une tâche doit avoir :

- Objectif clair
- Dépendances identifiées
- Critère de succès

### Definition of Done

Pour passer en DONE :

- Code OK
- Tests OK
- Typage OK
- Logs propres
- `data/` respecté
- Doc à jour
- ✅ VALIDÉ manuellement

---

## 4. 🏛️ Décisions Architecturales (ADR)

### ADR-001 — Python 3.9 strict

**Statut** : ✅ VALIDÉ  
**Décision** : Typage `Optional[X]`, pas `X | Y`, pas `match/case`

### ADR-002 — Persistance centralisée

**Statut** : ✅ VALIDÉ  
**Décision** : Tous fichiers runtime dans `data/`, jamais dans `src/` ni `plugins/`

### ADR-003 — Logging centralisé

**Statut** : ✅ VALIDÉ  
**Décision** : Un seul point d'émission (eva_engine ou terminal_ui)

### ADR-004 — EvaComponent universel

**Statut** : ✅ VALIDÉ  
**Décision** : Tout composant hérite de `EvaComponent`

### ADR-005 — EventBus synchrone P0

**Statut** : ✅ VALIDÉ  
**Décision** : Synchrone P0, interface stable pour async P1

### ADR-006 — Injection explicite

**Statut** : ✅ VALIDÉ  
**Décision** : Pas de singleton, injection config + event_bus

### ADR-007 — Package layout simple

**Statut** : ✅ VALIDÉ  
**Décision** : `eva/` à la racine (pas `src/eva/`)

### ADR-008 — Config YAML

**Statut** : ✅ VALIDÉ  
**Décision** : YAML pour config (pas TOML)

## 💡 Backlog / Idées Futures

**À ne pas traiter avant P0/P1 clean.**

- [ ] R-100 — Support multi-modal (audio, image)
- [ ] R-101 — Connecteurs externes (calendrier, mail, web)
- [ ] R-102 — Mode offline (modèle local via ollama)
- [ ] R-103 — Interface vocale
- [ ] R-104 — Mobile app (React Native)

---

## 📊 Métriques Globales (historique)

| Phase | Tests | Durée  | Dettes |
| ----- | ----- | ------ | ------ |
| P1    | 216   | 10.35s | 5      |
| P2    | 356   | ~26s   | 8      |
| P3    | 495   | ~15s   | 3      |
| P4    | 515   | ~8min  | 0      |
| P5    | 560   | ~8min  | 0      |
| P6(A) | 567   | ~8min  | 0      |

## ARBORESCENCE CIBLE

```text
Eva/                                                                    ✅
├── .env                                                                ✅
├── .env.example                                                        ✅
├── .gitignore                                                          ✅
├── MANIFEST.in                                                         ✅
├── MANIFEST.md                                                         ✅
├── PROMPT_EVA                                                          ✅
├── pyproject.toml                                                      ✅
├── README.md                                                           ✅
├── ROADMAP.md                                                          ✅
│
├── data/ # TOUTE persistance ici                                       ✅
│   ├── cache/ # Cache LLM / embeddings                                 ✅
│   ├── dumps/ # Exports / snapshots debug                              ✅
│   ├── logs/ # Logs runtime                                            ✅
│   ├── memory/ # Mémoire conversationnelle                             ✅
│   └── prompts/ # Templates de prompts                                 ✅
│
├── dist/                                                               ✅
│   ├── eva_assistant-0.1.0.dev0-py3-none-any.whl                       ✅
│   └── eva_assistant-0.1.0.dev0.tar.gz                                 ✅
│
├── docs/                                                               ✅
│   ├── ARCHITECTURE.md                                                 ✅
│   ├── CHANGELOG.md                                                    ✅
│   ├── CONTRAT.md                                                      ✅
│   ├── DEBT.md                                                         ✅
│   ├── JOURNAL.md                                                      ✅
│   ├── JOURNAL.md.old                                                  ✅
│   └── PROMPT DE BOOTSTRAP EVA.md                                      ✅
│
├── eva/ # Package Python principal                                     ✅
│   ├── __init__.py                                                     ✅
│   ├── __main__.py                                                     ✅
│   ├── cli.py                                                          ✅
│   ├── config.yaml                                                     ✅
│   ├── repl.py                                                         ✅
│   │
│   ├── agents/                                                         ✅
│   │   ├── __init__.py                                                 ✅
│   │   └── agent_base.py # R-021 : Agent Base (ReAct loop)             ✅
│   │
│   ├── conversation/                                                   ✅
│   │   ├── __init__.py                                                 ✅
│   │   └── conversation_engine.py # R-014                              ✅
│   │
│   ├── core/                                                           ✅
│   │   ├── __init__.py                                                 ✅
│   │   ├── config_manager.py # R-003 : Config centralisée              ✅
│   │   ├── eva_component.py # R-005 : Base class universelle           ✅
│   │   ├── eva_engine.py # R-006 : Pipeline principal                  ✅
│   │   ├── event_bus.py # R-004 : Bus d'événements                     ✅
│   │   ├── logging_manager.py # R-009                                  ✅
│   │   └── version_manager.py # R-010                                  ✅
│   │
│   ├── data/                                                           ✅
│   │   ├── memory/                                                     ✅
│   │   │   └── conversation_YYYY-MM-DD.json # Runtime                  ✅
│   │   └── prompts/                                                    ✅
│   │       ├── custom.txt                                              ✅
│   │       ├── system.txt                                              ✅
│   │       ├── system_concise.txt                                      ✅
│   │       └── test_unresolved.txt                                     ✅
│   │
│   ├── llm/                                                            ✅
│   │   ├── __init__.py                                                 ✅
│   │   ├── llm_client.py # R-012 : Interface abstraite                 ✅
│   │   └── providers/                                                  ✅
│   │       ├── __init__.py                                             ✅
│   │       ├── anthropic_provider.py                                   ✅
│   │       ├── groq_provider.py                                        ✅
│   │       ├── ollama_provider.py                                      ✅
│   │       └── openai_provider.py                                      ✅
│   │
│   ├── memory/                                                         ✅
│   │   ├── __init__.py                                                 ✅
│   │   └── memory_manager.py # R-011 (P1)                              ✅
│   │
│   ├── plugins/                                                        ✅
│   │   ├── __init__.py                                                 ✅
│   │   ├── plugin_base.py # R-015                                      ✅
│   │   ├── plugin_loader.py # R-015                                    ✅
│   │   └── plugin_registry.py # R-015                                  ✅
│   │
│   ├── prompt/                                                         ✅
│   │   ├── __init__.py                                                 ✅
│   │   └── prompt_manager.py # R-013                                   ✅
│   │
│   ├── rag/ # R-024 : Mémoire vectorielle (RAG)                        ✅
│   │   ├── __init__.py                                                 ✅
│   │   ├── chunker.py # TextChunker                                    ✅
│   │   ├── embeddings_provider.py # Abstract + Fake + Local            ✅
│   │   ├── similarity_engine.py # CosineSimilarity                     ✅
│   │   ├── storage.py # VectorStorage (persistence atomique)           ✅
│   │   └── vector_memory.py # VectorMemory (orchestrateur)             ✅
│   │
│   ├── tools/ # R-020 : Tool Calling System                            ✅
│   │   ├── __init__.py                                                 ✅
│   │   ├── decorator.py # @tool decorator + auto-schema                ✅
│   │   ├── demo_tools.py # 4 tools (time, calc, plugins, status)       ✅
│   │   ├── tool_definition.py # ToolDefinition + OpenAI schema         ✅
│   │   ├── tool_executor.py # ToolExecutor                             ✅
│   │   └── tool_registry.py # ToolRegistry                             ✅
│   │
│   └── ui/                                                             ✅
│       ├── __init__.py                                                 ✅
│       └── terminal_ui.py # R-030 : Point d'émission logs UI           ⏳
│
├── eva_assistant.egg-info/ # Généré par pip install -e                 ✅
│   ├── PKG-INFO                                                        ✅
│   ├── SOURCES.txt                                                     ✅
│   ├── dependency_links.txt                                            ✅
│   ├── entry_points.txt                                                ✅
│   ├── requires.txt                                                    ✅
│   └── top_level.txt                                                   ✅
│
├── plugins/ # Plugins tiers / custom                                   ✅
│   ├── .gitkeep                                                        ✅
│   └── example_plugin.py                                               ✅
│
├── scripts/                                                            ✅
│   └── eva_cli.py.old # R-007 : Entrée CLI (CLI minimal)               ✅
│
└── tests/                                                              ✅
    ├── __init__.py                                                     ✅
    ├── conftest.py                                                     ✅
    ├── smoke/                                                          ✅
    │   └── test_smoke.py # R-008                                       ✅
    └── unit/                                                           ✅
        ├── conftest.py # Fixtures RAG (FakeEmbeddingProvider, etc.)    ✅
        ├── test_agent_base.py # R-021 AgentBase (ReAct loop)           ✅
        ├── test_chunker.py # R-024 RAG                                 ✅
        ├── test_config_manager.py # R-003a                             ✅
        ├── test_conftest.py # Validation fixtures conftest             ✅
        ├── test_conversation_engine.py # R-014                         ✅
        ├── test_conversation_tools.py # R-020 Tool Calling             ✅
        ├── test_demo_tools.py # R-020 Demo Tools                       ✅
        ├── test_embeddings.py # R-024 RAG                              ✅
        ├── test_eva_component.py # R-005                               ✅
        ├── test_eva_engine.py # R-006                                  ✅
        ├── test_event_bus.py # R-004                                   ✅
        ├── test_llm_client.py # R-012                                  ✅
        ├── test_logging_manager.py # R-009                             ✅
        ├── test_memory_manager.py # R-018                              ✅
        ├── test_plugin_loader.py # R-018                               ✅
        ├── test_plugins.py # R-018                                     ✅
        ├── test_prompt_manager.py # R-013                              ✅
        ├── test_rag_integration.py # R-024 RAG (end-to-end)            ✅
        ├── test_secrets.py # R-003b                                    ✅
        ├── test_similarity.py # R-024 RAG                              ✅
        ├── test_storage.py # R-024 RAG                                 ✅
        ├── test_tools.py # R-020 Tool System                           ✅
        ├── test_vector_memory.py # R-024 RAG                           ✅
        └── test_version_manager.py # R-010                             ✅

```
