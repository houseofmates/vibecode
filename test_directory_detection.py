#!/usr/bin/env python3
"""
Test script for Termisol directory detection and device mapping
"""
import os
import socket
import sys

# Add the api directory to the path
sys.path.insert(0, '/home/house/vibecode')

from api.termisol_adapter import TermisolSession

def test_directory_detection():
    print("🧪 Testing Termisol Directory Detection")
    print("=" * 50)
    
    # Test 1: Default directory detection
    print("\n📍 Test 1: Default directory detection")
    session1 = TermisolSession("test1")
    print(f"Detected directory: {session1.cwd}")
    print(f"Expected: /home/house")
    
    # Test 2: Explicit directory
    print("\n📍 Test 2: Explicit directory")
    session2 = TermisolSession("test2", cwd="/home/house/vibecode")
    print(f"Explicit directory: {session2.cwd}")
    print(f"Expected: /home/house/vibecode")
    
    # Test 3: Current directory detection
    print("\n📍 Test 3: Current directory detection")
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # Test 4: Device detection
    print("\n📍 Test 4: Device detection")
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
        print(f"Hostname: {hostname}")
        print(f"Local IP: {local_ip}")
        
        # Test device-specific mapping
        session3 = TermisolSession("test3", cwd=current_dir)
        print(f"Device-aware directory: {session3.cwd}")
        
    except Exception as e:
        print(f"Device detection failed: {e}")
    
    # Test 5: Workspace-specific mapping
    print("\n📍 Test 5: Workspace-specific mapping")
    workspace_tests = [
        "/home/house/vibecode",
        "/home/house/termisol", 
        "/home/house/workspace",
        "/home/house"
    ]
    
    for workspace in workspace_tests:
        if os.path.exists(workspace):
            session = TermisolSession("test_workspace", cwd=workspace)
            print(f"Workspace {workspace}: {session.cwd}")
        else:
            print(f"Workspace {workspace}: (does not exist)")
    
    print("\n✅ Directory detection tests completed!")

if __name__ == "__main__":
    test_directory_detection()
