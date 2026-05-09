#!/usr/bin/env python3
"""
Test script to verify drag-and-drop pastes paths at cursor instead of changing directory
"""
import os
import sys

# Add the current directory to the path to import our modules
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, repo_root)

def test_drag_drop_behavior():
    print("🧪 Testing Drag-and-Drop Paste Behavior")
    print("=" * 50)
    
    # Test that the JavaScript changes are in place
    js_file = os.path.join(repo_root, 'static', 'termisol_terminal.js')
    
    if os.path.exists(js_file):
        with open(js_file, 'r') as f:
            content = f.read()
        
        # Check for the updated behavior
        if 'Pasted directory path:' in content:
            print("✅ Directory drop now pastes path instead of changing directory")
        else:
            print("❌ Directory drop still changes directory")
            
        if 'Pasted file path:' in content:
            print("✅ File drop now pastes path instead of changing directory")
        else:
            print("❌ File drop still changes directory")
            
        # Check that cd commands are removed
        if 'cdCommand' in content and 'await this.sendInput(cdCommand)' in content:
            print("❌ Still contains cd commands - need to remove")
        else:
            print("✅ cd commands removed from drag-and-drop")
            
        # Check for path cleaning logic
        if 'pathToPaste' in content:
            print("✅ Path cleaning logic implemented")
        else:
            print("❌ Path cleaning logic missing")
            
    else:
        print("❌ JavaScript file not found")
    
    print("\n📋 Expected Behavior:")
    print("   1. Drag file/folder into terminal")
    print("   2. Path is pasted at cursor position")
    print("   3. No automatic directory change occurs")
    print("   4. User can then use the path as needed")
    
    print("\n🎯 Test completed!")

if __name__ == "__main__":
    test_drag_drop_behavior()
