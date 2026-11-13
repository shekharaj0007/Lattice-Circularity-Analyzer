# Relay Pipeline - Quick Reference Card

## Installation (5 minutes)

```bash
cd relay_pipeline
pip install -r requirements.txt
cp .env.example .env
# Add GROQ_API_KEY to .env
```

## Verification

```bash
python verify_setup.py    # Check setup
python quick_test.py       # Test components
```

## Running

### Full Pipeline (~25 min, ~250 API calls)

```bash
python main.py
```

### Conservative (preserves API quota)

```bash
# Step 1: Measure API (~100 calls, 10 min)
python main.py --skip-quality --skip-load

# Step 2: Test quality (~60 calls, 5 min)
python main.py --skip-fetch --skip-measure --skip-load

# Step 3: Load test with stand-in (0 calls, 5 min)
python main.py --skip-fetch --skip-measure --skip-quality --use-standin
```

### Testing Chunking Strategies

```bash
# Compare all three profiles
python main.py --profile aggressive --skip-measure --skip-load
python main.py --profile balanced --skip-measure --skip-load
python main.py --profile minimal --skip-measure --skip-load
```

## Analysis

```bash
python analyze_results.py
```

Creates:
- `results/analysis_summary.json` - Key metrics
- `results/analysis_plots.png` - Performance plots
- `results/quality_plots.png` - Quality charts

## Results Files

```
results/
├── groq_measurements.json      # API latency, limits, tokens
├── groq_call_log.json          # Detailed call logs
├── quality_test_results.json   # Answer quality
├── load_test_real_*.csv        # Load test data (real)
├── load_test_standin_*.csv     # Load test data (stand-in)
└── load_test_*_summary.json    # Summary stats
```

## Key Metrics

### API Measurements
- Latency: mean, P95, P99
- Rate limits: RPM, TPM, daily
- Token usage patterns
- Error rates

### Quality Metrics
- Success rate
- Verification rate
- Quality scores
- Topic coverage

### Performance
- End-to-end latency
- Stage breakdowns
- Throughput
- Token usage per query

### Load Tests
- Success rate by scenario
- Latency under load
- Budget refusals
- Error distribution

## Common Commands

```bash
# Skip steps
python main.py --skip-fetch          # Use existing papers
python main.py --skip-measure        # Use defaults
python main.py --skip-quality        # Skip quality tests
python main.py --skip-load           # Skip load tests

# Use stand-in (no API calls)
python main.py --use-standin

# Change chunking
python main.py --profile aggressive  # 256 chars
python main.py --profile balanced    # 512 chars (default)
python main.py --profile minimal     # 1024 chars

# Combine options
python main.py --skip-measure --profile minimal --use-standin
```

## Analyzing Data in Python

```python
import pandas as pd
import json

# Load measurements
with open('results/groq_measurements.json') as f:
    measurements = json.load(f)

# Load load test results
df = pd.read_csv('results/load_test_real_20260113_120000.csv')

# Analyze
print("Success rate:", df['success'].mean())
print("Avg latency:", df[df['success']]['total_latency'].mean())
print("Avg tokens:", df[df['success']]['tokens_used'].mean())

# By scenario
print(df.groupby('scenario')['success'].mean())
print(df.groupby('scenario')['total_latency'].mean())
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "GROQ_API_KEY not set" | Add to `.env` file |
| "ModuleNotFoundError" | Run `pip install -r requirements.txt` |
| "Rate limit exceeded" | Wait or use `--use-standin` |
| Papers not downloading | Check internet, try later |
| Out of memory | Close other programs |

## Pipeline Architecture

```
Query → Intent → Retrieval → Generation → Verification → (Retry?) → Answer
         ↓         ↓            ↓             ↓
       Groq    Local Emb     Groq          Groq
      (<100ms)  (~50ms)     (~800ms)      (~500ms)
