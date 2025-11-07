"""
Task completion validation logic.

This module contains validation functions for determining when tasks are complete.
"""

from typing import Dict
from .config import VALIDATION_PATTERNS


def validate_task_completion(
    task_config: Dict,
    current_url: str,
    page_title: str,
    action: Dict
) -> bool:
    """
    Validate if task is actually complete before accepting 'finish' action
    
    Args:
        task_config: Task configuration
        current_url: Current page URL  
        page_title: Current page title
        action: Proposed finish action
        
    Returns:
        True if task is genuinely complete, False otherwise
    """
    if action['action'] != 'finish':
        return True  # Not a finish action, so validation passes
    
    task_id = task_config['task_id']
    
    # Check if we have validation rules for this task
    if task_id not in VALIDATION_PATTERNS:
        return True  # No specific validation, accept finish
        
    validation_rule = VALIDATION_PATTERNS[task_id]
    return _validate_against_pattern(current_url, page_title, validation_rule)


def _validate_against_pattern(current_url: str, page_title: str, pattern: Dict) -> bool:
    """Validate URL and title against a pattern"""
    url_lower = current_url.lower()
    title_lower = page_title.lower()
    
    # Check URL patterns
    url_patterns = pattern.get("url_patterns", [])
    if url_patterns and not any(p in url_lower for p in url_patterns):
        # Check for minimum URL segments if specified
        min_segments = pattern.get("min_url_segments")
        if min_segments and len(current_url.split('/')) < min_segments:
            print("⚠️  Task completion validation failed:")
            print(f"   {pattern['error_message']}")
            return False
    
    # Check title patterns if specified
    title_patterns = pattern.get("title_patterns", [])
    if title_patterns and not any(p in title_lower for p in title_patterns):
        if 'filter' in pattern.get("url_patterns", []):  # Special case for filter tasks
            print("⚠️  Task completion validation failed:")
            print(f"   {pattern['error_message']}")
            return False
    
    return True