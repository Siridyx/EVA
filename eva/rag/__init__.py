"""
EVA RAG — Retrieval-Augmented Generation

Système de mémoire vectorielle pour recherche de contexte pertinent.

Composants :
- TextChunker : Découpe texte en chunks
- EmbeddingsProvider : Interface + LocalProvider + FakeProvider
- SimilarityEngine : Calcul similarité (cosine, prêt FAISS)
- VectorStorage : Persistance JSON+npz avec atomic save
- VectorMemory : Composant principal (add, search)

Standards :
- Python 3.9 strict
- Tests offline déterministes (FakeProvider)
- Format search strict : doc_id, chunk_id, text, metadata, score
- Atomic save pour éviter corruption
- Compatibilité embeddings (model_name + dim)
"""

from eva.rag.chunker import TextChunker
from eva.rag.embeddings_provider import (
    EmbeddingsProvider,
    FakeEmbeddingProvider,
)
from eva.rag.similarity_engine import SimilarityEngine, CosineSimilarity
from eva.rag.storage import VectorStorage
from eva.rag.vector_memory import VectorMemory

__all__ = [
    "TextChunker",
    "EmbeddingsProvider",
    "FakeEmbeddingProvider",
    "SimilarityEngine",
    "CosineSimilarity",
    "VectorStorage",
    "VectorMemory",
]