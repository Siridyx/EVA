"""Test integration RAG + ConversationEngine"""

import pytest
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.memory.memory_manager import MemoryManager
from eva.prompt.prompt_manager import PromptManager
from eva.rag.vector_memory import VectorMemory
from eva.rag.chunker import TextChunker
from eva.rag.embeddings_provider import FakeEmbeddingProvider
from eva.rag.similarity_engine import CosineSimilarity
from eva.rag.storage import VectorStorage


class MockLLM:
    """Mock LLM pour tests."""
    
    def __init__(self):
        self.responses = ["Réponse test avec contexte RAG."]
        self.call_count = 0
        self.last_messages = []
    
    def complete(self, messages, profile="default", tools=None):
        self.last_messages = messages
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response


def test_rag_end_to_end(tmp_path, config, event_bus):
    """Test end-to-end RAG : add + search + retrieve."""
    # Setup components
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    embeddings = FakeEmbeddingProvider(embedding_dim=128)
    similarity = CosineSimilarity()
    storage = VectorStorage(str(tmp_path / "vectors"))
    
    vector_memory = VectorMemory(
        config, event_bus, chunker, embeddings, similarity, storage
    )
    vector_memory.start()
    
    # 1. Add documents
    vector_memory.add_document(
        "RAG means Retrieval-Augmented Generation. It combines retrieval and generation.",
        {"source": "rag_intro.txt"}
    )
    vector_memory.add_document(
        "Vector databases store embeddings for similarity search.",
        {"source": "vectors.txt"}
    )
    vector_memory.add_document(
        "Python is a programming language used for AI.",
        {"source": "python.txt"}
    )
    
    # 2. Search
    results = vector_memory.search("What is RAG?", top_k=2)
    
    # Vérifie résultats
    assert len(results) > 0
    assert len(results) <= 2
    
    # Vérifie format
    result = results[0]
    assert "doc_id" in result
    assert "chunk_id" in result
    assert "text" in result
    assert "metadata" in result
    assert "score" in result
    
    # Vérifie tri (décroissant)
    if len(results) > 1:
        assert results[0]["score"] >= results[1]["score"]
    
    # Vérifie score valide
    assert 0.0 <= result["score"] <= 1.0
    
    # 3. Persistence
    vector_memory.stop()
    
    # 4. Reload
    vector_memory2 = VectorMemory(
        config, event_bus, chunker, embeddings, similarity, storage
    )
    vector_memory2.start()
    
    # Vérifie documents chargés
    assert len(vector_memory2._documents) > 0
    
    # Search fonctionne
    results2 = vector_memory2.search("embeddings", top_k=1)
    assert len(results2) > 0


def test_rag_with_conversation_engine_mock(tmp_path, config, event_bus, memory, prompt):
    """Test RAG avec ConversationEngine (mock integration)."""
    # Setup RAG
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    embeddings = FakeEmbeddingProvider(embedding_dim=128)
    similarity = CosineSimilarity()
    storage = VectorStorage(str(tmp_path / "vectors"))
    
    vector_memory = VectorMemory(
        config, event_bus, chunker, embeddings, similarity, storage
    )
    vector_memory.start()
    
    # Add knowledge
    vector_memory.add_document(
        "EVA is an Extensible Virtual Assistant built with Python.",
        {"source": "eva_intro.md"}
    )
    vector_memory.add_document(
        "RAG enhances LLM responses by retrieving relevant context.",
        {"source": "rag_benefits.md"}
    )
    
    # Mock retrieve_context (ce que ConversationEngine fera)
    query = "What is EVA?"
    results = vector_memory.search(query, top_k=2)
    
    # Format context
    context_lines = ["--- Context from vector memory ---"]
    for i, result in enumerate(results, 1):
        context_lines.append(f"[{i}] {result['text']}")
        context_lines.append(f"    (score: {result['score']:.2f})")
    context_lines.append("--- End context ---")
    
    context = "\n".join(context_lines)
    
    # Vérifie contexte contient info pertinente
    assert "EVA" in context
    assert "score:" in context


def test_rag_empty_query(tmp_path, config, event_bus):
    """search() avec query vide gère gracefully."""
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    embeddings = FakeEmbeddingProvider(embedding_dim=128)
    similarity = CosineSimilarity()
    storage = VectorStorage(str(tmp_path / "vectors"))
    
    vector_memory = VectorMemory(
        config, event_bus, chunker, embeddings, similarity, storage
    )
    vector_memory.start()
    
    vector_memory.add_document("Some text", {})
    
    # Query vide
    results = vector_memory.search("", top_k=3)
    
    # Devrait retourner résultats (embedding vide != crash)
    assert isinstance(results, list)


def test_rag_performance_no_crash(tmp_path, config, event_bus):
    """RAG gère beaucoup de documents sans crash (perf guardrail)."""
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    embeddings = FakeEmbeddingProvider(embedding_dim=128)
    similarity = CosineSimilarity()
    storage = VectorStorage(str(tmp_path / "vectors"))
    
    vector_memory = VectorMemory(
        config, event_bus, chunker, embeddings, similarity, storage
    )
    vector_memory.start()
    
    # Ajouter 50 documents
    for i in range(50):
        vector_memory.add_document(
            f"Document {i} with some content about topic {i % 5}.",
            {"doc_id": f"doc_{i}"}
        )
    
    # Search doit marcher (O(n) OK pour MVP)
    results = vector_memory.search("topic 2", top_k=5)
    
    assert len(results) > 0
    assert len(results) <= 5