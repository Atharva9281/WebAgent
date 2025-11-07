"""
Clean Browser Controller Module

Handles all browser-related operations with CLEAN image annotation:
- Authentication (persistent profiles + session files)
- Page loading and navigation
- Action execution (click, type, scroll)
- Screenshot capture with PIL-based annotation (NO DOM manipulation)

Key Innovation: User sees clean page throughout automation while
Gemini sees annotated screenshots for decision making.
"""

import os
import base64
from typing import Dict, List
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from task_definitions import get_session_file

from .utils import (
    add_boxes_to_image,
    load_mark_page_script,
    wait_for_page_load,
    setup_anti_detection,
    create_browser_args,
    get_ignore_args,
    cleanup_browser_resources
)
from .actions import (
    execute_action,
    take_screenshot,
    wait_for_selector,
    evaluate_javascript
)


class CleanBrowserController:
    """
    Manages browser operations with clean image annotation
    (NO DOM manipulation - uses PIL for image annotation)
    """
    
    def __init__(self):
        """Initialize clean browser controller"""
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.mark_page_script = None
        self._load_mark_page_script()
    
    def _load_mark_page_script(self):
        """Load the clean mark_page.js annotation script"""
        self.mark_page_script = load_mark_page_script()
    
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
                return self._setup_with_persistent_profile(profile_dir)
            else:
                return self._setup_with_session_file(session_file)
                
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            self.cleanup()
            return False
    
    def _setup_with_persistent_profile(self, profile_dir: str) -> bool:
        """Setup browser with persistent profile"""
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            channel="chrome",
            viewport={'width': 1920, 'height': 1080},
            slow_mo=1000,
            args=create_browser_args(),
            ignore_default_args=get_ignore_args()
        )
        
        # Add anti-detection script
        setup_anti_detection(self.context)
        self.browser = None  # No separate browser object
        
        return self._setup_page()
    
    def _setup_with_session_file(self, session_file: str) -> bool:
        """Setup browser with session file"""
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
        
        return self._setup_page()
    
    def _setup_page(self) -> bool:
        """Setup the main page and close extra pages"""
        existing_pages = self.context.pages
        if existing_pages:
            self.page = existing_pages[0]
        else:
            self.page = self.context.new_page()

        # Close extra pages
        for extra in list(self.context.pages):
            if extra != self.page:
                try:
                    extra.close()
                except Exception:
                    pass
        return True
    
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
            
            # More robust page loading for slow sites
            print("⏳ Waiting for page to load...")
            wait_for_page_load(self.page)
            
            # Give extra time for any dynamic content
            print("🕐 Allowing time for dynamic content...")
            self.page.wait_for_timeout(1000)
            
            print("✅ Navigation complete - Page is CLEAN (no visual annotations)\n")
            return True
            
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            return False
    
    def annotate_and_capture_clean(self) -> Dict:
        """
        Get element data and create annotated screenshot using PIL
        WITHOUT any DOM manipulation (user sees clean page)
        
        Returns:
            Dict with bboxes, clean screenshot, and annotated screenshot
        """
        if not self.page:
            return {"bboxes": [], "screenshot": b"", "screenshot_b64": ""}
        
        try:
            print("📍 Getting element positions (NO DOM changes)...")
            
            # 1. Inject clean script and get element data (NO visual changes)
            self.page.evaluate(self.mark_page_script)
            bboxes = self.page.evaluate("getInteractiveElements()")
            
            print(f"   Found {len(bboxes)} interactive elements")
            
            # 2. Take clean screenshot (user sees this clean version)
            print("📸 Taking clean screenshot...")
            screenshot_bytes = self.page.screenshot(full_page=False)
            
            # 3. Add boxes to image using Python PIL (not DOM)
            print("🎨 Adding annotations to image copy (PIL)...")
            annotated_bytes = add_boxes_to_image(screenshot_bytes, bboxes)
            
            # 4. Encode annotated version for Gemini
            screenshot_b64 = base64.b64encode(annotated_bytes).decode()
            
            print("✅ Clean annotation complete")
            print("   👀 User sees: Clean page (no boxes)")
            print("   🤖 Gemini sees: Annotated screenshot")
            
            return {
                "bboxes": bboxes,
                "screenshot": screenshot_bytes,      # Clean for saving
                "screenshot_b64": screenshot_b64     # Annotated for Gemini
            }
            
        except Exception as e:
            print(f"⚠️  Clean annotation failed: {e}")
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
        return execute_action(self.page, action, bboxes)
    
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
    
    def take_screenshot(self, full_page: bool = False) -> bytes:
        """Take a screenshot of the current page"""
        return take_screenshot(self.page, full_page)
    
    def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for a selector to appear on the page"""
        return wait_for_selector(self.page, selector, timeout)
    
    def evaluate_javascript(self, script: str):
        """Execute JavaScript in the page context"""
        return evaluate_javascript(self.page, script)
    
    def cleanup(self):
        """Clean up browser resources"""
        cleanup_browser_resources(self.playwright, self.browser, self.context)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None