"""
Utility functions for sub-goal management.
"""

import re
from typing import Dict, List, Optional


def normalize_text(text: str) -> str:
    """Normalize text to lowercase and strip whitespace."""
    return (text or "").strip().lower()


def normalize_for_search(text: str) -> str:
    """Normalize text for search by removing non-alphanumeric characters."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def collect_bbox_text(bboxes: List[Dict]) -> List[str]:
    """Collect text and aria labels from bounding boxes."""
    collected = []
    for bbox in bboxes:
        parts = []
        if bbox.get("text"):
            parts.append(bbox["text"])
        if bbox.get("ariaLabel"):
            parts.append(bbox["ariaLabel"])
        if parts:
            collected.append(" ".join(parts))
    return collected


def action_targets(action: Dict, element_index: int) -> bool:
    """Check if action targets a specific element index."""
    if action.get("action") in ["click", "type"]:
        target_id = action.get("element_id")
        if target_id is not None:
            return int(target_id) == int(element_index)
    return False


def dropdown_open(ui_state: Dict) -> bool:
    """Check if dropdown is currently open."""
    if not ui_state.get("modals"):
        return False
    dropdowns = ui_state.get("dropdowns") or []
    return bool(dropdowns)
