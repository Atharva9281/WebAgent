"""
Shared CLI helpers for Agent B variants.
"""

from __future__ import annotations

from typing import Iterable, Optional

from agent import AgentBase
from task_definitions import TASKS


def print_launch_banner(title: str, mode_line: Optional[str] = None) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    if mode_line:
        print(mode_line)
        print("=" * 70)


def handle_query(agent: AgentBase, query: str, *, success_prefix: str = "") -> None:
    result = agent.handle_query(query)

    if result.get("success"):
        print("\n✅ Query handled successfully!")
        if result.get("is_multi_task"):
            print(
                f"{success_prefix}Multi-task: {result.get('successful_tasks', 0)}/"
                f"{result.get('total_tasks', 0)} completed"
            )
            print(f"{success_prefix}Summary: {result.get('summary', 'N/A')}")
            print(f"{success_prefix}Datasets: Multiple dataset directories created")
        else:
            dataset = result.get("task_id", "unknown")
            print(f"{success_prefix}Dataset: dataset/{dataset}/")
    else:
        print("\n⚠️  Query did not complete")
        if "error" in result:
            print(f"   Error: {result['error']}")
        elif result.get("is_multi_task"):
            print(
                f"   Multi-task: {result.get('successful_tasks', 0)}/"
                f"{result.get('total_tasks', 0)} completed"
            )
            print(f"   {result.get('failed_tasks', 0)} tasks failed")


def handle_task(agent: AgentBase, task_id: str, *, header_prefix: str = "") -> None:
    print(f"\n🎯 PREDEFINED TASK MODE\nTask ID: {task_id}\n" + "=" * 70 + "\n")
    result = agent.execute_task(task_id)
    if result.get("success"):
        print(f"\n✅ {header_prefix}Task completed successfully!")
    else:
        print(f"\n⚠️  {header_prefix}Task did not complete")
        if "error" in result:
            print(f"   Error: {result['error']}")


def handle_batch(
    agent: AgentBase,
    *,
    header_prefix: str = "",
    continue_prompt: str = "Press ENTER to continue to next task...",
) -> None:
    print("\n🚀 BATCH MODE - Running all predefined tasks...\n" + "=" * 70 + "\n")
    for index, task in enumerate(TASKS, start=1):
        print(f"\n[{index}/{len(TASKS)}] Starting: {task['name']}")
        result = agent.execute_task(task["task_id"])
        status = "✅ Completed" if result.get("success") else "⚠️  Failed"
        print(f"{status}: {header_prefix}{task['name']}")
        if index < len(TASKS):
            print("\n" + "=" * 70)
            input(continue_prompt)
    print(f"\n✅ {header_prefix}Batch execution finished.")


def interactive_menu(
    agent: AgentBase,
    *,
    menu_title: str = "📋 INTERACTIVE MODE",
    query_mode_title: str = "🗣️  NATURAL LANGUAGE MODE",
    query_examples: Optional[Iterable[str]] = None,
    multi_examples: Optional[Iterable[str]] = None,
    variant_notice: Optional[str] = None,
    success_prefix: str = "",
) -> None:
    print("\n" + "=" * 70)
    print(menu_title)
    print("=" * 70)
    print("\n1. NATURAL LANGUAGE QUERY")
    print("   Enter a query like: 'How do I create a project in Linear?'")
    print("\n2. PREDEFINED TASK")
    print("   Choose from existing task definitions")
    print("\n3. BATCH ALL TASKS")
    print("   Run all predefined tasks")
    print("\n" + "=" * 70)

    choice = input("\nChoose mode (1/2/3): ").strip()

    if choice == "1":
        print("\n" + "=" * 70)
        print(query_mode_title)
        print("=" * 70)
        if variant_notice:
            print(variant_notice)
        if query_examples:
            print("\nExample queries:")
            for example in query_examples:
                print(f"  {example}")
        if multi_examples:
            print("  MULTI-TASKS (any quantity):")
            for example in multi_examples:
                print(f"  - {example}")
        print("\n" + "=" * 70)

        query = input("\nEnter your query: ").strip()
        if not query:
            print("❌ No query entered")
            return
        handle_query(agent, query, success_prefix=success_prefix)

    elif choice == "2":
        print("\n" + "=" * 70)
        print("📋 PREDEFINED TASKS")
        print("=" * 70)

        for index, task in enumerate(TASKS, start=1):
            print(f"\n{index}. {task['task_id']}")
            print(f"   App: {task['app'].upper()}")
            print(f"   Goal: {task['goal']}")

        print("\n" + "=" * 70)
        selection = input("\nEnter task number or task_id: ").strip()

        try:
            task_index = int(selection)
        except ValueError:
            task_id = selection
        else:
            if 1 <= task_index <= len(TASKS):
                task_id = TASKS[task_index - 1]["task_id"]
            else:
                print(f"❌ Invalid task number. Choose 1-{len(TASKS)}")
                return

        handle_task(agent, task_id, header_prefix=success_prefix)

    elif choice == "3":
        handle_batch(agent, header_prefix=success_prefix)

    else:
        print("❌ Invalid mode selected")
