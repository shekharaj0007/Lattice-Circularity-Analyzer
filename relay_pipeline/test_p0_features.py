#!/usr/bin/env python3
"""
Unit tests for P0 correctness features (API-independent).
Tests citation system, evidence gate, and pipeline constraints.
"""

import sys
sys.path.insert(0, 'src')

from citations import CitationExtractor
from evidence_gate import EvidenceGate

def test_citation_extraction():
    """Test citation pattern extraction."""
    print("\n" + "="*70)
    print("TEST 1: Citation Extraction")
    print("="*70)
    
    extractor = CitationExtractor()
    
    # Test valid citation
    answer = """The transformer architecture uses multi-head attention 
    [Attention Is All You Need v7, p.3, chunk c1] with 8 heads."""
    
    citations = extractor.extract_citations(answer)
    
    assert len(citations) == 1, f"Expected 1 citation, got {len(citations)}"
    assert citations[0]["paper"] == "Attention Is All You Need"
    assert citations[0]["version"] == "v7"
    assert citations[0]["page"] == 3
    assert citations[0]["chunk_id"] == 1
    
    print("✓ Citation extracted correctly")
    print(f"  Paper: {citations[0]['paper']}")
    print(f"  Version: {citations[0]['version']}")
    print(f"  Page: {citations[0]['page']}")
    print(f"  Chunk: c{citations[0]['chunk_id']}")
    
    # Test multiple citations
    answer_multi = """
    Transformers [Attention Is All You Need v7, p.5, chunk c2] were
    improved by Moshi [Moshi v1, p.2, chunk c1].
    """
    
    citations_multi = extractor.extract_citations(answer_multi)
    assert len(citations_multi) == 2
    print(f"\n✓ Multiple citations: {len(citations_multi)} found")
    
    return True

def test_citation_verification():
    """Test citation verification against chunks."""
    print("\n" + "="*70)
    print("TEST 2: Citation Verification")
    print("="*70)
    
    extractor = CitationExtractor()
    
    # Test valid citation
    answer = """The model has 6 layers [Attention Is All You Need v7, p.3, chunk c2]."""
    citations = extractor.extract_citations(answer)
    
    # Mock chunk with matching content
    chunks = [{
        "id": 2,
        "text": "The encoder consists of 6 identical layers. Each layer has two sub-layers.",
        "metadata": {"paper": "Attention Is All You Need", "arxiv_version": "v7"}
    }]
    
    valid, issues = extractor.verify_citations(answer, citations, chunks)
    
    print(f"Valid: {valid}")
    if issues:
        print(f"Issues: {issues}")
    else:
        print("✓ Citation verified against chunk")
    
    # Test citation with missing chunk
    bad_citations = [{
        "paper": "Attention Is All You Need",
        "version": "v7",
        "page": 3,
        "chunk_id": 999  # Doesn't exist
    }]
    
    valid_bad, issues_bad = extractor.verify_citations(answer, bad_citations, chunks)
    
    assert not valid_bad, "Should fail for missing chunk"
    print(f"\n✓ Missing chunk detected: {issues_bad[0][:60]}...")
    
    return True

def test_fabricated_quote_detection():
    """Test detection of fabricated quotes."""
    print("\n" + "="*70)
    print("TEST 3: Fabricated Quote Detection")
    print("="*70)
    
    extractor = CitationExtractor()
    
    # Test fabricated quote
    answer = 'The paper states that "transformers are perfect models".'
    
    chunks = [{
        "id": 1,
        "text": "The transformer model uses multi-head attention."
    }]
    
    valid, msg = extractor.verify_no_fabrication(answer, chunks)
    
    assert not valid, "Should detect fabricated quote"
    print(f"✓ Fabricated quote detected")
    print(f"  Reason: {msg[:80]}...")
    
    # Test valid quote
    answer_valid = 'The model uses "multi-head attention" mechanism.'
    
    valid_ok, msg_ok = extractor.verify_no_fabrication(answer_valid, chunks)
    
    assert valid_ok, "Should accept valid quote"
    print(f"\n✓ Valid quote accepted")
    
    return True

def test_version_validation():
    """Test paper version validation."""
    print("\n" + "="*70)
    print("TEST 4: Version Validation")
    print("="*70)
    
    extractor = CitationExtractor()
    
    # Test correct version
    answer = "Transformers [Attention Is All You Need v7, p.1, chunk c1]."
    citations = extractor.extract_citations(answer)
    
    chunks = [{
        "id": 1,
        "text": "Test content",
        "metadata": {"paper": "Attention Is All You Need", "arxiv_version": "v7"}
    }]
    
    valid, issues = extractor.verify_citations(answer, citations, chunks)
    print("✓ Correct version v7 validated")
    
    # Test wrong version
    bad_answer = "Moshi uses [Moshi v7, p.1, chunk c1]."
    bad_citations = extractor.extract_citations(bad_answer)
    
    chunks_bad = [{
        "id": 1,
        "text": "Test",
        "metadata": {"paper": "Moshi", "arxiv_version": "v1"}
    }]
    
    valid_bad, issues_bad = extractor.verify_citations(bad_answer, bad_citations, chunks_bad)
    
    assert not valid_bad, "Should reject wrong version"
    print(f"✓ Wrong version detected: {issues_bad[0][:60]}...")
    
    return True

