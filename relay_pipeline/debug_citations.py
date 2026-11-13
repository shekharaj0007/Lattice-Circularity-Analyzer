#!/usr/bin/env python3
"""
Debug citation extraction issues.
Tests actual model outputs to see if they include citations.
"""

import os
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
from groq_client import InstrumentedGroqClient
from citations import CitationExtractor
import json

load_dotenv()

def test_generation_with_debug():
    """Test generation and log raw output."""
    print("="*70)
    print("CITATION GENERATION DEBUG")
    print("="*70)
    print()
    
    # Initialize
    client = InstrumentedGroqClient(
        model=os.getenv("GROQ_GENERATION_MODEL", "llama-3.1-70b-versatile")
    )
    extractor = CitationExtractor()
    
    # Sample context (simulating what pipeline provides)
    sample_context = """[Chunk c1]: The Transformer model architecture relies on self-attention mechanisms. 
The encoder consists of 6 identical layers, each with two sub-layers.

[Chunk c2]: Multi-head attention allows the model to jointly attend to information 
from different representation subspaces. We employ h=8 parallel attention heads.

[Chunk c3]: The model uses learned embeddings to convert input tokens to vectors 
of dimension 512."""
    
    sample_query = "How many layers does the Transformer encoder have?"
    
    # Test current prompt (what pipeline uses)
    print("Test 1: Current Pipeline Prompt")
    print("-" * 70)
    
    system_prompt_current = """You are a helpful assistant. Answer based ONLY on the provided context.
Include citations in format: [Paper vN, p.PAGE, chunk cID]
Example: The transformer uses attention [Attention Is All You Need v7, p.3, chunk c1].
If context doesn't answer the question, say so."""
    
    messages_current = [
        {"role": "system", "content": system_prompt_current},
        {"role": "user", "content": f"Context:\n{sample_context}\n\nQuestion: {sample_query}\n\nAnswer:"}
    ]
    
    result1 = client.chat_completion(messages_current, max_tokens=400, temperature=0.7)
    answer1 = result1["content"]
    
    print(f"Model: {client.model}")
    print(f"Raw Output:\n{answer1}")
    print()
    
    citations1 = extractor.extract_citations(answer1)
    print(f"Citations found: {len(citations1)}")
    if citations1:
        for c in citations1:
            print(f"  - {c}")
    else:
        print("  ❌ NO CITATIONS EXTRACTED")
    print()
    print()
    
    # Test improved prompt (more explicit)
    print("Test 2: Improved Prompt (More Explicit)")
    print("-" * 70)
    
    system_prompt_improved = """You are a helpful assistant. Answer based ONLY on the provided context.

CRITICAL: You MUST cite every claim using this EXACT format:
[Paper Name v7, p.PAGE, chunk cID]

Example answer:
"The Transformer encoder has 6 layers [Attention Is All You Need v7, p.3, chunk c1] with multi-head attention [Attention Is All You Need v7, p.4, chunk c2]."

Paper name: "Attention Is All You Need"
Version: v7
Use the chunk IDs from the context (c1, c2, etc.)

If context doesn't answer the question, say "The provided context doesn't answer this question." """
    
    messages_improved = [
        {"role": "system", "content": system_prompt_improved},
        {"role": "user", "content": f"Context:\n{sample_context}\n\nQuestion: {sample_query}\n\nAnswer with citations:"}
    ]
    
    result2 = client.chat_completion(messages_improved, max_tokens=400, temperature=0.7)
    answer2 = result2["content"]
    
    print(f"Model: {client.model}")
    print(f"Raw Output:\n{answer2}")
    print()
    
    citations2 = extractor.extract_citations(answer2)
    print(f"Citations found: {len(citations2)}")
    if citations2:
        for c in citations2:
            print(f"  - {c}")
        print("  ✅ CITATIONS EXTRACTED SUCCESSFULLY")
    else:
        print("  ❌ NO CITATIONS EXTRACTED")
    print()
    print()
    
    # Test with multiple papers
    print("Test 3: Multi-Paper Context")
    print("-" * 70)
    
    multi_context = """[Chunk c1 from Attention Is All You Need]: The Transformer uses 6 encoder layers.

[Chunk c2 from Moshi]: Moshi is a speech-text foundation model with low latency."""
    
    multi_query = "How many encoder layers does the Transformer use?"
    
    system_prompt_multi = """You are a helpful assistant. Answer based ONLY on the provided context.

CRITICAL: You MUST cite every claim using this EXACT format:
[Paper Name vN, p.PAGE, chunk cID]

Available papers and versions:
- "Attention Is All You Need" v7
- "Moshi" v1
- "Dynamic Chunking" v2

Example: The encoder has 6 layers [Attention Is All You Need v7, p.3, chunk c1].

Use the chunk IDs from the context (c1, c2, etc.)."""
    
    messages_multi = [
        {"role": "system", "content": system_prompt_multi},
        {"role": "user", "content": f"Context:\n{multi_context}\n\nQuestion: {multi_query}\n\nAnswer with citations:"}
    ]
    
    result3 = client.chat_completion(messages_multi, max_tokens=400, temperature=0.7)
    answer3 = result3["content"]
    
    print(f"Model: {client.model}")
    print(f"Raw Output:\n{answer3}")
    print()
    
    citations3 = extractor.extract_citations(answer3)
    print(f"Citations found: {len(citations3)}")
    if citations3:
        for c in citations3:
            print(f"  - {c}")
        print("  ✅ CITATIONS EXTRACTED SUCCESSFULLY")
    else:
        print("  ❌ NO CITATIONS EXTRACTED")
    print()
    print()
    
    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Test 1 (Current): {len(citations1)} citations")
    print(f"Test 2 (Improved): {len(citations2)} citations")
    print(f"Test 3 (Multi-paper): {len(citations3)} citations")
    print()
    
    if len(citations2) > 0 or len(citations3) > 0:
        print("✅ Solution: Improved prompt works better")
        print("   Recommendation: Update pipeline to use more explicit prompt")
    else:
        print("⚠️  Model may not be following citation format")
        print("   Check if model output includes ANY brackets or paper names")
        print()
        print("   Checking for alternative formats in Test 2 output:")
        if '[' in answer2:
            print("   - Found '[' character")
        if 'chunk' in answer2.lower():
            print("   - Found 'chunk' text")
        if any(paper in answer2 for paper in ["Attention", "Transformer"]):
            print("   - Found paper reference")
    
    # Save debug outputs
    debug_data = {
        "test1_current": {
            "prompt": system_prompt_current,
            "output": answer1,
            "citations_found": len(citations1),
            "citations": citations1
        },
        "test2_improved": {
            "prompt": system_prompt_improved,
            "output": answer2,
            "citations_found": len(citations2),
            "citations": citations2
        },
        "test3_multi": {
            "prompt": system_prompt_multi,
            "output": answer3,
            "citations_found": len(citations3),
            "citations": citations3
        }
    }
    
    os.makedirs('results', exist_ok=True)
    with open('results/citation_debug.json', 'w') as f:
        json.dump(debug_data, f, indent=2)
    
    print()
    print("Debug data saved to: results/citation_debug.json")

if __name__ == "__main__":
    test_generation_with_debug()
