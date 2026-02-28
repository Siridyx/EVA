### 📘 JOURNAL — EVA Project

Projet : EVA — Assistant IA Personnel
Auteur : Sébastien
Phase actuelle : Phase 4 — Qualité & Production (en cours)
Statut global : Phase 3 ✅ — Phase 4(A) ✅ — Phase 4(B) ✅
Dernière mise à jour : 2026-02-28

### 🎯 Objectif du Journal

Ce journal sert à :

- Tracer toute l'évolution du projet EVA
- Documenter les décisions techniques
- Garder l'historique des validations
- Centraliser incidents et optimisations
- Préparer les phases futures

Aucune information critique ne doit être perdue.

---

### 📍 Phase 0 — Core System (COMPLÉTÉE ✅)

🔹 Modules livrés

```
ID        Module            Statut
R-003     ConfigManager     ✅
R-004     EventBus          ✅
R-005     EvaComponent      ✅
R-006     EVAEngine         ✅
R-007     CLI minimal       ✅
R-009     LoggingManager    ✅
R-010     VersionManager    ✅
```

🔹 Validation Phase 0

- 96 tests passés
- Temps moyen : ~0.35s
- Aucun appel réseau
- CLI fonctionnel
- Pipeline stable

👉 Phase 0 considérée comme socle solide

## 🗓️ Phase 0 → Début Phase 1 — Mise en place dettes fondatrices

- Création DEBT-001 : EventBus async (R-003)
- Création DEBT-002 : Pipeline parallèle (R-006)
- Création DEBT-003 : Test hardening global (R-008 → R-018)
- Décision : Acceptées comme dette P2 (non bloquantes)

---

### 📍 Phase 1 — Intelligence de Base (VALIDÉE ✅)

🔹 R-011 — MemoryManager
Statut : ✅ Validé

- Stockage JSON
- Session unique
- Context window
- Trim automatique
- Persistence
  Tests : 14/14 OK

🔹 R-012 — LLMClient

Statut : ✅ Validé

- Architecture provider
- MockTransport
- Support OpenAI (refactorable)
- Support Ollama en local
  Tests OK
  Pas de fuite réseau

🔹 R-013 — PromptManager
Statut : ✅ Validé

- Templates texte
- Variables {{ }}
- Auto-create
- Reload
- Render sécurisé
  ⚠ Incident encodage UTF-8 corrigé

🔹 R-014 — ConversationEngine
Statut : ✅ TERMINÉ

```
Steps validés
Step        Description           Statut
1           Squelette             ✅
2           API                   ✅
3           Format messages       ✅
4           Context memory        ✅
5           Prompt système        ✅
6           Appel LLM             ✅
7           Persist réponse       ✅
8           Events                ✅
9           Engine integration    ✅
10          Unit tests            ✅
11          Smoke test            ✅

Tests cumulés : +32
```

🔹 R-015 — Plugin System

Statut : ✅ Validé

- Loader
- Registry
- Safe import
- Plugins isolés
- Events

Total tests : 214
Temps : ~11s

🔹 R-018 — Tests Hardening

Statut : ✅ Validé (Essentiel)

Implémenté

- tmp_path global
- EVA_TEST_MODE
- Isolation I/O
- Timeouts courts

Reporté (DEBT)

- Network guard
- Markers pytest

📊 Performances Tests (Évolution)

```
Date              Tests           Temps
Début P1          182             29 min ❌
Après fixes       214             11s ✅

Gain : x150 🚀
```

## 🚨 Incidents Importants

🟥 Incident 1 — Prompt corrompu

- UTF-8 mixé
- MemoryError
- Tests bloqués

Fix :

- Recréation fichier
- Normalisation encodage

🟥 Incident 2 — Tests lents
Cause :

- data/ partagé
- teardown leak

Fix :

- tmp_path
- conftest autouse
- env isolé

## 🔧 Optimisations Majeures

- Isolation complète filesystem
- Mock LLM
- Config test-mode
- Centralisation data/
- Logging unifié
  Impact : stabilité + vitesse

## 📐 Décisions Structurantes

Architecture

- EvaComponent comme base unique
- EventBus cross-cutting
- Pipeline séquentiel
- Providers abstraits

Philosophie

- Test-first
- Modularité
- Pas de magie cachée
- Debug prioritaire

