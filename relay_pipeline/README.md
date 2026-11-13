# Relay Assignment Pipeline

A complete RAG (Retrieval-Augmented Generation) pipeline implementation with comprehensive instrumentation, rate limiting, and load testing capabilities.

## Architecture

**4-Stage Pipeline:**
1. **Intent Classification** - Classifies query type (FACTUAL, CONCEPTUAL, COMPARATIVE, PROCEDURAL)
2. **Retrieval** - Semantic search with local embeddings
3. **Generation** - LLM-based answer generation using Groq API
4. **Verification** - Model-based quality verification with retry loop

**Key Features:**
- **Strategic Model Sizing**: Different models for different stages
  - Small/fast models for simple tasks (intent, verification)
  - Large/capable models for generation (where quality matters)
  - Optimal cost/quality tradeoff
- Centralized rate limiting with token budget tracking
- Refuses requests at 80% of daily budget
- Real Groq API integration with detailed instrumentation
- Local sentence-transformers embeddings (no API calls)
- Semantic chunking with section boundary detection
- Stand-in service for load testing without consuming API quota
- Comprehensive metrics and logging

## Setup

### 1. Install Dependencies

```bash
cd relay_pipeline
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file:

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

Get a free Groq API key at: https://console.groq.com/

### 3. Run the Pipeline

**Full pipeline (recommended first run):**
```bash
python main.py
```

**Skip certain steps:**
```bash
# Skip paper fetching if already downloaded
python main.py --skip-fetch

# Skip Groq measurement (uses conservative defaults)
python main.py --skip-measure

# Skip quality tests
python main.py --skip-quality

# Use stand-in service for load tests (doesn't consume API quota)
python main.py --use-standin
```

**Different chunking profiles:**
```bash
# Aggressive: small chunks, more retrieval
python main.py --profile aggressive

# Balanced: medium chunks (default)
python main.py --profile balanced

# Minimal: large chunks, less retrieval
python main.py --profile minimal
```

## Pipeline Steps

### Step 1: Fetch Papers

Fetches 3 papers from arXiv:
- "Attention Is All You Need" (arXiv 1706.03762v7)
- "Moshi: a speech-text foundation model for real-time dialogue" (arXiv 2410.00037v1)
- "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling" (arXiv 2507.07955v2)

### Step 2: Semantic Chunking

Splits papers into semantic chunks using:
- Section boundary detection (numbered sections, headers)
- Configurable chunk sizes with overlap
- Three profiles: aggressive (256 chars), balanced (512 chars), minimal (1024 chars)

### Step 3: Generate Embeddings

Creates vector embeddings using sentence-transformers:
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Local processing (no API calls)
- Batch processing for efficiency

### Step 4: Measure Groq API

Measures real API characteristics:
- Latency distribution (mean, std, percentiles)
- Time to first token (TTFT) for streaming
- Rate limits (RPM, TPM)
- Error rates
- Token usage patterns

**Conservative approach:** Uses documented limits instead of stress testing to avoid hitting rate limits.

### Step 5: Quality Testing

Tests answer quality on 28 questions:
- Covers all 3 papers (11 transformer, 7 Moshi, 5 dynamic chunking, 5 cross-paper)
- Multiple question types (9 factual, 10 conceptual, 6 comparative, 3 procedural)
- Includes edge cases to test refusal quality (cost data, GPT-4 comparisons)
- Detail questions (BLEU scores, latency requirements, model dimensions)
- Conceptual depth questions (multi-head rationale, complexity analysis)
- Evaluates topic coverage, verification status, answer length
- Computes quality scores (0-1)

### Step 6: Load Testing

Runs 3 load scenarios:
1. **Steady Load** - Constant request rate
2. **Burst Load** - Periodic spikes
3. **Sustained Overload** - Rate above capacity

Can use real Groq API or calibrated stand-in service.

## Results

All results are saved in `results/` directory:

### Measurements
- `groq_measurements.json` - API latency, limits, token usage
- `groq_call_log.json` - Detailed call-by-call logs

### Quality Tests
- `quality_test_results.json` - Answer quality evaluations
  - Per-question results
  - Topic coverage analysis
  - Verification status
  - Quality scores

### Load Tests
- `load_test_real_YYYYMMDD_HHMMSS.csv` - Detailed results (real API)
- `load_test_standin_YYYYMMDD_HHMMSS.csv` - Detailed results (stand-in)
- `load_test_*_summary.json` - Summary statistics

## Results Analysis

The CSV files contain per-request data:
- `scenario` - Load scenario name
- `query_id` - Request identifier
- `timestamp` - Time since scenario start
- `success` - Whether request succeeded
- `verified` - Whether answer passed verification
- `total_latency` - End-to-end latency
- `intent_latency`, `retrieval_latency`, `generation_latency`, `verification_latency`
- `tokens_used` - Total tokens consumed
- `retry_needed` - Whether retry loop was triggered
- `error` - Error message if failed

## Strategic Model Sizing

The pipeline uses **different models for different stages** to optimize cost and quality:

### Model Selection Strategy

**Small/Fast Models** (intent classification, verification):
- `llama-3.2-3b-preview` - Intent classification
- `gemma2-9b-it` - Verification
- **Why**: Simple tasks (categorization, checking) don't need large models
- **Benefit**: Save tokens on 50% of API calls

**Large/Capable Models** (generation):
- `llama-3.1-70b-versatile` - Answer generation
- **Why**: Generation is the hard task that needs quality
- **Benefit**: Spend tokens where it matters most

**Local Models** (retrieval):
- `all-MiniLM-L6-v2` - Embeddings
- **Why**: Semantic search doesn't need API calls
- **Benefit**: Zero API cost for retrieval

### Configuration

Set models in `.env`:

```bash
# Default/fallback
GROQ_MODEL=llama-3.1-8b-instant

