"""
Main Task Parser

Orchestrates the parsing of natural language queries into structured task configurations.
Combines LLM-based intent parsing with heuristic parameter extraction.
"""

import json
from typing import Dict, Optional, List
import google.generativeai as genai
from dotenv import load_dotenv

from .app_config import APP_MAPPINGS
from .parameter_extractors import ParameterExtractor
from .task_builder import TaskBuilder

load_dotenv()


class TaskParser:
    """
    Parses natural language queries into structured task configurations
    """
    
    def __init__(self, gemini_api_key: str):
        """
        Initialize task parser with Gemini API
        
        Args:
            gemini_api_key: Gemini API key
        """
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        print("✅ Task Parser initialized with Gemini")
    
    def parse_query(self, query: str) -> Dict:
        """
        Parse natural language query into task configuration
        
        Args:
            query: Natural language query (e.g., "How do I create a project in Linear?")
            
        Returns:
            Task configuration dictionary ready for agent.execute_dynamic_task()
        """
        print(f"\n{'='*70}")
        print(f"🔍 PARSING QUERY")
        print(f"{'='*70}")
        print(f"Query: {query}")
        print(f"{'='*70}\n")
        
        # Extract app from query
        app_info = self._identify_app(query)
        
        if not app_info:
            print("❌ Could not identify app from query")
            print("Available apps: Linear, Notion, Asana")
            return None
        
        print(f"✅ Identified app: {app_info['name'].upper()}")
        
        # Use Gemini to parse the query intent
        task_intent = self._parse_intent_with_gemini(query, app_info['name'])

        if not task_intent:
            print("❌ Could not parse task intent")
            return None

        # Augment with heuristic extraction to ensure parameters are captured
        task_intent = self._augment_intent_with_heuristics(
            task_intent=task_intent,
            query=query,
            app=app_info['name']
        )

        # Reconcile intent so project-centric queries stay in project workflow
        task_intent = TaskBuilder.enforce_project_intent(
            task_intent=task_intent,
            query=query,
            app=app_info['name']
        )
        
        print(f"✅ Parsed intent:")
        print(f"   Goal: {task_intent['goal']}")
        print(f"   Action: {task_intent['action']}")
        print(f"   Object: {task_intent['object']}")
        
        # Build task configuration
        task_config = TaskBuilder.build_task_config(task_intent, app_info, query)
        
        print(f"\n✅ Task configuration generated:")
        print(f"   Task ID: {task_config['task_id']}")
        print(f"   Start URL: {task_config['start_url']}")
        print(f"   Max steps: {task_config['max_steps']}")
        print(f"{'='*70}\n")
        
        return task_config
    
    def _identify_app(self, query: str) -> Optional[Dict]:
        """
        Identify which app the query is about
        
        Args:
            query: Natural language query
            
        Returns:
            App info dictionary or None
        """
        query_lower = query.lower()
        
        # Check each app's keywords
        for app_name, app_info in APP_MAPPINGS.items():
            for keyword in app_info['keywords']:
                if keyword in query_lower:
                    return app_info
        
        return None
    
    def _parse_intent_with_gemini(self, query: str, app: str) -> Optional[Dict]:
        """
        Use Gemini to parse the user's intent from the query
        
        Args:
            query: Natural language query
            app: Identified app name
            
        Returns:
            Intent dictionary with goal, action, object, parameters, etc.
        """
        prompt = f"""Parse this query for web automation:
Query: "{query}"
App: {app}

Extract: ACTION, OBJECT, GOAL, task_name, description, expected_steps, success_criteria, parameters.
For multi-task: detect QUANTITY/SERIES and set is_multi_task: true.

JSON format:
SINGLE: {{"action": "create", "object": "project", "goal": "Create project 'X' in {app}", "task_name": "Create Project", "description": "Navigate and create project", "expected_steps": 7, "success_criteria": ["Project appears"], "parameters": {{"project_name": "X"}}, "is_multi_task": false}}

MULTI: {{"action": "create", "object": "project", "goal": "Create N projects in {app}", "task_name": "Create Projects", "description": "Navigate and create multiple projects", "expected_steps": "N*7", "success_criteria": ["All projects appear"], "parameters": {{"count": N, "names": ["X", "Y"]}}, "is_multi_task": true}}

Rules: Quantity → multi-task. Single names → project_name. Lists → names. Output JSON only."""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text
            
            # Parse JSON
            intent = json.loads(json_str)
            
            # Ensure parameters field exists
            if "parameters" not in intent:
                intent["parameters"] = {}
            
            # Ensure is_multi_task field exists
            if "is_multi_task" not in intent:
                intent["is_multi_task"] = False
            
            return intent
            
        except Exception as e:
            print(f"⚠️ Error parsing intent with Gemini: {e}")
            
            # Fallback: basic parsing
            return TaskBuilder.build_fallback_intent(query, app)

    def _augment_intent_with_heuristics(self, task_intent: Dict, query: str, app: str) -> Dict:
        """
        Combine LLM intent with heuristic extraction to ensure parameters are captured.
        
        Args:
            task_intent: Intent parsed by Gemini (may be missing parameters)
            query: Original natural language query
            app: Target application name
        
        Returns:
            Augmented intent dictionary
        """
        # Ensure required keys exist
        task_intent.setdefault("parameters", {})
        task_intent.setdefault("is_multi_task", False)
        
        # Use fallback parser to extract structured parameters
        heuristic_intent = TaskBuilder.build_fallback_intent(query, app)
        if not heuristic_intent:
            return task_intent
        
        heuristic_params = heuristic_intent.get("parameters", {}) or {}
        params = task_intent.get("parameters", {}) or {}
        
        # Merge parameters using the extractor utility
        params = ParameterExtractor.merge_parameters(params, heuristic_params)
        
        # Determine multi-task flag
        is_multi = ParameterExtractor.determine_multi_task_flag(
            params, 
            heuristic_intent.get("is_multi_task", False)
        )
        task_intent["is_multi_task"] = is_multi
        
        # Merge additional structured parameters (status, dates, etc.)
        additional_params = ParameterExtractor.extract_additional_parameters(query)
        for key, value in additional_params.items():
            if key not in params:
                params[key] = value
        
        # Normalize synonymous fields
        params = ParameterExtractor.normalize_parameter_synonyms(params)

        # Persist merged parameters
        task_intent["parameters"] = params
        
        return task_intent

    def validate_task_config(self, task_config: Dict) -> bool:
        """
        Validate that a task config has all required fields
        
        Args:
            task_config: Task configuration dictionary
            
        Returns:
            True if valid, False otherwise
        """
        return TaskBuilder.validate_task_config(task_config)
    
    def expand_multi_task(self, task_config: Dict) -> List[Dict]:
        """
        Expand a multi-task configuration into individual task configurations
        
        Args:
            task_config: Multi-task configuration
            
        Returns:
            List of individual task configurations
        """
        return TaskBuilder.expand_multi_task(task_config)