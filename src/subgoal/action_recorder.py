from typing import Dict, List, Optional
from .goal_checkers import normalize_text


def record_action(action: Dict, goals: List[Dict]) -> Optional[Dict]:
    """Infers goal completion from the most recent action (post-execution)."""
    if not action:
        return None
    action_type = action.get("action")

    if action_type == "click":
        element_text = (action.get("element_text") or "").lower()
        if not element_text:
            return None
        for goal in goals:
            if goal["completed"]:
                continue
            if goal["key"] == "filter" and goal.get("value"):
                target = goal["value"].lower().rstrip("s")
                if target and target in element_text:
                    if any(keyword in element_text for keyword in ["filter", "status", "workflow", "showing", "chip", "project"]):
                        goal["completed"] = True
            if goal["key"] == "open_projects" and "project" in element_text:
                goal["completed"] = True
            if goal["key"] == "status":
                target = normalize_text(goal.get("value"))
                if target and target in element_text and "order" not in element_text:
                    goal["completed"] = True
            if goal["key"] == "priority":
                target = normalize_text(goal.get("value"))
                if target and target in element_text and "order" not in element_text:
                    goal["completed"] = True
            if goal["key"] == "submit":
                if any(
                    keyword in element_text
                    for keyword in ["create project", "create", "submit", "finish", "done"]
                ):
                    goal["completed"] = True

    elif action_type == "type":
        typed = (action.get("text") or "")
        typed_norm = normalize_text(typed)
        if not typed_norm:
            return None
        for goal in goals:
            if goal["completed"]:
                continue
            if goal["key"] == "project_name" or goal["key"] == "issue_name":
                target = (goal.get("value") or "").strip().lower()
                if target and target == typed_norm:
                    goal["completed"] = True
            if goal["key"] == "priority":
                target = normalize_text(goal.get("value"))
                if target and target in typed_norm:
                    goal["completed"] = True
            if goal["key"] == "description":
                target = normalize_text(goal.get("value"))
                if target:
                    if target in typed_norm:
                        goal["completed"] = True
                elif typed_norm:
                    goal["completed"] = True

    # Return pending goal (find first non-completed goal)
    for goal in goals:
        if not goal["completed"]:
            return goal
    return None