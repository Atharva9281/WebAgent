"""
Agent B - Main Web Automation Agent (Modular Version)

Vision-enabled web automation agent that captures UI states
(including non-URL states like modals and forms) while navigating
Linear and Notion.

This is the main orchestrator that coordinates:
- BrowserController: Browser management and actions
- GeminiClient: AI decision making  
- StateDetector: UI state detection
- Dataset generation: Screenshots + metadata

Usage:
    python src/agent.py
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

# Import our modules
from browser_controller import BrowserController
from gemini_client import GeminiClient
from state_detector import get_complete_ui_state, describe_ui_state
from task_definitions import get_task_by_id, TASKS, list_all_tasks

# Load environment variables
load_dotenv()


class AgentB:
    """
    Main web automation agent orchestrator
    """
    
    def __init__(self, gemini_api_key: str):
        """
        Initialize the agent with its components
        
        Args:
            gemini_api_key: Gemini API key from environment
        """
        self.browser = BrowserController()
        self.gemini = GeminiClient(gemini_api_key)
        self.action_history = []
        
        print("✅ Agent B initialized")
        print("   Components: BrowserController + GeminiClient + StateDetector")
    
    def execute_task(self, task_id: str) -> Dict:
        """
        Execute a complete task from start to finish
        
        Args:
            task_id: Task identifier (e.g., "linear_create_project")
            
        Returns:
            Task execution metadata
        """
        # Get task configuration
        try:
            task_config = get_task_by_id(task_id)
        except ValueError as e:
            print(f"❌ Error: {e}")
            print(f"Available tasks: {list_all_tasks()}")
            return {"success": False, "error": str(e)}
        
        self._print_task_header(task_config)
        
        # Create dataset directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"{task_id}_{timestamp}"
        dataset_dir = Path("dataset") / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Dataset directory: {dataset_dir}")
        
        # Initialize metadata
        metadata = self._initialize_metadata(task_config, dataset_dir)
        
        # Reset action history
        self.action_history = []
        
        # Setup browser
        if not self.browser.setup_browser(task_config):
            return {"success": False, "error": "Browser setup failed"}
        
        # Navigate to start URL
        if not self.browser.navigate_to_url(task_config['start_url']):
            self.browser.cleanup()
            return {"success": False, "error": "Navigation failed"}
        
        # Execute main task loop
        try:
            success = self._execute_task_loop(task_config, dataset_dir, metadata)
            metadata["success"] = success
        except Exception as e:
            print(f"\n❌ Task execution failed: {e}")
            import traceback
            traceback.print_exc()
            metadata["error"] = str(e)
            metadata["success"] = False
        finally:
            # Always cleanup browser
            self.browser.cleanup()
        
        # Save final metadata
        self._finalize_metadata(metadata, dataset_dir)
        
        # Print summary
        self._print_task_summary(metadata, dataset_dir)
        
        return metadata
    
    def _print_task_header(self, task_config: Dict):
        """Print task start header"""
        print("\n" + "="*70)
        print(f"🚀 STARTING TASK: {task_config['name']}")
        print("="*70)
        print(f"Goal: {task_config['goal']}")
        print(f"App: {task_config['app'].upper()}")
        print(f"Start URL: {task_config['start_url']}")
        print(f"Max steps: {task_config['max_steps']}")
        print("="*70 + "\n")
    
    def _initialize_metadata(self, task_config: Dict, dataset_dir: Path) -> Dict:
        """Initialize task metadata"""
        return {
            "task_id": task_config['task_id'],
            "task_name": task_config['name'],
            "app": task_config['app'],
            "goal": task_config['goal'],
            "start_url": task_config['start_url'],
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "success": False,
            "total_steps": 0,
            "dataset_dir": str(dataset_dir)
        }
    
    def _execute_task_loop(self, task_config: Dict, dataset_dir: Path, metadata: Dict) -> bool:
        """
        Main task execution loop
        
        Returns:
            True if task completed successfully, False otherwise
        """
        max_steps = task_config['max_steps']
        goal = task_config['goal']
        
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        for step_num in range(1, max_steps + 1):
            print(f"\n{'─'*70}")
            print(f"📸 STEP {step_num}/{max_steps}")
            print(f"{'─'*70}")
            
            try:
                # Execute single step
                step_success = self._execute_single_step(
                    step_num=step_num,
                    goal=goal,
                    task_config=task_config,
                    dataset_dir=dataset_dir,
                    metadata=metadata
                )
                
                if step_success == "completed":
                    print("\n🎉 Task marked as complete by agent!")
                    print("✅ Task completion validated successfully")
                    return True
                elif step_success == "failed":
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"\n⚠️  Too many consecutive failures ({max_consecutive_failures})")
                        print("   Stopping task execution")
                        return False
                else:
                    consecutive_failures = 0  # Reset on success
                
                # Small delay between actions
                time.sleep(1)
                
            except Exception as e:
                print(f"\n❌ Step {step_num} failed: {e}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_consecutive_failures:
                    print(f"\n⚠️  Too many consecutive failures ({max_consecutive_failures})")
                    return False
                
                # Save error screenshot
                self._save_error_screenshot(dataset_dir, step_num)
                continue
        
        print(f"\n⚠️  Reached maximum steps ({max_steps})")
        return False
    
    def _execute_single_step(
        self,
        step_num: int,
        goal: str,
        task_config: Dict,
        dataset_dir: Path,
        metadata: Dict
    ) -> str:
        """
        Execute a single step of the task
        
        Returns:
            "completed" if task finished, "failed" if step failed, "continue" if should continue
        """
        # 1. ANNOTATE PAGE
        print("1️⃣  Annotating page...")
        annotation_result = self.browser.annotate_and_capture()
        
        if not annotation_result['bboxes']:
            print("⚠️  No interactive elements found - might be loading")
            time.sleep(2)
            return "continue"
        
        print(f"   Found {len(annotation_result['bboxes'])} interactive elements")
        
        # 2. SAVE SCREENSHOT
        screenshot_filename = f"step_{step_num:02d}.png"
        screenshot_path = dataset_dir / screenshot_filename
        
        with open(screenshot_path, 'wb') as f:
            f.write(annotation_result['screenshot'])
        
        print(f"2️⃣  Screenshot saved: {screenshot_filename}")
        
        # 3. DETECT UI STATE
        print("3️⃣  Detecting UI state...")
        ui_state = get_complete_ui_state(self.browser.page)
        description = describe_ui_state(ui_state)
        print(f"   {description}")
        
        # 4. GET NEXT ACTION FROM GEMINI
        print("4️⃣  Asking Gemini for next action...")
        action = self.gemini.get_next_action(
            goal=goal,
            screenshot_b64=annotation_result['screenshot_b64'],
            bboxes=annotation_result['bboxes'],
            current_url=self.browser.get_current_url(),
            action_history=self.action_history
        )
        
        self._print_action_info(action)
        
        # 5. VALIDATE TASK COMPLETION (if finish action)
        if action['action'] == 'finish':
            if self.gemini.validate_task_completion(
                task_config=task_config,
                current_url=self.browser.get_current_url(),
                page_title=self.browser.get_page_title(),
                action=action
            ):
                # Save final step and return completion
                self._save_step_metadata(
                    step_num, action, "Task completed successfully", 
                    ui_state, description, screenshot_filename, dataset_dir, metadata
                )
                return "completed"
            else:
                print("\n❌ Task completion validation failed - continuing...")
                # Convert finish to wait and continue
                action['action'] = 'wait'
                action['reasoning'] = 'Task not actually complete - continuing automation'
        
        # 6. EXECUTE ACTION
        print("5️⃣  Executing action...")
        observation = self.browser.execute_action(action, annotation_result['bboxes'])
        print(f"   ✅ {observation}")
        
        # 7. SAVE STEP METADATA
        self._save_step_metadata(
            step_num, action, observation, ui_state, description, 
            screenshot_filename, dataset_dir, metadata
        )
        
        # 8. UPDATE HISTORY
        self.action_history.append({
            "step": step_num,
            "action": action['action'],
            "observation": observation
        })
        
        return "continue"
    
    def _print_action_info(self, action: Dict):
        """Print action information"""
        print(f"   🤖 Action: {action['action']}")
        if action.get('element_id') is not None:
            print(f"   🎯 Element: [{action['element_id']}]")
        if action.get('text'):
            print(f"   ✍️  Text: '{action['text'][:50]}...'")
        if action.get('reasoning'):
            print(f"   💭 Reasoning: {action['reasoning']}")
    
    def _save_step_metadata(
        self,
        step_num: int,
        action: Dict,
        observation: str,
        ui_state: Dict,
        description: str,
        screenshot_filename: str,
        dataset_dir: Path,
        metadata: Dict
    ):
        """Save metadata for a single step"""
        step_metadata = {
            "step": step_num,
            "url": self.browser.get_current_url(),
            "screenshot": screenshot_filename,
            "action": action,
            "observation": observation,
            "ui_state": ui_state,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        
        metadata["steps"].append(step_metadata)
        
        # Save individual step JSON
        step_json_path = dataset_dir / f"step_{step_num:02d}.json"
        with open(step_json_path, 'w') as f:
            json.dump(step_metadata, f, indent=2)
    
    def _save_error_screenshot(self, dataset_dir: Path, step_num: int):
        """Save screenshot on error"""
        try:
            error_screenshot = self.browser.page.screenshot()
            error_path = dataset_dir / f"step_{step_num:02d}_error.png"
            with open(error_path, 'wb') as f:
                f.write(error_screenshot)
        except:
            pass
    
    def _finalize_metadata(self, metadata: Dict, dataset_dir: Path):
        """Save final metadata to file"""
        metadata["finished_at"] = datetime.now().isoformat()
        metadata["total_steps"] = len(metadata["steps"])
        
        metadata_path = dataset_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _print_task_summary(self, metadata: Dict, dataset_dir: Path):
        """Print task completion summary"""
        print("\n" + "="*70)
        if metadata["success"]:
            print("✅ TASK COMPLETED SUCCESSFULLY")
        else:
            print("⚠️  TASK INCOMPLETE")
        print("="*70)
        print(f"Total steps: {metadata['total_steps']}")
        print(f"Dataset saved: {dataset_dir}")
        print("="*70 + "\n")


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("🤖 AGENT B - WEB AUTOMATION AGENT (MODULAR)")
    print("="*70)
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ Error: GEMINI_API_KEY not found in .env file")
        print("   Please add your API key to .env")
        print("   Get key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    # Create agent
    agent = AgentB(gemini_api_key=api_key)
    
    # Show available tasks
    print("\n" + "="*70)
    print("📋 AVAILABLE TASKS")
    print("="*70)
    
    for i, task in enumerate(TASKS, 1):
        print(f"\n{i}. {task['task_id']}")
        print(f"   App: {task['app'].upper()}")
        print(f"   Goal: {task['goal']}")
    
    print("\n" + "="*70)
    
    # Interactive mode
    if len(sys.argv) > 1:
        # Command line argument provided
        task_id = sys.argv[1]
    else:
        # Ask user
        print("\nEnter task number or task_id (or 'all' to run all tasks):")
        user_input = input("> ").strip()
        
        if user_input.lower() == 'all':
            # Run all tasks
            print("\n🚀 Running ALL tasks...")
            for task in TASKS:
                agent.execute_task(task['task_id'])
                print("\n" + "="*70)
                input("Press ENTER to continue to next task...")
            return
        
        # Parse input
        try:
            task_num = int(user_input)
            if 1 <= task_num <= len(TASKS):
                task_id = TASKS[task_num - 1]['task_id']
            else:
                print(f"❌ Invalid task number. Choose 1-{len(TASKS)}")
                return
        except ValueError:
            # Assume it's a task_id
            task_id = user_input
    
    # Execute task
    result = agent.execute_task(task_id)
    
    # Show summary
    if result.get('success'):
        print("\n✅ Task completed successfully!")
        print(f"   Dataset: dataset/{result.get('task_id', 'unknown')}_*/")
    else:
        print("\n⚠️  Task did not complete")
        if 'error' in result:
            print(f"   Error: {result['error']}")


if __name__ == "__main__":
    main()