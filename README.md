# EVA — Assistant IA Personnel Modulaire

EVA est un assistant IA local, extensible et testable, conçu comme un véritable projet logiciel — pas comme un simple script.

---

## 📌 Statut du Projet

| Indicateur       | Valeur                        |
| ---------------- | ----------------------------- |
| **Version**      | 0.2.0-p2                      |
| **Phase**        | 3 en cours 🔄 (R-033 ✅)       |
| **Tests**        | 445 (≈95% coverage, ~27s)     |
| **Provider**     | Ollama local (gratuit)        |
| **Python**       | 3.9 strict                    |

---

## ✨ Fonctionnalités

### 💬 Conversation
- Dialogue multi-tours avec mémoire contextuelle persistante
- Fenêtre de contexte configurable
- Prompt système personnalisable (templates `.txt`)

### 🔧 Tool Calling
- Système de tools complet (`ToolDefinition`, `ToolRegistry`, `ToolExecutor`)
- `@tool` decorator pour créer des tools en une ligne
- 4 demo tools : `get_time`, `calc`, `list_plugins`, `get_status`
- Architecture provider-agnostic (Ollama JSON + OpenAI natif)

### 🤖 Agent Autonome
- `AgentBase` : boucle **ReAct** (Reason → Act → Observe)
- Exécution autonome d'un goal jusqu'à réponse finale
- Traçabilité complète des steps (`AgentResult`, `AgentStep`)
- Limite configurable (`agent.max_steps`, défaut 10)

### 🧠 Mémoire Vectorielle (RAG)
- `TextChunker` : découpage texte avec overlap configurable
- `EmbeddingsProvider` : interface abstraite (Fake offline + Local sentence-transformers)
- `CosineSimilarity` : recherche par similarité vectorielle
- `VectorStorage` : persistence atomique (`.json` + `.npz`)
- `VectorMemory` : orchestrateur complet (lifecycle + events)

### 🧩 Plugins
- Loader dynamique avec auto-discovery
- Registry central avec isolation des erreurs
- Convention simple : `get_plugin(config, event_bus) → PluginBase`

### 🏗️ Architecture Core
- `EvaComponent` : classe de base universelle (lifecycle + injection)
- `EventBus` : communication découplée (pub/sub synchrone)
- `ConfigManager` : YAML + dotenv + secrets
- `LoggingManager` : logs structurés avec rotation
- `EVAEngine` : orchestrateur central du pipeline

---

## 🚀 Installation

```bash
# Cloner le dépôt
git clone <repo> && cd EVA

# Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Installer en mode développement
pip install -e ".[dev]"
```

**Prérequis** : [Ollama](https://ollama.com) installé et démarré avec `llama3.2:latest`

```bash
ollama pull llama3.2
ollama serve
```

---

## 💻 Usage

```bash
# Lancer EVA en mode interactif
eva

# Commandes disponibles dans le REPL
/start    # Démarrer la session
/status   # Statut du système
/new      # Nouvelle conversation
/prompt   # Changer le prompt système
/config   # Voir la configuration
/help     # Aide
/quit     # Quitter
```

---

## 🏛️ Architecture

```
EVA/
├── eva/                    # Package principal
│   ├── agents/             # Agents autonomes (ReAct)
│   ├── conversation/       # Pipeline conversationnel
│   ├── core/               # Fondations (Config, EventBus, Engine...)
│   ├── llm/                # Clients LLM + providers
│   ├── memory/             # Mémoire conversationnelle
│   ├── plugins/            # Système de plugins
│   ├── prompt/             # Templates de prompts
│   ├── rag/                # Mémoire vectorielle (RAG)
│   └── tools/              # Tool calling system
├── plugins/                # Plugins tiers / custom
├── data/                   # Runtime (logs, memory, cache)
├── tests/                  # Suite de tests
└── docs/                   # Documentation détaillée
```

**Providers LLM supportés** : Ollama · OpenAI · Anthropic · Groq

---

## 🧪 Tests

```bash
# Suite complète
pytest

# Tests unitaires uniquement
pytest tests/unit/

# Tests d'un module
pytest tests/unit/test_agent_base.py -v
```

| Métrique       | Valeur  |
| -------------- | ------- |
| Tests totaux   | 445     |
| Durée          | ~27s    |
| Coverage       | ~95%    |

---

## 📊 Roadmap

| Phase     | Statut      | Contenu                              |
| --------- | ----------- | ------------------------------------ |
| Phase 0   | ✅ Complète | Fondations (Config, EventBus, Engine) |
| Phase 1   | ✅ Complète | Conversation, LLM, Prompts, Plugins  |
| Phase 1.1 | ✅ Complète | Provider Ollama local                |
| Phase 2   | ✅ Complète | Tool Calling, Agent ReAct, RAG       |
| Phase 3   | 🔄 En cours | CLI avancé ✅, Terminal UI, API REST  |
| Phase 4   | ⏳ À venir  | CI/CD, Audit, Performance            |

---

## 📚 Documentation

| Fichier               | Contenu                              |
| --------------------- | ------------------------------------ |
| `ROADMAP.md`          | Feuille de route détaillée           |
| `docs/ARCHITECTURE.md`| Design global et composants          |
| `docs/JOURNAL.md`     | Historique des décisions techniques  |
| `docs/CHANGELOG.md`   | Modifications par version            |
| `docs/DEBT.md`        | Dettes techniques tracées            |

---

## ⚙️ Stack Technique

- **Runtime** : Python 3.9
- **LLM local** : Ollama (`llama3.2:latest`)
- **Embeddings** : sentence-transformers (`all-MiniLM-L6-v2`)
- **Config** : YAML + python-dotenv
- **Tests** : pytest + coverage
- **Packaging** : pyproject.toml (PEP 517/518)