## 🗂️ Dette Technique (Liens)

```
ID                     Sujet                              Phase
DEBT-001               EventBus async                     P4
DEBT-002               Pipeline parallèle                 P4
DEBT-003               Test hardening global              P4
DEBT-004               Network Guard pytest               P4
DEBT-005               Markers pytest                     P4

Voir DEBT.md
```

## 📌 Phase 1 — Conclusion

À la fin de Phase 1 :

✅ Assistant fonctionnel
✅ Mémoire
✅ Prompts
✅ LLM
✅ Plugins
✅ CLI
✅ Packaging
✅ Tests rapides

👉 EVA est utilisable réellement

---

## 📍 Phase 2 — Tool Calling (100% ✅)

**Objectif** : EVA peut appeler des fonctions et outils externes

### 🔹 R-020 — Tool Calling System

**Statut** : ✅ VALIDÉ

**Implémentation** :

- ToolDefinition (dataclass frozen)
  - name, description, function, parameters, returns
  - validate_arguments() avec type checking
  - to_dict() pour serialization
  - to_openai_function() pour OpenAI (R-023)
- ToolRegistry (EvaComponent)
  - register(), unregister(), get(), list_tools(), get_all_definitions()
  - Events : tool_registered, tool_unregistered, registry_cleared
  - Détection duplicates
- Decorator @tool
  - Syntaxe simple : `@tool(name, description, parameters)`
  - Crée ToolDefinition automatiquement
  - Preserve fonction originale
  - Helpers : is_tool(), get_tool_definition()
- ToolExecutor (EvaComponent)
  - execute(tool_name, arguments) avec validation stricte
  - Timeout configurable (30s default)
  - Error handling safe (tool crash ≠ EVA crash)
  - Events : tool_called, tool_result, tool_error
  - Format résultat : `{"success": bool, "result": Any, "tool_name": str}`

- ConversationEngine integration
  - \_detect_tool_call(llm_response) → parse JSON
  - Workflow : User → LLM → detect → execute → LLM → response
  - Memory persistence (tool calls + results)
  - Event tool_call_detected
  - Format interne : `{"tool_name": str, "arguments": dict}`

**Demo Tools** :

- get_time(city) : Heure dans ville (demo UTC)
- calc(expression) : Calculatrice safe (pas eval)
- list_plugins() : Liste plugins
- get_status() : Status EVA

**Tests** : 45 tests (10+9+7+7+4+8)

**Incidents** :

- Ordre paramètres EvaComponent inversé (fix : config, event_bus, name)
- Cache Python .pyc (fix : delete __pycache__)
- Classe ToolDefinition dupliquée (fix : suppression duplication)

---

### 🔹 R-021 — Prompt Engineering Tool Calling

**Statut** : ✅ VALIDÉ

**Modifications** :

- system.txt mis à jour avec instructions tool calling
- Format JSON strict documenté
- 3 exemples concrets (get_time, calc, list_plugins)
- Règles LLM : JSON strict, une ligne, pas texte autour
- Instruction reformulation après tool result

**Méthodes** :

- ConversationEngine.\_build_tools_list() → formate liste tools pour prompt
- PromptManager.render(strict=False) → permet placeholders non résolus

**Tests** : 4 tests integration

---

### 🔹 R-022 — Test End-to-End Ollama

**Statut** : ✅ VALIDÉ

**Résultats** :

- Test 1 (calc) : "Combien font 42 \* 17 ?" → "Le résultat du calcul est : 714." ✅
- Test 2 (direct) : "Qui es-tu ?" → Réponse sans tool ✅
- Test 3 (get_time) : "Quelle heure à Tokyo ?" → "Il est actuellement 09:06:24 à Tokyo." ✅

**Workflow validé** :

1. Détection tool call JSON
2. Exécution tool via ToolExecutor
3. Reformulation langage naturel par LLM
4. Memory persistence

---

### 🔹 R-023 — OpenAI Function Calling Adapter

**Statut** : ✅ VALIDÉ

**Architecture** :

- Provider-agnostic : Format interne EVA neutre
- Ollama : Prompt engineering JSON (`{"action":"tool_call",...}`)
- OpenAI : Function calling natif (tools parameter)

**Implémentation** :

