# Dataset Directory

This directory contains recordings of agent task executions, including screenshots and metadata.

## Structure

Each task execution creates a new directory with timestamped naming:

```
dataset/
├── linear_create_project_20251106_123456/
│   ├── step_01.png              # Screenshot with annotations
│   ├── step_02.png
│   ├── step_03.png
│   └── metadata.json            # Task execution metadata
│
├── linear_create_issue_20251106_234567/
│   └── ...
│
└── README.md (this file)
```

## Metadata Format

Each task directory contains a `metadata.json` file with:

```json
{
  "task_id": "linear_create_project_20251106_123456",
  "query": "Create project Jobhunt with urgent priority",
  "app": "linear",
  "start_url": "https://linear.app",
  "start_time": "2024-11-06T12:34:56",
  "end_time": "2024-11-06T12:35:42",
  "total_steps": 8,
  "success": true,
  "steps": [
    {
      "step": 1,
      "action": "click",
      "element_id": 8,
      "element_text": "Projects",
      "url": "https://linear.app/team/TRI/active",
      "screenshot": "step_01.png",
      "ui_state": {
        "modals": [],
        "forms": [],
        "dropdowns": []
      }
    }
  ]
}
```

## Screenshot Naming

- `step_01.png` - First action (annotated with bounding boxes)
- `step_02.png` - Second action
- etc.

## Usage

### View Screenshots
```bash
# Mac
open dataset/linear_create_project_20251106_123456/step_01.png

# Linux  
xdg-open dataset/linear_create_project_20251106_123456/step_01.png
```

### Analyze Metadata
```bash
# Pretty print JSON
cat dataset/linear_create_project_*/metadata.json | python -m json.tool

# Extract just the actions
cat dataset/linear_create_project_*/metadata.json | jq '.steps[].action'
```

### Process Programmatically
```python
import json
from pathlib import Path

# Find latest task recording
task_dirs = sorted(Path('dataset').glob('linear_create_project_*'))
latest = task_dirs[-1]

# Load metadata
with open(latest / 'metadata.json') as f:
    data = json.load(f)

# Analyze steps
for step in data['steps']:
    print(f"Step {step['step']}: {step['action']}")
    print(f"  Screenshot: {step['screenshot']}")
```

## Cleanup

To clear old task recordings:

```bash
# Remove all dataset directories
rm -rf dataset/linear_* dataset/notion_*

# Keep only recent recordings (last 24 hours)
find dataset -name "linear_*" -mtime +1 -exec rm -rf {} \;
```

## Data Analysis

This dataset is valuable for:
- Debugging agent behavior
- Training web automation models
- Analyzing UI workflows
- Understanding task execution patterns
