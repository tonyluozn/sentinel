#!/usr/bin/env python3
"""Quick verification script to check if Sentinel is set up correctly."""

import sys
from pathlib import Path

def check_imports():
    """Check if all imports work."""
    print("Checking imports...")
    try:
        import sentinel
        from sentinel.trace import Event, EventType, JsonlTraceStore
        from sentinel.github import GitHubClient, FileCache
        from sentinel.evidence import EvidenceGraph
        from sentinel.interventions import Supervisor
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("  Run: pip install -e .")
        return False

def check_api_keys():
    """Check if API keys are set."""
    import os
    print("\nChecking API keys...")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    
    if openai_key:
        print(f"✓ OPENAI_API_KEY is set (starts with: {openai_key[:7]}...)")
    else:
        print("✗ OPENAI_API_KEY not set")
        print("  Set it: export OPENAI_API_KEY='sk-your-key'")
    
    if github_token:
        print(f"✓ GITHUB_TOKEN is set (starts with: {github_token[:7]}...)")
    else:
        print("⚠ GITHUB_TOKEN not set (optional but recommended)")
        print("  Set it: export GITHUB_TOKEN='ghp_your-token'")
    
    return bool(openai_key)

def check_cli():
    """Check if CLI is accessible."""
    print("\nChecking CLI...")
    try:
        from sentinel.cli import main
        print("✓ CLI module accessible")
        return True
    except Exception as e:
        print(f"✗ CLI error: {e}")
        return False

def main():
    """Run all checks."""
    print("=" * 50)
    print("Sentinel Setup Verification")
    print("=" * 50)
    
    all_ok = True
    
    all_ok &= check_imports()
    all_ok &= check_api_keys()
    all_ok &= check_cli()
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✓ Setup looks good! You can run:")
        print("  sentinel --help")
        print("  sentinel fetch --repo owner/repo --milestone 'v1.0'")
    else:
        print("✗ Some issues found. Please fix them above.")
        sys.exit(1)
    print("=" * 50)

if __name__ == "__main__":
    main()
