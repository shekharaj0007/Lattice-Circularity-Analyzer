#!/usr/bin/env python3
"""
Verify that configured Groq models actually exist and work.
Run this before executing the full pipeline to catch model name errors early.
"""

import os
import sys
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def test_model(client, model_name: str, description: str) -> bool:
    """Test if a model works with a simple completion."""
    try:
        print(f"Testing {description}: {model_name}... ", end="", flush=True)
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
            max_tokens=10,
            temperature=0
        )
        
        if response and response.choices:
            print(f"✓ OK")
            return True
        else:
            print(f"✗ FAILED (no response)")
            return False
            
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def main():
    """Test all configured models."""
    print("="*70)
    print("GROQ MODEL VERIFICATION")
    print("="*70)
    print()
    
    # Check API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not set in .env")
        print("   Run: cp .env.example .env")
        print("   Then add your API key")
        return False
    
    print(f"✓ API key found: {api_key[:8]}...")
    print()
    
    # Initialize client
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        print(f"❌ Failed to initialize Groq client: {e}")
        return False
    
    # Models to test
    models_to_test = [
        (os.getenv("GROQ_MODEL", "gemma2-9b-it"), "Default/Fallback"),
        (os.getenv("GROQ_INTENT_MODEL", "gemma2-9b-it"), "Intent Model"),
        (os.getenv("GROQ_VERIFICATION_MODEL", "gemma2-9b-it"), "Verification Model"),
        (os.getenv("GROQ_GENERATION_MODEL", "llama-3.1-70b-versatile"), "Generation Model"),
    ]
    
    # Remove duplicates (keep unique models)
    unique_models = {}
    for model, desc in models_to_test:
        if model not in unique_models:
            unique_models[model] = desc
    
    print(f"Testing {len(unique_models)} unique model(s):")
    print()
    
    # Test each model
    results = {}
    for model, desc in unique_models.items():
        results[model] = test_model(client, model, desc)
    
    print()
    print("="*70)
    
    # Summary
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL {total} MODEL(S) WORKING")
        print()
        print("Ready to run pipeline:")
        print("  python main.py")
        return True
    else:
        print(f"⚠️  {total - passed}/{total} MODEL(S) FAILED")
        print()
        print("Failed models:")
        for model, success in results.items():
            if not success:
                print(f"  ✗ {model}")
        print()
        print("Check GROQ_MODELS.md for working model names")
        print("Update .env with correct models")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