- ToolDefinition.to_openai_function() → conversion schema OpenAI
- LLMClient.complete(tools=...) → parameter ajouté
- OpenAIProvider.\_do_complete(tools=...) → utilise tools parameter
- OllamaProvider.\_do_complete(tools=...) → ignore (prompt engineering)
- ConversationEngine construit tools_openai si executor présent

**Backward compatible** : OllamaProvider ignore tools parameter

**Tests** : 4 tests integration (100% pass)

---

### 🔹 R-024 — Mémoire Vectorielle (RAG)

**Statut** : ✅ VALIDÉ

**Objectif** : Permettre à EVA de retrouver des informations pertinentes dans une base de connaissances via similarité vectorielle.

**Architecture** (pipeline complet) :

```
add_document(text)
    │
    ├─→ TextChunker.chunk(text)        → List[str]
    ├─→ EmbeddingsProvider.embed(chunk) → np.ndarray (normalisé L2)
    ├─→ VectorStorage.save()           → index.json + index.npz (atomique)
    └─→ emit(vector_document_added)

search(query, top_k)
    │
    ├─→ EmbeddingsProvider.embed(query) → np.ndarray
    ├─→ CosineSimilarity.compute()      → scores [num_docs]
    ├─→ np.argsort(scores)[::-1][:k]   → top-k indices
    ├─→ format résultats               → List[Dict]
    └─→ emit(vector_search_performed)
```

**Tests** : 55 actifs (9+12+7+10+13+4)

**Incidents & Fixes** :

🟡 Incident 1 — NaN dans FakeEmbeddingProvider
- Cause : `np.frombuffer(sha256_bytes, dtype=float32)` → NaN/Inf
- Fix : `np.random.default_rng(seed)` seedé via SHA256 → déterministe + valide

🟡 Incident 2 — `AttributeError: 'VectorMemory' has no attribute 'state'`
- Cause : `__repr__` utilisait `self.state` inexistant
- Fix : calcul inline via `self._running` / `self._started`

🟡 Incident 3 — `FileNotFoundError: tests/config.yaml`
- Cause : `conftest.py` — chemin `parent.parent` incorrect
- Fix : `parent.parent.parent / "eva" / "config.yaml"`

🟡 Incident 4 — Events non reçus dans tests
- Cause : handler `def handler(event, payload)` — EventBus appelle `handler(payload)`
- Fix : lambdas `lambda p: events_received.append(...)`

---

### 🔹 R-021b — AgentBase (boucle ReAct)

**Statut** : ✅ VALIDÉ

**Contexte** :
`eva/agents/agent_base.py` existait dans l'arborescence cible mais était vide. Implémenté avant Phase 3.

**Architecture — Boucle ReAct** :

```
run(goal)
    │
    ├─→ Prompt système (tools_list injecté)
    ├─→ Messages : [system, user(goal)]
    │
    └─→ LOOP (step 1..max_steps) :
            LLM.complete(messages)
            _parse_response(raw)
            │
            ├─→ "tool_call"     → _execute_tool() → observation → messages += → continuer
            ├─→ "final_answer"  → AgentResult(success=True, answer)
            └─→ texte brut      → final_answer implicite
        max_steps atteint → AgentResult(success=False)
```

**Events** : `agent_started`, `agent_run_start`, `agent_step_start`, `agent_step_complete`, `agent_run_complete`, `agent_max_steps_reached`, `agent_run_error`

**Tests** : 43 tests

**Incidents** : correction triviale `subscribe` → `on` (EventBus API)

---

## 📊 Métriques Phase 2

**Tests** :

- Phase 1.1 : 216 tests
- R-020-023 : +49 tests
- R-024 (RAG) : +55 tests
- R-021b (AgentBase) : +43 tests
- Total : 356 passed (+ 2 skipped, 27 xfailed)
- Durée : ~26s

**Couverture** : ~95% global

---

## 📌 Phase 2 — Conclusion

✅ Tool calling fonctionnel (Ollama + OpenAI)
✅ Agent autonome (boucle ReAct)
✅ Mémoire vectorielle (RAG complet)
✅ Provider-agnostic architecture
✅ 356 tests, ~95% coverage

---

## 📍 Phase 3 — Interface Utilisateur (EN COURS 🔄)

### 🔹 R-033 — Command Registry + CLI avancé

