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
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from PIL import Image, ImageDraw, ImageFont
from task_definitions import get_session_file


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
        mark_page_path = Path(__file__).parent / "mark_page_clean.js"
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
            
            self.page = self.context.new_page()
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
            self.page.wait_for_timeout(3000)
            
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
            annotated_bytes = self._add_boxes_to_image(screenshot_bytes, bboxes)
            
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
    
    def _add_boxes_to_image(self, image_bytes: bytes, bboxes: List[Dict]) -> bytes:
        """
        Add numbered bounding boxes to a screenshot image using PIL
        
        Args:
            image_bytes: Original clean screenshot bytes
            bboxes: List of bounding box data from JavaScript
            
        Returns:
            Annotated image bytes with red numbered boxes
        """
        # Load image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        draw = ImageDraw.Draw(image)
        
        # Try to load a good font (fallback to default if not available)
        font = self._get_font()
        
        # Draw boxes and labels for each interactive element
        for bbox in bboxes:
            x, y = bbox['x'], bbox['y']
            w, h = bbox['width'], bbox['height']
            index = bbox['index']
            
            # Draw red bounding box outline
            draw.rectangle(
                [x, y, x + w, y + h],
                outline='red',
                width=2
            )
            
            # Draw numbered label
            self._draw_label(draw, x, y, str(index), font)
        
        # Convert annotated image back to bytes
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()
    
    def _get_font(self):
        """Get the best available font for labels"""
        # Try common font paths
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "/System/Library/Fonts/Helvetica.ttc",                  # macOS
            "C:/Windows/Fonts/arial.ttf",                           # Windows
            "Arial.ttf"                                              # Generic
        ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, 16)
            except:
                continue
        
        # Fallback to default font
        try:
            return ImageFont.load_default()
        except:
            return None
    
    def _draw_label(self, draw, x: int, y: int, text: str, font):
        """Draw a numbered label with background"""
        # Calculate text size
        try:
            if font:
                bbox_text = draw.textbbox((0, 0), text, font=font)
                text_width = bbox_text[2] - bbox_text[0]
                text_height = bbox_text[3] - bbox_text[1]
            else:
                text_width, text_height = len(text) * 10, 16
        except:
            text_width, text_height = len(text) * 10, 16
        
        # Draw red background for label
        padding = 4
        draw.rectangle(
            [x, y, x + text_width + 2 * padding, y + text_height + 2 * padding],
            fill='red'
        )
        
        # Draw white text
        draw.text(
            (x + padding, y + padding),
            text,
            fill='white',
            font=font
        )
    
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
        """Execute click action using center coordinates"""
        element_id = action.get('element_id', 0)
        
        if element_id >= len(bboxes):
            return f"Error: Element [{element_id}] not found (max: {len(bboxes)-1})"
        
        bbox = bboxes[element_id]
        
        # Log what we're about to click for debugging
        print(f"     🎯 Clicking element [{element_id}] on CLEAN page:")
        print(f"       Text: '{bbox['text'][:50].strip()}'")
        print(f"       Type: {bbox['type']}")
        print(f"       Position: ({bbox['centerX']}, {bbox['centerY']})")
        if bbox.get('ariaLabel'):
            print(f"       Aria-label: '{bbox['ariaLabel'][:30]}'")
        
        # Click at center coordinates (more reliable than corners)
        self.page.mouse.click(bbox['centerX'], bbox['centerY'])
        
        # Wait for potential navigation/modal
        self.page.wait_for_timeout(2000)
        
        return f"Clicked element [{element_id}]: {bbox['text'][:50].strip()}"
    
    def _execute_type(self, action: Dict, bboxes: List[Dict]) -> str:
        """Execute type action"""
        element_id = action.get('element_id', 0)
        text = action.get('text', '')
        
        if element_id >= len(bboxes):
            return f"Error: Element [{element_id}] not found"
        
        bbox = bboxes[element_id]
        
        # Click to focus at center
        self.page.mouse.click(bbox['centerX'], bbox['centerY'])
        self.page.wait_for_timeout(300)
        
        # Clear existing text
        self.page.keyboard.press("Control+A")
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
        self.page.wait_for_timeout(3000)
        return "Waited 3 seconds"
    
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
            print("🧹 Cleaning up clean browser...")
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            print("✅ Clean browser closed cleanly")
        except Exception as e:
            print(f"⚠️  Clean browser cleanup warning: {e}")
        finally:
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None