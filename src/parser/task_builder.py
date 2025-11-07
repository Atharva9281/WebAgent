"""
Task Builder Utilities

Contains task building logic for creating structured task configurations
from parsed intents and parameters.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional
from .app_config import APP_MAPPINGS, ACTION_KEYWORDS, OBJECT_KEYWORDS, DEFAULT_CONFIG


class TaskBuilder:
    """Utility class for building task configurations from parsed intents"""
    
    @staticmethod
    def build_task_config(task_intent: Dict, app_info: Dict, query: str) -> Dict:
        """
        Build complete task configuration from parsed intent and app info
        
        Args:
            task_intent: Parsed intent dictionary
            app_info: App configuration dictionary  
            query: Original query string
            
        Returns:
            Complete task configuration dictionary
        """
        task_config = {
            "task_id": TaskBuilder.generate_task_id(task_intent, app_info['name']),
            "app": app_info['name'],
            "name": task_intent['task_name'],
            "goal": task_intent['goal'],
            "description": task_intent['description'],
            "start_url": app_info['url'],
            "expected_steps": task_intent.get('expected_steps', DEFAULT_CONFIG['expected_steps']),
            "max_steps": DEFAULT_CONFIG['max_steps'],
            "success_criteria": task_intent['success_criteria'],
            "captures_non_url_states": DEFAULT_CONFIG['captures_non_url_states'],
            "parsed_from_query": query,
            "parameters": dict(task_intent.get('parameters', {})),
            "is_multi_task": task_intent.get('is_multi_task', False),
            "action": task_intent['action'],
            "object": task_intent['object']
        }
        
        return task_config

    @staticmethod
    def generate_task_id(intent: Dict, app: str) -> str:
        """
        Generate a unique task ID from intent
        
        Args:
            intent: Intent dictionary
            app: App name
            
        Returns:
            Task ID string
        """
        action = intent['action']
        obj = intent['object']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Clean strings for ID
        action_clean = re.sub(r'[^a-z0-9]', '_', action.lower())
        obj_clean = re.sub(r'[^a-z0-9]', '_', obj.lower())
        
        return f"{app}_{action_clean}_{obj_clean}_{timestamp}"

    @staticmethod
    def build_fallback_intent(query: str, app: str) -> Dict:
        """
        Build fallback intent when LLM parsing fails
        
        Args:
            query: Natural language query
            app: App name
            
        Returns:
            Basic intent dictionary with extracted parameters
        """
        from .parameter_extractors import ParameterExtractor
        
        query_lower = query.lower()
        
        # Detect action
        action = TaskBuilder._detect_action(query_lower)
        
        # Detect object
        obj = TaskBuilder._detect_object(query_lower)
        
        # Extract parameters with multi-task support
        count, extracted_names, is_multi_task = ParameterExtractor.extract_quantity_and_names(query, obj)
        
        parameters = {}
        
        # Set count if multi-task
        if is_multi_task and count > 1:
            parameters["count"] = count
        
        # Set names based on extraction
        if extracted_names:
            if len(extracted_names) > 1:
                is_multi_task = True
                parameters["names"] = extracted_names
                parameters["count"] = len(extracted_names)
            else:
                # Single name - map to appropriate parameter
                name_params = ParameterExtractor.extract_names_by_object_type(extracted_names, obj)
                parameters.update(name_params)
        
        # If we detected count but no names, generate pattern
        if is_multi_task and "names" not in parameters and count > 1:
            name_pattern = ParameterExtractor.generate_name_pattern_if_needed(query, obj, count, bool(extracted_names))
            if name_pattern:
                parameters["names"] = [name_pattern.replace('{i}', str(i)) for i in range(1, count + 1)]
                parameters["name_pattern"] = name_pattern
        
        # Extract additional parameters like status or dates
        additional_params = ParameterExtractor.extract_additional_parameters(query)
        for key, value in additional_params.items():
            if value:
                parameters[key] = value

        # Build goal and description
        if is_multi_task:
            goal = f"{action.title()} {count} {obj}s in {app}"
            description = f"Navigate to {app} and {action} {count} {obj}s"
            expected_steps = 8 * count  # Multiply by count
        else:
            goal = f"{action.title()} {obj} in {app}"
            description = f"Navigate to {app} and {action} a {obj}"
            expected_steps = 8
        
        return {
            "action": action,
            "object": obj,
            "goal": goal,
            "task_name": f"{action.title()} {obj.title()} in {app.title()}",
            "description": description,
            "expected_steps": expected_steps,
            "success_criteria": [
                f"{obj.title()} {action} completed successfully"
            ],
            "parameters": parameters,
            "is_multi_task": is_multi_task
        }

    @staticmethod
    def _detect_action(query_lower: str) -> str:
        """Detect action from query text"""
        for action, keywords in ACTION_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                return action
        return "navigate"

    @staticmethod
    def _detect_object(query_lower: str) -> str:
        """Detect object from query text"""
        for obj, keywords in OBJECT_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                return obj
        return "item"

    @staticmethod
    def enforce_project_intent(task_intent: Dict, query: str, app: str) -> Dict:
        """Ensure project queries stay in project workflow."""
        from .parameter_extractors import ParameterExtractor
        
        query_lower = query.lower()
        mentions_project = "project" in query_lower or "projects" in query_lower
        if not mentions_project:
            return task_intent

        create_keywords = ["create", "add", "new", "make"]
        should_create = any(keyword in query_lower for keyword in create_keywords)

        # Force object/action to project/create when appropriate
        task_intent["object"] = "project"
        if should_create:
            task_intent["action"] = "create"

        params = task_intent.setdefault("parameters", {})
        project_name = (
            params.get("project_name")
            or params.get("name")
            or params.get("title")
        )

        if should_create:
            if not project_name:
                extracted = TaskBuilder.build_fallback_intent(query, app)
                if extracted and extracted.get("parameters", {}).get("project_name"):
                    project_name = extracted["parameters"]["project_name"]
                    params["project_name"] = project_name
            pretty_name = project_name or "new project"
            task_intent["goal"] = f"Create a new project named '{pretty_name}' in {app}"
            task_intent["task_name"] = f"Create Project in {app.title()}"
            task_intent["description"] = f"Navigate to {app} and create a new project named '{pretty_name}'."
            task_intent["success_criteria"] = [
                f"Project named '{pretty_name}' appears in the project list",
                "Creation modal is submitted successfully"
            ]
        else:
            task_intent["goal"] = task_intent.get("goal") or f"Manage project in {app}"
            task_intent["task_name"] = task_intent.get("task_name") or f"Project workflow in {app.title()}"

        if "description" not in params and "description" in query_lower:
            project_label = project_name or "the project"
            params["description"] = f"Automated description for {project_label}."

        return task_intent

    @staticmethod
    def expand_multi_task(task_config: Dict) -> List[Dict]:
        """
        Expand a multi-task configuration into individual task configurations
        
        Args:
            task_config: Multi-task configuration
            
        Returns:
            List of individual task configurations
        """
        if not task_config.get('is_multi_task', False):
            return [task_config]
        
        parameters = task_config.get('parameters', {})
        count = parameters.get('count', 1)
        names = parameters.get('names', [])
        
        if count <= 1:
            return [task_config]
        
        individual_tasks = []
        
        for i in range(count):
            individual_task = task_config.copy()
            individual_task['is_multi_task'] = False
            individual_task['task_id'] = f"{task_config['task_id']}_part_{i+1}"
            
            individual_params = {}
            
            if names and i < len(names):
                task_name = names[i]
            elif 'name_pattern' in parameters:
                task_name = parameters['name_pattern'].replace('{i}', str(i+1))
            else:
                obj = task_config['object']
                task_name = f"{obj.title()} {i+1}"
            
            obj = task_config['object']
            if obj == "project":
                individual_params["project_name"] = task_name
            elif obj == "page":
                individual_params["page_name"] = task_name
            elif obj == "database":
                individual_params["database_name"] = task_name
            elif obj == "issue":
                individual_params["issue_title"] = task_name
            else:
                individual_params["name"] = task_name
            
            individual_task['parameters'] = individual_params
            individual_task['goal'] = f"Create {obj} named '{task_name}' in {task_config['app']}"
            individual_task['description'] = f"Navigate to {task_config['app']} and create {obj} named '{task_name}'"
            individual_task['name'] = f"Create {obj.title()}: {task_name}"
            individual_task['expected_steps'] = task_config['expected_steps'] // count
            individual_task['success_criteria'] = [
                f"{obj.title()} appears in list",
                f"{obj.title()} name is '{task_name}'"
            ]
            
            individual_tasks.append(individual_task)
        
        return individual_tasks

    @staticmethod
    def validate_task_config(task_config: Dict) -> bool:
        """
        Validate that a task config has all required fields
        
        Args:
            task_config: Task configuration dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            "task_id",
            "app",
            "goal",
            "start_url",
            "max_steps"
        ]
        
        for field in required_fields:
            if field not in task_config:
                print(f"❌ Missing required field: {field}")
                return False
        
        return True