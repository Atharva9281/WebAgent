from typing import Dict, List, Optional
from .element_finders import (
    find_status_control, find_priority_control, find_description_bbox, 
    find_project_name_bbox, find_submit_control, find_option_element, 
    find_search_field, action_targets, extract_modal_bbox
)
from .goal_checkers import normalize_text, dropdown_open, collect_bbox_text


def guide_status_action(action: Dict, ui_state: Dict, bboxes: List[Dict], value: str, goals: List[Dict]) -> Optional[Dict]:
    """Guide action for setting status/backlog value."""
    target_norm = normalize_text(value)
    if dropdown_open(ui_state):
        option = find_option_element(bboxes, target_norm)
        if option:
            if not action_targets(action, option["index"]):
                return {
                    "action": "click",
                    "element_id": option["index"],
                    "reasoning": f"Select the backlog option '{value}' in the dropdown.",
                }
            return None

        search = find_search_field(bboxes, placeholder_keywords=["status"])
        if search and not action_targets(action, search["index"]):
            pass
            return {
                "action": "type",
                "element_id": search["index"],
                "text": value,
                "reasoning": f"Search for the backlog option '{value}' before selecting it.",
            }

    control = find_status_control(bboxes)
    if control:
        # If already targeting this element, let it proceed
        if action_targets(action, control["index"]):
            return None
        
        return {
            "action": "click",
            "element_id": control["index"],
            "reasoning": f"Open the backlog chip to change it to '{value}'.",
        }

    pass
    return {
        "action": "wait",
        "reasoning": f"Waiting for backlog chip or options matching '{value}' to appear.",
    }


def guide_priority_action(action: Dict, ui_state: Dict, bboxes: List[Dict], value: str, goals: List[Dict]) -> Optional[Dict]:
    """Guide action for setting priority value."""
    target_norm = normalize_text(value)
    if dropdown_open(ui_state):
        option = find_option_element(bboxes, target_norm)
        if option and not action_targets(action, option["index"]):
            return {
                "action": "click",
                "element_id": option["index"],
                "reasoning": f"Select the priority '{value}' in the dropdown.",
            }
        if option:
            return None
        search = find_search_field(bboxes, placeholder_keywords=["priority"])
        if search and not action_targets(action, search["index"]):
            pass
            return {
                "action": "type",
                "element_id": search["index"],
                "text": value,
                "reasoning": f"Search for the priority '{value}' before selecting it.",
            }

    control = find_priority_control(bboxes)
    if control:
        # If already targeting this element, let it proceed
        if action_targets(action, control["index"]):
            return None
        
        return {
            "action": "click",
            "element_id": control["index"],
            "reasoning": f"Open the priority chip to change it to '{value}'.",
        }

    pass
    return {
        "action": "wait",
        "reasoning": f"Waiting for priority chip or options matching '{value}' to appear.",
    }


def guide_description_action(action: Dict, bboxes: List[Dict], value: str, modal_bbox: Optional[Dict], goals: List[Dict], task_config: Dict) -> Optional[Dict]:
    """Guide action for filling description field."""
    def _auto_description_text() -> str:
        parameters = task_config.get("parameters", {}) or {}
        project_name = parameters.get("project_name") or parameters.get("name") or "this project"
        return f"Automated description for {project_name} created by Agent B."
    
    field = find_description_bbox(bboxes, modal_bbox=modal_bbox)
    if not field:
        return None
    
    if action.get("action") == "type" and action_targets(action, field["index"]):
        typed_text = (action.get("text") or "").strip().lower()
        project_name = next((g["value"] for g in goals if g["key"] in ["project_name", "issue_name"]), "")
        if typed_text == project_name.lower():
            return {
                "action": "type",
                "element_id": field["index"],
                "text": value.strip() or _auto_description_text(),
                "reasoning": "Fill in the project description field with the requested text.",
            }
        return None

    text_to_use = action.get("text") or value.strip()
    if not text_to_use:
        text_to_use = _auto_description_text()

    return {
        "action": "type",
        "element_id": field["index"],
        "text": text_to_use,
        "reasoning": "Fill in the project description field with the requested text.",
    }


def guide_project_name_action(action: Dict, bboxes: List[Dict], value: str, modal_bbox: Optional[Dict], goals: List[Dict]) -> Optional[Dict]:
    """Guide action for filling project name field."""
    field = find_project_name_bbox(bboxes, modal_bbox=modal_bbox)
    if not field:
        return None
    if action.get("action") == "type" and action_targets(action, field["index"]):
        return None

    desired_text = value.strip() or action.get("text") or "New project"
    pass
    return {
        "action": "type",
        "element_id": field["index"],
        "text": desired_text,
        "reasoning": f"Type the project name '{desired_text}'.",
    }


def guide_submit_action(action: Dict, bboxes: List[Dict], modal_bbox: Optional[Dict], goals: List[Dict]) -> Optional[Dict]:
    """Guide action for submitting the form."""
    button = find_submit_control(bboxes, modal_bbox=modal_bbox)
    if button:
        # If already targeting submit button, let it proceed
        if action_targets(action, button["index"]):
            return None
        
        return {
            "action": "click",
            "element_id": button["index"],
            "reasoning": "All required fields complete. Submit to finish.",
        }
    return None


def should_block_optional_click(action: Dict, element_text: str, pending_goal: Optional[Dict]) -> bool:
    """Check if an optional click should be blocked."""
    OPTIONAL_CLICK_KEYWORDS = ["icon", "emoji", "avatar", "color", "image"]
    
    if action["action"] == "click" and element_text:
        if any(keyword in element_text for keyword in OPTIONAL_CLICK_KEYWORDS):
            if not pending_goal or pending_goal["key"] not in ["target_date", "priority"]:
                return True
    return False


