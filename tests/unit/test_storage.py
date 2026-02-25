"""Tests pour VectorStorage"""

import pytest
import numpy as np
import os
import json
from eva.rag.storage import VectorStorage


def test_storage_init(tmp_path):
    """Initialisation storage OK."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    assert storage.storage_dir == str(storage_dir)
    assert not storage.exists()


def test_storage_save_and_load(tmp_path):
    """Save puis load OK."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    vectors = np.array([[0.1, 0.2], [0.3, 0.4]])
    documents = [
        {"doc_id": "doc1", "text": "Hello"},
        {"doc_id": "doc2", "text": "World"}
    ]
    
    storage.save(
        vectors=vectors,
        documents=documents,
        model_name="test-model",
        embedding_dim=2
    )
    
    assert storage.exists()
    
    data = storage.load()
    
    assert data is not None
    assert np.allclose(data["vectors"], vectors)
    assert len(data["documents"]) == 2
    assert data["metadata"]["model_name"] == "test-model"
    assert data["metadata"]["embedding_dim"] == 2


def test_storage_load_nonexistent(tmp_path):
    """Load sans index retourne None."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    data = storage.load()
    
    assert data is None


def test_storage_save_validation_vectors_docs_mismatch(tmp_path):
    """Mismatch vectors/docs raise ValueError."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    vectors = np.array([[0.1, 0.2]])
    documents = [{"doc_id": "doc1"}, {"doc_id": "doc2"}]  # 2 docs, 1 vector
    
    with pytest.raises(ValueError, match="Mismatch"):
        storage.save(
            vectors=vectors,
            documents=documents,
            model_name="test",
            embedding_dim=2
        )


def test_storage_save_validation_dimension_mismatch(tmp_path):
    """Dimension mismatch raise ValueError."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    vectors = np.array([[0.1, 0.2, 0.3]])  # dim=3
    documents = [{"doc_id": "doc1"}]
    
    with pytest.raises(ValueError, match="Dimension mismatch"):
        storage.save(
            vectors=vectors,
            documents=documents,
            model_name="test",
            embedding_dim=2  # Expected dim=2
        )


def test_storage_validate_compatibility_ok(tmp_path):
    """Validate compatibility OK si compatible."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    vectors = np.array([[0.1, 0.2]])
    documents = [{"doc_id": "doc1"}]
    
    storage.save(
        vectors=vectors,
        documents=documents,
        model_name="model-A",
        embedding_dim=2
    )
    
    # Même modèle/dim → OK
    storage.validate_compatibility("model-A", 2)


def test_storage_validate_compatibility_model_mismatch(tmp_path):
    """Validate compatibility raise si model différent."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    vectors = np.array([[0.1, 0.2]])
    documents = [{"doc_id": "doc1"}]
    
    storage.save(
        vectors=vectors,
        documents=documents,
        model_name="model-A",
        embedding_dim=2
    )
    
    # Modèle différent → ValueError
    with pytest.raises(ValueError, match="Model mismatch"):
        storage.validate_compatibility("model-B", 2)


def test_storage_validate_compatibility_dim_mismatch(tmp_path):
    """Validate compatibility raise si dim différent."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    vectors = np.array([[0.1, 0.2]])
    documents = [{"doc_id": "doc1"}]
    
    storage.save(
        vectors=vectors,
        documents=documents,
        model_name="model-A",
        embedding_dim=2
    )
    
    # Dim différente → ValueError
    with pytest.raises(ValueError, match="Dimension mismatch"):
        storage.validate_compatibility("model-A", 3)


def test_storage_clear(tmp_path):
    """clear() supprime index."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    vectors = np.array([[0.1, 0.2]])
    documents = [{"doc_id": "doc1"}]
    
    storage.save(
        vectors=vectors,
        documents=documents,
        model_name="test",
        embedding_dim=2
    )
    
    assert storage.exists()
    
    storage.clear()
    
    assert not storage.exists()


def test_storage_atomic_save(tmp_path):
    """Atomic save : .tmp créé puis rename."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    vectors = np.array([[0.1, 0.2]])
    documents = [{"doc_id": "doc1"}]
    
    storage.save(
        vectors=vectors,
        documents=documents,
        model_name="test",
        embedding_dim=2
    )
    
    # Pas de .tmp après save (renommés)
    assert not os.path.exists(str(storage_dir / "index.json.tmp"))
    assert not os.path.exists(str(storage_dir / "index.npz.tmp"))
    
    # Index final existe
    assert os.path.exists(str(storage_dir / "index.json"))
    assert os.path.exists(str(storage_dir / "index.npz"))


def test_storage_repr(tmp_path):
    """repr() retourne string valide."""
    storage_dir = tmp_path / "vectors"
    storage = VectorStorage(str(storage_dir))
    
    repr_str = repr(storage)
    
    assert "VectorStorage" in repr_str
    assert "empty" in repr_str
    
    # Après save
    vectors = np.array([[0.1, 0.2]])
    documents = [{"doc_id": "doc1"}]
    storage.save(vectors, documents, "test", 2)
    
    repr_str = repr(storage)
    assert "exists" in repr_str