.

### 📘 JOURNAL — EVA Project

Projet : EVA — Assistant IA Personnel
Auteur : Sébastien
Phase actuelle : Phase 2 — Tool Calling, Agent ReAct, RAG
Statut global : ✅ Phase 2 validée (100%)
Dernière mise à jour : 2026-02-26

### 🎯 Objectif du Journal

Ce journal sert à :

- Tracer toute l’évolution du projet EVA
- Documenter les décisions
- Garder l’historique des validations
- Centraliser incidents et optimisations
- Préparer les phases futures

Aucune information critique ne doit être perdue.

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

### 📍 Phase 1 — Intelligence de Base (EN COURS → VALIDÉE ✅)

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
DEBT-001               EventBus async                     P2
DEBT-002               Pipeline parallèle                 P2
DEBT-003               Test hardening global              P2
DEBT-004               Network Guard pytest               P2
DEBT-005               Markers pytest                     P2
DEBT-006               CI/CD automatisé                   P2

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
- Cache Python .pyc (fix : delete **pycache**)
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

**Script** : test_ollama_tools.py (temporaire, supprimé après validation)

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

**Conversion** :

- EVA format : `{"tool_name": "calc", "arguments": {"expression": "2+3"}}`
- OpenAI schema : `{"type": "function", "function": {...}}`
- OpenAI response : tool_calls → converti vers format EVA

**Backward compatible** : OllamaProvider ignore tools parameter

**Tests** : 4 tests integration (100% pass)

---

## 📊 Métriques Phase 2

**Tests** :

- Phase 1.1 : 216 tests
- R-020-023 : +49 tests
- R-024 (RAG) : +55 tests
- R-021 (AgentBase) : +43 tests
- Total : 356 passed (+ 2 skipped, 27 xfailed)
- Durée : ~26s

**Couverture** :

- Tools : 100%
- Integration : 100%
- Global : ~95%

**Dettes** :

- DEBT-008 : 27 tests xfailed (prompts, logging, events)
- Aucune nouvelle dette P0/P1

---

## 🎯 Phase 2 — Bilan Final (100%)

**À la fin de R-020-023** :

✅ Tool calling fonctionnel
✅ Provider-agnostic (Ollama + OpenAI)
✅ Demo tools opérationnels
✅ Tests end-to-end validés
✅ Architecture extensible

**Phase 2 complète** :

- ✅ R-024 : RAG / Embeddings
- ✅ R-021 : AgentBase (ReAct loop)

**Prochaine étape** : Phase 3 (Terminal UI, API REST)

---

---

## 📍 Phase 2 — RAG (EN COURS → VALIDÉ ✅)

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

**Composants implémentés** :

- `TextChunker` : découpage par caractères avec overlap (sliding window)
  - `chunk_size` configurable (défaut 500)
  - `chunk_overlap` configurable (défaut 50)
  - Validation paramètres à l'init
- `EmbeddingsProvider` : interface abstraite (`embed()`, `get_embedding_dim()`)
  - `FakeEmbeddingProvider` : hash SHA256 → seed RNG → vecteur uniforme → normalisation L2
  - `LocalEmbeddingProvider` : sentence-transformers, lazy load
- `CosineSimilarity` : dot product sur vecteurs pré-normalisés L2
  - Validation shapes et dimensions à l'appel
- `VectorStorage` : persistence atomique (write .tmp → rename)
  - Métadonnées : `model_name`, `embedding_dim`, `created_at`
  - `validate_compatibility()` : détecte mismatch modèle/dimension
- `VectorMemory` : orchestrateur principal (hérite `EvaComponent`)
  - Lifecycle `start()` → load index si existe
  - Lifecycle `stop()` → save index si modifié
  - `add_document()` → pipeline chunk+embed+store
  - `search()` → embed query + similarity + top-k
  - `clear()` → reset index

**Tests** : 55 actifs (9+12+7+10+13+4)

```
Fichier                    Tests              Cible
test_chunker.py            9                  TextChunker
test_embeddings.py         12                 EmbeddingsProvider (Fake + Local)
test_similarity.py         7                  CosineSimilarity
test_storage.py            10                 VectorStorage
test_vector_memory.py      13                 VectorMemory
test_rag_integration.py    4                  Integration end-to-end
```

**Incidents & Fixes** :

🟡 Incident 1 — NaN dans FakeEmbeddingProvider
- Cause : `np.frombuffer(sha256_bytes, dtype=float32)` interprète les bits SHA256 comme floats → certains patterns forment des NaN/Inf
- Fix : `np.random.default_rng(seed)` seedé avec `int.from_bytes(hash_bytes[:8], 'big')` → garantit des valeurs valides, reste déterministe

🟡 Incident 2 — `AttributeError: 'VectorMemory' has no attribute 'state'`
- Cause : `VectorMemory.__repr__` utilisait `self.state` qui n'existe pas dans `EvaComponent`
- Fix : calcul inline `"running" if self._running else ("started" if self._started else "stopped")`

🟡 Incident 3 — `FileNotFoundError: tests/config.yaml`
- Cause : `conftest.py` calculait `parent.parent` depuis `tests/unit/` → atterrissait dans `tests/`
- Fix : `parent.parent.parent / "eva" / "config.yaml"` (3 niveaux + sous-dossier)

🟡 Incident 4 — Events non reçus dans tests
- Cause : handler `def handler(event, payload)` avec 2 args alors que `EventBus` appelle `handler(payload)` → crash silencieux (EventBus absorbe les exceptions)
- Fix : lambdas `lambda p: events_received.append("vector_document_added")`

**Métriques** :

```
Tests avant corrections : 9/13 (69%)
Tests après corrections  : 13/13 (100%)
```

---

---

## 📍 Phase 2 — AgentBase (2026-02-26 ✅)

### 🔹 R-021 — AgentBase (boucle ReAct)

**Statut** : ✅ VALIDÉ

**Contexte** :
Le fichier `eva/agents/agent_base.py` existait dans l'arborescence cible mais était vide. Cette session implémente l'agent autonome avant la Phase 3 UX.

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

**Composants** :

- `AgentStep` (dataclass) : step_num, action, tool_name, tool_args, observation, content, raw_response
- `AgentResult` (dataclass) : success, answer, steps, goal
- `AgentBase(EvaComponent)` : agent principal, lifecycle + events

**Format JSON LLM** :

```json
{"action":"tool_call","tool_name":"calc","arguments":{"expression":"2+2"}}
{"action":"final_answer","content":"Le résultat est 4."}
```

**Events** : `agent_started`, `agent_run_start`, `agent_step_start`, `agent_step_complete`, `agent_run_complete`, `agent_max_steps_reached`, `agent_run_error`

**Tests** : 43 tests en 0.27s — suite complète : 356 passed (~26s)

**Incidents** : aucun bloquant — correction triviale `subscribe` → `on` (EventBus API)

---

## 📝 Notes Personnelles

- Projet structuré dès P0
- Tests = colonne vertébrale
- Collaboration Claude + ChatGPT efficace
- Progression constante
- Pas de dette critique

## 📦 Annexes — Chiffres Clés

- Lignes roadmap : ~700
- Modules : 22+
- Tests : 356
- Temps dev : massif 😄
- Niveau : PRO

✅ Fin JOURNAL
