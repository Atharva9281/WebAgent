"""
Agent B - Standard Web Automation Agent.

This entrypoint now delegates the shared orchestration flow to AgentBase,
keeping this file focused on CLI wiring and persona-specific logging.
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from agent_base import AgentBase, list_predefined_tasks
from agent_cli import (
    handle_batch,
    handle_query,
    handle_task,
    interactive_menu,
    print_launch_banner,
)
from browser_controller import BrowserController


class AgentB(AgentBase):
    """Standard Agent B implementation using the annotated browser controller."""

    BROWSER_CONTROLLER_CLS = BrowserController

    MODE_NAME = "AGENT B - WEB AUTOMATION AGENT"
    MODE_INTRO_LINES = [
        "Components: BrowserController + GeminiClient + StateDetector",
        "Mode: RUNTIME FLEXIBLE",
    ]

    QUERY_HEADER_TITLE = "🤖 AGENT B - HANDLING RUNTIME QUERY"
    MULTI_TASK_HEADER_TITLE = "🔥 MULTI-TASK DETECTED"
    SINGLE_TASK_HEADER_TITLE = "🚀 STARTING DYNAMIC TASK"
    PREDEFINED_TASK_HEADER_TITLE = "🚀 STARTING TASK"

    def _capture_annotation(self):
        return self.browser.annotate_and_capture()


def _build_agent() -> AgentB:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ Error: GEMINI_API_KEY not found in .env file")
        print("   Please add your API key to .env")
        print("   Get key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    return AgentB(gemini_api_key=api_key)


def main() -> None:
    print_launch_banner("🤖 AGENT B - WEB AUTOMATION AGENT", "Mode: RUNTIME FLEXIBLE")
    agent = _build_agent()

    parser = argparse.ArgumentParser(
        description="Agent B - Web Automation Agent with Runtime Flexibility"
    )
    parser.add_argument("query", nargs="?", help="Natural language query to execute")
    parser.add_argument("--task", help="Execute a predefined task by ID")
    parser.add_argument("--all", action="store_true", help="Run all predefined tasks")
    parser.add_argument("--list", action="store_true", help="List predefined tasks")
    args = parser.parse_args()

    if args.list:
        list_predefined_tasks("agent.py")
        return

    if args.all:
        handle_batch(agent)
        return

    if args.task:
        handle_task(agent, args.task)
        return

    if args.query:
        print(f"\n🗣️  NATURAL LANGUAGE MODE (CLI)\nQuery: {args.query}\n" + "=" * 70 + "\n")
        handle_query(agent, args.query)
        return

    interactive_menu(
        agent,
        menu_title="📋 INTERACTIVE MODE",
        query_mode_title="🗣️  NATURAL LANGUAGE MODE",
        query_examples=[
            "SINGLE TASKS:",
            "- How do I create a project in Linear?",
            "- Show me how to filter issues in Linear",
            "- How do I create a page in Notion?",
        ],
        multi_examples=[
            "Create [N] projects with titles [name1, name2, ...]",
            "Create [N] issues called [pattern] 1 through [N]",
            "Create pages titled [any names you want]",
        ],
    )


if __name__ == "__main__":
    main()
