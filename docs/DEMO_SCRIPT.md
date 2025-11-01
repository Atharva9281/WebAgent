# Loom Demo Recording Guide

This guide helps you record a professional 3-5 minute demo video.

## Preparation (Before Recording)

1. **Clean environment**:
   - Close unnecessary browser tabs
   - Close unnecessary applications
   - Clear terminal history: `clear`

2. **Test run**:
   - Run agent on one task
   - Verify it works
   - Know what to expect

3. **Setup OBS or Loom**:
   - Install Loom: https://www.loom.com/
   - Or use OBS Studio (free)
   - Test audio (clear voice)

## Recording Script (3-5 minutes)

### Part 1: Introduction (30 seconds)
```
"Hi, I'm demonstrating Agent B, a web automation agent that captures 
UI states including non-URL states like modals and forms.

The key challenge this solves is that traditional automation relies 
on URL changes, but many UI states don't have URLs - like modal 
dialogs or dropdown menus.

Let me show you how it works."
```

### Part 2: Show Project Structure (30 seconds)
```
"Here's the project structure. 

[Show in VS Code or terminal]

- src/ contains the agent code
- auth/ stores saved login sessions  
- dataset/ will contain our captured screenshots

Let me show you the agent in action."
```

### Part 3: Run Agent - Live Demo (2 minutes)
```
[In terminal]
"I'll run the agent on a Linear task - creating a project."

python src/agent.py

[Let it run - shows visible Chrome browser]

"Notice the browser window is visible so you can see exactly 
what the agent is doing.

Watch as it:
1. Navigates to Linear - already logged in via saved session
2. Clicks 'New Project' - opens modal
3. Fills in the project name  
4. Clicks Create

The key point: steps 2-4 all happen at the SAME URL, but the 
agent captures each UI state change with screenshots."

[Agent completes]

"And it's done."
```

### Part 4: Show Dataset (1 minute)
```
[Open dataset folder]

"Here's the output in the dataset folder.

[Show folder structure]

dataset/linear_create_project/
- step_1.png - Project list page
- step_2.png - Modal opened - same URL
- step_3.png - Form filled - still same URL  
- step_4.png - Success state
- metadata.json - Rich metadata

[Open a few images]

"Notice how step 2 and 3 are at the same URL but capture 
different UI states - the modal opening and form being filled.

[Open metadata.json]

"The metadata includes:
- What action was taken
- The URL (which may not change)
- UI state info - modals detected, form fields, etc."
```

### Part 5: Code Walkthrough (30-60 seconds)
```
[Show agent.py briefly]

"The agent uses:
- Gemini 2.5 Flash for vision and reasoning
- Playwright for browser control  
- Set-of-Marks annotation - those numbered boxes you saw

[Show mark_page.js or annotation example]

"This JavaScript annotates interactive elements with numbers,
so Gemini can just say 'Click [5]' instead of describing 
complex selectors."
```

### Part 6: Wrap Up (15 seconds)
```
"That's Agent B - successfully capturing non-URL UI states 
across Linear and Notion. The complete dataset with 5 tasks 
and full code is included. Thanks for watching!"
```

## Recording Tips

1. **Speak clearly and slowly**
2. **Show, don't just tell** - visuals are key
3. **Keep mouse movements smooth**
4. **Pause briefly after each major point**
5. **If you mess up, just restart** - 5 min is short enough

## Upload

1. Upload to Loom (free account)
2. Make link shareable
3. Add link to README.md
4. Include in submission

## Checklist

- [ ] Audio is clear
- [ ] Screen is visible (1080p+ recommended)
- [ ] Agent runs successfully
- [ ] Dataset is shown
- [ ] Code is briefly explained
- [ ] Under 5 minutes
- [ ] Link is shareable