# Small/fast for simple tasks
GROQ_INTENT_MODEL=llama-3.2-3b-preview
GROQ_VERIFICATION_MODEL=gemma2-9b-it

# Large/capable for generation
GROQ_GENERATION_MODEL=llama-3.1-70b-versatile
```

### Alternative Models

**Small/Fast Options:**
- `llama-3.2-1b-preview` - Fastest, minimal quality
- `llama-3.2-3b-preview` - Fast, good quality (recommended)
- `gemma-7b-it` - Balanced
- `gemma2-9b-it` - Better quality (recommended)

**Large/Capable Options:**
- `llama-3.1-70b-versatile` - High quality (recommended)
- `llama-3.3-70b-versatile` - Latest, best quality
- `mixtral-8x7b-32768` - Long context support

### Cost/Quality Tradeoff

**Without strategic sizing** (all stages use llama-3.1-70b):
- High quality across all stages
- ~3x token cost
- Slower (larger model latency)

**With strategic sizing** (mixed models):
- Same generation quality
- ~60% lower token cost (small models for 2/3 stages)
- Faster (small models for simple tasks)
- Better budget utilization

### Testing Different Combinations

Experiment with model combinations:

```bash
# Conservative: all small models
GROQ_INTENT_MODEL=llama-3.2-3b-preview
GROQ_GENERATION_MODEL=llama-3.1-70b-versatile  # still use large for gen
GROQ_VERIFICATION_MODEL=llama-3.2-3b-preview

# Balanced: mixed sizes (recommended)
GROQ_INTENT_MODEL=llama-3.2-3b-preview
GROQ_GENERATION_MODEL=llama-3.1-70b-versatile
GROQ_VERIFICATION_MODEL=gemma2-9b-it

# Aggressive: maximum quality
GROQ_INTENT_MODEL=gemma2-9b-it
GROQ_GENERATION_MODEL=llama-3.3-70b-versatile
GROQ_VERIFICATION_MODEL=gemma2-9b-it
```

Compare results in `quality_test_results.json` to find optimal balance.

## Architecture Components

### Rate Limiting (`rate_limiter.py`)
- **RateLimiter**: RPM/TPM tracking with wait time calculation
- **TokenBudgetTracker**: Daily budget monitoring
- Refuses requests at 80% threshold
- Thread-safe with detailed metrics

### Pipeline (`pipeline.py`)
- 4-stage processing with retry loop
- Comprehensive instrumentation
- Per-stage timing and token tracking
- Query logging for analysis

### Embeddings (`embeddings.py`)
- Local sentence-transformers
- Cosine similarity search
- Optional re-ranking
- Batch processing

### Stand-in Service (`standin_service.py`)
- Simulates Groq API behavior
- Realistic latency distribution
- Rate limit enforcement
- Configurable failure rates
- Load-dependent degradation
- Calibrates from real measurements

## Testing Different Configurations

### Chunking Strategies

Test all three profiles to compare retrieval quality:

```bash
# Aggressive: more chunks, more context, higher token usage
python main.py --profile aggressive --skip-measure

