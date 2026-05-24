# Features

Each feature lists its acceptance criteria and the test(s) that must be written
**before** implementation begins. Features are ordered by recommended build sequence.

---

## F-01 · Data Models

**Description:** All Pydantic models defined in `dungeon_daddy/data/models.py` are
validated, serialisable, and deserializable.

**Acceptance criteria:**
- All model fields have correct types and defaults
- A `Dungeon` round-trips through `model_dump(mode="json")` → `model_validate()` without data loss
- `Connection` serialises `from_room`/`to_room` as `from`/`to` in JSON (via alias)
- Invalid data (wrong type, missing required field) raises a `ValidationError`
- `SessionState` starts with empty transcript and empty visited rooms

**Tests to write first:** `tests/unit/data/test_models.py`

---

## F-02 · Dungeon Repository

**Description:** `DungeonRepository` reads and writes dungeon and session JSON files
from the user data directory. The bundled sample loads correctly.

**Acceptance criteria:**
- `save()` writes a pretty-printed (indent=2) JSON file
- `load()` returns a valid `Dungeon` equal to what was saved
- `load()` raises `FileNotFoundError` for a missing name
- `list_dungeons()` returns only `.json` stems, not `_session.json` files
- `save_session()` writes a file named `<dungeon_id>_session.json`
- `load_session()` returns `None` if no session file exists
- `load_sample()` returns the Tomb of the Forgotten King with 3 levels and 9 rooms total
- Files are never overwritten silently — existing file is replaced atomically (write to temp, rename)

**Tests to write first:** `tests/unit/data/test_repository.py`

---

## F-03 · LLM Provider Interface

**Description:** `LLMProvider` Protocol is defined. `AnthropicProvider` implements it.
The interface is mockable with `pytest-mock`.

**Acceptance criteria:**
- A mock object satisfying `LLMProvider` can be used anywhere a real provider is expected
- `AnthropicProvider.complete()` returns a non-empty string when called with valid messages
- `AnthropicProvider.stream()` yields at least one string chunk
- `AnthropicProvider` reads `ANTHROPIC_API_KEY` from environment if `api_key` is not passed
- `model_id` property returns the model string passed at construction

**Tests to write first:** `tests/unit/llm/test_provider.py`
- Unit tests mock the `anthropic.Anthropic` client — no real API calls
- Integration test in `tests/integration/test_llm_integration.py` makes one real call
  (skipped if `ANTHROPIC_API_KEY` is not set)

---

## F-04 · Design Agent

**Description:** `DesignAgent` builds a valid message list from chat history and dungeon
context and calls its injected provider.

**Acceptance criteria:**
- `DesignAgent.chat()` calls `provider.complete()` exactly once
- The system prompt passed to `complete()` contains the dungeon title
- The `history` list is passed through unchanged as the messages argument
- The return value is whatever the provider returns (no wrapping)

**Tests to write first:** `tests/unit/llm/test_design_agent.py`

---

## F-05 · Dungeon Master Agent

**Description:** `DungeonMasterAgent` builds context from room + level + dungeon
and calls its injected provider.

**Acceptance criteria:**
- `DungeonMasterAgent.respond()` calls `provider.complete()` exactly once
- The system prompt contains the current room's name and note
- The system prompt contains the level's ecology
- The return value is the provider's raw response

**Tests to write first:** `tests/unit/llm/test_dm_agent.py`

---

## F-06 · Map Renderers — Grid

**Description:** `GridRenderer` draws a graph-paper map of a `Level` within a given region.

**Acceptance criteria:**
- `GridRenderer.draw()` calls at least one `arcade.draw_rect_filled()` per room
- Rooms not in `visited` are drawn with `BG_2` fill
- The current room is drawn with `TEAL` stroke
- Connections of type `hole` use a dashed line (via `line_width` or texture)
- Entry markers are drawn as teal circles

**Tests to write first:** `tests/unit/map/test_grid_renderer.py`
- Use `unittest.mock.patch` on `arcade.draw_*` functions to verify calls without
  opening a window

---

## F-07 · Map Renderers — Tiles

**Description:** `TilesRenderer` draws a shaded top-down tile view.

**Acceptance criteria:**
- Each cell of each room is drawn individually
- Edge bevels are drawn only on top/left edges where the adjacent cell is empty
- The current room has an animated overlay (opacity changes over time)

**Tests to write first:** `tests/unit/map/test_tiles_renderer.py`

