# SoftLight: Vision-Powered Web Automation Agent

An intelligent web automation agent that uses Gemini 2.0 Flash vision AI to perform natural language tasks on web applications like Linear and Notion.

## 🎯 What It Does

SoftLight is a generalizable web automation agent that:
- **Understands natural language queries** like "Create a project named Jobhunt in Linear"
- **Uses vision AI** (Gemini 2.0 Flash) to see and understand web pages
- **Automates complex workflows** across Linear and Notion
- **Handles modals, forms, and dynamic content** automatically
- **Tracks sub-goals** to complete multi-step tasks reliably

## ✨ Key Features

- **Natural Language Interface**: Describe tasks in plain English
- **Vision-Powered Navigation**: Gemini sees the page and decides actions
- **Sub-Goal Management**: Breaks complex tasks into trackable steps
- **Modal & Form Detection**: Automatically handles dialogs and forms
- **Set-of-Marks Annotation**: Numbered bounding boxes for element targeting
- **Authenticated Sessions**: Pre-saved logins for Linear and Notion

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Gemini API key
# Get from: https://ai.google.dev/
GEMINI_API_KEY=your_key_here
```

### 3. Setup Authentication (One-time)

```bash
# Login to Linear and Notion
python3 src/setup_auth.py
```

This opens browsers where you manually log in. Sessions are saved to `auth/` for reuse.

### 4. Run the Agent

```bash
# Interactive mode - type your queries
python3 src/agent.py

# Example queries:
# - "Create project Assessment in Linear"
# - "Create issue Jobhunt with urgent priority in Linear"
# - "Show projects with backlog status in Linear"
```

## 📁 Project Structure

```
SoftLight_legacy/
├── README.md
├── REFACTORING.md              # Code refactoring documentation
├── requirements.txt
├── .env                        # Configuration (API keys)
│
├── auth/                       # Saved browser sessions
│   ├── linear_profile/
│   └── notion_profile/
│
├── src/                        # Source code (refactored into modules)
│   ├── agent/                  # Agent orchestration
│   │   ├── base.py            # Main agent class
│   │   ├── task_executor.py   # Task execution loop
│   │   ├── helpers.py         # Utilities
│   │   └── printing.py        # Display functions
│   │
│   ├── parser/                 # Natural language parsing
│   │   ├── parser.py          # Main parser
│   │   ├── task_builder.py    # Task configuration
│   │   └── app_config.py      # App definitions
│   │
│   ├── subgoal/                # Sub-goal management
│   │   ├── manager.py         # Goal tracking
│   │   ├── action_guides.py   # Action guidance
│   │   ├── element_finders.py # Element detection
│   │   └── goal_checkers.py   # Completion checking
│   │
│   ├── gemini/                 # Gemini AI client
│   │   ├── client.py          # API client
│   │   ├── retry_logic.py     # Error handling
│   │   └── parsing.py         # Response parsing
│   │
│   ├── detector/               # UI state detection
│   │   ├── detector.py        # Main detector
│   │   ├── modal_detector.py  # Modal/dialog detection
│   │   └── form_detector.py   # Form field detection
│   │
│   ├── browser/                # Browser control
│   │   ├── controller.py      # Main controller
│   │   ├── actions.py         # Action execution
│   │   └── utils.py           # Utilities
│   │
│   ├── browser_controller.py  # Browser with annotations
│   ├── mark_page.js           # Page annotation script
│   ├── agent.py               # CLI entrypoint
│   ├── agent_cli.py           # CLI utilities
│   ├── setup_auth.py          # Authentication setup
│   └── task_definitions.py    # Predefined tasks
│
└── dataset/                    # Generated task recordings
    └── README.md
```

## 🎯 Example Usage

### Create a Project in Linear

```bash
$ python3 src/agent.py
Enter your query: Create project Jobhunt and set priority urgent in Linear
```

The agent will:
1. Navigate to Linear projects page
2. Open the "Create Project" modal
3. Type "Jobhunt" in the name field
4. Set priority to "Urgent"
5. Generate an automated description
6. Click "Create Project"

All steps are executed automatically with screenshots saved to `dataset/`.

### Filter Projects by Status

```bash
Enter your query: Show me projects with backlog status in Linear
```

The agent will:
1. Navigate to Linear projects
2. Open the filter menu
3. Select "Status" filter
4. Choose "Backlog" option
5. Display filtered results

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required
GEMINI_API_KEY=your_api_key_here

# Optional
BROWSER_HEADLESS=false          # Keep browser visible
SCREENSHOT_DELAY=1000           # Wait after actions (ms)
MAX_STEPS_PER_TASK=20          # Maximum steps per task
VERBOSE_LOGGING=true            # Detailed output
```

## 🏗️ Architecture

### Components

1. **Natural Language Parser** (`src/parser/`)
   - Converts user queries into structured task configs
   - Uses Gemini to understand intent

2. **Sub-Goal Manager** (`src/subgoal/`)
   - Breaks tasks into trackable goals
   - Guides actions to complete objectives
   - Validates completion

3. **Browser Controller** (`src/browser/`)
   - Controls Playwright browser
   - Injects Set-of-Marks annotations
   - Captures screenshots

4. **State Detector** (`src/detector/`)
   - Detects modals, forms, dropdowns
   - Tracks UI state changes
   - Identifies loading states

5. **Vision AI Client** (`src/gemini/`)
   - Sends annotated screenshots to Gemini
   - Gets next action decisions
   - Handles retries and errors

### How It Works

```
User Query → Parser → Task Config → Sub-Goals
                                        ↓
Screenshot ← Browser ← Action ← Gemini Vision
     ↓                              ↑
State Detector → Update Goals → Next Action
```

## 📊 Supported Tasks

### Linear
- ✅ Create projects with status, priority, description
- ✅ Create issues with status, priority, description
- ✅ Filter projects/issues by status
- ✅ Update project/issue properties

### Notion
- ✅ Create pages
- ✅ Create databases
- (More tasks being added)

## 🔍 Troubleshooting

### Authentication Issues
```bash
# Delete saved sessions and re-authenticate
rm -rf auth/linear_profile auth/notion_profile
python3 src/setup_auth.py
```

### Browser Crashes
```bash
# Run in headless mode
# In .env, set:
BROWSER_HEADLESS=true
```

### API Errors
```bash
# Verify API key
cat .env | grep GEMINI_API_KEY

# Check API quota at: https://ai.google.dev/
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📚 Documentation

- [REFACTORING.md](REFACTORING.md) - Code refactoring details
- [dataset/README.md](dataset/README.md) - Dataset structure
- [auth/README.md](auth/README.md) - Authentication guide

## 🤝 Contributing

This is a research project. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [WebVoyager](https://arxiv.org/abs/2401.13919) - Set-of-Marks inspiration
- [Playwright](https://playwright.dev/) - Browser automation
- [Gemini 2.0 Flash](https://ai.google.dev/) - Vision AI
