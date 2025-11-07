"""
Task execution logic for AgentBase.

This module contains the core task execution loop and step processing logic.
"""

import time
import sys
from typing import Dict, List
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from detector import get_complete_ui_state, describe_ui_state
from .helpers import (
    build_transition_metadata, 
    build_submit_hint, 
    enrich_action_details, 
    save_step_metadata,
    save_error_screenshot
)
from .printing import (
    print_step_header, 
    print_action_info, 
    print_multi_task_header, 
    print_expanded_task_list, 
    print_multi_task_progress, 
    print_multi_task_pause
)


def execute_task_loop(
    agent_instance, 
    task_config: Dict, 
    dataset_dir: Path, 
    metadata: Dict
) -> bool:
    """Execute the main task loop."""
    max_steps = task_config["max_steps"]
    goal = task_config["goal"]

    consecutive_failures = 0
    max_failures = 3

    for step_num in range(1, max_steps + 1):
        print_step_header(step_num, max_steps)

        try:
            outcome = execute_single_step(
                agent_instance=agent_instance,
                step_num=step_num,
                goal=goal,
                task_config=task_config,
                dataset_dir=dataset_dir,
                metadata=metadata,
            )

            if outcome == "completed":
                print("\n🎉 Task marked as complete by agent!")
                print(agent_instance.FINISH_SUCCESS_MESSAGE)
                return True

            if outcome == "failed":
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print(f"\n⚠️  Too many consecutive failures ({max_failures})")
                    print("   Stopping task execution")
                    return False
            else:
                consecutive_failures = 0

            time.sleep(agent_instance.STEP_WAIT_BETWEEN_SECONDS)

        except Exception as err:  # pragma: no cover - defensive logging
            print(f"\n❌ Step {step_num} failed: {err}")
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                print(f"\n⚠️  Too many consecutive failures ({max_failures})")
                return False
            save_error_screenshot(dataset_dir, step_num, agent_instance.browser.page)

    print(f"\n⚠️  Reached maximum steps ({max_steps})")
    return False


def execute_single_step(
    agent_instance,
    step_num: int,
    goal: str,
    task_config: Dict,
    dataset_dir: Path,
    metadata: Dict,
) -> str:
    """Execute a single step of the task."""
    print(f"1️⃣  {agent_instance.STEP_ANNOTATE_LABEL}")
    annotation_result = agent_instance._capture_annotation()

    if not annotation_result["bboxes"]:
        print("⚠️  No interactive elements found - might be loading")
        time.sleep(2)
        return "continue"

    screenshot_filename = f"step_{step_num:02d}.png"
    screenshot_path = dataset_dir / screenshot_filename

    with open(screenshot_path, "wb") as handle:
        handle.write(annotation_result["screenshot"])

    print(f"2️⃣  {agent_instance.STEP_SCREENSHOT_LABEL}: {screenshot_filename}")

    print("3️⃣  Detecting UI state...")
    ui_state = get_complete_ui_state(agent_instance.browser.page)
    description = describe_ui_state(ui_state)
    print(f"   {description}")
    transition = build_transition_metadata(step_num, ui_state, agent_instance.previous_step_state)

    if agent_instance.subgoal_manager:
        agent_instance.subgoal_manager.update(ui_state, annotation_result["bboxes"])

    submit_hint = build_submit_hint(ui_state, annotation_result["bboxes"])

    combined_hint = None
    if agent_instance.subgoal_manager:
        combined_hint = agent_instance.subgoal_manager.build_hint(submit_hint, ui_state)
    elif submit_hint:
        combined_hint = submit_hint

    print("4️⃣  Asking Gemini for next action...")
    action = agent_instance.gemini.get_next_action(
        goal=goal,
        screenshot_b64=annotation_result["screenshot_b64"],
        bboxes=annotation_result["bboxes"],
        current_url=agent_instance.browser.get_current_url(),
        action_history=agent_instance.action_history,
        task_parameters=task_config.get("parameters", {}),
        hint=combined_hint,
    )

    enrich_action_details(action, annotation_result["bboxes"])

    if agent_instance.subgoal_manager:
        # Call adjust_action FIRST to handle pending goals (like open_projects)
        action = agent_instance.subgoal_manager.adjust_action(action, ui_state, annotation_result["bboxes"])
        
        # Then block finish if needed
        blocked_reason = agent_instance.subgoal_manager.block_finish_reason(action, ui_state)
        if blocked_reason:
            print(agent_instance.FINISH_BLOCKED_LOG.format(reason=blocked_reason))
            action = {"action": "wait", "reasoning": f"{blocked_reason} - waiting before finishing"}

    print_action_info(action)

    if action["action"] == "finish":
        if agent_instance.gemini.validate_task_completion(
            task_config=task_config,
            current_url=agent_instance.browser.get_current_url(),
            page_title=agent_instance.browser.get_page_title(),
            action=action,
        ):
            save_step_metadata(
                step_num,
                action,
                "Task completed successfully",
                ui_state,
                description,
                screenshot_filename,
                dataset_dir,
                metadata,
                transition,
                agent_instance.browser,
                agent_instance.STEP_METADATA_EXTRA,
            )
            return "completed"

        print("\n❌ Task completion validation failed - continuing...")
        action["action"] = "wait"
        action["reasoning"] = "Task not actually complete - continuing automation"

    print(f"5️⃣  {agent_instance.STEP_EXECUTE_LABEL}")
    observation = agent_instance.browser.execute_action(action, annotation_result["bboxes"])
    print(agent_instance.STEP_ACTION_LOG.format(observation=observation))
    agent_instance._post_action_observation(observation)

    save_step_metadata(
        step_num,
        action,
        observation,
        ui_state,
        description,
        screenshot_filename,
        dataset_dir,
        metadata,
        transition,
        agent_instance.browser,
        agent_instance.STEP_METADATA_EXTRA,
    )

    if agent_instance.subgoal_manager:
        agent_instance.subgoal_manager.record_action(action)

    agent_instance.action_history.append(
        {"step": step_num, "action": action["action"], "observation": observation}
    )
    
    # Update previous step state
    agent_instance.previous_step_state = {
        "step": step_num,
        "url": ui_state.get("url", "") if ui_state else "",
        "page_hash": ui_state.get("page_hash", "") if ui_state else "",
    }
    
    return "continue"


def execute_multi_task(agent_instance, task_config: Dict, original_query: str) -> Dict:
    """Execute multiple tasks in sequence."""
    print_multi_task_header(task_config, agent_instance.MULTI_TASK_HEADER_TITLE, agent_instance.MULTI_TASK_EXTRA_LINES)

    individual_tasks = agent_instance.task_parser.expand_multi_task(task_config)
    print_expanded_task_list(individual_tasks)

    all_results = []
    for index, specific_task in enumerate(individual_tasks, start=1):
        print_multi_task_progress(index, len(individual_tasks))
        result = agent_instance.execute_dynamic_task(specific_task)
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
            print_multi_task_pause(index)
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