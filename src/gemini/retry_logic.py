"""
Retry and error handling logic for Gemini API calls.

This module contains error handling, retry logic, and fallback mechanisms
for robust Gemini API communication.
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
import json
from .config import DEBUG_LOG_FILE, DEBUG_LOG_SEPARATOR


def handle_gemini_error(error: Exception) -> Dict[str, Any]:
    """
    Handle Gemini API errors and return a fallback action.
    
    Args:
        error: The exception that occurred
        
    Returns:
        Fallback wait action dictionary
    """
    print(f"⚠️  Gemini API error: {error}")
    return {
        "action": "wait",
        "reasoning": f"Error: {error}",
        "raw_response": str(error)
    }


def log_early_finish_attempt(
    response_text: str, 
    current_url: str, 
    action_history: list,
    log_file: str = DEBUG_LOG_FILE
) -> None:
    """
    Log Gemini finish recommendations for debugging early exits.
    
    Args:
        response_text: The response from Gemini that triggered finish
        current_url: Current page URL
        action_history: History of previous actions
        log_file: Path to debug log file
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "step": action_history[-1]['step'] if action_history else 0,
        "url": current_url,
        "response_excerpt": response_text[:400]
    }

    try:
        with open(log_file, "a") as logfile:
            logfile.write(json.dumps(entry))
            logfile.write("\n" + DEBUG_LOG_SEPARATOR + "\n")
    except Exception:
        pass

    print(f"📝 Logged early finish attempt (step {entry['step']})")


def retry_with_backoff(
    func, 
    max_retries: int = 3, 
    base_delay: float = 1.0,
    backoff_multiplier: float = 2.0
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        backoff_multiplier: Multiplier for delay on each retry
        
    Returns:
        Result of successful function call
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (backoff_multiplier ** attempt)
                print(f"⚠️  Attempt {attempt + 1} failed: {e}")
                print(f"   Retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                print(f"❌ All {max_retries + 1} attempts failed")
    
    raise last_exception


def validate_api_response(response_text: str) -> bool:
    """
    Validate that the API response contains expected content.
    
    Args:
        response_text: Response text from Gemini API
        
    Returns:
        True if response appears valid, False otherwise
    """
    if not response_text or not response_text.strip():
        return False
    
    # Check for common indicators of a valid response
    valid_indicators = [
        "ACTION:",
        "click",
        "type", 
        "scroll",
        "wait",
        "finish"
    ]
    
    response_lower = response_text.lower()
    return any(indicator.lower() in response_lower for indicator in valid_indicators)


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error messages for logging and display.
    
    Args:
        error: Exception to sanitize
        
    Returns:
        Cleaned error message string
    """
    error_str = str(error)
    
    # Remove sensitive information patterns
    sensitive_patterns = [
        r'api[_-]?key[_-]?[=:]\s*[a-zA-Z0-9]+',
        r'token[_-]?[=:]\s*[a-zA-Z0-9]+',
        r'password[_-]?[=:]\s*\S+',
    ]
    
    import re
    for pattern in sensitive_patterns:
        error_str = re.sub(pattern, '[REDACTED]', error_str, flags=re.IGNORECASE)
    
    # Limit length
    if len(error_str) > 200:
        error_str = error_str[:197] + "..."
    
    return error_str


class GeminiRetryManager:
    """
    Manager for handling retries and error recovery in Gemini API calls.
    """
    
    def __init__(
        self, 
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_multiplier: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_multiplier = backoff_multiplier
        self.total_attempts = 0
        self.total_failures = 0
    
    def execute_with_retry(self, func, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result of successful function execution
        """
        self.total_attempts += 1
        
        def wrapped_func():
            return func(*args, **kwargs)
        
        try:
            return retry_with_backoff(
                wrapped_func,
                max_retries=self.max_retries,
                base_delay=self.base_delay,
                backoff_multiplier=self.backoff_multiplier
            )
        except Exception as e:
            self.total_failures += 1
            raise e
    
    def get_stats(self) -> Dict[str, int]:
        """Get retry statistics."""
        return {
            "total_attempts": self.total_attempts,
            "total_failures": self.total_failures,
            "success_rate": 1.0 - (self.total_failures / max(1, self.total_attempts))
        }