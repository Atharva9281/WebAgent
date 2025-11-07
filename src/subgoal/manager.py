from typing import Dict, List, Optional
from .element_finders import (
    find_status_control, find_priority_control, find_submit_control,
    extract_modal_bbox
)
from .goal_checkers import (
    is_value_in_forms, control_matches, is_status_selected, 
    is_priority_selected, is_description_filled, is_date_visible,
    is_filter_applied, collect_bbox_text, normalize_text
)
from .action_guides import (
    guide_status_action, guide_priority_action, guide_description_action,
    guide_project_name_action, guide_submit_action, should_block_optional_click,
    should_block_cancel_close, should_guide_typing, adjust_action
)
from .action_recorder import record_action
from .goal_setup import setup_goals


class SubGoalManager:
    """Track and manage ordered sub-goals extracted from a task configuration."""

    OPTIONAL_CLICK_KEYWORDS = ["icon", "emoji", "avatar", "color", "image"]
    STATUS_TOKENS = [
        "backlog",
        "todo",
        "to do",
        "in progress",
        "in-progress",
        "inprogress",
        "done",
        "completed",
        "complete",
        "canceled",
        "cancelled",
        "blocked",
    ]
    PRIORITY_TOKENS = [
        "no priority",
        "none",
        "urgent",
        "high",
        "medium",
        "low",
        "critical",
    ]
    DESCRIPTION_ARIA_KEYWORDS = ["description", "details", "summary", "notes"]

    def __init__(self, task_config: Dict):
        self.task_config = task_config
        self.goals: List[Dict] = []
        self.pending_goal: Optional[Dict] = None
        self._loading_finish_blocks = 0
        self._modal_bbox: Optional[Dict] = None
        self.goals = setup_goals(task_config)
        print(f"[SubGoalManager] Initialized goals: {self.goals}")

    def update(self, ui_state: Dict, bboxes: List[Dict]):
        """Update completion status for each sub-goal based on the current UI."""
        if not self.goals:
            self.pending_goal = None
            return

        forms = ui_state.get("forms", []) or []
        texts = collect_bbox_text(bboxes)

        url = ui_state.get("url") or ""
        self._modal_bbox = extract_modal_bbox(ui_state)

        status_control = find_status_control(bboxes)
        priority_control = find_priority_control(bboxes)

        for index, goal in enumerate(self.goals):
            if goal["completed"]:
                continue

            key = goal["key"]
            value = goal.get("value")

            if key == "open_projects":
                goal["completed"] = "/project" in url
            elif key == "project_name" or key == "issue_name":
                goal["completed"] = is_value_in_forms(value, forms)
            elif key == "status":
                goal["completed"] = control_matches(status_control, value)
            elif key == "priority":
                goal["completed"] = control_matches(priority_control, value)
            elif key == "target_date":
                goal["completed"] = is_date_visible(value, texts)
            elif key == "filter":
                goal["completed"] = is_filter_applied(value, texts)
            elif key == "description":
                goal["completed"] = is_description_filled(value, forms)
            elif key == "submit":
                prior_complete = all(g["completed"] for g in self.goals[:index])
                if prior_complete and ui_state.get("modals"):
                    goal["completed"] = False
                elif prior_complete and not ui_state.get("modals"):
                    goal["completed"] = True

        self.pending_goal = self._get_pending_goal()

    def all_completed(self) -> bool:
        return not self.goals or all(goal["completed"] for goal in self.goals)

    def build_hint(self, submit_hint: Optional[Dict], ui_state: Dict) -> Optional[Dict]:
        """Build a combined guidance hint for Gemini."""
        messages: List[str] = []
        if self.pending_goal:
            pending_message = self._build_goal_hint(self.pending_goal)
            if pending_message:
                messages.append(pending_message)

        if submit_hint:
            messages.append(submit_hint["message"])

        if (
            not self.pending_goal
            and self.all_completed()
            and not ui_state.get("modals")
            and not submit_hint
        ):
            messages.append("All required steps satisfied. Finish the task now.")

        if not messages:
            return None

        hint = {
            "type": "guidance",
            "message": " | ".join(messages),
        }
        if submit_hint and submit_hint.get("element_id") is not None:
            hint["element_id"] = submit_hint["element_id"]
        return hint

    def block_finish_reason(self, action: Dict, ui_state: Dict) -> Optional[str]:
        """Return a reason string if finish should be blocked, otherwise None."""
        if action.get("action") != "finish":
            self._loading_finish_blocks = 0
            return None
        if ui_state.get("modals"):
            self._loading_finish_blocks = 0
            return f"Modal still open ({len(ui_state['modals'])})"
        if self.pending_goal:
            self._loading_finish_blocks = 0
            return f"Pending sub-goal: {self.pending_goal['key']}"
        if ui_state.get("loading", {}).get("is_loading"):
            if not self.all_completed():
                if self._loading_finish_blocks == 0:
                    self._loading_finish_blocks = 1
                    return "Page still loading"
            else:
                self._loading_finish_blocks = 0
        else:
            self._loading_finish_blocks = 0
        return None

    def adjust_action(self, action: Dict, ui_state: Dict, bboxes: List[Dict]) -> Dict:
        """Adjust Gemini's action to avoid loops and optional distractions."""
        return adjust_action(action, ui_state, bboxes, self.pending_goal, self.goals, self._modal_bbox, self.task_config)

    def record_action(self, action: Dict):
        """Infers goal completion from the most recent action (post-execution)."""
        self.pending_goal = record_action(action, self.goals)


    def _get_pending_goal(self) -> Optional[Dict]:
        from .goal_setup import get_pending_goal
        return get_pending_goal(self.goals)

    def _build_goal_hint(self, goal: Dict) -> str:
        from .goal_setup import build_goal_hint
        return build_goal_hint(goal)

    def _goal_completed(self, key: str) -> bool:
        from .goal_setup import goal_completed
        return goal_completed(self.goals, key)