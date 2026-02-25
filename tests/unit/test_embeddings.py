"""Tests pour EmbeddingsProvider"""

import pytest
import numpy as np
from eva.rag.embeddings_provider import (
    FakeEmbeddingProvider,
    LocalEmbeddingProvider,
)


# --- FakeEmbeddingProvider Tests ---

def test_fake_provider_init():
    """Initialisation FakeProvider OK."""
    provider = FakeEmbeddingProvider(embedding_dim=128)
    
    assert provider.get_embedding_dim() == 128


def test_fake_provider_init_invalid_dim():
    """embedding_dim <= 0 raise ValueError."""
    with pytest.raises(ValueError, match="embedding_dim must be > 0"):
        FakeEmbeddingProvider(embedding_dim=0)


def test_fake_provider_embed():
    """embed() génère vecteur correct."""
    provider = FakeEmbeddingProvider(embedding_dim=384)
    
    vec = provider.embed("Hello world")
    
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (384,)
    assert vec.dtype == np.float32


def test_fake_provider_deterministic():
    """Même texte → même vecteur (déterministe)."""
    provider = FakeEmbeddingProvider(embedding_dim=128)
    
    vec1 = provider.embed("Test text")
    vec2 = provider.embed("Test text")
    
    assert np.allclose(vec1, vec2)


def test_fake_provider_different_texts():
    """Textes différents → vecteurs différents."""
    provider = FakeEmbeddingProvider(embedding_dim=128)
    
    vec1 = provider.embed("Text A")
    vec2 = provider.embed("Text B")
    
    # Pas identiques
    assert not np.allclose(vec1, vec2)


def test_fake_provider_normalized():
    """Vecteurs sont normalisés L2 (norm ≈ 1)."""
    provider = FakeEmbeddingProvider(embedding_dim=128)
    
    vec = provider.embed("Normalize me")
    norm = np.linalg.norm(vec)
    
    assert np.isclose(norm, 1.0, atol=1e-5)


def test_fake_provider_cache():
    """Cache fonctionne (même objet retourné)."""
    provider = FakeEmbeddingProvider(embedding_dim=128)
    
    vec1 = provider.embed("Cached text")
    vec2 = provider.embed("Cached text")
    
    # Même objet numpy (cache)
    assert vec1 is vec2


def test_fake_provider_repr():
    """repr() retourne string valide."""
    provider = FakeEmbeddingProvider(embedding_dim=256)
    provider.embed("Test")
    
    repr_str = repr(provider)
    
    assert "FakeEmbeddingProvider" in repr_str
    assert "256" in repr_str
    assert "cached=1" in repr_str


# --- LocalEmbeddingProvider Tests ---

def test_local_provider_init():
    """Initialisation LocalProvider OK."""
    provider = LocalEmbeddingProvider("all-MiniLM-L6-v2")
    
    assert provider.model_name == "all-MiniLM-L6-v2"


def test_local_provider_embed():
    """embed() génère vecteur (skip si pas installé)."""
    provider = LocalEmbeddingProvider("all-MiniLM-L6-v2")
    
    vec = provider.embed("Hello world")
    
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (384,)  # all-MiniLM-L6-v2 dimension


def test_local_provider_dimension():
    """get_embedding_dim() retourne dimension correcte."""
    provider = LocalEmbeddingProvider("all-MiniLM-L6-v2")
    
    dim = provider.get_embedding_dim()
    
    assert dim == 384


def test_local_provider_repr():
    """repr() retourne string valide."""
    provider = LocalEmbeddingProvider("all-MiniLM-L6-v2")
    
    repr_str = repr(provider)
    
    assert "LocalEmbeddingProvider" in repr_str
    assert "all-MiniLM-L6-v2" in repr_str