def should_block_cancel_close(action: Dict, element_text: str, ui_state: Dict) -> bool:
    """Check if cancel/close actions should be blocked while modal is open."""
    if (
        action["action"] == "click"
        and element_text
        and any(keyword in element_text for keyword in ["cancel", "close", "discard"])
        and ui_state.get("modals")
    ):
        return True
    return False


def should_guide_typing(action: Dict, pending_goal: Optional[Dict]) -> bool:
    """Check if typing action should be guided based on pending goal."""
    if action["action"] == "type" and pending_goal:
        if pending_goal["key"] in ["project_name", "issue_name", "filter", "description"]:
            return False  # Allow typing for these fields
        else:
            return True  # Block typing for other pending goals
    return False


def adjust_action(action: Dict, ui_state: Dict, bboxes: List[Dict], pending_goal: Optional[Dict], goals: List[Dict], modal_bbox: Optional[Dict], task_config: Optional[Dict] = None) -> Dict:
    """Adjust Gemini's action to avoid loops and optional distractions."""
    if not action:
        return action

    def _all_completed() -> bool:
        return not goals or all(goal["completed"] for goal in goals)

    if (
        action["action"] not in ("finish", "wait")
        and not pending_goal
        and _all_completed()
        and not ui_state.get("modals")
    ):
        return {"action": "finish", "reasoning": "All required steps completed"}

    if action["action"] == "wait":
        return action

    element = None
    element_text = ""
    element_id = action.get("element_id")
    if element_id is not None and element_id < len(bboxes):
        element = bboxes[element_id]
        if element:
            text = element.get("text") or ""
            aria = element.get("ariaLabel") or ""
            element_text = f"{text} {aria}".strip().lower()

    # Handle specific pending goals
    if pending_goal and pending_goal["key"] == "open_projects":
        project_candidate = None
        for bbox in bboxes:
            text_parts = []
            if bbox.get("text"):
                text_parts.append(bbox["text"])
            if bbox.get("ariaLabel"):
                text_parts.append(bbox["ariaLabel"])
            combined = " ".join(text_parts).lower()
            if "project" in combined:
                project_candidate = bbox
                break
        if project_candidate:
            target_index = project_candidate["index"]
            if action["action"] != "click" or action.get("element_id") != target_index:
                pass
                return {
                    "action": "click",
                    "element_id": target_index,
                    "reasoning": "Open the Projects view before applying filters",
                }
        elif action["action"] != "click":
            pass
            return {"action": "wait", "reasoning": "Waiting for Projects navigation element"}

    # Handle filter goal with modal open
    if (
        pending_goal
        and pending_goal["key"] == "filter"
        and ui_state.get("modals")
    ):
        target_value = (pending_goal.get("value") or "").strip().lower()
        candidate_bbox = None
        for bbox in bboxes:
            combined_parts = []
            if bbox.get("text"):
                combined_parts.append(bbox["text"])
            if bbox.get("ariaLabel"):
                combined_parts.append(bbox["ariaLabel"])
            combined = " ".join(combined_parts).strip().lower()
            if not combined:
                continue
            if target_value and target_value in combined:
                candidate_bbox = bbox
                break

        if candidate_bbox:
            candidate_index = candidate_bbox["index"]
            if action["action"] != "click" or action.get("element_id") != candidate_index:
                return {
                    "action": "click",
                    "element_id": candidate_index,
                    "reasoning": f"Select the filter option matching '{target_value}'",
                }
        else:
            if action["action"] == "click" and element_text:
                relevant_tokens = ["status", "workflow", "filter", "add", "condition", target_value]
                if any(token for token in relevant_tokens if token and token in element_text):
                    return action
            if action["action"] == "type":
                return action
            if action["action"] != "wait":
                pass
            return {"action": "wait", "reasoning": "Waiting for filter options to appear"}

    # Block cancel/close actions while modal is open
    if should_block_cancel_close(action, element_text, ui_state):
        pass
        return {"action": "wait", "reasoning": "Blocked cancel/close while modal is open"}

    # Guide typing actions based on pending goal
    if should_guide_typing(action, pending_goal):
        return {"action": "wait", "reasoning": "Focus on pending sub-goal instead of typing"}

    # Guide specific pending goal actions
    if pending_goal:
        goal_key = pending_goal.get("key")
        goal_value = pending_goal.get("value") or ""
        if goal_key == "project_name" or goal_key == "issue_name":
            guided = guide_project_name_action(action, bboxes, goal_value, modal_bbox, goals)
            if guided:
                return guided
        elif goal_key == "status":
            guided = guide_status_action(action, ui_state, bboxes, goal_value, goals)
            if guided:
                return guided
        elif goal_key == "priority":
            guided = guide_priority_action(action, ui_state, bboxes, goal_value, goals)
            if guided:
                return guided
        elif goal_key == "description":
            guided = guide_description_action(action, bboxes, goal_value, modal_bbox, goals, task_config or {})
            if guided:
                return guided
        elif goal_key == "submit":
            guided = guide_submit_action(action, bboxes, modal_bbox, goals)
            if guided:
                return guided

    # Block optional decoration clicks
    if should_block_optional_click(action, element_text, pending_goal):
        pass
        return {"action": "wait", "reasoning": "Ignoring optional decoration controls"}

    # Auto-submit if all goals complete
    if (
        not pending_goal
        and _all_completed()
        and action["action"] != "finish"
    ):
        control = find_submit_control(bboxes)
        if control:
            return {
                "action": "click",
                "element_id": control["index"],
                "reasoning": "All fields complete. Submit the form to finish.",
            }
        return {"action": "finish", "reasoning": "All required steps complete"}

    return action