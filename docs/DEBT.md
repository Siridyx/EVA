# DEBT — Dettes Techniques

Tracker des dettes techniques identifiées dans EVA.

**Dernière mise à jour** : 2026-02-21

---

## 📊 Vue d'ensemble

| Métrique       | Valeur |
| -------------- | ------ |
| Dettes actives | 8      |
| Dettes P0      | 0      |
| Dettes P1      | 0      |
| Dettes P2      | 8      |
| Effort total   | ~12h   |

---

## 🎯 Principe

**Une dette technique est acceptable SI** :

- Trackée et documentée
- Datée et assignée à une phase
- Non bloquante pour phase actuelle
- Estimée (effort + impact)

**Critères de priorisation** :

- **P0** : Critique (sécurité, données, corruption)
- **P1** : Important (UX, performance majeure, maintenabilité)
- **P2** : Nice-to-have (polish, optimisation, confort dev)

---

## 📋 Dettes Actives

### [DEBT-001] Async EventBus (P2)

- **Priorité** : P2 (nice-to-have)
- **Phase** : Phase 2 (Agents)
- **Effort** : M (~4h)
- **Impact** : Performance améliorée sur événements longs
- **Description** :
  - EventBus actuellement synchrone (P0 MVP)
  - Async permettrait handlers longs sans bloquer
  - Utile pour agents avec I/O réseau
  - API doit rester compatible (rétrocompatibilité)
- **Fichiers concernés** :
  - `eva/core/event_bus.py`
  - Tous les handlers (migration optionnelle)
