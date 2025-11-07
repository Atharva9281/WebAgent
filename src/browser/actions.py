"""
Browser action execution methods.

This module contains all the action execution logic for browser automation,
including click, type, scroll, and wait operations.
"""

import sys
from typing import Dict, List
from .utils import (
    validate_element_bounds, 
    get_element_info_for_logging,
    get_platform_select_all_shortcut
)


def take_screenshot(page, full_page: bool = False) -> bytes:
    """
    Take a screenshot of the current page
    
    Args:
        page: Playwright page object
        full_page: Whether to take a full page screenshot
        
    Returns:
        Screenshot bytes
    """
    if page:
        try:
            return page.screenshot(full_page=full_page)
        except Exception as e:
            print(f"⚠️  Screenshot failed: {e}")
            return b""
    return b""


def wait_for_selector(page, selector: str, timeout: int = 10000) -> bool:
    """
    Wait for a selector to appear on the page
    
    Args:
        page: Playwright page object
        selector: CSS selector to wait for
        timeout: Timeout in milliseconds
        
    Returns:
        True if element appeared, False otherwise
    """
    if not page:
        return False
    
    try:
        page.wait_for_selector(selector, timeout=timeout)
        return True
    except:
        return False


def evaluate_javascript(page, script: str):
    """
    Execute JavaScript in the page context
    
    Args:
        page: Playwright page object
        script: JavaScript code to execute
        
    Returns:
        Result of the JavaScript execution
    """
    if page:
        try:
            return page.evaluate(script)
        except Exception as e:
            print(f"⚠️  JavaScript evaluation failed: {e}")
            return None
    return None


def execute_action(page, action: Dict, bboxes: List[Dict]) -> str:
    """
    Execute an action using Playwright
    
    Args:
        page: Playwright page object
        action: Action dictionary from Gemini
        bboxes: List of annotated elements
        
    Returns:
        Observation string describing what happened
    """
    if not page:
        return "Error: No page available"
    
    action_type = action['action']
    
    try:
        if action_type == 'click':
            return execute_click(page, action, bboxes)
        elif action_type == 'type':
            return execute_type(page, action, bboxes)
        elif action_type == 'scroll':
            return execute_scroll(page, action)
        elif action_type == 'wait':
            return execute_wait(page)
        elif action_type == 'finish':
            summary = action.get('summary', 'Task completed')
            return f"Task finished: {summary}"
        else:
            return f"Unknown action: {action_type}"
            
    except Exception as e:
        return f"Action failed: {str(e)}"


def execute_click(page, action: Dict, bboxes: List[Dict]) -> str:
    """Execute click action using center coordinates"""
    element_id = action.get('element_id', 0)
    
    if not validate_element_bounds(element_id, bboxes):
        return f"Error: Element [{element_id}] not found (max: {len(bboxes)-1})"
    
    bbox = bboxes[element_id]
    element_info = get_element_info_for_logging(bbox)
    
    # Log what we're about to click for debugging
    print(f"     🎯 Clicking element [{element_id}] on CLEAN page:")
    print(f"       Text: '{element_info['text']}'")
    print(f"       Type: {element_info['type']}")
    print(f"       Position: {element_info['position']}")
    if element_info['aria_label']:
        print(f"       Aria-label: '{element_info['aria_label']}'")
    
    # Click at center coordinates (more reliable than corners)
    page.mouse.click(bbox['centerX'], bbox['centerY'])
    
    # Wait for potential navigation/modal
    page.wait_for_timeout(1000)
    
    return f"Clicked element [{element_id}]: {element_info['text']}"


def execute_type(page, action: Dict, bboxes: List[Dict]) -> str:
    """Execute type action"""
    element_id = action.get('element_id', 0)
    text = action.get('text', '')
    
    if not validate_element_bounds(element_id, bboxes):
        return f"Error: Element [{element_id}] not found"
    
    bbox = bboxes[element_id]
    
    # Click to focus at center
    page.mouse.click(bbox['centerX'], bbox['centerY'])
    page.wait_for_timeout(300)
    
    # Clear existing text with platform-appropriate shortcut
    select_all = get_platform_select_all_shortcut()
    page.keyboard.press(select_all)
    page.keyboard.press("Backspace")
    
    # Type new text
    page.keyboard.type(text, delay=50)
    
    # Wait for any autocomplete/validation
    page.wait_for_timeout(1200)
    
    return f"Typed into [{element_id}]: '{text}'"


def execute_scroll(page, action: Dict) -> str:
    """Execute scroll action"""
    direction = action.get('direction', 'down')
    amount = 500 if direction == 'down' else -500
    
    page.mouse.wheel(0, amount)
    page.wait_for_timeout(1000)
    
    return f"Scrolled {direction}"


def execute_wait(page) -> str:
    """Execute wait action"""
    page.wait_for_timeout(1000)
    return "Waited 1 second"


def execute_keyboard_shortcut(page, shortcut: str) -> str:
    """
    Execute a keyboard shortcut
    
    Args:
        page: Playwright page object
        shortcut: Keyboard shortcut string (e.g., "Control+A", "Meta+C")
        
    Returns:
        Observation string
    """
    try:
        page.keyboard.press(shortcut)
        page.wait_for_timeout(500)
        return f"Pressed {shortcut}"
    except Exception as e:
        return f"Failed to press {shortcut}: {str(e)}"


def execute_hover(page, element_id: int, bboxes: List[Dict]) -> str:
    """
    Execute hover action over an element
    
    Args:
        page: Playwright page object
        element_id: Element index to hover over
        bboxes: List of available elements
        
    Returns:
        Observation string
    """
    if not validate_element_bounds(element_id, bboxes):
        return f"Error: Element [{element_id}] not found"
    
    bbox = bboxes[element_id]
    element_info = get_element_info_for_logging(bbox)
    
    try:
        page.mouse.move(bbox['centerX'], bbox['centerY'])
        page.wait_for_timeout(500)
        return f"Hovered over [{element_id}]: {element_info['text']}"
    except Exception as e:
        return f"Failed to hover over element [{element_id}]: {str(e)}"


def execute_double_click(page, element_id: int, bboxes: List[Dict]) -> str:
    """
    Execute double click action
    
    Args:
        page: Playwright page object
        element_id: Element index to double click
        bboxes: List of available elements
        
    Returns:
        Observation string
    """
    if not validate_element_bounds(element_id, bboxes):
        return f"Error: Element [{element_id}] not found"
    
    bbox = bboxes[element_id]
    element_info = get_element_info_for_logging(bbox)
    
    try:
        page.mouse.dblclick(bbox['centerX'], bbox['centerY'])
        page.wait_for_timeout(1000)
        return f"Double-clicked element [{element_id}]: {element_info['text']}"
    except Exception as e:
        return f"Failed to double-click element [{element_id}]: {str(e)}"


def execute_right_click(page, element_id: int, bboxes: List[Dict]) -> str:
    """
    Execute right click (context menu) action
    
    Args:
        page: Playwright page object
        element_id: Element index to right click
        bboxes: List of available elements
        
    Returns:
        Observation string
    """
    if not validate_element_bounds(element_id, bboxes):
        return f"Error: Element [{element_id}] not found"
    
    bbox = bboxes[element_id]
    element_info = get_element_info_for_logging(bbox)
    
    try:
        page.mouse.click(bbox['centerX'], bbox['centerY'], button='right')
        page.wait_for_timeout(800)
        return f"Right-clicked element [{element_id}]: {element_info['text']}"
    except Exception as e:
        return f"Failed to right-click element [{element_id}]: {str(e)}"