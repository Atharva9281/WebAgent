"""
Response parsing utilities for Gemini client.

This module contains functions for parsing Gemini API responses into structured actions.
"""

from typing import Dict, List, Optional
import re


def parse_action_response(response_text: str) -> Dict:
    """
    Parse Gemini's action response into structured format
    
    Args:
        response_text: Raw response from Gemini
        
    Returns:
        Structured action dictionary
    """
    # Extract reasoning and action line
    reasoning_text = ""
    if "ACTION:" in response_text:
        parts = response_text.split("ACTION:")
        reasoning_text = parts[0].strip()
        action_line = parts[-1].strip()
    else:
        action_line = response_text.strip()
    
    # Remove any markdown formatting
    action_line = action_line.replace("`", "").strip()
    
    # Parse action
    parts = action_line.split(";", 1)
    main_part = parts[0].strip()
    
    # Extract action type
    action_words = main_part.split()
    if not action_words:
        return {
            "action": "wait",
            "raw_response": response_text,
            "reasoning": reasoning_text or "Could not parse action"
        }
    
    action_type = action_words[0].lower()
    
    result = {
        "action": action_type,
        "raw_response": response_text,
        "reasoning": reasoning_text
    }
    
    # Parse based on action type
    if action_type == "click":
        result.update(parse_click_action(main_part))
    elif action_type == "type":
        result.update(parse_type_action(main_part, parts))
    elif action_type == "scroll":
        result.update(parse_scroll_action(action_line))
    elif action_type == "finish":
        result.update(parse_finish_action(parts))
    else:
        # Handle cases where Gemini returns JSON-like shorthand
        result = handle_alternative_formats(action_type, main_part, parts, result)

    return result


def handle_alternative_formats(action_type: str, main_part: str, parts: List[str], result: Dict) -> Dict:
    """Handle alternative response formats from Gemini"""
    normalized = action_type.strip()
    lowered = normalized.lower()
    
    if "answer" in lowered:
        if "finish" in lowered:
            result["action"] = "finish"
            result.update(parse_finish_action(parts))
        elif "wait" in lowered:
            result["action"] = "wait"
        elif "click" in lowered:
            result["action"] = "click"
            result.update(parse_click_action(main_part))
        elif "type" in lowered:
            result["action"] = "type"
            result.update(parse_type_action(main_part, parts))
        else:
            result["action"] = "wait"
    elif normalized in {"wait", "finish", "click", "type", "scroll"}:
        result["action"] = normalized
        if normalized == "finish":
            result.update(parse_finish_action(parts))
        elif normalized == "click":
            result.update(parse_click_action(main_part))
        elif normalized == "type":
            result.update(parse_type_action(main_part, parts))
        elif normalized == "scroll":
            result.update(parse_scroll_action(main_part))
    else:
        result["action"] = "wait"
        result["reasoning"] = "Unrecognized action payload, defaulting to wait"
        
    return result


def parse_click_action(main_part: str) -> Dict:
    """Parse click action to extract element ID"""
    element_id = extract_element_id(main_part)
    return {"element_id": element_id if element_id is not None else 0}


def parse_type_action(main_part: str, parts: List[str]) -> Dict:
    """Parse type action to extract element ID and text"""
    result = {}
    
    element_id = extract_element_id(main_part)
    result["element_id"] = element_id if element_id is not None else 0
    
    # Extract text after semicolon
    if len(parts) > 1:
        result["text"] = parts[1].strip()
    else:
        result["text"] = ""

    return result


def extract_element_id(text: str) -> Optional[int]:
    """Extract a numeric element identifier from Gemini output."""
    match = re.search(r"\[(\d+)\]", text)
    if not match:
        match = re.search(r"(\d+)", text)
    if not match:
        return None
    number_text = next(group for group in match.groups() if group)
    try:
        return int(number_text)
    except (TypeError, ValueError):
        return None


def parse_scroll_action(action_line: str) -> Dict:
    """Parse scroll action to extract direction"""
    if "down" in action_line.lower():
        return {"direction": "down"}
    else:
        return {"direction": "up"}


def parse_finish_action(parts: List[str]) -> Dict:
    """Parse finish action to extract summary"""
    if len(parts) > 1:
        return {"summary": parts[1].strip()}
    else:
        return {"summary": "Task completed"}