- **Rationale** :
  - P0 : Synchrone suffit (pas d'I/O lourds)
  - P2 : Agents feront appels réseau (LLM, tools, APIs)
  - Migration simple : `async def handler()` + `await bus.emit()`
- **Créé** : 2026-02-17 (R-003)

---

### [DEBT-002] Pipeline Parallèle (P2)

- **Priorité** : P2 (nice-to-have)
- **Phase** : Phase 2 (Agents)
- **Effort** : L (~6h)
- **Impact** : Performance multi-agents
- **Description** :
  - EVAEngine pipeline mode = "sequential" (P0)
  - Mode "parallel" permettrait exécution concurrente
  - Utile pour multi-agents indépendants
  - Coordination nécessaire (locks, state)
- **Fichiers concernés** :
  - `eva/core/eva_engine.py`
  - Components lifecycle (thread-safety)
- **Rationale** :
  - P0/P1 : Un seul agent conversationnel (sequential OK)
  - P2 : Multi-agents (planificateur + exécuteurs)
  - Besoin orchestration sophisticated
- **Note** : Évaluer asyncio vs threading vs multiprocessing
- **Créé** : 2026-02-17 (R-006)

---

### [DEBT-003] Test Hardening Avancé (P2)

**Voir R-045 dans ROADMAP.md**

- **Priorité** : P2 (qualité)
- **Phase** : Phase 4 (Quality)
- **Effort** : M (~3h)
- **Impact** : Tests plus robustes et maintenables
- **Description** :
  - Timeouts courts : déjà fait (R-018) ✅
  - Network guard : DEBT-004 (R-045)
  - Pytest markers : DEBT-005 (R-045)
  - Test data factories (si besoin)
  - Property-based testing (hypothesis) (optionnel)
- **Fichiers concernés** :
  - `tests/conftest.py`
  - `pyproject.toml` ([tool.pytest.ini_options])
  - Tous les tests (markers)
- **Rationale** :
  - R-018 a couvert isolation I/O + timeouts (MVP suffit)
  - Network guard complexe avec MockTransport
  - Markers utiles pour CI/CD (run sélectifs)
- **Créé** : 2026-02-17 (R-008), mis à jour 2026-02-19 (R-018)

---

### [DEBT-004] Network Guard pytest (R-018 → R-045)

- **Priorité** : P2 (non-bloquant)
- **Phase** : Phase 4 Qualité (R-045)
- **Effort** : S (~2h)
- **Impact** : Sécurité tests + détection fuites réseau
- **Description** :
  - Bloquer tout accès réseau réel en tests unit
  - Autoriser uniquement via mocks (MockTransport)
  - Exception pour tests marqués `@pytest.mark.integration`
  - Détecter automatiquement appels réseau accidentels
- **Fichiers concernés** :
  - `tests/conftest.py` (fixture block_network)
  - Guard via monkeypatch socket.socket
- **Rationale** :
  - Tests actuels : 216 passent en 10.35s (acceptable P1)
  - MockTransport couvre déjà 99% des cas
  - Guard fin nécessite analyse précise des edge cases
- **Lien** : Sera implémenté dans R-045 (Phase 4)
- **Créé** : 2026-02-19 (R-018)

---

### [DEBT-005] Pytest markers unit/integration (R-018 → R-045)

- **Priorité** : P2 (non-bloquant)
- **Phase** : Phase 4 Qualité (R-045)
- **Effort** : XS (~1h)
- **Impact** : Organisation tests + CI/CD optimisée
- **Description** :
  - Ajouter markers dans `pyproject.toml` (unit, integration, smoke)
  - Tagger tests existants selon leur nature
  - Permettre runs sélectifs : `pytest -m unit`, `pytest -m integration`
  - Faciliter CI/CD (unit rapides, integration plus longs)
- **Fichiers concernés** :
  - `pyproject.toml` ([tool.pytest.ini_options])
  - Tous les tests (ajout decorators)
- **Rationale** :
  - Tests actuels : organisation implicite via dossiers (unit/, smoke/)
  - Markers explicites = meilleure lisibilité + flexibilité
  - Pas bloquant pour P1 (structure actuelle suffit)
- **Lien** : Sera implémenté dans R-045 (Phase 4)
- **Créé** : 2026-02-19 (R-018)

---

### [DEBT-006] Provider Groq (Cloud gratuit)

- **Priorité** : P2 (nice-to-have)
- **Phase** : Phase 2
- **Effort** : XS (~1h)
- **Impact** : Alternative cloud gratuite à Ollama
- **Description** :
  - Provider Groq pour LLM cloud gratuit/limité
  - API compatible OpenAI
  - Modèles : llama, mixtral, gemma
  - Rate limits mais gratuit
- **Fichiers concernés** :
  - `eva/llm/providers/groq_provider.py` (nouveau)
  - `eva/config.yaml` (section groq)
- **Rationale** :
  - Ollama local suffit pour P1.1
  - Groq utile pour users sans GPU
  - Déjà compatible OpenAI API (implémentation rapide)
- **Créé** : 2026-02-21 (R-012b)

---

### [DEBT-007] Provider Anthropic (Claude)

- **Priorité** : P2 (nice-to-have)
- **Phase** : Phase 2+
- **Effort** : S (~2h)
- **Impact** : Support modèles Claude (qualité supérieure)
- **Description** :
  - Provider Anthropic pour Claude 3/4
  - API key requise (payant)
  - Meilleure qualité que GPT sur certaines tâches
- **Fichiers concernés** :
  - `eva/llm/providers/anthropic_provider.py` (nouveau)
  - `eva/config.yaml` (section anthropic)
- **Rationale** :
  - Ollama + OpenAI suffisent pour P1
  - Claude excellent pour raisonnement complexe
  - Implémentation similaire OpenAI
- **Créé** : 2026-02-21 (R-012b)

---

### [DEBT-008] Tests suite cleanup (30 tests restants)

- **Priorité** : P2 (qualité)
- **Phase** : Phase 4 (Qualité)
- **Effort** : M (~3h)
- **Impact** : 100% tests verts (actuellement 88%)
- **Description** :
  - 30 tests échouent suite modifications Phase 1.1/R-020
  - Catégories :
    - **Prompts invalides** : 17 tests ConversationEngine utilisent prompts avec `{{missing_var}}`
    - **Paths data/** : 9 tests LoggingManager tentent d'écrire dans data/ réel (hors tmp_path)
    - **Events manquants** : 3 tests attendent anciens events (conversation_request_received, etc.)
    - **Divers** : 1 test .env.example
- **Fichiers concernés** :
  - `tests/unit/test_conversation_engine.py` (17 tests)
  - `tests/unit/test_logging_manager.py` (9 tests)
  - `tests/smoke/test_smoke.py` (2 tests)
  - `tests/unit/test_eva_component.py` (1 test)
  - `tests/unit/test_secrets.py` (1 test)
- **Plan de résolution** :
  - **Prompts** : Créer fixture `valid_prompts` avec system.txt sans placeholders manquants
  - **Logging** : LoggingManager doit créer parent directories avant FileHandler
  - **Events** : Supprimer tests d'events obsolètes ou mettre à jour events émis
  - **Paths** : Tous tests doivent utiliser tmp_path (déjà couvert par conftest normalement)
- **Rationale** :
  - 88% tests verts = acceptable pour Phase 2 (MVP tools)
  - Fix complet = Phase 4 (Quality)
  - Tests tools (33) passent tous ✅
- **Créé** : 2026-02-22 (R-020 Step 6)

---

## 📜 Dettes Résolues

Aucune pour l'instant (toutes les dettes actives).

---

## 🎯 Règles de Gestion

### Création Dette

**Quand créer une dette ?**

- Feature non-critique omise volontairement
- Optimisation reportée (perf acceptable)
- Refactoring nécessaire mais non urgent
- Polish UX non bloquant

**Quand NE PAS créer de dette ?**

- Bug critique (fix immédiat)
- Sécurité (fix immédiat)
- Corruption données (fix immédiat)
- Bloquant phase actuelle (résoudre maintenant)

### Résolution Dette

**Critères de résolution** :

- Code implémenté et testé
- Documentation mise à jour
- Dette marquée "Résolue" avec date
- Issue/PR référencée (si applicable)

### Review Régulière

**Fréquence** : À chaque fin de phase

- Réévaluer priorités
- Archiver dettes obsolètes
- Identifier nouvelles dettes
- Mettre à jour estimations

---

**Dernière review** : 2026-02-21 (Fin Phase 1.1)
