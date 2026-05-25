# UI Testing

`UITestHarness` in `tools/ui_harness.py` manages app lifecycle (launch / shutdown).
Do not use `subprocess.Popen` directly in tests, and do not call `arcade_stop.py`
manually during a test run.

---

## Claude-driven tests (preferred)

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

---

## Interaction protocol

For every UI interaction during a Claude-driven test:

1. **Screenshot** (optional but recommended) — capture current state before acting
2. **Act** — perform the UI action (`left_click`, `type`, `key`, `scroll`, …)
3. **Wait** — if the UI needs time to update, pause before the next step
4. **Screenshot** — capture the result
5. **Verify** — inspect the screenshot to confirm the expected outcome

---

## Harness API summary

| Method | Purpose |
|---|---|
| `h.pin_window(x=0, y=0)` | Move window to known screen position, refresh rect |
| `h.refresh_window_rect()` | Re-query Win32 for current window position |
| `h.capture("label")` | Full-screen PNG (legacy — includes desktop/taskbar) |
| `h.capture_window("label")` | Window-only PNG (cleaner, window-relative pixels) |
| `h.window_rect` | `(left, top, right, bottom)` in screen pixels |

The harness waits for the window to appear, then waits `render_wait=4.0 s` for the
frame to fully paint before returning — do not add extra `time.sleep`.

---

## Automated smoke tests (legacy)

Smoke tests in `tools/smoke_test_phase*.py` use pixel-color math via `mss`.
Run directly: `python tools/smoke_test_phase5.py`

`tools/ui_input.py` provides ctypes helpers for automated tests:
- `click_app(rect, x, y)` — click at Arcade app coordinates
- `key_combo(VK_CONTROL, VK_O)` — keyboard shortcut
- `scroll_at(sx, sy, clicks)` — mouse wheel (positive = up)
- `type_text(text)` — Unicode text input via SendInput

Integration tests for the harness: `tests/integration/test_ui_harness.py`
