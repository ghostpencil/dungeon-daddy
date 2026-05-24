# tools/

Developer scripts for smoke testing and UI automation. **Windows only** — the
platform backend (`platform_win32.py`) uses Win32 ctypes; non-Windows raises
`NotImplementedError`.

---

## Setup

Install dev dependencies from the project root:

```
pip install -r requirements-dev.txt
```

Set required environment variables:

| Variable | Used by |
|---|---|
| `OPENAI_API_KEY` | Dungeon Daddy wizard (GPT-4o) |
| `ANTHROPIC_API_KEY` | Vision step classifier in Strategy B smoke tests |

---

## Running smoke tests

**Always `cd` into `tools/` first** — the harness imports `platform_host` as a
top-level module, so the `tools/` directory must be on `sys.path`:

```
cd tools
python smoke_test_phase7.py
python smoke_test_phase13.py
```

Running as `python tools/smoke_test_phaseX.py` from the project root will fail
with `ModuleNotFoundError: No module named 'platform_host'`.

Screenshots and chat logs are written to `tools/screenshots/`.

---

## Files

| File | Purpose |
|---|---|
| `ui_harness.py` | `UITestHarness` context manager — launches app, manages window |
| `platform_host.py` | Selects `platform_win32` or `platform_stub` based on OS |
| `platform_win32.py` | Win32 ctypes backend (DPI, window pos, mouse/keyboard input) |
| `platform_stub.py` | Non-Windows stub — raises `NotImplementedError` |
| `ui_input.py` | Low-level ctypes helpers (`click_app`, `key_combo`, `scroll_at`, `type_text`) |
| `smoke_helpers.py` | Shared utilities for smoke tests |
| `smoke_test_phase*.py` | Phase-specific end-to-end smoke tests |
| `arcade_stop.py` | Closes a manually-started Dungeon Daddy window |
| `dpi.py` | DPI query utility |

---

## Strategy B smoke tests (phase 7, 13)

These tests drive the app via a vision loop:

1. Take a screenshot
2. Send it to Claude (`claude-sonnet-4-6`) to classify the current wizard step
3. Act (type a message, click a button)
4. Repeat until the dungeon is generated or an error is detected

After each run a structured chat log (`phase*_b34_chatlog_<timestamp>.json`) is
written to `tools/screenshots/` — useful for debugging wizard conversations.

Requires both `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`.
