from typing import Dict, List, Optional


def setup_goals(task_config: Dict) -> List[Dict]:
    """Extract and setup ordered sub-goals from a task configuration."""
    goals = []
    params = task_config.get("parameters", {}) or {}
    goal_text = (task_config.get("goal") or "").lower()
    object_text = (task_config.get("object") or "").lower()

    is_project = "project" in goal_text or "project" in object_text
    is_issue = "issue" in goal_text or "issue" in object_text
    
    # Check if this is a creation/modification task (not just querying/filtering)
    is_create_modify = any(word in goal_text for word in ["create", "add", "update", "change", "set", "modify"])
    
    if is_project and is_create_modify:
        goals.append({"key": "open_projects", "value": None, "completed": False})
    elif is_project and not is_create_modify:
        # Querying/filtering projects - still need to navigate to projects
        goals.append({"key": "open_projects", "value": None, "completed": False})

    name_value = (
        params.get("project_name") 
        or params.get("issue_name")
        or params.get("issue_title")
        or params.get("name") 
        or params.get("title")
    )
    status_value = (
        params.get("status")
        or params.get("backlog_status")
        or params.get("backlog_progress")
        or params.get("progress")
        or params.get("workflow_state")
    )
    priority_value = params.get("priority") or params.get("importance") or params.get("urgency")
    target_value = params.get("target_date") or params.get("due_date") or params.get("deadline")
    filter_value = params.get("filter") or params.get("filter_status") or params.get("status")
    description_value = (
        params.get("description")
        or params.get("project_description")
        or params.get("issue_description")
        or params.get("notes")
    )
    
    # Auto-generate description if query mentions "generate description" or "add description"
    if not description_value and (is_project or is_issue):
        if any(phrase in goal_text for phrase in ["generate description", "add description", "create description", "with description"]):
            obj_name = name_value or ("project" if is_project else "issue")
            description_value = f"Automated description for {obj_name}."

    # For filter queries, use status as filter value (not for create/modify)
    if not is_create_modify and not filter_value and status_value:
        filter_value = status_value
    
    if not filter_value and not is_create_modify:
        # Fallback: infer filter target from goal text (only if NOT creating/modifying)
        STATUS_KEYWORDS = [
            "backlog",
            "in progress",
            "in-progress",
            "todo",
            "to do",
            "completed",
            "done",
            "cancelled",
            "canceled",
            "blocked",
        ]
        for keyword in STATUS_KEYWORDS:
            if keyword in goal_text:
                filter_value = keyword
                break

    if isinstance(name_value, str) and name_value.strip():
        # Use appropriate key based on object type
        name_key = "issue_name" if is_issue else "project_name"
        goals.append({"key": name_key, "value": name_value.strip(), "completed": False})
    if isinstance(status_value, str) and status_value.strip() and is_create_modify:
        # Only create status goal for create/modify tasks, not filter tasks
        goals.append({"key": "status", "value": status_value.strip(), "completed": False})
    if isinstance(priority_value, str) and priority_value.strip():
        goals.append({"key": "priority", "value": priority_value.strip(), "completed": False})
    if isinstance(target_value, str) and target_value.strip():
        goals.append({"key": "target_date", "value": target_value.strip(), "completed": False})
    if isinstance(filter_value, str) and filter_value.strip():
        goals.append({"key": "filter", "value": filter_value.strip(), "completed": False})
    if isinstance(description_value, str) and description_value.strip():
        goals.append({"key": "description", "value": description_value.strip(), "completed": False})

    if goals:
        goals.append({"key": "submit", "value": None, "completed": False})

    return goals


def get_pending_goal(goals: List[Dict]) -> Optional[Dict]:
    """Find the first incomplete goal."""
    for goal in goals:
        if not goal["completed"]:
            return goal
    return None


def build_goal_hint(goal: Dict) -> str:
    """Build a hint message for a specific goal."""
    key = goal["key"]
    value = goal.get("value")
    if key == "open_projects":
        return "Navigate to the Projects view from the sidebar."
    if key == "project_name":
        return f"Next required step: type the project name '{value}'."
    if key == "status":
        return f"Next required step: set the status/backlog to '{value}'."
    if key == "priority":
        return f"Next required step: set the priority to '{value}'."
    if key == "target_date":
        return f"Next required step: set the target/due date to '{value}'."
    if key == "filter":
        return f"Next required step: open the filter panel and apply '{value}'."
    if key == "description":
        if value:
            return f"Next required step: type the project description '{value}'."
        return "Next required step: add a project description."
    if key == "submit":
        return "All required fields are satisfied. Click the primary submit/create button to finish."
    return ""


def goal_completed(goals: List[Dict], key: str) -> bool:
    """Check if a specific goal key is completed."""
    for goal in goals:
        if goal["key"] == key:
            return goal["completed"]
    return False