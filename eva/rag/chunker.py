"""
TextChunker — Découpe texte en chunks

Chunking simple avec overlapping optionnel.

Standards :
- Chunks de taille configurable
- Overlapping pour contexte
- Préservation métadonnées
- Pas d'allocations inutiles
"""

from typing import List


class TextChunker:
    """
    Découpe texte en chunks de taille fixe avec overlapping.
    
    Attributes:
        chunk_size: Taille max d'un chunk (en caractères)
        chunk_overlap: Nombre de caractères overlapping entre chunks
    
    Example:
        >>> chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        >>> chunks = chunker.chunk("Long text here...")
        >>> len(chunks)
        5
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialise le chunker.
        
        Args:
            chunk_size: Taille max chunk (caractères)
            chunk_overlap: Overlap entre chunks (caractères)
        
        Raises:
            ValueError: Si chunk_size <= 0 ou overlap >= chunk_size
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk(self, text: str) -> List[str]:
        """
        Découpe texte en chunks.
        
        Args:
            text: Texte à découper
        
        Returns:
            Liste de chunks (strings)
        
        Example:
            >>> chunker = TextChunker(chunk_size=10, chunk_overlap=2)
            >>> chunker.chunk("Hello world!")
            ['Hello worl', 'rld!']
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            # Fin du chunk
            end = start + self.chunk_size
            
            # Extraire chunk
            chunk = text[start:end]
            chunks.append(chunk)
            
            # Si on a atteint ou dépassé la fin, on arrête
            if end >= text_len:
                break

            # Prochain start avec overlap
            start = end - self.chunk_overlap
        
        return chunks
    
    def __repr__(self) -> str:
        """Représentation string."""
        return f"TextChunker(size={self.chunk_size}, overlap={self.chunk_overlap})"