import re
from typing import Dict, List, Optional


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


class SubGoalManager:
    """Track and manage ordered sub-goals extracted from a task configuration."""

    OPTIONAL_CLICK_KEYWORDS = ["icon", "emoji", "avatar", "color", "image"]

    def __init__(self, task_config: Dict):
        self.task_config = task_config
        self.goals: List[Dict] = []
        self.pending_goal: Optional[Dict] = None
        self._loading_finish_blocks = 0
        self._setup_goals(task_config)
        print(f"[SubGoalManager] Initialized goals: {self.goals}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, ui_state: Dict, bboxes: List[Dict]):
        """Update completion status for each sub-goal based on the current UI."""
        if not self.goals:
            self.pending_goal = None
            return

        forms = ui_state.get("forms", []) or []
        texts = self._collect_bbox_text(bboxes)

        url = ui_state.get("url") or ""

        for index, goal in enumerate(self.goals):
            if goal["completed"]:
                continue

            key = goal["key"]
            value = goal.get("value")

            if key == "open_projects":
                goal["completed"] = "/project" in url  # covers /projects and /project/...
            elif key == "project_name":
                goal["completed"] = self._is_value_in_forms(value, forms)
            elif key == "status":
                goal["completed"] = self._is_status_selected(value, texts)
            elif key == "priority":
                goal["completed"] = self._is_priority_selected(value, texts)
            elif key == "target_date":
                goal["completed"] = self._is_date_visible(value, texts)
            elif key == "filter":
                goal["completed"] = self._is_filter_applied(value, texts)
            elif key == "submit":
                prior_complete = all(g["completed"] for g in self.goals[:index])
                if prior_complete and not ui_state.get("modals"):
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
            if self._loading_finish_blocks == 0:
                self._loading_finish_blocks = 1
                return "Page still loading"
        else:
            self._loading_finish_blocks = 0
        return None

    def adjust_action(self, action: Dict, ui_state: Dict, bboxes: List[Dict]) -> Dict:
        """Adjust Gemini's action to avoid loops and optional distractions."""
        if not action:
            return action

        if (
            action["action"] not in ("finish", "wait")
            and not self.pending_goal
            and self.all_completed()
            and not ui_state.get("modals")
        ):
            print("✅ All sub-goals complete and modal closed. Switching to finish.")
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

        if self.pending_goal and self.pending_goal["key"] == "open_projects":
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
                    print("⚠️  Need to open Projects view. Redirecting click to Projects navigation.")
                    return {
                        "action": "click",
                        "element_id": target_index,
                        "reasoning": "Open the Projects view before applying filters",
                    }
            elif action["action"] != "click":
                print("⚠️  Waiting for Projects navigation to appear.")
                return {"action": "wait", "reasoning": "Waiting for Projects navigation element"}

        if (
            self.pending_goal
            and self.pending_goal["key"] == "filter"
            and ui_state.get("modals")
        ):
            target_value = (self.pending_goal.get("value") or "").strip().lower()
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
                    print(
                        f"⚠️  Pending filter '{target_value}'. Redirecting click to element [{candidate_index}] '{candidate_bbox.get('text', '').strip()}'"
                    )
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
                    print("⚠️  Filter option not visible yet. Waiting briefly.")
                return {"action": "wait", "reasoning": "Waiting for filter options to appear"}

        if (
            action["action"] == "click"
            and element_text
            and any(keyword in element_text for keyword in ["cancel", "close", "discard"])
            and ui_state.get("modals")
        ):
            print("⚠️  Blocked click on cancel/close while modal open. Converting to wait.")
            return {"action": "wait", "reasoning": "Blocked cancel/close while modal is open"}

        if action["action"] == "type" and self._goal_completed("project_name"):
            print("⚠️  Project name already set. Suppressing extra typing.")
            return {"action": "wait", "reasoning": "Project name already satisfied"}

        if action["action"] == "type" and self.pending_goal:
            if self.pending_goal["key"] == "project_name":
                pass
            elif self.pending_goal["key"] == "filter":
                return action
            else:
                print("⚠️  Typing skipped - different sub-goal pending.")
                return {"action": "wait", "reasoning": "Focus on pending sub-goal instead of typing"}

        if (
            action["action"] == "click"
            and self._goal_completed("status")
            and element_text
            and any(token in element_text for token in ["status", "backlog", "progress", "todo"])
            and (not self.pending_goal or self.pending_goal["key"] != "status")
        ):
            print("⚠️  Status already satisfied. Skipping redundant click.")
            return {"action": "wait", "reasoning": "Status already satisfied"}

        if (
            action["action"] == "click"
            and self._goal_completed("priority")
            and element_text
            and "priority" in element_text
            and (not self.pending_goal or self.pending_goal["key"] != "priority")
        ):
            print("⚠️  Priority already satisfied. Skipping redundant click.")
            return {"action": "wait", "reasoning": "Priority already satisfied"}

        if action["action"] == "click" and element_text:
            if any(keyword in element_text for keyword in self.OPTIONAL_CLICK_KEYWORDS):
                if not self.pending_goal or self.pending_goal["key"] not in ["target_date", "priority"]:
                    print("⚠️  Skipping optional decoration control.")
                    return {"action": "wait", "reasoning": "Ignoring optional decoration controls"}

        if not self.pending_goal and self.all_completed() and action["action"] != "finish":
            return {"action": "finish", "reasoning": "All required steps complete"}

        return action

    def record_action(self, action: Dict):
        """Infers goal completion from the most recent action (post-execution)."""
        if not action:
            return
        action_type = action.get("action")

        if action_type == "click":
            element_text = (action.get("element_text") or "").lower()
            if not element_text:
                return
            for goal in self.goals:
                if goal["completed"]:
                    continue
                if goal["key"] == "filter" and goal.get("value"):
                    target = goal["value"].lower().rstrip("s")
                    if target and target in element_text:
                        if any(keyword in element_text for keyword in ["filter", "status", "workflow", "showing", "chip"]):
                            goal["completed"] = True
                if goal["key"] == "open_projects" and "project" in element_text:
                    goal["completed"] = True

        elif action_type == "type":
            typed = (action.get("text") or "").strip().lower()
            if not typed:
                return
            for goal in self.goals:
                if goal["completed"]:
                    continue
                if goal["key"] == "project_name":
                    target = (goal.get("value") or "").strip().lower()
                    if target and target == typed:
                        goal["completed"] = True
                if goal["key"] == "priority":
                    target = (goal.get("value") or "").strip().lower()
                    if target and target in typed:
                        goal["completed"] = True

        self.pending_goal = self._get_pending_goal()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _setup_goals(self, task_config: Dict):
        params = task_config.get("parameters", {}) or {}
        goal_text = (task_config.get("goal") or "").lower()
        object_text = (task_config.get("object") or "").lower()

        if "project" in goal_text or "project" in object_text:
            self.goals.append({"key": "open_projects", "value": None, "completed": False})

        name_value = params.get("project_name") or params.get("name") or params.get("title")
        status_value = (
            params.get("status")
            or params.get("backlog_status")
            or params.get("backlog_progress")
            or params.get("progress")
            or params.get("workflow_state")
        )
        priority_value = params.get("priority") or params.get("importance") or params.get("urgency")
        target_value = params.get("target_date") or params.get("due_date") or params.get("deadline")
        filter_value = params.get("filter") or params.get("filter_status")

        if not filter_value:
            # Fallback: infer filter target from goal text
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
            self.goals.append({"key": "project_name", "value": name_value.strip(), "completed": False})
        if isinstance(status_value, str) and status_value.strip():
            self.goals.append({"key": "status", "value": status_value.strip(), "completed": False})
        if isinstance(priority_value, str) and priority_value.strip():
            self.goals.append({"key": "priority", "value": priority_value.strip(), "completed": False})
        if isinstance(target_value, str) and target_value.strip():
            self.goals.append({"key": "target_date", "value": target_value.strip(), "completed": False})
        if isinstance(filter_value, str) and filter_value.strip():
            self.goals.append({"key": "filter", "value": filter_value.strip(), "completed": False})

        if self.goals:
            self.goals.append({"key": "submit", "value": None, "completed": False})

        self.pending_goal = self._get_pending_goal()

    def _collect_bbox_text(self, bboxes: List[Dict]) -> List[str]:
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

    def _normalize_text(self, text: str) -> str:
        return (text or "").strip().lower()

    def _normalize_for_search(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (text or "").lower())

    def _is_value_in_forms(self, value: str, forms: List[Dict]) -> bool:
        target = self._normalize_text(value)
        for field in forms:
            field_value = self._normalize_text(field.get("value", ""))
            if field_value == target:
                return True
        return False

    def _is_status_selected(self, value: str, texts: List[str]) -> bool:
        target_norm = self._normalize_for_search(value)
        if not target_norm:
            return False
        for text in texts:
            if target_norm in self._normalize_for_search(text):
                return True
        return False

    def _is_priority_selected(self, value: str, texts: List[str]) -> bool:
        target_norm = self._normalize_for_search(value)
        if not target_norm:
            return False
        for text in texts:
            norm_text = self._normalize_for_search(text)
            if "priority" in norm_text and target_norm in norm_text:
                return True
        return False

    def _is_filter_applied(self, value: str, texts: List[str]) -> bool:
        target_norm = self._normalize_for_search(value)
        targets = {target_norm}
        if target_norm.endswith("s"):
            targets.add(target_norm[:-1])
        keywords = {"filter", "filters", "filtered", "showing", "statusis", "status:", "workflow", "state:"}
        for text in texts:
            norm_text = self._normalize_for_search(text)
            if any(token in norm_text for token in targets):
                if any(key in norm_text for key in keywords):
                    print(f"[SubGoalManager] Detected filter chip text: {text!r}")
                    return True
                if f"statusis{target_norm}" in norm_text:
                    print(f"[SubGoalManager] Detected status phrase: {text!r}")
                    return True
        return False

    def _is_date_visible(self, value: str, texts: List[str]) -> bool:
        token_sets = self._date_token_sets(value)
        if not token_sets:
            return False
        for text in texts:
            lower = text.lower()
            if all(any(token_variant in lower for token_variant in options) for options in token_sets):
                return True
        return False

    def _date_token_sets(self, value: str) -> List[List[str]]:
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

    def _get_pending_goal(self) -> Optional[Dict]:
        for goal in self.goals:
            if not goal["completed"]:
                return goal
        return None

    def _build_goal_hint(self, goal: Dict) -> str:
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
        if key == "submit":
            return "All required fields are satisfied. Click the primary submit/create button to finish."
        return ""

    def _goal_completed(self, key: str) -> bool:
        for goal in self.goals:
            if goal["key"] == key:
                return goal["completed"]
        return False
