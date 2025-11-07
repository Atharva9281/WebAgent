"""
Main UI state detection orchestrator.

This module provides the main interface for detecting UI states,
combining modal detection, form analysis, loading states, and page changes.
"""

import hashlib
from playwright.sync_api import Page
from typing import Dict

from .modal_detector import detect_modals, detect_dropdowns_open
from .form_detector import get_form_states, summarise_forms


def detect_loading_state(page: Page) -> Dict:
    """
    Detect if page is in a loading state
    
    Args:
        page: Playwright page object
        
    Returns:
        Dict with loading state information
    """
    loading = {
        "state": "idle",
        "is_loading": False,
        "indicators": []
    }
    
    try:
        # Check for common loading indicators
        loading_selectors = [
            '[class*="loading"]',
            '[class*="spinner"]',
            '[aria-busy="true"]',
            '[class*="skeleton"]',
            '[data-loading="true"]'
        ]
        
        for selector in loading_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements:
                    if element.is_visible():
                        loading["state"] = "active"
                        loading["is_loading"] = True
                        loading["indicators"].append(selector)
                        break
            except:
                continue
                
    except Exception as e:
        print(f"Warning: Error detecting loading state: {e}")
    
    return loading


def get_page_hash(page: Page) -> str:
    """
    Generate a hash of the current page state for change detection
    
    Args:
        page: Playwright page object
        
    Returns:
        Hash string of page content
    """
    try:
        # Get page content (text only, no HTML)
        content = page.evaluate('''() => {
            return document.body.innerText || '';
        }''')
        
        # Create hash
        return hashlib.md5(content.encode()).hexdigest()
    except:
        return ""


def ui_state_changed(page: Page, previous_hash: str) -> bool:
    """
    Check if UI state has changed since last check
    
    Args:
        page: Playwright page object
        previous_hash: Hash from previous state
        
    Returns:
        True if state changed, False otherwise
    """
    current_hash = get_page_hash(page)
    return current_hash != previous_hash


def get_complete_ui_state(page: Page) -> Dict:
    """
    Get complete UI state snapshot
    Combines all detection methods into one comprehensive state
    
    Args:
        page: Playwright page object
        
    Returns:
        Complete UI state dictionary
    """
    return {
        "url": page.url,
        "title": page.title() if hasattr(page, 'title') else "",
        "modals": detect_modals(page),
        "forms": get_form_states(page),
        "forms_summary": summarise_forms(page),
        "dropdowns": detect_dropdowns_open(page),
        "loading": detect_loading_state(page),
        "page_hash": get_page_hash(page)
    }


def describe_ui_state(ui_state: Dict) -> str:
    """
    Generate human-readable description of UI state
    
    Args:
        ui_state: UI state dictionary from get_complete_ui_state()
        
    Returns:
        Human-readable description string
    """
    descriptions = []
    
    # URL
    descriptions.append(f"Page: {ui_state['url']}")
    
    # Modals
    if ui_state['modals']:
        modal_count = len(ui_state['modals'])
        if modal_count == 1:
            modal_type = ui_state['modals'][0].get('type', 'modal')
            modal_title = ui_state['modals'][0].get('title', '')
            if modal_title:
                descriptions.append(f"{modal_type.title()} opened: '{modal_title}'")
            else:
                descriptions.append(f"{modal_type.title()} is open")
        else:
            descriptions.append(f"{modal_count} modals/dialogs open")
    
    # Forms
    filled_forms = [f for f in ui_state['forms'] if f['filled']]
    empty_forms = [f for f in ui_state['forms'] if not f['filled']]
    
    if filled_forms:
        descriptions.append(f"{len(filled_forms)} form field(s) filled")
    if empty_forms:
        descriptions.append(f"{len(empty_forms)} empty form field(s) visible")
    
    # Dropdowns
    if ui_state['dropdowns']:
        descriptions.append(f"{len(ui_state['dropdowns'])} dropdown(s) open")
    
    # Loading
    if ui_state['loading']['is_loading']:
        descriptions.append("Page is loading...")
    
    if not descriptions:
        descriptions.append("Standard page view")
    
    return " | ".join(descriptions)


def get_state_changes(current_state: Dict, previous_state: Dict) -> Dict:
    """
    Compare two UI states and identify what changed
    
    Args:
        current_state: Current UI state
        previous_state: Previous UI state  
        
    Returns:
        Dictionary describing what changed
    """
    changes = {
        "url_changed": False,
        "modals_changed": False,
        "forms_changed": False,
        "loading_changed": False,
        "content_changed": False,
        "changes_summary": []
    }
    
    if not previous_state:
        changes["changes_summary"].append("Initial state")
        return changes
    
    # Check URL changes
    if current_state.get("url") != previous_state.get("url"):
        changes["url_changed"] = True
        changes["changes_summary"].append("URL changed")
    
    # Check modal changes  
    current_modals = len(current_state.get("modals", []))
    previous_modals = len(previous_state.get("modals", []))
    if current_modals != previous_modals:
        changes["modals_changed"] = True
        if current_modals > previous_modals:
            changes["changes_summary"].append("Modal opened")
        else:
            changes["changes_summary"].append("Modal closed")
    
    # Check form changes
    current_filled = len([f for f in current_state.get("forms", []) if f.get("filled")])
    previous_filled = len([f for f in previous_state.get("forms", []) if f.get("filled")])
    if current_filled != previous_filled:
        changes["forms_changed"] = True
        changes["changes_summary"].append("Form fields changed")
    
    # Check loading state changes
    current_loading = current_state.get("loading", {}).get("is_loading", False)
    previous_loading = previous_state.get("loading", {}).get("is_loading", False)
    if current_loading != previous_loading:
        changes["loading_changed"] = True
        if current_loading:
            changes["changes_summary"].append("Started loading")
        else:
            changes["changes_summary"].append("Finished loading")
    
    # Check content changes via hash
    current_hash = current_state.get("page_hash", "")
    previous_hash = previous_state.get("page_hash", "")
    if current_hash != previous_hash and current_hash and previous_hash:
        changes["content_changed"] = True
        changes["changes_summary"].append("Page content changed")
    
    if not changes["changes_summary"]:
        changes["changes_summary"].append("No significant changes detected")
    
    return changes