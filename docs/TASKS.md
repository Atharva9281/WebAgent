# Task Definitions

This document describes the 5 tasks that Agent B will execute.

## Linear Tasks (3)

### Task 1: Create Project
**Objective**: Create a new project named "AI Agent Demo Project"

- **Start URL**: `https://linear.app`
- **Expected Steps**: 5-7
- **Success Criteria**: Project appears in project list

**Non-URL States Captured**:
1. Project list page (has URL)
2. Click "New Project" button → Modal opens (NO URL CHANGE)
3. Form fields visible → Fill project name (NO URL CHANGE)
4. Click "Create" → Loading state (NO URL CHANGE)
5. Success → Navigate to new project (URL CHANGES)

**Why This Task Matters**: 
Demonstrates capturing modal state without URL change.

---

### Task 2: Create Issue
**Objective**: Create an issue titled "Test Issue from Agent" in Engineering team

- **Start URL**: `https://linear.app`
- **Expected Steps**: 6-8
- **Success Criteria**: Issue visible in issues list

**Non-URL States Captured**:
1. Navigate to issues
2. Click "New Issue" → Dialog opens (NO URL CHANGE)
3. Fill title field (NO URL CHANGE)
4. Select team dropdown (NO URL CHANGE)
5. Choose team (NO URL CHANGE)
6. Click "Create" → Success (URL CHANGES)

**Why This Task Matters**:
Demonstrates capturing multiple form states and dropdowns.

---

### Task 3: Filter Issues
**Objective**: Filter issues to show only "In Progress" status

- **Start URL**: `https://linear.app/issues`
- **Expected Steps**: 4-5
- **Success Criteria**: Only "In Progress" issues visible

**Non-URL States Captured**:
1. Issues list page
2. Click filter button → Dropdown opens (NO URL CHANGE)
3. Select "In Progress" (NO URL CHANGE)
4. Apply filter → List updates (NO URL CHANGE)

**Why This Task Matters**:
Demonstrates capturing dropdown and filtered state changes.

---

## Notion Tasks (2)

### Task 4: Create Page
**Objective**: Create a new page titled "Agent Test Page" with some content

- **Start URL**: `https://www.notion.so`
- **Expected Steps**: 5-6
- **Success Criteria**: Page visible in sidebar

**Non-URL States Captured**:
1. Workspace home
2. Click "+ New Page" → Editor opens (NO URL CHANGE initially)
3. Type title (NO URL CHANGE)
4. Add content blocks (NO URL CHANGE)
5. Page created (URL CHANGES)

**Why This Task Matters**:
Demonstrates capturing content editor states.

---

### Task 5: Create Database
**Objective**: Create a table database named "Test Database" and add one entry

- **Start URL**: `https://www.notion.so`
- **Expected Steps**: 7-9
- **Success Criteria**: Database with one entry visible

**Non-URL States Captured**:
1. Workspace home
2. Click "+ New Page" → Type selector appears (NO URL CHANGE)
3. Select "Table" → Database view created (NO URL CHANGE)
4. Rename database (NO URL CHANGE)
5. Add column (NO URL CHANGE)
6. Add row → Inline editor opens (NO URL CHANGE)
7. Fill data (NO URL CHANGE)
8. Complete (URL may change)

**Why This Task Matters**:
Demonstrates capturing complex database editor states.

---

## Summary

Total: **5 tasks** across **2 apps**

All tasks demonstrate capturing **non-URL states**:
- Modals/dialogs
- Form fields
- Dropdowns
- Content editors
- Loading states

Expected dataset size: **25-50 screenshots** total