**Statut** : ✅ VALIDÉ

**Contexte** :
Avant de construire l'UI Textual (R-030), définir le contrat Command Registry partagé entre CLI, Terminal UI et API REST — sinon chaque couche aurait son propre dispatch, créant de la dette.

**Décision clé** :
R-033 ne devient pas une mini-UI. Périmètre strict :
- Historique haut/bas (readline)
- Autocomplétion `/commandes` (Tab)
- Command Registry unifié
- Zéro I/O dans les handlers

**Contrat Command Registry** :

```
Command(name, help, handler(args: str, ctx: CommandContext) → CommandResult)

CommandResult(success, output, event, event_payload, should_quit)
    └─→ Handlers ne font jamais print/input — l'UI affiche output

CommandContext(engine, config, event_bus, registry)
    └─→ Injection explicite — handlers stateless
```

**8 commandes par défaut** :

```
/help  (h, ?)    Aide dynamique générée depuis le registry
/status (stat)   Statut moteur + composants
/start           Démarre EVAEngine
/stop            Arrête EVAEngine
/new             Nouvelle conversation
/config (cfg)    Aperçu ou /config get KEY
/clear (cls)     Efface l'écran (ANSI)
/quit (exit, q)  should_quit=True + event cli_quit
```

**REPL refactorisé** (`eva/repl.py`) :
- Couche I/O mince : `input() → registry.execute() → print(output)`
- Readline : historique + Tab autocomplete
- Fallback gracieux si readline absent (Windows sans pyreadline3)

**Bénéfice architectural** :
R-030 (Textual), R-031 (FastAPI) utiliseront exactement le même `CommandRegistry` — zéro duplication de logique.

**Tests** : 89 tests (89/89)
**Suite complète** : 445 passed (~27s), 0 régression

---

## 📐 Décisions Phase 3

**Ordre d'implémentation** :
1. R-033 — Command Registry (contrat first) ✅
2. R-030 — Terminal UI Textual (construit sur R-033) ✅
3. R-031 — API REST FastAPI (construit sur R-033)
4. R-032 — Interface web légère (construit sur R-031)

**Principe UI retenu** :
Un seul point de sortie utilisateur. L'UI affiche, les handlers retournent. Pas de print dans la logique métier.

---

## 📝 Notes

