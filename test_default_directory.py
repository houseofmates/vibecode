#!/usr/bin/env python3
"""
Test the default directory behavior when no workspace is selected
"""
import os
import sys

# Add the api directory to the path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, repo_root)
home_dir = os.path.expanduser('~')

from api.termisol_adapter import TermisolSession

def test_default_directory():
    print("🧪 Testing Default Directory Behavior")
    print("=" * 50)
    
    # Test what happens when we're in vibecode but want default
    print(f"\n📍 Test: User in vibecode but wants default {home_dir}")
    
    # Simulate being in vibecode directory
    original_cwd = os.getcwd()
    os.chdir(repo_root)
    
    try:
        # Create session without explicit CWD (should default to the current user home directory)
        session = TermisolSession("test_default")
        print(f"Current directory: {os.getcwd()}")
        print(f"Detected directory: {session.cwd}")
        print(f"Expected (per user request): {home_dir}")
        
        if session.cwd == home_dir:
            print(f"✅ PASS: Default directory correctly set to {home_dir}")
        else:
            print("❌ FAIL: Should default to the user home directory when no workspace selected")
            
    finally:
        os.chdir(original_cwd)
    
    # Test with explicit CWD
    print("\n📍 Test: Explicit CWD should be respected")
    explicit_cwd = os.path.join(repo_root, 'termisol')
    os.makedirs(explicit_cwd, exist_ok=True)
    try:
        session_explicit = TermisolSession("test_explicit", cwd=explicit_cwd)
        print(f"Explicit CWD: {explicit_cwd}")
        print(f"Detected directory: {session_explicit.cwd}")
        
        if session_explicit.cwd == explicit_cwd:
            print("✅ PASS: Explicit CWD respected")
        else:
            print("❌ FAIL: Explicit CWD not respected")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n✅ Default directory tests completed!")

if __name__ == "__main__":
    test_default_directory()
