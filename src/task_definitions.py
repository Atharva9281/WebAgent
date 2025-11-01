"""
Task Definitions

Defines the 5 tasks that Agent B will execute:
- 3 Linear tasks
- 2 Notion tasks

Each task specifies:
- Task name/ID
- Application (linear or notion)
- Goal description
- Start URL
- Expected number of steps
- Success criteria
"""

from typing import List, Dict

# Task configurations
TASKS: List[Dict] = [
    # ==================== LINEAR TASKS ====================
    {
        "task_id": "linear_create_project",
        "app": "linear",
        "name": "Create Project in Linear",
        "goal": "Create a new project named 'AI Agent Demo Project'",
        "description": "Navigate to Linear and create a new project with the name 'AI Agent Demo Project'",
        "start_url": "https://linear.app",
        "expected_steps": 7,
        "max_steps": 15,
        "success_criteria": [
            "Project appears in project list",
            "Project name is 'AI Agent Demo Project'"
        ],
        "captures_non_url_states": True,
        "non_url_states": [
            "Modal dialog opening (same URL)",
            "Form fields becoming visible (same URL)",
            "Form being filled (same URL)",
            "Loading/submission state (same URL)"
        ],
        "notes": "This task demonstrates capturing modal state without URL change"
    },
    {
        "task_id": "linear_create_issue",
        "app": "linear",
        "name": "Create Issue in Linear",
        "goal": "Create a new issue titled 'Test Issue from Agent' and assign it to a team",
        "description": "Navigate to Linear issues and create a new issue with title 'Test Issue from Agent'",
        "start_url": "https://linear.app",
        "expected_steps": 8,
        "max_steps": 15,
        "success_criteria": [
            "Issue appears in issues list",
            "Issue title is 'Test Issue from Agent'"
        ],
        "captures_non_url_states": True,
        "non_url_states": [
            "Issue creation dialog (same URL)",
            "Title input field (same URL)",
            "Team dropdown menu (same URL)",
            "Team selection (same URL)"
        ],
        "notes": "Demonstrates capturing dropdown states and form interactions"
    },
    {
        "task_id": "linear_filter_issues",
        "app": "linear",
        "name": "Filter Issues in Linear",
        "goal": "Filter the issues list to show only issues with 'In Progress' status",
        "description": "Navigate to Linear issues page and apply filter to show only 'In Progress' issues",
        "start_url": "https://linear.app/issues",
        "expected_steps": 5,
        "max_steps": 10,
        "success_criteria": [
            "Filter is applied",
            "Only 'In Progress' issues are visible"
        ],
        "captures_non_url_states": True,
        "non_url_states": [
            "Filter dropdown opening (same URL)",
            "Status selection menu (same URL)",
            "Filtered list updating (same URL)"
        ],
        "notes": "Demonstrates capturing filter/dropdown interactions"
    },
    
    # ==================== NOTION TASKS ====================
    {
        "task_id": "notion_create_page",
        "app": "notion",
        "name": "Create Page in Notion",
        "goal": "Create a new page titled 'Agent Test Page' with some content",
        "description": "Navigate to Notion and create a new page with title 'Agent Test Page' and add a paragraph of text",
        "start_url": "https://www.notion.so",
        "expected_steps": 6,
        "max_steps": 12,
        "success_criteria": [
            "Page appears in sidebar",
            "Page title is 'Agent Test Page'",
            "Page has content"
        ],
        "captures_non_url_states": True,
        "non_url_states": [
            "Page creation menu (same URL initially)",
            "Title editor (same URL initially)",
            "Content blocks (same URL initially)"
        ],
        "notes": "Demonstrates capturing content editor states"
    },
    {
        "task_id": "notion_create_database",
        "app": "notion",
        "name": "Create Database in Notion",
        "goal": "Create a table database named 'Test Database' and add one entry",
        "description": "Navigate to Notion and create a new table database with name 'Test Database', then add one row with data",
        "start_url": "https://www.notion.so",
        "expected_steps": 9,
        "max_steps": 15,
        "success_criteria": [
            "Database is created",
            "Database name is 'Test Database'",
            "Database has at least one entry"
        ],
        "captures_non_url_states": True,
        "non_url_states": [
            "Database type selector (same URL)",
            "Table view editor (same URL)",
            "Column editor (same URL)",
            "Row inline editor (same URL)",
            "Cell editing state (same URL)"
        ],
        "notes": "Demonstrates capturing complex database editor states"
    }
]


def get_task_by_id(task_id: str) -> Dict:
    """
    Get a task configuration by its ID
    
    Args:
        task_id: The task identifier (e.g., "linear_create_project")
        
    Returns:
        Task configuration dictionary
        
    Raises:
        ValueError: If task_id not found
    """
    for task in TASKS:
        if task["task_id"] == task_id:
            return task
    
    raise ValueError(f"Task not found: {task_id}")


def get_tasks_by_app(app: str) -> List[Dict]:
    """
    Get all tasks for a specific application
    
    Args:
        app: Application name ("linear" or "notion")
        
    Returns:
        List of task configurations for that app
    """
    return [task for task in TASKS if task["app"] == app]


def list_all_tasks() -> List[str]:
    """
    Get list of all task IDs
    
    Returns:
        List of task ID strings
    """
    return [task["task_id"] for task in TASKS]


def get_session_file(app: str) -> str:
    """
    Get the auth session file path for an app
    
    Args:
        app: Application name ("linear" or "notion")
        
    Returns:
        Path to session file
    """
    return f"auth/{app}_session.json"


def validate_task_config(task: Dict) -> bool:
    """
    Validate that a task configuration has all required fields
    
    Args:
        task: Task configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "task_id",
        "app",
        "name",
        "goal",
        "start_url",
        "max_steps"
    ]
    
    for field in required_fields:
        if field not in task:
            print(f"Missing required field: {field}")
            return False
    
    return True


# Validate all tasks on import
def _validate_all_tasks():
    """Validate all task configurations"""
    for task in TASKS:
        if not validate_task_config(task):
            raise ValueError(f"Invalid task configuration: {task.get('task_id', 'unknown')}")

_validate_all_tasks()


# Summary statistics
TOTAL_TASKS = len(TASKS)
LINEAR_TASKS = len([t for t in TASKS if t["app"] == "linear"])
NOTION_TASKS = len([t for t in TASKS if t["app"] == "notion"])


# Example usage and module info
if __name__ == "__main__":
    print("=" * 70)
    print("TASK DEFINITIONS MODULE")
    print("=" * 70)
    print(f"\nTotal tasks: {TOTAL_TASKS}")
    print(f"Linear tasks: {LINEAR_TASKS}")
    print(f"Notion tasks: {NOTION_TASKS}")
    
    print("\n" + "-" * 70)
    print("AVAILABLE TASKS:")
    print("-" * 70)
    
    for task in TASKS:
        print(f"\n📋 {task['task_id']}")
        print(f"   App: {task['app'].upper()}")
        print(f"   Goal: {task['goal']}")
        print(f"   Expected steps: {task['expected_steps']}")
        print(f"   Non-URL states: {len(task['non_url_states'])}")
    
    print("\n" + "=" * 70)
    print("\nUsage in agent.py:")
    print("  from task_definitions import get_task_by_id, TASKS")
    print("  task = get_task_by_id('linear_create_project')")
    print("=" * 70)