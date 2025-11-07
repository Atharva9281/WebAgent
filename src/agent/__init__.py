"""
Agent module for web automation.

Exports the main AgentBase class for building automation agents.
"""

from .base import AgentBase, list_predefined_tasks

__all__ = ["AgentBase", "list_predefined_tasks"]