---

## F-08 · Map Renderers — Graph

**Description:** `GraphRenderer` draws rooms as nodes and connections as edges.

**Acceptance criteria:**
- Each room is rendered as a circle positioned by its grid centre
- Each non-stair connection is drawn as a line with a type label
- Nodes not in `visited` are drawn with `BG_1` fill

**Tests to write first:** `tests/unit/map/test_graph_renderer.py`

---

## F-09 · Loop Overlay

**Description:** `LoopOverlay` draws path A (teal) and path B (violet) arcs
over the map when an active loop is set.

**Acceptance criteria:**
- No drawing occurs if `active_loop` is `None`
- Path A is drawn as solid teal lines through room centres (in path_a order)
- Path B is drawn as dashed violet lines (in path_b order)
- Entry and goal labels appear at the first and last room of path A

**Tests to write first:** `tests/unit/map/test_loop_overlay.py`

---

## F-10 · Window and Views

**Description:** `DungeonDaddyWindow` opens, displays the chrome, and switches
between `DesignView` and `PlayView`.

**Acceptance criteria:**
- Window opens at 1400×900
- Chrome (menu bar + title bar) is drawn on every frame
- Switching mode replaces the active view without reloading the dungeon
- Both views receive the same `Dungeon` object

**Tests:** Window and views require a running Arcade context. Focus unit tests on the
renderer and panel logic. Integration tests for the window itself are out of scope
for the initial build — manual verification is acceptable here.

---

## F-11 · Dungeon Tree Panel (Design Mode)

**Description:** Left panel in Design Mode shows a collapsible tree of all levels
and rooms, with loop-path highlighting.

**Acceptance criteria:**
- All levels are shown; all rooms appear under their level when expanded
- Clicking a level header toggles collapsed/expanded
- Clicking a room row fires `on_select(room_id)`
- Room rows are coloured by path membership (A=teal, B=violet, both=indigo, neither=INK_3)

---

## F-12 · Design Chat Panel

**Description:** Centre panel in Design Mode. Scrollable chat history with GM/DM bubbles.
Input sends to `DesignAgent` in a background thread.

**Acceptance criteria:**
- Chat history scrolls to the bottom on each new message
- Sending a message appends a GM bubble immediately
- A "thinking…" indicator appears while the agent is responding
- When the agent responds, the indicator is replaced with a DM bubble
- Ctrl+Enter sends the message; Enter inserts a newline
- Quick chip buttons pre-fill the input

---

## F-13 · Inspector Panel — Settings Tab

**Description:** Right panel, Settings tab. Editable party/dungeon settings and
a room inspector for the selected room.

**Acceptance criteria:**
- Party size, party level, theme, level count, complexity are all editable
- Changing values updates local state (not the dungeon on disk)
- When a room is selected in the tree, the room inspector card appears with
  correct name, type, dimensions, and note

---

## F-14 · Inspector Panel — Loops Tab

**Description:** Right panel, Loops tab. Full loop editor per level.

**Acceptance criteria:**
- Level picker shows all levels; active level is highlighted
- Primary loop card shows the active loop's pattern name, cycle diagram, path A and B chip rows
- Pattern library shows all 9 patterns as cards with mini-cycle diagram
- Clicking a pattern card applies it as the primary loop, auto-assigning rooms
- Shift-clicking adds it as a sub-loop
- Removing a sub-loop (× button) removes it from the list
- Activating a loop fires `on_activate_loop(loop_id)` which updates the tree highlighting

---

## F-15 · Play Chat Panel

**Description:** Left panel in Play Mode. Current room banner + scrollable chat +
`DungeonMasterAgent` integration.

**Acceptance criteria:**
- Current room banner updates when `current_room_id` changes
- Clicking a room on the map triggers a GM movement message + DM narration
- DM narration is generated by `DungeonMasterAgent` in a background thread
- Quick chips ("Describe room", "Search", "Roll initiative", "Listen") pre-fill the input
- Turn counter increments on each GM send

---

## F-16 · Dungeon Persistence (Save / Load)

**Description:** User can save the current dungeon and session, and reload a
previously saved dungeon.

**Acceptance criteria:**
- "File → Save" writes the current dungeon and session state to JSON
- "File → Open" shows available dungeons and loads the selected one
- "File → New" loads a blank dungeon template
- The sample dungeon loads at first launch if no user dungeons exist
- Saved files are valid, pretty-printed JSON readable in a text editor

