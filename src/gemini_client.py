"""
Gemini Client Module

Handles all AI-related operations:
- Gemini API communication
- Action decision making
- Response parsing
- Task completion validation
"""

from typing import Dict, List
from datetime import datetime
import json
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
        task_parameters: Dict = None,
        hint: Dict = None
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
            prompt = self._build_prompt(
                goal,
                current_url,
                elements_text,
                history_text,
                task_parameters,
                hint
            )
            
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
            parsed_action = self._parse_action_response(response_text)

            if parsed_action.get('action') == 'finish':
                self._log_early_finish(response_text, current_url, action_history)

            return parsed_action
            
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
        if not bboxes:
            return "No interactive elements detected."

        lines = []
        for bbox in bboxes[:40]:
            text = (bbox.get("text", "") or "").strip()
            aria = (bbox.get("ariaLabel", "") or "").strip()
            role = bbox.get("role") or ""
            href = bbox.get("href") or ""

            snippet = f"[{bbox['index']}] {bbox['type']}: \"{text[:50]}\""
            if aria:
                snippet += f" (aria: {aria[:40]})"
            if role:
                snippet += f" (role: {role})"
            if href:
                snippet += f" (href: {href[:60]})"
            lines.append(snippet)

        return "\n".join(lines)

    def _format_history(self, action_history: List[Dict]) -> str:
        """Format action history for context with loop-awareness"""
        if not action_history:
            return "RECENT ACTIONS: None (first step)\n"

        lines = ["RECENT ACTIONS (what you just did):"]
        for entry in action_history[-5:]:
            step = entry.get("step")
            action = entry.get("action", "unknown")
            observation = entry.get("observation", "")

            detail = ""
            if "Typed" in observation:
                parts = observation.split("'")
                typed = parts[1] if len(parts) > 1 else ""
                detail = f"typed \"{typed}\""
            elif "Clicked" in observation:
                parts = observation.split(": ")
                clicked = parts[1] if len(parts) > 1 else observation
                detail = f"clicked \"{clicked[:50]}\""
            elif observation:
                detail = observation[:60]

            if detail:
                lines.append(f"  Step {step}: {action} - {detail}")
            else:
                lines.append(f"  Step {step}: {action}")

        return "\n".join(lines) + "\n"

    def _build_prompt(
        self,
        goal: str,
        current_url: str,
        elements_text: str,
        history_text: str,
        task_parameters: Dict = None,
        hint: Dict = None
    ) -> str:
        """Build the comprehensive prompt for Gemini"""
        
        # Build parameters section
        parameters_text = ""
        if task_parameters:
            parameters_text = "\n\n🎯 TASK PARAMETERS (use these exact values):\n"
            guidance_lines = []
            for key, value in task_parameters.items():
                if value is None or value == "":
                    continue
                if isinstance(value, list):
                    display_value = ", ".join(str(v) for v in value)
                else:
                    display_value = value
                parameters_text += f"  - {key}: {display_value}\n"
            
            # Provide explicit instructions for known structured parameters
            param_lower = {k: (v.lower() if isinstance(v, str) else v) for k, v in task_parameters.items()}
            if "project_name" in task_parameters:
                guidance_lines.append(f"Type the project name field with exactly \"{task_parameters['project_name']}\" before saving.")
                guidance_lines.append("After the creation modal is open, stay inside it (look for 'New project') and avoid clicking the main 'Add project' button again.")
            if "status" in param_lower:
                guidance_lines.append("Inside the modal, click the button showing the current status/backlog (e.g., \"Backlog\", \"In Progress\") and choose the requested status.")
            if "priority" in param_lower:
                guidance_lines.append("Set the priority dropdown to the requested value.")
            if "target_date" in task_parameters:
                guidance_lines.append("Click the date/target control in the modal and set it to the specified date using the picker.")
            if "assignee" in param_lower:
                guidance_lines.append("Assign the item to the specified person if an assignee field is available.")
            
            if guidance_lines:
                parameters_text += "\nTASK-SPECIFIC INSTRUCTIONS:\n"
                for line in guidance_lines:
                    parameters_text += f"  - {line}\n"

        hint_text = ""
        if hint and hint.get("message"):
            hint_text = f"\n💡 CONTEXT HINT:\n  - {hint['message']}\n"

        return f"""You are a web automation agent. Your goal: {goal}

Current URL: {current_url}

This screenshot has RED NUMBERED BOXES in the TOP-LEFT corner of interactive elements.

Available interactive elements:
{elements_text}

Previous actions:
{history_text}{parameters_text}{hint_text}

🚨 CRITICAL RULES TO PREVENT LOOPS:
1. DON'T REPEAT YOURSELF
   - If history shows you already typed a value, do NOT type it again.
   - If a field already displays text, move on.
2. NEVER CLICK CANCEL (unless the task explicitly asks).
3. COMPLETE FORMS PROPERLY
   - In a modal, fill required fields, then immediately click Create/Submit/Save.
   - Optional controls (icons, colors) are secondary.
4. MODAL AWARENESS
   - Once a modal is open, stay inside it until you submit it.
   - Do NOT reopen the same modal unless it closed unexpectedly.
5. DETERMINE COMPLETION
   - If the modal closes after submission and the list updates, call finish with a short summary.

AVAILABLE ACTIONS:
1. click [number] - Click the element with that number
2. type [number]; [text] - Type text (use the exact parameter values)
3. scroll down/up - Scroll the page
4. wait - Wait 3 seconds
5. finish; [summary] - Task is complete

DECISION PROCESS (follow carefully):
1. Review RECENT ACTIONS to see what you just did.
2. Inspect the screenshot to confirm what changed.
3. If required fields are filled and there is a submit button, click it.
4. If a required field is empty, fill it once.
5. If the goal is met, respond with finish; <summary>.
6. Otherwise choose the best next step without repeating work.

Output format (single line):
ACTION: <action>

Examples:
- ACTION: click [56]
- ACTION: type [12]; second task
- ACTION: finish; Created project and updated status"""
    
    def _parse_action_response(self, response_text: str) -> Dict:
        """
        Parse Gemini's action response into structured format
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Structured action dictionary
        """
        # Extract reasoning and action line
        reasoning_text = ""
        if "ACTION:" in response_text:
            parts = response_text.split("ACTION:")
            reasoning_text = parts[0].strip()
            action_line = parts[-1].strip()
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
                "reasoning": reasoning_text or "Could not parse action"
            }
        
        action_type = action_words[0].lower()
        
        result = {
            "action": action_type,
            "raw_response": response_text,
            "reasoning": reasoning_text
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
        else:
            # Handle cases where Gemini returns JSON-like shorthand such as {"answer":"finish"}
            normalized = action_type.strip()
            lowered = normalized.lower()
            if "answer" in lowered:
                if "finish" in lowered:
                    result["action"] = "finish"
                    result.update(self._parse_finish_action(parts))
                elif "wait" in lowered:
                    result["action"] = "wait"
                elif "click" in lowered:
                    result["action"] = "click"
                    result.update(self._parse_click_action(main_part))
                elif "type" in lowered:
                    result["action"] = "type"
                    result.update(self._parse_type_action(main_part, parts))
                else:
                    result["action"] = "wait"
            elif normalized in {"wait", "finish", "click", "type", "scroll"}:
                result["action"] = normalized
                if normalized == "finish":
                    result.update(self._parse_finish_action(parts))
                elif normalized == "click":
                    result.update(self._parse_click_action(main_part))
                elif normalized == "type":
                    result.update(self._parse_type_action(main_part, parts))
                elif normalized == "scroll":
                    result.update(self._parse_scroll_action(action_line))
            else:
                result["action"] = "wait"
                result["reasoning"] = "Unrecognized action payload, defaulting to wait"

        return result

    def _log_early_finish(self, response_text: str, current_url: str, action_history: List[Dict]):
        """Log Gemini finish recommendations for debugging early exits."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": action_history[-1]['step'] if action_history else 0,
            "url": current_url,
            "response_excerpt": response_text[:400]
        }

        try:
            with open("debug_early_finish.log", "a") as logfile:
                logfile.write(json.dumps(entry))
                logfile.write("\n" + "-" * 80 + "\n")
        except Exception:
            pass

        print(f"📝 Logged early finish attempt (step {entry['step']})")
    
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
