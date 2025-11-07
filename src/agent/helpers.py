"""
Agent helper utilities and support functions.

This module contains utility functions and helper methods used by the AgentBase class.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json


def build_transition_metadata(step_num: int, ui_state: Dict, previous_step_state: Optional[Dict]) -> Dict:
    """Compare current state to previous step for change tracking."""
    previous = previous_step_state or {}
    current_url = ui_state.get("url", "") if ui_state else ""
    current_hash = ui_state.get("page_hash", "") if ui_state else ""

    transition = {
        "previous_step": previous.get("step"),
        "previous_url": previous.get("url", ""),
        "previous_page_hash": previous.get("page_hash", ""),
        "current_step": step_num,
        "current_url": current_url,
        "current_page_hash": current_hash,
        "url_changed": False,
        "dom_changed": False,
    }

    if previous:
        transition["url_changed"] = transition["previous_url"] != current_url
        prev_hash = previous.get("page_hash", "")
        if prev_hash and current_hash:
            transition["dom_changed"] = prev_hash != current_hash
        else:
            transition["dom_changed"] = bool(prev_hash or current_hash)

    return transition


def build_submit_hint(ui_state: Dict, bboxes: List[Dict]) -> Optional[Dict]:
    """Detect primary submit button when a modal with filled fields is open."""
    if not ui_state.get("modals"):
        return None

    filled_fields = [field for field in ui_state.get("forms", []) if field.get("filled")]
    if not filled_fields:
        return None

    submit_keywords = ["create", "submit", "save", "add", "confirm", "done", "finish", "publish"]
    cancel_keywords = ["cancel", "close", "discard"]

    candidates = []
    for bbox in bboxes:
        text = (bbox.get("text") or "").strip()
        if bbox.get("type") != "button" or not text:
            continue
        lower = text.lower()
        if any(keyword in lower for keyword in submit_keywords) and not any(
            keyword in lower for keyword in cancel_keywords
        ):
            candidates.append(bbox)

    if not candidates:
        return None

    primary = candidates[0]
    label = (primary.get("text") or "").strip() or "primary action"
    message = f"Modal detected with filled fields. Consider clicking [{primary['index']}] '{label}' to submit."
    print(f"💡 {message}")
    return {"type": "modal_submit_suggestion", "message": message, "element_id": primary["index"]}


def enrich_action_details(action: Dict, bboxes: List[Dict]) -> None:
    """Attach contextual element metadata to the action payload."""
    if not action or action.get("element_id") is None:
        return

    try:
        element_id = int(action.get("element_id"))
    except (TypeError, ValueError):
        return

    bbox = next((box for box in bboxes if box.get("index") == element_id), None)
    if not bbox:
        return

    text = (bbox.get("text") or "").strip()
    action["element_text"] = text
    action["element_type"] = bbox.get("type", "")
    action["bbox"] = [
        bbox.get("x"),
        bbox.get("y"),
        bbox.get("width"),
        bbox.get("height"),
    ]
    action["element_details"] = {
        "text": text,
        "type": bbox.get("type", ""),
        "aria_label": bbox.get("ariaLabel", ""),
        "role": bbox.get("role", ""),
        "href": bbox.get("href", ""),
        "id": bbox.get("id", ""),
        "class_name": bbox.get("className", ""),
    }


def save_step_metadata(
    step_num: int,
    action: Dict,
    observation: str,
    ui_state: Dict,
    description: str,
    screenshot_filename: str,
    dataset_dir: Path,
    metadata: Dict,
    transition: Optional[Dict] = None,
    browser_controller = None,
    step_metadata_extra: Dict = None,
) -> None:
    """Persist metadata for a single step."""
    step_metadata = {
        "step": step_num,
        "url": browser_controller.get_current_url() if browser_controller else "",
        "screenshot": screenshot_filename,
        "action": action,
        "observation": observation,
        "ui_state": ui_state,
        "description": description,
        "timestamp": datetime.now().isoformat(),
    }
    if transition:
        step_metadata["transition"] = transition
    if step_metadata_extra:
        step_metadata.update(step_metadata_extra)

    metadata["steps"].append(step_metadata)
    step_json_path = dataset_dir / f"step_{step_num:02d}.json"
    with open(step_json_path, "w") as handle:
        json.dump(step_metadata, handle, indent=2)


def save_error_screenshot(dataset_dir: Path, step_num: int, page) -> None:
    """Capture a screenshot when a step throws."""
    try:  # pragma: no cover - best effort only
        error_bytes = page.screenshot()
        error_path = dataset_dir / f"step_{step_num:02d}_error.png"
        with open(error_path, "wb") as handle:
            handle.write(error_bytes)
    except Exception:
        pass


def finalise_metadata(metadata: Dict, dataset_dir: Path) -> None:
    """Persist aggregated metadata to disk."""
    metadata["finished_at"] = datetime.now().isoformat()
    metadata["total_steps"] = len(metadata["steps"])
    metadata_path = dataset_dir / "metadata.json"
    with open(metadata_path, "w") as handle:
        json.dump(metadata, handle, indent=2)


def create_dataset_dir(
    task_config: Dict, 
    is_predefined: bool, 
    dataset_predefined_suffix: str = "",
    dataset_dynamic_suffix: str = "",
    dataset_dir_name: str = "dataset"
) -> Path:
    """Create dataset directory for a task."""
    suffix = dataset_predefined_suffix if is_predefined else dataset_dynamic_suffix

    if is_predefined:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"{task_config['task_id']}{suffix}_{timestamp}"
    else:
        dataset_name = f"{task_config['task_id']}{suffix}"

    dataset_dir = Path(dataset_dir_name) / dataset_name
    dataset_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Dataset directory: {dataset_dir}")
    return dataset_dir


def initialise_metadata(
    task_config: Dict, 
    dataset_dir: Path, 
    is_predefined: bool, 
    metadata_base: Dict = None
) -> Dict:
    """Initialize metadata for a task."""
    metadata = {
        "task_id": task_config["task_id"],
        "task_name": task_config["name"],
        "app": task_config["app"],
        "goal": task_config["goal"],
        "start_url": task_config["start_url"],
        "started_at": datetime.now().isoformat(),
        "steps": [],
        "success": False,
        "total_steps": 0,
        "parsed_from_query": task_config.get("parsed_from_query", ""),
    }
    if metadata_base:
        metadata.update(metadata_base)
    metadata["dataset_dir"] = str(dataset_dir)
    return metadata