---

## F-16b · Loop Auto-Assignment Algorithm

When a pattern card is clicked and applied to a level, rooms are assigned to
path A and path B automatically using the following algorithm:

1. Build a directed adjacency list from the level's `connections`
   (excluding `stair_up` / `stair_down` connections).
2. Identify `entry`: the room with the most connections (hub) or, if tied,
   the lowest-numbered room.
3. Identify `goal`: the room furthest from `entry` by hop count (BFS).
4. Find the shortest path from `entry` to `goal` → assign as `path_a`.
5. Find an alternate path from `entry` to `goal` that shares no intermediate
   rooms with `path_a` → assign as `path_b`.
   - If no fully disjoint path exists, find the alternate path with the
     **fewest overlapping intermediate rooms** with `path_a`. If multiple
     alternate paths have the same overlap count, choose the one with the
     fewest total hops (shortest). If still tied, choose the first found by BFS.
6. If only one path exists (linear dungeon), `path_b = path_a` (loop degrades
   gracefully — the user can manually reassign chips).

The algorithm does **not** guarantee the semantics of the chosen pattern (e.g.,
that path A is actually "short"). It produces a structurally valid loop; the
designer is expected to review and adjust room assignments using the drag UI.

**Tests to write first:** Add `test_loop_auto_assign()` to `tests/unit/data/test_models.py`
using the Tomb of the Forgotten King level data.

---

## F-16c · Dungeon Validation Rules

A dungeon is "valid" when all of the following hold for every level:

1. **Connectivity:** Every room is reachable from the first room via `connections`
   (ignoring direction). No orphan rooms.
2. **Loop consistency:** Every room ID referenced in `loop.path_a` and
   `loop.path_b` exists in the level's `rooms` list.
3. **Entry/goal exist:** Every `Loop.entry` and `Loop.goal` references a real room.
4. **No self-connections:** No connection has `from_room == to_room`.
5. **Grid bounds:** Every room's `x + w <= level.width` and `y + h <= level.height`.
6. **No duplicate room IDs:** All `room.id` values within a level are unique.

Validation is run by `DungeonRepository` on load and by `DesignView` when the
user clicks "Validate" (or triggers the Design Agent). The result is exposed as:

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]   # human-readable, one per failed rule
```

The tree header shows "✓ validated" when the last validation passed, and
"⚠ {n} issues" when it failed.

**Tests to write first:** `tests/unit/data/test_models.py` — `test_validate_dungeon_*`

---

## F-18 · Dungeon Creation Wizard (Per-Level Flow)

**Description:** When Design Mode opens with no dungeon loaded, `DungeonWizardAgent`
drives the chat through a two-phase structured Q&A. Phase 1 collects dungeon-wide
settings. Phase 2 walks the GM through designing each level one at a time — for each
level the GM chooses a main loop pattern and an optional sub-loop, then the level is
generated immediately so the GM can explore it before moving on.

### Phase 1 — Global Collection

**Acceptance criteria:**
- Chat opens in wizard mode with a greeting and first question
- Agent collects: title (optional), theme, mood/atmosphere, setting/location, party
  (size, level, class mix), main quest, number of levels
- Agent asks clarifying questions before confirming
- When GM confirms global settings, agent outputs a `DungeonBrief` block
  (detected via ` ```brief ` marker)
- `DungeonWizardAgent.parse_brief()` extracts the brief correctly
- `DungeonBrief` contains: title, theme, setting, party_composition, main_quest,
  num_levels — **no loop patterns** (those are collected per level)
- Wizard immediately transitions to Level 1 design dialogue

### Phase 2 — Level-by-Level Loop Design

For each level N (1 … num_levels):

**Acceptance criteria:**
- Wizard describes level N's place in the dungeon (entry, mid, boss) and offers an
  ecology/flavor suggestion the GM can accept or override
- Wizard presents all 9 loop patterns with brief descriptions, asks GM to choose
  the main loop pattern
