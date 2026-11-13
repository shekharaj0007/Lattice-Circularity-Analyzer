# Getting Started with Relay Pipeline

Quick start guide to get the pipeline running.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Internet connection (for downloading papers and API calls)
- Groq API key (free tier available)

## Installation

### 1. Navigate to project directory

```bash
cd relay_pipeline
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `groq` - Groq API client
- `sentence-transformers` - Local embeddings
- `torch` - ML framework
- `PyPDF2` - PDF processing
- `pandas`, `numpy`, `scikit-learn` - Data processing
- `matplotlib`, `seaborn` - Visualization
- Other utilities

**Note:** Installation may take 5-10 minutes due to PyTorch and transformer models.

### 3. Get Groq API Key

1. Visit https://console.groq.com/
2. Sign up for free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key

**Free tier limits:**
- 30 requests per minute (RPM)
- 14,400 tokens per minute (TPM)
- 14,400 tokens per day

### 4. Configure environment

```bash
# Copy example config
cp .env.example .env

# Edit .env and add your key
nano .env  # or use any text editor
```

Add this line to `.env`:
```
GROQ_API_KEY=your_actual_key_here
```

### 5. Verify setup

```bash
python verify_setup.py
```

This checks:
- File structure
- Python syntax
- Module imports
- Configuration

## Running the Pipeline

### Quick Test (No API calls)

Test the setup without consuming API quota:

```bash
python quick_test.py
```

This tests:
- Paper fetching setup
- Chunking algorithms
- Embeddings (downloads ~90MB model on first run)
- Rate limiting
- Stand-in service
- Test questions

### Full Pipeline

Run the complete pipeline:

```bash
python main.py
```

**What it does:**
1. Fetches 3 papers from arXiv (~5-10 MB)
2. Chunks papers into semantic segments
3. Generates local embeddings
4. Measures Groq API characteristics (~60 API calls, ~10 minutes)
5. Tests answer quality on 15 questions (~60 API calls)
6. Runs 3 load test scenarios (~100+ API calls)

**Total API usage:** ~200-250 API calls, ~5000-8000 tokens

**Duration:** 20-30 minutes

### Running Specific Steps

Skip steps you've already run:

```bash
# Skip paper fetching (if already downloaded)
python main.py --skip-fetch

# Skip Groq measurement (uses documented defaults)
python main.py --skip-measure

# Skip quality tests (only do load tests)
python main.py --skip-quality

# Use stand-in service for load tests (saves API quota)
python main.py --use-standin
```

### Recommended First Run

Conservative approach that preserves API quota:

```bash
# Step 1: Fetch papers and measure API (uses ~100 calls)
python main.py --skip-quality --skip-load

# Step 2: Test answer quality (uses ~60 calls)
python main.py --skip-fetch --skip-measure --skip-load

# Step 3: Load test with stand-in (uses ~0 real API calls)
python main.py --skip-fetch --skip-measure --skip-quality --use-standin
```

## Understanding Results

### Results Directory

All outputs are saved in `results/`:

```
results/
├── groq_measurements.json      # API latency, limits, token usage
├── groq_call_log.json          # Detailed per-call logs
├── quality_test_results.json   # Answer quality evaluations
├── load_test_real_*.csv        # Load test data (real API)
├── load_test_standin_*.csv     # Load test data (stand-in)
└── load_test_*_summary.json    # Summary statistics
```

### Analyzing Results

Generate summary and plots:

```bash
python analyze_results.py
```

This creates:
- `analysis_summary.json` - Key metrics table
- `analysis_plots.png` - Performance visualizations
- `quality_plots.png` - Answer quality charts
- Console output with detailed statistics

### Reading CSV Results

Load in Python:

```python
import pandas as pd

# Load load test results
df = pd.read_csv('results/load_test_real_20260113_120000.csv')

# Basic analysis
print(df['success'].mean())  # Success rate
print(df['total_latency'].mean())  # Avg latency
print(df['tokens_used'].mean())  # Avg tokens

# Group by scenario
print(df.groupby('scenario')['success'].mean())
```

Or open in Excel/Google Sheets for exploration.

## Testing Different Configurations

### Chunking Strategies

Compare retrieval approaches:

```bash
# More chunks, more context, higher token usage
python main.py --profile aggressive --skip-measure --skip-load

# Medium chunks (default)
python main.py --profile balanced --skip-measure --skip-load

