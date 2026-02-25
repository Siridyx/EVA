"""Tests pour TextChunker"""

import pytest
from eva.rag.chunker import TextChunker


def test_chunker_init():
    """Initialisation chunker OK."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    
    assert chunker.chunk_size == 100
    assert chunker.chunk_overlap == 20


def test_chunker_init_invalid_size():
    """chunk_size <= 0 raise ValueError."""
    with pytest.raises(ValueError, match="chunk_size must be > 0"):
        TextChunker(chunk_size=0)


def test_chunker_init_invalid_overlap():
    """chunk_overlap < 0 raise ValueError."""
    with pytest.raises(ValueError, match="chunk_overlap must be >= 0"):
        TextChunker(chunk_size=100, chunk_overlap=-1)


def test_chunker_init_overlap_too_large():
    """chunk_overlap >= chunk_size raise ValueError."""
    with pytest.raises(ValueError, match="chunk_overlap must be < chunk_size"):
        TextChunker(chunk_size=100, chunk_overlap=100)


def test_chunker_empty_text():
    """Texte vide retourne liste vide."""
    chunker = TextChunker()
    
    chunks = chunker.chunk("")
    
    assert chunks == []


def test_chunker_text_smaller_than_chunk():
    """Texte < chunk_size retourne 1 chunk."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    text = "Short text"
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunker_exact_chunk_size():
    """Texte == chunk_size retourne 1 chunk."""
    chunker = TextChunker(chunk_size=10, chunk_overlap=2)
    text = "1234567890"
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunker_multiple_chunks_no_overlap():
    """Plusieurs chunks sans overlap."""
    chunker = TextChunker(chunk_size=5, chunk_overlap=0)
    text = "Hello world!"
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) == 3
    assert chunks[0] == "Hello"
    assert chunks[1] == " worl"
    assert chunks[2] == "d!"


def test_chunker_multiple_chunks_with_overlap():
    """Plusieurs chunks avec overlap."""
    chunker = TextChunker(chunk_size=10, chunk_overlap=3)
    text = "Hello world, how are you?"
    
    chunks = chunker.chunk(text)
    
    # Vérifier overlap
    assert len(chunks) >= 2
    # Le dernier bout du chunk 1 doit être dans chunk 2
    if len(chunks) >= 2:
        overlap_text = chunks[0][-3:]
        assert chunks[1].startswith(overlap_text) or overlap_text in chunks[1]


def test_chunker_repr():
    """repr() retourne string valide."""
    chunker = TextChunker(chunk_size=500, chunk_overlap=50)
    
    repr_str = repr(chunker)
    
    assert "TextChunker" in repr_str
    assert "500" in repr_str
    assert "50" in repr_str