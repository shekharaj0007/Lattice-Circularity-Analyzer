"""Semantic chunking for PDF papers."""
import re
from typing import List, Dict
import numpy as np


class SemanticChunker:
    """Chunk papers based on semantic boundaries."""
    
    # Section heading patterns
    SECTION_PATTERNS = [
        r'\n\s*\d+\.?\s+[A-Z][^\n]{5,80}\n',  # Numbered sections
        r'\n\s*[A-Z][A-Z\s]{5,50}\n',  # ALL CAPS headings
        r'\n\s*(?:Abstract|Introduction|Related Work|Methodology|Methods|Results|Discussion|Conclusion|References|Appendix)',
    ]
    
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, source: str = "") -> List[Dict[str, any]]:
        """Chunk text using semantic boundaries."""
        # First, try to split by sections
        sections = self._split_by_sections(text)
        
        chunks = []
        chunk_id = 0
        
        for section in sections:
            # If section is small enough, keep it as one chunk
            if len(section) <= self.chunk_size * 1.5:
                chunks.append({
                    "id": chunk_id,
                    "text": section.strip(),
                    "char_count": len(section),
                    "source": source
                })
                chunk_id += 1
            else:
                # Split large sections into smaller chunks with overlap
                section_chunks = self._split_with_overlap(section)
                for sc in section_chunks:
                    chunks.append({
                        "id": chunk_id,
                        "text": sc.strip(),
                        "char_count": len(sc),
                        "source": source
                    })
                    chunk_id += 1
        
        return chunks
    
    def _split_by_sections(self, text: str) -> List[str]:
        """Split text by section boundaries."""
        # Find all section boundaries
        boundaries = [0]
        
        for pattern in self.SECTION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                pos = match.start()
                if pos not in boundaries:
                    boundaries.append(pos)
        
        boundaries.append(len(text))
        boundaries = sorted(set(boundaries))
        
        # Extract sections
        sections = []
        for i in range(len(boundaries) - 1):
            section = text[boundaries[i]:boundaries[i+1]]
            if section.strip():
                sections.append(section)
        
        return sections if sections else [text]
    
    def _split_with_overlap(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                sentence_end = max(
                    text.rfind('. ', start, end),
                    text.rfind('.\n', start, end),
                    text.rfind('? ', start, end),
                    text.rfind('! ', start, end)
                )
                if sentence_end > start + self.chunk_size // 2:
                    end = sentence_end + 1
            
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            
            start = end - self.overlap
        
        return chunks


class ChunkingProfile:
    """Predefined chunking profiles for testing."""
    
    @staticmethod
    def get_aggressive():
        return SemanticChunker(chunk_size=256, overlap=30)
    
    @staticmethod
    def get_balanced():
        return SemanticChunker(chunk_size=512, overlap=50)
    
    @staticmethod
    def get_minimal():
        return SemanticChunker(chunk_size=1024, overlap=100)


if __name__ == "__main__":
    # Test chunking
    sample_text = """
    1. Introduction
    This is an introduction section with some content.
    It has multiple sentences.
    
    2. Related Work
    Previous work has shown various approaches.
    We build on these foundations.
    
    3. Methodology
    Our approach uses a novel technique.
    """
    
    for name, chunker in [
        ("Aggressive", ChunkingProfile.get_aggressive()),
        ("Balanced", ChunkingProfile.get_balanced()),
        ("Minimal", ChunkingProfile.get_minimal())
    ]:
        chunks = chunker.chunk_text(sample_text, "test")
        print(f"\n{name}: {len(chunks)} chunks")
        for c in chunks[:2]:
            print(f"  Chunk {c['id']}: {c['char_count']} chars")
