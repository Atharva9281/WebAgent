"""
Form field detection and analysis utilities.

This module contains functions for detecting form fields,
their values, and generating form state summaries.
"""

from playwright.sync_api import Page
from typing import List, Dict


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
                # Skip if not visible or hidden
                if not input_element.is_visible():
                    continue
                
                input_type = input_element.get_attribute('type') or 'text'
                if input_type == 'hidden':
                    continue
                
                # Get field properties
                field_info = _extract_field_info(input_element, input_type)
                
                # Get current value and determine if filled
                _set_field_value_and_state(input_element, field_info)
                
                # Try to find associated label
                _set_field_label(page, field_info)
                
                form_fields.append(field_info)
                
            except Exception:
                continue
                
    except Exception as e:
        print(f"Warning: Error getting form states: {e}")
    
    return form_fields


def _extract_field_info(input_element, input_type: str) -> Dict:
    """Extract basic field information"""
    return {
        "type": input_element.evaluate('el => el.tagName.toLowerCase()'),
        "input_type": input_type,
        "name": input_element.get_attribute('name') or '',
        "placeholder": input_element.get_attribute('placeholder') or '',
        "id": input_element.get_attribute('id') or '',
        "aria_label": input_element.get_attribute('aria-label') or '',
        "value": "",
        "filled": False
    }


def _set_field_value_and_state(input_element, field_info: Dict) -> None:
    """Set field value and filled state"""
    try:
        if field_info["type"] == "select":
            value = input_element.input_value() or ""
        else:
            value = input_element.input_value() or ""
        
        field_info["value"] = value[:200]  # Limit length
        field_info["filled"] = len(value) > 0
        field_info["state"] = "filled" if field_info["filled"] else "empty"
    except Exception:
        field_info["state"] = "empty"


def _set_field_label(page: Page, field_info: Dict) -> None:
    """Try to find and set associated label"""
    try:
        if field_info["id"]:
            label = page.query_selector(f'label[for="{field_info["id"]}"]')
            if label:
                field_info["label"] = (label.text_content() or "")[:100]
    except Exception:
        pass


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


def analyze_form_completion(forms: List[Dict]) -> Dict:
    """
    Analyze form completion status for automation hints
    
    Args:
        forms: List of form fields from get_form_states()
        
    Returns:
        Analysis results with completion status and suggestions
    """
    analysis = {
        "total_fields": len(forms),
        "filled_fields": 0,
        "empty_fields": 0,
        "required_fields": 0,
        "completion_percentage": 0.0,
        "has_required_empty": False,
        "ready_for_submit": False
    }
    
    if not forms:
        return analysis
    
    filled_count = 0
    required_empty_count = 0
    
    for field in forms:
        if field.get("filled", False):
            filled_count += 1
        
        # Check if field appears required (basic heuristics)
        is_required = _field_appears_required(field)
        if is_required:
            analysis["required_fields"] += 1
            if not field.get("filled", False):
                required_empty_count += 1
    
    analysis["filled_fields"] = filled_count
    analysis["empty_fields"] = len(forms) - filled_count
    analysis["completion_percentage"] = (filled_count / len(forms)) * 100
    analysis["has_required_empty"] = required_empty_count > 0
    analysis["ready_for_submit"] = required_empty_count == 0
    
    return analysis


def _field_appears_required(field: Dict) -> bool:
    """Check if a field appears to be required using heuristics"""
    # Check for common required field indicators
    indicators = [
        field.get("aria_label", "").lower(),
        field.get("placeholder", "").lower(),
        field.get("name", "").lower(),
        field.get("label", "").lower()
    ]
    
    required_keywords = ["required", "mandatory", "*", "must"]
    
    for indicator in indicators:
        if any(keyword in indicator for keyword in required_keywords):
            return True
    
    # Common required field types/names
    required_names = ["name", "title", "email", "password"]
    field_name = field.get("name", "").lower()
    
    return any(req_name in field_name for req_name in required_names)


def get_fillable_fields(page: Page) -> List[Dict]:
    """
    Get only the fields that are currently fillable (visible and enabled)
    
    Args:
        page: Playwright page object
        
    Returns:
        List of fillable form fields
    """
    all_fields = get_form_states(page)
    fillable = []
    
    for field in all_fields:
        # Skip already filled fields for efficiency
        if field.get("filled", False):
            continue
            
        # Skip non-text input types that we typically don't fill
        skip_types = ["submit", "button", "reset", "checkbox", "radio"]
        if field.get("input_type") in skip_types:
            continue
            
        fillable.append(field)
    
    return fillable