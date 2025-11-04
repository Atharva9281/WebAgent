"""
Natural Language Task Parser

Converts runtime queries from Agent A into executable task configurations.

Examples:
  "How do I create a project in Linear?"
  → {"app": "linear", "goal": "Create a new project", "start_url": "https://linear.app"}
  
  "Show me how to filter a database in Notion"
  → {"app": "notion", "goal": "Filter a database", "start_url": "https://notion.so"}

This makes Agent B truly generalizable - it doesn't need hardcoded tasks.
"""

import re
from typing import Dict, Optional, List
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()


class TaskParser:
    """
    Parses natural language queries into structured task configurations
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
        
        print(f"✅ Parsed intent:")
        print(f"   Goal: {task_intent['goal']}")
        print(f"   Action: {task_intent['action']}")
        print(f"   Object: {task_intent['object']}")
        
        # Build task configuration
        task_config = {
            "task_id": self._generate_task_id(task_intent, app_info['name']),
            "app": app_info['name'],
            "name": task_intent['task_name'],
            "goal": task_intent['goal'],
            "description": task_intent['description'],
            "start_url": app_info['url'],
            "expected_steps": task_intent.get('expected_steps', 10),
            "max_steps": 20,
            "success_criteria": task_intent['success_criteria'],
            "captures_non_url_states": True,
            "parsed_from_query": query,
            "parameters": dict(task_intent.get('parameters', {})),
            "is_multi_task": task_intent.get('is_multi_task', False),
            "action": task_intent['action'],
            "object": task_intent['object']
        }
        
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
        for app_name, app_info in self.APP_MAPPINGS.items():
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
        prompt = f"""You are a task intent parser for web automation.

User query: "{query}"
Target app: {app}

Parse this query and extract:
1. The ACTION (create, filter, edit, delete, search, etc.)
2. The OBJECT (project, issue, page, database, task, etc.)
3. A clear GOAL statement
4. A task name
5. A description
6. Expected number of steps (estimate)
7. Success criteria (list of conditions that indicate completion)
8. PARAMETERS - Extract any specific values mentioned:
   - If query mentions a NAME (e.g., "named X", "called X", "titled X"), extract it
   - If query mentions FILTERS (e.g., "status is X", "assigned to X"), extract them
   - If query mentions TEXT CONTENT, extract it
   - Any other specific values
9. MULTI-TASK DETECTION:
   - If query mentions QUANTITY (e.g., "3 projects", "5 issues"), extract it
   - If query mentions SERIES/LIST (e.g., "assignment 1, 2, 3", "A, B, C"), extract individual items
   - Determine if this is a single task or multiple tasks

Output EXACTLY in this JSON format:

For SINGLE TASK:
{{
  "action": "create",
  "object": "project",
  "goal": "Create a new project named 'Trial Project' in {app}",
  "task_name": "Create Project in {app.title()}",
  "description": "Navigate to {app} and create a new project named 'Trial Project'",
  "expected_steps": 7,
  "success_criteria": [
    "Project appears in project list",
    "Project name is 'Trial Project'"
  ],
  "parameters": {{
    "project_name": "Trial Project"
  }},
  "is_multi_task": false
}}

For MULTI-TASK:
{{
  "action": "create",
  "object": "project",
  "goal": "Create [N] projects with specified names in {app}",
  "task_name": "Create Multiple Projects in {app.title()}",
  "description": "Navigate to {app} and create multiple projects with specified names",
  "expected_steps": "[N * base_steps]",
  "success_criteria": [
    "All [N] projects appear in project list",
    "Projects have correct names"
  ],
  "parameters": {{
    "count": "[extracted_count]",
    "names": ["[extracted_name1]", "[extracted_name2]", "..."],
    "name_pattern": "[extracted_pattern] {{i}}"
  }},
  "is_multi_task": true
}}

CRITICAL RULES:
1. If query mentions QUANTITY (numbers + object), set is_multi_task: true
2. If query mentions SERIES/LIST, extract individual items to parameters.names
3. For multi-task, multiply expected_steps by count
4. Single names go to parameters.project_name, lists go to parameters.names
5. Output ONLY the JSON, no other text.

