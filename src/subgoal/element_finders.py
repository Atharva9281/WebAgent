import re
from typing import Dict, List, Optional, Iterable


def find_modal_button(
    bboxes: List[Dict],
    *,
    aria_keywords: Optional[List[str]] = None,
    text_tokens: Optional[Iterable[str]] = None,
    modal_bbox: Optional[Dict] = None,
) -> Optional[Dict]:
    """Find a modal button based on aria keywords or text tokens."""
    def _normalize_text(text: str) -> str:
        return (text or "").strip().lower()

    def _within_modal(bbox: Dict, modal_bbox: Dict) -> bool:
        if not modal_bbox:
            return False
        x = bbox.get("x")
        y = bbox.get("y")
        if x is None or y is None:
            return False
        left = modal_bbox.get("x", 0)
        top = modal_bbox.get("y", 0)
        right = left + modal_bbox.get("width", 0)
        bottom = top + modal_bbox.get("height", 0)
        return left <= x <= right and top <= y <= bottom

    aria_keywords = [kw.lower() for kw in (aria_keywords or [])]
    normalized_tokens = [_normalize_text(token) for token in (text_tokens or []) if token]

    for bbox in bboxes:
        if bbox.get("type") != "button":
            continue
        aria = (bbox.get("ariaLabel") or "").lower()
        text = (bbox.get("text") or "").strip().lower()
        if modal_bbox and not _within_modal(bbox, modal_bbox):
            continue
        if aria_keywords and any(keyword in aria for keyword in aria_keywords):
            return bbox
        if normalized_tokens and any(token in text for token in normalized_tokens):
            return bbox
    return None


def find_option_element(bboxes: List[Dict], target_norm: str) -> Optional[Dict]:
    """Find an option element in a dropdown that matches the target text."""
    def _normalize_text(text: str) -> str:
        return (text or "").strip().lower()

    if not target_norm:
        return None
    for bbox in bboxes:
        text = (bbox.get("text") or "").strip()
        if not text:
            continue
        normalized = _normalize_text(text)
        if normalized == target_norm or target_norm in normalized:
            return bbox
    return None


def find_description_bbox(bboxes: List[Dict], modal_bbox: Optional[Dict] = None) -> Optional[Dict]:
    """Find the description text area or input field."""
    DESCRIPTION_ARIA_KEYWORDS = ["description", "details", "summary", "notes"]
    
    def _within_modal(bbox: Dict, modal_bbox: Dict) -> bool:
        if not modal_bbox:
            return False
        x = bbox.get("x")
        y = bbox.get("y")
        if x is None or y is None:
            return False
        left = modal_bbox.get("x", 0)
        top = modal_bbox.get("y", 0)
        right = left + modal_bbox.get("width", 0)
        bottom = top + modal_bbox.get("height", 0)
        return left <= x <= right and top <= y <= bottom

    aria_keywords = [kw.lower() for kw in DESCRIPTION_ARIA_KEYWORDS]
    for bbox in bboxes:
        element_type = (bbox.get("type") or "").lower()
        role = (bbox.get("role") or "").lower()
        aria = (bbox.get("ariaLabel") or "").lower()
        if modal_bbox and not _within_modal(bbox, modal_bbox):
            continue
        if element_type == "textarea":
            return bbox
        if role == "textbox" and any(keyword in aria for keyword in aria_keywords):
            return bbox
        if any(keyword in aria for keyword in aria_keywords):
            return bbox
    return None


def find_project_name_bbox(bboxes: List[Dict], modal_bbox: Optional[Dict] = None) -> Optional[Dict]:
    """Find the project name input field."""
    def _within_modal(bbox: Dict, modal_bbox: Dict) -> bool:
        if not modal_bbox:
            return False
        x = bbox.get("x")
        y = bbox.get("y")
        if x is None or y is None:
            return False
        left = modal_bbox.get("x", 0)
        top = modal_bbox.get("y", 0)
        right = left + modal_bbox.get("width", 0)
        bottom = top + modal_bbox.get("height", 0)
        return left <= x <= right and top <= y <= bottom

    aria_keywords = ["project name", "name field", "title"]
    for bbox in bboxes:
        element_type = (bbox.get("type") or "").lower()
        role = (bbox.get("role") or "").lower()
        aria = (bbox.get("ariaLabel") or "").lower()
        text = (bbox.get("text") or "").strip().lower()
        if modal_bbox and not _within_modal(bbox, modal_bbox):
            continue
        if role == "textbox" or element_type in {"div", "input"}:
            if any(keyword in aria for keyword in aria_keywords):
                return bbox
            if text in {"untitled", "new project"}:
                return bbox
    return None


