"""
Main orchestration script for Relay Assignment Pipeline.

This script:
1. Fetches papers from arXiv
2. Processes and chunks them
3. Generates embeddings
4. Measures real Groq API
5. Runs quality tests
6. Runs load tests
7. Calibrates stand-in service
8. Collects all results
"""

import os
import sys
import argparse
from datetime import datetime
import json
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src import (
    PaperFetcher,
    ChunkingProfile,
    EmbeddingEngine,
    RateLimiter,
    TokenBudgetTracker,
    InstrumentedGroqClient,
    Pipeline,
    StandinGroqService,
    TEST_QUESTIONS,
    evaluate_answer_quality,
    LoadTester,
    LoadScenario,
    GroqMeasurement
)

load_dotenv()


def setup_directories():
    """Create necessary directories."""
    dirs = ['data', 'results', 'results/logs']
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def step1_fetch_papers():
    """Step 1: Fetch arXiv papers."""
    print("\n" + "="*80)
    print("STEP 1: Fetching Papers from arXiv")
    print("="*80)
    
    fetcher = PaperFetcher(data_dir="data")
    paper_paths = fetcher.fetch_all_papers()
    papers_data = fetcher.extract_all_texts(paper_paths)
    
    print(f"\n✓ Fetched and extracted {len(papers_data)} papers")
    return papers_data


def step2_create_chunks(papers_data, profile_name="balanced"):
    """Step 2: Create semantic chunks."""
    print("\n" + "="*80)
    print(f"STEP 2: Creating Semantic Chunks ({profile_name} profile)")
    print("="*80)
    
    # Get chunker profile
    if profile_name == "aggressive":
        chunker = ChunkingProfile.get_aggressive()
    elif profile_name == "minimal":
        chunker = ChunkingProfile.get_minimal()
    else:
        chunker = ChunkingProfile.get_balanced()
    
    all_chunks = []
    for paper in papers_data:
        chunks = chunker.chunk_text(paper["text"], source=paper["filename"])
        all_chunks.extend(chunks)
    
    print(f"✓ Created {len(all_chunks)} chunks")
    print(f"  Avg chunk size: {sum(c['char_count'] for c in all_chunks) / len(all_chunks):.0f} chars")
    
    return all_chunks


def step3_generate_embeddings(chunks):
    """Step 3: Generate embeddings."""
    print("\n" + "="*80)
    print("STEP 3: Generating Embeddings")
    print("="*80)
    
    embedding_engine = EmbeddingEngine(model_name="all-MiniLM-L6-v2")
    chunks_with_embeddings = embedding_engine.embed_chunks(chunks)
    
    print(f"✓ Generated embeddings for {len(chunks_with_embeddings)} chunks")
    
    return chunks_with_embeddings, embedding_engine


def step4_measure_groq():
    """Step 4: Measure real Groq API."""
    print("\n" + "="*80)
    print("STEP 4: Measuring Real Groq API")
    print("="*80)
    
    if not os.getenv("GROQ_API_KEY"):
        print("⚠ GROQ_API_KEY not set - skipping real measurements")
        return None
    
    measurer = GroqMeasurement()
    measurements = measurer.run_full_measurement()
    
    # Save measurements
    measurer.save_measurements("results/groq_measurements.json")
    measurer.save_call_log("results/groq_call_log.json")
    
    return measurements


