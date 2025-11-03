"""
Agent B - Clean Web Automation Agent

CLEAN VERSION: User sees unmodified pages throughout automation.
Annotations are added to screenshots using Python PIL, not DOM manipulation.

Key Benefits:
- User sees clean browser (no red boxes interrupting experience)
- Gemini sees annotated screenshots for decision making  
- More reliable clicking (no timing issues with DOM rendering)
- Better for production use

Usage:
    python src/agent_clean.py
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

# Import our modules (using clean versions)
from browser_controller_clean import CleanBrowserController
from gemini_client import GeminiClient
from state_detector import get_complete_ui_state, describe_ui_state
from task_definitions import get_task_by_id, TASKS, list_all_tasks
from task_parser import TaskParser

# Load environment variables
load_dotenv()


class CleanAgentB:
    """
    Clean web automation agent - User sees clean pages throughout
    """
    
    def __init__(self, gemini_api_key: str):
        """
        Initialize the clean agent with its components
        
        Args:
            gemini_api_key: Gemini API key from environment
        """
        self.browser = CleanBrowserController()  # Clean version
        self.gemini = GeminiClient(gemini_api_key)
        self.task_parser = TaskParser(gemini_api_key=gemini_api_key)
        self.action_history = []
        
        print("✅ Clean Agent B initialized")
        print("   Components: CleanBrowserController + GeminiClient + StateDetector")
        print("   🎨 Image annotation: Python PIL (NO DOM manipulation)")
        print("   👀 User experience: Clean browser throughout automation")
        print(f"   Task Parser: Ready")
    
    def handle_query(self, query: str) -> Dict:
        """
        Handle a natural language query from Agent A (Clean Version)
        
        This is the main entry point for runtime task execution.
        Agent A sends queries like: "How do I create a project in Linear?"
        
        Args:
            query: Natural language query
            
        Returns:
            Task execution metadata
        """
        print("\n" + "="*70)
        print("🤖 CLEAN AGENT B - HANDLING RUNTIME QUERY")
        print("="*70)
        print(f"Query from Agent A: {query}")
        print("🎨 Mode: Clean UI (no bounding boxes shown to user)")
        print("="*70 + "\n")
        
        # Parse natural language query into task configuration
        task_config = self.task_parser.parse_query(query)
        
        if not task_config:
            print("❌ Failed to parse query")
            return {
                "success": False,
                "error": "Could not parse query",
                "query": query
            }
        
        # Validate task configuration
        if not self.task_parser.validate_task_config(task_config):
            print("❌ Invalid task configuration")
            return {
                "success": False,
                "error": "Invalid task configuration",
                "query": query
            }
        
        # Check if this is a multi-task
        if task_config.get('is_multi_task', False):
            print(f"\n{'='*70}")
            print(f"🔥 MULTI-TASK DETECTED (CLEAN VERSION)")
            print(f"{'='*70}")
            print(f"Count: {task_config.get('parameters', {}).get('count', 1)}")
            print(f"Names: {task_config.get('parameters', {}).get('names', [])}")
            print(f"🎨 Clean UI: User will see unmodified pages throughout")
            print(f"{'='*70}\n")
            
            # Expand multi-task into individual tasks
            individual_tasks = self.task_parser.expand_multi_task(task_config)
            
            print(f"📋 Expanded into {len(individual_tasks)} individual clean tasks:")
            for i, task in enumerate(individual_tasks, 1):
                print(f"   {i}. {task['name']} (clean)")
            print()
            
            # Execute each individual task
            all_results = []
            for i, individual_task in enumerate(individual_tasks, 1):
                print(f"\n{'='*70}")
                print(f"🚀 EXECUTING CLEAN TASK {i}/{len(individual_tasks)}")
                print(f"{'='*70}")
                
                result = self.execute_dynamic_task(individual_task)
                result["task_number"] = i
                result["total_tasks"] = len(individual_tasks)
                result["original_query"] = query
                result["mode"] = "clean"
                all_results.append(result)
                
                if not result.get('success', False):
                    print(f"\n⚠️  Clean task {i} failed, stopping multi-task execution")
                    break
                
                if i < len(individual_tasks):
                    print(f"\n✅ Clean task {i} completed. Continuing to next task...")
                    import time
                    time.sleep(2)  # Brief pause between tasks
            
            # Return summary result
            successful_tasks = sum(1 for r in all_results if r.get('success', False))
            return {
                "success": successful_tasks == len(individual_tasks),
                "original_query": query,
                "is_multi_task": True,
                "mode": "clean",
                "total_tasks": len(individual_tasks),
                "successful_tasks": successful_tasks,
                "failed_tasks": len(individual_tasks) - successful_tasks,
                "individual_results": all_results,
                "summary": f"Completed {successful_tasks}/{len(individual_tasks)} clean tasks"
            }
        else:
            # Execute single task
            print(f"\n{'='*70}")
            print(f"🚀 EXECUTING DYNAMIC TASK (CLEAN VERSION)")
            print(f"{'='*70}\n")
            
            result = self.execute_dynamic_task(task_config)
            result["original_query"] = query
            
            return result
    
    
    def execute_dynamic_task(self, task_config: Dict) -> Dict:
        """
        Execute a dynamically generated task configuration (Clean Version)
        
        This method accepts task configs from the parser (runtime)
        or from task_definitions.py (predefined)
        
        Args:
            task_config: Task configuration dictionary
            
        Returns:
            Task execution metadata
        """
        print("\n" + "="*70)
        print(f"🚀 STARTING DYNAMIC TASK (CLEAN): {task_config['name']}")
        print("="*70)
        print(f"Goal: {task_config['goal']}")
        print(f"App: {task_config['app'].upper()}")
        print(f"Start URL: {task_config['start_url']}")
        print(f"Max steps: {task_config['max_steps']}")
        print("🎨 UI Mode: CLEAN (user sees unmodified pages)")
        print("="*70 + "\n")
        
        # Create dataset directory (mark as clean)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"{task_config['task_id']}_clean"
        dataset_dir = Path("dataset") / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Clean dataset directory: {dataset_dir}")
        
        # Initialize metadata
        metadata = {
            "task_id": task_config['task_id'],
            "task_name": task_config['name'],
            "app": task_config['app'],
            "goal": task_config['goal'],
            "start_url": task_config['start_url'],
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "success": False,
            "total_steps": 0,
            "mode": "clean",
            "annotation_method": "PIL",
            "parsed_from_query": task_config.get('parsed_from_query', '')
        }
        
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
            print(f"\n❌ Clean task execution failed: {e}")
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
    
    def execute_task(self, task_id: str) -> Dict:
        """
        Execute a complete task from start to finish (clean version)
        
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
        dataset_name = f"{task_id}_clean_{timestamp}"
        dataset_dir = Path("dataset") / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Clean dataset directory: {dataset_dir}")
        
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
        print(f"🚀 STARTING CLEAN TASK: {task_config['name']}")
        print("="*70)
        print(f"Goal: {task_config['goal']}")
        print(f"App: {task_config['app'].upper()}")
        print(f"Start URL: {task_config['start_url']}")
        print(f"Max steps: {task_config['max_steps']}")
        print(f"🎨 Annotation: PIL image manipulation (clean user experience)")
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
            "dataset_dir": str(dataset_dir),
            "annotation_method": "PIL_clean",  # Mark as clean version
            "user_experience": "clean_browser"
        }
    
    def _execute_task_loop(self, task_config: Dict, dataset_dir: Path, metadata: Dict) -> bool:
        """
        Main task execution loop (clean version)
        
        Returns:
            True if task completed successfully, False otherwise
        """
        max_steps = task_config['max_steps']
        goal = task_config['goal']
        
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        for step_num in range(1, max_steps + 1):
            print(f"\n{'─'*70}")
            print(f"📸 CLEAN STEP {step_num}/{max_steps}")
            print(f"{'─'*70}")
            
            try:
                # Execute single step (clean version)
                step_success = self._execute_single_step_clean(
                    step_num=step_num,
                    goal=goal,
                    task_config=task_config,
                    dataset_dir=dataset_dir,
                    metadata=metadata
                )
                
                if step_success == "completed":
                    print("\n🎉 Clean task marked as complete by agent!")
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
                print(f"\n❌ Clean step {step_num} failed: {e}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_consecutive_failures:
                    print(f"\n⚠️  Too many consecutive failures ({max_consecutive_failures})")
                    return False
                
                continue
        
        print(f"\n⚠️  Reached maximum steps ({max_steps})")
        return False
    
    def _execute_single_step_clean(
        self,
        step_num: int,
        goal: str,
        task_config: Dict,
        dataset_dir: Path,
        metadata: Dict
    ) -> str:
        """
        Execute a single step of the task (clean version)
        
        Returns:
            "completed" if task finished, "failed" if step failed, "continue" if should continue
        """
        # 1. CLEAN ANNOTATION & CAPTURE
        print("1️⃣  Clean annotation (PIL-based, no DOM changes)...")
        annotation_result = self.browser.annotate_and_capture_clean()
        
        if not annotation_result['bboxes']:
            print("⚠️  No interactive elements found - might be loading")
            time.sleep(2)
            return "continue"
        
        print(f"   Found {len(annotation_result['bboxes'])} interactive elements")
        print("   👀 User sees: Clean page (no visual interference)")
        
        # 2. SAVE CLEAN SCREENSHOT
        screenshot_filename = f"step_{step_num:02d}.png"
        screenshot_path = dataset_dir / screenshot_filename
        
        # Save the CLEAN screenshot (what user sees)
        with open(screenshot_path, 'wb') as f:
            f.write(annotation_result['screenshot'])
        
        print(f"2️⃣  Clean screenshot saved: {screenshot_filename}")
        
        # 3. DETECT UI STATE
        print("3️⃣  Detecting UI state...")
        ui_state = get_complete_ui_state(self.browser.page)
        description = describe_ui_state(ui_state)
        print(f"   {description}")
        
        # 4. GET NEXT ACTION FROM GEMINI (with annotated image)
        print("4️⃣  Asking Gemini for next action...")
        print("   🤖 Gemini receives: PIL-annotated screenshot")
        action = self.gemini.get_next_action(
            goal=goal,
            screenshot_b64=annotation_result['screenshot_b64'],  # Annotated version
            bboxes=annotation_result['bboxes'],
            current_url=self.browser.get_current_url(),
            action_history=self.action_history,
            task_parameters=task_config.get('parameters', {})
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
        
        # 6. EXECUTE ACTION ON CLEAN PAGE
        print("5️⃣  Executing action on clean page...")
        observation = self.browser.execute_action(action, annotation_result['bboxes'])
        print(f"   ✅ {observation}")
        print("   👀 User still sees: Clean page (no visual artifacts)")
        
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
            "screenshot_type": "clean_user_view",  # Mark as clean
            "annotation_method": "PIL_image_processing",
            "action": action,
            "observation": observation,
            "ui_state": ui_state,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "user_experience": "clean_no_visual_interference"
        }
        
        metadata["steps"].append(step_metadata)
        
        # Save individual step JSON
        step_json_path = dataset_dir / f"step_{step_num:02d}.json"
        with open(step_json_path, 'w') as f:
            json.dump(step_metadata, f, indent=2)
    
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
            print("✅ CLEAN TASK COMPLETED SUCCESSFULLY")
        else:
            print("⚠️  CLEAN TASK INCOMPLETE")
        print("="*70)
        print(f"Total steps: {metadata['total_steps']}")
        print(f"Clean dataset saved: {dataset_dir}")
        print(f"🎨 Annotation method: PIL image processing")
        print(f"👀 User experience: Clean browser (no visual interference)")
        print("="*70 + "\n")


def main():
    """Main entry point for clean agent - supports CLI and interactive modes"""
    print("\n" + "="*70)
    print("🤖 CLEAN AGENT B - WEB AUTOMATION AGENT")
    print("="*70)
    print("🎨 Image annotation: Python PIL (NO DOM manipulation)")
    print("👀 User experience: Clean browser throughout automation")
    print("🤖 AI experience: Annotated screenshots for decision making")
    print("Mode: RUNTIME FLEXIBLE")
    print("="*70)
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ Error: GEMINI_API_KEY not found in .env file")
        print("   Please add your API key to .env")
        print("   Get key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    # Create clean agent
    agent = CleanAgentB(gemini_api_key=api_key)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description='Clean Agent B - Web Automation Agent with Clean UI (Runtime Flexible)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single task queries (clean UI):
  python src/agent_clean.py "How do I create a project in Linear?"
  python src/agent_clean.py "Show me how to filter issues in Linear"
  
  # Multi-task queries (clean UI - any quantity):
  python src/agent_clean.py "Create 8 projects named Team A through H"
  python src/agent_clean.py "Create 15 issues with titles Feature 1, Feature 2..."
  
  # Predefined task by ID:
  python src/agent_clean.py --task linear_create_project
  
  # Run all predefined tasks:
  python src/agent_clean.py --all
        """
    )
    
    parser.add_argument(
        'query',
        nargs='?',
        help='Natural language query (e.g., "How do I create a project in Linear?")'
    )
    
    parser.add_argument(
        '--task',
        help='Execute a predefined task by ID (e.g., linear_create_project)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all predefined tasks in batch (clean mode)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available predefined tasks'
    )
    
    args = parser.parse_args()
    
    # Handle --list flag
    if args.list:
        print("\n" + "="*70)
        print("📋 AVAILABLE PREDEFINED TASKS (CLEAN VERSION)")
        print("="*70)
        
        for i, task in enumerate(TASKS, 1):
            print(f"\n{i}. {task['task_id']}")
            print(f"   App: {task['app'].upper()}")
            print(f"   Goal: {task['goal']}")
        
        print("\n" + "="*70)
        print("\nUsage:")
        print(f"  python src/agent_clean.py --task {TASKS[0]['task_id']}")
        print("="*70 + "\n")
        return
    
    # Handle --all flag
    if args.all:
        print("\n🚀 BATCH MODE - Running all predefined tasks (clean)...")
        print("="*70 + "\n")
        
        for i, task in enumerate(TASKS, 1):
            print(f"\n[{i}/{len(TASKS)}] Starting: {task['name']} (clean)")
            result = agent.execute_task(task['task_id'])
            
            if result.get('success'):
                print(f"✅ Completed (clean): {task['name']}")
            else:
                print(f"⚠️  Failed (clean): {task['name']}")
            
            if i < len(TASKS):
                print("\n" + "="*70)
                input("Press ENTER to continue to next task...")
        
        print("\n✅ All clean tasks completed!")
        return
    
    # Handle --task flag
    if args.task:
        print(f"\n🎯 PREDEFINED TASK MODE (CLEAN)")
        print(f"Task ID: {args.task}")
        print("="*70 + "\n")
        
        result = agent.execute_task(args.task)
        
        if result.get('success'):
            print("\n✅ Clean task completed successfully!")
            print(f"   Dataset: dataset/{result.get('task_id', 'unknown')}_clean_*/")
        else:
            print("\n⚠️  Clean task did not complete")
            if 'error' in result:
                print(f"   Error: {result['error']}")
        
        return
    
    # Handle natural language query from command line
    if args.query:
        print(f"\n🗣️  NATURAL LANGUAGE MODE (CLI - CLEAN)")
        print(f"Query: {args.query}")
        print("🎨 Clean UI: User sees unmodified pages (no bounding boxes)")
        print("="*70 + "\n")
        
        result = agent.handle_query(args.query)
        
        if result.get('success'):
            print("\n✅ Clean query handled successfully!")
            print(f"   Original query: {result.get('original_query', 'N/A')}")
            
            if result.get('is_multi_task', False):
                print(f"   Multi-task (clean): {result.get('successful_tasks', 0)}/{result.get('total_tasks', 0)} completed")
                print(f"   Summary: {result.get('summary', 'N/A')}")
                print(f"   Clean datasets: Multiple clean dataset directories created")
            else:
                print(f"   Task ID: {result.get('task_id', 'unknown')}")
                print(f"   Clean dataset: dataset/{result.get('task_id', 'unknown')}_clean/")
        else:
            print("\n⚠️  Clean query did not complete")
            if 'error' in result:
                print(f"   Error: {result['error']}")
            elif result.get('is_multi_task', False):
                print(f"   Multi-task (clean): {result.get('successful_tasks', 0)}/{result.get('total_tasks', 0)} completed")
                print(f"   {result.get('failed_tasks', 0)} clean tasks failed")
        
        return
    
    # INTERACTIVE MODE (no arguments provided)
    print("\n" + "="*70)
    print("📋 INTERACTIVE MODE (CLEAN)")
    print("="*70)
    print("\n1. NATURAL LANGUAGE QUERY (Clean UI)")
    print("   Enter a query like: 'How do I create a project in Linear?'")
    print("   🎨 User sees clean browser (no bounding boxes)")
    print("\n2. PREDEFINED TASK (Clean UI)")
    print("   Choose from existing task definitions")
    print("\n3. BATCH ALL TASKS (Clean UI)")
    print("   Run all predefined tasks")
    print("\n" + "="*70)
    
    mode = input("\nChoose mode (1/2/3): ").strip()
    
    if mode == "1":
        # NATURAL LANGUAGE MODE
        print("\n" + "="*70)
        print("🗣️  NATURAL LANGUAGE MODE (CLEAN)")
        print("="*70)
        print("🎨 Clean UI: User sees unmodified pages throughout")
        print("\nExample queries:")
        print("  SINGLE TASKS (clean UI):")
        print("  - How do I create a project in Linear?")
        print("  - Show me how to filter issues in Linear")
        print("  - How do I create a page in Notion?")
        print("  MULTI-TASKS (clean UI - any quantity):")
        print("  - Create [N] projects with titles [name1, name2, ...]")
        print("  - Create [N] issues called [pattern] 1 through [N]")
        print("  - Create pages titled [any names you want]")
        print("\n" + "="*70)
        
        query = input("\nEnter your query: ").strip()
        
        if not query:
            print("❌ No query entered")
            return
        
        # Execute using natural language parser
        result = agent.handle_query(query)
        
        # Show summary
        if result.get('success'):
            print("\n✅ Clean query handled successfully!")
            print(f"   Dataset: dataset/{result.get('task_id', 'unknown')}_clean/")
        else:
            print("\n⚠️  Clean query did not complete")
            if 'error' in result:
                print(f"   Error: {result['error']}")
    
    elif mode == "2":
        # PREDEFINED TASK MODE
        print("\n" + "="*70)
        print("📋 PREDEFINED TASKS (CLEAN)")
        print("="*70)
        
        for i, task in enumerate(TASKS, 1):
            print(f"\n{i}. {task['task_id']}")
            print(f"   App: {task['app'].upper()}")
            print(f"   Goal: {task['goal']}")
        
        print("\n" + "="*70)
        
        task_input = input("\nEnter task number or task_id: ").strip()
        
        try:
            task_num = int(task_input)
            if 1 <= task_num <= len(TASKS):
                task_id = TASKS[task_num - 1]['task_id']
            else:
                print(f"❌ Invalid task number. Choose 1-{len(TASKS)}")
                return
        except ValueError:
            task_id = task_input
        
        # Execute predefined task
        result = agent.execute_task(task_id)
        
        # Show summary
        if result.get('success'):
            print("\n✅ Clean task completed successfully!")
        else:
            print("\n⚠️  Clean task did not complete")
    
    elif mode == "3":
        # BATCH MODE
        print("\n🚀 Running ALL predefined tasks (clean version)...")
        for task in TASKS:
            agent.execute_task(task['task_id'])
            print("\n" + "="*70)
            input("Press ENTER to continue to next task...")
    
    else:
        print("❌ Invalid mode selected")


if __name__ == "__main__":
    main()