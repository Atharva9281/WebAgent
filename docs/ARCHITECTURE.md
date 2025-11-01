# System Architecture

## Overview

Agent B is a vision-enabled web automation agent that captures UI states (including non-URL states) while navigating web applications.

## Core Components

### 1. Browser Layer (Playwright)
- Launches visible Chrome browser
- Loads saved authentication sessions
- Executes actions (click, type, scroll)

### 2. Annotation Layer (Set-of-Marks)
- JavaScript injected into page (`mark_page.js`)
- Adds numbered bounding boxes to interactive elements
- Returns element metadata (type, text, coordinates)

### 3. Vision Layer (Gemini 2.5 Flash)
- Receives annotated screenshot
- Sees numbered bounding boxes
- Decides next action based on task description

### 4. State Capture Layer
- Takes screenshot after every action
- Detects modals (role="dialog")
- Captures form field states
- Records metadata (URL, action, UI state)

### 5. Execution Loop
```
1. Annotate page with bounding boxes
2. Take screenshot
3. Send to Gemini: "What should I do next?"
4. Parse action (e.g., "Click [5]")
5. Execute action
6. Wait for UI to settle
7. Capture new state
8. Repeat until task complete
```

## Key Innovation: Non-URL State Capture

Traditional web automation relies on URL changes. We capture:
- **Modals**: Detected via `[role="dialog"]` selectors
- **Forms**: Read input values and filled state
- **Visual Changes**: Screenshot after every action

Example:
```
Step 1: URL = linear.app/projects (list page)
Step 2: URL = linear.app/projects (modal opened - SAME URL!)
Step 3: URL = linear.app/projects (form filled - STILL SAME URL!)
Step 4: URL = linear.app/project/123 (now changed)
```

## Data Flow
```
User Task
    ↓
Agent Loop
    ↓
mark_page.js (annotate)
    ↓
Screenshot (with boxes)
    ↓
Gemini 2.5 Flash
    ↓
Action Decision
    ↓
Playwright Execution
    ↓
State Capture (screenshot + metadata)
    ↓
Repeat or Complete
```

## Tech Stack Rationale

| Component | Choice | Why |
|-----------|--------|-----|
| LLM | Gemini 2.5 Flash | Free tier, vision-enabled, fast |
| Browser | Playwright | Reliable, Python support, visible mode |
| Annotation | Set-of-Marks | Proven by WebVoyager paper |
| Auth | storage_state | Industry standard, simple |
| Language | Python | Best ecosystem for AI/ML |