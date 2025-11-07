"""
Browser utility functions and helpers.

This module contains utility functions for browser operations,
image processing, and font handling.
"""

import io
import sys
from pathlib import Path
from typing import Dict, List
from PIL import Image, ImageDraw, ImageFont


def get_font():
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


def draw_label(draw, x: int, y: int, text: str, font):
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


def add_boxes_to_image(image_bytes: bytes, bboxes: List[Dict]) -> bytes:
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
    font = get_font()
    
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
        draw_label(draw, x, y, str(index), font)
    
    # Convert annotated image back to bytes
    output = io.BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def load_mark_page_script() -> str:
    """Load the clean mark_page.js annotation script"""
    mark_page_path = Path(__file__).parent.parent / "mark_page_clean.js"
    with open(mark_page_path, 'r') as f:
        return f.read()


def get_platform_select_all_shortcut() -> str:
    """Get the platform-appropriate select-all keyboard shortcut"""
    return "Meta+A" if sys.platform == "darwin" else "Control+A"


def validate_element_bounds(element_id: int, bboxes: List[Dict]) -> bool:
    """
    Validate that an element ID is within bounds of available elements
    
    Args:
        element_id: Element index to validate
        bboxes: List of available bounding boxes
        
    Returns:
        True if element ID is valid, False otherwise
    """
    return 0 <= element_id < len(bboxes)


def get_element_info_for_logging(bbox: Dict) -> Dict[str, str]:
    """
    Extract useful element information for logging purposes
    
    Args:
        bbox: Bounding box dictionary
        
    Returns:
        Dictionary with formatted element information
    """
    return {
        "text": bbox.get('text', '')[:50].strip(),
        "type": bbox.get('type', ''),
        "position": f"({bbox.get('centerX', 0)}, {bbox.get('centerY', 0)})",
        "aria_label": bbox.get('ariaLabel', '')[:30] if bbox.get('ariaLabel') else ""
    }


def wait_for_page_load(page, timeout: int = 30000) -> bool:
    """
    Robust page loading with multiple fallbacks
    
    Args:
        page: Playwright page object
        timeout: Timeout in milliseconds
        
    Returns:
        True if page loaded successfully
    """
    try:
        # Try networkidle first (most robust)
        page.wait_for_load_state("networkidle", timeout=timeout)
        print("✅ Page fully loaded")
        return True
    except Exception as e:
        print(f"⚠️  Networkidle timeout ({e}), trying domcontentloaded...")
        try:
            # Fallback to DOM content loaded
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            print("✅ DOM content loaded")
            return True
        except Exception as e2:
            print(f"⚠️  DOM timeout ({e2}), proceeding anyway...")
            return False


def setup_anti_detection(context):
    """Add anti-detection scripts to browser context"""
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = window.chrome || {};
        window.chrome.runtime = window.chrome.runtime || {};
    """)


def create_browser_args(maximized: bool = True, disable_automation: bool = True) -> List[str]:
    """
    Create browser launch arguments
    
    Args:
        maximized: Whether to start maximized
        disable_automation: Whether to disable automation detection
        
    Returns:
        List of browser arguments
    """
    args = []
    
    if maximized:
        args.append('--start-maximized')
    
    if disable_automation:
        args.append('--disable-blink-features=AutomationControlled')
    
    return args


def get_ignore_args(disable_automation: bool = True) -> List[str]:
    """
    Get arguments to ignore for stealth mode
    
    Args:
        disable_automation: Whether to disable automation features
        
    Returns:
        List of arguments to ignore
    """
    if disable_automation:
        return ['--enable-automation']
    return []



def cleanup_browser_resources(playwright_instance, browser, context):
    """
    Clean up browser resources safely
    
    Args:
        playwright_instance: Playwright instance
        browser: Browser instance
        context: Browser context
    """
    try:
        print("🧹 Cleaning up clean browser...")
        if context:
            context.close()
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        print("✅ Clean browser closed cleanly")
    except Exception as e:
        print(f"⚠️  Clean browser cleanup warning: {e}")