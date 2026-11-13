"""
Verify the pipeline setup without requiring all dependencies.
Checks file structure and basic Python syntax.
"""

import os
import sys
from pathlib import Path


def check_file_structure():
    """Check that all required files exist."""
    print("\n" + "="*60)
    print("CHECKING FILE STRUCTURE")
    print("="*60)
    
    required_files = [
        "requirements.txt",
        ".env.example",
        "README.md",
        "main.py",
        "analyze_results.py",
        "quick_test.py",
        "src/__init__.py",
        "src/paper_fetcher.py",
        "src/chunker.py",
        "src/embeddings.py",
        "src/rate_limiter.py",
        "src/groq_client.py",
        "src/pipeline.py",
        "src/standin_service.py",
        "src/test_questions.py",
        "src/load_tester.py",
        "src/measure_groq.py",
    ]
    
    missing = []
    found = []
    
    for filepath in required_files:
        if os.path.exists(filepath):
            found.append(filepath)
            print(f"  ✓ {filepath}")
        else:
            missing.append(filepath)
            print(f"  ✗ {filepath} MISSING")
    
    print(f"\nFiles: {len(found)}/{len(required_files)} found")
    
    return len(missing) == 0


def check_directories():
    """Check that required directories exist."""
    print("\n" + "="*60)
    print("CHECKING DIRECTORIES")
    print("="*60)
    
    required_dirs = ["src", "data", "results", "standin"]
    
    for dirname in required_dirs:
        exists = os.path.isdir(dirname)
        print(f"  {'✓' if exists else '✗'} {dirname}/")
        if not exists:
            os.makedirs(dirname, exist_ok=True)
            print(f"    Created {dirname}/")
    
    return True


def check_python_syntax():
    """Check Python files for syntax errors."""
    print("\n" + "="*60)
    print("CHECKING PYTHON SYNTAX")
    print("="*60)
    
    python_files = list(Path(".").rglob("*.py"))
    
    errors = []
    
    for filepath in python_files:
        # Skip test files and __pycache__
        if "__pycache__" in str(filepath):
            continue
        
        try:
            with open(filepath, 'r') as f:
                code = f.read()
                compile(code, str(filepath), 'exec')
            print(f"  ✓ {filepath}")
        except SyntaxError as e:
            print(f"  ✗ {filepath}: {e}")
            errors.append((filepath, e))
    
    print(f"\nChecked {len(python_files)} Python files")
    print(f"Syntax errors: {len(errors)}")
    
    return len(errors) == 0


def check_imports():
    """Check that source files can be imported."""
    print("\n" + "="*60)
    print("CHECKING MODULE IMPORTS")
    print("="*60)
    
    sys.path.insert(0, 'src')
    
    modules = [
        "paper_fetcher",
        "chunker",
        "rate_limiter",
        "test_questions",
        "load_tester",
    ]
    
    success = []
    failed = []
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
            success.append(module)
        except ImportError as e:
            # Expected if dependencies not installed
            if "groq" in str(e) or "sentence" in str(e) or "torch" in str(e) or "PyPDF2" in str(e):
                print(f"  ⚠ {module} (missing dependencies - expected)")
                success.append(module)
            else:
                print(f"  ✗ {module}: {e}")
                failed.append(module)
        except Exception as e:
            print(f"  ✗ {module}: {e}")
            failed.append(module)
    
    print(f"\nModules: {len(success)}/{len(modules)} importable")
    
    return len(failed) == 0


def check_config():
    """Check configuration files."""
    print("\n" + "="*60)
    print("CHECKING CONFIGURATION")
    print("="*60)
    
    # Check .env.example
    if os.path.exists(".env.example"):
        with open(".env.example") as f:
            content = f.read()
            print("  ✓ .env.example exists")
            if "GROQ_API_KEY" in content:
                print("    - Contains GROQ_API_KEY")
            if "GROQ_RPM_LIMIT" in content:
                print("    - Contains rate limit config")
    
    # Check if .env exists
    if os.path.exists(".env"):
        print("  ✓ .env file exists")
        print("    Note: Make sure GROQ_API_KEY is set")
    else:
        print("  ⚠ .env file not found")
        print("    Run: cp .env.example .env")
        print("    Then add your GROQ_API_KEY")
    
    return True


def main():
    print("\n" + "="*80)
    print("RELAY PIPELINE SETUP VERIFICATION")
    print("="*80)
    
    tests = [
        ("File Structure", check_file_structure),
        ("Directories", check_directories),
        ("Python Syntax", check_python_syntax),
        ("Module Imports", check_imports),
        ("Configuration", check_config),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {name} check failed: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"VERIFICATION RESULTS: {passed}/{len(tests)} checks passed")
    
    if failed == 0:
        print("✓ Setup verified successfully!")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Add GROQ_API_KEY to .env file")
        print("  3. Run quick test: python quick_test.py")
        print("  4. Run full pipeline: python main.py")
    else:
        print(f"⚠ {failed} check(s) failed - see output above")
    
    print("="*80)


if __name__ == "__main__":
    main()
