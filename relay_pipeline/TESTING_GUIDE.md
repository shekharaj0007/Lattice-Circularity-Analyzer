# Testing Guide - Relay Pipeline with P0 Features

## Overview

This guide covers testing the complete pipeline with newly implemented P0 correctness features:
- Citation system
- Evidence gate
- Prompt size caps
- Two-strike refusal logic

## Prerequisites

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 3. Verify setup
python verify_setup.py
```

## Testing Phases

### Phase 1: Measure Groq Limits (~10 min, ~50 API calls)

**Purpose**: Characterize real API for stand-in calibration

```bash
# Run measurement suite (conservative)
cd relay_pipeline
python -c "
import sys
sys.path.insert(0, 'src')
from measure_groq import GroqMeasurement

measurer = GroqMeasurement()
measurements = measurer.run_full_measurement()

measurer.save_measurements('results/groq_measurements.json')
measurer.save_call_log('results/groq_call_log.json')

print('\n✅ Measurements complete!')
print(f'Latency: {measurements[\"latency_distribution\"][\"mean\"]:.0f}ms')
print(f'TPM limit: {measurements[\"rate_limits\"][\"tpm_observed\"]}')
"
```

**Expected Output**:
- `results/groq_measurements.json` - Latency, limits, token usage
- `results/groq_call_log.json` - Detailed logs

**Metrics to Check**:
- Mean latency ~800ms
- P95 latency <2000ms
- RPM limit: 30
- TPM limit: 14,400

---

### Phase 2: Quality Tests (~15 min, ~112 API calls)

**Purpose**: Test all 28 questions with P0 features

```bash
# Run quality tests
python main.py --skip-fetch --skip-measure --skip-load

# Or step by step:
cd relay_pipeline
python -c "
import os
os.makedirs('results', exist_ok=True)

# Run quality tests
import sys
sys.path.insert(0, 'src')

# ... (quality test code)
"
```

**Expected Output**:
- `results/quality_test_results.json`

**Metrics to Check**:
```json
{
  "total": 28,
  "successful": 20-25,
  "verified": 18-22,
  "avg_quality": 0.65-0.80,
  "evidence_gate_refusals": 2-4,
  "citation_failures": 0-2
}
```

**Key P0 Feature Tests**:

1. **Evidence Gate** - Should refuse edge cases:
   - Q26 (cost data): "Papers don't appear to answer this"
   - Q27 (GPT-4 comparison): Weak evidence refusal

2. **Citation System** - Should extract and verify:
   - Format: `[Paper v7, p.3, chunk c1]`
   - Correct versions (v7/v1/v2)
   - Chunk IDs match retrieved

3. **Two-Strike Refusal** - Should refuse after 2 failures:
   - Never return unverified answer
   - Track refusal reason

---

### Phase 3: Load Tests (5-10 min, 0 real API calls)

**Purpose**: Test performance under load using stand-in

```bash
# Calibrate stand-in from Phase 1
python main.py --skip-fetch --skip-measure --skip-quality --use-standin

# Or individual load test:
cd relay_pipeline
python -c "
import sys
sys.path.insert(0, 'src')
from load_tester import LoadTester, LoadScenario
from standin_service import StandinGroqService
import json

# Load calibration
with open('results/groq_measurements.json') as f:
    measurements = json.load(f)

# Calibrate stand-in
service = StandinGroqService()
service.calibrate(measurements)