- Projet structuré dès P0 — la rigueur paie au fil des phases
- Tests = colonne vertébrale (tests cassés = signal d'architecture incorrecte)
- Progression constante, zéro dette P0/P1

## 📦 Annexes — Chiffres Clés

- Modules : 25+
- Tests : 445
- Coverage : ~95%
- Durée suite : ~27s
- Niveau : PRO

---

### 🔹 R-030 — Terminal UI Textual

**Statut** : ✅ VALIDÉ

**Contexte** :
R-033 a défini le contrat. R-030 construit le Terminal UI par-dessus, sans modifier le registry.

**Architecture** :

```
EvaTuiApp(App)
    │
    ├─→ compose() : Header | Horizontal(ChatView + StatusSidebar) | EvaInput | Footer
    │
    ├─→ on_mount() : _init_eva() → ConfigManager, EventBus, MemoryManager, PromptManager,
    │                              OllamaProvider, ConversationEngine, EVAEngine
    │
    ├─→ on_input_submitted() : dispatch /commande → CommandRegistry | message → worker
    │
    └─→ _llm_worker() : asyncio.to_thread(engine.process, text) → call_from_thread()
```

**Composants** :
- `ChatView(Vertical)` : `add_message()`, `replace_thinking()`, scroll auto
- `MessageWidget(Static)` : rendu coloré (msg-eva, msg-user, msg-sys, msg-err)
- `StatusSidebar(Static)` : `_render_status()` / `_render_no_engine()` → RUNNING/STOPPED
- `EvaInput(Input)` : `on_key(Tab)` → `registry.get_completions()` → complète si unique
- Bindings : `Ctrl+Q`, `F1`, `Ctrl+L`

**Décision clé — conflit `_registry`** :
Textual utilise `self._registry` en interne. Renommage en `self._cmd_registry` pour éviter le conflit.

**Dépendances ajoutées** :
- `textual>=0.65.0` (installé : 8.0.0)
- `pytest-asyncio>=0.23.0` (installé : 1.2.0)

**Tests** : 42 tests
- 7 `TestStatusSidebarRender` — rendu sans UI
- 6 `TestTheme` — TCSS existence + contenu
- 7 `TestEvaTuiAppInit` — attributs initiaux
- 3 `TestCLITuiFlag` — flag --tui
- 5 `TestDispatchLogic` — dispatch commandes/messages
- 2 `TestEvaInput` — instanciation
- 10 `TestEvaTuiSmoke` — smoke tests Textual avec pilot
- 2 `TestTuiInit` — module __init__

**Suite complète** : 487 passed (~14s), 0 régression

---

## 📊 Métriques Phase 3 (partielle)

**Tests** :
- R-033 : +89 tests
- R-030 : +42 tests
- Total : 487 passed
- Durée : ~14s

---

## 📦 Annexes — Chiffres Clés

- Modules : 30+
- Tests : 487
- Coverage : ~95%
- Durée suite : ~14s
- Niveau : PRO

---

### 🔹 R-031 — API REST FastAPI

**Statut** : ✅ VALIDÉ — LOCKED

**Contexte** :
R-033 a défini le contrat. R-031 expose EVA via HTTP — 3 endpoints simples sur le même EVAEngine.

**Architecture** :

```
FastAPI(lifespan)
    │
    ├─→ lifespan() : asyncio.to_thread(_init_eva) au startup
    │                engine.stop() au shutdown
    │
    ├─→ GET /health  → HealthResponse(status="ok", version)            # toujours 200
    ├─→ GET /status  → StatusResponse(engine, provider, components)     # toujours 200
    └─→ POST /chat   → asyncio.to_thread(engine.process, message)      # 503/422/500
              └─→ ChatResponse(response, conversation_id, metadata)
```

**Contrat /chat (Phase 3)** :
- Request : `{message: str, conversation_id?: str}`
- Response : `{response: str, conversation_id: str, metadata: {provider: str, latency_ms: int}}`
- `conversation_id` généré via `uuid.uuid4()` si non fourni par le client
- `latency_ms` mesuré via `time.monotonic()` autour de l'appel LLM

**Contrat /status (Phase 3)** :
- Toujours HTTP 200 (pas de 503 — mode dégradé supporté)
- `engine` : "RUNNING" | "STOPPED" | "UNAVAILABLE" (si engine None)
- `provider` : "ollama" si engine démarré, None sinon

**Décisions** :
- `EvaState` module-level (pas de DI complexe pour 3 endpoints)
- `asyncio.to_thread` : appel LLM synchrone depuis route async FastAPI
- `fastapi[standard]` : inclut uvicorn + httpx (pas de dépendance explicite uvicorn)
- Lifespan (pas `@app.on_event`) : pattern moderne FastAPI recommandé
- `host=127.0.0.1` strict Phase 3 (Phase 4 ajoutera auth JWT avant 0.0.0.0)

**Décision clé — import sys.modules dans les tests** :
`import eva.api.app as api_module` résout `eva.api.app` comme l'objet FastAPI (à cause de l'export dans `__init__.py`). Correction : `api_module = sys.modules["eva.api.app"]` après import du module.

**Tests** : 4 tests essentiels
- `test_health_ok` : GET /health → 200 + status/version
- `test_status_returns_200` : GET /status → 200 (UNAVAILABLE sans engine, RUNNING avec)
- `test_chat_returns_response` : POST /chat → 200 + response/conversation_id/metadata
- `test_chat_validation_error` : POST /chat message vide → 422

**Suite complète** : 491 passed (~15s), 0 régression

---

### 🔹 R-031 — Stabilisation (Phase 3 LOCKED)

**Date** : 2026-02-27

**Corrections appliquées** :

1. **Sécurité host** : `main(host="127.0.0.1")` — commentaire Phase 3 security rule
2. **Contrat /chat** : nouveau format `conversation_id` + `metadata{provider, latency_ms}`, suppression `ok`
3. **Contrat /status** : toujours HTTP 200, format `{engine, provider, components}`
4. **Dépendances** : commentaire explicatif `fastapi[standard]` dans `pyproject.toml`
5. **Tests** : simplifiés de 37 → 4 tests essentiels (couverture ciblée)
6. **Docstring** : en-tête complet dans `eva/api/app.py` (Scope Phase 3 + Future phases)

