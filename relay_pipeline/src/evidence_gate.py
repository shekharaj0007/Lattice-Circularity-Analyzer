"""
Evidence quality assessment gate.

Purpose: Save tokens by refusing early when evidence is weak, rather than generating ungrounded answers.
Trade-off: Conservative threshold (refuse more, safer) vs aggressive (answer more, riskier).
"""
from typing import List, Dict, Tuple
import numpy as np


class EvidenceGate:
    """
    Assess evidence quality and decide whether to proceed with generation.
    
    Uses retrieval scores (similarity) to determine if evidence is strong enough.
    If weak, returns refusal immediately without calling generation LLM.
    """
    
    # Thresholds based on similarity scores (0-1 range)
    # Trade-off: Lower = more conservative (refuse more), Higher = more aggressive (answer more)
    STRONG_THRESHOLD = 0.75  # High confidence - proceed
    WEAK_THRESHOLD = 0.50    # Low confidence - refuse
    # Between thresholds: use secondary signals
    
    def __init__(self, strong_threshold: float = 0.75, weak_threshold: float = 0.50):
        """
        Initialize evidence gate.
        
        Args:
            strong_threshold: Proceed if max similarity >= this
            weak_threshold: Refuse if max similarity < this
        """
        self.strong_threshold = strong_threshold
        self.weak_threshold = weak_threshold
        
        # Metrics
        self.total_assessments = 0
        self.proceeded = 0
        self.refused = 0
        self.tokens_saved = 0  # Estimated generation tokens saved
    
    def assess_evidence(self, retrieved_chunks: List[Dict], 
                       query: str) -> Tuple[bool, str, Dict]:
        """
        Assess evidence quality and decide whether to proceed.
        
        Args:
            retrieved_chunks: Chunks with similarity scores
            query: Original query
        
        Returns:
            (should_proceed, reason, metadata)
            - should_proceed: True to generate, False to refuse
            - reason: Explanation
            - metadata: Assessment details
        """
        self.total_assessments += 1
        
        if not retrieved_chunks:
            self.refused += 1
            self.tokens_saved += 400  # Typical generation cost
            return False, "No relevant passages found", {
                "decision": "refuse",
                "reason": "no_chunks",
                "max_similarity": 0.0,
                "chunks_count": 0
            }
        
        # Extract similarity scores
        similarities = [chunk.get("similarity", 0.0) for chunk in retrieved_chunks]
        max_similarity = max(similarities)
        avg_similarity = np.mean(similarities)
        top_k_avg = np.mean(similarities[:min(3, len(similarities))])  # Top 3 average
        
        metadata = {
            "max_similarity": max_similarity,
            "avg_similarity": avg_similarity,
            "top_k_avg": top_k_avg,
            "chunks_count": len(retrieved_chunks)
        }
        
        # Decision logic
        # 1. Strong evidence - definitely proceed
        if max_similarity >= self.strong_threshold:
            self.proceeded += 1
            return True, f"Strong evidence (similarity={max_similarity:.2f})", {
                **metadata,
                "decision": "proceed",
                "reason": "strong_evidence"
            }
        
        # 2. Weak evidence - refuse
        if max_similarity < self.weak_threshold:
            self.refused += 1
            self.tokens_saved += 400
            
            # Find closest passage for user feedback
            best_chunk_idx = similarities.index(max_similarity)
            closest_passage = retrieved_chunks[best_chunk_idx]["text"][:200]
            
            return False, f"Papers don't appear to answer this. Closest related passage (not an answer): '{closest_passage}...'", {
                **metadata,
                "decision": "refuse",
                "reason": "weak_evidence",
                "closest_passage": closest_passage
            }
        
        # 3. Borderline - use secondary signals
        # Check if top-3 average is strong enough
        if top_k_avg >= self.weak_threshold + 0.1:  # Slightly above weak threshold
            self.proceeded += 1
            return True, f"Moderate evidence (top-3 avg={top_k_avg:.2f})", {
                **metadata,
                "decision": "proceed",
                "reason": "moderate_evidence"
            }
        
        # 4. Default to refuse (conservative)
        self.refused += 1
        self.tokens_saved += 400
        
        best_chunk_idx = similarities.index(max_similarity)
        closest_passage = retrieved_chunks[best_chunk_idx]["text"][:200]
        
        return False, f"Evidence not strong enough. Closest passage (not an answer): '{closest_passage}...'", {
            **metadata,
            "decision": "refuse",
            "reason": "borderline_refuse",
            "closest_passage": closest_passage
        }
    
    def get_stats(self) -> Dict:
        """Get evidence gate statistics."""
        return {
            "total_assessments": self.total_assessments,
            "proceeded": self.proceeded,
            "refused": self.refused,
            "refuse_rate": self.refused / self.total_assessments if self.total_assessments > 0 else 0,
            "tokens_saved": self.tokens_saved,
            "avg_tokens_saved_per_refusal": self.tokens_saved / self.refused if self.refused > 0 else 0
        }
    
    def update_thresholds(self, strong: float, weak: float):
        """
        Update thresholds dynamically.
        
        Allows tuning based on measurements:
        - Too many bad answers? Raise thresholds (more conservative)
        - Too many refusals? Lower thresholds (more aggressive)
        """
        if weak >= strong:
            raise ValueError("weak_threshold must be < strong_threshold")
        
        self.strong_threshold = strong
        self.weak_threshold = weak


def test_evidence_gate():
    """Test evidence gate logic."""
    gate = EvidenceGate()
    
    # Test 1: Strong evidence
    strong_chunks = [
        {"id": 1, "text": "Relevant text here", "similarity": 0.85},
        {"id": 2, "text": "Also relevant", "similarity": 0.78}
    ]
    proceed, reason, meta = gate.assess_evidence(strong_chunks, "test query")
    assert proceed == True
    assert meta["decision"] == "proceed"
    print(f"✓ Strong evidence: {reason}")
    
    # Test 2: Weak evidence
    weak_chunks = [
        {"id": 1, "text": "Not very relevant", "similarity": 0.35},
        {"id": 2, "text": "Also weak", "similarity": 0.30}
    ]
    proceed, reason, meta = gate.assess_evidence(weak_chunks, "test query")
    assert proceed == False
    assert meta["decision"] == "refuse"
    print(f"✓ Weak evidence: {reason[:80]}...")
    
    # Test 3: No chunks
    proceed, reason, meta = gate.assess_evidence([], "test query")
    assert proceed == False
    print(f"✓ No chunks: {reason}")
    
    # Test 4: Stats
    stats = gate.get_stats()
    print(f"\n✓ Stats: {stats}")
    print(f"  Tokens saved: {stats['tokens_saved']}")
    print(f"  Refuse rate: {stats['refuse_rate']*100:.1f}%")


if __name__ == "__main__":
    test_evidence_gate()