# Run scenarios...
"
```

**Expected Output**:
- `results/load_test_standin_*.csv`
- `results/load_test_standin_summary_*.json`

**Scenarios**:
1. Steady load (10 req/min, 60s) → ~10 requests
2. Burst load (3 bursts × 8 req) → ~24 requests
3. Sustained overload (25 req/min, 60s) → ~25 requests, some refusals
4. Ramp up (5→30 req/min, 60s) → ~15 requests

**Metrics to Check**:
- Success rate >90% for steady/burst
- Success rate 60-80% for overload (budget refusals expected)
- Evidence gate saves ~400 tokens per refusal

---

### Phase 4: Analyze Results (1 min)

**Purpose**: Generate summary tables and plots

```bash
python analyze_results.py
```

**Expected Output**:
- `results/analysis_summary.json`
- `results/analysis_plots.png`
- `results/quality_plots.png`

**Key Metrics**:
```json
{
  "API Latency (mean)": "850 ms",
  "API Latency (P95)": "1500 ms",
  "TPM Limit": 14400,
  "Questions Answered": "23/28",
  "Verification Rate": "85-90%",
  "Avg Quality Score": "0.72",
  "Evidence Gate Refusals": "3-5",
  "Tokens Saved by Gate": "1200-2000",
  "Citation Success Rate": "90-95%"
}
```

---

## Testing P0 Features Specifically

### 1. Citation System

**Test Citation Extraction**:
```python
from src.citations import CitationExtractor

extractor = CitationExtractor()

# Test valid citation
answer = "The transformer has 6 layers [Attention Is All You Need v7, p.5, chunk c2]."
citations = extractor.extract_citations(answer)

assert len(citations) == 1
assert citations[0]["version"] == "v7"
assert citations[0]["chunk_id"] == 2
print("✓ Citation extraction works")

# Test verification
chunks = [
    {"id": 2, "text": "The model consists of 6 encoder and 6 decoder layers"}
]
valid, issues = extractor.verify_citations(answer, citations, chunks)
print(f"Valid: {valid}, Issues: {issues}")

# Test fabricated quote detection
answer_with_fake = 'The paper says "this is a fake quote" about transformers.'
valid, msg = extractor.verify_no_fabrication(answer_with_fake, chunks)
print(f"Fabricated quote detected: {not valid}")
```

**Expected**:
- ✓ Extracts citations correctly
- ✓ Verifies against chunks
- ✓ Detects fabricated quotes

### 2. Evidence Gate

**Test Evidence Assessment**:
```python
from src.evidence_gate import EvidenceGate

gate = EvidenceGate()

# Test weak evidence
weak_chunks = [
    {"id": 1, "text": "Not relevant", "similarity": 0.35}
]
proceed, reason, meta = gate.assess_evidence(weak_chunks, "test query")

assert not proceed
assert "don't appear to answer" in reason
assert meta["decision"] == "refuse"
print(f"✓ Weak evidence refused: {reason[:50]}...")

# Test strong evidence
strong_chunks = [
    {"id": 1, "text": "Relevant text", "similarity": 0.85}
]
proceed, reason, meta = gate.assess_evidence(strong_chunks, "test query")

assert proceed
assert meta["decision"] == "proceed"
print(f"✓ Strong evidence proceeds")

# Check token savings
stats = gate.get_stats()
print(f"✓ Tokens saved: {stats['tokens_saved']}")
```

**Expected**:
- ✓ Refuses weak evidence
- ✓ Proceeds with strong evidence
- ✓ Tracks tokens saved

### 3. Prompt Size Caps

**Verify in Pipeline**:
```python
from src.pipeline import Pipeline

# Check constants
assert Pipeline.MAX_PROMPT_TOKENS == 4000
assert Pipeline.MAX_CONTEXT_CHARS == 3000
print("✓ Prompt size caps configured")

# Context building should truncate
# (Tested implicitly in quality tests)
```

**Expected**:
- ✓ Caps defined
- ✓ No token limit errors during tests

### 4. Two-Strike Refusal

**Test in Pipeline**:
```python
# This is tested during quality tests
# Look for queries with:
# - "refusal": true
# - "refusal_reason": "Answer failed verification twice"
# - verification_attempts: 2

# These should NOT count as success
```

**Expected**:
- ✓ Refuses after 2 verification failures
- ✓ success=False for refusals
- ✓ Tracks refusal reason

---

## Verifying Results

### 1. Check P0 Feature Usage

```python
import json

with open('results/quality_test_results.json') as f:
    results = json.load(f)

# Count evidence gate refusals
refusals = [r for r in results if r.get('refusal') and 'evidence' in r.get('refusal_reason', '')]
print(f"Evidence gate refusals: {len(refusals)}")