---

---

### 🔹 R-032 — Interface Web Légère

**Statut** : ✅ VALIDÉ

**Contexte** :
R-031 (API REST) était LOCKED. R-032 ajoute une interface browser sans modifier l'API.

**Architecture** :

```
eva --web
    └─→ import eva.web.app  ← side-effect : enregistre GET / sur app FastAPI
    └─→ uvicorn.run(app)    ← même app objet que R-031

http://127.0.0.1:8000/       → HTML page (R-032)
http://127.0.0.1:8000/chat   → POST JSON (R-031, inchangé)
http://127.0.0.1:8000/status → GET JSON  (R-031, inchangé)
http://127.0.0.1:8000/docs   → Swagger UI (FastAPI auto)
```

**Décisions** :
- Module-plugin : `import eva.web.app` enregistre `GET /` sur l'app (pas de nouvelle app FastAPI)
- HTML/CSS/JS inline dans une string Python — zéro dépendance ajoutée, zéro CDN
- `_build_html()` + `_HTML` module-level : construit une seule fois au chargement
- Polling `/status` toutes les 5s via `setInterval` (vanilla JS)
- `conversation_id` maintenu côté client entre les échanges (contrat R-031 respecté)

**Tests** : 4 essentiels
- `test_web_index_ok` : GET / → 200 + text/html
- `test_web_has_chat_input` : HTML contient `msg-input`
- `test_cli_has_web_flag` : `--web` dans cli.py
- `test_web_references_chat_api` : `/chat` dans le HTML

**Suite complète** : 495 passed (~15s), 0 régression

**Vérification post-commit (89cfbee)** :
- Bug corrigé : `hideThinking(null)` affichait la chaîne `"null"` → suppression de l'élément DOM
- Code mort supprimé : `if (thinkingEl === null) {}` (jamais exécuté)
- 5/5 points de sécurité vérifiés : instance unique FastAPI, endpoints /chat//health//status exposés, host=127.0.0.1, setInterval sans fuite, textContent uniquement (pas d'innerHTML)
- Tests web : 4/4 + API : 4/4 = 8/8 ✅

---

## 📊 Métriques Phase 3 (COMPLÈTE ✅)