```

## Rate Limits (Groq Free Tier)

- **RPM**: 30 requests/minute
- **TPM**: 14,400 tokens/minute  
- **Daily**: 14,400 tokens/day
- **Refusal threshold**: 80% of daily (11,520 tokens)

## Chunking Profiles

| Profile | Chunk Size | Overlap | Top-K | Use Case |
|---------|------------|---------|-------|----------|
| Aggressive | 256 chars | 30 | 10 | Max coverage, high tokens |
| Balanced | 512 chars | 50 | 5 | Default, good balance |
| Minimal | 1024 chars | 100 | 3 | Less context, low tokens |

## Load Scenarios

1. **Steady Load**: Constant rate (10 req/min, 60s)
2. **Burst Load**: Periodic spikes (3 bursts of 8 req, 20s apart)
3. **Sustained Overload**: Above capacity (25 req/min, 60s)
4. **Ramp Up**: Increasing load (5→30 req/min over 60s)

## Test Questions

- **28 questions** across 3 papers
- **4 types**: 9 FACTUAL, 10 CONCEPTUAL, 6 COMPARATIVE, 3 PROCEDURAL
- **Papers**: 
  1. Attention Is All You Need (11 questions)
  2. Moshi (speech-text) (7 questions)
  3. Dynamic Chunking (5 questions)
  4. Cross-paper (5 questions)
- **Coverage**: Detail questions, conceptual depth, edge cases, cross-paper comparisons

## Quick Stats

- **Code**: ~4300 lines across 20 files
- **Documentation**: ~1450 lines across 4 guides
- **Tests**: 4 test scripts
- **Papers**: 3 from arXiv
- **Questions**: 18 with expected topics
- **Load scenarios**: 4 with detailed metrics

## Files to Read First

1. `README.md` - Comprehensive overview
2. `GETTING_STARTED.md` - Installation and usage
3. `PROJECT_SUMMARY.md` - What was built
4. This file - Quick commands

## Workflow for Writeup

```bash
# 1. Run pipeline
python main.py

# 2. Analyze results
python analyze_results.py

# 3. Get summary data
cat results/analysis_summary.json

# 4. Load CSV for tables
# Open in pandas/Excel

# 5. Use plots
# results/analysis_plots.png
# results/quality_plots.png
```

## API Usage Estimate

| Operation | Calls | Tokens | Time |
|-----------|-------|--------|------|
| Latency measurement | 25 | ~1500 | 3 min |
| Error rate test | 15 | ~750 | 2 min |
| Token usage test | 10 | ~800 | 2 min |
| Quality tests (15Q) | ~60 | ~3000 | 5 min |
| Load test (real) | 100+ | ~5000 | 10 min |
| **Total** | **~210** | **~11,000** | **~22 min** |

**Note**: Using `--use-standin` for load tests reduces to ~110 calls and ~5,000 tokens.

## Stand-in Service

Simulates Groq API without consuming quota:

- Realistic latency (calibrated from measurements)
- Rate limit enforcement
- Configurable failure rate (default 2%)
- Load degradation (>70% capacity)
- Streaming with TTFT

Enable:
```bash
python main.py --use-standin
```

## Extending

### Add Questions

Edit `src/test_questions.py`:
```python
TEST_QUESTIONS.append({
    "id": 100,
    "question": "...",
    "type": "CONCEPTUAL",
    "expected_topics": [...]
})
```

### Change Retrieval

Edit pipeline creation in `main.py`:
```python
Pipeline(..., top_k=10, rerank=True, max_retries=2)
```

### Custom Scenario

```python
from src import LoadScenario

scenario = {
    "name": "Custom",
    "duration": 120,
    "rate": 15,
    "pattern": "steady"
}
```

## Key Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Pipeline | `src/pipeline.py` | 450 | 4-stage RAG |
| Rate Limiter | `src/rate_limiter.py` | 200 | RPM/TPM/budget |
| Groq Client | `src/groq_client.py` | 250 | Instrumented API |
| Stand-in | `src/standin_service.py` | 300 | Simulated service |
| Embeddings | `src/embeddings.py` | 120 | Local retrieval |
| Load Tester | `src/load_tester.py` | 300 | Load scenarios |
| Measurement | `src/measure_groq.py` | 300 | API profiling |

## Environment Variables

```bash
# Required
GROQ_API_KEY=your_key_here

# Strategic Model Sizing (optimal cost/quality)
GROQ_INTENT_MODEL=llama-3.2-3b-preview       # Small/fast for intent
GROQ_GENERATION_MODEL=llama-3.1-70b-versatile # Large for generation
GROQ_VERIFICATION_MODEL=gemma2-9b-it          # Small/fast for verification

# Optional (defaults shown)
GROQ_MODEL=llama-3.1-8b-instant  # Fallback model
GROQ_RPM_LIMIT=30
GROQ_TPM_LIMIT=14400
GROQ_DAILY_TOKEN_LIMIT=14400
BUDGET_THRESHOLD=0.8
EMBEDDING_MODEL=all-MiniLM-L6-v2
MAX_RETRIES=1
```

## Model Selection Strategy

**Why different models?**
- **Intent/Verification**: Simple tasks → small/fast models save tokens
- **Generation**: Hard task → large models ensure quality
- **Retrieval**: Local embeddings → zero API cost

**Cost savings**: ~60% lower token usage vs. using large model for everything

---

**TIP**: Start with `python verify_setup.py` and `python quick_test.py` before the full run!

**TIP**: Use `--use-standin` for load tests to preserve API quota!

**TIP**: Run `analyze_results.py` after completing the pipeline for plots and summary!
