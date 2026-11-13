"""
Quick test to verify pipeline setup works correctly.
Tests individual components without consuming much API quota.
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, 'src')

from src import (
    PaperFetcher,
    ChunkingProfile,
    EmbeddingEngine,
    RateLimiter,
    TokenBudgetTracker,
    StandinGroqService,
    TEST_QUESTIONS
)

load_dotenv()


def test_paper_fetching():
    """Test paper fetching (will skip if already downloaded)."""
    print("\n" + "="*60)
    print("TEST 1: Paper Fetching")
    print("="*60)
    
    fetcher = PaperFetcher(data_dir="data")
    print(f"Papers configured: {len(fetcher.PAPERS)}")
    
    # Just check if we can access papers
    for paper in fetcher.PAPERS:
        print(f"  - {paper['title'][:40]}... (arXiv {paper['arxiv_id']})")
    
    print("✓ Paper fetcher initialized")
    return True


def test_chunking():
    """Test semantic chunking."""
    print("\n" + "="*60)
    print("TEST 2: Semantic Chunking")
    print("="*60)
    
    test_text = """
    1. Introduction
    This is a test paper about machine learning.
    It has multiple sections.
    
    2. Related Work
    Previous research has explored various approaches.
    We build on this foundation.
    
    3. Methodology
    Our approach uses a novel technique.
    We evaluate on standard benchmarks.
    """
    
    for name, chunker in [
        ("Aggressive", ChunkingProfile.get_aggressive()),
        ("Balanced", ChunkingProfile.get_balanced()),
        ("Minimal", ChunkingProfile.get_minimal())
    ]:
        chunks = chunker.chunk_text(test_text, "test")
        print(f"  {name}: {len(chunks)} chunks")
    
    print("✓ Chunking works")
    return True


def test_embeddings():
    """Test embedding generation."""
    print("\n" + "="*60)
    print("TEST 3: Embeddings")
    print("="*60)
    
    print("Loading embedding model...")
    engine = EmbeddingEngine(model_name="all-MiniLM-L6-v2")
    
    test_chunks = [
        {"id": 0, "text": "Machine learning is a subset of artificial intelligence.", "char_count": 55},
        {"id": 1, "text": "Deep learning uses neural networks with many layers.", "char_count": 52},
        {"id": 2, "text": "Natural language processing handles human language.", "char_count": 51},
    ]
    
    print("Generating embeddings...")
    chunks_with_emb = engine.embed_chunks(test_chunks)
    
    print(f"  Generated {len(chunks_with_emb)} embeddings")
    print(f"  Embedding dimension: {chunks_with_emb[0]['embedding'].shape[0]}")
    
    # Test retrieval
    query = "What is deep learning?"
    results = engine.retrieve_top_k(query, chunks_with_emb, k=2)
    
    print(f"\nQuery: '{query}'")
    print(f"Top result (similarity {results[0]['similarity']:.3f}): {results[0]['text'][:50]}...")
    
    print("✓ Embeddings work")
    return True


def test_rate_limiting():
    """Test rate limiter."""
    print("\n" + "="*60)
    print("TEST 4: Rate Limiting")
    print("="*60)
    
    limiter = RateLimiter(rpm_limit=5, tpm_limit=1000)
    budget = TokenBudgetTracker(daily_token_limit=10000, budget_threshold=0.8)
    
    print("Simulating requests...")
    for i in range(10):
        wait = limiter.acquire(estimated_tokens=100)
        can_proceed, msg = budget.can_proceed(100)
        
        if i < 3:  # Only print first few
            print(f"  Request {i+1}: wait={wait:.2f}s, budget={'OK' if can_proceed else 'REFUSED'}")
        
        if can_proceed:
            budget.add_usage(100)
    
    stats = limiter.get_stats()
    print(f"\nRate limiter stats:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Wait events: {stats['wait_events']}")
    
    print("✓ Rate limiting works")
    return True


def test_standin_service():
    """Test stand-in service."""
    print("\n" + "="*60)
    print("TEST 5: Stand-in Service")
    print("="*60)
    
    service = StandinGroqService(
        rpm_limit=30,
        tpm_limit=14400,
        failure_rate=0.05
    )
    
    print("Testing stand-in API calls...")
    success_count = 0
    
    for i in range(5):
        result = service.chat_completion([
            {"role": "user", "content": f"Test question {i}"}
        ])
        
        if result["success"]:
            success_count += 1
            if i < 2:  # Only print first couple
                print(f"  Request {i+1}: ✓ {result['latency']*1000:.0f}ms, {result['usage']['total_tokens']} tokens")
        else:
            print(f"  Request {i+1}: ✗ {result['error']}")
    
    stats = service.get_stats()
    print(f"\nStand-in stats:")
    print(f"  Success rate: {stats['success_rate']*100:.1f}%")
    print(f"  Avg latency: {stats['avg_latency_ms']:.0f}ms")
    
    print("✓ Stand-in service works")
    return True


def test_questions():
    """Test question loading."""
    print("\n" + "="*60)
    print("TEST 6: Test Questions")
    print("="*60)
    
    print(f"Total questions loaded: {len(TEST_QUESTIONS)}")
    
    by_type = {}
    for q in TEST_QUESTIONS:
        qtype = q["type"]
        by_type[qtype] = by_type.get(qtype, 0) + 1
    
    print("By type:")
    for qtype, count in sorted(by_type.items()):
        print(f"  {qtype}: {count}")
    
    print("\nSample questions:")
    for q in TEST_QUESTIONS[:3]:
        print(f"  Q{q['id']}: {q['question'][:60]}...")
    
    print("✓ Test questions loaded")
    return True


def main():
    print("\n" + "="*80)
    print("RELAY PIPELINE QUICK TEST")
    print("="*80)
    
    # Create directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    tests = [
        ("Paper Fetching", test_paper_fetching),
        ("Chunking", test_chunking),
        ("Embeddings", test_embeddings),
        ("Rate Limiting", test_rate_limiting),
        ("Stand-in Service", test_standin_service),
        ("Test Questions", test_questions),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} FAILED: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✓ All systems operational!")
        print("\nNext steps:")
        print("  1. Add GROQ_API_KEY to .env file")
        print("  2. Run: python main.py")
    else:
        print(f"✗ {failed} test(s) failed")
    print("="*80)


if __name__ == "__main__":
    main()
