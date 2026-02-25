# MANIFEST.md

Inventaire complet des fichiers du projet EVA.

Dernière mise à jour : 2026-02-25 (R-024 RAG)

---

## 📁 Structure Racine

| Fichier            | Rôle                                |
| ------------------ | ----------------------------------- |
| `README.md`        | Documentation principale            |
| `ARCHITECTURE.md`  | Design decisions, principes         |
| `PHASES.md`        | Plan développement par phases       |
| `CONTRACTS.md`     | Contrats techniques par requirement |
| `DEBT.md`          | Dette technique trackée             |
| `MANIFEST.md`      | Ce fichier - inventaire complet     |
| `CHANGELOG.md`     | Historique des versions             |
| `.gitignore`       | Fichiers exclus de Git              |
| `requirements.txt` | Dépendances Python                  |
| `pytest.ini`       | Configuration pytest                |
| `conftest.py`      | Fixtures pytest globales            |

---

## 📦 eva/ — Code Source Principal

### eva/core/ — Composants Système

| Fichier              | Rôle                      | Tests                     |
| -------------------- | ------------------------- | ------------------------- |
| `__init__.py`        | Exports core              | -                         |
| `eva_component.py`   | Classe base composants    | `test_eva_component.py`   |
| `config_manager.py`  | Configuration centralisée | `test_config_manager.py`  |
| `event_bus.py`       | Bus événements            | `test_event_bus.py`       |
| `logging_manager.py` | Logging structuré         | `test_logging_manager.py` |
| `eva_engine.py`      | Moteur principal EVA      | `test_eva_engine.py`      |

### eva/conversation/ — Gestion Conversations

| Fichier                  | Rôle                        | Tests                                                       |
| ------------------------ | --------------------------- | ----------------------------------------------------------- |
| `__init__.py`            | Exports conversation        | -                                                           |
| `conversation_engine.py` | Orchestration conversations | `test_conversation_engine.py`, `test_conversation_tools.py` |

### eva/llm/ — Clients LLM

| Fichier                        | Rôle                  | Tests                     |
| ------------------------------ | --------------------- | ------------------------- |
| `__init__.py`                  | Exports LLM           | -                         |
| `llm_client.py`                | Classe base LLM       | `test_llm_client.py`      |
| `providers/`                   | Providers spécifiques | -                         |
| `providers/__init__.py`        | Exports providers     | -                         |
| `providers/openai_provider.py` | Provider OpenAI       | `test_llm_client.py`      |
| `providers/ollama_provider.py` | Provider Ollama       | `test_ollama_provider.py` |

### eva/memory/ — Gestion Mémoire

| Fichier             | Rôle                     | Tests                    |
| ------------------- | ------------------------ | ------------------------ |
| `__init__.py`       | Exports memory           | -                        |
| `memory_manager.py` | Historique conversations | `test_memory_manager.py` |

### eva/prompt/ — Templates Prompts

| Fichier             | Rôle              | Tests                    |
| ------------------- | ----------------- | ------------------------ |
| `__init__.py`       | Exports prompt    | -                        |
| `prompt_manager.py` | Gestion templates | `test_prompt_manager.py` |

### eva/tools/ — Système Tools (R-020)

| Fichier              | Rôle                     | Tests                |
| -------------------- | ------------------------ | -------------------- |
| `__init__.py`        | Exports tools            | -                    |
| `tool_definition.py` | Dataclass ToolDefinition | `test_tools.py`      |
| `tool_registry.py`   | Registry tools           | `test_tools.py`      |
| `decorator.py`       | Decorator @tool          | `test_tools.py`      |
| `tool_executor.py`   | Exécuteur tools          | `test_tools.py`      |
| `demo_tools.py`      | 4 tools démo             | `test_demo_tools.py` |

**Nouveauté R-020** :

- ToolDefinition.to_openai_function() pour OpenAI adapter
- ToolExecutor.execute() avec timeout et error handling
- @tool decorator pour création simple
- 4 demo tools fonctionnels

### eva/rag/ — Mémoire Vectorielle RAG (R-024)

| Fichier                  | Rôle                                    | Tests                     |
| ------------------------ | --------------------------------------- | ------------------------- |
| `__init__.py`            | Exports RAG                             | -                         |
| `chunker.py`             | TextChunker (sliding window par chars)  | `test_chunker.py`         |
| `embeddings_provider.py` | Interface + Fake + Local (ST)           | `test_embeddings.py`      |
| `similarity_engine.py`   | Interface + CosineSimilarity            | `test_similarity.py`      |
| `storage.py`             | VectorStorage (JSON + NPZ, atomique)    | `test_storage.py`         |
| `vector_memory.py`       | VectorMemory (orchestrateur principal)  | `test_vector_memory.py`   |

**Nouveauté R-024** :

