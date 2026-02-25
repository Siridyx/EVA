"""
SimilarityEngine — Calcul similarité

Engines :
- SimilarityEngine : Interface abstraite
- CosineSimilarity : Cosine via L2 normalize + dot product
- (Future) FaissSimilarity : ANN rapide

Standards :
- Extensible sans refactor VectorMemory
- L2 normalized vectors
- Scores ∈ [0, 1]
"""

from abc import ABC, abstractmethod
import numpy as np


class SimilarityEngine(ABC):
    """
    Interface abstraite pour calcul similarité.
    
    Permet de switch entre différentes implémentations
    (cosine, FAISS, etc.) sans refactor VectorMemory.
    """
    
    @abstractmethod
    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calcule similarité entre query et documents.
        
        Args:
            query_embedding: Vecteur query (shape: [embedding_dim])
            doc_embeddings: Vecteurs docs (shape: [num_docs, embedding_dim])
        
        Returns:
            Scores similarité (shape: [num_docs])
            Scores ∈ [0, 1] (ou [-1, 1] selon métrique)
        """
        pass


class CosineSimilarity(SimilarityEngine):
    """
    Cosine similarity via L2 normalize + dot product.
    
    Assume vecteurs déjà normalisés L2 (norm=1).
    Cosine = dot(A, B) si A et B normalisés.
    
    Scores ∈ [-1, 1] théoriquement, mais ∈ [0, 1] si vecteurs positifs.
    
    Example:
        >>> engine = CosineSimilarity()
        >>> query = np.array([1.0, 0.0, 0.0])
        >>> docs = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        >>> scores = engine.compute_similarity(query, docs)
        >>> scores
        array([1.0, 0.0])
    """
    
    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calcule cosine similarity.
        
        Assume vecteurs normalisés L2.
        Cosine = dot product.
        
        Args:
            query_embedding: Vecteur query normalisé (shape: [dim])
            doc_embeddings: Vecteurs docs normalisés (shape: [num_docs, dim])
        
        Returns:
            Scores cosine (shape: [num_docs])
        
        Raises:
            ValueError: Si shapes incompatibles
        """
        # Validation shapes
        if query_embedding.ndim != 1:
            raise ValueError(
                f"query_embedding must be 1D, got shape {query_embedding.shape}"
            )
        
        if doc_embeddings.ndim != 2:
            raise ValueError(
                f"doc_embeddings must be 2D, got shape {doc_embeddings.shape}"
            )
        
        if query_embedding.shape[0] != doc_embeddings.shape[1]:
            raise ValueError(
                f"Dimension mismatch: query {query_embedding.shape[0]} "
                f"vs docs {doc_embeddings.shape[1]}"
            )
        
        # Cosine = dot product (vecteurs normalisés)
        scores = np.dot(doc_embeddings, query_embedding)
        
        return scores
    
    def __repr__(self) -> str:
        """Représentation string."""
        return "CosineSimilarity()"