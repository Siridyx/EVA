"""
VectorStorage — Persistance JSON+npz avec atomic save

Storage :
- Format: JSON (metadata) + npz (vectors)
- Index unique: data/vectors/index.*
- Atomic save: .tmp → rename
- Metadata: model_name, embedding_dim, created_at, version

Standards :
- Validation compatibilité embeddings
- Pas de corruption si crash
- Migration claire si changement modèle
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np


class VectorStorage:
    """
    Storage persistant pour vecteurs + metadata.
    
    Format MVP : JSON + npz
    Index unique : data/vectors/index.json + index.npz
    
    Atomic save pour éviter corruption :
    - Écrire .tmp
    - Rename (atomic sur POSIX)
    
    Metadata obligatoire :
    - model_name : Nom modèle embeddings
    - embedding_dim : Dimension vecteurs
    - created_at : Timestamp création
    - version : Schema version ("1.0")
    - num_documents : Nombre docs
    
    Attributes:
        storage_dir: Répertoire storage (data/vectors/)
    
    Example:
        >>> storage = VectorStorage("data/vectors")
        >>> storage.save(
        ...     vectors=np.array([[0.1, 0.2], [0.3, 0.4]]),
        ...     documents=[{"text": "A"}, {"text": "B"}],
        ...     model_name="all-MiniLM-L6-v2",
        ...     embedding_dim=384
        ... )
        >>> data = storage.load()
        >>> data["vectors"].shape
        (2, 2)
    """
    
    def __init__(self, storage_dir: str):
        """
        Initialise VectorStorage.
        
        Args:
            storage_dir: Chemin répertoire storage (ex: data/vectors/)
        """
        self.storage_dir = storage_dir
        self._index_json = os.path.join(storage_dir, "index.json")
        self._index_npz = os.path.join(storage_dir, "index.npz")
    
    def save(
        self,
        vectors: np.ndarray,
        documents: List[Dict[str, Any]],
        model_name: str,
        embedding_dim: int
    ) -> None:
        """
        Sauvegarde index (atomic).
        
        Atomic save :
        1. Écrire .tmp
        2. Rename atomic
        
        Args:
            vectors: Embeddings (shape: [num_docs, embedding_dim])
            documents: Metadata documents
            model_name: Nom modèle embeddings
            embedding_dim: Dimension vecteurs
        
        Raises:
            ValueError: Si validation échoue
        """
        # Validation
        if vectors.shape[0] != len(documents):
            raise ValueError(
                f"Mismatch: {vectors.shape[0]} vectors vs {len(documents)} documents"
            )
        
        if vectors.shape[1] != embedding_dim:
            raise ValueError(
                f"Dimension mismatch: vectors {vectors.shape[1]} vs expected {embedding_dim}"
            )
        
        # Créer répertoire si nécessaire
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Metadata
        metadata = {
            "model_name": model_name,
            "embedding_dim": embedding_dim,
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
            "num_documents": len(documents),
            "documents": documents
        }
        
        # Atomic save : .tmp → rename
        # IMPORTANT: numpy ajoute .npz automatiquement, donc on utilise index.tmp (pas index.npz.tmp)
        tmp_json = self._index_json + ".tmp"
        tmp_npz_base = os.path.join(self.storage_dir, "index.tmp")  # numpy ajoutera .npz
        tmp_npz_full = tmp_npz_base + ".npz"
        
        try:
            # Écrire .tmp
            with open(tmp_json, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            np.savez_compressed(tmp_npz_base, embeddings=vectors)
            
            # Rename atomic
            os.replace(tmp_json, self._index_json)
            os.replace(tmp_npz_full, self._index_npz)
            
        except Exception as e:
            # Cleanup .tmp si erreur
            if os.path.exists(tmp_json):
                os.remove(tmp_json)
            if os.path.exists(tmp_npz_full):
                os.remove(tmp_npz_full)
            raise RuntimeError(f"Save failed: {e}")
    
    def load(self) -> Optional[Dict[str, Any]]:
        """
        Charge index depuis disque.
        
        Validation :
        - Vérifie que metadata est cohérent
        - Retourne None si index n'existe pas
        
        Returns:
            Dict avec clés : vectors, documents, metadata
            Ou None si pas d'index
        
        Raises:
            ValueError: Si validation échoue
        """
        # Vérifier existence
        if not os.path.exists(self._index_json):
            return None
        
        if not os.path.exists(self._index_npz):
            return None
        
        try:
            # Load metadata
            with open(self._index_json, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Load vectors
            npz_data = np.load(self._index_npz)
            vectors = npz_data["embeddings"]
            
            # Validation cohérence
            if vectors.shape[0] != metadata.get("num_documents", 0):
                raise ValueError(
                    f"Corruption: {vectors.shape[0]} vectors vs "
                    f"{metadata['num_documents']} in metadata"
                )
            
            if vectors.shape[1] != metadata.get("embedding_dim", 0):
                raise ValueError(
                    f"Dimension mismatch: {vectors.shape[1]} vs "
                    f"{metadata['embedding_dim']} in metadata"
                )
            
            return {
                "vectors": vectors,
                "documents": metadata.get("documents", []),
                "metadata": {
                    "model_name": metadata["model_name"],
                    "embedding_dim": metadata["embedding_dim"],
                    "created_at": metadata["created_at"],
                    "version": metadata.get("version", "1.0"),
                    "num_documents": metadata["num_documents"]
                }
            }
        
        except Exception as e:
            raise RuntimeError(f"Load failed: {e}")
    
    def validate_compatibility(
        self,
        expected_model: str,
        expected_dim: int
    ) -> None:
        """
        Valide compatibilité index existant.
        
        Args:
            expected_model: Nom modèle attendu
            expected_dim: Dimension attendue
        
        Raises:
            ValueError: Si incompatible
        """
        data = self.load()
        
        if data is None:
            return  # Pas d'index = OK
        
        metadata = data["metadata"]
        
        # Vérifier model_name
        if metadata["model_name"] != expected_model:
            raise ValueError(
                f"Model mismatch: index uses '{metadata['model_name']}' "
                f"but config expects '{expected_model}'. "
                "Clear index and rebuild."
            )
        
        # Vérifier embedding_dim
        if metadata["embedding_dim"] != expected_dim:
            raise ValueError(
                f"Dimension mismatch: index uses {metadata['embedding_dim']} "
                f"but config expects {expected_dim}. "
                "Clear index and rebuild."
            )
    
    def clear(self) -> None:
        """
        Supprime index (pour rebuild).
        """
        if os.path.exists(self._index_json):
            os.remove(self._index_json)
        
        if os.path.exists(self._index_npz):
            os.remove(self._index_npz)
    
    def exists(self) -> bool:
        """Vérifie si index existe."""
        return os.path.exists(self._index_json) and os.path.exists(self._index_npz)
    
    def __repr__(self) -> str:
        """Représentation string."""
        status = "exists" if self.exists() else "empty"
        return f"VectorStorage(dir={self.storage_dir}, status={status})"