def find_status_control(bboxes: List[Dict]) -> Optional[Dict]:
    """Find the status control element (button or chip)."""
    candidates = []
    
    for bbox in bboxes:
        aria = (bbox.get("ariaLabel") or "").lower()
        text = (bbox.get("text") or "").strip().lower()
        
        if "order by" in aria or "sort" in aria:
            continue
        
        # Check aria-label first (most reliable)
        if "change project status" in aria or "change status" in aria:
            return bbox
        if "status" in aria and "order by" not in aria:
            candidates.append((bbox, 3))
        
        # Check text (works for any element type)
        if len(text) < 100 and text:
            if text in {"backlog", "todo", "planned", "in progress", "done", "canceled"}:
                candidates.append((bbox, 4))
            if text in {"backlog", "todo", "planned", "in progress"}:
                candidates.append((bbox, 2))
            if "status" in text and len(text) < 30:
                candidates.append((bbox, 1))
    
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    return None


def find_priority_control(bboxes: List[Dict]) -> Optional[Dict]:
    """Find the priority control element (button or chip)."""
    candidates = []
    for bbox in bboxes:
        aria = (bbox.get("ariaLabel") or "").lower()
        text = (bbox.get("text") or "").strip().lower()
        
        if "order by" in aria or "sort" in aria:
            continue
        
        # Check aria-label first
        if "change project priority" in aria or "change priority" in aria:
            return bbox
        if "priority" in aria and "order by" not in aria:
            candidates.append((bbox, 3))
        
        # Check text (works for any element type)
        if len(text) < 100 and text:
            if any(keyword in text for keyword in {"no priority", "urgent", "high", "medium", "low"}):
                candidates.append((bbox, 4))
            if text in {"no priority", "urgent", "high", "medium", "low"}:
                candidates.append((bbox, 2))
            if "priority" in text and len(text) < 30:
                candidates.append((bbox, 1))
    
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    return None


def find_submit_control(bboxes: List[Dict], modal_bbox: Optional[Dict] = None) -> Optional[Dict]:
    """Find the submit/create button."""
    submit_keywords = [
        "create project",
        "create new project",
        "create",
        "submit",
        "finish",
        "done",
        "save project",
        "confirm",
    ]
    for bbox in bboxes:
        element_type = (bbox.get("type") or "").lower()
        role = (bbox.get("role") or "").lower()
        if element_type not in {"button"} and role != "button":
            continue
        text = (bbox.get("text") or "").strip().lower()
        aria = (bbox.get("ariaLabel") or "").strip().lower()
        combined = f"{text} {aria}".strip()
        if any(keyword in combined for keyword in submit_keywords):
            if "create new issue" in combined or "new view" in combined:
                continue
            return bbox
    return None


def find_search_field(bboxes: List[Dict], placeholder_keywords: Iterable[str]) -> Optional[Dict]:
    """Find a dropdown search field based on placeholder keywords."""
    keywords = [kw.lower() for kw in placeholder_keywords]
    for bbox in bboxes:
        element_type = (bbox.get("type") or "").lower()
        role = (bbox.get("role") or "").lower()
        aria = (bbox.get("ariaLabel") or "").lower()
        placeholder = (bbox.get("placeholder") or "").lower()

        if element_type in {"input", "textbox"} or role == "textbox":
            if any(keyword in aria for keyword in keywords) or any(
                keyword in placeholder for keyword in keywords
            ):
                return bbox
    return None


def extract_modal_bbox(ui_state: Dict) -> Optional[Dict]:
    """Extract the bbox of the first valid modal from UI state."""
    modals = ui_state.get("modals") or []
    for modal in modals:
        bbox = modal.get("bbox")
        if bbox and bbox.get("width", 0) >= 50 and bbox.get("height", 0) >= 50:
            return bbox
    return None


def within_modal(bbox: Dict, modal_bbox: Dict) -> bool:
    """Check if a bbox is within the modal boundaries."""
    if not modal_bbox:
        return False
    x = bbox.get("x")
    y = bbox.get("y")
    if x is None or y is None:
        return False
    left = modal_bbox.get("x", 0)
    top = modal_bbox.get("y", 0)
    right = left + modal_bbox.get("width", 0)
    bottom = top + modal_bbox.get("height", 0)
    return left <= x <= right and top <= y <= bottom


def action_targets(action: Dict, element_index: int) -> bool:
    """Check if an action targets a specific element index."""
    if not action:
        return False
    return (
        action.get("action") in {"click", "type"}
        and action.get("element_id") == element_index
    )