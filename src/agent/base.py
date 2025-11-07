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

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from task_definitions import get_task_by_id, list_all_tasks
from parser import TaskParser
from subgoal import SubGoalManager
from gemini import GeminiClient
from .helpers import create_dataset_dir, initialise_metadata, finalise_metadata
from .task_executor import execute_task_loop, execute_multi_task
from .printing import (
    print_initialisation_summary,
    print_query_header,
    print_multi_task_header,
    print_expanded_task_list,
    print_multi_task_progress,
    print_multi_task_pause,
    print_single_task_header,
    print_predefined_task_header,
    print_step_header,
    print_action_info,
    print_task_summary,
    list_predefined_tasks
)


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

        print_initialisation_summary(self.MODE_NAME, self.MODE_INTRO_LINES)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle_query(self, query: str) -> Dict:
        """Entry point for natural-language requests."""
        print_query_header(query, self.QUERY_HEADER_TITLE, self.QUERY_HEADER_EXTRA)

        task_config = self.task_parser.parse_query(query)
        if not task_config:
            print("❌ Failed to parse query")
            return {"success": False, "error": "Could not parse query", "query": query}

        if not self.task_parser.validate_task_config(task_config):
            print("❌ Invalid task configuration")
            return {"success": False, "error": "Invalid task configuration", "query": query}

        if task_config.get("is_multi_task", False):
            return execute_multi_task(self, task_config, query)

        result = self.execute_dynamic_task(task_config)
        result["original_query"] = query
        return result

    def execute_dynamic_task(self, task_config: Dict) -> Dict:
        """Execute a runtime-generated task configuration."""
        print_single_task_header(task_config, self.SINGLE_TASK_HEADER_TITLE, self.SINGLE_TASK_EXTRA_LINES)

        dataset_dir = create_dataset_dir(
            task_config, 
            is_predefined=False,
            dataset_predefined_suffix=self.DATASET_PREDEFINED_SUFFIX,
            dataset_dynamic_suffix=self.DATASET_DYNAMIC_SUFFIX,
            dataset_dir_name=self.DATASET_DIR_NAME
        )
        metadata = initialise_metadata(
            task_config, 
            dataset_dir, 
            is_predefined=False, 
            metadata_base=self.METADATA_BASE
        )

        self.action_history = []
        self.subgoal_manager = SubGoalManager(task_config)
        self.previous_step_state = None

        if not self.browser.setup_browser(task_config):
            return {"success": False, "error": "Browser setup failed"}

        if not self.browser.navigate_to_url(task_config["start_url"]):
            self.browser.cleanup()
            return {"success": False, "error": "Navigation failed"}

        try:
            success = execute_task_loop(self, task_config, dataset_dir, metadata)
            metadata["success"] = success
        except Exception as err:  # pragma: no cover - defensive logging
            print(f"\n❌ Task execution failed: {err}")
            import traceback

            traceback.print_exc()
            metadata["error"] = str(err)
            metadata["success"] = False
        finally:
            self.browser.cleanup()

        finalise_metadata(metadata, dataset_dir)
        print_task_summary(metadata, dataset_dir)
        return metadata

    def execute_task(self, task_id: str) -> Dict:
        """Execute a predefined task by identifier."""
        try:
            task_config = get_task_by_id(task_id)
        except ValueError as err:
            print(f"❌ Error: {err}")
            print(f"Available tasks: {list_all_tasks()}")
            return {"success": False, "error": str(err)}

        print_predefined_task_header(task_config, self.PREDEFINED_TASK_HEADER_TITLE, self.PREDEFINED_TASK_EXTRA_LINES)

        dataset_dir = create_dataset_dir(
            task_config, 
            is_predefined=True,
            dataset_predefined_suffix=self.DATASET_PREDEFINED_SUFFIX,
            dataset_dynamic_suffix=self.DATASET_DYNAMIC_SUFFIX,
            dataset_dir_name=self.DATASET_DIR_NAME
        )
        metadata = initialise_metadata(
            task_config, 
            dataset_dir, 
            is_predefined=True, 
            metadata_base=self.METADATA_BASE
        )

        self.action_history = []
        self.subgoal_manager = SubGoalManager(task_config)
        self.previous_step_state = None

        if not self.browser.setup_browser(task_config):
            return {"success": False, "error": "Browser setup failed"}

        if not self.browser.navigate_to_url(task_config["start_url"]):
            self.browser.cleanup()
            return {"success": False, "error": "Navigation failed"}

        try:
            success = execute_task_loop(self, task_config, dataset_dir, metadata)
            metadata["success"] = success
        except Exception as err:  # pragma: no cover - defensive logging
            print(f"\n❌ Task execution failed: {err}")
            import traceback

            traceback.print_exc()
            metadata["error"] = str(err)
            metadata["success"] = False
        finally:
            self.browser.cleanup()

        finalise_metadata(metadata, dataset_dir)
        print_task_summary(metadata, dataset_dir)
        return metadata

    # ------------------------------------------------------------------
    # Hooks & methods for subclasses
    # ------------------------------------------------------------------
    @abstractmethod
    def _capture_annotation(self) -> Dict:
        """Return annotation payload for the current page."""

    def _post_action_observation(self, observation: str) -> None:
        """Optional hook for subclasses to add logging after executing."""
        if self.STEP_POST_OBSERVATION_LABEL:
            print(self.STEP_POST_OBSERVATION_LABEL)