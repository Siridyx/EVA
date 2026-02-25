"""
VectorMemory — Composant mémoire vectorielle

Composant principal RAG :
- add_document(text, metadata) → chunk + embed + store
- search(query, top_k) → retrieve contexte pertinent
- clear() → reset index

Standards :
- Hérite EvaComponent
- Events observabilité
- Format search strict
- Gère 0 docs sans crash
- O(n) MVP (FAISS plus tard)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np

from eva.core.eva_component import EvaComponent
from eva.rag.chunker import TextChunker
from eva.rag.embeddings_provider import EmbeddingsProvider
from eva.rag.similarity_engine import SimilarityEngine
from eva.rag.storage import VectorStorage


class VectorMemory(EvaComponent):
    """
    Mémoire vectorielle pour RAG.
    
    Pipeline :
    1. add_document() → chunk → embed → store
    2. search() → embed query → similarity → top-k
    
    Attributes:
        _chunker: TextChunker
        _embeddings: EmbeddingsProvider
        _similarity: SimilarityEngine
        _storage: VectorStorage
        _vectors: Vectors en mémoire (lazy load)
        _documents: Documents en mémoire
    
    Events :
        - vector_document_added : Document ajouté
        - vector_search_performed : Recherche effectuée
        - vector_index_loaded : Index chargé depuis disque
    
    Example:
        >>> memory = VectorMemory(config, event_bus, chunker, embeddings, similarity, storage)
        >>> memory.start()
        >>> memory.add_document("Long text...", {"source": "file.txt"})
        >>> results = memory.search("query", top_k=3)
        >>> results[0]["score"]  # Score similarité
        0.95
    """
    
    def __init__(
        self,
        config,
        event_bus,
        chunker: TextChunker,
        embeddings: EmbeddingsProvider,
        similarity: SimilarityEngine,
        storage: VectorStorage
    ):
        """
        Initialise VectorMemory.
        
        Args:
            config: ConfigManager
            event_bus: EventBus
            chunker: TextChunker
            embeddings: EmbeddingsProvider
            similarity: SimilarityEngine
            storage: VectorStorage
        """
        # Assigner AVANT super().__init__ (pour __repr__)
        self._chunker = chunker
        self._embeddings = embeddings
        self._similarity = similarity
        self._storage = storage
        
        # Index en mémoire (lazy load)
        self._vectors: Optional[np.ndarray] = None
        self._documents: List[Dict[str, Any]] = []
        
        super().__init__(config, event_bus, "VectorMemory")
    
    def _do_start(self) -> None:
        """
        Démarre VectorMemory.
        
        Load index si existe.
        Valide compatibilité embeddings.
        """
        # Valider compatibilité si index existe
        model_name = self.get_config("rag.embedding_model", "all-MiniLM-L6-v2")
        embedding_dim = self._embeddings.get_embedding_dim()
        
        try:
            self._storage.validate_compatibility(model_name, embedding_dim)
        except ValueError as e:
            self.emit("vector_compatibility_error", {"error": str(e)})
            raise
        
        # Load index si existe
        if self._storage.exists():
            data = self._storage.load()
            
            if data is not None:
                self._vectors = data["vectors"]
                self._documents = data["documents"]
                
                # Event avec index_age_days
                created_at = datetime.fromisoformat(data["metadata"]["created_at"])
                age_days = (datetime.utcnow() - created_at).days
                
                self.emit("vector_index_loaded", {
                    "num_documents": len(self._documents),
                    "embedding_dim": embedding_dim,
                    "index_age_days": age_days,
                    "model_name": model_name
                })
        
        self.emit("vector_memory_started", {})
    
    def _do_stop(self) -> None:
        """Arrête VectorMemory."""
        # Save avant stop si vectors modifiés
        if self._vectors is not None and len(self._documents) > 0:
            self._save_index()
        
        self.emit("vector_memory_stopped", {})
    
    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Ajoute document à l'index.
        
        Pipeline :
        1. Chunk texte
        2. Embed chunks
        3. Store vectors + metadata
        
        Args:
            text: Texte à indexer
            metadata: Métadonnées document (optionnel)
        
        Raises:
            RuntimeError: Si not running
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")
        
        if not text.strip():
            return  # Texte vide → skip
        
        # Metadata par défaut
        if metadata is None:
            metadata = {}
        
        # 1. Chunk texte
        chunks = self._chunker.chunk(text)
        
        # 2. Embed chunks
        chunk_vectors = []
        for chunk in chunks:
            vec = self._embeddings.embed(chunk)
            chunk_vectors.append(vec)
        
        chunk_vectors = np.array(chunk_vectors)
        
        # 3. Créer documents metadata
        doc_id = metadata.get("doc_id", f"doc_{len(self._documents)}")
        
        chunk_docs = []
        for i, chunk in enumerate(chunks):
            chunk_docs.append({
                "doc_id": doc_id,
                "chunk_id": i,
                "text": chunk,
                "metadata": metadata
            })
        
        # 4. Ajouter à index en mémoire
        if self._vectors is None:
            self._vectors = chunk_vectors
            self._documents = chunk_docs
        else:
            self._vectors = np.vstack([self._vectors, chunk_vectors])
            self._documents.extend(chunk_docs)
        
        # 5. Save index
        self._save_index()
        
        # Event
        self.emit("vector_document_added", {
            "doc_id": doc_id,
            "num_chunks": len(chunks),
            "total_documents": len(self._documents)
        })
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Recherche documents similaires.
        
        Pipeline :
        1. Embed query
        2. Compute similarity
        3. Top-k
        4. Format résultats
        
        Args:
            query: Query texte
            top_k: Nombre résultats (défaut 3)
        
        Returns:
            Liste résultats triés décroissant par score.
            Format : {"doc_id", "chunk_id", "text", "metadata", "score"}
        
        Raises:
            RuntimeError: Si not running
        
        Example:
            >>> results = memory.search("What is RAG?", top_k=3)
            >>> results[0]["score"]
            0.95
            >>> results[0]["text"]
            "RAG means Retrieval-Augmented Generation..."
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")
        
        # Gère 0 docs sans crash
        if self._vectors is None or len(self._documents) == 0:
            return []
        
        # 1. Embed query
        query_vec = self._embeddings.embed(query)
        
        # 2. Compute similarity
        scores = self._similarity.compute_similarity(query_vec, self._vectors)
        
        # 3. Top-k (argsort décroissant)
        top_k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        # 4. Format résultats
        results = []
        for idx in top_indices:
            doc = self._documents[idx]
            results.append({
                "doc_id": doc["doc_id"],
                "chunk_id": doc["chunk_id"],
                "text": doc["text"],
                "metadata": doc["metadata"],
                "score": float(scores[idx])
            })
        
        # Event
        self.emit("vector_search_performed", {
            "query": query[:50],
            "top_k": top_k,
            "num_results": len(results)
        })
        
        return results
    
    def clear(self) -> None:
        """
        Clear index (pour rebuild).
        
        Raises:
            RuntimeError: Si not running
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")
        
        self._vectors = None
        self._documents = []
        self._storage.clear()
        
        self.emit("vector_index_cleared", {})
    
    def _save_index(self) -> None:
        """Save index vers disque."""
        if self._vectors is None or len(self._documents) == 0:
            return
        
        model_name = self.get_config("rag.embedding_model", "all-MiniLM-L6-v2")
        embedding_dim = self._embeddings.get_embedding_dim()
        
        self._storage.save(
            vectors=self._vectors,
            documents=self._documents,
            model_name=model_name,
            embedding_dim=embedding_dim
        )
    
    def __repr__(self) -> str:
        """Représentation string."""
        num_docs = len(self._documents) if self._documents else 0
        state = "running" if self._running else ("started" if self._started else "stopped")
        return f"VectorMemory(state={state}, documents={num_docs})"