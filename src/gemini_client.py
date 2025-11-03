"""
Gemini Client Module

Handles all AI-related operations:
- Gemini API communication
- Action decision making
- Response parsing
- Task completion validation
"""

from typing import Dict, List
import google.generativeai as genai


class GeminiClient:
    """
    Manages interactions with Gemini AI for decision making
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini client
        
        Args:
            api_key: Gemini API key
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        print("✅ Gemini client initialized")
        print(f"   Model: gemini-2.0-flash-exp")
    
    def get_next_action(
        self,
        goal: str,
        screenshot_b64: str,
        bboxes: List[Dict],
        current_url: str,
        action_history: List[Dict],
        task_parameters: Dict = None
    ) -> Dict:
        """
        Ask Gemini to decide the next action
        
        Args:
            goal: Task goal description
            screenshot_b64: Base64 encoded screenshot with annotations
            bboxes: List of annotated elements from mark_page.js
            current_url: Current page URL
            action_history: Previous actions taken
            task_parameters: Extracted parameters from query (e.g., project_name)
            
        Returns:
            Structured action dictionary
        """
        try:
            # Format element list for Gemini with better context
            elements_text = self._format_elements(bboxes)
            
            # Format action history
            history_text = self._format_history(action_history)
            
            # Build comprehensive prompt
            prompt = self._build_prompt(goal, current_url, elements_text, history_text, task_parameters)
            
            # Call Gemini with vision
            response = self.model.generate_content([
                prompt,
                {
                    "mime_type": "image/png",
                    "data": screenshot_b64
                }
            ])
            
            response_text = response.text.strip()
            
            # Parse and return structured action
            return self._parse_action_response(response_text)
            
        except Exception as e:
            print(f"⚠️  Gemini API error: {e}")
            # Fallback: wait action
            return {
                "action": "wait",
                "reasoning": f"Error: {e}",
                "raw_response": str(e)
            }
    
    def _format_elements(self, bboxes: List[Dict]) -> str:
        """Format element list for Gemini with enhanced context"""
        return "\n".join([
            f"[{bbox['index']}] {bbox['type']}: \"{bbox['text'][:50].strip()}\" {bbox.get('ariaLabel', '').strip()}" + 
            (f" (href: {bbox['href'][:30]})" if bbox.get('href') else "") +
            (f" (role: {bbox['role']})" if bbox.get('role') else "")
            for bbox in bboxes[:30]  # Limit to 30 to avoid token overflow
        ])
    
    def _format_history(self, action_history: List[Dict]) -> str:
        """Format action history for context"""
        if not action_history:
            return "None (first step)"
        
        return "\n".join([
            f"Step {h['step']}: {h['action']} - {h['observation']}"
            for h in action_history[-5:]  # Last 5 actions
        ])
    
    def _build_prompt(self, goal: str, current_url: str, elements_text: str, history_text: str, task_parameters: Dict = None) -> str:
        """Build the comprehensive prompt for Gemini"""
        
        # Build parameters section
        parameters_text = ""
        if task_parameters:
            parameters_text = "\n\nTASK PARAMETERS (use these specific values):\n"
            for key, value in task_parameters.items():
                parameters_text += f"  - {key}: {value}\n"
        
        return f"""You are a web automation agent. Your goal: {goal}

Current URL: {current_url}

This screenshot has RED NUMBERED BOXES in the TOP-LEFT corner of interactive elements.

Available interactive elements:
{elements_text}

Previous actions:
{history_text}{parameters_text}

Choose ONE action from:
1. click [number] - Click an element by its number
2. type [number]; [text] - Type text into an input field
3. scroll down/up - Scroll the page
4. wait - Wait 3 seconds for page to load
5. finish; [summary] - Task is complete

CRITICAL RULES:
- Output EXACTLY in this format: ACTION: <action>
- Use the EXACT number from the list above
- If parameters specify a NAME, USE THAT EXACT NAME when typing
- Choose the action that makes progress toward the goal
- Be VERY careful with element selection - read the text carefully
- If you see a modal/form, interact with it
- ONLY use "finish" if you have ACTUALLY completed the goal - not just made progress
- For filtering tasks: you must actually apply a filter, not just view existing content
- Double-check that your action directly helps achieve the specific goal

Examples:
- ACTION: click [5]
- ACTION: type [12]; Trial Project
- ACTION: scroll down
- ACTION: finish; Successfully created project

