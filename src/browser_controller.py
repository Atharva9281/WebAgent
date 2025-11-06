"""
Browser Controller Module

Handles all browser-related operations:
- Authentication (persistent profiles + session files)
- Page loading and navigation
- Action execution (click, type, scroll)
- Screenshot capture with annotations
"""

import os
import base64
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from task_definitions import get_session_file


class BrowserController:
    """
    Manages browser operations for web automation
    """
    
    def __init__(self):
        """Initialize browser controller"""
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.mark_page_script = None
        self._load_mark_page_script()
    
    def _load_mark_page_script(self):
        """Load the mark_page.js annotation script"""
        mark_page_path = Path(__file__).parent / "mark_page.js"
        with open(mark_page_path, 'r') as f:
            self.mark_page_script = f.read()
    
    def setup_browser(self, task_config: Dict) -> bool:
        """
        Setup browser with authentication for the given task
        
        Args:
            task_config: Task configuration dictionary
            
        Returns:
            True if setup successful, False otherwise
        """
        app_name = task_config['app']
        profile_dir = f"auth/{app_name}_profile"
        session_file = get_session_file(app_name)
        
        use_persistent_profile = os.path.exists(profile_dir)
        use_session_file = os.path.exists(session_file)
        
        if not use_persistent_profile and not use_session_file:
            print(f"❌ No authentication found for {app_name}")
            print("   Please run: python src/setup_auth.py")
            return False
        
        if use_persistent_profile:
            print(f"🔐 Using persistent profile: {profile_dir}")
        else:
            print(f"🔐 Using session file: {session_file}")
        
        try:
            self.playwright = sync_playwright().start()
            
            if use_persistent_profile:
                # Use persistent profile (newer method)
                self.context = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    channel="chrome",
                    viewport={'width': 1920, 'height': 1080},
                    slow_mo=1000,
                    args=[
                        '--start-maximized',
                        '--disable-blink-features=AutomationControlled'
                    ],
                    ignore_default_args=['--enable-automation']
                )
                # Add anti-detection script
                self.context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = window.chrome || {};
                    window.chrome.runtime = window.chrome.runtime || {};
                """)
                self.browser = None  # No separate browser object
            else:
                # Use session file (older method)
                self.browser = self.playwright.chromium.launch(
                    headless=False,
                    channel="chrome",
                    slow_mo=1000,
                    args=['--start-maximized']
                )
                self.context = self.browser.new_context(
                    storage_state=session_file,
                    viewport={'width': 1920, 'height': 1080}
                )
            
            existing_pages = self.context.pages
            if existing_pages:
                self.page = existing_pages[0]
            else:
                self.page = self.context.new_page()
            for extra in list(self.context.pages):
                if extra != self.page:
                    try:
                        extra.close()
                    except Exception:
                        pass
            return True
            
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            self.cleanup()
            return False
    
    def navigate_to_url(self, url: str) -> bool:
        """
        Navigate to URL with robust loading handling
        
        Args:
            url: Target URL
            
        Returns:
            True if navigation successful, False otherwise
        """
        if not self.page:
            print("❌ No page available - call setup_browser first")
            return False
        
        try:
            print(f"\n🌐 Navigating to: {url}")
            self.page.goto(url, timeout=30000)
            
            # More robust page loading for slow sites like Notion
            print("⏳ Waiting for page to load...")
            try:
                self.page.wait_for_load_state("networkidle", timeout=30000)
                print("✅ Page fully loaded")
            except Exception as e:
                print(f"⚠️  Networkidle timeout ({e}), trying domcontentloaded...")
                try:
                    self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                    print("✅ DOM content loaded")
                except Exception as e2:
                    print(f"⚠️  DOM timeout ({e2}), proceeding anyway...")
            
            # Give extra time for any dynamic content
            print("🕐 Allowing time for dynamic content...")
            self.page.wait_for_timeout(1000)
            
            print("✅ Navigation complete\n")
            return True
            
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            return False
    
    def annotate_and_capture(self) -> Dict:
        """
        Annotate page with bounding boxes and capture screenshot
        
        Returns:
            Dict with bboxes, screenshot bytes, and base64 screenshot
        """
        if not self.page:
            return {"bboxes": [], "screenshot": b"", "screenshot_b64": ""}
        
        try:
            # Inject mark_page.js script
            self.page.evaluate(self.mark_page_script)
            
            # Run markPage() to add numbered boxes
            bboxes = self.page.evaluate("markPage()")
            
            # Small delay for boxes to render
            self.page.wait_for_timeout(500)
            
            # Take screenshot WITH boxes visible
            screenshot_bytes = self.page.screenshot(full_page=False)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            
            # Remove boxes for clean execution
            self.page.evaluate("unmarkPage()")
            
            return {
                "bboxes": bboxes,
                "screenshot": screenshot_bytes,
                "screenshot_b64": screenshot_b64
            }
            
        except Exception as e:
            print(f"⚠️  Annotation failed: {e}")
            return {"bboxes": [], "screenshot": b"", "screenshot_b64": ""}
    
    def execute_action(self, action: Dict, bboxes: List[Dict]) -> str:
        """
        Execute an action using Playwright
        
        Args:
            action: Action dictionary from Gemini
            bboxes: List of annotated elements
            
        Returns:
            Observation string describing what happened
        """
        if not self.page:
            return "Error: No page available"
        
        action_type = action['action']
        
        try:
            if action_type == 'click':
                return self._execute_click(action, bboxes)
            elif action_type == 'type':
                return self._execute_type(action, bboxes)
            elif action_type == 'scroll':
                return self._execute_scroll(action)
            elif action_type == 'wait':
                return self._execute_wait()
            elif action_type == 'finish':
                summary = action.get('summary', 'Task completed')
                return f"Task finished: {summary}"
            else:
                return f"Unknown action: {action_type}"
                
        except Exception as e:
            return f"Action failed: {str(e)}"
    
    def _execute_click(self, action: Dict, bboxes: List[Dict]) -> str:
        """Execute click action"""
        element_id = action.get('element_id', 0)
        
        if element_id >= len(bboxes):
            return f"Error: Element [{element_id}] not found (max: {len(bboxes)-1})"
        
        bbox = bboxes[element_id]
        
        # Log what we're about to click for debugging
        print(f"     🎯 Clicking element [{element_id}]:")
        print(f"       Text: '{bbox['text'][:50].strip()}'")
        print(f"       Type: {bbox['type']}")
        print(f"       Position: ({bbox['x']}, {bbox['y']})")
        if bbox.get('ariaLabel'):
            print(f"       Aria-label: '{bbox['ariaLabel'][:30]}'")
        
        # Click at center coordinates
        self.page.mouse.click(bbox['x'], bbox['y'])
        
        # Wait for potential navigation/modal
        self.page.wait_for_timeout(1000)
        
        return f"Clicked element [{element_id}]: {bbox['text'][:50].strip()}"
    
    def _execute_type(self, action: Dict, bboxes: List[Dict]) -> str:
        """Execute type action"""
        element_id = action.get('element_id', 0)
        text = action.get('text', '')
        
        if element_id >= len(bboxes):
            return f"Error: Element [{element_id}] not found"
        
        bbox = bboxes[element_id]
        
        # Click to focus
        self.page.mouse.click(bbox['x'], bbox['y'])
        self.page.wait_for_timeout(300)
        
        # Clear existing text with platform-appropriate shortcut
        select_all = "Meta+A" if sys.platform == "darwin" else "Control+A"
        self.page.keyboard.press(select_all)
        self.page.keyboard.press("Backspace")
        
        # Type new text
        self.page.keyboard.type(text, delay=50)
        
        # Wait for any autocomplete/validation
        self.page.wait_for_timeout(1200)
        
        return f"Typed into [{element_id}]: '{text}'"
    
    def _execute_scroll(self, action: Dict) -> str:
        """Execute scroll action"""
        direction = action.get('direction', 'down')
        amount = 500 if direction == 'down' else -500
        
        self.page.mouse.wheel(0, amount)
        self.page.wait_for_timeout(1000)
        
        return f"Scrolled {direction}"
    
    def _execute_wait(self) -> str:
        """Execute wait action"""
        self.page.wait_for_timeout(1000)
        return "Waited 1 second"
    
    def get_current_url(self) -> str:
        """Get current page URL"""
        if self.page:
            return self.page.url
        return ""
    
    def get_page_title(self) -> str:
        """Get current page title"""
        if self.page:
            try:
                return self.page.title()
            except:
                return ""
        return ""
    
    def cleanup(self):
        """Clean up browser resources"""
        try:
            print("🧹 Cleaning up browser...")
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            print("✅ Browser closed cleanly")
        except Exception as e:
            print(f"⚠️  Browser cleanup warning: {e}")
        finally:
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None