- Pipeline RAG complet : chunk → embed → store → search
- FakeEmbeddingProvider : hash SHA256 → seed RNG → vecteur déterministe (tests 100% offline)
- VectorStorage : persistence atomique (index.json + index.npz, write-tmp-then-rename)
- VectorMemory : hérite EvaComponent, events observabilité, persistence transparente

### eva/plugins/ — Système Plugins

| Fichier               | Rôle                   | Tests                      |
| --------------------- | ---------------------- | -------------------------- |
| `__init__.py`         | Exports plugins        | -                          |
| `plugin_interface.py` | Interface base plugins | `test_plugin_interface.py` |
| `plugin_registry.py`  | Registry plugins       | `test_plugin_registry.py`  |

### eva/utils/ — Utilitaires

| Fichier         | Rôle            | Tests                |
| --------------- | --------------- | -------------------- |
| `__init__.py`   | Exports utils   | -                    |
| `secrets.py`    | Gestion secrets | `test_secrets.py`    |
| `validators.py` | Validateurs     | `test_validators.py` |

### eva/ — Autres

| Fichier       | Rôle                     | Tests          |
| ------------- | ------------------------ | -------------- |
| `__init__.py` | Exports racine           | -              |
| `repl.py`     | Interface ligne commande | `test_repl.py` |

---

## 🧪 tests/ — Tests

### tests/unit/ — Tests Unitaires

| Fichier                       | Cible              | Tests                      |
| ----------------------------- | ------------------ | -------------------------- |
| `test_eva_component.py`       | EvaComponent       | 13 tests                   |
| `test_config_manager.py`      | ConfigManager      | 8 tests                    |
| `test_event_bus.py`           | EventBus           | 13 tests                   |
| `test_logging_manager.py`     | LoggingManager     | 10 tests (9 xfail)         |
| `test_eva_engine.py`          | EVAEngine          | 10 tests                   |
| `test_conversation_engine.py` | ConversationEngine | 30 tests (plusieurs xfail) |
| `test_conversation_tools.py`  | Tools integration  | 4 tests                    |
| `test_llm_client.py`          | LLMClient          | 12 tests                   |
| `test_ollama_provider.py`     | OllamaProvider     | 7 tests                    |
| `test_memory_manager.py`      | MemoryManager      | 14 tests                   |
| `test_prompt_manager.py`      | PromptManager      | 14 tests                   |
| `test_tools.py`               | Tool system        | 33 tests                   |
| `test_demo_tools.py`          | Demo tools         | 8 tests                    |
| `test_plugin_interface.py`    | PluginInterface    | 8 tests                    |
| `test_plugin_registry.py`     | PluginRegistry     | 12 tests                   |
| `test_secrets.py`             | Secrets            | 3 tests (1 xfail)          |
| `test_validators.py`          | Validators         | 4 tests                    |
| `test_repl.py`                | REPL               | 10 tests                   |

### tests/unit/ — Tests RAG (R-024)

| Fichier                    | Cible                | Tests                  |
| -------------------------- | -------------------- | ---------------------- |
| `conftest.py`              | Fixtures partagées   | -                      |
| `test_chunker.py`          | TextChunker          | 9                      |
| `test_embeddings.py`       | EmbeddingsProvider   | 12                     |
| `test_similarity.py`       | CosineSimilarity     | 7                      |
| `test_storage.py`          | VectorStorage        | 10                     |
| `test_vector_memory.py`    | VectorMemory         | 13                     |
| `test_rag_integration.py`  | Integration RAG      | 4                      |

### tests/smoke/ — Tests Smoke

| Fichier         | Rôle                                   |
| --------------- | -------------------------------------- |
| `test_smoke.py` | Tests intégration end-to-end (2 xfail) |

### tests/ — Configuration

| Fichier       | Rôle                      |
| ------------- | ------------------------- |
| `conftest.py` | Fixtures pytest partagées |

---

## 📂 eva/data/ — Données Runtime (gitignored)

| Répertoire | Rôle                |
| ---------- | ------------------- |
| `logs/`    | Fichiers logs       |
| `memory/`  | Persistence mémoire |
| `cache/`   | Cache temporaire    |
| `prompts/` | Templates prompts   |
| `dumps/`   | Debug dumps         |

---

## 📚 docs/ — Documentation

| Fichier | Rôle                    |
| ------- | ----------------------- |
| `*.md`  | Documentation technique |

---

## 📊 Métriques Projet

**Code Production** :

- ~3500 lignes Python (+500 depuis R-024 RAG)
- 10 modules principaux (+1 eva/rag/)
- 55+ composants

**Tests** :

- ~320 tests passent ✅ (232 tools + 55 RAG + régression)
- 27 tests xfailed (DEBT-008)
- Couverture : ~95%
- Durée : ~17s

**Phase Actuelle** : Phase 2 ✅ COMPLÈTE (R-020-023-024)

---

**Dernière mise à jour** : 2026-02-25 (R-024 RAG complet)
