import re
from typing import Dict, List, Optional, Iterable


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
        self._modal_bbox = self._extract_modal_bbox(ui_state)

        status_control = self._find_status_control(bboxes)
        priority_control = self._find_priority_control(bboxes)

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
                goal["completed"] = self._control_matches(status_control, value)
            elif key == "priority":
                goal["completed"] = self._control_matches(priority_control, value)
            elif key == "target_date":
                goal["completed"] = self._is_date_visible(value, texts)
            elif key == "filter":
                goal["completed"] = self._is_filter_applied(value, texts)
            elif key == "description":
                goal["completed"] = self._is_description_filled(value, forms)
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

        pending_goal = self.pending_goal
        if pending_goal:
            goal_key = pending_goal.get("key")
            goal_value = pending_goal.get("value") or ""
            if goal_key == "project_name":
                guided = self._guide_project_name_action(action, bboxes, goal_value)
                if guided:
                    return guided
            elif goal_key == "status":
                guided = self._guide_status_action(action, ui_state, bboxes, goal_value)
                if guided:
                    return guided
            elif goal_key == "priority":
                guided = self._guide_priority_action(action, ui_state, bboxes, goal_value)
                if guided:
                    return guided
            elif goal_key == "description":
                guided = self._guide_description_action(action, bboxes, goal_value)
                if guided:
                    return guided
            elif goal_key == "submit":
                guided = self._guide_submit_action(action, bboxes)
                if guided:
                    return guided

        if action["action"] == "click" and element_text:
            if any(keyword in element_text for keyword in self.OPTIONAL_CLICK_KEYWORDS):
                if not self.pending_goal or self.pending_goal["key"] not in ["target_date", "priority"]:
                    print("⚠️  Skipping optional decoration control.")
                    return {"action": "wait", "reasoning": "Ignoring optional decoration controls"}

        if (
            not self.pending_goal
            and self.all_completed()
            and action["action"] != "finish"
        ):
            control = self._find_submit_control(bboxes)
            if control:
                print(
                    f"⚠️  All sub-goals satisfied. Redirecting to submit button "
                    f"[{control['index']}] '{(control.get('text') or '').strip()}'"
                )
                return {
                    "action": "click",
                    "element_id": control["index"],
                    "reasoning": "All fields complete. Submit the form to finish.",
                }
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
                if goal["key"] == "status":
                    target = self._normalize_text(goal.get("value"))
                    if target and target in element_text and "order" not in element_text:
                        goal["completed"] = True
                if goal["key"] == "priority":
                    target = self._normalize_text(goal.get("value"))
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
            typed_norm = self._normalize_text(typed)
            if not typed_norm:
                return
            for goal in self.goals:
                if goal["completed"]:
                    continue
                if goal["key"] == "project_name":
                    target = (goal.get("value") or "").strip().lower()
                    if target and target == typed_norm:
                        goal["completed"] = True
                if goal["key"] == "priority":
                    target = self._normalize_text(goal.get("value"))
                    if target and target in typed_norm:
                        goal["completed"] = True
                if goal["key"] == "description":
                    target = self._normalize_text(goal.get("value"))
                    if target:
                        if target in typed_norm:
                            goal["completed"] = True
                    elif typed_norm:
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
        description_value = (
            params.get("description")
            or params.get("project_description")
            or params.get("notes")
        )

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
        if isinstance(description_value, str) and description_value.strip():
            self.goals.append({"key": "description", "value": description_value.strip(), "completed": False})

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

    def _control_matches(self, control: Optional[Dict], value: Optional[str]) -> bool:
        if not control or not value:
            return False
        control_text = (control.get("text") or control.get("ariaLabel") or "").strip().lower()
        if not control_text:
            return False
        target_norm = self._normalize_text(value)
        return target_norm in control_text

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

    def _is_description_filled(self, value: Optional[str], forms: List[Dict]) -> bool:
        target_norm = self._normalize_text(value)
        for field in forms:
            field_type = (field.get("type") or "").lower()
            aria = (field.get("aria_label") or "").lower()
            if field_type in {"textarea"} or any(keyword in aria for keyword in self.DESCRIPTION_ARIA_KEYWORDS):
                current_value = self._normalize_text(field.get("value", ""))
                if target_norm:
                    if target_norm in current_value:
                        return True
                elif current_value:
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

    def _guide_status_action(self, action: Dict, ui_state: Dict, bboxes: List[Dict], value: str) -> Optional[Dict]:
        target_norm = self._normalize_text(value)
        if self._dropdown_open(ui_state):
            option = self._find_option_element(bboxes, target_norm)
            if option:
                if not self._action_targets(action, option["index"]):
                    print(
                        f"⚠️  Pending status '{value}'. Redirecting to option "
                        f"[{option['index']}] '{(option.get('text') or '').strip()}'"
                    )
                    return {
                        "action": "click",
                        "element_id": option["index"],
                        "reasoning": f"Select the status '{value}' in the dropdown.",
                    }
                return None

            search = self._find_dropdown_search(bboxes, placeholder_keywords=["status"])
            if search and not self._action_targets(action, search["index"]):
                print(f"⚠️  Pending status '{value}'. Typing into status search field [{search['index']}]")
                return {
                    "action": "type",
                    "element_id": search["index"],
                    "text": value,
                    "reasoning": f"Search for the status '{value}' before selecting it.",
                }

        control = self._find_status_control(bboxes)
        if control and not self._action_targets(action, control["index"]):
            label = (control.get("ariaLabel") or control.get("text") or "").strip()
            print(
                f"⚠️  Pending status '{value}'. Redirecting click to status control "
                f"[{control['index']}] '{label}'"
            )
            return {
                "action": "click",
                "element_id": control["index"],
                "reasoning": f"Open the status menu to change it to '{value}'.",
            }

        print("⚠️  Status options not yet accessible. Waiting briefly.")
        return {
            "action": "wait",
            "reasoning": f"Waiting for status control or options matching '{value}' to appear.",
        }

    def _guide_priority_action(self, action: Dict, ui_state: Dict, bboxes: List[Dict], value: str) -> Optional[Dict]:
        target_norm = self._normalize_text(value)
        if self._dropdown_open(ui_state):
            option = self._find_option_element(bboxes, target_norm)
            if option and not self._action_targets(action, option["index"]):
                print(
                    f"⚠️  Pending priority '{value}'. Redirecting to option "
                    f"[{option['index']}] '{(option.get('text') or '').strip()}'"
                )
                return {
                    "action": "click",
                    "element_id": option["index"],
                    "reasoning": f"Select the priority '{value}' in the dropdown.",
                }
            if option:
                return None
            search = self._find_dropdown_search(bboxes, placeholder_keywords=["priority"])
            if search and not self._action_targets(action, search["index"]):
                print(f"⚠️  Pending priority '{value}'. Typing into priority search field [{search['index']}]")
                return {
                    "action": "type",
                    "element_id": search["index"],
                    "text": value,
                    "reasoning": f"Search for the priority '{value}' before selecting it.",
                }

        control = self._find_priority_control(bboxes)
        if control and not self._action_targets(action, control["index"]):
            label = (control.get("ariaLabel") or control.get("text") or "").strip()
            print(
                f"⚠️  Pending priority '{value}'. Redirecting click to priority control "
                f"[{control['index']}] '{label}'"
            )
            return {
                "action": "click",
                "element_id": control["index"],
                "reasoning": f"Open the priority menu to change it to '{value}'.",
            }

        print("⚠️  Priority options not yet accessible. Waiting briefly.")
        return {
            "action": "wait",
            "reasoning": f"Waiting for priority control or options matching '{value}' to appear.",
        }

    def _guide_description_action(self, action: Dict, bboxes: List[Dict], value: str) -> Optional[Dict]:
        field = self._find_description_bbox(bboxes, modal_bbox=self._modal_bbox)
        if not field:
            return None
        if action.get("action") == "type" and self._action_targets(action, field["index"]):
            return None

        text_to_use = action.get("text") or value.strip()
        if not text_to_use:
            text_to_use = self._auto_description_text()

        print(f"⚠️  Pending description. Redirecting typing to element [{field['index']}]")
        return {
            "action": "type",
            "element_id": field["index"],
            "text": text_to_use,
            "reasoning": "Fill in the project description field with the requested text.",
        }

    def _guide_project_name_action(self, action: Dict, bboxes: List[Dict], value: str) -> Optional[Dict]:
        field = self._find_project_name_bbox(bboxes, modal_bbox=self._modal_bbox)
        if not field:
            return None
        if action.get("action") == "type" and self._action_targets(action, field["index"]):
            return None

        desired_text = value.strip() or action.get("text") or "New project"
        print(f"⚠️  Pending project name. Redirecting typing to element [{field['index']}]")
        return {
            "action": "type",
            "element_id": field["index"],
            "text": desired_text,
            "reasoning": f"Type the project name '{desired_text}'.",
        }

    def _guide_submit_action(self, action: Dict, bboxes: List[Dict]) -> Optional[Dict]:
        button = self._find_submit_control(bboxes, modal_bbox=self._modal_bbox)
        if button and not self._action_targets(action, button["index"]):
            label = (button.get("text") or button.get("ariaLabel") or "").strip()
            print(
                f"⚠️  All goals satisfied. Redirecting to submit control "
                f"[{button['index']}] '{label}'"
            )
            return {
                "action": "click",
                "element_id": button["index"],
                "reasoning": "All required fields complete. Submit to finish.",
            }
        return None

    def _dropdown_open(self, ui_state: Dict) -> bool:
        if not ui_state.get("modals"):
            return False
        dropdowns = ui_state.get("dropdowns") or []
        return bool(dropdowns)

    def _find_modal_button(
        self,
        bboxes: List[Dict],
        *,
        aria_keywords: Optional[List[str]] = None,
        text_tokens: Optional[Iterable[str]] = None,
        modal_bbox: Optional[Dict] = None,
    ) -> Optional[Dict]:
        aria_keywords = [kw.lower() for kw in (aria_keywords or [])]
        normalized_tokens = [self._normalize_text(token) for token in (text_tokens or []) if token]

        for bbox in bboxes:
            if bbox.get("type") != "button":
                continue
            aria = (bbox.get("ariaLabel") or "").lower()
            text = (bbox.get("text") or "").strip().lower()
            if modal_bbox and not self._within_modal(bbox, modal_bbox):
                continue
            if aria_keywords and any(keyword in aria for keyword in aria_keywords):
                return bbox
            if normalized_tokens and any(token in text for token in normalized_tokens):
                return bbox
        return None

    def _find_option_element(self, bboxes: List[Dict], target_norm: str) -> Optional[Dict]:
        if not target_norm:
            return None
        for bbox in bboxes:
            text = (bbox.get("text") or "").strip()
            if not text:
                continue
            normalized = self._normalize_text(text)
            if normalized == target_norm or target_norm in normalized:
                return bbox
        return None

    def _action_targets(self, action: Dict, element_index: int) -> bool:
        if not action:
            return False
        return (
            action.get("action") in {"click", "type"}
            and action.get("element_id") == element_index
        )

    def _find_description_bbox(self, bboxes: List[Dict], modal_bbox: Optional[Dict] = None) -> Optional[Dict]:
        aria_keywords = [kw.lower() for kw in self.DESCRIPTION_ARIA_KEYWORDS]
        for bbox in bboxes:
            element_type = (bbox.get("type") or "").lower()
            role = (bbox.get("role") or "").lower()
            aria = (bbox.get("ariaLabel") or "").lower()
            if modal_bbox and not self._within_modal(bbox, modal_bbox):
                continue
            if element_type == "textarea":
                return bbox
            if role == "textbox" and any(keyword in aria for keyword in aria_keywords):
                return bbox
            if any(keyword in aria for keyword in aria_keywords):
                return bbox
        return None

    def _find_project_name_bbox(self, bboxes: List[Dict], modal_bbox: Optional[Dict] = None) -> Optional[Dict]:
        aria_keywords = ["project name", "name field", "title"]
        for bbox in bboxes:
            element_type = (bbox.get("type") or "").lower()
            role = (bbox.get("role") or "").lower()
            aria = (bbox.get("ariaLabel") or "").lower()
            text = (bbox.get("text") or "").strip().lower()
            if modal_bbox and not self._within_modal(bbox, modal_bbox):
                continue
            if role == "textbox" or element_type in {"div", "input"}:
                if any(keyword in aria for keyword in aria_keywords):
                    return bbox
                if text in {"untitled", "new project"}:
                    return bbox
        return None

    def _find_status_control(self, bboxes: List[Dict]) -> Optional[Dict]:
        for bbox in bboxes:
            if (bbox.get("type") or "").lower() not in {"button", "div", "span"}:
                continue
            aria = (bbox.get("ariaLabel") or "").lower()
            text = (bbox.get("text") or "").strip().lower()
            if "order by" in aria or "sort" in aria:
                continue
            if "change project status" in aria or "change status" in aria:
                return bbox
            if "status" in aria and "order by" not in aria:
                return bbox
            if text in {"backlog", "todo", "planned"}:
                return bbox
        return None

    def _find_priority_control(self, bboxes: List[Dict]) -> Optional[Dict]:
        for bbox in bboxes:
            if (bbox.get("type") or "").lower() not in {"button", "div", "span"}:
                continue
            aria = (bbox.get("ariaLabel") or "").lower()
            text = (bbox.get("text") or "").strip().lower()
            if "order by" in aria or "sort" in aria:
                continue
            if "change project priority" in aria or "change priority" in aria:
                return bbox
            if "priority" in aria and "order by" not in aria:
                return bbox
            if text in {"no priority", "priority", "urgent", "high priority", "medium priority", "low priority"}:
                return bbox
        return None

    def _find_dropdown_search(
        self, bboxes: List[Dict], placeholder_keywords: Iterable[str]
    ) -> Optional[Dict]:
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

    def _find_submit_control(self, bboxes: List[Dict], modal_bbox: Optional[Dict] = None) -> Optional[Dict]:
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
            if modal_bbox and not self._within_modal(bbox, modal_bbox):
                continue
            text = (bbox.get("text") or "").strip().lower()
            aria = (bbox.get("ariaLabel") or "").strip().lower()
            combined = f"{text} {aria}".strip()
            if any(keyword in combined for keyword in submit_keywords):
                if "create new issue" in combined or "new view" in combined:
                    continue
                return bbox
        return None

    def _auto_description_text(self) -> str:
        parameters = self.task_config.get("parameters", {}) or {}
        project_name = parameters.get("project_name") or parameters.get("name") or "this project"
        return f"Automated description for {project_name} created by Agent B."

    def _extract_modal_bbox(self, ui_state: Dict) -> Optional[Dict]:
        modals = ui_state.get("modals") or []
        for modal in modals:
            bbox = modal.get("bbox")
            if bbox and bbox.get("width", 0) >= 50 and bbox.get("height", 0) >= 50:
                return bbox
        return None

    def _within_modal(self, bbox: Dict, modal_bbox: Dict) -> bool:
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
        if key == "description":
            if value:
                return f"Next required step: type the project description '{value}'."
            return "Next required step: add a project description."
        if key == "submit":
            return "All required fields are satisfied. Click the primary submit/create button to finish."
        return ""

    def _goal_completed(self, key: str) -> bool:
        for goal in self.goals:
            if goal["key"] == key:
                return goal["completed"]
        return False
        control = self._find_priority_control(bboxes)
        if control:
            current_text = (control.get("text") or "").strip().lower()
            target_norm = self._normalize_text(value)
            if target_norm and target_norm in current_text and "priority" not in current_text:
                return None
