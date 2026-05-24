# Dungeon Daddy — Agent Instructions

You are implementing **Dungeon Daddy**: a Python desktop application for game masters
running tabletop dungeon crawls. It is AI-powered, built on the Arcade 2D game engine,
and follows a cyber-arcane visual aesthetic.

---

# Core Rule — Minimize Context

Do NOT load all spec files.

At start, read only:
- CLAUDE.md
- spec/PROJECT_INDEX.md

Load other files only when needed.

---

# Phase Discipline

Phase and status are in PROJECT_INDEX.md.

## If STABILIZATION
- Do not move to next phase
- No new features
- No architecture changes
- Only:
    - bug fixes
    - behavior fixes
    - UI fixes
    - test fixes
    - spec alignment

If unsure → ask

## If BUILD
- Work only within current phase
- Do not skip ahead

---

# Always-Active Rules

- TDD required (tests first)
- Small steps only (one behavior)
- No new libraries without approval
- Python 3.12+
- Use pathlib (no OS-specific paths)
- JSON must be readable (indent=2)
- LLM must use dependency injection

---

# Skills

## TDD Skill

When writing tests for a new phase or new feature, use the installed TDD skill.

Use the TDD skill before:
- creating a new test file
- adding tests for a new module
- starting a new phase
- defining test strategy

Do not write phase tests from memory if the TDD skill applies.

For bug fixes during STABILIZATION:
- use the TDD skill only if adding or changing tests
- otherwise keep the fix minimal

---

## UI Testing

`UITestHarness` in `tools/ui_harness.py` manages app lifecycle (launch / shutdown).
Do not use `subprocess.Popen` directly in tests, and do not call `arcade_stop.py`
manually during a test run.

### Claude-driven tests (preferred)

Use `computer-use-mcp` (`mcp__computer-use-mcp__computer`) for screenshots and
interaction.  The harness owns the process; the MCP tool owns the visuals.

```python
with UITestHarness(tag="phase9") as h:
    h.pin_window()          # move window to (0, 0) so MCP coordinates are stable
    # h.window_rect → (left, top, right, bottom) in absolute screen pixels
    # Now use mcp__computer-use-mcp__computer for all interaction:
    #   action="get_screenshot"            → Claude sees the live window
    #   action="left_click", coordinate=[x, y]
    #   action="type",  text="..."         → types into focused widget
    #   action="key",   text="ctrl+o"      → keyboard shortcuts
    #   action="scroll", coordinate=[x,y], text="up" / "down"
# app is terminated on __exit__, even if assertions raise
```

MCP coordinate system: `x` from left edge of screen, `y` from top edge of screen
(standard screen pixels — not Arcade's bottom-up y).

After `pin_window()`, the app window starts at (0, 0), so MCP click coordinates
map directly to app-window positions without any offset math.

### Interaction protocol

For every UI interaction during a Claude-driven test:

1. **Screenshot** (optional but recommended) — capture current state before acting
2. **Act** — perform the UI action (`left_click`, `type`, `key`, `scroll`, …)
3. **Wait** — if the UI needs time to update, pause before the next step
4. **Screenshot** — capture the result
5. **Verify** — inspect the screenshot to confirm the expected outcome

### Harness API summary

| Method | Purpose |
|---|---|
| `h.pin_window(x=0, y=0)` | Move window to known screen position, refresh rect |
| `h.refresh_window_rect()` | Re-query Win32 for current window position |
| `h.capture("label")` | Full-screen PNG (legacy — includes desktop/taskbar) |
| `h.capture_window("label")` | Window-only PNG (cleaner, window-relative pixels) |
| `h.window_rect` | `(left, top, right, bottom)` in screen pixels |

The harness waits for the window to appear, then waits `render_wait=4.0 s` for the
frame to fully paint before returning — do not add extra `time.sleep`.

### Automated smoke tests (legacy)

Smoke tests in `tools/smoke_test_phase*.py` use pixel-color math via `mss`.
Run directly: `python tools/smoke_test_phase5.py`

`tools/ui_input.py` provides ctypes helpers for automated tests:
- `click_app(rect, x, y)` — click at Arcade app coordinates
- `key_combo(VK_CONTROL, VK_O)` — keyboard shortcut
- `scroll_at(sx, sy, clicks)` — mouse wheel (positive = up)
- `type_text(text)` — Unicode text input via SendInput

Integration tests for the harness: `tests/integration/test_ui_harness.py`

---

## Commands

```
python -m dungeon_daddy          # start the app manually
python tools/arcade_stop.py      # stop a manually-started app window
```

---
# Context Loading

Before coding, classify task:

- phase
- dependencies
- data model
- persistence
- LLM/agents
- UI/layout
- visuals
- map/rendering
- testing
- architecture

Load only needed files.

---

# Spec Loading Rules

## IMPLEMENTATION_PHASES.md
Only if:
- phase is unknown
- checking exit criteria
- preparing next phase

Otherwise: do not open

## TECH_STACK.md
Only if:
- adding libs
- using new library API

## TESTING.md
Only if:
- writing/modifying tests
- TDD questions
- writing or modifying a smoke test (`tools/smoke_test_phase*.py`) — read the
  Strategy A vs Strategy B guidance before starting

## ARCHITECTURE.md
Only if:
- creating/changing modules
- state/threading/view ownership

## DATA_MODEL.md
Only if:
- models or JSON work

## LLM_INTERFACE.md
Only if:
- providers or agents

## UI_SPEC.md
Only if:
- UI behavior or layout

## VISUAL_DESIGN.md
Only if:
- colors, fonts, drawing

## FEATURES.md
Only if:
- checking scope or acceptance criteria

---

# Workflow (TDD)

For each task:

1. Write failing test
2. Implement minimal code
3. Refactor
4. Repeat

No large batches.

---

# Spec Rules

- If you open a spec → say which one
- Use only needed parts
- If spec conflicts with request → ask for override

---

# Output Rules

- Keep code minimal
- No unrelated changes
- No future features
- No assumptions

---

# Reference

Prototype exists:
- prototype/
- data/dungeon.js
- spec/samples/

Use as reference only. Do not port.

---

# Summary

- Load minimal context
- Stay in phase
- Follow TDD
- Open specs only when needed
- Ask when unsure