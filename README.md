# Agent B: Web Automation with Non-URL State Capture

[![Demo Video](https://img.shields.io/badge/Demo-Loom%20Video-blue)](DEMO_LINK_HERE)

An intelligent web automation agent that captures rich UI states including modals, forms, and other non-URL-based interface changes using vision-powered decision making.

## 🎯 Problem Solved

Traditional web automation relies on URL changes to track navigation state. However, many modern web applications use modals, dropdowns, and dynamic content that don't trigger URL changes. **Agent B captures these non-URL states** by taking screenshots after every action and recording rich metadata about the UI state.

## ✨ Key Features

- **Vision-Powered Navigation**: Uses Gemini 2.5 Flash to "see" the page and decide next actions
- **Non-URL State Capture**: Records modals, forms, and dynamic content changes
- **Saved Authentication**: Pre-authenticated sessions for Linear and Notion
- **Set-of-Marks Annotation**: Numbered bounding boxes for precise element targeting
- **Rich Metadata**: JSON output with URLs, actions, UI states, and more

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone and setup
git clone <your-repo>
cd agent-b

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Setup Authentication

```bash
# Run auth setup for Linear and Notion
python src/setup_auth.py
```

This opens browsers where you manually log in. Sessions are saved to `auth/` for reuse.

### 3. Run Agent

```bash
# Run all 5 tasks
python src/agent.py

# Or run specific task
python src/agent.py --task linear_create_project
```

### 4. View Results

```bash
# Check generated dataset
ls dataset/

# View screenshots and metadata
open dataset/linear_create_project/step_1.png
cat dataset/linear_create_project/metadata.json
```

## 📁 Project Structure

```
agent-b/
├── README.md
├── requirements.txt
├── .env                    # API keys
├── .gitignore
├── auth/                   # Saved browser sessions
│   ├── linear_state.json
│   └── notion_state.json
├── src/                    # Source code
│   ├── agent.py           # Main agent
│   ├── setup_auth.py      # Authentication setup
│   └── mark_page.js       # Page annotation script
├── dataset/               # Generated screenshots + metadata
│   ├── linear_create_project/
│   ├── linear_create_issue/
│   ├── linear_filter_issues/
│   ├── notion_create_page/
│   └── notion_create_database/
└── docs/                  # Documentation
    ├── ARCHITECTURE.md
    ├── TASKS.md
    └── DEMO_SCRIPT.md
```

## 🎭 Example: Non-URL State Capture

Here's how Agent B captures states that traditional automation misses:

```json
{
  "task": "create_project_linear",
  "steps": [
    {
      "step": 1,
      "action": "Navigate to Linear",
      "url": "https://linear.app/projects",
      "screenshot": "step_1.png",
      "ui_state": {
        "type": "list_view",
        "visible_modals": []
      }
    },
    {
      "step": 2,
      "action": "Click [12]",
      "url": "https://linear.app/projects",  // SAME URL!
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

**Key Innovation**: Step 2 has the same URL as Step 1, but captures the modal opening state that traditional automation would miss.

## 🗂️ Dataset Tasks

Agent B executes 5 tasks across 2 applications:

### Linear (3 tasks)
1. **Create Project** - Demonstrates modal state capture
2. **Create Issue** - Shows form field state changes  
3. **Filter Issues** - Captures dropdown and filter states

### Notion (2 tasks)  
4. **Create Page** - Records content editor states
5. **Create Database** - Complex multi-step database creation

## 🏗️ Architecture

- **Browser Layer**: Playwright (visible Chrome browser)
- **Annotation Layer**: Set-of-Marks JavaScript injection
- **Vision Layer**: Gemini 2.5 Flash for decision making
- **State Capture**: Screenshot + metadata after every action

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed technical overview.

## 🔧 Configuration

### Environment Variables (.env)
```bash
GEMINI_API_KEY=your_api_key_here
BROWSER_HEADLESS=false           # Keep visible during automation
SCREENSHOT_DELAY=1000           # Wait time after actions (ms)
```

### Task Configuration
Edit task definitions in `src/agent.py` or see [docs/TASKS.md](docs/TASKS.md).

## 📊 Expected Output

After running all tasks, you'll have:
- **25-50 screenshots** showing step-by-step UI navigation
- **Rich JSON metadata** for each action and state change
- **Authenticated sessions** saved for future runs
- **Complete dataset** ready for analysis or training

## 🎬 Demo Video

[📺 Watch 3-minute Loom demo](DEMO_LINK_HERE) - See Agent B in action

## 🔍 Troubleshooting

**Authentication Issues**: Delete `auth/*.json` and re-run `setup_auth.py`

**Browser Crashes**: Set `BROWSER_HEADLESS=true` in `.env`

**API Errors**: Verify `GEMINI_API_KEY` in `.env`

**Slow Performance**: Increase `SCREENSHOT_DELAY` in `.env`

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Task Definitions](docs/TASKS.md)
- [Demo Recording Guide](docs/DEMO_SCRIPT.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [WebVoyager](https://arxiv.org/abs/2401.13919) for Set-of-Marks inspiration
- [Playwright](https://playwright.dev/) for reliable browser automation
- [Gemini](https://ai.google.dev/) for vision-powered decision making