"""
Printing and display helpers for AgentBase.

This module contains all the printing and display methods used by AgentBase.
"""

from typing import Dict, List
from pathlib import Path


def print_initialisation_summary(mode_name: str, intro_lines: List[str]) -> None:
    print(f"✅ {mode_name} initialised")
    for line in intro_lines:
        print(f"   {line}")
    print(f"   Task Parser: Ready")


def print_query_header(query: str, header_title: str, header_extra: List[str]) -> None:
    print("\n" + "=" * 70)
    print(header_title)
    print("=" * 70)
    print(f"Query: {query}")
    for line in header_extra:
        print(line)
    print("=" * 70 + "\n")


def print_multi_task_header(task_config: Dict, header_title: str, extra_lines: List[str]) -> None:
    print("\n" + "=" * 70)
    print(header_title)
    print("=" * 70)
    for line in extra_lines:
        print(line)
    print(f"Count: {task_config.get('parameters', {}).get('count', 1)}")
    print(f"Names: {task_config.get('parameters', {}).get('names', [])}")
    print("=" * 70 + "\n")


def print_expanded_task_list(tasks: List[Dict]) -> None:
    print(f"📋 Expanded into {len(tasks)} individual tasks:")
    for index, task in enumerate(tasks, start=1):
        print(f"   {index}. {task['name']}")
    print()


def print_multi_task_progress(index: int, total: int) -> None:
    print("\n" + "=" * 70)
    print(f"🚀 EXECUTING TASK {index}/{total}")
    print("=" * 70)


def print_multi_task_pause(index: int) -> None:
    print(f"\n✅ Task {index} completed. Continuing to next task...")


def print_single_task_header(task_config: Dict, header_title: str, extra_lines: List[str]) -> None:
    print("\n" + "=" * 70)
    print(f"{header_title}: {task_config['name']}")
    print("=" * 70)
    print(f"Goal: {task_config['goal']}")
    print(f"App: {task_config['app'].upper()}")
    print(f"Start URL: {task_config['start_url']}")
    print(f"Max steps: {task_config['max_steps']}")
    for line in extra_lines:
        print(line)
    print("=" * 70 + "\n")


def print_predefined_task_header(task_config: Dict, header_title: str, extra_lines: List[str]) -> None:
    print("\n" + "=" * 70)
    print(f"{header_title}: {task_config['name']}")
    print("=" * 70)
    print(f"Goal: {task_config['goal']}")
    print(f"App: {task_config['app'].upper()}")
    print(f"Start URL: {task_config['start_url']}")
    print(f"Max steps: {task_config['max_steps']}")
    for line in extra_lines:
        print(line)
    print("=" * 70 + "\n")


def print_step_header(step_num: int, max_steps: int) -> None:
    print("\n" + "─" * 70)
    print(f"📸 STEP {step_num}/{max_steps}")
    print("─" * 70)


def print_action_info(action: Dict) -> None:
    print(f"   🤖 Action: {action['action']}")
    if action.get("element_id") is not None:
        print(f"   🎯 Element: [{action['element_id']}]")
    if action.get("text"):
        print(f"   ✍️  Text: '{action['text'][:50]}...'")
    if action.get("reasoning"):
        print(f"   💭 Reasoning: {action['reasoning']}")


def print_task_summary(metadata: Dict, dataset_dir: Path) -> None:
    print("\n" + "=" * 70)
    if metadata.get("success"):
        print("✅ TASK COMPLETED SUCCESSFULLY")
    else:
        print("⚠️  TASK INCOMPLETE")
    print("=" * 70)
    print(f"Total steps: {metadata.get('total_steps', 0)}")
    print(f"Dataset saved: {dataset_dir}")
    print("=" * 70 + "\n")


def list_predefined_tasks(script_name: str = "agent.py") -> None:
    """Utility helper for CLI modes."""
    from task_definitions import TASKS
    
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