#!/usr/bin/env python3
"""
Test Clean Annotation Approach

Simple test to verify that PIL-based image annotation works correctly
without modifying the existing working code.

Usage:
    python test_clean_annotation.py
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from browser_controller_clean import CleanBrowserController
from dotenv import load_dotenv

load_dotenv()

def test_clean_annotation():
    """Test the clean annotation approach"""
    print("🧪 Testing Clean Annotation Approach")
    print("="*50)
    
    # Initialize clean browser controller
    browser = CleanBrowserController()
    
    # Test configuration
    test_config = {
        "app": "linear",
        "task_id": "test_clean",
        "start_url": "https://linear.app"
    }
    
    try:
        print("\n1️⃣  Setting up browser...")
        if not browser.setup_browser(test_config):
            print("❌ Browser setup failed")
            return False
        
        print("✅ Browser setup successful")
        
        print("\n2️⃣  Navigating to Linear...")
        if not browser.navigate_to_url("https://linear.app"):
            print("❌ Navigation failed")
            browser.cleanup()
            return False
        
        print("✅ Navigation successful")
        
        print("\n3️⃣  Testing clean annotation...")
        result = browser.annotate_and_capture_clean()
        
        if not result['bboxes']:
            print("❌ No interactive elements found")
            browser.cleanup()
            return False
        
        print(f"✅ Found {len(result['bboxes'])} interactive elements")
        print(f"✅ Clean screenshot: {len(result['screenshot'])} bytes")
        print(f"✅ Annotated screenshot: {len(result['screenshot_b64'])} chars")
        
        # Save test images
        test_dir = Path("test_output")
        test_dir.mkdir(exist_ok=True)
        
        # Save clean screenshot
        with open(test_dir / "clean_screenshot.png", "wb") as f:
            f.write(result['screenshot'])
        
        # Save annotated screenshot
        import base64
        with open(test_dir / "annotated_screenshot.png", "wb") as f:
            f.write(base64.b64decode(result['screenshot_b64']))
        
        print(f"\n📁 Test output saved to: {test_dir}/")
        print("   - clean_screenshot.png (what user sees)")
        print("   - annotated_screenshot.png (what Gemini sees)")
        
        print("\n4️⃣  Element data sample:")
        for i, bbox in enumerate(result['bboxes'][:5]):  # Show first 5
            print(f"   [{bbox['index']}] {bbox['type']}: '{bbox['text'][:30]}...'")
        
        browser.cleanup()
        
        print("\n🎉 Clean annotation test completed successfully!")
        print("👀 User saw: Clean page throughout test")
        print("🤖 AI would see: Annotated screenshots with numbered boxes")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        browser.cleanup()
        return False

if __name__ == "__main__":
    test_clean_annotation()