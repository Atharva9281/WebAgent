"""
App Configuration and Constants

Contains application mappings, known task types, and configuration constants
used throughout the task parsing system.
"""

# Known app mappings (extensible)
APP_MAPPINGS = {
    "linear": {
        "name": "linear",
        "url": "https://linear.app",
        "session_file": "auth/linear_session.json",
        "keywords": ["linear", "linear.app"]
    },
    "notion": {
        "name": "notion",
        "url": "https://www.notion.so",
        "session_file": "auth/notion_session.json",
        "keywords": ["notion", "notion.so"]
    },
    "asana": {
        "name": "asana",
        "url": "https://app.asana.com",
        "session_file": "auth/asana_session.json",
        "keywords": ["asana", "asana.com"]
    }
}

# Linear task types and objects
LINEAR_TASK_TYPES = {
    "create": ["project", "issue", "ticket", "milestone", "label"],
    "edit": ["project", "issue", "ticket", "milestone", "label"],
    "delete": ["project", "issue", "ticket", "milestone", "label"],
    "filter": ["issue", "ticket", "project"],
    "search": ["issue", "ticket", "project"],
    "navigate": ["dashboard", "project", "issue"]
}

# Notion task types and objects
NOTION_TASK_TYPES = {
    "create": ["page", "database", "table", "block", "template"],
    "edit": ["page", "database", "table", "block", "property"],
    "delete": ["page", "database", "table", "block"],
    "filter": ["database", "table", "page"],
    "search": ["page", "database", "content"],
    "navigate": ["workspace", "page", "database"]
}

# Asana task types and objects
ASANA_TASK_TYPES = {
    "create": ["project", "task", "team", "goal", "portfolio"],
    "edit": ["project", "task", "team", "goal"],
    "delete": ["project", "task", "team"],
    "filter": ["task", "project"],
    "search": ["task", "project", "team"],
    "navigate": ["dashboard", "project", "task"]
}

# Common action keywords
ACTION_KEYWORDS = {
    "create": ["create", "add", "new", "make"],
    "edit": ["edit", "modify", "change", "update"],
    "delete": ["delete", "remove", "trash"],
    "filter": ["filter", "search", "find", "query"],
    "navigate": ["navigate", "go", "open", "view", "show"]
}

# Common object keywords
OBJECT_KEYWORDS = {
    "project": ["project", "workspace"],
    "issue": ["issue", "ticket", "bug"],
    "page": ["page", "document", "note"],
    "database": ["database", "table", "collection"],
    "task": ["task", "todo", "item"]
}

# Status normalization mapping
STATUS_MAPPINGS = {
    "inprogress": "In Progress",
    "in progress": "In Progress",
    "progress": "In Progress",
    "in-progress": "In Progress",
    "inprogrss": "In Progress",
    "backlog": "Backlog",
    "todo": "Todo",
    "done": "Done",
    "completed": "Completed",
    "canceled": "Canceled",
    "cancelled": "Cancelled"
}

# Instruction keywords that should be filtered from names
INSTRUCTION_KEYWORDS = {
    "change", "set", "update", "switch", "make", "turn", "modify",
    "add", "include", "write", "provide", "generate", "create"
}

# Default configuration values
DEFAULT_CONFIG = {
    "max_steps": 20,
    "expected_steps": 10,
    "captures_non_url_states": True,
    "timeout": 30
}

# Multi-task detection patterns
QUANTITY_PATTERNS = [
    r'(\d+)\s+{obj}s?',  # "3 projects", "5 issues"
    r'create\s+(\d+)',   # "create 5"
    r'add\s+(\d+)',      # "add 3"
    r'make\s+(\d+)'      # "make 4"
]

# Name extraction patterns
NAME_PATTERNS = [
    r'named?\s+(?:as\s+)?["\']?([^"\']+)["\']?',
    r'called\s+["\']?([^"\']+)["\']?',
    r'titled?\s+["\']?([^"\']+)["\']?',
    r'with\s+titles?\s+([^"\']+)',
    r'labels?\s+["\']?([^"\']+)["\']?'
]

# Status extraction patterns
STATUS_PATTERNS = [
    r'(?:status|backlog|workflow)[^a-zA-Z0-9]+(?:modal\s+)?(?:to|as|set to)\s+([a-zA-Z ]+?)(?:,| and|$)',
    r'(?:change|move|set)\s+(?:the\s+)?(?:status|backlog|workflow)[^a-zA-Z0-9]+to\s+([a-zA-Z ]+?)(?:,| and|$)',
    r'backlog(?:\s+progress)?(?:\s+modal)?\s+(?:to|as|set to)\s+([a-zA-Z ]+?)(?:,| and|$)'
]

# Target date extraction patterns
TARGET_DATE_PATTERNS = [
    r'target date\s+(?:to\s+)?([a-zA-Z0-9 ,]+?)(?:,| and|$)',
    r'target\s+(?:to\s+)?([a-zA-Z0-9 ,]+?)(?:,| and|$)',
    r'(?:due date|deadline)\s+(?:to\s+)?([a-zA-Z0-9 ,]+?)(?:,| and|$)'
]

# Priority extraction patterns
PRIORITY_PATTERNS = [
    r'(?:set|change)\s+(?:the\s+)?priority\s+(?:to\s+)?([a-zA-Z ]+?)(?:,| and|$)'
]

# Description extraction patterns
DESCRIPTION_PATTERNS = [
    r'(?:add|include|write|set|provide|generate)\s+(?:a\s+)?description(?:\s+for\s+(?:the\s+)?(?:project|it))?\s*(?:called|named|as|to|of)?\s*["\']([^"\']+)["\']',
    r'description\s+(?:is|should be|to|as)\s+["\']([^"\']+)["\']',
    r'description:\s*([^,\n]+)'
]