Examples:
- "Create a project named [NAME]" → is_multi_task: false, parameters: {{"project_name": "[NAME]"}}
- "Create [N] projects titled [name1, name2, ...]" → is_multi_task: true, parameters: {{"count": N, "names": ["name1", "name2", ...]}}
- "Create [N] issues called [PATTERN] 1 through [N]" → is_multi_task: true, parameters: {{"count": N, "name_pattern": "[PATTERN] {{i}}"}}
"""
        
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
            import json
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
            return self._fallback_parse(query, app)


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
        heuristic_intent = self._fallback_parse(query, app)
        if not heuristic_intent:
            return task_intent
        
        heuristic_params = heuristic_intent.get("parameters", {}) or {}
        params = task_intent.get("parameters", {}) or {}
        
        # Merge individual name parameters if missing
        for key in ["project_name", "page_name", "database_name", "issue_title", "name", "name_pattern"]:
            if key not in params and heuristic_params.get(key):
                params[key] = heuristic_params[key]
        
        instruction_keywords = {"change", "set", "update", "switch", "make", "turn"}

        # Merge explicit lists of names
        if heuristic_params.get("names"):
            if not params.get("names"):
                params["names"] = heuristic_params["names"]
            else:
                # Ensure uniqueness while preserving order
                existing = params["names"]
                for name in heuristic_params["names"]:
                    if name not in existing:
                        existing.append(name)
                params["names"] = existing
        
        # Clean name lists to remove instruction-like entries
        if params.get("names"):
            cleaned_names = []
            for name in params["names"]:
                lower_name = name.lower().strip()
                if any(lower_name.startswith(k) for k in instruction_keywords):
                    continue
                cleaned_names.append(name)
            if cleaned_names:
                params["names"] = cleaned_names
            else:
                params.pop("names", None)
                params.pop("count", None)
        
        # Merge counts
        if "count" not in params and heuristic_params.get("count"):
            params["count"] = heuristic_params["count"]
        
        # If we have names but no count, infer it
        if params.get("names") and not params.get("count"):
            params["count"] = len(params["names"])
        
        # Determine multi-task flag
        is_multi = task_intent.get("is_multi_task", False)
        if params.get("names"):
            is_multi = len(params["names"]) > 1
            if not is_multi:
                params.pop("names", None)
        if params.get("count", 1) > 1:
            is_multi = True
        if heuristic_intent.get("is_multi_task"):
            is_multi = True
        if not params.get("names") and params.get("count", 1) <= 1:
            params.pop("count", None)
        task_intent["is_multi_task"] = is_multi
        
        # Merge additional structured parameters (status, dates, etc.)
        additional_params = self._extract_additional_parameters(query)
        for key, value in additional_params.items():
            if key not in params:
                params[key] = value
        
        # Normalize synonymous fields
        if "status" not in params and "progress" in params:
            progress_val = params.pop("progress")
            params["status"] = self._normalize_status_value(progress_val) if isinstance(progress_val, str) else progress_val
        if "backlog_progress" in params:
            backlog_val = params.pop("backlog_progress")
            params["status"] = self._normalize_status_value(backlog_val)
        if "backlog_modal" in params:
            backlog_val = params.pop("backlog_modal")
            params["status"] = self._normalize_status_value(backlog_val)
        if "status" in params and isinstance(params["status"], str):
            params["status"] = self._normalize_status_value(params["status"])
        if "target_date" in params and isinstance(params["target_date"], str):
            params["target_date"] = params["target_date"].strip().rstrip(".")

        # Persist merged parameters
        task_intent["parameters"] = params
        
        return task_intent

    def _normalize_status_value(self, value: str) -> str:
        """Normalize status/progress strings into a user-facing label."""
        import re

        clean = str(value).strip()
        clean = clean.replace('-', ' ').replace('_', ' ')
        clean = re.sub(r'\s+', ' ', clean)
        mapping = {
            "inprogress": "In Progress",
            "in progress": "In Progress",
            "progress": "In Progress",
            "in-progress": "In Progress",
            "backlog": "Backlog",
            "todo": "Todo",
        }
        lower = clean.lower()
        if lower in mapping:
            return mapping[lower]
        return clean.title()

    def _extract_additional_parameters(self, query: str) -> Dict:
        """
        Extract structured fields from query text (status, dates, priority, etc.).
        """
        import re
        params: Dict[str, str] = {}
        
        # Status / workflow field changes
        status_patterns = [
            r'(?:status|backlog|workflow)[^a-zA-Z0-9]+(?:modal\s+)?(?:to|as|set to)\s+([a-zA-Z ]+?)(?:,| and|$)',
            r'(?:change|move|set)\s+(?:the\s+)?(?:status|backlog|workflow)[^a-zA-Z0-9]+to\s+([a-zA-Z ]+?)(?:,| and|$)'
        ]
        for pattern in status_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                status_raw = match.group(1).strip()
                params["status"] = self._normalize_status_value(status_raw)
                break

        # Additional backlog/progress phrasing
        if "status" not in params:
            match = re.search(
                r'backlog(?:\s+progress)?(?:\s+modal)?\s+(?:to|as|set to)\s+([a-zA-Z ]+?)(?:,| and|$)',
                query,
                re.IGNORECASE,
            )
            if match:
                status_raw = match.group(1).strip()
                params["status"] = self._normalize_status_value(status_raw)

        # Target/Due date extraction
        target_patterns = [
            r'target date\s+(?:to\s+)?([a-zA-Z0-9 ,]+?)(?:,| and|$)',
            r'target\s+(?:to\s+)?([a-zA-Z0-9 ,]+?)(?:,| and|$)',
            r'(?:due date|deadline)\s+(?:to\s+)?([a-zA-Z0-9 ,]+?)(?:,| and|$)'
        ]
        for pattern in target_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                target_raw = match.group(1).strip().rstrip('.')
                params["target_date"] = target_raw.title()
                break
        
        # Priority changes
        priority_patterns = [
            r'(?:set|change)\s+(?:the\s+)?priority\s+(?:to\s+)?([a-zA-Z ]+?)(?:,| and|$)'
        ]
        for pattern in priority_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                params["priority"] = match.group(1).strip().title()
                break
        
        return params
    
    
    def _fallback_parse(self, query: str, app: str) -> Dict:
        """
        Fallback parser if Gemini fails - now with parameter extraction
        
        Args:
            query: Natural language query
            app: App name
            
        Returns:
            Basic intent dictionary with extracted parameters
        """
        query_lower = query.lower()
        
        # Detect action
        action = "navigate"
        if "create" in query_lower or "add" in query_lower or "new" in query_lower:
            action = "create"
        elif "edit" in query_lower or "modify" in query_lower or "change" in query_lower:
            action = "edit"
        elif "delete" in query_lower or "remove" in query_lower:
            action = "delete"
        elif "filter" in query_lower or "search" in query_lower or "find" in query_lower:
            action = "filter"
        
        # Detect object
        obj = "item"
        if "project" in query_lower:
            obj = "project"
        elif "issue" in query_lower or "ticket" in query_lower:
            obj = "issue"
        elif "page" in query_lower:
            obj = "page"
        elif "database" in query_lower or "table" in query_lower:
            obj = "database"
        elif "task" in query_lower:
            obj = "task"
        
        # Extract parameters (SIMPLE REGEX) with multi-task support
        import re
        parameters = {}
        is_multi_task = False
        instruction_keywords = {"change", "set", "update", "switch", "make", "turn"}
        
        # Check for quantity patterns (multi-task detection)
        quantity_patterns = [
            r'(\d+)\s+' + obj + r's?',  # "3 projects", "5 issues"
            r'create\s+(\d+)',          # "create 5"
        ]
        
        count = 1
        for pattern in quantity_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                if count > 1:
                    is_multi_task = True
                    parameters["count"] = count
                break
        
        # Try to extract name patterns
        name_patterns = [
            r'named?\s+(?:as\s+)?["\']?([^"\']+)["\']?',
            r'called\s+["\']?([^"\']+)["\']?',
            r'titled?\s+["\']?([^"\']+)["\']?',
            r'with\s+titles?\s+([^"\']+)',
        ]
        
        extracted_names = []
        for pattern in name_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                extracted_text = match.group(1).strip()

                # Helper to split when instruction keyword appears
                def split_instruction(text: str):
                    lower = text.lower()
                    for kw in instruction_keywords:
                        idx = lower.find(kw + " ")
                        if idx != -1:
                            return text[:idx].strip(), text[idx:].strip()
                    return text.strip(), ""

                # If there's an " and " that likely separates instructions, split once
                if " and " in extracted_text.lower():
                    split_parts = re.split(r'\s+and\s+', extracted_text, maxsplit=1, flags=re.IGNORECASE)
                    name_candidate = split_parts[0].strip()
                    instruction_tail = split_parts[1].strip() if len(split_parts) > 1 else ""
                else:
                    name_candidate = extracted_text
                    instruction_tail = ""

                # Remove instruction phrases embedded in the candidate
                name_candidate, embedded_tail = split_instruction(name_candidate)
                if embedded_tail:
                    instruction_tail = f"{embedded_tail} {'and ' + instruction_tail if instruction_tail else ''}".strip()

                # Check if it's a series (contains commas OR multiple distinct parts)
                if ',' in name_candidate:
                    parts = [part.strip() for part in name_candidate.split(',') if part.strip()]
                else:
                    parts = [name_candidate]
                
                # Filter out parts that look like instructions ("change", "set", etc.)
                cleaned_parts = []
                for part in parts:
                    part_lower = part.lower()
                    if any(part_lower.startswith(k) for k in instruction_keywords):
                        instruction_tail = f"{part} {'and ' + instruction_tail if instruction_tail else ''}".strip()
                        continue
                    cleaned_parts.append(part)
                
                if cleaned_parts:
                    if len(cleaned_parts) > 1:
                        is_multi_task = True
                        extracted_names = cleaned_parts
                        parameters["names"] = cleaned_parts
                        parameters["count"] = len(cleaned_parts)
                    else:
                        single_name = cleaned_parts[0].strip().strip(" '\"")
                        normalized_name = single_name
                        if obj == "project":
                            parameters["project_name"] = normalized_name
                        elif obj == "page":
                            parameters["page_name"] = normalized_name
                        elif obj == "database":
                            parameters["database_name"] = normalized_name
                        elif obj == "issue":
                            parameters["issue_title"] = normalized_name
                        else:
                            parameters["name"] = normalized_name
                else:
                    # No valid names extracted; ensure multi-task isn't set just from instructions
                    is_multi_task = False

                # Append any instruction tail back into query for further processing
                if instruction_tail:
                    query = query + " " + instruction_tail
                break
        
        # If we detected count but no names, generate pattern
        if is_multi_task and "names" not in parameters and count > 1:
            # Try to detect pattern like "Bug 1 through 5" or "assignment 1, 2, 3"
            if "through" in query or "to" in query:
                # Generate numbered series
                base_name = obj.title()  # Default base name
                parameters["names"] = [f"{base_name} {i}" for i in range(1, count + 1)]
                parameters["name_pattern"] = f"{base_name} {{i}}"
        
        # Extract additional parameters like status or dates
        additional_params = self._extract_additional_parameters(query)
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
    
    
    def _generate_task_id(self, intent: Dict, app: str) -> str:
        """
        Generate a unique task ID from intent
        
        Args:
            intent: Intent dictionary
            app: App name
            
        Returns:
            Task ID string
        """
        from datetime import datetime
        
        action = intent['action']
        obj = intent['object']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Clean strings for ID
        action_clean = re.sub(r'[^a-z0-9]', '_', action.lower())
        obj_clean = re.sub(r'[^a-z0-9]', '_', obj.lower())
        
        return f"{app}_{action_clean}_{obj_clean}_{timestamp}"
    
    
    def validate_task_config(self, task_config: Dict) -> bool:
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
    
    
    def expand_multi_task(self, task_config: Dict) -> List[Dict]:
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
            # Create individual task config
            individual_task = task_config.copy()
            individual_task['is_multi_task'] = False
            individual_task['task_id'] = f"{task_config['task_id']}_part_{i+1}"
            
            # Set individual parameters
            individual_params = {}
            
            # Get name for this iteration
            if names and i < len(names):
                # Use specific name from list
                task_name = names[i]
            elif 'name_pattern' in parameters:
                # Use pattern to generate name
                task_name = parameters['name_pattern'].replace('{i}', str(i+1))
            else:
                # Generate default name
                obj = task_config['object']
                task_name = f"{obj.title()} {i+1}"
            
            # Set parameter based on object type
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
            
            # Update goal and description for individual task
            individual_task['goal'] = f"Create {obj} named '{task_name}' in {task_config['app']}"
            individual_task['description'] = f"Navigate to {task_config['app']} and create {obj} named '{task_name}'"
            individual_task['name'] = f"Create {obj.title()}: {task_name}"
            individual_task['expected_steps'] = task_config['expected_steps'] // count
            
            # Update success criteria
            individual_task['success_criteria'] = [
                f"{obj.title()} appears in list",
                f"{obj.title()} name is '{task_name}'"
            ]
            
            individual_tasks.append(individual_task)
        
        return individual_tasks


# Example usage and testing
if __name__ == "__main__":
    print("="*70)
    print("TASK PARSER - NATURAL LANGUAGE TO TASK CONFIG")
    print("="*70)
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env")
        exit(1)
    
    # Create parser
    parser = TaskParser(gemini_api_key=api_key)
    
    # Test queries
    test_queries = [
        "How do I create a project in Linear?",
        "Show me how to filter issues in Linear",
        "How do I create a new page in Notion?",
        "How can I add a database in Notion?",
        "What's the process for creating a task in Linear?"
    ]
    
    print("\n" + "="*70)
    print("TESTING QUERIES")
    print("="*70 + "\n")
    
    for query in test_queries:
        task_config = parser.parse_query(query)
        
        if task_config:
            print(f"✅ Successfully parsed query")
            print(f"   Generated task ID: {task_config['task_id']}")
            print(f"   Goal: {task_config['goal']}")
        else:
            print(f"❌ Failed to parse query")
        
        print("\n" + "-"*70 + "\n")
