"""
EmbeddingsProvider — Interface et implémentations

Providers :
- EmbeddingsProvider : Interface abstraite
- LocalProvider : sentence-transformers (production)
- FakeEmbeddingProvider : Hash déterministe (tests)

Standards :
- Tests 100% offline (FakeProvider)
- Cache embeddings
- Validation dimension
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import hashlib
import numpy as np


class EmbeddingsProvider(ABC):
    """
    Interface abstraite pour embedding providers.
    
    Tous les providers doivent implémenter :
    - embed(text) → vector
    - get_embedding_dim() → int
    """
    
    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """
        Génère embedding pour un texte.
        
        Args:
            text: Texte à embedder
        
        Returns:
            Vecteur numpy (shape: [embedding_dim])
        """
        pass
    
    @abstractmethod
    def get_embedding_dim(self) -> int:
        """
        Retourne dimension embeddings.
        
        Returns:
            Dimension (ex: 384 pour all-MiniLM-L6-v2)
        """
        pass


class FakeEmbeddingProvider(EmbeddingsProvider):
    """
    Provider déterministe pour tests (hash texte).
    
    Génère vecteurs basés sur hash SHA256 du texte.
    Pas de download, pas de random, 100% déterministe.
    
    Attributes:
        embedding_dim: Dimension des vecteurs
        _cache: Cache embeddings déjà calculés
    
    Example:
        >>> provider = FakeEmbeddingProvider(embedding_dim=128)
        >>> vec = provider.embed("Hello world")
        >>> vec.shape
        (128,)
        >>> # Même texte → même vecteur
        >>> vec2 = provider.embed("Hello world")
        >>> np.allclose(vec, vec2)
        True
    """
    
    def __init__(self, embedding_dim: int = 384):
        """
        Initialise FakeProvider.
        
        Args:
            embedding_dim: Dimension vecteurs (défaut 384)
        
        Raises:
            ValueError: Si embedding_dim <= 0
        """
        if embedding_dim <= 0:
            raise ValueError("embedding_dim must be > 0")
        
        self._embedding_dim = embedding_dim
        self._cache: Dict[str, np.ndarray] = {}
    
    def embed(self, text: str) -> np.ndarray:
        """
        Génère embedding déterministe via hash.
        
        Utilise SHA256(text) pour générer vecteur.
        Normalize L2 pour compatibilité cosine.
        
        Args:
            text: Texte à embedder
        
        Returns:
            Vecteur normalisé (shape: [embedding_dim])
        """
        # Cache hit
        if text in self._cache:
            return self._cache[text]
        
        # Hash texte → seed entier déterministe
        hash_bytes = hashlib.sha256(text.encode('utf-8')).digest()
        seed = int.from_bytes(hash_bytes[:8], 'big')

        # Générer vecteur via RNG seedé (pas de NaN/Inf possible)
        rng = np.random.default_rng(seed)
        vector = rng.random(self._embedding_dim).astype(np.float32)

        # Normalize L2 pour cosine similarity
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        # Cache
        self._cache[text] = vector
        
        return vector
    
    def get_embedding_dim(self) -> int:
        """Retourne dimension embeddings."""
        return self._embedding_dim
    
    def __repr__(self) -> str:
        """Représentation string."""
        return f"FakeEmbeddingProvider(dim={self._embedding_dim}, cached={len(self._cache)})"


class LocalEmbeddingProvider(EmbeddingsProvider):
    """
    Provider local avec sentence-transformers.
    
    Utilise modèles Hugging Face (ex: all-MiniLM-L6-v2).
    
    Note:
        Nécessite sentence-transformers installé.
        Télécharge modèle au premier usage (~80MB pour all-MiniLM).
    
    Attributes:
        model_name: Nom modèle Hugging Face
        _model: Instance SentenceTransformer (lazy load)
        _cache: Cache embeddings
    
    Example:
        >>> provider = LocalEmbeddingProvider("all-MiniLM-L6-v2")
        >>> vec = provider.embed("Hello world")
        >>> vec.shape
        (384,)
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialise LocalProvider.
        
        Args:
            model_name: Nom modèle sentence-transformers
        """
        self.model_name = model_name
        self._model: Optional[Any] = None
        self._cache: Dict[str, np.ndarray] = {}
    
    def _load_model(self) -> None:
        """Lazy load du modèle."""
        if self._model is not None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        self._model = SentenceTransformer(self.model_name)
    
    def embed(self, text: str) -> np.ndarray:
        """
        Génère embedding via sentence-transformers.
        
        Args:
            text: Texte à embedder
        
        Returns:
            Vecteur normalisé (shape: [embedding_dim])
        """
        # Cache hit
        if text in self._cache:
            return self._cache[text]
        
        # Load model si nécessaire
        self._load_model()
        
        # Embed
        vector = self._model.encode(text, convert_to_numpy=True)
        
        # Normalize L2
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        # Cache
        self._cache[text] = vector
        
        return vector
    
    def get_embedding_dim(self) -> int:
        """Retourne dimension embeddings."""
        self._load_model()
        return self._model.get_sentence_embedding_dimension()
    
    def __repr__(self) -> str:
        """Représentation string."""
        return f"LocalEmbeddingProvider(model={self.model_name}, cached={len(self._cache)})"