# Count citation failures  
citation_fails = [r for r in results if r.get('refusal') and 'verification' in r.get('refusal_reason', '')]
print(f"Citation failures: {len(citation_fails)}")

# Check successful with citations
successful = [r for r in results if r.get('success')]
print(f"Successful answers: {len(successful)}")
```

### 2. Validate Data for Writeup

**Required Files**:
- ✅ `groq_measurements.json` - API characteristics
- ✅ `quality_test_results.json` - Answer quality
- ✅ `load_test_*.csv` - Performance data
- ✅ `analysis_summary.json` - Key metrics

**Key Metrics for Tables**:
1. API Latency (mean, P95, P99)
2. Rate Limits (RPM, TPM, daily)
3. Question Success Rate
4. Verification Rate
5. Citation Success Rate
6. Evidence Gate Refusal Rate
7. Tokens Saved by Gate
8. Quality Scores by Type

---

## Troubleshooting

### Issue: Rate Limit Errors

**Solution**: Tests are conservative, but if you hit limits:
```bash
# Use stand-in for all tests
python main.py --use-standin

# Or wait 1 minute and retry
```

### Issue: Verification Failing Too Much

**Possible Causes**:
1. Citations not being included by generation model
2. Chunk IDs not matching
3. Thresholds too strict

**Debug**:
```python
# Check if citations are in answers
with open('results/quality_test_results.json') as f:
    results = json.load(f)

for r in results[:5]:
    if r.get('success'):
        answer = r.get('answer', '')
        has_citation = '[' in answer and 'chunk c' in answer
        print(f"Q{r['query_id']}: Citations present: {has_citation}")
```

### Issue: Evidence Gate Refusing Too Much

**Solution**: Lower thresholds
```python
# In evidence_gate.py or pipeline initialization
gate = EvidenceGate(
    strong_threshold=0.70,  # Was 0.75
    weak_threshold=0.45     # Was 0.50
)
```

---

## Expected Timeline

**With API Key** (~25-30 minutes total):
1. Phase 1 (Measure): ~10 min
2. Phase 2 (Quality): ~15 min  
3. Phase 3 (Load): ~5 min
4. Phase 4 (Analyze): ~1 min

**Without API Key** (stand-in only, ~10 minutes):
1. Skip Phase 1
2. Skip Phase 2
3. Phase 3 (Load): ~5 min
4. Phase 4 (Analyze): ~1 min (limited data)

---

## Success Criteria

After all phases:

✅ **Measurements**:
- Latency distribution captured
- Rate limits confirmed
- Token patterns measured

✅ **Quality**:
- 20-25/28 questions answered
- 85-90% verification rate
- 3-5 evidence gate refusals (edge cases)
- 0-2 citation failures
- Avg quality score 0.65-0.80

✅ **Load Performance**:
- Steady load: >95% success
- Burst load: >90% success
- Overload: 60-80% success (budget refusals expected)

✅ **P0 Features Working**:
- Citations extracted and verified
- Evidence gate saves ~400 tokens/refusal
- Two-strike refusal never returns unverified
- Prompt caps prevent errors

✅ **Data Ready**:
- All JSON files generated
- CSV files for tables
- Plots for visualization
- Metrics ready for writeup

---

## Quick Reference Commands

```bash
# Full test suite (with API key)
python main.py

# Individual phases
python main.py --skip-quality --skip-load  # Phase 1 only
python main.py --skip-fetch --skip-measure --skip-load  # Phase 2 only
python main.py --skip-fetch --skip-measure --skip-quality --use-standin  # Phase 3 only

# Analyze
python analyze_results.py

# Verify P0 features
python src/citations.py
python src/evidence_gate.py
```

---

## Notes

- Total API calls: ~160 (well within daily 14,400 limit)
- Stand-in preserves quota for quality tests
- Conservative approach: measure, don't stress test
- Results reproducible with fixed random seeds

---

**Testing Guide Complete** - Ready to execute all phases!