# Fewer chunks, less context, lower token usage
python main.py --profile minimal --skip-measure --skip-load
```

Compare `quality_test_results.json` across runs to see which works best.

### Retrieval Parameters

Edit `main.py` to experiment:

```python
pipeline = Pipeline(
    # ... other params ...
    top_k=10,        # Retrieve more chunks
    rerank=True,     # Enable re-ranking
    max_retries=2    # More retry attempts
)
```

## Troubleshooting

### "ModuleNotFoundError"

Dependencies not installed:
```bash
pip install -r requirements.txt
```

### "GROQ_API_KEY not set"

Environment variable not configured:
```bash
cp .env.example .env
# Edit .env and add your key
```

Or set temporarily:
```bash
export GROQ_API_KEY=your_key_here
python main.py
```

### "Rate limit exceeded"

You've hit Groq's free tier limits:
- Wait 1 minute for RPM reset
- Wait 24 hours for daily token reset
- Use `--use-standin` for load tests
- Use `--skip-measure` to reduce API calls

### "Papers not downloading"

arXiv connection issues:
- Check internet connection
- Try again later (arXiv may be temporarily down)
- Check arXiv IDs in `src/paper_fetcher.py`

### Out of memory

Embedding model too large:
- Use smaller model in `src/embeddings.py`
- Reduce batch size in `embed_chunks()`
- Close other programs

### Slow performance

Normal for first run:
- Downloads models (~90MB)
- Downloads papers (~10MB)
- Generates embeddings (~2 mins)
- API calls have latency (~1s each)

Subsequent runs are faster (cached models/papers).

## What to Expect

### First Run Timeline

```
00:00 - Setup directories
00:10 - Fetch papers from arXiv (3 papers)
00:30 - Download embedding model (first time only)
02:30 - Generate embeddings for ~200 chunks
03:00 - Measure Groq API (60 requests, 10 mins)
13:00 - Test answer quality (15 questions, 5 mins)
18:00 - Load tests (3 scenarios, 7 mins)
25:00 - Complete! Results saved.
```

### API Quota Usage

**Careful measurements (~100 calls):**
- Latency distribution: 25 calls
- Error rates: 15 calls
- Token usage: 10 calls
- Quality tests: 15 calls
- Buffer: 35 calls

**Conservative load tests (stand-in):**
- Uses 0 real API calls
- Still generates realistic results

**Aggressive load tests (real API):**
- Can use 100-200+ calls
- May hit daily limit
- Recommended only after calibrating stand-in

## Next Steps

After running the pipeline:

1. **Review measurements**
   ```bash
   cat results/groq_measurements.json
   ```

2. **Analyze quality**
   ```bash
   python analyze_results.py
   ```

3. **Explore load test data**
   - Open CSV files in pandas/Excel
   - Compare scenarios
   - Check latency distributions

4. **Use data for writeup**
   - `analysis_summary.json` has key metrics
   - CSV files have detailed per-request data
   - Plots show distributions

5. **Experiment**
   - Try different chunking profiles
   - Adjust retrieval parameters
   - Test on custom questions
   - Calibrate stand-in more precisely

## Project Structure

```
relay_pipeline/
├── README.md                    # Comprehensive documentation
├── GETTING_STARTED.md           # This file
├── requirements.txt             # Dependencies
├── .env.example                 # Config template
├── main.py                      # Main orchestration script
├── analyze_results.py           # Results analysis
├── quick_test.py                # Quick functionality test
├── verify_setup.py              # Setup verification
│
├── src/                         # Source code
│   ├── __init__.py
│   ├── paper_fetcher.py         # arXiv paper download
│   ├── chunker.py               # Semantic chunking
│   ├── embeddings.py            # Local embeddings
│   ├── rate_limiter.py          # Rate limiting + budget
│   ├── groq_client.py           # Instrumented Groq client
│   ├── pipeline.py              # 4-stage RAG pipeline
│   ├── standin_service.py       # Simulated service
│   ├── test_questions.py        # Test question bank
│   ├── load_tester.py           # Load testing framework
│   └── measure_groq.py          # API measurement suite
│
├── data/                        # Downloaded papers (git-ignored)
├── results/                     # Output files (git-ignored)
└── standin/                     # Stand-in service files
```

## Support

For issues:
1. Check this guide
2. Review README.md for detailed docs
3. Check verify_setup.py output
4. Review error messages carefully

Common solutions:
- Missing dependencies → `pip install -r requirements.txt`
- Missing API key → Add to `.env` file
- Rate limits → Use `--use-standin` or wait
- Import errors → Check Python 3.8+ and dependencies

## Summary

**Minimal setup:**
```bash
pip install -r requirements.txt
cp .env.example .env
# Add GROQ_API_KEY to .env
python verify_setup.py
python quick_test.py
```

**Full run:**
```bash
python main.py
```

**Analysis:**
```bash
python analyze_results.py
```

You're ready to build and test your RAG pipeline! 🚀
