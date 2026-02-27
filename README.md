# EVA — Assistant IA Personnel Modulaire

EVA est un assistant IA local, extensible et testable, conçu comme un véritable projet logiciel — pas comme un simple script.

---

## 📌 Statut du Projet

| Indicateur       | Valeur                        |
| ---------------- | ----------------------------- |
| **Version**      | 0.3.0                         |
| **Phase**        | 3 ✅ COMPLÈTE — Phase 4 en cours |
| **Tests**        | 495 (≈95% coverage, ~15s)     |
| **Provider**     | Ollama local (gratuit)        |
| **Python**       | 3.9 – 3.12 (CI : 3.9 + 3.11) |
| **Licence**      | Propriétaire — All rights reserved |

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

### 🌐 API REST (FastAPI)
- `GET /health`, `GET /status`, `POST /chat` — 3 endpoints
- Docs auto Swagger : `http://localhost:8000/docs`
- Lancement : `eva --api`
- Appels LLM non-bloquants (`asyncio.to_thread`)

### 🖥️ Terminal UI (Textual)
- `EvaTuiApp` : interface graphique en terminal (`eva --tui`)
- Layout split : chat scrollable 70% / sidebar statut 30%
- Appels LLM non-bloquants (worker thread) — UI toujours réactive
- Tab autocomplete + Ctrl+Q quit + F1 aide + Ctrl+L clear
- Thème sombre cyan/bleu

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
```

**Install selon le besoin** (les extras sont optionnels) :

```bash
# Core seul — REPL conversationnel uniquement (minimal)
pip install -e .

# Développement complet — core + tests + lint
pip install -e ".[dev]"

# API REST FastAPI
pip install -e ".[api]"

# Terminal UI Textual
pip install -e ".[tui]"

# Mémoire vectorielle (RAG — lourd : PyTorch + transformers)
pip install -e ".[rag]"

# Tout + développement (CI complète)
pip install -e ".[dev,api,tui,rag]"
```

**Prérequis** : [Ollama](https://ollama.com) installé et démarré avec `llama3.2:latest`

```bash
ollama pull llama3.2
ollama serve
```

---

## 💻 Usage

```bash
# REPL interactif (défaut)
eva

# Terminal UI graphique (Textual)
eva --tui

# API REST (FastAPI — http://localhost:8000)
eva --api

# Interface web browser (FastAPI + UI vanilla — http://localhost:8000)
eva --web

# Commandes disponibles dans le REPL
/start    # Démarrer la session
/status   # Statut du système
/new      # Nouvelle conversation
/config   # Voir la configuration (ou /config get KEY)
/clear    # Effacer l'écran
/help     # Aide
/quit     # Quitter (/exit, /q)
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
│   ├── tools/              # Tool calling system
│   ├── ui/                 # Command Registry + TUI
│   │   └── tui/            # Terminal UI Textual (R-030)
│   ├── api/                # API REST FastAPI (R-031)
│   └── web/                # Interface web légère (R-032)
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
| Tests totaux   | 495     |
| Durée          | ~15s    |
| Coverage       | ~95%    |

---

## 📊 Roadmap

| Phase     | Statut      | Contenu                              |
| --------- | ----------- | ------------------------------------ |
| Phase 0   | ✅ Complète | Fondations (Config, EventBus, Engine) |
| Phase 1   | ✅ Complète | Conversation, LLM, Prompts, Plugins  |
| Phase 1.1 | ✅ Complète | Provider Ollama local                |
| Phase 2   | ✅ Complète | Tool Calling, Agent ReAct, RAG       |
| Phase 3   | ✅ Complète | CLI avancé, TUI, API REST, Interface web |
| Phase 4   | 🔄 En cours | Packaging, CI/CD, Audit, Performance |

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
- **CI** : GitHub Actions (lint flake8 + pytest, Python 3.9 + 3.11)

---

## 📄 Licence

Copyright (c) 2024-2026 Siridyx. **All rights reserved.**

Ce logiciel est propriétaire. Toute reproduction, distribution ou usage commercial sans autorisation écrite préalable est interdite. Voir le fichier [LICENSE](LICENSE) pour les détails complets.