- Wizard asks whether a sub-loop is desired; if yes, offers the remaining 8 options
- When GM confirms the level design, agent outputs a `LevelBrief` block
  (detected via ` ```level_brief ` marker)
- `DungeonWizardAgent.parse_level_brief()` extracts a `LevelBrief` correctly
- Generation triggers immediately — the GM sees "Generating level N…" in chat
- Generated level appears in `DungeonTreePanel` and the Test Drive button activates
- GM can type in chat to request changes to the current level before moving on
- When GM is satisfied (or types `/next`), the wizard moves to level N+1
- After all levels are designed and generated, the dungeon is saved and edit mode activates
- If the GM types `/reset` at any point, the brief and all generated levels are cleared
  and the wizard restarts from the beginning

### New Data Model

```python
@dataclass
class LevelBrief:
    level_number: int
    ecology: str           # flavor description for the generator
    main_loop_pattern: str # key from loop_patterns.json
    sub_loop_pattern: str | None = None
```

**Updated `DungeonBrief`:** remove `primary_loop_pattern` and `optional_sub_loop`
fields — these are now per-level in `LevelBrief`.

**Tests to write first:** `tests/unit/llm/test_wizard_agent.py`
- Mock the provider; assert the global system prompt does NOT include the pattern list
- Assert `parse_brief()` extracts a `DungeonBrief` (no loop fields) from a valid
  ` ```brief ` block; returns `None` when no block is present
- Assert the level-design prompt contains all 9 pattern descriptions
- Assert `parse_level_brief()` extracts a `LevelBrief` from a valid
  ` ```level_brief ` block; returns `None` when no block is present

---

## F-19 · Level-by-Level Generation (Immediate, Per-Level)

**Description:** `DungeonGeneratorAgent` generates each level immediately after its
`LevelBrief` is confirmed. It validates the output and retries up to 3 times on
failure. The GM sees the level in the tree as soon as it is ready and can explore
it via Test Drive. The GM can request changes via chat before the wizard moves on
to the next level.

**Acceptance criteria:**
- Generation is triggered per level as soon as the wizard confirms a `LevelBrief` —
  not batched after all levels are collected
- Each level is generated as a valid `Level` JSON matching the Pydantic schema,
  using the `LevelBrief` (ecology + loop patterns) as context
- `validate_dungeon()` is run on each level before it is accepted
- If validation fails, errors are fed back to the LLM (up to 3 attempts);
  each retry shows "Revising level N…" in chat
- After 3 failed attempts, an error appears in chat and the GM can type to intervene;
  the wizard waits for GM input before retrying or skipping
- Generated level appears in `DungeonTreePanel` immediately
- Test Drive button activates as soon as at least one level exists (partial dungeon)
- GM can switch to Test Drive to explore the level, then return to Design Mode
- When GM is satisfied with the level, the wizard moves to the next level
- After all levels, a cross-level stair consistency check runs:
  every `stair_down` in level N must have a matching `stair_up` in level N+1
- After all levels pass, the dungeon is saved and Design Mode switches to edit mode

**Tests to write first:** `tests/unit/llm/test_generator_agent.py`
- Mock the provider; assert `parse_level()` extracts a valid `Level` from a
  ` ```json ` block
- Assert `generate_level()` receives the `LevelBrief` ecology and loop pattern
  in the context
- Assert validation errors are included in the context on retry calls
- Assert `parse_level()` raises `ValueError` on a response with no ` ```json ` block

---

## F-20 · Room Memory (`/remember`)

**Description:** In Play Mode, the GM records what happened in a room using
`/remember <event>`. Events accumulate in per-level markdown files. The DM Agent
uses this memory when the party revisits a room. Memory can be edited.

**Acceptance criteria:**
- `/remember <text>` appends a dated event to the current room's section in the
  level memory file
- A system bubble `"Remembered: <text>"` appears in chat immediately
- No LLM call is made for `/remember` commands
- `DungeonMasterAgent.respond()` receives `room_memory` as context; the system
  prompt includes past events when memory exists
- "Edit Memory" button appears in Play Mode when the current level has a memory file
- Clicking "Edit Memory" opens a `UITextArea` overlay with the raw markdown
- GM can edit and save; `DungeonRepository.save_room_memory()` overwrites the file
- Memory files are human-readable markdown editable outside the app
- Memory survives session reload: closing and reopening the dungeon preserves all events

**Tests to write first:** `tests/unit/data/test_repository.py`
- `test_append_room_event_creates_file` — first event creates the directory and file
- `test_append_room_event_creates_section` — event for a new room creates the `##` header
- `test_append_room_event_appends` — second event for same room appends, not overwrites
- `test_load_room_memory_missing` — returns `""` when no file exists
- `test_save_and_load_room_memory` — round-trip save/load preserves content

---

## F-17 · Loop Pattern Catalog

**Description:** All 9 patterns from the design are available in the app.

The 9 patterns:

| Key | Name | Source |
|---|---|---|
| `lock_key` | Lock & Key | Dormans |
| `gambit` | Gambit | Dormans |
| `foreshadow` | Foreshadowing | Sersa Victory |
| `fork_choice` | True Fork | Dormans |
| `pursuit` | Pursuit | Sersa Victory |
| `secret_shortcut` | Secret Shortcut | Alexandrian |
| `hub_spoke` | Hub & Spoke | Alexandrian |
| `bottleneck` | Branch & Bottleneck | Dormans |
| `shortcut_back` | Shortcut Back | Alexandrian |

**Acceptance criteria:**
- All 9 patterns load from `dungeon_daddy/data/loop_patterns.json`
- Each pattern has: key, name, blurb, path_a_length, path_b_length, beats, source
- `LoopPatternCatalog.load_bundled()` returns all 9 without errors

**Tests to write first:** Include in `tests/unit/data/test_models.py`

---

## F-21 · Stepper Rail Opacity (Play Mode)

**Status: COMPLETE**

**Description:** The right-side stepper rail in Play Mode is fully opaque so map content never shows through it, including after window resize.

**Acceptance criteria:**
- Stepper rail background is painted solid (`BG_1`) before drawing widgets
- Map content does not bleed into the stepper rail at any window size
- Up/down buttons and level label remain visible and clickable after resize

**Detail:** `spec/FEATURE_RA_PANEL_TRANSPARENCY.md`

---

## F-22 · Map Pan Tool (Play Mode)

**Status: COMPLETE**

**Description:** A dedicated Pan tool in the map tab bar lets the GM drag the map viewport without accidentally selecting rooms. Pan offset is applied to all rendering and hit-testing so room click coordinates stay accurate after panning.

**Acceptance criteria:**
- [Pan] button appears in tab bar, visually separated from Grid/Tiles/Graph tabs
- Active tab is highlighted with teal border/bg; only one tab active at a time
- Dragging inside the map viewport while Pan is active moves map content smoothly
- Dragging from outside the map viewport (e.g. chat panel) has no effect
- Map content is scissor-clipped to the viewport — no bleed into adjacent panels
- Switching back to Grid/Tiles/Graph deactivates Pan and restores room-click behaviour
- Room hit-testing respects the current pan offset

**Tests:** `tests/unit/map/test_map_pan.py`

**Detail:** `spec/FEATURE_MAP_PAN.md`

---

## F-23 · Dungeon → Validate with Auto-Fix

**Status: COMPLETE**

**Description:** `Dungeon → Validate` runs `validate_dungeon()` on the loaded dungeon and reports results via a native dialog. When auto-fixable errors are present the GM is offered a Yes/No prompt before any changes are made. Fixes are applied in-memory only; the GM must save explicitly to persist them.

**Acceptance criteria:**
- `Dungeon → Validate` is available in the menu bar and calls `validate_dungeon()`
- If no dungeon is loaded, shows "No dungeon loaded."
- If the dungeon is valid, shows "Dungeon is valid."
- If errors are found and none are auto-fixable, lists all errors
- If auto-fixable errors exist, prompts "N error(s) found. X can be fixed automatically. Apply automatic fixes now?"
- Accepting the prompt applies fixes and re-validates; result shows fixes applied and any remaining errors
- Declining the prompt shows the original error list unchanged
- `auto_fix_dungeon(dungeon) -> list[str]` in `models.py` handles two fix types:
  - Empty `loop.explanation` → set to `"Explanation pending."`
  - Extra `type="main"` loops (beyond the first) → demoted to `type="sub"`
- Room spacing violations and other structural errors are reported but not auto-fixed

**Tests:** `tests/unit/data/test_models.py` — `test_auto_fix_*`

---

## F-24 · Menu Completions — Minimise and About

**Status: COMPLETE**

**Description:** Implements the remaining trivial menu stubs.

**Acceptance criteria:**
- `Window → Minimise` iconifies the application window via Arcade/Pyglet's `minimize()`
- `Help → About` shows a native info dialog with the app name and description
- Both items are no longer dimmed in the dropdown

---

## F-25 · Native Dialog Window Ownership (HWND Parenting)

**Status: COMPLETE**

**Description:** All tkinter dialogs (message boxes, file picker) are owned by the Arcade window at the Win32 level so they cannot be buried behind it.

**Acceptance criteria:**
- Every tkinter dialog is created via `DungeonDaddyWindow._make_tk_root()`, which calls `SetWindowLongPtrW(tk_hwnd, GWL_HWNDPARENT, arcade_hwnd)` to set the Arcade window as the dialog's Win32 owner
- Clicking away to the Arcade window brings the dialog back to the foreground
- If `self._hwnd` is unavailable the call is silently skipped (no crash)
- Applies to: error dialog, info dialog, yes/no prompt, folder picker

---

## F-26 · DM Stateful Conversation

**Status: COMPLETE**

**Detail spec:** `spec/FEATURE_DM_STATEFUL_CONVERSATION.md`

**Description:** DM chat in Play Mode gains persistent conversation history within a
session and automatic memory tagging. Currently every LLM call is stateless (single
message only) and the GM must manually `/remember` anything worth keeping.

**Feature A — Persistent Conversation History:**
`PlayView` accumulates `_dm_history: list[LLMMessage]` and passes it to every DM call.
History is compacted by dropping oldest turn pairs when it exceeds a 2 000-token budget.
Cleared on level change. `/clear` command resets it manually.

**Feature B — Auto-Remember via `[REMEMBER]` tag:**
The DM `SYSTEM_PROMPT` instructs the model to append `[REMEMBER: one sentence]` for
significant events. `PlayView` parses and strips the tag, calls `append_room_event()`
automatically, and posts a `📝 Noted:` system message. Manual `/remember` unchanged.

**Acceptance criteria:**
- DM call for message B includes message A and prior DM response in its history
- History clears on level change; `/clear` resets and confirms in chat
- Oldest turn pair dropped (not split) when history exceeds 2 000 tokens
- `[REMEMBER: ...]` tag is stripped from chat display and written to `memory/level_N.md`
- `📝 Noted: <text>` system message appears after auto-remember
- Manual `/remember <text>` continues to work unchanged

**Tests to write first:**
- `tests/unit/views/test_play_view_history.py`
- `tests/unit/views/test_play_view_remember.py`
- `tests/unit/agents/test_dm_agent_history.py`

---

## F-27 · Loop Toggle Strip (Play Mode)

**Status: COMPLETE**

**Description:** The map panel in Play Mode displays a row of pill chips — one per loop defined in the active level. Clicking a pill activates that loop, updating the `LoopOverlay` and firing the `on_activate_loop` callback.

**Acceptance criteria:**
- Pill chips are drawn in `MapPanel` for each loop in the active level
- Clicking a pill updates `state.active_loop_id` and fires `on_activate_loop(loop_id)`
- `LoopOverlay` redraws path A/B arcs when the active loop changes
- Only one loop is active at a time; clicking the active pill has no effect

**Tests:** `tests/unit/ui/test_map_panel.py`

---

## F-28 · Loop Activation System Message (Play Mode)

**Status: COMPLETE**

**Description:** When the GM activates a loop in Play Mode, a system bubble is posted to the DM chat explaining the loop's narrative structure (entry room, goal room, path A and path B descriptions).

**Acceptance criteria:**
- Activating a loop via the toggle strip posts a system bubble to the chat log
- Bubble includes: loop name, entry room, goal room, path A room list, path B room list
- Bubble is styled as a system message (not a GM or DM bubble)
- No LLM call is made when posting the activation message

**Tests:** `tests/unit/views/test_play_view.py`

---

## F-29 · DM Agent Loop Context

**Status: COMPLETE**

**Description:** `DungeonMasterAgent.respond()` accepts an `active_loop` parameter. When a loop is active, a loop context section is injected into the system prompt so the DM can reference the narrative structure in its responses.

**Acceptance criteria:**
- `DungeonMasterAgent.respond()` accepts `active_loop: Loop | None = None`
- When `active_loop` is provided, the system prompt includes: loop name, entry room, goal room, path A rooms, path B rooms
- When `active_loop` is `None`, no loop section is added to the prompt
- Existing prompt content is unchanged when no loop is active

**Tests:** `tests/unit/llm/test_dm_agent.py`

---

## F-30 · Linux Platform Backend (WSL2)

**Status: FUTURE**

**Description:** Implement `tools/platform_linux.py` so the smoke-test infrastructure
runs natively on Linux (including WSL2). The abstraction boundary from
`FEATURE_PORTABLE_UI_TESTS.md` Issue 1 is already in place; this feature fills in
the real backend behind it.

**Background:**

`tools/platform_stub.py` raises `NotImplementedError` on all non-Windows platforms.
On Linux the equivalent Win32 operations are available via `xdotool` (CLI) or
`python-xlib` / `Xlib` (pure Python). WSL2 with an X server (e.g. WSLg, VcXsrv,
or Xming) can run the Arcade app and expose an X11 display, making the full
smoke-test suite runnable on Windows developer machines without a second OS.

**Plan:**

1. Add `tools/platform_linux.py` implementing the same interface as
   `platform_win32.py`: `set_dpi_awareness`, `find_window`, `get_window_rect`,
   `get_system_metrics`, `set_window_pos`, `post_message`, `set_cursor_pos`,
   `mouse_event`, `send_click`, `send_key_combo`, `send_scroll`, `send_text`,
   `get_dpi_scale`. Use `xdotool` via `subprocess` for window management and input;
   use `Xlib.display` for pixel geometry queries.

2. Update `tools/platform_host.py` to return `platform_linux` when
   `sys.platform == "linux"`.

3. `set_dpi_awareness()` is a no-op on Linux (X11 does not have a DPI-awareness
   mode equivalent). `get_dpi_scale()` reads the Xft.dpi resource via
   `xrdb -query` or falls back to `1.0`.

4. `find_window(title)` calls `xdotool search --name <title>` and returns the
   first window ID as an int (0 if not found).

5. No new third-party Python libraries beyond `python-xlib` (already available in
   most Linux environments). `xdotool` must be installed in the WSL2 environment
   (`sudo apt install xdotool`).

6. Update `tools/platform_stub.py` error message to remove "requires Windows" and
   broaden it to: _"UI smoke tests require a supported platform (Windows or Linux
   with X11). Contribute a platform backend for your OS."_

