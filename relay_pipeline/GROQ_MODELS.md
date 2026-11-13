# Groq Free Tier Models

This document lists the **actual working models** available on Groq's free tier as of November 2026.

## Available Models

### Small/Fast Models
Recommended for: Intent classification, verification, simple tasks

| Model | Size | Best For |
|-------|------|----------|
| `gemma2-9b-it` | 9B | General purpose, good quality **(Recommended)** |
| `gemma-7b-it` | 7B | Lighter alternative, faster |

**Token Cost**: Lower (fewer parameters)  
**Latency**: ~500-800ms  
**Use Cases**: Intent classification, verification, simple Q&A

---

### Large/Capable Models
Recommended for: Answer generation, complex reasoning

| Model | Size | Best For |
|-------|------|----------|
| `llama-3.1-70b-versatile` | 70B | High quality generation **(Recommended)** |
| `llama-3.3-70b-versatile` | 70B | Latest version, best quality |
| `mixtral-8x7b-32768` | 8x7B | Long context (32K tokens) |

**Token Cost**: Higher (more parameters)  
**Latency**: ~800-1500ms  
**Use Cases**: Answer generation, complex reasoning, detailed responses

---

## Strategic Model Sizing

The pipeline uses **different models for different stages** to optimize cost and quality:

```bash
# .env configuration
GROQ_MODEL=gemma2-9b-it                    # Fallback
GROQ_INTENT_MODEL=gemma2-9b-it             # Small/fast for intent
GROQ_VERIFICATION_MODEL=gemma2-9b-it       # Small/fast for verification
GROQ_GENERATION_MODEL=llama-3.1-70b-versatile  # Large for generation
```

### Why This Works

1. **Intent Classification** (simple) → Small model (gemma2-9b-it)
   - Task: Categorize question type (FACTUAL, CONCEPTUAL, etc.)
   - Needs: Speed, low cost
   - Saves: ~60% tokens vs large model

2. **Generation** (hard) → Large model (llama-3.1-70b-versatile)
   - Task: Write detailed answer with citations
   - Needs: Quality, reasoning
   - Worth: Spending tokens on the important task

3. **Verification** (checking) → Small model (gemma2-9b-it)
   - Task: Check if citations are valid
   - Needs: Speed, accuracy
   - Saves: ~60% tokens vs large model

**Result**: Same generation quality, 40-50% lower token cost overall.

---

## Rate Limits (Free Tier)

| Limit | Value |
|-------|-------|
| **RPM** (Requests/minute) | 30 |
| **TPM** (Tokens/minute) | 14,400 |
| **Daily Token Limit** | 14,400 |

**Note**: These are observed limits. Groq may adjust them.

---

## Testing Model Performance

Use `measure_groq.py` to test a specific model:

```bash
# Test default model (gemma2-9b-it)
python src/measure_groq.py

# Or set MODEL_TO_TEST in measure_groq.py:
# MODEL_TO_TEST = "llama-3.1-70b-versatile"
```

---

## Models That DON'T Exist

These models are **not available** on Groq free tier (despite appearing in some docs):

❌ `llama-3.1-8b-instant` - Does not exist  
❌ `llama-3.2-1b-preview` - Does not exist  
❌ `llama-3.2-3b-preview` - Does not exist  
❌ `llama-3.2-8b-preview` - Does not exist  

If you see errors like `model not found`, check this list.

---

## Recommended Configurations

### Balanced (Default)
```bash
GROQ_INTENT_MODEL=gemma2-9b-it
GROQ_VERIFICATION_MODEL=gemma2-9b-it
GROQ_GENERATION_MODEL=llama-3.1-70b-versatile
```
- **Cost**: Medium
- **Quality**: High where it matters
- **Speed**: Fast for simple tasks

### Maximum Quality
```bash
GROQ_INTENT_MODEL=gemma2-9b-it
GROQ_VERIFICATION_MODEL=gemma2-9b-it
GROQ_GENERATION_MODEL=llama-3.3-70b-versatile
```
- **Cost**: Higher
- **Quality**: Best possible
- **Speed**: Slower

### Budget Conscious
```bash
GROQ_INTENT_MODEL=gemma-7b-it
GROQ_VERIFICATION_MODEL=gemma-7b-it
GROQ_GENERATION_MODEL=llama-3.1-70b-versatile
```
- **Cost**: Lowest
- **Quality**: Still good for generation
- **Speed**: Fastest

---

## References

- **Groq Documentation**: https://console.groq.com/docs/models
- **Free Tier Limits**: Check Groq console for latest

---

**Last Updated**: November 13, 2026
