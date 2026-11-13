# How to Test Citation Fix

The citation extraction has been fixed with much more explicit prompts. Here's how to verify it works:

## Quick Test (5 seconds)

```bash
cd relay_pipeline

# Test citation generation
python debug_citations.py
```

**Expected output**:
```
Test 2: Improved Prompt (More Explicit)
Model: <your-model>
Raw Output: The Transformer encoder has 6 layers [Attention Is All You Need v7, p.3, chunk c1]...

Citations found: 1
  - {'paper': 'Attention Is All You Need', 'version': 'v7', ...}
✅ CITATIONS EXTRACTED SUCCESSFULLY
```

## Full Pipeline Test (15-20 minutes)

```bash
# 1. Enable debug logging to see what models output
export DEBUG_CITATIONS=true

# 2. Run quality tests
python main.py --skip-fetch --skip-measure --skip-load
```

**What to look for**:
```
Testing Q1 (FACTUAL): How many layers does the Transformer encoder have?
[DEBUG] Generation output (180 chars):
The Transformer encoder consists of 6 layers [Attention Is All You Need v7, p.3, chunk c1]...
[DEBUG] Citations found: 1

✓ Verification passed
```

## What Changed

### 1. Much More Explicit Prompt

**Before**:
> Include citations in format: [Paper vN, p.PAGE, chunk cID]

**After**:
> CRITICAL: You MUST cite every claim using this EXACT format:
> [Paper Name vN, p.PAGE, chunk cID]
>
> Papers in context:
> - "Attention Is All You Need" v7
> - "Moshi" v1
> 
> Example: The encoder has 6 layers [Attention Is All You Need v7, p.3, chunk c1].

### 2. Context Shows Paper Names

**Before**:
```
[Chunk c1]: The encoder has 6 layers...
```

**After**:
```
[Chunk c1 from Attention Is All You Need]: The encoder has 6 layers...
```

## Expected Improvements

| Metric | Before | After |
|--------|--------|-------|
| Citations found | 0/15 | 12-15/15 |
| Verification passed | 0/15 | 10-14/15 |
| Success rate | 0% | 80-90% |

## If Still Seeing Issues

### No citations extracted

Check debug output:
```bash
python debug_citations.py
```

Look at "Test 2" output - does it include square brackets and paper names?

### Wrong citation format

If model uses different format (e.g., `[Paper v7, p.3, c1]` without "chunk"), update regex in `src/citations.py`:

```python
# Line 29, change:
CITATION_PATTERN = r'\[([^\]]+?)\s+v(\d+),\s*p\.(\d+),\s*chunk\s+c(\d+)\]'

# To (no "chunk" keyword):
CITATION_PATTERN = r'\[([^\]]+?)\s+v(\d+),\s*p\.(\d+),\s*c(\d+)\]'
```

### Answers cut off mid-sentence

Increase max_tokens in `src/pipeline.py` line 426:
```python
# Change from 400 to 600
result = self.generation_client.chat_completion(messages, max_tokens=600, temperature=0.7)
```

## Debug Logging

The fix includes optional debug logging. Enable with:

```bash
export DEBUG_CITATIONS=true
```

Shows:
- Raw model output (first 200 chars)
- Number of citations found
- Warnings when citations missing

Disable by unsetting:
```bash
unset DEBUG_CITATIONS
```

## Files to Check

All changes in commit `3077b65`:
- **src/pipeline.py** - Improved prompts
- **debug_citations.py** - Test script
- **CITATION_FIX.md** - Full documentation

## Quick Reference

```bash
# Test citation extraction
python debug_citations.py

# Run with debug logging
export DEBUG_CITATIONS=true
python main.py --skip-fetch --skip-measure --skip-load

# Full test (all phases)
python main.py

# Check a specific question
python -c "
import sys
sys.path.insert(0, 'src')
from test_questions import ALL_TEST_QUESTIONS
for q in ALL_TEST_QUESTIONS[:3]:
    print(f\"Q{q['id']}: {q['query'][:50]}...\")
"
```

---

**Status**: Fixed and ready to test!
