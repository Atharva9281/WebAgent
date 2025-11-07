"""
Gemini Client Module

Handles all AI-related operations:
- Gemini API communication
- Action decision making
- Response parsing
- Task completion validation
"""

from typing import Dict, List, Optional
import base64
import re

import google.generativeai as genai

from .config import (
    GEMINI_MODEL_NAME,
    MAX_ELEMENTS_FOR_CONTEXT,
    MAX_TEXT_LENGTH,
    MAX_ARIA_LENGTH, 
    MAX_HREF_LENGTH,
    MAX_OBSERVATION_LENGTH,
    MAX_HISTORY_STEPS,
    PROMPT_TEMPLATE,
    TASK_GUIDANCE_TEMPLATES
)
from .retry_logic import handle_gemini_error, log_early_finish_attempt
from .validation import validate_task_completion
from .parsing import parse_action_response


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
        self.model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        print("✅ Gemini client initialized")
        print(f"   Model: {GEMINI_MODEL_NAME}")
    
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
            hint: Context hint from subgoal manager
            
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

            # Decode the screenshot into raw bytes for Gemini vision input
            screenshot_bytes = base64.b64decode(screenshot_b64) if screenshot_b64 else b""

            # Call Gemini with vision
            response = self.model.generate_content([
                prompt,
                {
                    "mime_type": "image/png",
                    "data": screenshot_bytes
                }
            ])

            response_text = response.text.strip()
            
            # Parse and return structured action
            parsed_action = parse_action_response(response_text)

            if parsed_action.get('action') == 'finish':
                log_early_finish_attempt(response_text, current_url, action_history)

            return parsed_action
            
        except Exception as e:
            return handle_gemini_error(e)
    
    def _format_elements(self, bboxes: List[Dict]) -> str:
        """Format element list for Gemini with enhanced context"""
        if not bboxes:
            return "No interactive elements detected."

        lines = []
        for bbox in bboxes[:MAX_ELEMENTS_FOR_CONTEXT]:
            text = (bbox.get("text", "") or "").strip()
            aria = (bbox.get("ariaLabel", "") or "").strip()
            role = bbox.get("role") or ""
            href = bbox.get("href") or ""

            snippet = f"[{bbox['index']}] {bbox['type']}: \"{text[:MAX_TEXT_LENGTH]}\""
            if aria:
                snippet += f" (aria: {aria[:MAX_ARIA_LENGTH]})"
            if role:
                snippet += f" (role: {role})"
            if href:
                snippet += f" (href: {href[:MAX_HREF_LENGTH]})"
            lines.append(snippet)

        return "\n".join(lines)

    def _format_history(self, action_history: List[Dict]) -> str:
        """Format action history for context with loop-awareness"""
        if not action_history:
            return "RECENT ACTIONS: None (first step)\n"

        lines = ["RECENT ACTIONS (what you just did):"]
        for entry in action_history[-MAX_HISTORY_STEPS:]:
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
                detail = f"clicked \"{clicked[:MAX_TEXT_LENGTH]}\""
            elif observation:
                detail = observation[:MAX_OBSERVATION_LENGTH]

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
            
            for param, template in TASK_GUIDANCE_TEMPLATES.items():
                if param == "project_name" and "project_name" in task_parameters:
                    guidance_lines.append(template.format(value=task_parameters['project_name']))
                    guidance_lines.append("After the creation modal is open, stay inside it (look for 'New project') and avoid clicking the main 'Add project' button again.")
                elif param in param_lower:
                    guidance_lines.append(template)
            
            if guidance_lines:
                parameters_text += "\nTASK-SPECIFIC INSTRUCTIONS:\n"
                for line in guidance_lines:
                    parameters_text += f"  - {line}\n"

        hint_text = ""
        if hint and hint.get("message"):
            hint_text = f"\n💡 CONTEXT HINT:\n  - {hint['message']}\n"

        return PROMPT_TEMPLATE.format(
            goal=goal,
            current_url=current_url,
            elements_text=elements_text,
            history_text=history_text,
            parameters_text=parameters_text,
            hint_text=hint_text
        )
    
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
        return validate_task_completion(task_config, current_url, page_title, action)