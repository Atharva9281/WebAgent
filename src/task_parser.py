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
from typing import Dict, Optional
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
            "parsed_from_query": query
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
                
                # Check if it's a series (contains commas or "and")
                if ',' in extracted_text or ' and ' in extracted_text:
                    # Split series: "assignment 1, 2, 3" or "A and B and C"
                    parts = re.split(r'[,\s]+and\s+|,\s*', extracted_text)
                    extracted_names = [part.strip() for part in parts if part.strip()]
                    if len(extracted_names) > 1:
                        is_multi_task = True
                        parameters["names"] = extracted_names
                        parameters["count"] = len(extracted_names)
                else:
                    # Single name
                    if obj == "project":
                        parameters["project_name"] = extracted_text
                    elif obj == "page":
                        parameters["page_name"] = extracted_text
                    elif obj == "database":
                        parameters["database_name"] = extracted_text
                    elif obj == "issue":
                        parameters["issue_title"] = extracted_text
                break
        
        # If we detected count but no names, generate pattern
        if is_multi_task and "names" not in parameters and count > 1:
            # Try to detect pattern like "Bug 1 through 5" or "assignment 1, 2, 3"
            if "through" in query or "to" in query:
                # Generate numbered series
                base_name = obj.title()  # Default base name
                parameters["names"] = [f"{base_name} {i}" for i in range(1, count + 1)]
                parameters["name_pattern"] = f"{base_name} {{i}}"
        
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