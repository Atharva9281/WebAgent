# Dataset Output

This directory contains the generated screenshots and metadata from Agent B's task execution.

## Structure

After running Agent B, you'll see subdirectories for each task:

```
dataset/
├── linear_create_project/
│   ├── step_1.png          # Screenshots for each step
│   ├── step_2.png
│   ├── step_3.png
│   └── metadata.json       # Rich metadata about the task
├── linear_create_issue/
├── linear_filter_issues/
├── notion_create_page/
└── notion_create_database/
```

## Metadata Format

Each `metadata.json` file contains:

```json
{
  "task": "linear_create_project",
  "description": "Create a new project in Linear",
  "start_url": "https://linear.app",
  "timestamp": "2025-11-02T10:30:00",
  "success": true,
  "steps": [
    {
      "step": 1,
      "action": "Navigate to Linear",
      "url": "https://linear.app/projects",
      "screenshot": "step_1.png",
      "ui_state": {
        "type": "list_view",
        "visible_modals": [],
        "form_fields": []
      }
    },
    {
      "step": 2,
      "action": "Click [12]",
      "url": "https://linear.app/projects",
      "screenshot": "step_2.png", 
      "ui_state": {
        "type": "modal_open",
        "visible_modals": [{"type": "dialog", "title": "Create Project"}],
        "form_fields": [{"name": "project_name", "filled": false}]
      }
    }
  ]
}
```

## Key Features

- **Non-URL State Tracking**: Notice step 2 has same URL but different UI state
- **Rich UI Metadata**: Captures modals, forms, and dynamic content
- **Visual Evidence**: Screenshots show exactly what the agent saw
- **Reproducible Actions**: Each action is precisely recorded

## File Sizes

Expected dataset size: **10-30 MB** total
- Screenshots: ~200-500 KB each
- Metadata: ~5-20 KB per task

## Usage

### View Screenshots
```bash
# Mac
open dataset/linear_create_project/step_1.png

# Linux  
xdg-open dataset/linear_create_project/step_1.png

# Windows
start dataset/linear_create_project/step_1.png
```

### Analyze Metadata
```bash
# Pretty print JSON
cat dataset/linear_create_project/metadata.json | python -m json.tool

# Extract just the actions
jq '.steps[].action' dataset/linear_create_project/metadata.json
```

### Process Programmatically
```python
import json

# Load metadata
with open('dataset/linear_create_project/metadata.json', 'r') as f:
    data = json.load(f)

# Analyze steps
for step in data['steps']:
    print(f"Step {step['step']}: {step['action']}")
    print(f"  URL: {step['url']}")
    print(f"  UI State: {step['ui_state']['type']}")
```

## Data Analysis

This dataset is valuable for:
- Training web automation models
- Analyzing UI state transitions
- Understanding non-URL navigation patterns
- Building better web automation tools

The key insight: **URLs don't capture the full navigation story**. This dataset shows the missing pieces.

## Cleanup

To regenerate the dataset:
```bash
# Remove all generated data
rm -rf dataset/*/

# Keep just the README
# (directories will be recreated on next run)
```