# Testing & TDD Protocol

## The Vertical Slicing Mandate

**We follow a strict "Tracer Bullet" TDD workflow. Horizontal bulk-testing is prohibited.**

Do not write all tests for a module at once. Follow the **Red-Green-Refactor** loop for one behavior at a time:

1.  **Identify a Public Behavior:** Pick one specific capability from the current `IMPLEMENTATION_PHASES.md` step.
2.  **RED:** Write **one** test targeting the public interface (e.g., a Pydantic model validation or a Repository load).
3.  **GREEN:** Implement the **minimal** application code required to pass that specific test.
4.  **REFACTOR:** Clean the code while ensuring the test stays green.
5.  **REPEAT:** Move to the next behavior.

---

## Test File Map & Priority

Modules must be built following this dependency order. Complete one "Vertical Slice" (Test + Impl) before moving to the next priority level:

| Application module | Test file | Priority |
| :--- | :--- | :--- |
| `dungeon_daddy/data/models.py` | `tests/unit/data/test_models.py` | 1 |
| `dungeon_daddy/data/repository.py` | `tests/unit/data/test_repository.py` | 2 |
| `dungeon_daddy/llm/provider.py` | `tests/unit/llm/test_provider.py` | 3 |
| `dungeon_daddy/llm/agents/*.py` | `tests/unit/llm/test_*.py` | 4-7 |
| `dungeon_daddy/ui/theme.py` | `tests/unit/ui/test_theme.py` | 8 |
| `dungeon_daddy/map/*.py` | `tests/unit/map/test_*.py` | 9-12 |

---

## Strategy by Layer

### 1. Data & Theme (Logic Only)
* **Behavior focus:** Verify that data round-trips correctly and theme constants are valid.
* **Protocol:** No mocking. Use real Pydantic models and `tmp_path`.

### 2. LLM Layer (The "Deep Module" Approach)
* **Behavior focus:** Verify the agent produces correct system prompts and handles errors.
* **Protocol:** **Never make real API calls.** Patch the `anthropic.Anthropic` client using `mocker`.

### 3. Map Renderers (Visual Logic)
* **Behavior focus:** Verify that the correct drawing functions are called with expected parameters.
* **Protocol:** Use `import arcade` (not `from arcade import...`). Patch drawing functions at the module level.

---

## Mock Policy — Use Real Objects Whenever Possible

**Default: no mocks.** Only introduce a mock when a real component cannot run in the test environment. If you find yourself mocking an internal application class, stop and ask whether the real class can be used instead.

### When mocking is mandatory

| What | Why |
| :--- | :--- |
| Arcade rendering (`arcade.draw_*`, `arcade.Window.__init__`) | Requires a GPU/display context |
| OS dialogs (Tkinter `filedialog`, `messagebox`) | Blocks the process waiting for user input |
| External APIs (`OpenAIProvider`, `AnthropicProvider`) | Network calls; non-deterministic; costs money |
| Win32 HWND operations (`ctypes.windll.*`) | Requires a real window handle |

### When mocking is wrong

If a real object can be constructed — even via `__new__` with manual attribute setup — **use it**. Mocking internal application components means your test only verifies that one object calls a method on a mock; it does not verify that the two real objects actually work together.

**Concrete example** (the mistake this rule prevents):

```python
# WRONG — mocks the window; only proves design_view calls set_switch_to_play_enabled
view.window = MagicMock()
view._refresh_play_button_state()
view.window.set_switch_to_play_enabled.assert_called_once_with(False)
```

```python
# RIGHT — uses real window so the wiring is actually exercised
win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
win._menu = win._build_menu()          # real MenuAction created
view.window = win
view._refresh_play_button_state()
assert win._switch_to_play_action.enabled is False   # real flag on real object
```

The first test would pass even if `window.set_switch_to_play_enabled` did nothing. The second test fails unless the full chain — `_refresh_play_button_state` → `set_switch_to_play_enabled` → `_switch_to_play_action.enabled` — is actually wired correctly.

### Rule of thumb

> If renaming or removing an internal method breaks your test but the user-visible behavior is unchanged, you are mocking too deep.

### Constructing real objects without Arcade

Most application objects can be tested without Arcade initialisation using `__new__` + manual attribute setup:

```python
win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
win._repo = DungeonRepository(tmp_path)   # real repo
win._menu = win._build_menu()             # real menu with real MenuActions
win._design_view = MagicMock()            # mock only because DesignView needs Arcade UI
win._play_view = MagicMock()

view = DesignView.__new__(DesignView)
view._repo = repo                         # real repo
view._dungeon = dungeon                   # real model object
view._inspector = MagicMock()             # mock only because InspectorPanel needs Arcade
view.window = win                         # real window — not a mock
```

Only the Arcade rendering components (`_inspector`, `_chat`, `_tree`, `_map`) need to be mocked. Business logic objects (`Window`, `DesignView`, `PlayView`, `DungeonRepository`, all data models) should be real.

---

## Integration Tests
Written only after the unit-level "Tracer Bullets" for a phase are complete:
* `tests/integration/test_dungeon_persistence.py`: Full disk I/O round-trip.
* `tests/integration/test_llm_integration.py`: Real API calls (Requires `ANTHROPIC_API_KEY`).
* `tests/integration/test_play_menu.py`: Menu wiring — real Window + real DesignView + real repo.

---

## Smoke Tests (UI / end-to-end)

Smoke tests live in `tools/smoke_test_phase*.py` and run against a live app window
managed by `UITestHarness`.  Two driving strategies are available.

---

### Strategy A — Pixel-based (rigid sequence)

