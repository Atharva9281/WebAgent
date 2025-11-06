"""
Shared runtime logic for Agent B variants.

This module defines AgentBase, a reusable orchestrator that both the
standard and clean agents inherit from.  It encapsulates the common
workflow: parsing tasks, managing sub-goals, running the main loop,
capturing annotation data, executing actions, and saving datasets.

Subclasses provide small customisations through class attributes or by
overriding a handful of hook methods (for logging or metadata tweaks).
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from state_detector import get_complete_ui_state, describe_ui_state
from task_definitions import TASKS, get_task_by_id, list_all_tasks
from task_parser import TaskParser
from subgoal_manager import SubGoalManager
from gemini_client import GeminiClient


class AgentBase(ABC):
    """
    Base class implementing the shared automation flow.

    Subclasses supply a browser controller class and customise prints,
    dataset naming, and step metadata through class attributes or hooks.
    """

    # ------------------------------------------------------------------
    # Subclass configuration knobs
    # ------------------------------------------------------------------
    BROWSER_CONTROLLER_CLS = None  # type: ignore

    MODE_NAME = "WEB AUTOMATION AGENT"
    MODE_INTRO_LINES: List[str] = []
    RUNTIME_MODE_LABEL = "RUNTIME FLEXIBLE"

    QUERY_HEADER_TITLE = "🤖 AGENT B - HANDLING RUNTIME QUERY"
    QUERY_HEADER_EXTRA: List[str] = []

    MULTI_TASK_HEADER_TITLE = "🔥 MULTI-TASK DETECTED"
    MULTI_TASK_EXTRA_LINES: List[str] = []

    SINGLE_TASK_HEADER_TITLE = "🚀 STARTING DYNAMIC TASK"
    SINGLE_TASK_EXTRA_LINES: List[str] = []

    PREDEFINED_TASK_HEADER_TITLE = "🚀 STARTING TASK"
    PREDEFINED_TASK_EXTRA_LINES: List[str] = []

    DATASET_DYNAMIC_SUFFIX = ""
    DATASET_PREDEFINED_SUFFIX = ""
    DATASET_DIR_NAME = "dataset"

    METADATA_BASE: Dict[str, str] = {}
    STEP_METADATA_EXTRA: Dict[str, str] = {}

    STEP_ANNOTATE_LABEL = "Annotating page..."
    STEP_SCREENSHOT_LABEL = "Screenshot saved"
    STEP_EXECUTE_LABEL = "Executing action..."
    STEP_POST_OBSERVATION_LABEL: Optional[str] = None
    STEP_WAIT_BETWEEN_SECONDS = 1

    FINISH_SUCCESS_MESSAGE = "✅ Task completion validated successfully"
    FINISH_BLOCKED_LOG = "⚠️  Finish blocked: {reason}. Converting to wait..."
    STEP_ACTION_LOG = "   ✅ {observation}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def __init__(self, gemini_api_key: str):
        if not self.BROWSER_CONTROLLER_CLS:
            raise ValueError("Subclass must set BROWSER_CONTROLLER_CLS")

        self.browser = self.BROWSER_CONTROLLER_CLS()
        self.gemini = GeminiClient(gemini_api_key)
        self.task_parser = TaskParser(gemini_api_key=gemini_api_key)
        self.action_history: List[Dict] = []
        self.subgoal_manager: Optional[SubGoalManager] = None
        self.previous_step_state: Optional[Dict] = None

        self._print_initialisation_summary()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle_query(self, query: str) -> Dict:
        """Entry point for natural-language requests."""
        self._print_query_header(query)

        task_config = self.task_parser.parse_query(query)
        if not task_config:
            print("❌ Failed to parse query")
            return {"success": False, "error": "Could not parse query", "query": query}

        if not self.task_parser.validate_task_config(task_config):
            print("❌ Invalid task configuration")
            return {"success": False, "error": "Invalid task configuration", "query": query}

        if task_config.get("is_multi_task", False):
            return self._execute_multi_task(task_config, query)

        result = self.execute_dynamic_task(task_config)
        result["original_query"] = query
        return result

    def execute_dynamic_task(self, task_config: Dict) -> Dict:
        """Execute a runtime-generated task configuration."""
        self._print_single_task_header(task_config)

        dataset_dir = self._create_dataset_dir(task_config, is_predefined=False)
        metadata = self._initialise_metadata(task_config, dataset_dir, is_predefined=False)

        self.action_history = []
        self.subgoal_manager = SubGoalManager(task_config)
        self.previous_step_state = None

        if not self.browser.setup_browser(task_config):
            return {"success": False, "error": "Browser setup failed"}

        if not self.browser.navigate_to_url(task_config["start_url"]):
            self.browser.cleanup()
            return {"success": False, "error": "Navigation failed"}

        try:
            success = self._execute_task_loop(task_config, dataset_dir, metadata)
            metadata["success"] = success
        except Exception as err:  # pragma: no cover - defensive logging
            print(f"\n❌ Task execution failed: {err}")
            import traceback

            traceback.print_exc()
            metadata["error"] = str(err)
            metadata["success"] = False
        finally:
            self.browser.cleanup()

        self._finalise_metadata(metadata, dataset_dir)
        self._print_task_summary(metadata, dataset_dir)
        return metadata

    def execute_task(self, task_id: str) -> Dict:
        """Execute a predefined task by identifier."""
        try:
            task_config = get_task_by_id(task_id)
        except ValueError as err:
            print(f"❌ Error: {err}")
            print(f"Available tasks: {list_all_tasks()}")
            return {"success": False, "error": str(err)}

        self._print_predefined_task_header(task_config)

        dataset_dir = self._create_dataset_dir(task_config, is_predefined=True)
        metadata = self._initialise_metadata(task_config, dataset_dir, is_predefined=True)

        self.action_history = []
        self.subgoal_manager = SubGoalManager(task_config)
        self.previous_step_state = None

        if not self.browser.setup_browser(task_config):
            return {"success": False, "error": "Browser setup failed"}

        if not self.browser.navigate_to_url(task_config["start_url"]):
            self.browser.cleanup()
            return {"success": False, "error": "Navigation failed"}

        try:
            success = self._execute_task_loop(task_config, dataset_dir, metadata)
            metadata["success"] = success
        except Exception as err:  # pragma: no cover - defensive logging
            print(f"\n❌ Task execution failed: {err}")
            import traceback

            traceback.print_exc()
            metadata["error"] = str(err)
            metadata["success"] = False
        finally:
            self.browser.cleanup()

        self._finalise_metadata(metadata, dataset_dir)
        self._print_task_summary(metadata, dataset_dir)
        return metadata

    # ------------------------------------------------------------------
    # Multi-task handling
    # ------------------------------------------------------------------
    def _execute_multi_task(self, task_config: Dict, original_query: str) -> Dict:
        self._print_multi_task_header(task_config)

        individual_tasks = self.task_parser.expand_multi_task(task_config)
        self._print_expanded_task_list(individual_tasks)

        all_results = []
        for index, specific_task in enumerate(individual_tasks, start=1):
            self._print_multi_task_progress(index, len(individual_tasks))
            result = self.execute_dynamic_task(specific_task)
            result.update(
                {
                    "task_number": index,
                    "total_tasks": len(individual_tasks),
                    "original_query": original_query,
                }
            )
            all_results.append(result)

            if not result.get("success"):
                print(f"\n⚠️  Task {index} failed, stopping multi-task execution")
                break

            if index < len(individual_tasks):
                self._print_multi_task_pause(index)
                time.sleep(2)

        successful = sum(1 for r in all_results if r.get("success"))
        total = len(individual_tasks)
        return {
            "success": successful == total,
            "original_query": original_query,
            "is_multi_task": True,
            "total_tasks": total,
            "successful_tasks": successful,
            "failed_tasks": total - successful,
            "individual_results": all_results,
            "summary": f"Completed {successful}/{total} tasks",
        }

    # ------------------------------------------------------------------
    # Core execution loop
    # ------------------------------------------------------------------
    def _execute_task_loop(self, task_config: Dict, dataset_dir: Path, metadata: Dict) -> bool:
        max_steps = task_config["max_steps"]
        goal = task_config["goal"]

        consecutive_failures = 0
        max_failures = 3

        for step_num in range(1, max_steps + 1):
            self._print_step_header(step_num, max_steps)

            try:
                outcome = self._execute_single_step(
                    step_num=step_num,
                    goal=goal,
                    task_config=task_config,
                    dataset_dir=dataset_dir,
                    metadata=metadata,
                )

                if outcome == "completed":
                    print("\n🎉 Task marked as complete by agent!")
                    print(self.FINISH_SUCCESS_MESSAGE)
                    return True

                if outcome == "failed":
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        print(f"\n⚠️  Too many consecutive failures ({max_failures})")
                        print("   Stopping task execution")
                        return False
                else:
                    consecutive_failures = 0

                time.sleep(self.STEP_WAIT_BETWEEN_SECONDS)

            except Exception as err:  # pragma: no cover - defensive logging
                print(f"\n❌ Step {step_num} failed: {err}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print(f"\n⚠️  Too many consecutive failures ({max_failures})")
                    return False
                self._save_error_screenshot(dataset_dir, step_num)

        print(f"\n⚠️  Reached maximum steps ({max_steps})")
        return False

    def _execute_single_step(
        self,
        step_num: int,
        goal: str,
        task_config: Dict,
        dataset_dir: Path,
        metadata: Dict,
    ) -> str:
        print(f"1️⃣  {self.STEP_ANNOTATE_LABEL}")
        annotation_result = self._capture_annotation()

        if not annotation_result["bboxes"]:
            print("⚠️  No interactive elements found - might be loading")
            time.sleep(2)
            return "continue"

        screenshot_filename = f"step_{step_num:02d}.png"
        screenshot_path = dataset_dir / screenshot_filename

        with open(screenshot_path, "wb") as handle:
            handle.write(annotation_result["screenshot"])

        print(f"2️⃣  {self.STEP_SCREENSHOT_LABEL}: {screenshot_filename}")

        print("3️⃣  Detecting UI state...")
        ui_state = get_complete_ui_state(self.browser.page)
        description = describe_ui_state(ui_state)
        print(f"   {description}")
        transition = self._build_transition_metadata(step_num, ui_state)

        if self.subgoal_manager:
            self.subgoal_manager.update(ui_state, annotation_result["bboxes"])

        submit_hint = self._build_submit_hint(ui_state, annotation_result["bboxes"])

        combined_hint = None
        if self.subgoal_manager:
            combined_hint = self.subgoal_manager.build_hint(submit_hint, ui_state)
        elif submit_hint:
            combined_hint = submit_hint

        print("4️⃣  Asking Gemini for next action...")
        action = self.gemini.get_next_action(
            goal=goal,
            screenshot_b64=annotation_result["screenshot_b64"],
            bboxes=annotation_result["bboxes"],
            current_url=self.browser.get_current_url(),
            action_history=self.action_history,
            task_parameters=task_config.get("parameters", {}),
            hint=combined_hint,
        )

        self._enrich_action_details(action, annotation_result["bboxes"])

        if self.subgoal_manager:
            blocked_reason = self.subgoal_manager.block_finish_reason(action, ui_state)
            if blocked_reason:
                print(self.FINISH_BLOCKED_LOG.format(reason=blocked_reason))
                action = {"action": "wait", "reasoning": f"{blocked_reason} - waiting before finishing"}

            action = self.subgoal_manager.adjust_action(action, ui_state, annotation_result["bboxes"])

        self._print_action_info(action)

        if action["action"] == "finish":
            if self.gemini.validate_task_completion(
                task_config=task_config,
                current_url=self.browser.get_current_url(),
                page_title=self.browser.get_page_title(),
                action=action,
            ):
                self._save_step_metadata(
                    step_num,
                    action,
                    "Task completed successfully",
                    ui_state,
                    description,
                    screenshot_filename,
                    dataset_dir,
                    metadata,
                    transition,
                )
                return "completed"

            print("\n❌ Task completion validation failed - continuing...")
            action["action"] = "wait"
            action["reasoning"] = "Task not actually complete - continuing automation"

        print(f"5️⃣  {self.STEP_EXECUTE_LABEL}")
        observation = self.browser.execute_action(action, annotation_result["bboxes"])
        print(self.STEP_ACTION_LOG.format(observation=observation))
        self._post_action_observation(observation)

        self._save_step_metadata(
            step_num,
            action,
            observation,
            ui_state,
            description,
            screenshot_filename,
            dataset_dir,
            metadata,
            transition,
        )

        if self.subgoal_manager:
            self.subgoal_manager.record_action(action)

        self.action_history.append(
            {"step": step_num, "action": action["action"], "observation": observation}
        )
        return "continue"

    # ------------------------------------------------------------------
    # Hooks & helpers
    # ------------------------------------------------------------------
    @abstractmethod
    def _capture_annotation(self) -> Dict:
        """Return annotation payload for the current page."""

    def _post_action_observation(self, observation: str) -> None:
        """Optional hook for subclasses to add logging after executing."""
        if self.STEP_POST_OBSERVATION_LABEL:
            print(self.STEP_POST_OBSERVATION_LABEL)

    def _enrich_action_details(self, action: Dict, bboxes: List[Dict]) -> None:
        """Attach contextual element metadata to the action payload."""
        if not action or action.get("element_id") is None:
            return

        try:
            element_id = int(action.get("element_id"))
        except (TypeError, ValueError):
            return

        bbox = next((box for box in bboxes if box.get("index") == element_id), None)
        if not bbox:
            return

        text = (bbox.get("text") or "").strip()
        action["element_text"] = text
        action["element_type"] = bbox.get("type", "")
        action["bbox"] = [
            bbox.get("x"),
            bbox.get("y"),
            bbox.get("width"),
            bbox.get("height"),
        ]
        action["element_details"] = {
            "text": text,
            "type": bbox.get("type", ""),
            "aria_label": bbox.get("ariaLabel", ""),
            "role": bbox.get("role", ""),
            "href": bbox.get("href", ""),
            "id": bbox.get("id", ""),
            "class_name": bbox.get("className", ""),
        }

    def _build_transition_metadata(self, step_num: int, ui_state: Dict) -> Dict:
        """Compare current state to previous step for change tracking."""
        previous = self.previous_step_state or {}
        current_url = ui_state.get("url", "") if ui_state else ""
        current_hash = ui_state.get("page_hash", "") if ui_state else ""

        transition = {
            "previous_step": previous.get("step"),
            "previous_url": previous.get("url", ""),
            "previous_page_hash": previous.get("page_hash", ""),
            "current_step": step_num,
            "current_url": current_url,
            "current_page_hash": current_hash,
            "url_changed": False,
            "dom_changed": False,
        }

        if previous:
            transition["url_changed"] = transition["previous_url"] != current_url
            prev_hash = previous.get("page_hash", "")
            if prev_hash and current_hash:
                transition["dom_changed"] = prev_hash != current_hash
            else:
                transition["dom_changed"] = bool(prev_hash or current_hash)

        return transition

    def _build_submit_hint(self, ui_state: Dict, bboxes: List[Dict]) -> Optional[Dict]:
        """Detect primary submit button when a modal with filled fields is open."""
        if not ui_state.get("modals"):
            return None

        filled_fields = [field for field in ui_state.get("forms", []) if field.get("filled")]
        if not filled_fields:
            return None

        submit_keywords = ["create", "submit", "save", "add", "confirm", "done", "finish", "publish"]
        cancel_keywords = ["cancel", "close", "discard"]

        candidates = []
        for bbox in bboxes:
            text = (bbox.get("text") or "").strip()
            if bbox.get("type") != "button" or not text:
                continue
            lower = text.lower()
            if any(keyword in lower for keyword in submit_keywords) and not any(
                keyword in lower for keyword in cancel_keywords
            ):
                candidates.append(bbox)

        if not candidates:
            return None

        primary = candidates[0]
        label = (primary.get("text") or "").strip() or "primary action"
        message = f"Modal detected with filled fields. Consider clicking [{primary['index']}] '{label}' to submit."
        print(f"💡 {message}")
        return {"type": "modal_submit_suggestion", "message": message, "element_id": primary["index"]}

    def _save_step_metadata(
        self,
        step_num: int,
        action: Dict,
        observation: str,
        ui_state: Dict,
        description: str,
        screenshot_filename: str,
        dataset_dir: Path,
        metadata: Dict,
        transition: Optional[Dict] = None,
    ) -> None:
        """Persist metadata for a single step."""
        step_metadata = {
            "step": step_num,
            "url": self.browser.get_current_url(),
            "screenshot": screenshot_filename,
            "action": action,
            "observation": observation,
            "ui_state": ui_state,
            "description": description,
            "timestamp": datetime.now().isoformat(),
        }
        if transition:
            step_metadata["transition"] = transition
        if self.STEP_METADATA_EXTRA:
            step_metadata.update(self.STEP_METADATA_EXTRA)

        metadata["steps"].append(step_metadata)
        step_json_path = dataset_dir / f"step_{step_num:02d}.json"
        with open(step_json_path, "w") as handle:
            json.dump(step_metadata, handle, indent=2)

        self.previous_step_state = {
            "step": step_num,
            "url": ui_state.get("url", "") if ui_state else "",
            "page_hash": ui_state.get("page_hash", "") if ui_state else "",
        }

    def _save_error_screenshot(self, dataset_dir: Path, step_num: int) -> None:
        """Capture a screenshot when a step throws."""
        try:  # pragma: no cover - best effort only
            error_bytes = self.browser.page.screenshot()
            error_path = dataset_dir / f"step_{step_num:02d}_error.png"
            with open(error_path, "wb") as handle:
                handle.write(error_bytes)
        except Exception:
            pass

    def _finalise_metadata(self, metadata: Dict, dataset_dir: Path) -> None:
        """Persist aggregated metadata to disk."""
        metadata["finished_at"] = datetime.now().isoformat()
        metadata["total_steps"] = len(metadata["steps"])
        metadata_path = dataset_dir / "metadata.json"
        with open(metadata_path, "w") as handle:
            json.dump(metadata, handle, indent=2)

    # ------------------------------------------------------------------
    # Printing helpers (override for custom messaging)
    # ------------------------------------------------------------------
    def _print_initialisation_summary(self) -> None:
        print(f"✅ {self.MODE_NAME} initialised")
        for line in self.MODE_INTRO_LINES:
            print(f"   {line}")
        print(f"   Task Parser: Ready")

    def _print_query_header(self, query: str) -> None:
        print("\n" + "=" * 70)
        print(self.QUERY_HEADER_TITLE)
        print("=" * 70)
        print(f"Query: {query}")
        for line in self.QUERY_HEADER_EXTRA:
            print(line)
        print("=" * 70 + "\n")

    def _print_multi_task_header(self, task_config: Dict) -> None:
        print("\n" + "=" * 70)
        print(self.MULTI_TASK_HEADER_TITLE)
        print("=" * 70)
        for line in self.MULTI_TASK_EXTRA_LINES:
            print(line)
        print(f"Count: {task_config.get('parameters', {}).get('count', 1)}")
        print(f"Names: {task_config.get('parameters', {}).get('names', [])}")
        print("=" * 70 + "\n")

    def _print_expanded_task_list(self, tasks: List[Dict]) -> None:
        print(f"📋 Expanded into {len(tasks)} individual tasks:")
        for index, task in enumerate(tasks, start=1):
            print(f"   {index}. {task['name']}")
        print()

    def _print_multi_task_progress(self, index: int, total: int) -> None:
        print("\n" + "=" * 70)
        print(f"🚀 EXECUTING TASK {index}/{total}")
        print("=" * 70)

    def _print_multi_task_pause(self, index: int) -> None:
        print(f"\n✅ Task {index} completed. Continuing to next task...")

    def _print_single_task_header(self, task_config: Dict) -> None:
        print("\n" + "=" * 70)
        print(f"{self.SINGLE_TASK_HEADER_TITLE}: {task_config['name']}")
        print("=" * 70)
        print(f"Goal: {task_config['goal']}")
        print(f"App: {task_config['app'].upper()}")
        print(f"Start URL: {task_config['start_url']}")
        print(f"Max steps: {task_config['max_steps']}")
        for line in self.SINGLE_TASK_EXTRA_LINES:
            print(line)
        print("=" * 70 + "\n")

    def _print_predefined_task_header(self, task_config: Dict) -> None:
        print("\n" + "=" * 70)
        print(f"{self.PREDEFINED_TASK_HEADER_TITLE}: {task_config['name']}")
        print("=" * 70)
        print(f"Goal: {task_config['goal']}")
        print(f"App: {task_config['app'].upper()}")
        print(f"Start URL: {task_config['start_url']}")
        print(f"Max steps: {task_config['max_steps']}")
        for line in self.PREDEFINED_TASK_EXTRA_LINES:
            print(line)
        print("=" * 70 + "\n")

    def _print_step_header(self, step_num: int, max_steps: int) -> None:
        print("\n" + "─" * 70)
        print(f"📸 STEP {step_num}/{max_steps}")
        print("─" * 70)

    def _print_action_info(self, action: Dict) -> None:
        print(f"   🤖 Action: {action['action']}")
        if action.get("element_id") is not None:
            print(f"   🎯 Element: [{action['element_id']}]")
        if action.get("text"):
            print(f"   ✍️  Text: '{action['text'][:50]}...'")
        if action.get("reasoning"):
            print(f"   💭 Reasoning: {action['reasoning']}")

    def _print_task_summary(self, metadata: Dict, dataset_dir: Path) -> None:
        print("\n" + "=" * 70)
        if metadata.get("success"):
            print("✅ TASK COMPLETED SUCCESSFULLY")
        else:
            print("⚠️  TASK INCOMPLETE")
        print("=" * 70)
        print(f"Total steps: {metadata.get('total_steps', 0)}")
        print(f"Dataset saved: {dataset_dir}")
        print("=" * 70 + "\n")

    # ------------------------------------------------------------------
    # Dataset & metadata helpers
    # ------------------------------------------------------------------
    def _create_dataset_dir(self, task_config: Dict, *, is_predefined: bool) -> Path:
        suffix = self.DATASET_PREDEFINED_SUFFIX if is_predefined else self.DATASET_DYNAMIC_SUFFIX

        if is_predefined:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dataset_name = f"{task_config['task_id']}{suffix}_{timestamp}"
        else:
            dataset_name = f"{task_config['task_id']}{suffix}"

        dataset_dir = Path(self.DATASET_DIR_NAME) / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Dataset directory: {dataset_dir}")
        return dataset_dir

    def _initialise_metadata(self, task_config: Dict, dataset_dir: Path, *, is_predefined: bool) -> Dict:
        metadata = {
            "task_id": task_config["task_id"],
            "task_name": task_config["name"],
            "app": task_config["app"],
            "goal": task_config["goal"],
            "start_url": task_config["start_url"],
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "success": False,
            "total_steps": 0,
            "parsed_from_query": task_config.get("parsed_from_query", ""),
        }
        if self.METADATA_BASE:
            metadata.update(self.METADATA_BASE)
        metadata["dataset_dir"] = str(dataset_dir)
        return metadata


def list_predefined_tasks(script_name: str = "agent.py") -> None:
    """Utility helper for CLI modes."""
    print("\n" + "=" * 70)
    print("📋 AVAILABLE PREDEFINED TASKS")
    print("=" * 70)
    for index, task in enumerate(TASKS, start=1):
        print(f"\n{index}. {task['task_id']}")
        print(f"   App: {task['app'].upper()}")
        print(f"   Goal: {task['goal']}")
    print("\n" + "=" * 70)
    print("\nUsage:")
    if TASKS:
        print(f"  python src/{script_name} --task {TASKS[0]['task_id']}")
    print("=" * 70 + "\n")
