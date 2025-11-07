"""
UI State Detection module for web automation.

Exports the main state detection functions for analyzing web page states.
"""

from .detector import (
    get_complete_ui_state,
    describe_ui_state,
    ui_state_changed,
    get_page_hash,
    detect_loading_state,
    get_state_changes
)
from .modal_detector import detect_modals, detect_dropdowns_open
from .form_detector import get_form_states, summarise_forms, analyze_form_completion, get_fillable_fields

__all__ = [
    "get_complete_ui_state",
    "describe_ui_state", 
    "ui_state_changed",
    "get_page_hash",
    "detect_loading_state",
    "get_state_changes",
    "detect_modals",
    "detect_dropdowns_open", 
    "get_form_states",
    "summarise_forms",
    "analyze_form_completion",
    "get_fillable_fields"
]