import re
from typing import Dict, List, Optional


# Month synonyms for date checking
MONTH_SYNONYMS = {
    "january": ["jan", "january"],
    "february": ["feb", "february"],
    "march": ["mar", "march"],
    "april": ["apr", "april"],
    "may": ["may"],
    "june": ["jun", "june"],
    "july": ["jul", "july"],
    "august": ["aug", "august"],
    "september": ["sep", "sept", "september"],
    "october": ["oct", "october"],
    "november": ["nov", "november"],
    "december": ["dec", "december"],
}


def normalize_text(text: str) -> str:
    """Normalize text by trimming and converting to lowercase."""
    return (text or "").strip().lower()


def normalize_for_search(text: str) -> str:
    """Normalize text for search by removing non-alphanumeric characters."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def is_value_in_forms(value: str, forms: List[Dict]) -> bool:
    """Check if a specific value exists in any form field."""
    target = normalize_text(value)
    for field in forms:
        field_value = normalize_text(field.get("value", ""))
        if field_value == target:
            return True
    return False


def control_matches(control: Optional[Dict], value: Optional[str]) -> bool:
    """Check if a control element matches a target value."""
    if not control or not value:
        return False
    control_text = (control.get("text") or control.get("ariaLabel") or "").strip().lower()
    if not control_text:
        return False
    target_norm = normalize_text(value)
    return target_norm in control_text


def is_status_selected(value: str, texts: List[str]) -> bool:
    """Check if a status value is selected/visible in the UI texts."""
    target_norm = normalize_for_search(value)
    if not target_norm:
        return False
    for text in texts:
        if target_norm in normalize_for_search(text):
            return True
    return False


def is_priority_selected(value: str, texts: List[str]) -> bool:
    """Check if a priority value is selected/visible in the UI texts."""
    target_norm = normalize_for_search(value)
    if not target_norm:
        return False
    for text in texts:
        norm_text = normalize_for_search(text)
        if "priority" in norm_text and target_norm in norm_text:
            return True
    return False


def is_description_filled(value: Optional[str], forms: List[Dict]) -> bool:
    """Check if the description field is filled with the target value."""
    DESCRIPTION_ARIA_KEYWORDS = ["description", "details", "summary", "notes"]
    
    target_norm = normalize_text(value)
    for field in forms:
        field_type = (field.get("type") or "").lower()
        aria = (field.get("aria_label") or "").lower()
        if field_type in {"textarea"} or any(keyword in aria for keyword in DESCRIPTION_ARIA_KEYWORDS):
            current_value = normalize_text(field.get("value", ""))
            if target_norm:
                if target_norm in current_value:
                    return True
            elif current_value:
                return True
    return False


def is_date_visible(value: str, texts: List[str]) -> bool:
    """Check if a date value is visible in the UI texts."""
    def _date_token_sets(value: str) -> List[List[str]]:
        raw_tokens = [tok for tok in re.split(r"[\s,/-]+", value.lower()) if tok]
        token_sets: List[List[str]] = []
        for token in raw_tokens:
            if token.isdigit():
                trimmed = token.lstrip("0") or "0"
                token_sets.append([trimmed, token])
            else:
                matched = False
                for variants in MONTH_SYNONYMS.values():
                    if token in variants:
                        token_sets.append(variants)
                        matched = True
                        break
                if not matched:
                    token_sets.append([token])
        return token_sets
    
    token_sets = _date_token_sets(value)
    if not token_sets:
        return False
    for text in texts:
        lower = text.lower()
        if all(any(token_variant in lower for token_variant in options) for options in token_sets):
            return True
    return False


def is_filter_applied(value: str, texts: List[str]) -> bool:
    """Check if a filter is applied based on UI text content."""
    target_norm = normalize_for_search(value)
    targets = {target_norm}
    if target_norm.endswith("s"):
        targets.add(target_norm[:-1])
    keywords = {"filter", "filters", "filtered", "showing", "statusis", "status:", "workflow", "state:", "project"}
    for text in texts:
        norm_text = normalize_for_search(text)
        if any(token in norm_text for token in targets):
            if any(key in norm_text for key in keywords):
                return True
            if f"statusis{target_norm}" in norm_text:
                return True
    return False


def collect_bbox_text(bboxes: List[Dict]) -> List[str]:
    """Collect all text content from bboxes for analysis."""
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


def dropdown_open(ui_state: Dict) -> bool:
    """Check if any dropdowns are currently open."""
    if not ui_state.get("modals"):
        return False
    dropdowns = ui_state.get("dropdowns") or []
    return bool(dropdowns)