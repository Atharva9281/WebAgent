"""
Agent B - Clean Web Automation Agent.

This variant reuses the shared AgentBase flow while switching to the clean
browser controller so the user never sees annotation overlays.
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
from browser_controller_clean import CleanBrowserController


class CleanAgentB(AgentBase):
    """Agent B variant that keeps the visible browser pristine."""

    BROWSER_CONTROLLER_CLS = CleanBrowserController

    MODE_NAME = "CLEAN AGENT B - WEB AUTOMATION AGENT"
    MODE_INTRO_LINES = [
        "Components: CleanBrowserController + GeminiClient + StateDetector",
        "🎨 Image annotation via off-screen rendering (no DOM overlays)",
        "👀 User experience: Clean browser throughout automation",
    ]

    QUERY_HEADER_TITLE = "🤖 CLEAN AGENT B - HANDLING RUNTIME QUERY"
    MULTI_TASK_HEADER_TITLE = "🔥 MULTI-TASK DETECTED (CLEAN)"
    SINGLE_TASK_HEADER_TITLE = "🚀 STARTING DYNAMIC TASK (CLEAN)"
    PREDEFINED_TASK_HEADER_TITLE = "🚀 STARTING TASK (CLEAN)"

    DATASET_DYNAMIC_SUFFIX = "_clean"
    DATASET_PREDEFINED_SUFFIX = "_clean"

    def _capture_annotation(self):
        return self.browser.annotate_and_capture_clean()


def _build_agent() -> CleanAgentB:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ Error: GEMINI_API_KEY not found in .env file")
        print("   Please add your API key to .env")
        print("   Get key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    return CleanAgentB(gemini_api_key=api_key)


def main() -> None:
    print_launch_banner("🤖 CLEAN AGENT B - WEB AUTOMATION AGENT", "Mode: CLEAN UI")
    agent = _build_agent()

    parser = argparse.ArgumentParser(
        description="Clean Agent B - Web Automation Agent with Runtime Flexibility"
    )
    parser.add_argument("query", nargs="?", help="Natural language query to execute")
    parser.add_argument("--task", help="Execute a predefined task by ID")
    parser.add_argument("--all", action="store_true", help="Run all predefined tasks")
    parser.add_argument("--list", action="store_true", help="List predefined tasks")
    args = parser.parse_args()

    if args.list:
        list_predefined_tasks("agent_clean.py")
        return

    if args.all:
        handle_batch(
            agent,
            header_prefix="Clean ",
            continue_prompt="Press ENTER to continue to next clean task...",
        )
        return

    if args.task:
        handle_task(agent, args.task, header_prefix="Clean ")
        return

    if args.query:
        print(
            f"\n🗣️  NATURAL LANGUAGE MODE (CLEAN CLI)\nQuery: {args.query}\n"
            + "=" * 70
            + "\n"
        )
        handle_query(agent, args.query, success_prefix="🎨 ")
        return

    interactive_menu(
        agent,
        menu_title="📋 INTERACTIVE MODE (CLEAN)",
        query_mode_title="🗣️  NATURAL LANGUAGE MODE (CLEAN)",
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
        variant_notice="🎨 Mode: Clean UI (no bounding boxes shown to user)",
        success_prefix="🎨 ",
    )


if __name__ == "__main__":
    main()