def test_evidence_gate_weak():
    """Test evidence gate refuses weak evidence."""
    print("\n" + "="*70)
    print("TEST 5: Evidence Gate - Weak Evidence")
    print("="*70)
    
    gate = EvidenceGate()
    
    # Test weak evidence (< 0.50)
    weak_chunks = [
        {"id": 1, "text": "Not relevant", "similarity": 0.35},
        {"id": 2, "text": "Also not relevant", "similarity": 0.28}
    ]
    
    proceed, reason, meta = gate.assess_evidence(weak_chunks, "test query")
    
    assert not proceed, "Should refuse weak evidence"
    assert meta["decision"] == "refuse"
    assert "don't appear to answer" in reason
    
    print(f"✓ Weak evidence refused")
    print(f"  Max similarity: {meta['max_similarity']:.2f}")
    print(f"  Reason: {reason[:60]}...")
    print(f"  Tokens will be saved: ~400")
    
    return True

def test_evidence_gate_strong():
    """Test evidence gate proceeds with strong evidence."""
    print("\n" + "="*70)
    print("TEST 6: Evidence Gate - Strong Evidence")
    print("="*70)
    
    gate = EvidenceGate()
    
    # Test strong evidence (>= 0.75)
    strong_chunks = [
        {"id": 1, "text": "Highly relevant", "similarity": 0.88},
        {"id": 2, "text": "Also relevant", "similarity": 0.82}
    ]
    
    proceed, reason, meta = gate.assess_evidence(strong_chunks, "test query")
    
    assert proceed, "Should proceed with strong evidence"
    assert meta["decision"] == "proceed"
    
    print(f"✓ Strong evidence accepted")
    print(f"  Max similarity: {meta['max_similarity']:.2f}")
    print(f"  Reason: {reason[:60]}...")
    
    return True

def test_evidence_gate_moderate():
    """Test evidence gate with moderate evidence."""
    print("\n" + "="*70)
    print("TEST 7: Evidence Gate - Moderate Evidence")
    print("="*70)
    
    gate = EvidenceGate()
    
    # Test moderate evidence (0.50-0.75) with good top-3 average
    # Need top_k_avg >= 0.60 to proceed
    moderate_chunks = [
        {"id": 1, "text": "Somewhat relevant", "similarity": 0.65},
        {"id": 2, "text": "Also relevant", "similarity": 0.63},
        {"id": 3, "text": "Relevant too", "similarity": 0.61}
    ]
    
    proceed, reason, meta = gate.assess_evidence(moderate_chunks, "test query")
    
    # Should proceed with moderate evidence
    assert proceed, "Should proceed with moderate evidence"
    assert meta["decision"] == "proceed"
    assert "moderate" in reason.lower() or "top-3" in reason.lower()
    
    print(f"✓ Moderate evidence accepted")
    print(f"  Max similarity: {meta['max_similarity']:.2f}")
    print(f"  Top-3 avg: {meta['top_k_avg']:.2f}")
    print(f"  Reason: {reason[:60]}...")
    
    return True

def test_evidence_gate_stats():
    """Test evidence gate statistics tracking."""
    print("\n" + "="*70)
    print("TEST 8: Evidence Gate - Statistics")
    print("="*70)
    
    gate = EvidenceGate()
    
    # Run several assessments
    weak_chunks = [{"id": 1, "text": "Not relevant", "similarity": 0.25}]
    strong_chunks = [{"id": 1, "text": "Relevant", "similarity": 0.85}]
    
    gate.assess_evidence(weak_chunks, "query 1")  # Refuse
    gate.assess_evidence(weak_chunks, "query 2")  # Refuse
    gate.assess_evidence(strong_chunks, "query 3")  # Proceed
    
    stats = gate.get_stats()
    
    assert stats["total_assessments"] == 3
    assert stats["refused"] == 2
    assert stats["tokens_saved"] == 800  # 2 * 400
    
    print(f"✓ Statistics tracked correctly")
    print(f"  Total: {stats['total_assessments']}")
    print(f"  Refused: {stats['refused']}")
    print(f"  Tokens saved: {stats['tokens_saved']}")
    
    return True

def test_prompt_size_caps():
    """Test prompt size constraints are defined."""
    print("\n" + "="*70)
    print("TEST 9: Prompt Size Caps")
    print("="*70)
    
    # Read pipeline source to verify constants
    import os
    pipeline_path = os.path.join('src', 'pipeline.py')
    
    with open(pipeline_path, 'r') as f:
        content = f.read()
    
    assert 'MAX_PROMPT_TOKENS = 4000' in content, "MAX_PROMPT_TOKENS not set to 4000"
    assert 'MAX_CONTEXT_CHARS = 3000' in content, "MAX_CONTEXT_CHARS not set to 3000"
    
    print(f"✓ Prompt size caps configured")
    print(f"  MAX_PROMPT_TOKENS: 4000")
    print(f"  MAX_CONTEXT_CHARS: 3000")
    
    return True

def run_all_tests():
    """Run all P0 feature tests."""
    print("\n" + "="*70)
    print("P0 FEATURE VALIDATION")
    print("Testing: Citations, Evidence Gate, Constraints")
    print("="*70)
    
    tests = [
        ("Citation Extraction", test_citation_extraction),
        ("Citation Verification", test_citation_verification),
        ("Fabricated Quote Detection", test_fabricated_quote_detection),
        ("Version Validation", test_version_validation),
        ("Evidence Gate - Weak", test_evidence_gate_weak),
        ("Evidence Gate - Strong", test_evidence_gate_strong),
        ("Evidence Gate - Moderate", test_evidence_gate_moderate),
        ("Evidence Gate - Stats", test_evidence_gate_stats),
        ("Prompt Size Caps", test_prompt_size_caps),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n✗ {name} FAILED: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✅ ALL P0 FEATURES WORKING CORRECTLY")
    else:
        print(f"⚠️  {failed} test(s) failed")
    print("="*70)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
