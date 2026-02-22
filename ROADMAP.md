# EVA — ROADMAP

Feuille de route du projet EVA (Assistant IA Personnel).

**Version** : 0.1.0-p1  
**Dernière mise à jour** : 2026-02-21  
**Phase actuelle** : Phase 1.1 (Intelligence + Provider Local) — 100%

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
| Phase 2   | ⏳ TODO | 0% (0/5)    | -     | -      |
| Phase 3   | ⏳ TODO | 0% (0/4)    | -     | -      |
| Phase 4   | ⏳ TODO | 0% (0/6)    | -     | -      |

**Total items complétés** : 19/34 (56%)

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

## 🎊 PHASE 1 + 1.1 COMPLÈTES ! 🎊

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

## PHASE 2 — AGENTS & ORCHESTRATION (P2) ⏳

Objectif : EVA devient intelligent et autonome.

- [ ] [P2][L][todo] R-020 — Tool Calling (function calling) (deps: R-014)
- [ ] [P2][L][todo] R-021 — Agent Base (raisonnement + planning) (deps: R-020)
- [ ] [P2][M][todo] R-022 — Tool Registry (enregistrement + dispatch) (deps: R-020)
- [ ] [P2][L][todo] R-023 — Planificateur multi-step (deps: R-021, R-022)
- [ ] [P2][XL][todo] R-024 — Mémoire vectorielle (RAG) (deps: R-011)

**Statut** : 0/5 items (0%)  
**Tests** : -  
**Dépendances** : Phase 1 complète ✅

---

## PHASE 3 — INTERFACE UTILISATEUR (P2)

Objectif : UX agréable et accessible.

- [ ] [P2][M][todo] R-030 — Terminal UI (rich/textual) (deps: R-006, R-014)
- [ ] [P2][M][todo] R-031 — API REST locale (FastAPI) (deps: R-014, R-020)
- [ ] [P2][S][todo] R-032 — Interface web légère (deps: R-031)
- [ ] [P2][S][todo] R-033 — CLI avancé (historique, autocomplete) (deps: R-006)

**Statut** : 0/4 items (0%)  
**Tests** : -  
**Dépendances** : Phase 1 + Phase 2

---

## PHASE 4 — QUALITÉ & PRODUCTION (P2)

Objectif : projet publiable.

- [ ] [P2][M][todo] R-040 — CI/CD (deps: R-008, R-018, R-024)
- [ ] [P2][S][todo] R-041 — Packaging complet (deps: R-017b)
- [ ] [P2][M][todo] R-042 — Documentation (deps: R-006, R-014, R-020, R-030)
- [ ] [P2][S][todo] R-043 — Audit sécurité (deps: R-016, R-041)
- [ ] [P2][M][todo] R-044 — Profiling performance (deps: R-006, R-020)
- [ ] [P2][M][todo] R-045 — Test Hardening avancé (deps: R-018)
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

| Métrique           | Valeur      | Objectif          |
| ------------------ | ----------- | ----------------- |
| **Tests totaux**   | 216         | 150+ (P1 complet) |
| **Durée tests**    | 10.35s      | <15s              |
| **Coverage**       | ~95%        | > 90%             |
| **Dettes P0**      | 0           | 0                 |
| **Dettes P1**      | 0           | 0                 |
| **Dettes P2**      | 7           | <10               |
| **Phase actuelle** | P1.1 (100%) | P1.1 (100%)       |

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

**Immédiat** : Rebuild wheel finale avec Ollama ✅

**Court terme** : Phase 2 (Agents & Orchestration)

- Tool calling
- Agent avec raisonnement
- Planning multi-step
- RAG vectoriel

**Moyen terme** : Phase 3 (UX)

- Terminal UI
- API REST
- Interface web

**Long terme** : Phase 4 (Production)

- CI/CD
- Audit sécurité
- Performance

---

**Dernière modification** : 2026-02-21 (Phase 1.1 Ollama complete)

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
├── PROMPT_EVA                                                          ✅
├── pyproject.toml                                                      ✅
├── README.md                                                           ✅
├── ROADMAP.md                                                          ✅
│
├── data/ # TOUTE persistance ici                                       ✅
│   ├── logs/ # Logs runtime                                            ✅
│   ├── memory/ # Mémoire conversationnelle                             ✅
│   ├── cache/ # Cache LLM / embeddings                                 ✅
│   ├── prompts/ # Templates de prompts                                 ✅
│   └── dumps/ # Exports / snapshots debug                              ✅
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
│   └── JOURNAL.md                                                      ✅
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
│   │   └── agent_base.py # R-020
│   │
│   ├── conversation/                                                   ✅
│   │   ├── __init__.py                                                 ✅
│   │   └── conversation_engine.py # R-014                              ✅
│   │
│   ├── core/                                                           ✅
│   │   ├── __init__.py                                                 ✅
│   │   ├── eva_component.py # R-005 : Base class universelle           ✅
│   │   ├── config_manager.py # R-003 : Config centralisée              ✅
│   │   ├── event_bus.py # R-004 : Bus d'événements                     ✅
│   │   ├── eva_engine.py # R-006 : Pipeline principal                  ✅
│   │   ├── logging_manager.py # R-009                                  ✅
│   │   └── version_manager.py # R-010                                  ✅
│   │
│   ├── data/                                                           ✅
│   │   ├── memory/                                                     ✅
│   │   │   └── conversation.json                                       ✅
│   │   └── prompts/                                                    ✅
│   │       ├── system_concise.txt                                      ✅
│   │       └── system.txt                                              ✅
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
│   │   ├── plugin_loader.py # R-015                                    ✅
│   │   ├── plugin_base.py # R-015                                      ✅
│   │   └── plugin_registry.py # R-015                                  ✅
│   │
│   ├── prompt/                                                         ✅
│   │   ├── __init__.py                                                 ✅
│   │   └── prompt_manager.py # R-013                                   ✅
│   │
│   └── ui/                                                             ✅
│       ├── __init__.py                                                 ✅
│       └── terminal_ui.py # R-030 : Point d'émission logs UI
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
        ├── test_config_manager.py # R-003a                             ✅
        ├── test_conversation_engine.py # R-014                         ✅
        ├── test_eva_component.py # R-005                               ✅
        ├── test_eva_engine.py # R-006                                  ✅
        ├── test_event_bus.py # R-004                                   ✅
        ├── test_llm_client.py # R-012                                  ✅
        ├── test_logging_manager.py # R-009                             ✅
        ├── test_memory_manager.py # R-018                              ✅
        ├── test_plugin_loader.py # R-018                               ✅
        ├── test_plugins.py # R-018                                     ✅
        ├── test_prompt_manager.py # R-013                              ✅
        ├── test_secrets.py # R-003b                                    ✅
        └── test_version_manager.py # R-010                             ✅

```