# Balanced: medium chunks (recommended)
python main.py --profile balanced --skip-measure

# Minimal: fewer chunks, less context, lower token usage
python main.py --profile minimal --skip-measure
```

Compare `quality_test_results.json` across runs.

### Load Testing Strategy

1. **Measure real API first:**
   ```bash
   python main.py --skip-quality --skip-load
   ```

2. **Run quality tests with real API:**
   ```bash
   python main.py --skip-fetch --skip-measure --skip-load
   ```

3. **Run load tests with stand-in:**
   ```bash
   python main.py --skip-fetch --skip-measure --skip-quality --use-standin
   ```

This preserves API quota while still measuring performance under load.

## Stand-in Service

The stand-in service (`StandinGroqService`) simulates Groq API with:
- **Latency simulation**: Normal distribution based on measurements
- **Rate limiting**: RPM/TPM enforcement
- **Failures**: Configurable error rate (default 2%)
- **Load degradation**: Slowdown at >70% capacity
- **Streaming**: Token-by-token delays with TTFT

Calibrate from real measurements:
```python
from src import StandinGroqService
import json

# Load measurements
with open('results/groq_measurements.json') as f:
    measurements = json.load(f)

# Calibrate stand-in
service = StandinGroqService()
service.calibrate(measurements)
```

## Extending the Pipeline

### Add Custom Questions

Edit `src/test_questions.py`:

```python
TEST_QUESTIONS.append({
    "id": 100,
    "question": "Your question here",
    "paper": "Paper name",
    "type": "CONCEPTUAL",
    "expected_topics": ["topic1", "topic2"]
})
```

### Change Retrieval Parameters

In `main.py` or when creating Pipeline:

```python
pipeline = Pipeline(
    groq_client=groq_client,
    embedding_engine=embedding_engine,
    rate_limiter=rate_limiter,
    budget_tracker=budget_tracker,
    chunks=chunks,
    top_k=10,          # Retrieve more chunks
    rerank=True,       # Enable re-ranking
    max_retries=2      # More retry attempts
)
```

### Add Custom Load Scenarios

In your script:

```python
from src import LoadScenario

custom_scenario = {
    "name": "Custom Scenario",
    "duration": 120,
    "rate": 15,
    "pattern": "steady",
    "description": "Custom load pattern"
}

tester.run_scenario(custom_scenario)
```

## Troubleshooting

### "GROQ_API_KEY not set"
- Create `.env` file with `GROQ_API_KEY=your_key_here`
- Or set environment variable: `export GROQ_API_KEY=your_key_here`

### Rate limit errors during measurement
- Use `--skip-measure` to use conservative defaults
- Reduce request counts in `measure_groq.py`

### Out of memory during embedding
- Reduce batch size in `embeddings.py`
- Use smaller embedding model

### Papers not downloading
- Check internet connection
- Verify arXiv IDs in `paper_fetcher.py`
- arXiv may have temporary issues - try again later

## Data for Writeup

Key files for analysis:
1. `groq_measurements.json` - Latency distribution, limits
2. `quality_test_results.json` - Answer quality metrics
3. `load_test_*.csv` - Performance under load
4. CSV can be loaded in pandas for tables/plots

Example analysis:
```python
import pandas as pd
import json

# Load measurements
with open('results/groq_measurements.json') as f:
    measurements = json.load(f)

# Load quality results
with open('results/quality_test_results.json') as f:
    quality = json.load(f)

# Load load test results
df = pd.read_csv('results/load_test_real_20260113_045500.csv')

# Analyze
print("Latency p95:", measurements['latency_distribution']['p95'])
print("Success rate:", df['success'].mean())
print("Avg tokens:", df['tokens_used'].mean())
```

## License

Educational project for The Relay Assignment.