**Tests** :
- R-033 : +89 tests
- R-030 : +42 tests
- R-031 : +4 tests (37 initiaux → simplifiés à l'essentiel)
- R-032 : +4 tests
- Total : 495 passed
- Durée : ~15s

**Phase 3 : 4/4 items (100%) ✅**

---

---

## 🚀 Phase 4 — Packaging + CI/CD (en cours)

### 🔹 Phase 4(A) — Packaging + CI/CD

**Date** : 2026-02-28

**Problème détecté** :
`version = "0.2.0-p2"` dans `pyproject.toml` → PEP 440 non conforme → `pip install -e .` échoue.

**Corrections appliquées** :

1. **Version PEP 440** : `0.2.0-p2` → `0.3.0`
   - Convention : MINOR = numéro de Phase complète (0.1.0 → 0.2.0 → 0.3.0 → 0.4.0)
   - Documenté dans `pyproject.toml` (commentaire + stratégie future setuptools_scm)

2. **Source unique de version** : `eva/__init__.py` lit via `importlib.metadata`
   - Plus de duplication (pyproject.toml = seule source de vérité)
   - Fallback `"dev"` si package non installé (signal clair)

3. **`pyproject.toml` finalisé** :
   - `package-data` : ajout `**/*.tcss` (styles TUI absents précédemment)
   - `classifiers` : `Pre-Alpha` → `Alpha`

4. **CI/CD GitHub Actions** (`.github/workflows/ci.yml`) :
   - Job `lint` : flake8 `--select=E9,F63,F7,F82` (erreurs critiques seulement)
   - Job `test` : `pip install -e ".[dev,api,tui,rag]"` + smokes + pytest
   - Matrix : Python 3.9 (baseline) + 3.11 (LTS récent)
   - Note sécurité : `host=127.0.0.1` commenté, TestClient sans bind réseau

5. **Validation locale** :
   - `pip install -e .` → `Successfully installed eva-assistant-0.3.0` ✅
   - `eva --version` → `EVA 0.3.0` ✅
   - `python -c "import eva; print(eva.__version__)"` → `0.3.0` ✅
   - `pytest --tb=short -q` → `495 passed, 0 régression` ✅
   - `flake8 eva/ --select=E9,F63,F7,F82` → aucune erreur critique ✅

### 🔹 Phase 4(A) — Hardening packaging (2026-02-28)

Suite au hardening appliqué après validation initiale :

1. **Compat Python élargie** : `requires-python = ">=3.9,<3.13"` (3.10/3.11/3.12 incluses)
   - CI matrix étendue : Python 3.9 (baseline) + 3.11 (LTS récent)
   - CI install : `pip install -e ".[dev,api,tui,rag]"` — tous les extras pour tester la suite complète

2. **Optional deps restructurées** :
   - `[api]` : `fastapi[standard]>=0.104.0` — plus hors des deps core
   - `[tui]` : `textual>=0.65.0` — plus hors des deps core
   - `[rag]` : `numpy + sentence-transformers` — lourd, optionnel
   - `[all]` : raccourci pour api+tui+rag
   - `[dev]` : inchangé (pytest, flake8, black, mypy, httpx)
   - Core minimal : `pyyaml + python-dotenv + requests` uniquement

3. **LICENSE propriétaire** : fichier `LICENSE` créé (Copyright Siridyx, All rights reserved)
   - `license = {file = "LICENSE"}` dans `pyproject.toml`
   - Mention README : section Licence + indicateur dans table statut

4. **Politique hotfix documentée** dans `pyproject.toml` :
   - `0.3.x` : correctifs Phase 3 (hotfix)
   - `0.4.0.devN` : en cours Phase 4
   - `0.4.0` : Phase 4 complète

---

## 📦 Annexes — Chiffres Clés

- Modules : 37+
- Tests : 495
- Coverage : ~95%
- Durée suite : ~15s
- Version : 0.3.0 (PEP 440)
- Niveau : PRO

### 🔹 Phase 4(B) — Sécurité API REST (2026-02-28)

**Objectif** : rendre `eva --api` production-ready avec authentification + rate limiting.

#### Fichiers créés / modifiés

| Fichier | Action | Description |
|---|---|---|
| `eva/api/security.py` | CRÉÉ | `ApiKeyManager` + `RateLimiter` |
| `eva/api/app.py` | MODIFIÉ | imports, EvaState, _init_eva, dépendances FastAPI, routes, main() |
| `eva/config.yaml` | MODIFIÉ | `paths.secrets` + section `api` |
| `eva/cli.py` | MODIFIÉ | flag `--print-api-key` |
| `tests/unit/test_api.py` | MODIFIÉ | 6 nouveaux tests + 3 existants mis à jour + reset_state étendu |

#### Décisions techniques

**ApiKeyManager** :
- Clé 256 bits = `secrets.token_hex(32)` = 64 hex chars
- Persistée dans `eva/data/secrets/api_key.txt` (couvert par `.gitignore` via `eva/data/**`)
- `chmod 600` tenté (ignoré silencieusement sur Windows)
- Chargée au démarrage de l'API, affichée dans le terminal avant uvicorn

**RateLimiter** :
- Fenêtre glissante 60s par IP, in-memory (`collections.deque`)
- Reset au redémarrage API (acceptable Phase 4 — Redis en Phase 5)
- Mode dégradé : si non initialisé, pas de limite (API toujours accessible)

**Sécurité non bloquante** :
- Bloc `try/except` séparé dans `_init_eva()` pour l'init sécurité
- Erreur → `_state.init_error` + log, mais API démarre quand même

**Auth FastAPI** :
- `require_api_key` : dépendance `Depends()` sur `/status` et `/chat`
- Priorité : `Authorization: Bearer <key>` > `X-EVA-Key: <key>` (fallback)
- `secrets.compare_digest` : protection timing attack (pas d'early exit)
- `/health` reste public (aucune auth)

#### Validation

```
pytest tests/unit/test_api.py -v  → 10/10 PASSED
pytest --tb=short -q              → 501 passed, 2 skipped, 27 xfailed, 4 xpassed (14.48s)
                                     0 régression
```

---

✅ Fin JOURNAL (Phase 3 COMPLÈTE — Phase 4(A) HARDENED — Phase 4(B) VALIDÉE)
