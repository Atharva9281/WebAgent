"""
SubGoal Manager Package

This package contains modules for managing sub-goals in task automation:
- element_finders: Functions to find UI elements
- goal_checkers: Functions to check goal completion status
- action_guides: Functions to guide actions based on pending goals
- manager: Main SubGoalManager class
"""

from .manager import SubGoalManager

__all__ = ['SubGoalManager']