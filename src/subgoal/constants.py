"""
Constants and configuration for sub-goal management.
"""

# Month synonyms for date parsing
MONTH_SYNONYMS = {
    "january": ["jan", "january"],
    "february": ["feb", "february"],
    "march": ["mar", "march"],
    "april": ["apr", "april"],
    "may": ["may"],
    "june": ["jun", "june"],
    "july": ["jul", "july"],
    "august": ["aug", "august"],
    "september": ["sep", "sept", "september"],
    "october": ["oct", "october"],
    "november": ["nov", "november"],
    "december": ["dec", "december"],
}

# Keywords for optional UI elements that should be ignored
OPTIONAL_CLICK_KEYWORDS = ["icon", "emoji", "avatar", "color", "image"]

# Status values recognized by the system
STATUS_TOKENS = [
    "backlog",
    "todo",
    "to do",
    "in progress",
    "in-progress",
    "inprogress",
    "done",
    "completed",
    "complete",
    "canceled",
    "cancelled",
    "blocked",
]

# Priority values recognized by the system
PRIORITY_TOKENS = [
    "no priority",
    "none",
    "urgent",
    "high",
    "medium",
    "low",
    "critical",
]

# ARIA label keywords for description fields
DESCRIPTION_ARIA_KEYWORDS = ["description", "details", "summary", "notes"]

# Keywords for filter detection
FILTER_KEYWORDS = {
    "filter",
    "filters",
    "filtered",
    "showing",
    "statusis",
    "status:",
    "workflow",
    "state:",
    "project",
}

# Keywords for filter completion detection in clicked elements
FILTER_COMPLETION_KEYWORDS = ["filter", "status", "workflow", "showing", "chip", "project"]
