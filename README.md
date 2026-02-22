# EVA — Assistant IA Personnel Modulaire

EVA est un assistant IA local, extensible et testable, conçu comme un véritable projet logiciel, pas comme un simple script.

Objectif :

- Construire un assistant fiable
- 100% contrôlable
- Évolutif vers agents autonomes
- Qualité industrielle (tests, docs, packaging)

---

## 📌 Statut du Projet

- Version : 0.1.0-dev
- Phase : 1.1 (Intelligence + Ollama)
- État : Stable
- Tests : 216+ (≈95% coverage)
- Runtime : ~10s pour la suite complète

Phase 1 et 1.1 sont terminées.

Phase 2 (Agents) en préparation.

---

## ✨ Fonctionnalités Actuelles

### Conversation

- Dialogue multi-tours
- Mémoire contextuelle persistante
- Fenêtre de contexte configurable
- Prompt système personnalisable

### LLM

- Ollama intégré (local, gratuit)
- Architecture provider-agnostic
- Support futur OpenAI / Groq / Anthropic

### Architecture

- Pipeline modulaire
- Injection explicite
- EventBus central
- Logging structuré
- Versioning interne

### Plugins

- Loader dynamique
- Registry central
- Isolation erreurs
- Plugins extensibles

### Qualité

- Tests unitaires + smoke
- Isolation I/O
- Mode test dédié
- Packaging propre (wheel)

---

## 🏗️ Architecture Résumée
