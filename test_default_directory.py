#!/usr/bin/env python3
"""
Test the default directory behavior when no workspace is selected
"""
import os
import sys

# Add the api directory to the path
sys.path.insert(0, '/home/house/vibecode')

from api.termisol_adapter import TermisolSession

def test_default_directory():
    print("🧪 Testing Default Directory Behavior")
    print("=" * 50)
    
    # Test what happens when we're in vibecode but want default
    print("\n📍 Test: User in vibecode but wants default /home/house")
    
    # Simulate being in vibecode directory
    original_cwd = os.getcwd()
    os.chdir('/home/house/vibecode')
    
    try:
        # Create session without explicit CWD (should default to /home/house)
        session = TermisolSession("test_default")
        print(f"Current directory: {os.getcwd()}")
        print(f"Detected directory: {session.cwd}")
        print(f"Expected (per user request): /home/house")
        
        if session.cwd == '/home/house':
            print("✅ PASS: Default directory correctly set to /home/house")
        else:
            print("❌ FAIL: Should default to /home/house when no workspace selected")
            
    finally:
        os.chdir(original_cwd)
    
    # Test with explicit CWD
    print("\n📍 Test: Explicit CWD should be respected")
    try:
        session_explicit = TermisolSession("test_explicit", cwd="/home/house/termisol")
        print(f"Explicit CWD: /home/house/termisol")
        print(f"Detected directory: {session_explicit.cwd}")
        
        if session_explicit.cwd == '/home/house/termisol':
            print("✅ PASS: Explicit CWD respected")
        else:
            print("❌ FAIL: Explicit CWD not respected")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n✅ Default directory tests completed!")

if __name__ == "__main__":
    test_default_directory()