Your response (one line only):"""
    
    def _parse_action_response(self, response_text: str) -> Dict:
        """
        Parse Gemini's action response into structured format
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Structured action dictionary
        """
        # Extract action line
        if "ACTION:" in response_text:
            action_line = response_text.split("ACTION:")[-1].strip()
        else:
            action_line = response_text.strip()
        
        # Remove any markdown formatting
        action_line = action_line.replace("`", "").strip()
        
        # Parse action
        parts = action_line.split(";", 1)
        main_part = parts[0].strip()
        
        # Extract action type
        action_words = main_part.split()
        if not action_words:
            return {
                "action": "wait",
                "raw_response": response_text,
                "reasoning": "Could not parse action"
            }
        
        action_type = action_words[0].lower()
        
        result = {
            "action": action_type,
            "raw_response": response_text,
            "reasoning": ""
        }
        
        # Parse based on action type
        if action_type == "click":
            result.update(self._parse_click_action(main_part))
        elif action_type == "type":
            result.update(self._parse_type_action(main_part, parts))
        elif action_type == "scroll":
            result.update(self._parse_scroll_action(action_line))
        elif action_type == "finish":
            result.update(self._parse_finish_action(parts))
        
        return result
    
    def _parse_click_action(self, main_part: str) -> Dict:
        """Parse click action to extract element ID"""
        try:
            # Extract number: "click [5]" or "click 5"
            number_str = main_part.split()[-1].strip("[]")
            element_id = int(number_str)
            return {"element_id": element_id}
        except (ValueError, IndexError):
            return {"element_id": 0}
    
    def _parse_type_action(self, main_part: str, parts: List[str]) -> Dict:
        """Parse type action to extract element ID and text"""
        result = {}
        
        try:
            # Extract number: "type [5]" 
            action_words = main_part.split()
            number_str = action_words[-1].strip("[]")
            result["element_id"] = int(number_str)
        except (ValueError, IndexError):
            result["element_id"] = 0
        
        # Extract text after semicolon
        if len(parts) > 1:
            result["text"] = parts[1].strip()
        else:
            result["text"] = ""
        
        return result
    
    def _parse_scroll_action(self, action_line: str) -> Dict:
        """Parse scroll action to extract direction"""
        if "down" in action_line.lower():
            return {"direction": "down"}
        else:
            return {"direction": "up"}
    
    def _parse_finish_action(self, parts: List[str]) -> Dict:
        """Parse finish action to extract summary"""
        if len(parts) > 1:
            return {"summary": parts[1].strip()}
        else:
            return {"summary": "Task completed"}
    
    def validate_task_completion(
        self,
        task_config: Dict,
        current_url: str,
        page_title: str,
        action: Dict
    ) -> bool:
        """
        Validate if task is actually complete before accepting 'finish' action
        
        Args:
            task_config: Task configuration
            current_url: Current page URL  
            page_title: Current page title
            action: Proposed finish action
            
        Returns:
            True if task is genuinely complete, False otherwise
        """
        if action['action'] != 'finish':
            return True  # Not a finish action, so validation passes
        
        task_id = task_config['task_id']
        
        # Task-specific validation logic
        if task_id == 'linear_filter_issues':
            return self._validate_linear_filter(current_url, page_title)
        elif task_id == 'linear_create_project':
            return self._validate_linear_project(current_url, page_title)
        elif task_id == 'linear_create_issue':
            return self._validate_linear_issue(current_url, page_title)
        elif task_id == 'notion_create_page':
            return self._validate_notion_page(current_url, page_title)
        elif task_id == 'notion_create_database':
            return self._validate_notion_database(current_url, page_title)
        
        return True  # Default: accept if no specific validation
    
    def _validate_linear_filter(self, current_url: str, page_title: str) -> bool:
        """Validate Linear filter task completion"""
        # Check if we're actually on a filtered view
        if 'filter' not in current_url.lower() and 'in progress' not in page_title.lower():
            print("⚠️  Task completion validation failed:")
            print("   Goal: Filter issues to 'In Progress'")
            print("   Current state: No evidence of filtering applied")
            print("   The agent should apply an actual filter, not just view existing content")
            return False
        return True
    
    def _validate_linear_project(self, current_url: str, page_title: str) -> bool:
        """Validate Linear project creation"""
        if 'project' not in current_url.lower():
            print("⚠️  Task completion validation failed:")
            print("   Goal: Create new project")
            print("   Current state: Not on a project page")
            return False
        return True
    
    def _validate_linear_issue(self, current_url: str, page_title: str) -> bool:
        """Validate Linear issue creation"""
        if 'issue' not in current_url.lower():
            print("⚠️  Task completion validation failed:")
            print("   Goal: Create new issue")
            print("   Current state: Not on an issue page")
            return False
        return True
    
    def _validate_notion_page(self, current_url: str, page_title: str) -> bool:
        """Validate Notion page creation"""
        # For Notion, check if we're on a specific page (has UUID in URL)
        if len(current_url.split('/')) < 4:
            print("⚠️  Task completion validation failed:")
            print("   Goal: Create new page")
            print("   Current state: Not on a specific page")
            return False
        return True
    
    def _validate_notion_database(self, current_url: str, page_title: str) -> bool:
        """Validate Notion database creation"""
        # Similar to page validation but could be more specific
        if len(current_url.split('/')) < 4:
            print("⚠️  Task completion validation failed:")
            print("   Goal: Create new database")
            print("   Current state: Not on a specific database page")
            return False
        return True