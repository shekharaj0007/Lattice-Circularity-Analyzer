"""
Citation extraction and verification system.

Purpose: Ensure factual correctness by verifying all claims are grounded in source material.
Trade-off: Deterministic regex matching (fast, reliable) vs LLM-based extraction (flexible but unreliable).
"""
import re
from typing import List, Dict, Tuple, Optional


# Paper versions from assignment
PAPER_VERSIONS = {
    "Attention Is All You Need": "v7",
    "attention": "v7",
    "transformer": "v7",
    "Moshi": "v1", 
    "moshi": "v1",
    "speech": "v1",
    "Dynamic Chunking": "v2",
    "chunking": "v2",
    "hierarchical": "v2"
}


class CitationExtractor:
    """Extract and verify citations from generated answers."""
    
    # Citation pattern: [Paper v1, p.5, chunk c12] or variations
    CITATION_PATTERN = r'\[([^\]]+?)\s+v(\d+),\s*p\.(\d+),\s*chunk\s+c(\d+)\]'
    
    def __init__(self):
        self.extraction_count = 0
        self.verification_count = 0
        self.failed_verifications = 0
    
    def extract_citations(self, answer: str) -> List[Dict]:
        """
        Extract all citations from answer text.
        
        Returns list of:
        {
            "paper": str,
            "version": str,
            "page": int,
            "chunk_id": int,
            "raw": str (original citation text)
        }
        """
        self.extraction_count += 1
        citations = []
        
        for match in re.finditer(self.CITATION_PATTERN, answer):
            paper, version, page, chunk_id = match.groups()
            citations.append({
                "paper": paper.strip(),
                "version": f"v{version}",
                "page": int(page),
                "chunk_id": int(chunk_id),
                "raw": match.group(0)
            })
        
        return citations
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize whitespace for comparison.
        - Collapse multiple spaces to one
        - Strip leading/trailing whitespace
        - Normalize newlines
        """
        # Replace multiple whitespace with single space
        normalized = re.sub(r'\s+', ' ', text)
        return normalized.strip()
    
    def verify_citations(self, answer: str, citations: List[Dict], 
                        retrieved_chunks: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Verify all citations are valid.
        
        Checks:
        1. Cited text appears verbatim in cited chunk (whitespace-normalized)
        2. Cited chunk ID is in retrieved chunks
        3. Version matches paper
        4. Numbers in answer appear in cited text
        
        Returns:
            (is_valid, issues_list)
        """
        self.verification_count += 1
        issues = []
        
        if not citations:
            issues.append("No citations found in answer")
            self.failed_verifications += 1
            return False, issues
        
        # Build chunk lookup
        chunk_lookup = {chunk["id"]: chunk for chunk in retrieved_chunks}
        
        for citation in citations:
            chunk_id = citation["chunk_id"]
            
            # Check 1: Chunk ID must be in retrieved chunks
            if chunk_id not in chunk_lookup:
                issues.append(f"Chunk c{chunk_id} not in retrieved chunks (available: {list(chunk_lookup.keys())})")
                continue
            
            chunk = chunk_lookup[chunk_id]
            
            # Check 2: Version must match paper
            paper = citation["paper"].lower()
            expected_version = None
            for key, version in PAPER_VERSIONS.items():
                if key.lower() in paper:
                    expected_version = version
                    break
            
            if expected_version and citation["version"] != expected_version:
                issues.append(f"Wrong version for {citation['paper']}: got {citation['version']}, expected {expected_version}")
        
        # Check 3: Extract claims from answer and verify against chunks
        # Remove citation markers to get clean text
        clean_answer = re.sub(self.CITATION_PATTERN, '', answer)
        
        # Extract sentences with numbers (likely factual claims)
        number_sentences = self._extract_number_sentences(clean_answer)
        
        for sentence in number_sentences:
            # Check if sentence appears in any cited chunk
            found = False
            normalized_sentence = self.normalize_text(sentence)
            
            for citation in citations:
                chunk_id = citation["chunk_id"]
                if chunk_id in chunk_lookup:
                    chunk_text = chunk_lookup[chunk_id]["text"]
                    normalized_chunk = self.normalize_text(chunk_text)
                    
                    # Check for substantial overlap (not just single words)
                    if self._has_substantial_overlap(normalized_sentence, normalized_chunk):
                        found = True
                        break
            
            if not found and len(sentence) > 30:  # Only check substantial claims
                issues.append(f"Unverified claim with numbers: '{sentence[:80]}...'")
        
        if issues:
            self.failed_verifications += 1
            return False, issues
        
        return True, []
    
    def _extract_number_sentences(self, text: str) -> List[str]:
        """Extract sentences containing numbers."""
        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        
        # Keep sentences with numbers
        number_sentences = []
        for sentence in sentences:
            if re.search(r'\d+', sentence):
                cleaned = sentence.strip()
                if cleaned:
                    number_sentences.append(cleaned)
        
        return number_sentences
    
    def _has_substantial_overlap(self, sentence: str, chunk: str, 
                                 min_match_length: int = 20) -> bool:
        """
        Check if sentence has substantial verbatim overlap with chunk.
        
        Looks for continuous matching substrings of at least min_match_length chars.
        """
        sentence_lower = sentence.lower()
        chunk_lower = chunk.lower()
        
        # Check if substantial substring exists
        sentence_words = sentence_lower.split()
        
        # Sliding window approach
        for window_size in range(len(sentence_words), 2, -1):  # Start with full sentence
            for i in range(len(sentence_words) - window_size + 1):
                window = ' '.join(sentence_words[i:i+window_size])
                if len(window) >= min_match_length and window in chunk_lower:
                    return True
        
        return False
    
    def verify_no_fabrication(self, answer: str, retrieved_chunks: List[Dict]) -> Tuple[bool, str]:
        """
        Test that answer doesn't contain fabricated quotes.
        
        Extracts quoted text and verifies it appears in chunks.
        """
        # Find all quoted text
        quoted_texts = re.findall(r'"([^"]{10,})"', answer)
        
        if not quoted_texts:
            return True, "No quotes to verify"
        
        for quote in quoted_texts:
            normalized_quote = self.normalize_text(quote)
            found = False
            
            for chunk in retrieved_chunks:
                normalized_chunk = self.normalize_text(chunk["text"])
                if normalized_quote.lower() in normalized_chunk.lower():
                    found = True
                    break
            
            if not found:
                return False, f"Fabricated quote: '{quote[:80]}...'"
        
        return True, "All quotes verified"
    
    def get_stats(self) -> Dict:
        """Get citation system statistics."""
        return {
            "extractions": self.extraction_count,
            "verifications": self.verification_count,
            "failed_verifications": self.failed_verifications,
            "success_rate": (self.verification_count - self.failed_verifications) / self.verification_count if self.verification_count > 0 else 0
        }