**Acceptance criteria:**

- `tools/platform_linux.py` satisfies the same interface as `platform_win32.py`
- `platform_host.get_platform()` returns `platform_linux` on `sys.platform == "linux"`
- The smoke tests pass in a WSL2 environment with WSLg (or equivalent X server) and
  `xdotool` installed
- `get_dpi_scale()` returns `1.0` on a default WSL2 display (no HiDPI config)
- `set_dpi_awareness()` is a no-op and does not raise

**Testing guidance:**

- Mock `subprocess.run` to simulate `xdotool` output in unit tests — no X server
  required for the unit test suite
- Integration tests require a running WSL2 environment with an X display; mark them
  `@pytest.mark.integration` and skip if `DISPLAY` is not set
- `platform_host` routing is already tested via `test_platform_host.py`; add a
  parametrized case for `"linux"` → `platform_linux`

**Dependencies:**

- `FEATURE_PORTABLE_UI_TESTS.md` Issue 1 (platform abstraction) — already complete
- WSL2 with WSLg or a manually configured X server on the developer machine
- `xdotool` installed in the WSL2 environment (`sudo apt install xdotool`)

---

## F-31 · Test Drive vs. Start Play

**Status: PLANNED**

**Detail spec:** `spec/FEATURE_TEST_DRIVE_VS_START_PLAY.md`

