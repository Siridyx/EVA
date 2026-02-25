"""Tests pour SimilarityEngine"""

import pytest
import numpy as np
from eva.rag.similarity_engine import CosineSimilarity


def test_cosine_similarity_identical_vectors():
    """Vecteurs identiques → score = 1.0."""
    engine = CosineSimilarity()
    
    query = np.array([1.0, 0.0, 0.0])
    docs = np.array([[1.0, 0.0, 0.0]])
    
    scores = engine.compute_similarity(query, docs)
    
    assert np.isclose(scores[0], 1.0)


def test_cosine_similarity_orthogonal_vectors():
    """Vecteurs orthogonaux → score = 0.0."""
    engine = CosineSimilarity()
    
    query = np.array([1.0, 0.0, 0.0])
    docs = np.array([[0.0, 1.0, 0.0]])
    
    scores = engine.compute_similarity(query, docs)
    
    assert np.isclose(scores[0], 0.0)


def test_cosine_similarity_multiple_docs():
    """Plusieurs docs → scores corrects."""
    engine = CosineSimilarity()
    
    query = np.array([1.0, 0.0, 0.0])
    docs = np.array([
        [1.0, 0.0, 0.0],  # Identique
        [0.0, 1.0, 0.0],  # Orthogonal
        [0.7071, 0.7071, 0.0],  # 45 degrés
    ])
    
    scores = engine.compute_similarity(query, docs)
    
    assert len(scores) == 3
    assert np.isclose(scores[0], 1.0)
    assert np.isclose(scores[1], 0.0)
    assert np.isclose(scores[2], 0.7071, atol=1e-3)


def test_cosine_similarity_invalid_query_shape():
    """Query 2D raise ValueError."""
    engine = CosineSimilarity()
    
    query = np.array([[1.0, 0.0]])  # 2D au lieu de 1D
    docs = np.array([[1.0, 0.0]])
    
    with pytest.raises(ValueError, match="query_embedding must be 1D"):
        engine.compute_similarity(query, docs)


def test_cosine_similarity_invalid_docs_shape():
    """Docs 1D raise ValueError."""
    engine = CosineSimilarity()
    
    query = np.array([1.0, 0.0])
    docs = np.array([1.0, 0.0])  # 1D au lieu de 2D
    
    with pytest.raises(ValueError, match="doc_embeddings must be 2D"):
        engine.compute_similarity(query, docs)


def test_cosine_similarity_dimension_mismatch():
    """Dimensions différentes raise ValueError."""
    engine = CosineSimilarity()
    
    query = np.array([1.0, 0.0])  # dim=2
    docs = np.array([[1.0, 0.0, 0.0]])  # dim=3
    
    with pytest.raises(ValueError, match="Dimension mismatch"):
        engine.compute_similarity(query, docs)


def test_cosine_similarity_repr():
    """repr() retourne string valide."""
    engine = CosineSimilarity()
    
    repr_str = repr(engine)
    
    assert "CosineSimilarity" in repr_str