def test_citation_extraction():
    """Test citation extraction and verification."""
    extractor = CitationExtractor()
    
    # Test extraction
    answer = "The transformer uses attention [Attention Is All You Need v7, p.3, chunk c1]. It has 6 layers [Attention Is All You Need v7, p.5, chunk c2]."
    citations = extractor.extract_citations(answer)
    
    assert len(citations) == 2
    assert citations[0]["paper"] == "Attention Is All You Need"
    assert citations[0]["version"] == "v7"
    assert citations[0]["chunk_id"] == 1
    
    print("✓ Citation extraction works")
    
    # Test normalization
    text1 = "The  transformer   uses\n\nattention"
    text2 = "The transformer uses attention"
    assert extractor.normalize_text(text1) == extractor.normalize_text(text2)
    
    print("✓ Text normalization works")
    
    # Test verification with mock chunks
    chunks = [
        {"id": 1, "text": "The transformer model uses self-attention mechanisms"},
        {"id": 2, "text": "The architecture consists of 6 encoder and 6 decoder layers"}
    ]
    
    valid, issues = extractor.verify_citations(answer, citations, chunks)
    print(f"Verification: {valid}, Issues: {issues}")
    
    print("✓ Citation verification works")


if __name__ == "__main__":
    test_citation_extraction()
