"""
Modal and dialog detection utilities.

This module contains functions for detecting modal dialogs,
overlays, and other popup elements on web pages.
"""

from playwright.sync_api import Page
from typing import List, Dict


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
        modals.extend(_detect_aria_dialogs(page))
        
        # Check for common modal class patterns
        modals.extend(_detect_modal_classes(page))
        
        # Check for overlay (backdrop)
        modals.extend(_detect_overlays(page, modals))
            
    except Exception as e:
        print(f"Warning: Error detecting modals: {e}")
    
    # Remove duplicates and invalid modals
    return _deduplicate_modals(modals)


def _detect_aria_dialogs(page: Page) -> List[Dict]:
    """Detect modals with ARIA role='dialog'"""
    modals = []
    
    try:
        dialogs = page.query_selector_all('[role="dialog"]')
        for dialog in dialogs:
            try:
                if not dialog.is_visible():
                    continue
                    
                bbox = _get_element_bbox(dialog)
                if not _is_valid_bbox(bbox):
                    continue
                    
                # Try to get modal title
                title = _extract_modal_title(dialog)

                modals.append({
                    "type": "dialog",
                    "title": title.strip()[:100],
                    "visible": True,
                    "state": "visible",
                    "bbox": bbox
                })
            except Exception:
                continue
    except Exception:
        pass
        
    return modals


def _detect_modal_classes(page: Page) -> List[Dict]:
    """Detect modals using common CSS class patterns"""
    modals = []
    
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
                    bbox = _get_element_bbox(element)
                    if not _is_valid_bbox(bbox):
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
            
    return modals


def _detect_overlays(page: Page, existing_modals: List[Dict]) -> List[Dict]:
    """Detect backdrop overlays"""
    modals = []
    
    try:
        overlay = page.query_selector('[class*="overlay"], [class*="backdrop"]')
        if overlay and overlay.is_visible():
            bbox = _get_element_bbox(overlay)
            if (
                bbox
                and _is_valid_bbox(bbox)
                and not existing_modals  # Only add if no other modals detected
            ):
                modals.append({
                    "type": "overlay",
                    "visible": True,
                    "state": "visible",
                    "bbox": bbox
                })
    except:
        pass
        
    return modals


def _get_element_bbox(element):
    """Safely get element bounding box"""
    try:
        return element.bounding_box()
    except Exception:
        return None


def _is_valid_bbox(bbox) -> bool:
    """Check if bounding box is valid (not too small)"""
    if not bbox:
        return False
    return bbox.get("width", 0) >= 10 and bbox.get("height", 0) >= 10


def _extract_modal_title(dialog_element) -> str:
    """Extract title from a dialog element"""
    title = ""
    try:
        title_element = dialog_element.query_selector('h1, h2, h3, [class*="title"], [class*="heading"]')
        if title_element:
            title = title_element.text_content() or ""
    except Exception:
        pass
    return title


def _deduplicate_modals(modals: List[Dict]) -> List[Dict]:
    """Remove duplicate modals based on position and properties"""
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

        # Skip when width is extremely small (likely invisible artifact)
        if bbox and (bbox.get("width", 0) < 10 or bbox.get("height", 0) < 10):
            continue

        deduped.append(modal)

    return deduped


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