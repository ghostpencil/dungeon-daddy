# UI Behavior Test

Test dungeon_daddy UI behavior against a live running window.

## How to use

`/ui-test <what to verify>`

Example: `/ui-test grid map renders rooms after loading sample dungeon`

## Workflow

### 1. Start the app

Run in background so it doesn't block:

```
python -m dungeon_daddy
```

Wait 3 seconds for the window to open, then take a screenshot with the ScreenshotTool (or equivalent screen capture tool available in this environment).

### 2. Perform setup actions (if needed)

If the test requires loading a dungeon, switching modes, or clicking UI elements, use the appropriate tools:
- Load sample dungeon: send `Ctrl+O` keypress (or instruct the user to press it)
- Switch to Play mode: look for the [Play] button in the title bar and click it
- Describe any other setup steps needed for the specific test

### 3. Take a screenshot

Capture the current window state.

### 4. Analyze the screenshot

Look for the specific behavior described in the test argument. Be explicit:
- What you expected to see
- What you actually see in the screenshot
- Whether the behavior matches the expectation
- Any visual anomalies (wrong colors, missing elements, clipped layout)

### 5. Report result

Output one of:
- **PASS** — with a one-line description of what was verified
- **FAIL** — with what was wrong, what was expected, and what was seen
- **BLOCKED** — if the app didn't start, a prior step failed, or the feature isn't built yet

### 6. Stop the app

```
python tools\arcade_stop.py
```

## Notes

- Always stop the app after the test, even on failure.
- If the window doesn't appear within 5 seconds, report BLOCKED and stop.
- Reference theme constants from `dungeon_daddy/ui/theme.py` when checking colors.
- Use pixel coordinates or region descriptions when calling out layout issues.
- Do not modify source files during a UI test.
