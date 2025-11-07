"""
Task Parser Module

A modular natural language task parser that converts runtime queries
into executable task configurations for web automation.

This module provides:
- TaskParser: Main orchestration class for parsing queries
- App configuration and constants
- Parameter extraction utilities
- Task building logic

Usage:
    from parser import TaskParser
    
    parser = TaskParser(gemini_api_key="your_key")
    task_config = parser.parse_query("Create a project in Linear")
"""

from .parser import TaskParser
from .app_config import APP_MAPPINGS, DEFAULT_CONFIG
from .parameter_extractors import ParameterExtractor
from .task_builder import TaskBuilder

__all__ = [
    'TaskParser',
    'APP_MAPPINGS', 
    'DEFAULT_CONFIG',
    'ParameterExtractor',
    'TaskBuilder'
]

__version__ = '1.0.0'