def step5_test_answer_quality(chunks, embedding_engine, measurements):
    """Step 5: Test answer quality on test questions."""
    print("\n" + "="*80)
    print("STEP 5: Testing Answer Quality")
    print("="*80)
    
    if not os.getenv("GROQ_API_KEY"):
        print("⚠ GROQ_API_KEY not set - skipping quality tests")
        return None
    
    # Create pipeline with strategic model sizing
    # Default/fallback client
    groq_client = InstrumentedGroqClient(
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    )
    
    # Stage-specific clients for optimal cost/quality
    intent_client = InstrumentedGroqClient(
        model=os.getenv("GROQ_INTENT_MODEL", "llama-3.2-3b-preview")
    )
    generation_client = InstrumentedGroqClient(
        model=os.getenv("GROQ_GENERATION_MODEL", "llama-3.1-70b-versatile")
    )
    verification_client = InstrumentedGroqClient(
        model=os.getenv("GROQ_VERIFICATION_MODEL", "gemma2-9b-it")
    )
    
    rate_limiter = RateLimiter(rpm_limit=30, tpm_limit=14400)
    budget_tracker = TokenBudgetTracker(daily_token_limit=14400, budget_threshold=0.8)
    
    pipeline = Pipeline(
        groq_client=groq_client,
        embedding_engine=embedding_engine,
        rate_limiter=rate_limiter,
        budget_tracker=budget_tracker,
        chunks=chunks,
        top_k=5,
        rerank=False,
        max_retries=1,
        intent_client=intent_client,
        generation_client=generation_client,
        verification_client=verification_client
    )
    
    print(f"\nModel Configuration:")
    print(f"  Intent: {intent_client.model}")
    print(f"  Generation: {generation_client.model}")
    print(f"  Verification: {verification_client.model}")
    
    # Test on subset of questions
    test_questions = TEST_QUESTIONS[:15]
    results = []
    
    print(f"Testing {len(test_questions)} questions...")
    
    for i, q in enumerate(test_questions):
        print(f"\nQ{i+1}/{len(test_questions)}: {q['question']}")
        
        result = pipeline.process_query(q["question"], query_id=q["id"])
        
        if result["success"]:
            # Evaluate quality
            quality = evaluate_answer_quality(
                result["answer"],
                q["expected_topics"],
                result["verified"]
            )
            
            result["quality_eval"] = quality
            
            print(f"  ✓ Success (verified={result['verified']}, quality={quality['quality_score']:.2f})")
            print(f"    Topics: {quality['topics_found']}/{quality['topics_expected']}")
            print(f"    Answer: {result['answer'][:100]}...")
        else:
            print(f"  ✗ Failed: {result.get('error', 'Unknown')}")
        
        results.append(result)
    
    # Save results
    with open("results/quality_test_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    successful = [r for r in results if r.get("success")]
    verified = [r for r in successful if r.get("verified")]
    avg_quality = sum(r["quality_eval"]["quality_score"] for r in successful) / len(successful) if successful else 0
    
    print(f"\n{'='*80}")
    print("Quality Test Summary:")
    print(f"  Questions answered: {len(successful)}/{len(test_questions)}")
    print(f"  Verified answers: {len(verified)}/{len(successful)}")
    print(f"  Average quality score: {avg_quality:.2f}")
    print(f"  Pipeline stats: {pipeline.get_stats()}")
    print(f"{'='*80}")
    
    return {
        "results": results,
        "summary": {
            "total": len(test_questions),
            "successful": len(successful),
            "verified": len(verified),
            "avg_quality": avg_quality
        }
    }


def step6_run_load_tests(chunks, embedding_engine, use_standin=False):
    """Step 6: Run load tests."""
    print("\n" + "="*80)
    print(f"STEP 6: Running Load Tests ({'Stand-in' if use_standin else 'Real Groq'})")
    print("="*80)
    
    if not use_standin and not os.getenv("GROQ_API_KEY"):
        print("⚠ GROQ_API_KEY not set and not using stand-in - skipping load tests")
        return None
    
    # Define scenarios
    scenarios = [
        LoadScenario.steady_load(duration_seconds=60, rate_per_minute=10),
        LoadScenario.burst_load(num_bursts=3, requests_per_burst=8, burst_interval=20),
        LoadScenario.sustained_overload(duration_seconds=60, rate_per_minute=25),
    ]
    
    def pipeline_factory():
        """Create a new pipeline instance."""
        if use_standin:
            # Use stand-in service
            from src.standin_service import StandinGroqService
            
            # Load calibration if available
            calibration = {}
            if os.path.exists("results/groq_measurements.json"):
                with open("results/groq_measurements.json") as f:
                    data = json.load(f)
                    if "latency_distribution" in data:
                        calibration = data
            
            service = StandinGroqService()
            if calibration:
                service.calibrate(calibration)
            
            groq_client = service
            # For stand-in, use same client for all stages
            intent_client = service
            generation_client = service
            verification_client = service
        else:
            # Strategic model sizing for real API
            groq_client = InstrumentedGroqClient(
                model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
            )
            intent_client = InstrumentedGroqClient(
                model=os.getenv("GROQ_INTENT_MODEL", "llama-3.2-3b-preview")
            )
            generation_client = InstrumentedGroqClient(
                model=os.getenv("GROQ_GENERATION_MODEL", "llama-3.1-70b-versatile")
            )
            verification_client = InstrumentedGroqClient(
                model=os.getenv("GROQ_VERIFICATION_MODEL", "gemma2-9b-it")
            )
        
        rate_limiter = RateLimiter(rpm_limit=30, tpm_limit=14400)
        budget_tracker = TokenBudgetTracker(daily_token_limit=14400, budget_threshold=0.8)
        
        return Pipeline(
            groq_client=groq_client,
            embedding_engine=embedding_engine,
            rate_limiter=rate_limiter,
            budget_tracker=budget_tracker,
            chunks=chunks,
            top_k=5,
            rerank=False,
            max_retries=1,
            intent_client=intent_client,
            generation_client=generation_client,
            verification_client=verification_client
        )
    
    # Run load tests
    tester = LoadTester(pipeline_factory, TEST_QUESTIONS)
    scenario_results = []
    
    for scenario in scenarios:
        result = tester.run_scenario(scenario)
        scenario_results.append(result)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    service_type = "standin" if use_standin else "real"
    
    df = tester.save_results_csv(
        scenario_results,
        f"results/load_test_{service_type}_{timestamp}.csv"
    )
    
    with open(f"results/load_test_{service_type}_summary_{timestamp}.json", 'w') as f:
        # Remove detailed results before saving summary
        summary_results = []
        for sr in scenario_results:
            sr_copy = sr.copy()
            sr_copy["results"] = f"{len(sr_copy['results'])} results (see CSV)"
            summary_results.append(sr_copy)
        
        json.dump(summary_results, f, indent=2)
    
    print(f"\n✓ Load test results saved")
    
    return scenario_results


def main():
    parser = argparse.ArgumentParser(description="Run Relay Assignment Pipeline")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip paper fetching")
    parser.add_argument("--skip-measure", action="store_true", help="Skip Groq measurement")
    parser.add_argument("--skip-quality", action="store_true", help="Skip quality tests")
    parser.add_argument("--skip-load", action="store_true", help="Skip load tests")
    parser.add_argument("--profile", choices=["aggressive", "balanced", "minimal"], 
                       default="balanced", help="Chunking profile")
    parser.add_argument("--use-standin", action="store_true", help="Use stand-in service for load tests")
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("RELAY ASSIGNMENT PIPELINE")
    print("="*80)
    
    setup_directories()
    
    # Step 1: Fetch papers
    if args.skip_fetch and os.path.exists("data"):
        print("\n⏭ Skipping paper fetch (using existing)")
        fetcher = PaperFetcher(data_dir="data")
        papers_data = []
        for paper in fetcher.PAPERS:
            filepath = os.path.join("data", f"{paper['title'][:30]}_{paper['arxiv_id']}.pdf")
            if os.path.exists(filepath):
                text = fetcher.extract_text_from_pdf(filepath)
                if text:
                    papers_data.append({
                        "path": filepath,
                        "filename": os.path.basename(filepath),
                        "text": text,
                        "char_count": len(text)
                    })
    else:
        papers_data = step1_fetch_papers()
    
    if not papers_data:
        print("❌ No papers available. Run without --skip-fetch")
        return
    
    # Step 2: Create chunks
    chunks = step2_create_chunks(papers_data, profile_name=args.profile)
    
    # Step 3: Generate embeddings
    chunks_with_embeddings, embedding_engine = step3_generate_embeddings(chunks)
    
    # Step 4: Measure Groq
    measurements = None
    if not args.skip_measure:
        measurements = step4_measure_groq()
    
    # Step 5: Quality tests
    if not args.skip_quality:
        quality_results = step5_test_answer_quality(
            chunks_with_embeddings, 
            embedding_engine, 
            measurements
        )
    
    # Step 6: Load tests
    if not args.skip_load:
        load_results = step6_run_load_tests(
            chunks_with_embeddings,
            embedding_engine,
            use_standin=args.use_standin
        )
    
    print("\n" + "="*80)
    print("✓ PIPELINE COMPLETE")
    print("="*80)
    print("\nResults saved in results/ directory:")
    print("  - groq_measurements.json: Real API measurements")
    print("  - groq_call_log.json: Detailed call logs")
    print("  - quality_test_results.json: Answer quality evaluation")
    print("  - load_test_*.csv: Load test detailed results")
    print("  - load_test_*_summary.json: Load test summaries")
    print("\nNext steps:")
    print("  1. Review results/groq_measurements.json for calibration data")
    print("  2. Check quality_test_results.json for answer quality")
    print("  3. Analyze load_test CSVs for performance under load")
    print("  4. Use this data for the 2-page writeup")


if __name__ == "__main__":
    main()
