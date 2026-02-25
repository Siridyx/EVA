"""Tests pour VectorMemory"""

import pytest
import numpy as np
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.rag.vector_memory import VectorMemory
from eva.rag.chunker import TextChunker
from eva.rag.embeddings_provider import FakeEmbeddingProvider
from eva.rag.similarity_engine import CosineSimilarity
from eva.rag.storage import VectorStorage


@pytest.fixture
def vector_memory(tmp_path, config, event_bus):
    """Fixture VectorMemory avec FakeProvider."""
    # Composants
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    embeddings = FakeEmbeddingProvider(embedding_dim=128)
    similarity = CosineSimilarity()
    storage = VectorStorage(str(tmp_path / "vectors"))
    
    # VectorMemory
    memory = VectorMemory(
        config=config,
        event_bus=event_bus,
        chunker=chunker,
        embeddings=embeddings,
        similarity=similarity,
        storage=storage
    )
    
    return memory


def test_vector_memory_init(vector_memory):
    """Initialisation VectorMemory OK."""
    assert vector_memory.name == "VectorMemory"
    assert not vector_memory.is_running


def test_vector_memory_start_stop(vector_memory):
    """Start/stop VectorMemory OK."""
    vector_memory.start()
    assert vector_memory.is_running
    
    vector_memory.stop()
    assert not vector_memory.is_running


def test_vector_memory_add_document(vector_memory):
    """add_document() ajoute document OK."""
    vector_memory.start()
    
    vector_memory.add_document(
        text="This is a test document about RAG.",
        metadata={"source": "test.txt"}
    )
    
    # Vérifie documents ajoutés
    assert len(vector_memory._documents) > 0


def test_vector_memory_add_document_not_running(vector_memory):
    """add_document() sans start raise RuntimeError."""
    with pytest.raises(RuntimeError, match="not started"):
        vector_memory.add_document("Text", {})


def test_vector_memory_search_empty_index(vector_memory):
    """search() sur index vide retourne []."""
    vector_memory.start()
    
    results = vector_memory.search("query", top_k=3)
    
    assert results == []


def test_vector_memory_search_results(vector_memory):
    """search() retourne résultats triés."""
    vector_memory.start()
    
    # Ajouter documents
    vector_memory.add_document(
        text="RAG means Retrieval-Augmented Generation.",
        metadata={"source": "doc1.txt"}
    )
    vector_memory.add_document(
        text="Python is a programming language.",
        metadata={"source": "doc2.txt"}
    )
    
    # Search
    results = vector_memory.search("What is RAG?", top_k=2)
    
    # Vérifie format
    assert len(results) <= 2
    
    if len(results) > 0:
        result = results[0]
        
        # Clés obligatoires
        assert "doc_id" in result
        assert "chunk_id" in result
        assert "text" in result
        assert "metadata" in result
        assert "score" in result
        
        # Score valide
        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 1.0


def test_vector_memory_search_sorted_descending(vector_memory):
    """search() résultats triés décroissant par score."""
    vector_memory.start()
    
    # Ajouter documents
    for i in range(5):
        vector_memory.add_document(f"Document {i}", {"id": i})
    
    results = vector_memory.search("Document 2", top_k=5)
    
    # Vérifier tri décroissant
    if len(results) > 1:
        for i in range(len(results) - 1):
            assert results[i]["score"] >= results[i+1]["score"]


def test_vector_memory_search_top_k(vector_memory):
    """search() respecte top_k."""
    vector_memory.start()
    
    # Ajouter 10 documents
    for i in range(10):
        vector_memory.add_document(f"Document {i}", {"id": i})
    
    results = vector_memory.search("query", top_k=3)
    
    assert len(results) <= 3


def test_vector_memory_search_not_running(vector_memory):
    """search() sans start raise RuntimeError."""
    with pytest.raises(RuntimeError, match="not started"):
        vector_memory.search("query")


def test_vector_memory_clear(vector_memory):
    """clear() vide index."""
    vector_memory.start()
    
    # Ajouter document
    vector_memory.add_document("Text", {})
    assert len(vector_memory._documents) > 0
    
    # Clear
    vector_memory.clear()
    
    assert len(vector_memory._documents) == 0
    assert vector_memory._vectors is None


def test_vector_memory_persistence(tmp_path, config, event_bus):
    """Index persisté et rechargé OK."""
    # Setup
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    embeddings = FakeEmbeddingProvider(embedding_dim=128)
    similarity = CosineSimilarity()
    storage = VectorStorage(str(tmp_path / "vectors"))
    
    # Memory 1 : ajouter documents
    memory1 = VectorMemory(config, event_bus, chunker, embeddings, similarity, storage)
    memory1.start()
    memory1.add_document("Document A", {"source": "A"})
    memory1.add_document("Document B", {"source": "B"})
    memory1.stop()
    
    # Memory 2 : load index
    memory2 = VectorMemory(config, event_bus, chunker, embeddings, similarity, storage)
    memory2.start()
    
    # Vérifie documents chargés
    assert len(memory2._documents) > 0
    
    # Search fonctionne
    results = memory2.search("Document A", top_k=1)
    assert len(results) > 0


def test_vector_memory_events(vector_memory, event_bus):
    """Events émis correctement."""
    events_received = []

    event_bus.on("vector_document_added", lambda p: events_received.append("vector_document_added"))
    event_bus.on("vector_search_performed", lambda p: events_received.append("vector_search_performed"))
    
    vector_memory.start()
    vector_memory.add_document("Text", {})
    vector_memory.search("query", top_k=1)
    
    assert "vector_document_added" in events_received
    assert "vector_search_performed" in events_received


def test_vector_memory_repr(vector_memory):
    """repr() retourne string valide."""
    repr_str = repr(vector_memory)
    
    assert "VectorMemory" in repr_str
    assert "state" in repr_str
    
    vector_memory.start()
    vector_memory.add_document("Text", {})
    
    repr_str = repr(vector_memory)
    assert "documents=" in repr_str