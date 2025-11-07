"""
Gemini Client Configuration and Constants.

This module contains all configuration parameters, constants,
and prompt templates used by the GeminiClient.
"""

# Gemini Model Configuration
GEMINI_MODEL_NAME = "gemini-2.0-flash-exp"

# Response parsing constants
SUBMIT_KEYWORDS = ["create", "submit", "save", "add", "confirm", "done", "finish", "publish"]
CANCEL_KEYWORDS = ["cancel", "close", "discard"]

# Maximum number of elements to process for context
MAX_ELEMENTS_FOR_CONTEXT = 40

# Text length limits for response formatting
MAX_TEXT_LENGTH = 50
MAX_ARIA_LENGTH = 40
MAX_HREF_LENGTH = 60
MAX_OBSERVATION_LENGTH = 60

# Action history limits
MAX_HISTORY_STEPS = 5

# Prompt templates and instructions
PROMPT_TEMPLATE = """You are a web automation agent. Your goal: {goal}

Current URL: {current_url}

This screenshot has RED NUMBERED BOXES in the TOP-LEFT corner of interactive elements.

Available interactive elements:
{elements_text}

Previous actions:
{history_text}{parameters_text}{hint_text}

🚨 CRITICAL RULES TO PREVENT LOOPS:
1. DON'T REPEAT YOURSELF
   - If history shows you already typed a value, do NOT type it again.
   - If a field already displays text, move on.
2. NEVER CLICK CANCEL (unless the task explicitly asks).
3. COMPLETE FORMS PROPERLY
   - In a modal, fill required fields, then immediately click Create/Submit/Save.
   - Optional controls (icons, colors) are secondary.
4. MODAL AWARENESS
   - Once a modal is open, stay inside it until you submit it.
   - Do NOT reopen the same modal unless it closed unexpectedly.
5. DETERMINE COMPLETION
   - If the modal closes after submission and the list updates, call finish with a short summary.

AVAILABLE ACTIONS:
1. click [number] - Click the element with that number
2. type [number]; [text] - Type text (use the exact parameter values)
3. scroll down/up - Scroll the page
4. wait - Wait 3 seconds
5. finish; [summary] - Task is complete

DECISION PROCESS (follow carefully):
1. Review RECENT ACTIONS to see what you just did.
2. Inspect the screenshot to confirm what changed.
3. If required fields are filled and there is a submit button, click it.
4. If a required field is empty, fill it once.
5. If the goal is met, respond with finish; <summary>.
6. Otherwise choose the best next step without repeating work.

Output format (single line):
ACTION: <action>

Examples:
- ACTION: click [56]
- ACTION: type [12]; second task
- ACTION: finish; Created project and updated status"""

# Task-specific guidance templates
TASK_GUIDANCE_TEMPLATES = {
    "project_name": "Type the project name field with exactly \"{value}\" before saving.",
    "modal_awareness": "After the creation modal is open, stay inside it (look for 'New project') and avoid clicking the main 'Add project' button again.",
    "status": "Inside the modal, look for the chip labeled \"Backlog\" (the current status) and click it to open the options, then choose the requested value.",
    "priority": "Click the priority chip (e.g., \"No priority\") to open its menu, then select the requested priority.",
    "target_date": "Click the date/target control in the modal and set it to the specified date using the picker.",
    "assignee": "Assign the item to the specified person if an assignee field is available."
}

# Task validation patterns
VALIDATION_PATTERNS = {
    "linear_filter_issues": {
        "url_patterns": ["filter"],
        "title_patterns": ["in progress"],
        "error_message": "Goal: Filter issues to 'In Progress'\nCurrent state: No evidence of filtering applied\nThe agent should apply an actual filter, not just view existing content"
    },
    "linear_create_project": {
        "url_patterns": ["project"],
        "title_patterns": [],
        "error_message": "Goal: Create new project\nCurrent state: Not on a project page"
    },
    "linear_create_issue": {
        "url_patterns": ["issue"],
        "title_patterns": [],
        "error_message": "Goal: Create new issue\nCurrent state: Not on an issue page"
    },
    "notion_create_page": {
        "url_patterns": [],
        "title_patterns": [],
        "min_url_segments": 4,
        "error_message": "Goal: Create new page\nCurrent state: Not on a specific page"
    },
    "notion_create_database": {
        "url_patterns": [],
        "title_patterns": [],
        "min_url_segments": 4,
        "error_message": "Goal: Create new database\nCurrent state: Not on a specific database page"
    }
}

# Debug logging configuration
DEBUG_LOG_FILE = "debug_early_finish.log"
DEBUG_LOG_SEPARATOR = "-" * 80