**Description:** The "Test Drive" and "Start Play →" buttons in the Inspector footer
currently both launch Play Mode identically. This feature gives them distinct,
correct behaviour: Test Drive is an ephemeral sandbox (no disk writes, works on
unsaved dungeons), while Start Play begins or resumes a persistent play session
(requires a saved dungeon, writes session state to disk).

**Acceptance criteria:**

- Clicking "Test Drive" opens Play Mode with no data written to disk during the session
- DM chat, room memory, loop activations, and position from a Test Drive are discarded on exit
- "Start Play →" is disabled (greyed) when the dungeon has not been saved
- Clicking "Start Play →" on a saved dungeon opens Play Mode and writes session state to disk
- Button label changes to "Continue Play →" when any prior session or room memory exists for the dungeon
- Clicking "Continue Play →" restores current level, room, visited rooms, active loop, and play transcript
- Returning from Test Drive to Design Mode discards all play data; returning from Start/Continue Play flushes session to disk

**Tests to write first:**
- `tests/unit/views/test_play_view.py` — transient vs. session load, repo write gating, session flush on hide
- `tests/unit/ui/panels/test_inspector_panel.py` — button disabled state, label switching
- `tests/unit/views/test_design_view.py` — routing split (Test Drive vs Start Play click handlers)
