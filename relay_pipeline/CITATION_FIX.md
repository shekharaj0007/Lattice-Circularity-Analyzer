# Citation Extraction Fix

## Problem
Models were not producing citations in the expected format, causing "No citations found" errors on all test questions.

## Root Cause
The generation prompts were **too vague** about citation format:
- Didn't specify which papers were available
- Didn't specify correct paper versions (v7, v1, v2)
- Didn't emphasize that citations are REQUIRED

## Solution

### 1. Improved Generation Prompt

**Before** (vague):
```
You are a helpful assistant. Answer based ONLY on the provided context.
Include citations in format: [Paper vN, p.PAGE, chunk cID]
Example: The transformer uses attention [Attention Is All You Need v7, p.3, chunk c1].
```

**After** (explicit):
```
CRITICAL: You MUST cite every claim using this EXACT format:
[Paper Name vN, p.PAGE, chunk cID]

Papers in context:
- "Attention Is All You Need" v7
- "Moshi" v1
- "Dynamic Chunking" v2

Example answer:
"The Transformer encoder has 6 layers [Attention Is All You Need v7, p.3, chunk c1]."

Rules:
1. Use EXACT paper names and versions listed above
2. Use chunk IDs from context (c1, c2, etc.)
3. Cite EVERY factual claim
```

### 2. Context Format Enhancement

**Before**:
```
[Chunk c1]: The encoder has 6 layers...
[Chunk c2]: Multi-head attention...
```

**After**:
```
[Chunk c1 from Attention Is All You Need]: The encoder has 6 layers...
[Chunk c2 from Attention Is All You Need]: Multi-head attention...
```

This tells the model which paper each chunk comes from.

### 3. Debug Logging

Added optional debug output to see what models actually produce:

```bash
export DEBUG_CITATIONS=true
python main.py
```

Shows:
- Raw model output
- Number of citations found
- Warnings for answers without citations

## Files Changed

1. **src/pipeline.py**:
   - `_stage_generation()`: Improved prompt, added paper metadata to context
   - `_retry_generation()`: Same improvements for retry attempts
   - Added debug logging (enable with `DEBUG_CITATIONS=true`)

2. **debug_citations.py** (new):
   - Test script to compare prompts
   - Shows what models actually output
   - Helps verify citation extraction works

## Testing

### Quick Test
```bash
cd relay_pipeline
python debug_citations.py
```

This will:
1. Test current prompt format
2. Test improved prompt format
3. Show raw outputs and citations found

### Full Pipeline Test
```bash
# Enable debug logging
export DEBUG_CITATIONS=true

# Run quality tests
python main.py --skip-fetch --skip-measure --skip-load
```

Look for `[DEBUG]` lines showing:
- What models actually output
- How many citations were extracted
- Warnings for missing citations

## Expected Improvements

### Before Fix
```
Testing Q1 (FACTUAL)...
  ✗ No citations found in answer
  ✗ Verification failed

Testing Q2 (FACTUAL)...
  ✗ No citations found in answer
  ✗ Verification failed

...all 15 questions fail
```

### After Fix
```
Testing Q1 (FACTUAL)...
  [DEBUG] Citations found: 2
  ✓ Citations verified
  ✓ Verification passed

Testing Q2 (FACTUAL)...
  [DEBUG] Citations found: 1
  ✓ Citations verified
  ✓ Verification passed

...most questions should pass
```

## If Still Failing

### Check Model Output Format

Run debug script:
```bash
python debug_citations.py
```

Check if model includes:
- Square brackets `[...]`
- Paper names
- Version numbers `v1`, `v7`, etc.
- Chunk IDs `c1`, `c2`, etc.

### Adjust Citation Regex

If model uses different format, update in `src/citations.py`:

```python
# Current pattern
CITATION_PATTERN = r'\[([^\]]+?)\s+v(\d+),\s*p\.(\d+),\s*chunk\s+c(\d+)\]'

# If model outputs differently, adjust pattern
# Example for format without "chunk": [Paper v7, p.3, c1]
CITATION_PATTERN = r'\[([^\]]+?)\s+v(\d+),\s*p\.(\d+),\s*c(\d+)\]'
```

### Increase max_tokens

If answers are cut off mid-sentence:
```python
# In pipeline.py, increase from 400
result = self.generation_client.chat_completion(messages, max_tokens=600, temperature=0.7)
```

## Additional Notes

- Citation extraction is **deterministic** (regex-based) - no LLM calls
- Fast and reliable once models follow format
- No risk of hallucinated verification results
- Trade-off: Models must follow exact format

## Status
✅ Prompt improved  
✅ Context format enhanced  
✅ Debug logging added  
✅ Retry logic updated  
⏳ Needs testing with real API  

Run `python debug_citations.py` to test citation generation.
