# EVA — ROADMAP

Feuille de route du projet EVA (Assistant IA Personnel).

**Version** : 0.2.0-p2
**Dernière mise à jour** : 2026-02-26
**Phase actuelle** : Phase 2 (Tool Calling & RAG) — 100%

---

## 🎯 Vision

Créer un assistant IA personnel :

- **Intelligent** : Conversations naturelles avec mémoire
- **Extensible** : Plugins tiers sans modification core
- **Local-first** : Fonctionne sans cloud (Ollama)
- **Professionnel** : Code propre, testé, documenté

---

## 📊 Progression Globale

| Phase     | Statut  | Progression | Tests | Durée  |
| --------- | ------- | ----------- | ----- | ------ |
| Phase 0   | ✅ DONE | 100% (8/8)  | 96    | 2.5s   |
| Phase 1   | ✅ DONE | 100% (7/7)  | 216   | 10.35s |
| Phase 1.1 | ✅ DONE | 100% (4/4)  | 216   | 10.35s |
| Phase 2   | ✅ DONE | 100% (6/6)  | 356   | ~26s   |
| Phase 3   | 🔄 WIP  | 25% (1/4)   | 445   | ~27s   |
| Phase 4   | ⏳ TODO | 0% (0/6)    | -     | -      |

**Total items complétés** : 25/34 (74%)

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

- DEBT-004 : Network guard pytest (R-045)
- DEBT-005 : Pytest markers unit/integration (R-045)
- DEBT-006 : Provider Groq (cloud gratuit)
- DEBT-007 : Provider Anthropic (Claude)
- DEBT-003 : Test hardening avancé

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
  - _parse_response(), _execute_tool(), _build_tools_description()
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

## PHASE 3 — INTERFACE UTILISATEUR (P3) 🔄 (25% en cours)

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
- [ ] [P3][M][todo] R-030 — Terminal UI (rich/textual) (deps: R-033)
- [ ] [P3][M][todo] R-031 — API REST locale (FastAPI) (deps: R-033, R-020)
- [ ] [P3][S][todo] R-032 — Interface web légère (deps: R-031)

**Statut** : 1/4 items (25%) 🔄
**Tests** : 445 passed (~27s)
**Dépendances** : Phase 1 + Phase 2

---

## PHASE 4 — QUALITÉ & PRODUCTION (P4)

Objectif : projet publiable.

- [ ] [P4][M][todo] R-040 — CI/CD (deps: R-008, R-018, R-024)
- [ ] [P4][S][todo] R-041 — Packaging complet (deps: R-017b)
- [ ] [P4][M][todo] R-042 — Documentation (deps: R-006, R-014, R-020, R-030)
- [ ] [P4][S][todo] R-043 — Audit sécurité (deps: R-016, R-041)
- [ ] [P4][M][todo] R-044 — Profiling performance (deps: R-006, R-020)
- [ ] [P4][M][todo] R-045 — Test Hardening avancé (deps: R-018)
  - Network guard (bloquer socket si pas mocké) → DEBT-004
  - Pytest markers (unit vs integration) → DEBT-005
  - Détection EVA_TEST_MODE ou PYTEST_CURRENT_TEST
  - Rationale : R-018 a couvert isolation I/O + timeouts courts (10.35s acceptable P1)
  - Note : Network guard complexe avec MockTransport, nécessite analyse fine

**Statut** : 0/6 items (0%)  
**Tests** : -  
**Dépendances** : Toutes phases précédentes

---

## 📊 Métriques Globales

| Métrique           | Valeur    | Objectif          |
| ------------------ | --------- | ----------------- |
| **Tests totaux**   | 356       | 200+ (P2 complet) |
| **Durée tests**    | ~26s      | <30s              |
| **Coverage**       | ~95%      | > 90%             |
| **Dettes P0**      | 0         | 0                 |
| **Dettes P1**      | 0         | 0                 |
| **Dettes P2**      | 8         | <10               |
| **Phase actuelle** | P2 (100%) | P2 (100%)         |

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

**Immédiat** : Phase 2 complète ✅

**Court terme** : Phase 3 (UX)

**Moyen terme** : Phase 3 (UX)

- Terminal UI
- API REST
- Interface web

**Long terme** : Phase 4 (Production)

- CI/CD
- Audit sécurité
- Performance

---

**Dernière modification** : 2026-02-26 (AgentBase R-021 codé + 43 tests)

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

## 📊 Métriques Globales

| Métrique           | Valeur    | Objectif          |
| ------------------ | --------- | ----------------- |
| **Tests totaux**   | 216       | 150+ (P1 complet) |
| **Durée tests**    | 10.35s    | <15s              |
| **Coverage**       | ~95%      | > 90%             |
| **Dettes P0**      | 0         | 0                 |
| **Dettes P1**      | 0         | 0                 |
| **Dettes P2**      | 5         | <10               |
| **Phase actuelle** | P1 (100%) | P1 (100%)         |

---

### Dettes P2 (Quality of Life)

- DEBT-004 : Network guard pytest (R-045)
- DEBT-005 : Pytest markers unit/integration (R-045)
- DEBT-003 : Test hardening avancé (déjà trackée)

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
│       └── terminal_ui.py # R-030 : Point d'émission logs UI          ⏳
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
