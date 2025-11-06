"""
UI State Detection Utilities

Detects non-URL UI states:
- Modal dialogs
- Form fields and their values
- Dropdown menus
- Loading states
- Visual changes

Used by agent.py to capture rich metadata about page state.
"""

from playwright.sync_api import Page
from typing import List, Dict, Optional
import hashlib


def detect_modals(page: Page) -> List[Dict]:
    """
    Detect if any modal/dialog is currently open on the page
    
    Args:
        page: Playwright page object
        
    Returns:
        List of detected modals with their properties
    """
    modals = []
    
    try:
        # Check for ARIA role="dialog"
        dialogs = page.query_selector_all('[role="dialog"]')
        for dialog in dialogs:
            try:
                if not dialog.is_visible():
                    continue
                try:
                    bbox = dialog.bounding_box()
                except Exception:
                    bbox = None
                if not bbox or bbox.get("width", 0) < 10 or bbox.get("height", 0) < 10:
                    continue
                # Try to get modal title
                title = ""
                try:
                    title_element = dialog.query_selector('h1, h2, h3, [class*="title"], [class*="heading"]')
                    if title_element:
                        title = title_element.text_content() or ""
                except Exception:
                    pass

                modals.append({
                    "type": "dialog",
                    "title": title.strip()[:100],
                    "visible": True,
                    "state": "visible",
                    "bbox": bbox
                })
            except Exception:
                continue
        
        # Check for common modal class patterns
        modal_selectors = [
            '[class*="modal"][class*="open"]',
            '[class*="Modal"][class*="visible"]',
            '[data-state="open"]',
            '[aria-modal="true"]'
        ]
        
        for selector in modal_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements:
                    if element.is_visible():
                        try:
                            bbox = element.bounding_box()
                        except Exception:
                            bbox = None
                        if not bbox or bbox.get("width", 0) < 10 or bbox.get("height", 0) < 10:
                            continue
                        # Avoid duplicates
                        if not any(m.get("type") == "modal" for m in modals):
                            modals.append({
                                "type": "modal",
                                "selector": selector,
                                "visible": True,
                                "state": "visible",
                                "bbox": bbox
                            })
                        break
            except:
                continue
        
        # Check for overlay (backdrop)
        try:
            overlay = page.query_selector('[class*="overlay"], [class*="backdrop"]')
            if overlay and overlay.is_visible():
                try:
                    bbox = overlay.bounding_box()
                except Exception:
                    bbox = None
                if (
                    bbox
                    and bbox.get("width", 0) >= 10
                    and bbox.get("height", 0) >= 10
                    and not modals  # Only add if no other modals detected
                ):
                    modals.append({
                        "type": "overlay",
                        "visible": True,
                        "state": "visible",
                        "bbox": bbox
                    })
        except:
            pass
            
    except Exception as e:
        print(f"Warning: Error detecting modals: {e}")
    
    if not modals:
        return modals

    deduped = []
    seen = set()
    for modal in modals:
        bbox = modal.get("bbox") or {}
        key = None
        if bbox:
            key = (
                round(bbox.get("x", 0), 1),
                round(bbox.get("y", 0), 1),
                round(bbox.get("width", 0), 1),
                round(bbox.get("height", 0), 1),
            )
        else:
            key = modal.get("selector") or modal.get("title") or modal.get("type")

        if key in seen:
            continue
        seen.add(key)

        # Normalise when width is extremely small (likely invisible artifact)
        if bbox and (bbox.get("width", 0) < 10 or bbox.get("height", 0) < 10):
            continue

        deduped.append(modal)

    return deduped


def get_form_states(page: Page) -> List[Dict]:
    """
    Get all form fields and their current values
    
    Args:
        page: Playwright page object
        
    Returns:
        List of form fields with their current state
    """
    form_fields = []
    
    try:
        # Find all visible input elements
        inputs = page.query_selector_all('input, textarea, select')
        
        for input_element in inputs:
            try:
                # Skip if not visible
                if not input_element.is_visible():
                    continue
                
                # Skip hidden inputs
                input_type = input_element.get_attribute('type') or 'text'
                if input_type == 'hidden':
                    continue
                
                # Get field properties
                field_info = {
                    "type": input_element.evaluate('el => el.tagName.toLowerCase()'),
                    "input_type": input_type,
                    "name": input_element.get_attribute('name') or '',
                    "placeholder": input_element.get_attribute('placeholder') or '',
                    "id": input_element.get_attribute('id') or '',
                    "aria_label": input_element.get_attribute('aria-label') or '',
                    "value": "",
                    "filled": False
                }
                
                # Get current value
                try:
                    if field_info["type"] == "select":
                        value = input_element.input_value() or ""
                    else:
                        value = input_element.input_value() or ""
                    
                    field_info["value"] = value[:200]  # Limit length
                    field_info["filled"] = len(value) > 0
                except:
                    pass
                
                # Get label if exists
                try:
                    # Try to find associated label
                    if field_info["id"]:
                        label = page.query_selector(f'label[for="{field_info["id"]}"]')
                        if label:
                            field_info["label"] = (label.text_content() or "")[:100]
                except:
                    pass

                field_info["state"] = "filled" if field_info["filled"] else "empty"
                
                form_fields.append(field_info)
                
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Warning: Error getting form states: {e}")
    
    return form_fields


def summarise_forms(page: Page) -> Dict:
    """Build lightweight summary statistics for form controls."""
    summary = {
        "checkbox_count": 0,
        "filled_count": 0
    }

    try:
        checkboxes = page.query_selector_all('input[type="checkbox"]')
        summary["checkbox_count"] = len(checkboxes)

        filled = 0
        for checkbox in checkboxes:
            try:
                if checkbox.is_checked():
                    filled += 1
            except Exception:
                try:
                    if checkbox.evaluate("el => !!el.checked"):
                        filled += 1
                except Exception:
                    continue

        summary["filled_count"] = filled
    except Exception:
        pass

    return summary


def detect_dropdowns_open(page: Page) -> List[Dict]:
    """
    Detect if any dropdown menus are currently open
    
    Args:
        page: Playwright page object
        
    Returns:
        List of open dropdowns
    """
    dropdowns = []
    
    try:
        # Check for ARIA expanded attributes
        expanded_elements = page.query_selector_all('[aria-expanded="true"]')
        
        for element in expanded_elements:
            if element.is_visible():
                dropdowns.append({
                    "type": "expanded",
                    "aria_label": element.get_attribute('aria-label') or '',
                    "visible": True,
                    "state": "visible"
                })
        
        # Check for role="listbox" or role="menu"
        listboxes = page.query_selector_all('[role="listbox"], [role="menu"]')
        for listbox in listboxes:
            if listbox.is_visible():
                dropdowns.append({
                    "type": "listbox",
                    "visible": True,
                    "state": "visible"
                })
                
    except Exception as e:
        print(f"Warning: Error detecting dropdowns: {e}")
    
    return dropdowns


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


# Example usage (for testing)
if __name__ == "__main__":
    print("State detector utility module loaded")
    print("\nAvailable functions:")
    print("  - detect_modals(page)")
    print("  - get_form_states(page)")
    print("  - detect_dropdowns_open(page)")
    print("  - detect_loading_state(page)")
    print("  - get_complete_ui_state(page)")
    print("  - describe_ui_state(ui_state)")