The default approach for most smoke tests.  Each step is sent at a fixed time and
pixel-color checks confirm the result.

**Use when:**
- The UI flow is deterministic (no LLM variation in response order)
- You are checking colors, layout positions, or button visibility
- The sequence of interactions is always the same

**Example:** `smoke_test_phase16.py` — Play Mode chat, `/clear`, Edit Memory overlay.

---

### Strategy B — Vision-guided (adaptive sequence)

Use the Claude vision API (`claude-sonnet-4-6`) to look at each screenshot and decide
which step to execute next.  Steps are named functions with plain-English descriptions.
The driver loops until a terminal step is reached or `max_steps` is hit.

**Use when:**
- An LLM controls the UI flow and may ask questions in varying order
- A rigid sequence would be brittle (wrong step sent at the wrong time)
- The number of turns is not fixed in advance

**Examples:** `smoke_test_phase7.py`, `smoke_test_phase13.py`

---

**How it works:**

1. Define each possible action as a named step with a vision description and an action function.
   Always include `wait_more`, `error_detected`, and `done`:

```python
_BASE_STEPS: dict[str, tuple[str, Callable | None]] = {
    "send_concept": (
        "Wizard is greeting and waiting for an initial dungeon concept.",
        lambda h: _send(h, "My dungeon concept..."),
    ),
    "send_details": (
        "Wizard asked for specifics: name, setting, party, quest.",
        lambda h: _send(h, "The dungeon is called..."),
    ),
    "wait_more": (
        "Wizard is still generating — no new complete DM message visible yet.",
        None,  # no-op; loop wait handles the pause
    ),
    "error_detected": (
        "The chat shows an error message — a ⚠ warning symbol is visible in a DM bubble. Stop immediately.",
        None,  # terminal
    ),
    "done": (
        "Wizard flow complete — level entry visible in DungeonTree, or final state reached.",
        None,  # terminal
    ),
}

_TERMINAL_STEPS = {"done", "error_detected"}
```

2. `_wizard_next_step(screenshot, available_steps, history)` sends the screenshot to Claude
   and returns a `_StepClassification(step, dm_response)` — both the next step name **and**
   the last DM message text extracted from the screenshot in a single API call.

   The classifier prompt asks for a JSON response:
   ```
   {"step": "send_details", "dm_response": "First sentence of last DM bubble, max 120 chars"}
   ```
   dm_response must be a single line (no newlines).  A regex fallback extracts the step name
   if `json.loads` fails (e.g. when Claude includes a long multi-line DM message):
   ```python
   m = re.search(r'"step"\s*:\s*"([^"]+)"', raw)
   step = m.group(1) if m else "wait_more"
   ```

3. `_vision_drive_wizard(h, steps, label)` runs the loop: screenshot → classify → act →
   wait → repeat.  Returns `(history, chat_log)`.

4. Steps already taken are passed as `history` so Claude does not repeat itself.

---

**Chat log:**

`_vision_drive_wizard` builds a structured `list[_ChatEntry]` as it runs and writes it to
`tools/screenshots/<label>_chatlog_<timestamp>.json` on exit.  Each entry contains:

```python
@dataclasses.dataclass
class _ChatEntry:
    step_index: int
    action: str          # step name chosen by classifier
    gm_sent: str | None  # exact text sent to wizard (None for wait/terminal steps)
    dm_response: str     # last DM message text extracted from screenshot
    screenshot: str      # filename in tools/screenshots/
    timestamp: str       # ISO-8601
```

Use the log for post-run analysis: feed the JSON + screenshots back to Claude to review
the conversation quality, identify where the wizard went off-track, or diagnose failures.

---

**Vision assertions:**

Use `_vision_assert(screenshot_path, question)` instead of pixel color checks for any
state that requires understanding layout or content (e.g. "does the tree show a level?").
It asks Claude a yes/no question about the screenshot.  Reserve pixel checks (`_has_violet`,
`_has_teal_in_messages`) only for simple, fast checks where color alone is sufficient
(e.g. launch checks, API-key guard).

```python
level_in_tree = _vision_assert(
    shot,
    "Does the narrow DungeonTree panel on the far left show a named level entry? "
    "Ignore the panel header bar.",
)
```

---

**Stopping mid-flow for assertions:**

Add a custom terminal step to pause the loop at a specific state:

```python
_OVERWRITE_DETECTED: _WizardStep = (
    "Wizard detected existing docs and is asking whether to overwrite them. Stop here.",
    None,  # terminal
)
steps["overwrite_detected"] = _OVERWRITE_DETECTED
history, chat_log = _vision_drive_wizard(h, steps, label="b1")
# → assert file state here, then manually send the next message
```

---

**Requirements:**
- `ANTHROPIC_API_KEY` must be set (`.env` or environment) — drives the vision classifier
- `OPENAI_API_KEY` (or whichever key the app's LLM uses) must also be set
- Each step waits `_STEP_WAIT` seconds (default 20 s) after acting before the next screenshot
- `wait_more` is a no-op step — Claude returns it when the wizard is still thinking,
  causing another wait cycle without sending a message
- `error_detected` is always a terminal step — test fails fast on any ⚠ error in chat
- Set `max_steps` high enough for the longest plausible conversation (default 20)

---

## Checklist Per Cycle
- [ ] Does this test describe a user-facing behavior?
- [ ] Am I using only the public interface?
- [ ] Is this the absolute minimal code to pass?
- [ ] Did I run `pytest` to confirm the RED state before writing the implementation?
- [ ] For every mock: is it mandatory? (GPU/network/OS dialog) If not, replace with the real object.