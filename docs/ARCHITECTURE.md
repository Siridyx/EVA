## EVA — Architecture

Documentation de l'architecture globale du projet EVA.

- Version : 0.1.0-p2
- Dernière mise à jour : 2026-02-25
- Phase : P2 (RAG - 100%)

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

  ***

## Composants P2 — Tool Calling

# Tool System (R-020-023)

- **Architecture** :
  - Provider-agnostic (format interne EVA neutre)
  - Ollama : Prompt engineering + JSON custom
  - OpenAI : Function calling natif

- **Composants** :
  - **ToolDefinition** (dataclass frozen)
    - name, description, function, parameters, returns
    - validate_arguments() avec type checking
    - to_openai_function() pour conversion OpenAI schema
  - **ToolRegistry** (EvaComponent)
    - register(), unregister(), get(), list_tools()
    - get_all_definitions() pour ConversationEngine
    - Events : tool_registered, tool_unregistered, registry_cleared
  - **ToolExecutor** (EvaComponent)
    - execute(tool_name, arguments) avec validation
    - Timeout configurable (30s default)
    - Error handling safe (tool crash ≠ EVA crash)
    - Events : tool_called, tool_result, tool_error
  - **@tool decorator**
    - Création simple tools
    - Auto-génération ToolDefinition
    - Helpers : is_tool(), get_tool_definition()

- **ConversationEngine Integration** :
  - \_detect_tool_call() : Parse JSON `{"action":"tool_call",...}`
  - Workflow 2 LLM calls : detect → execute → reformule
  - Memory persistence (tool calls + results)
  - Event tool_call_detected
  - tools_openai injection si provider supporte

- **Demo Tools** :
  - get_time(city) : Heure dans ville
  - calc(expression) : Calculatrice safe
  - list_plugins() : Liste plugins
  - get_status() : Status EVA

---

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

- P2 (actuel)
  - session unique (multi-conv = future)
  - pas de streaming
  - ✅ tool calling opérationnel
  - ✅ RAG vectoriel opérationnel (R-024)
  - pas de planning multi-step

---

## Composants R-024 — RAG (Retrieval-Augmented Generation)

# VectorMemory

- responsabilité
  - orchestrateur du pipeline RAG complet
  - hérite `EvaComponent` (lifecycle + events)
  - pipeline `add_document()` : chunk → embed → store
  - pipeline `search()` : embed query → similarity → top-k
  - persistence transparente (load au start, save après add)
- events observabilité
  - `vector_document_added` : document ajouté (doc_id, num_chunks, total)
  - `vector_search_performed` : recherche effectuée (query, top_k, num_results)
  - `vector_index_loaded` : index rechargé depuis disque
  - `vector_index_cleared` : index vidé

# TextChunker

- responsabilité
  - découpage texte en chunks avec overlap (sliding window par caractères)
- paramètres
  - `chunk_size` : taille chunk (défaut 500 chars)
  - `chunk_overlap` : overlap entre chunks (défaut 50 chars)
- garanties
  - texte vide → `[]`
  - texte ≤ chunk_size → `[texte]`

# EmbeddingsProvider

- interface abstraite
  - `embed(text)` → `np.ndarray` (normalisé L2)
  - `get_embedding_dim()` → `int`
- implémentations
  - `FakeEmbeddingProvider` : hash SHA256 → seed RNG → vecteur uniforme normalisé
    - 100% offline, déterministe (même texte = même vecteur)
    - Utilisé dans tous les tests unitaires
  - `LocalEmbeddingProvider` : sentence-transformers, lazy load
    - Modèle par défaut : `all-MiniLM-L6-v2` (~80 MB)
    - Cache interne pour éviter re-embed

# CosineSimilarity

- responsabilité
  - calcul similarité cosinus entre query et corpus
  - assume vecteurs déjà normalisés L2 (cosine = dot product)
- complexité : O(n × dim) — acceptable MVP (FAISS prévu P3)
- validation : shapes + dimensions à chaque appel

# VectorStorage

- responsabilité
  - persistence atomique index vectoriel sur disque
  - format : `index.json` (documents + métadonnées) + `index.npz` (vecteurs numpy)
- écriture atomique : write `.tmp` → `rename` (cohérence garantie)
- validation compatibilité : détecte mismatch `model_name` ou `embedding_dim`

---

## 🌊 Flux RAG (R-024)

```
add_document(text, metadata)
    │
    ├─→ TextChunker.chunk(text)
    │       → ["chunk1", "chunk2", ...]
    │
    ├─→ EmbeddingsProvider.embed(chunk_i)
    │       → np.ndarray [embedding_dim]  (normalisé L2)
    │
    ├─→ np.vstack([existing_vectors, new_vectors])
    │
    ├─→ VectorStorage.save(vectors, documents, model, dim)
    │       → index.json + index.npz (atomique)
    │
    └─→ emit("vector_document_added", {doc_id, num_chunks, total})


search(query, top_k)
    │
    ├─→ EmbeddingsProvider.embed(query)
    │       → np.ndarray [embedding_dim]
    │
    ├─→ CosineSimilarity.compute_similarity(query_vec, all_vectors)
    │       → scores [num_docs]  (dot product)
    │
    ├─→ np.argsort(scores)[::-1][:top_k]
    │       → indices triés décroissant
    │
    ├─→ format résultats
    │       → [{"doc_id", "chunk_id", "text", "metadata", "score"}, ...]
    │
    └─→ emit("vector_search_performed", {query, top_k, num_results})
```

---

## 🌊 Flux Tool Calling (Phase 2)

```
User Input (CLI)
    │
    ▼
ConversationEngine.respond(message)
    │
    ├─→ [1-4] (identique Phase 1)
    │
    ├─→ [5] Construire tools_openai si ToolExecutor présent
    │
    ├─→ [6] response = LLMClient.complete(messages, profile, tools=tools_openai)
    │   emit: llm_request_started
    │
    ├─→ [7] tool_call = _detect_tool_call(response)
    │
    ├─→ [8] SI tool_call détecté :
    │   │
    │   ├─→ [8a] emit: tool_call_detected
    │   │
    │   ├─→ [8b] result = ToolExecutor.execute(tool_name, arguments)
    │   │   emit: tool_called, tool_result | tool_error
    │   │
    │   ├─→ [8c] MemoryManager.add_message("assistant", tool_call_json)
    │   │
    │   ├─→ [8d] MemoryManager.add_message("tool", tool_result)
    │   │
    │   ├─→ [8e] messages.append(tool_call + tool_result)
    │   │
    │   └─→ [8f] response = LLMClient.complete(messages, profile, tools=tools_openai)
    │       (reformulation langage naturel)
    │
    ├─→ [9] MemoryManager.add_message("assistant", response)
    │
    └─→ return response
```

---
