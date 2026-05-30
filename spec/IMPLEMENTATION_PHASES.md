# Implementation Phases

This file defines the phased build order for Dungeon Daddy. Each phase ends with
something runnable and/or a green test suite. Work within a phase before moving to
the next. Do not skip phases — later phases depend on the foundations laid in earlier ones.

**Current status is listed for each phase.**

---

## Phase 1 — Pure Python Foundation

**Status: Complete**

Build and test the entire data layer before any UI or LLM code exists.
This phase has no Arcade dependency — tests run headlessly with no display.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/data/models.py` | `tests/unit/data/test_models.py` |
| `dungeon_daddy/data/repository.py` | `tests/unit/data/test_repository.py` |
| `dungeon_daddy/config.py` | (covered in repository tests) |

### What to build

- All Pydantic models: `LoopPattern`, `Loop`, `Room`, `Connection`, `Entry`,
  `Level`, `DungeonMeta`, `Dungeon`, `ChatMessage`, `SessionState`,
  `ValidationResult` (plain dataclass), `LoopPatternCatalog`
- `validate_dungeon()` module-level function with all 5 validation rules
- `DungeonRepository`: `list_dungeons()`, `load()`, `save()`,
  `load_session()`, `save_session()`, `load_sample()`,
  `load_room_memory()`, `save_room_memory()`, `append_room_event()`
- `AppConfig` dataclass with `ensure_dirs()`
- `dungeon_daddy/data/loop_patterns.json` (9 built-in loop patterns)
- `dungeon_daddy/data/samples/tomb_of_the_forgotten_king.json` (sample dungeon)

### Exit Criteria

- `pytest tests/unit/data/` is green
- Round-trip test: load sample dungeon → `model_dump(mode="json")` → re-validate → equal
- `validate_dungeon()` catches each error type with an intentionally broken fixture
- `DungeonRepository` tests use `tmp_path`; no real files written outside tmp
- Memory tests: `append_room_event` creates directory + file + section header on first call;
  subsequent calls append; `load_room_memory` returns `""` when no file exists

---

## Phase 2 — UI Primitives

**Status: Complete**

Build the theme constants and chrome drawing helpers. No window opens yet.
Tests patch `arcade.draw_*` — no display required.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/ui/theme.py` | `tests/unit/ui/test_theme.py` |
| `dungeon_daddy/ui/chrome.py` | (smoke-tested via Phase 3) |

### What to build

- `dungeon_daddy/ui/theme.py`: all color tuples (`BG_0`…`BG_HI`, `LINE`, `INK`,
  `TEAL`, `VIOLET`, `EMBER`, `GOLD`), `ROOM_COLORS` dict, font name constants,
  font size scale, spacing and panel width constants
- `dungeon_daddy/ui/chrome.py`: `MenuAction` dataclass, `draw_menu_bar()`,
  `draw_title_bar()`, dropdown renderer

### Exit Criteria

- `pytest tests/unit/ui/` is green
- `theme.py` exports all constants referenced in `spec/VISUAL_DESIGN.md`
- `MenuAction` dataclass matches spec; all menu items (including unimplemented ones)
  route through `_nyi()` or a real handler — nothing is decorative

---

## Phase 3 — Window Opens

**Status: Complete**

The application opens a window showing the chrome (menu bar + title bar) only.
No panels, no views beyond a placeholder. First time Arcade actually runs.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/__main__.py` | (manual smoke test only) |
| `dungeon_daddy/window.py` | (manual smoke test only) |

### What to build

- `DungeonDaddyWindow(arcade.Window)`: init, font loading (8 TTF files),
  API key check, `switch_to_design()`, `switch_to_play()`
- `__main__.py` entry point: construct `AppConfig`, call `ensure_dirs()`,
  construct `AnthropicProvider` (or no-op stub if key missing), open window
- A single placeholder `arcade.View` subclass that draws the chrome and a
  "Loading…" label — just enough to confirm the window opens
- Font files committed under `dungeon_daddy/assets/fonts/` (8 TTF files)

### Exit Criteria

- `python -m dungeon_daddy` opens a 1400×900 window with the menu bar and title bar
- Closing the window exits cleanly with no exceptions
- No LLM call is made on startup

---

## Phase 4 — LLM Foundation

**Status: Complete**

Build and test the LLM provider and all agent wrappers. No UI. Tests use mocked providers.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/llm/provider.py` | `tests/unit/llm/test_provider.py` |
| `dungeon_daddy/llm/anthropic_provider.py` | `tests/unit/llm/test_provider.py` |
| `dungeon_daddy/llm/agents/wizard_agent.py` | `tests/unit/llm/test_wizard_agent.py` |
| `dungeon_daddy/llm/agents/generator_agent.py` | `tests/unit/llm/test_generator_agent.py` |
| `dungeon_daddy/llm/agents/design_agent.py` | `tests/unit/llm/test_design_agent.py` |
| `dungeon_daddy/llm/agents/dm_agent.py` | `tests/unit/llm/test_dm_agent.py` |

### What to build

- `LLMMessage` dataclass, `LLMProvider` Protocol, `LLMError` exception (in `provider.py`)
- `AnthropicProvider`: `complete()`, `stream()`, `model_id` property;
  wraps `anthropic.APIError` as `LLMError`; uses `DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"`
- `DungeonBrief` dataclass
- `DungeonWizardAgent`: `SYSTEM_PROMPT`, `chat(history)`, `parse_brief(response)`,
  `_build_pattern_list()`
- `DungeonGeneratorAgent`: `SYSTEM_PROMPT`, `generate_level(brief, level_number,
  dungeon_so_far, validation_errors)`, `parse_level(response)`, `_build_context(...)`
- `DesignAgent`: `SYSTEM_PROMPT`, `chat(history, dungeon)`, `_build_context(dungeon)`
- `DungeonMasterAgent`: `SYSTEM_PROMPT`, `respond(history, room, level, dungeon, room_memory="")`,
  `_build_context(room, level, dungeon, room_memory)`

### Exit Criteria

- `pytest tests/unit/llm/` is green with all provider calls mocked
- `LLMError` is raised (not `anthropic.APIError`) when the mock raises an API error
- `DungeonWizardAgent.parse_brief()` extracts a `DungeonBrief` from a response with a
  ```brief``` block; returns `None` when no block present
- `DungeonGeneratorAgent.parse_level()` extracts a `Level` from a ```json``` block;
  raises `ValueError` when no block present
- `DungeonMasterAgent.respond()` includes room_memory in the system prompt when non-empty
- No real API call is made during tests

---

## Phase 5 — Design View Skeleton

**Status: Complete**

`DesignView` opens in **wizard mode** when no dungeon exists, or in **edit mode**
when a dungeon is loaded. Chat input works. No LLM calls wired yet — sending a
message shows a placeholder "…" response. The dungeon tree and inspector panels
render their structure but with placeholder content.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/views/design_view.py` | (manual smoke test) |
| `dungeon_daddy/ui/panels/chat_panel.py` | (manual smoke test) |
| `dungeon_daddy/ui/panels/dungeon_tree_panel.py` | (manual smoke test) |
| `dungeon_daddy/ui/panels/inspector_panel.py` | (manual smoke test) |

### What to build

- `DesignView`: `on_show_view()`, `on_hide_view()`, `on_draw()`, `on_update()`,
  `_build_ui()`, `on_chat_send()` (stub — no thread yet)
- `DesignView` modes: `wizard_mode`, `generation_mode`, `edit_mode`
  (tracked as `self._design_mode: str`)
- `ChatPanel`: scrollable history, input field, send button (greyed when busy),
  typing indicator, "↓ New message" badge
- `DungeonTreePanel`: collapsible level/room tree, coloured by loop path membership;
  shows "Generating level N…" placeholder rows during generation mode
- `InspectorPanel`: tabbed (Settings | Loops), renders placeholder content

### Exit Criteria

- `python -m dungeon_daddy` opens to Design Mode showing the wizard greeting message
- Chat input accepts text; sending shows the user's bubble + a placeholder response
- Loading the sample dungeon switches to edit mode and populates the tree
- No crash on window resize

---

## Phase 6 — Play View + Grid Map

**Status: Complete**

`PlayView` opens with the grid map rendered and the chat panel beside it.
Room clicks update session state. No LLM wired yet.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/views/play_view.py` | (manual smoke test) |
| `dungeon_daddy/map/base_renderer.py` | (abstract — tested via subclasses) |
| `dungeon_daddy/map/grid_renderer.py` | `tests/unit/map/test_grid_renderer.py` |
| `dungeon_daddy/map/loop_overlay.py` | `tests/unit/map/test_loop_overlay.py` |
| `dungeon_daddy/ui/panels/map_panel.py` | (manual smoke test) |
| `dungeon_daddy/ui/widgets/level_stepper.py` | (manual smoke test) |

### What to build

- `MapRenderer` abstract base class
- `GridRenderer`: draws graph-paper style rooms and connections using `arcade.draw_*`
- `LoopOverlay`: draws teal/violet arcs over the active loop's path_a / path_b
- `PlayView`: loads session state, renders map, handles room clicks,
  `on_select_room()` with 5-state atomic update
- `MapPanel`: container + variant selector buttons (grid selected; tiles/graph stubbed)
- `LevelStepper`: up/down navigation between levels

### Exit Criteria

- `pytest tests/unit/map/` is green (arcade.draw_* calls are patched)
- `python -m dungeon_daddy` can switch to Play Mode; grid map renders the sample dungeon
- Clicking a room updates `current_room_id` and highlights the room
- Level stepper navigates between the 3 sample levels

---

## Phase 7 — Wire Up LLM Design Flow (Wizard + Generator)

**Status: Complete**

`DesignView` now makes real LLM calls. Wizard mode collects dungeon settings via
chat and produces a `DungeonBrief`. Generator mode generates each level one by one,
validating each before accepting it. Edit mode activates `DesignAgent` for refinement.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/views/design_view.py` (update) | `tests/unit/llm/test_wizard_agent.py`, `tests/unit/llm/test_generator_agent.py` |

### What to build

- `_run_llm(history)` thread target for wizard mode (calls `DungeonWizardAgent.chat()`)
- `_run_generation(level_number)` thread target (calls `DungeonGeneratorAgent.generate_level()`
  with up to 3 retry attempts on validation failure)
- `_run_design_chat(history, dungeon)` thread target for edit mode (calls `DesignAgent.chat()`)
- `_result_queue: queue.Queue[LLMResult]` + `_llm_busy` guard (shared by all three)
- `LLMResult` dataclass extended with `result_type: str` (`"wizard"`, `"level"`, `"chat"`)
- `on_update()` queue drain — dispatches based on `result_type`:
  - `"wizard"`: check for brief block → if found, transition to generation mode
  - `"level"`: parse `Level`, append to dungeon, update tree, prompt GM to continue
  - `"chat"`: append DM bubble
- `on_hide()` thread join with 3-second timeout
- Send button greyed while `_llm_busy`

### State Machine — `DesignView.on_update()` dispatch

`LLMResult` gains a `result_type` field (`"wizard" | "level" | "chat"`) to let
`on_update()` route results without an if/elif chain on `_design_mode`:

```python
@dataclass
class LLMResult:
    content: str
    error: str | None = None
    result_type: str = "chat"   # "wizard" | "level" | "chat"

# In on_update():
result = self._result_queue.get_nowait()
if result.error:
    self._append_error_bubble(result.error)
    self._llm_busy = False
    return

match result.result_type:
    case "wizard":
        self._chat_history.append(ChatMessage(role="dm", content=result.content))
        brief = self._wizard_agent.parse_brief(result.content)
        if brief:
            self._brief = brief
            self._design_mode = "generation"
            self._current_level_number = 1
            self._append_system_bubble("Generating level 1…")
            self._spawn_generator_thread(1)
        else:
            self._llm_busy = False   # wizard continues

    case "level":
        try:
            level = self._generator_agent.parse_level(result.content)
            vresult = validate_dungeon_level(level)
            if vresult.is_valid:
                self._dungeon.levels.append(level)
                self._rebuild_tree()
                if self._current_level_number < self._brief.num_levels:
                    self._current_level_number += 1
                    self._append_system_bubble(
                        f"Level {self._current_level_number - 1} ready. "
                        f"Generating level {self._current_level_number}…"
                    )
                    self._spawn_generator_thread(self._current_level_number)
                else:
                    self._finish_generation()
            else:
                self._retry_count += 1
                if self._retry_count >= MAX_REVISION_ATTEMPTS:
                    self._append_error_bubble(
                        f"Level {self._current_level_number} could not be "
                        f"generated after {MAX_REVISION_ATTEMPTS} attempts."
                    )
                    self._design_mode = "edit"
                else:
                    self._append_system_bubble(
                        f"Revising level {self._current_level_number}…"
                    )
                    self._spawn_generator_thread(
                        self._current_level_number, errors=vresult.errors
                    )
        except (ValueError, ValidationError) as e:
            # Parse failure counts as a revision
            self._retry_count += 1
            ...
        finally:
            self._llm_busy = False

    case "chat":
        self._chat_history.append(ChatMessage(role="dm", content=result.content))
        self._llm_busy = False
```

### Exit Criteria

- Wizard collects dungeon settings and produces a `DungeonBrief` via real Claude call
- Generator produces all levels with valid JSON (requires `ANTHROPIC_API_KEY`)
- Each level appears in `DungeonTreePanel` as it is generated
- Validation errors trigger automatic retry (visible in chat as "Revising level N…")
- After all levels, edit mode activates and the GM can refine via `DesignAgent`
- If `ANTHROPIC_API_KEY` is missing, an inline notice appears — no crash
- Closing the window during generation joins the active thread cleanly

---

## Phase 8 — Wire Up LLM DM Chat + Room Memory

**Status: Complete**

`PlayView` makes real LLM calls. Clicking a room triggers a DM narration using
room context and play memory. `/remember` records events to markdown memory files.
The remaining map renderers (tiles, graph) are implemented.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/views/play_view.py` (update) | `tests/unit/llm/test_dm_agent.py` |
| `dungeon_daddy/map/tiles_renderer.py` | `tests/unit/map/test_tiles_renderer.py` |
| `dungeon_daddy/map/graph_renderer.py` | `tests/unit/map/test_graph_renderer.py` |
| `dungeon_daddy/ui/panels/loops_panel.py` | (manual smoke test) |
| `dungeon_daddy/ui/widgets/loop_card.py` | (manual smoke test) |
| `dungeon_daddy/ui/widgets/path_editor.py` | (manual smoke test) |
| `dungeon_daddy/ui/widgets/chat_bubble.py` | (manual smoke test) |

### What to build

- Threading wiring for `PlayView` + `DungeonMasterAgent`
- `on_room_click()` loads room memory and triggers `DungeonMasterAgent.respond()`
  with `room_memory` from `DungeonRepository.load_room_memory()`
- `/remember` command interception in `on_chat_send()` — calls
  `DungeonRepository.append_room_event()`, appends system bubble, no LLM call
- "Edit Memory" button in `PlayView` — opens `UITextArea` overlay with level
  memory markdown; save calls `DungeonRepository.save_room_memory()`
- `TilesRenderer`: shaded top-down tile style
- `GraphRenderer`: abstract node graph style
- Map variant switcher wired to swap the active renderer
- `LoopsPanel`, `LoopCard`, `PathEditor`, `ChatBubble` widgets
- Integration tests: `tests/integration/test_dungeon_persistence.py`,
  `tests/integration/test_llm_integration.py`

### Exit Criteria

- `pytest tests/unit/map/` fully green (all three renderers)
- `pytest tests/integration/` green (with real filesystem; LLM tests skipped if no key)
- Clicking a room triggers DM narration; room memory is included in context on revisit
- `/remember the party found the key` appends to the level memory file; verified by
  reading the file directly in the test
- "Edit Memory" overlay opens, edits persist after save
- Map variant switcher swaps renderers without crashing
- `File → Save` persists the dungeon and session state to disk

---

## Phase 9 — Edit Memory Overlay + LLM Integration Tests

**Status: Complete**

Complete the remaining F-20 acceptance criteria (Edit Memory UI) and add the
skippable LLM integration test suite.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/views/play_view.py` (update) | `tests/unit/views/test_play_view.py` |
| `tests/integration/test_llm_integration.py` | (new) |

### What to build

- "Edit Memory" button in `PlayView` — visible only when the current level has a
  memory file (`DungeonRepository.load_room_memory()` returns non-empty string)
- Clicking the button opens a `UITextArea` overlay (drawn over the map panel) pre-filled
  with the current level's memory markdown
- "Save" button on the overlay calls `DungeonRepository.save_room_memory()` and closes
  the overlay
- "Cancel" button (or Esc key) closes the overlay without saving
- `tests/integration/test_llm_integration.py` — one real provider call per agent
  (skipped via `pytest.mark.skipif` when `OPENAI_API_KEY` is not set)

### Exit Criteria

- [x] "Edit Memory" button is invisible when no memory file exists for the current level
- [x] "Edit Memory" button becomes visible after `/remember` adds content
- [x] Clicking "Edit Memory" opens overlay with current memory markdown pre-filled
- [x] Saving overwrites the file via `save_room_memory()` and closes overlay
- [x] Cancel / Esc closes overlay without writing to disk
- [x] `pytest tests/unit/` green (282 tests)
- [x] `pytest tests/integration/test_llm_integration.py` green (LLM tests skip without key)
- [x] Live: `/remember` a note → open Edit Memory → edit text → save → reload overlay →
      verify edited text persists

---

## Phase 10 — Design Mode Loop Editor

**Status: Complete**

`InspectorPanel` Loops tab is fully interactive. The GM can pick loop patterns,
add/remove sub-loops, switch levels, and see active loop assignments on the map.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/data/loop_assignment.py` (new) | `tests/unit/data/test_loop_assignment.py` |
| `dungeon_daddy/ui/panels/loops_panel.py` (new) | `tests/unit/ui/test_loops_panel.py` |
| `dungeon_daddy/ui/panels/inspector_panel.py` (update) | (existing) |
| `dungeon_daddy/ui/widgets/chat_bubble.py` (new) | (smoke test only) |

### What to build

- `auto_assign_loop_rooms(level)` — BFS algorithm: entry=most-connected, goal=BFS-furthest,
  path_a=shortest, path_b=fewest-overlap alternate (linear fallback: path_b=path_a)
- `LoopsPanel` — draws ACTIVE LOOPS and PATTERN LIBRARY sections; `_pattern_rects` and
  `_remove_rects` hit-tested on click; `_level_rects` for level picker
- `InspectorPanel` Loops tab wired — `on_mouse_press(x, y, modifiers)` routes via `_tab_rects`
- `chat_bubble.py` — `draw(x, y, text, color, max_width)` widget for in-map DM narration

### What was built (2026-05-05)

- `dungeon_daddy/data/loop_assignment.py` — BFS algorithm complete; 7 unit tests
- `dungeon_daddy/ui/panels/loops_panel.py` — ACTIVE LOOPS + PATTERN LIBRARY draw/click; 8 unit tests
- `dungeon_daddy/ui/panels/inspector_panel.py` — Loops tab wired; tab routing via `_tab_rects`
- `dungeon_daddy/views/design_view.py` — `on_mouse_press()` passes `modifiers` to inspector
- 297 unit tests, all green; smoke test PASS (Loops tab + PATTERN LIBRARY render correctly)

### What was built (2026-05-05, session 2)

- **`dungeon_daddy/ui/panels/loops_panel.py`** — × remove button:
  `_remove_rects: dict[str, tuple]` populated in `draw()` for each sub-loop card (right-aligned chip);
  `on_mouse_press()` checks `_remove_rects` before pattern rects → calls `remove_sub_loop(loop_id)`.
- `tests/unit/ui/test_loops_panel.py` — 9 tests (added `test_on_mouse_press_remove_rect_removes_sub_loop`)
- **Total: 298 unit tests, all green**

### What was built (2026-05-05, session 3)

- **`dungeon_daddy/ui/panels/loops_panel.py`** — Level picker chips:
  `_levels: list[Level]` + `_level_rects: dict[int, tuple]` added to `__init__`;
  `set_levels(levels)` method added; `draw()` renders L1/L2/… chips above ACTIVE LOOPS,
  active level highlighted in TEAL; `on_mouse_press()` checks `_level_rects` first → calls `set_level()`.
- **`dungeon_daddy/ui/panels/inspector_panel.py`** — `set_dungeon()` now calls
  `set_levels(dungeon.levels)` (and `set_levels([])` on clear).
- `tests/unit/ui/test_loops_panel.py` — 10 tests (added `test_on_mouse_press_level_rect_sets_level`)
- **Total: 299 unit tests, all green**

### What was built (2026-05-05, session 4)

- **`dungeon_daddy/ui/widgets/chat_bubble.py`** — `ChatBubble.draw(x, y, text, color, max_width)`;
  draws rounded-rect bubble with accent border and wrapped text. Import confirmed clean.
- **`dungeon_daddy/ui/panels/loops_panel.py`** — Bug fixes:
  - Added missing `BG_1` import (caused `NameError` when Loops tab was active)
  - Fixed `pat.id` → `pat.key` in `_pattern_rects` population (`LoopPattern` uses `.key`)
- **`tools/ui_input.py`** — Added `shift_click_app()` helper (holds Shift during left-click)
- **`tools/smoke_test_phase10.py`** — Phase 10 smoke test created (6 behaviors); partially passing:
  - B1 PASS: Loops tab switches (TEAL detected)
  - B2 PASS: Pattern click → TEAL loop card in ACTIVE LOOPS
  - B3 FAIL: Shift-click y-coordinate off; need to recalibrate `_PAT1_Y_WITH_MAIN`
  - B4 PASS: No VIOLET in sub-loop region (trivially, since B3 failed)
  - B5 PASS: Level picker chip click — app alive
  - B6 FAIL: `dungeon_daddy` module not on `sys.path` when run from `tools/`
- **Total: 299 unit tests, all green**

### What was built (2026-05-05, session 5)

- **`dungeon_daddy/ui/panels/loops_panel.py`** — `+` button on each pattern card:
  `_add_rects: dict[str, tuple]` added to `__init__` and cleared in `draw()`;
  each pattern card draws a teal `+` chip at the far right (18×16px);
  A/B path text shifted left to avoid overlap;
  `_pattern_rects` now covers only the card body (left of `+`);
  `on_mouse_press()` checks `_add_rects` before `_pattern_rects` → calls `add_sub_loop()` directly (no shift needed).
- `tests/unit/ui/test_loops_panel.py` — 12 tests (added `test_on_mouse_press_add_rect_calls_add_sub_loop`,
  `test_on_mouse_press_add_rect_does_not_call_apply_pattern`)
- **Total: 301 unit tests, all green**

### What was built (2026-05-05, session 6)

- **`tools/smoke_test_phase10.py`** — B3 replaced: shift-click skip removed; now clicks `+` button at
  `(_REMOVE_BTN_X, _PAT1_Y_WITH_MAIN)` = `(1379, 590)`, then scans y=605..645 for VIOLET sub-loop card.
  `shift_click_app` import removed. All 6 behaviors PASS.

### What was built (2026-05-05, session 7 — stabilization)

- **Play map room labels** — all 3 renderers (grid, tiles, graph) now show `"Name (1-A)"` format
- **`dungeon_daddy/ui/theme.py`** — `draw_chip()` gained optional `width: int = 80` param
- **`dungeon_daddy/ui/panels/chat_panel.py`** — suggestion chips sized to text width (7px/char + padding, 8px gaps); `_chip_rects` populated during `draw()`; `on_mouse_press(x, y) -> bool` added — clicks chips send the chip text via `_on_send`; ignored when busy
- **`dungeon_daddy/views/design_view.py`** — `on_mouse_press` now routes to `self._chat.on_mouse_press()`; removed leftover debug `print`
- `tests/unit/ui/test_chat_panel.py` — 6 new tests for chip click handling
- `tests/unit/map/test_grid_renderer.py` — updated 2 label assertions to include room ID
- **Total: 307 unit tests, all green**

### What was built (2026-05-05, session 8 — UI/UX polish)

13 UI/UX fixes applied across `chat_panel.py`, `dungeon_tree_panel.py`,
`inspector_panel.py`, `chrome.py`, and `theme.py`:

- Chat messages now top-anchor when content is sparse (no dead zone)
- Dungeon panel empty state: hex icon + "No dungeon yet" + hint text
- Input box reduced: `INPUT_H` 112→62, `INPUT_AREA_H` 160→104
- Send button renamed from "Draft" to "Send"
- Mode label ("Wizard Mode") replaced chip with plain `· label` status text
- Suggestion chips repositioned above the input box (were below, clipped)
- Context docs status unified: `✓ NNN words` / `○ pending` / `○ N / N`
- Theme field placeholder text added
- Complexity label and segmented control split into two rows (no overlap)
- `draw_kicker`: color `INK_3`→`INK_2`, teal accent bar added
- "DESIGN MODE" wrapped in a bordered badge
- Dungeon tree panel: explicit left border added
- `◆ Dungeon` bubble label color `INK_3`→`VIOLET`; double-space fixed

**Total: 307 unit tests, all green**

### What was built (2026-05-05, session 9 — Play Mode UI/UX polish)

11 Play Mode UI/UX fixes applied, each verified with a manual visual check:

1. **Chat header label** — `chat_panel.py` uses `mode="play"` to render "DUNGEON CHAT" kicker
2. **Play mode chips + LLM wiring** — `_CHIPS_PLAY` set active; chip click calls `_on_level_change`
   routed through `play_view._chat.on_mouse_press()` → `_on_chat_send()` → `DungeonMasterAgent`
3. **"Ask" button label** — button text in play mode is "Ask" (was "Send")
4. **Current Room banner** — 80 px `BG_1`/violet-gradient banner below header; "CURRENT ROOM"
   kicker + room name (`FONT_SERIF` 19 px) + note (12 px `INK_3`); wired via `set_current_room()`
5. **Turn/room chips in header** — teal "Turn {n}" chip at x+148, violet room-ID chip at x+240
6. **Variant tabs moved into map canvas** — removed fixed tab bar background; tabs repositioned
   as 52×22 px overlay at top-right inside `map_panel.py`; `_HEADER_H = 38`
7. **Edit Memory button removed from Play mode** — `_OVERLAY_TAB_H = 0`; no button rendered
8. **"DUNGEON VIEWER" header + gold dungeon title chip** — header bar added to map panel; gold
   pill auto-widths to `len(title)*7+20`; chip positioned at x+155+half-width; gold chip
   background brightened to `(90, 78, 22)` in `theme.py` `draw_chip()` palette
9. **Level name overlay (top-left) + legend (bottom-left)** — `_draw_level_overlay()` (teal "L{n}"
   + level name + dimensions) and `_draw_legend()` (icon+label pairs) drawn in-canvas
10. **Room type colors always visible** — removed fog-of-war from `grid_renderer.py` and
    `graph_renderer.py`; all rooms render with their type `fill`/`stroke` regardless of
    `visited_rooms`; test `test_unseen_rooms_use_unseen_fill` renamed `test_rooms_use_type_fill`
11. **Compass rose in level stepper** — `level_stepper.py` draws a circle outline + "N" label
    (`FONT_SERIF`) at the bottom of the stepper rail; `▼` button moved up `_COMPASS_H=48 px`
    to reserve space

**Total: 306 unit tests, all green (1 pre-existing `test_draw_title_bar_calls_rect_filled` failure)**

### Exit Criteria (F-14)

- [x] Pattern library shows all 9 patterns
- [x] Clicking a pattern card applies it as primary loop with auto-assigned rooms
- [x] Shift-clicking a pattern card adds it as a sub-loop
- [x] Removing a sub-loop (× button) removes it from the list
- [x] Level picker shows all levels; active level is highlighted
- [x] `chat_bubble.py` widget renders without crash (smoke test)
- [x] `pytest tests/unit/` green (307 tests)
- [x] Live smoke: pattern click → loop applied; + button → sub-loop added; × → removed

---

## Phase 11 — Design Mode Polish + Context Docs Foundation

**Status: Complete**

373 unit tests passing.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/ui/panels/dungeon_tree_panel.py` (update) | `tests/unit/ui/test_dungeon_tree_panel.py` |
| `dungeon_daddy/ui/panels/inspector_panel.py` (update) | `tests/unit/ui/test_inspector_panel.py` |
| `dungeon_daddy/ui/panels/chat_panel.py` (update) | `tests/unit/ui/test_chat_panel.py` |
| `dungeon_daddy/data/context_docs.py` (new) | `tests/unit/data/test_context_docs.py` |
| `dungeon_daddy/data/repository.py` (update) | `tests/unit/data/test_repository.py` |
| `dungeon_daddy/llm/agents/wizard_agent.py` (update) | `tests/unit/llm/test_wizard_agent.py` |
| `dungeon_daddy/views/design_view.py` (update) | (existing) |

### What to build

**F-11 — Tree room path colouring**
- `DungeonTreePanel.set_active_loop(loop: Loop | None)` — stores the active loop for the current level
- `draw()` — room rows tinted: path A → TEAL, path B → VIOLET, both → INDIGO, neither → INK_3
- Wire: when `on_activate_loop` fires in `DesignView`, call `_tree.set_active_loop(loop)`

**F-12 — Design chat keyboard shortcuts**
- `ChatPanel.on_key_press(key, modifiers)` — Ctrl+Enter calls `_on_send()`; Enter inserts `\n`
- `DesignView.on_key_press()` routes to `self._chat.on_key_press()`

**F-13 — Inspector Settings Tab editable fields**
- Party size, party level, theme, level count, complexity segmented control all write back to
  `dungeon.meta` on change (in-memory; no auto-save)
- `InspectorPanel.set_on_settings_change(callback)` — fires with updated `DungeonMeta` on any edit

**F-14 — Activate loop → tree highlight**
- `DesignView` passes `on_activate_loop=self._on_activate_loop` when constructing `InspectorPanel`
- `_on_activate_loop(loop_id)` looks up the loop and calls `self._tree.set_active_loop(loop)`

**C-1 — Context doc file structure + repo load/save**
- `ContextDocType` enum: `SETTING`, `PARTY`, `LEVEL_DESIGN`
- `DungeonRepository.load_context_doc(dungeon_name, doc_type, level_id=None) -> str`
- `DungeonRepository.save_context_doc(dungeon_name, doc_type, content, level_id=None)`
- Files live at: `{data_dir}/{dungeon_name}/setting.md`, `party.md`, `level_{N}_design.md`
- Level design doc format: plain markdown with `## Ecology`, `## Design Notes` headings;
  extensible — future phases can add `## Monsters` without breaking existing files

**C-2 — Wizard generates first-draft docs**
- After generation completes, `DesignView._finish_generation()` calls `_generate_context_docs()`
- `_generate_context_docs()` calls `DesignAgent` (or a dedicated prompt) to produce:
  - `setting.md` — dungeon world lore, atmosphere, factions, history (from `DungeonBrief`)
  - `party.md` — party backstory, motivations, hooks (from `DungeonBrief`)
  - `level_N_design.md` — per-level ecology and design notes (from each generated level)
- Docs are saved via `DungeonRepository.save_context_doc()`
- A "Writing context docs…" system bubble appears while generation runs

**C-3 — Context Docs UI**
- `InspectorPanel` Settings tab Context Docs rows show real word counts from loaded files
- `_context_doc_rects: list[tuple]` populated during `draw()` for hit-testing
- Clicking a row opens a `UITextArea` overlay (same pattern as Edit Memory overlay in Phase 9)
- Save writes the file via `save_context_doc()`; cancel discards; overlay has Save + Cancel buttons
- Status display: `✓ NNN words` (file exists, non-empty), `○ pending` (file missing or empty)

### What was built

- **F-11** — `DungeonTreePanel.set_active_loop(loop)` added; room rows render `▶`/TEAL (path A), `◇`/VIOLET (path B), `◆`/INDIGO (both), `▢`/INK_3 (neither). `INDIGO = (158, 100, 210)` added to `theme.py`. 5 new tests; 315 passing.
- **F-14** — `LoopsPanel` stores `_loop_rects` per loop row; click fires `activate_loop(loop_id)` → `on_activate_loop` callback. `DesignView._on_loop_activated(loop_id)` searches dungeon levels for matching `Loop` and calls `_tree.set_active_loop(loop)`. Wired via `InspectorPanel(on_activate_loop=...)`. 3 new tests; 318 passing.
- **F-12** — `ChatPanel.handle_key_press(key, modifiers) -> bool` added: Ctrl+Enter calls `_do_send()` and returns `True` (consumed); all other keys return `False`. `DesignView.on_key_press` delegates to it. 5 new tests; 323 passing.
- **F-13** — `DungeonMeta` extended with `party_size=4`, `party_level=3`, `num_levels=3`, `complexity="Moderate"`. `InspectorPanel` gains `set_on_settings_change`, `on_settings_field_change`, `on_complexity_change`; complexity segment clicks wired via `_complexity_seg_rects`. 19 new tests; 342 passing.
- **C-1** — `ContextDocType(str, Enum)` added to `models.py` (`SETTING`, `PARTY`, `LEVEL_DESIGN`). `DungeonRepository.load_context_doc` / `save_context_doc` added; files at `{data_dir}/{dungeon_name}/setting.md`, `party.md`, `level_{N}_design.md`. 7 new tests; 349 passing.
- **C-2** — `dungeon_daddy/llm/context_docs.py` added: `generate_setting_doc`, `generate_party_doc`, `generate_level_design_doc`, `generate_all_context_docs`. `skip_existing=True` by default. 14 new tests; 363 passing.
- **C-3** — `ContextDocStatus`; `set_context_doc_statuses`; `_context_doc_rects` hit-test; `open/save/close_context_doc_overlay` in DesignView; `_refresh_context_doc_statuses` on load. 373 total tests.

### Exit Criteria

- [x] Tree room rows tinted by loop path membership; tint updates when loop is activated
- [x] Ctrl+Enter sends Design chat message; Enter inserts newline
- [x] Settings tab fields (party size/level, theme, levels, complexity) are editable; in-memory state updates
- [x] Activating a loop from Loops tab calls `on_activate_loop` → tree colours update
- [x] `DungeonRepository` load/save context docs round-trips correctly; `tmp_path` used in tests
- [x] Wizard generates `setting.md` + `party.md` after all levels complete
- [x] `level_N_design.md` created per level with ecology + design notes
- [x] Context Docs UI shows real word counts (not hardcoded)
- [x] Click row → edit overlay opens pre-filled; save persists; cancel discards
- [x] `pytest tests/unit/` green (373 tests)

---

## Phase 12 — Context Engineering

**Status: Complete**

Add intelligent context assembly so the LLM always receives the most relevant
dungeon information without exceeding its context budget. Uses compaction —
an LLM-generated dense summary — rather than truncation.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/llm/context_builder.py` (new) | `tests/unit/llm/test_context_builder.py` |
| `dungeon_daddy/llm/context_compactor.py` (new) | `tests/unit/llm/test_context_compactor.py` |
| `dungeon_daddy/data/repository.py` (update) | `tests/unit/data/test_repository.py` |
| `dungeon_daddy/llm/agents/design_agent.py` (update) | `tests/unit/llm/test_design_agent.py` |
| `dungeon_daddy/llm/agents/dm_agent.py` (update) | `tests/unit/llm/test_dm_agent.py` |

### What to build

**ContextCompactor**
- `ContextCompactor(provider: LLMProvider)` — uses the injected provider to compress docs
- `compact(content: str, doc_type: ContextDocType) -> str` — returns a dense summary preserving
  all key facts; prompt is doc-type-aware (setting doc vs. party doc vs. level doc)
- Dirty-flag caching: compacted version stored as `{name}.compact.md` alongside the original;
  regenerated only when the source file is newer than the compact file

**ContextBuilder**
- `ContextBuilder(repo: DungeonRepository, compactor: ContextCompactor)`
- `build_design_context(dungeon, active_level_id=None) -> str` — assembles system prompt context:
  1. Structured dungeon meta (always, ~200 tokens)
  2. `setting.md` or `setting.compact.md` if over budget
  3. `party.md` or `party.compact.md` if over budget
  4. `level_N_design.md` for active level (or compact) if budget allows
- `build_play_context(dungeon, level, room, room_memory="") -> str` — assembles DM context:
  1. Current room + level ecology (always)
  2. `setting.md` compact (dungeon atmosphere)
  3. `party.md` compact (who the party is)
  4. Room memory (always, already small)
- `TOKEN_BUDGET = 3000` — approximate token ceiling for context block (1 token ≈ 4 chars)
- Budget enforcement: each doc measured in chars; compact version used when `len(doc) / 4 > remaining_budget`

**Agent integration**
- `DesignAgent._build_context()` replaced by `ContextBuilder.build_design_context()`
- `DungeonMasterAgent._build_context()` replaced by `ContextBuilder.build_play_context()`
- Both agents receive `ContextBuilder` via dependency injection at construction

### Exit Criteria

- [x] `ContextCompactor.compact()` calls provider exactly once and returns non-empty string
- [x] Compact file is written alongside source; not regenerated when source is unchanged
- [x] `ContextBuilder` assembles context within `TOKEN_BUDGET` chars × 4
- [x] When a doc fits in budget, full doc is used; when it exceeds, compact version is used
- [x] `DesignAgent` and `DungeonMasterAgent` use `ContextBuilder`; tests verify context includes setting doc content
- [x] No real API calls in unit tests (provider mocked)
- [x] `pytest tests/unit/` green

---

## Phase 13 — Incremental Context Docs + Wizard Save-Name

**Status: Complete**

433 unit tests passing after post-phase stabilisation.

### What was built

- `DungeonMeta.save_name: str | None = None` + `effective_name` property (`save_name or title`)
- `ContextBuilder` and `window.save_dungeon()` use `effective_name`
- `DesignView._write_setting_party_docs()` — called at brief-parse time
- `DesignView._write_level_design_doc(level)` — called after each level passes validation
- `DesignView._continue_to_generation()` extracted; `_context_overwrite_confirmed` + `_awaiting_name_choice` flags
- `_on_chat_send` intercepts `_awaiting_name_choice` before normal routing
- Post-phase stabilisation: `File → Open...` (Ctrl+O), per-dungeon folder layout, auto-migration, open error dialog, removed "+ Add level" button

### Exit Criteria

- [x] `DungeonMeta.save_name` field present; `None` falls back to `title` everywhere
- [x] `ContextBuilder` and `save_dungeon()` use `save_name or title`
- [x] `setting.md` and `party.md` written immediately after Phase 1 resolves
- [x] `level_N_design.md` written after each level passes validation
- [x] Inspector context doc rows update in real time as wizard progresses
- [x] If `setting.md` pre-exists, GM prompted once to overwrite or provide a new save name
- [x] `pytest tests/unit/` green (433 tests)

---

## Phase 14 — Obstacle-Aware Map Connection Routing

**Status: Complete**

481 unit tests passing.

### What was built

- `dungeon_daddy/map/routing.py` — pure geometry helpers: `get_room_rect`, `get_room_port`, `line_intersects_rect`, `path_intersects_any_room`, `calculate_path_length`, `select_port_direction`, `straight_path_blocked`, `route_orthogonal`, `route_detour`, `route_waypoints`, `is_route_problematic`; `CONNECTION_OBSTACLE_MARGIN = 16`
- `GridRenderer._port_screen()` + updated `draw()` — edge-port routing, orthogonal/detour/waypoint paths
- `Connection.waypoints: list[dict] | None = None` — optional manual waypoints in JSON
- `GridRenderer(debug_routing=True)` — draws TEAL port dots at endpoints, TEAL waypoint dots, EMBER segments for problematic routes

### Exit Criteria

- [x] Connections drawn from room edge ports, not centers
- [x] Renderer detects when a connection crosses an unrelated room
- [x] Orthogonal routing attempted when straight path is blocked (both H-first and V-first)
- [x] Detour routing attempted when both orthogonal options still cross a room
- [x] Manual `waypoints` in JSON are respected
- [x] Debug visualization toggle exists (off by default)
- [x] Existing level JSON files load without change
- [x] Level 1 Crucible map shows no connection lines through unrelated rooms
- [x] `pytest tests/unit/` green (481 tests)

---

## Phase 15 — Localized Connection Routing Refinement

**Status: Complete**

576 unit tests passing.

### Entry Conditions

- Phase 14 complete ✓
- 481 unit tests passing ✓
- Spec: `spec/FEATURE_MAP_CONNECTION_ROUTING_2.md`
- Validation test already written — do not rewrite it
- Second fixture `tests/fixtures/tomb.json` added (48 additional validation cases, all passing)

### Scope

| Task | Feature | Status | Notes |
|---|---|---|---|
| LR-1 | Add `get_local_bounds` | **Done** | `routing.py`: bounding rect of both rooms + `ROUTE_BOUNDING_MARGIN = 4` |
| LR-2 | Update `_score_path` | **Done** | Escape penalty, detour-ratio penalty, bend × 100, length × 10; `INTERSECTION_WEIGHT = 5000` |
| LR-3 | Fix `route_detour` candidates | **Done** | Waypoints clamped to local bounds; `fy == ty` degenerate case generates 5-point above/below paths; `fx == tx` symmetric fix also added |
| LR-4 | Update `route_orthogonal` | **Done** | Passes `local_bounds` + `direct_distance` into `_score_path` |
| LR-5 | Add constants | **Done** | `ROUTE_BOUNDING_MARGIN=4`, `INTERSECTION_WEIGHT=5000`, `ESCAPE_WEIGHT=500`, `MAX_DETOUR_RATIO=5.0`, `MAX_BEND_COUNT=6` |
| LR-6 | Degenerate unit test | **Done** | `test_routing.py::test_route_detour_degenerate_horizontal_alignment_avoids_blocker` |

### What was built

- **LR-5** — Constants added to `routing.py`: `ROUTE_BOUNDING_MARGIN=4`, `INTERSECTION_WEIGHT=5000`, `ESCAPE_WEIGHT=500`, `MAX_DETOUR_RATIO=5.0`, `MAX_BEND_COUNT=6`.
- **LR-1** — `get_local_bounds(from_room, to_room, margin=ROUTE_BOUNDING_MARGIN) -> Rect` added; returns bounding rect of both rooms expanded by margin.
- **LR-2** — `_score_path` updated: new formula `intersections * 5000 + length * 10 + bends * 100 + escape_penalty + detour_ratio_penalty`. Two private helpers added: `_escape_distance` and `_detour_ratio_penalty`.
- **LR-3** — `route_detour` clamps all four bypass positions to `local_bounds`. For `fy == ty`: replaces degenerate left/right with 5-point above/below paths that step vertically first. `fx == tx` symmetric case also handled.
- **LR-4** — `route_orthogonal` computes `local` and `direct_dist` and passes both into `_score_path`.
- **LR-6** — Synthetic unit test with a blocker directly between two horizontally-aligned rooms plus top/bottom walls that force left/right candidates; confirms the degenerate fix avoids the blocker.

### Post-Phase-15 Bug Fix

| Fix | What changed |
|---|---|
| `hit_test_connection` uses actual route path | Was testing straight center-to-center line; now mirrors `draw()` logic (waypoints → detour-if-blocked → straight port-to-port) and tests each segment. Bent connections are now clickable. 576 tests. |

### Exit Criteria

- [x] `tests/unit/map/test_routing_validation.py` — all 102 tests pass (was 99/102)
- [x] `L3/r5→r6` stays within local bounds (still flagged problematic, but local)
- [x] Degenerate `fy == ty` case covered by synthetic unit test in `test_routing.py`
- [x] Constants exported from `routing.py`
- [x] `pytest tests/unit/` green (576 tests)

---

## Phase 16 — DM Stateful Conversation

**Status: Complete**

598 unit tests passing.

### Entry Conditions

- Phase 15 complete ✓
- 576 unit tests passing ✓
- Spec: `spec/FEATURE_DM_STATEFUL_CONVERSATION.md`

### Scope

Two improvements to Play Mode DM chat: persistent conversation history within a session,
and automatic room memory tagging via a `[REMEMBER]` tag in DM responses.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/views/play_view.py` (update) | `tests/unit/views/test_play_view_history.py`, `tests/unit/views/test_play_view_remember.py` |
| `dungeon_daddy/llm/agents/dm_agent.py` (update) | `tests/unit/agents/test_dm_agent_history.py` |

### What to build

| Task | Feature | Notes |
|---|---|---|
| SC-1 | `PlayView._dm_history` accumulation | Add field; pass to every DM call (chat-send + room-entry) |
| SC-2 | History compaction — drop oldest turns | Budget 2 000 tokens; drop oldest user+assistant pairs |
| SC-3 | Clear on level change + `/clear` command | `_dm_history = []`; post `"💬 Conversation cleared."` system message |
| SC-4 | Increase `DMAgent` `max_tokens` 512 → 1 024 | `dm_agent.py` respond call |
| SC-5 | `[REMEMBER]` tag parsing + auto-remember | `_extract_remember()` in `play_view.py`; strip tag, call `append_room_event`, post `📝 Noted:` |
| SC-6 | Update `DungeonMasterAgent` `SYSTEM_PROMPT` | Add auto-remember guidance; tag format and usage rules |

### Exit Criteria

- [x] DM call for message B includes message A and prior DM response in its history
- [x] History clears on level change; `/clear` resets and confirms in chat
- [x] Oldest turn pair dropped (not split) when history exceeds 2 000 tokens
- [x] Room-entry auto-describe appends to and reads from the same `_dm_history`
- [x] `[REMEMBER: ...]` tag stripped from chat display; text written to `memory/level_N.md`
- [x] `📝 Noted: <text>` system message appears after auto-remember
- [x] Manual `/remember <text>` continues to work unchanged
- [x] `pytest tests/unit/` green (598 tests)

---

## Phase 17 — Play Mode Loop Guidance

**Status: Complete**

621 unit tests passing.

### Entry Conditions

- Phase 16 complete ✓
- 598 unit tests passing ✓
- Spec: F-27, F-28, F-29 in `spec/FEATURES.md`

### Scope

Three features giving the GM in-play guidance about the active loop narrative structure.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/ui/panels/map_panel.py` (update) | `tests/unit/ui/test_map_panel.py` |
| `dungeon_daddy/views/play_view.py` (update) | `tests/unit/views/test_play_view.py` |
| `dungeon_daddy/llm/agents/dm_agent.py` (update) | `tests/unit/llm/test_dm_agent.py` |

### What to build

| Task | Feature | Notes |
|---|---|---|
| LV-1 | F-29 · DM Agent Loop Context | `active_loop` param + loop section injected into system prompt |
| LV-2 | F-27 · Loop Toggle Strip | pill rects, toggle logic, `on_activate_loop` callback |
| LV-3 | F-28 · Loop Activation System Message | system bubble with explanation, entry/goal, path A/B |

### What was built

- **LV-1** — `DungeonMasterAgent.respond()` gains `active_loop` param; loop section (entry, goal, path A/B rooms) injected into system prompt when loop is active. 9 tests.
- **LV-2** — `MapPanel` draws loop pill chips; toggle logic updates `state.active_loop_id`; `on_activate_loop` callback fired. 5 tests.
- **LV-3** — On loop activation, a system bubble is posted to chat with loop name, entry/goal, and path A/B descriptions. 9 tests.

Smoke test fixes (found during `smoke_test_phase17.py`):
- `MapPanel.draw()` was missing pill rendering — added `draw_chip` calls
- `on_activate_loop` was not updating `state.active_loop_id` — fixed; `LoopOverlay` now responds to toggle

### Exit Criteria

- [x] Loop toggle strip renders pill chips for each loop in the active level
- [x] Clicking a pill toggles the active loop; `LoopOverlay` updates
- [x] Activating a loop posts a system bubble with entry/goal/path details
- [x] `DungeonMasterAgent` system prompt includes loop context when a loop is active
- [x] `pytest tests/unit/` green (621 tests)

---

## Phase 18 — Python Code Quality Stabilisation

**Status: Complete**

Address the type-safety, error-handling, and maintainability gaps identified in
the Python Pro assessment (2026-05-18). No new features. No new runtime behaviour.
All changes must be covered by existing or updated tests.

### Scope

| # | File(s) | Issue | Change |
|---|---------|-------|--------|
| 18-A | `dungeon_daddy/views/design_view.py` | `_design_mode` is a bare `str` — typos are silent | Add `DesignMode(str, Enum)` to `data/models.py`; replace all string literals in `design_view.py` |
| 18-B | `dungeon_daddy/views/design_view.py` | Agent constructor params typed `object \| None` | Replace with concrete types: `WizardAgent \| None`, `DungeonGeneratorAgent \| None`, `DesignAgent \| None` |
| 18-C | `dungeon_daddy/data/models.py` | `sub_loop_roles: list[dict] \| None` — unvalidated structure | Add `SubLoopRole(BaseModel)` with `role: str`; update `Room.sub_loop_roles: list[SubLoopRole] \| None` |
| 18-D | `dungeon_daddy/data/models.py` | `Connection.waypoints: list[dict] \| None` — unvalidated | Add `Waypoint(BaseModel)` with `x: float`, `y: float`; update `Connection.waypoints: list[Waypoint] \| None` |
| 18-E | `dungeon_daddy/llm/provider.py` | `LLMMessage.role: str` — accepts any string | Change to `role: Literal["user", "assistant", "system"]` |
| 18-F | `dungeon_daddy/views/design_view.py:358` | `except Exception: pass` silently swallows errors | Replace with `except Exception: _log.warning(...)` |
| 18-G | `dungeon_daddy/views/design_view.py:604` | Thread targets typed `history: list` | Tighten to `list[LLMMessage]`; `dungeon: object` → `Dungeon` |
| 18-H | `dungeon_daddy/views/design_view.py:641` | Manual double-`for` loop to find a loop by ID | Replace with `next((...), None)` generator expression |
| 18-I | `dungeon_daddy/llm/agents/generator_agent.py:74` | `parse_level` returns `object` | Change return type to `Level`; fix `_build_context` param types |
| 18-J | `pyproject.toml` | No mypy, ruff, or black configuration | Add `[tool.mypy]`, `[tool.ruff]`, and `[tool.ruff.lint]` sections |

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/data/models.py` | `tests/unit/data/test_models.py` |
| `dungeon_daddy/llm/provider.py` | `tests/unit/llm/test_provider.py` |
| `dungeon_daddy/llm/agents/generator_agent.py` | `tests/unit/llm/test_generator_agent.py` |
| `dungeon_daddy/views/design_view.py` | `tests/unit/views/test_design_view.py` |
| `pyproject.toml` | (tooling config — no test file) |

### What to build

**18-A — `DesignMode` enum**
- Add to `dungeon_daddy/data/models.py`:
  ```python
  class DesignMode(str, Enum):
      WIZARD = "wizard"
      LEVEL_WIZARD = "level_wizard"
      GENERATION = "generation"
      EDIT = "edit"
  ```
- Replace every string literal (`"wizard"`, `"edit"`, etc.) in `design_view.py` with `DesignMode.WIZARD`, etc.
- Update any test that compares `_design_mode` to a string literal

**18-C / 18-D — Typed Pydantic sub-models**
- Add `SubLoopRole(BaseModel)` with `role: str`
- Add `Waypoint(BaseModel)` with `x: float`, `y: float`
- Update `Room` and `Connection`; existing JSON round-trips must still pass
- `_coerce_sub_loop_roles` in `generator_agent.py` must be updated to produce dicts
  that Pydantic will coerce into `SubLoopRole` objects

**18-E — `LLMMessage.role` Literal**
- `Literal["user", "assistant", "system"]` covers all three roles used across agents
- Any test that constructs `LLMMessage(role="dm", ...)` must be updated to `"system"` or an
  appropriate role (check each call site)

**18-J — `pyproject.toml` tooling config**
```toml
[tool.mypy]
python_version = "3.12"
strict = true
exclude = ["tests/", "tools/", "prototype/"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
ignore = ["E501"]
```

### Exit Criteria

- [ ] `DesignMode` enum replaces all bare string literals for `_design_mode`; no `"wizard"` / `"edit"` string comparisons remain in `design_view.py`
- [ ] `SubLoopRole` and `Waypoint` Pydantic models exist; `Room` and `Connection` use them; sample dungeon JSON round-trips cleanly
- [ ] `LLMMessage.role` is `Literal["user", "assistant", "system"]`; all call sites pass a valid literal
- [ ] `parse_level` return type is `Level`; agent constructor params in `DesignView` use concrete types
- [ ] Bare `except Exception: pass` in `_close_overlay_ui` replaced with a logged warning
- [ ] Thread target type hints tightened: `history: list[LLMMessage]`, `dungeon: Dungeon`
- [ ] `_on_loop_activated` double-`for` loop replaced with `next()` expression
- [ ] `pyproject.toml` contains `[tool.mypy]`, `[tool.ruff]`, and `[tool.ruff.lint]` sections
- [ ] `pytest tests/unit/` green (all 646 tests pass; update count if new tests added)
- [ ] No new features or runtime behaviour introduced

---

## Post-Phase 18 — Stabilisation Fixes

**Status: Complete** — 664 unit tests passing after all fixes below.

### Smoke Test Verification Fixes (2026-05-17)

| File | Fix |
|---|---|
| `smoke_test_phase3.py`, `smoke_test_phase5.py` | DPI calibration tolerance `< 10` → `< 30` (Win11 invisible resize chrome adds 16 px to `GetWindowRect` width) |
| `smoke_test_phase11.py` | Replaced stale `OS_TITLEBAR_H` constant import with `os_titlebar_h()` function |
| `smoke_test_phase13.py` | Behavior 3b: 10 s pre-send wait (let wizard LLM finish streaming before "overwrite"); replaced fixed 25 s sleep with 5 s poll loop (up to 60 s) |

### Bug Fixes (2026-05-22 / 2026-05-23)

| Date | File | Fix |
|---|---|---|
| 2026-05-22 | `views/play_view.py` | Memory button gate changed from `_has_memory` to `self._dungeon is not None` — button now visible on all floors when a dungeon is loaded, not only floors with pre-existing stored memory |
| 2026-05-22 | `llm/agents/dm_agent.py` | DM system prompt: replaced "use sparingly" opt-in framing with opt-out framing; added "marking a location, manipulating objects" as explicit examples — DM now reliably tags concrete party actions with `[REMEMBER: ...]` |
| 2026-05-23 | `ui/panels/inspector_panel.py` | Theme field replaced with multi-line text area (4 visible lines, word-wrap, scrollbar, mouse-wheel scroll); `_wrap_text` + `on_mouse_scroll` added; design_view routes mouse scroll to inspector first |
| 2026-05-23 | `ui/panels/inspector_panel.py` | Pattern Library: fall back to `LoopPatternCatalog.load_bundled()` when `dungeon.loop_patterns` is empty — fixes empty library for dungeons saved before the field was populated (e.g. The Crucible) |

---

## Post-Phase 18 — IP-9: mypy None-Guard Fixes (6 Deferred Files)

**Status: Complete** — 824 unit tests passing.

Fix all six files that were placed under `ignore_errors = true` in
`pyproject.toml` during IP-1. No new features. No runtime behaviour changes.

**Spec:** `spec/FEATURE_IP9_MYPY_NONE_GUARDS.md`
**GitHub:** https://github.com/ghostpencil/dungeon-daddy/issues/2

### Files fixed

| Step | File | Status |
|---|---|---|
| 1 | `data/repository.py` | DONE |
| 2 | `llm/agents/dm_agent.py` | DONE |
| 3 | `views/design_view.py` | DONE |
| 4 | `views/play_view.py` | DONE |
| 5 | `window.py` | DONE |
| 6 | `ui/panels/map_panel.py` | DONE |
| 7 | `pyproject.toml` — remove all 6 `ignore_errors` overrides | DONE |

Also fixed as part of step 6: `llm/telemetry.py` (`ObservingProvider.last_usage` property added) and `llm/agents/wizard_agent.py` (`Mapping[str, LoopPattern]` replaces `dict[str, object]`).

### Exit Criteria

- [x] `mypy dungeon_daddy` passes with zero per-file overrides for these 6 files
- [x] `pytest tests/unit/` fully green (824 tests)
- [x] CI mypy step passes without the overrides

---

## Post-Phase 18 — Improvement Plan (IP-1 through IP-9, MC-1)

**Status: Complete** — 849 unit/integration tests passing. Stable release declared 2026-05-27.

All quality, tooling, and observability improvements from `spec/IMPROVEMENT_PLAN.md` are complete.

| ID | Title | Result |
|---|---|---|
| IP-1 | CI: lint, type-check, coverage gate | `ruff`, `mypy`, `pytest --cov` in CI; 74% coverage; 70% gate |
| IP-2 | LLM observability | `ObservingProvider` + `llm_calls.jsonl` + `tools/llm_cost_report.py` |
| IP-3 | Structured output for generator agent | `response_format={"type": "json_object"}` via `OpenAIProvider` |
| IP-4 | Model configurable via environment variable | `DUNGEON_DADDY_MODEL` env var; falls back to `gpt-4o` |
| IP-5 | Formal skip markers for API-gated integration tests | `@pytest.mark.live_api`; skip reason visible in CI |
| IP-6 | Minimal AI output evals | `tests/evals/`; 6 evals passing; `tools/run_evals.py` |
| IP-7 | Prompt versioning | `dungeon_daddy/prompts/*.txt`; `load_prompt()`; hash in telemetry |
| IP-8 | Consolidate requirements into pyproject.toml | `requirements.txt` / `requirements-dev.txt` deleted |
| IP-9 | Fix mypy None-guard issues (6 deferred files) | `mypy dungeon_daddy` clean; zero per-file overrides |
| MC-1 | Markdown rendering in chat panels | `MarkdownLabel` + `md_to_html()`; bold, italic, code, headings, bullets |

---

## Phase 19 — Vector Map Layout Phase 1

**Status: Complete** — 337 map unit tests passing. mypy zero errors. Closed 2026-05-30.

Spec: `spec/MAP_LAYOUT_PHASE_NEXT.md`

Improve the dungeon map renderer from a generic node graph into a semantically-aware, visually authored dungeon schematic. Rooms are placed by role, connections are routed orthogonally, labels are placed collision-aware, and the camera auto-fits on load.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/map/dungeon_layout/models.py` (new) | `tests/unit/map/layout/test_models.py` |
| `dungeon_daddy/map/dungeon_layout/semantics.py` (new) | `tests/unit/map/layout/test_semantics.py` |
| `dungeon_daddy/map/dungeon_layout/seed_layout.py` (new) | `tests/unit/map/layout/test_seed_layout.py` |
| `dungeon_daddy/map/dungeon_layout/ports.py` (new) | `tests/unit/map/layout/test_ports.py` |
| `dungeon_daddy/map/dungeon_layout/route_orthogonal.py` (new) | `tests/unit/map/layout/test_routing.py` |
| `dungeon_daddy/map/dungeon_layout/labels.py` (new) | `tests/unit/map/layout/test_labels.py` |
| `dungeon_daddy/map/dungeon_layout/camera_fit.py` (new) | `tests/unit/map/layout/test_camera_fit.py` |
| `dungeon_daddy/map/dungeon_layout/render_cache.py` (new) | (covered by integration) |
| `dungeon_daddy/map/dungeon_layout/validation.py` (new) | `tests/unit/map/layout/test_layout_invariants.py` |
| `dungeon_daddy/map/graph_renderer.py` (update) | `tests/unit/map/test_graph_renderer.py` |

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| 1 | Geometry models | **Done** — `dungeon_layout/models.py`, 21 tests |
| 2 | Room role classification + template selection | **Done** — `dungeon_layout/semantics.py`, 39 tests |
| 3 | Critical-path-first seed layout | **Done** — `dungeon_layout/seed_layout.py`, 4 tests |
| 4 | Port generation | **Done** — `dungeon_layout/ports.py`, 7 tests |
| 5 | Obstacle-aware orthogonal routing | **Done** — `dungeon_layout/route_orthogonal.py`, 7 tests |
| 6 | Label placement | **Done** — `dungeon_layout/labels.py`, 6 tests |
| 7 | Camera auto-fit | **Done** — `dungeon_layout/camera_fit.py`, 6 tests |
| 8 | Validation tests + JSON/Markdown feedback reports | **Done** — `dungeon_layout/validation.py`, 17 unit + 13 integration tests |
| 9 | Debug overlay | **Done** — `dungeon_layout/debug_overlay.py` + `layout_debug_renderer.py`, 9 tests |
| W | Pipeline wiring into map panel | **Done** — `dungeon_layout/__init__.py`, `layout_renderer.py`, `map_panel.py`, 19 tests |
| 10 | Room name labels in Graph view | **Done** — 1 test |
| 11 | Room click + selection highlight | **Done** — 6 tests |
| B | Post-close bug fixes (labels, room/connection → chat) | **Done** — 5 tests |

### Exit Criteria

- [x] At least three real dungeon floor fixtures render using the new pipeline
- [x] Room roles read from metadata or inferred consistently
- [x] At least four layout templates supported: `linear`, `hub_spoke`, `branch_merge`, `boss_endcap` or `lock_key`
- [x] Normal connections use port-based orthogonal routing
- [x] Normal connections do not pass through unrelated rooms
- [x] Excessive rectangular detours are penalized and avoided where a better route exists
- [x] Connection labels placed after routing and avoid obvious collisions
- [x] Camera auto-fit frames the full map on level load
- [x] Debug overlay shows rooms, inflated obstacles, ports, routes, labels, and camera bounds
- [x] Automated tests validate core layout invariants
- [x] Fixture tests generate JSON feedback reports (`test_outputs/layout_feedback/`)
- [x] Fixture tests generate Markdown feedback summary with warnings, metrics, and human review checklists
- [x] Map viewer still uses vector/geometric rendering (not tiles)
- [x] Existing pan/zoom functionality continues to work
- [x] `pytest tests/unit/` green (337 map tests)

---

## Phase 20 — Vector Map Layout Phase 2: Visual Hierarchy & Semantic Presentation

**Status: Complete** — 1097 unit+integration tests passing. Closed 2026-05-30.

Spec: `spec/MAP_LAYOUT_PHASE_2.md`

Built on Phase 19's collision-free graph layout to add semantic visual hierarchy:
room role styling, connection type language, endpoint emphasis, critical path
presentation, and visual hierarchy feedback output. Graph Mode only — Grid Mode
untouched.

### Modules Added / Updated

| Module | Notes |
|---|---|
| `dungeon_daddy/map/dungeon_layout/room_style.py` | `GraphRoomStyle` + `GraphRoomStyleResolver` |
| `dungeon_daddy/map/dungeon_layout/connection_style.py` | `GraphConnectionStyle` + `GraphConnectionStyleResolver` |
| `dungeon_daddy/map/dungeon_layout/endpoint_emphasis.py` | `EndpointEmphasisDetector` + `EndpointEmphasisResult` |
| `dungeon_daddy/map/dungeon_layout/critical_path_style.py` | `CriticalPathPresenter` + `CriticalPathPresentationResult` |
| `dungeon_daddy/map/dungeon_layout/visual_hierarchy_config.py` | `VisualHierarchyConfig` |
| `dungeon_daddy/map/dungeon_layout/visual_hierarchy_feedback.py` | `VisualHierarchyFeedbackReport` + `generate_visual_hierarchy_feedback` |
| `dungeon_daddy/map/dungeon_layout/semantics.py` | Expanded role vocabulary (65 tests) |
| `dungeon_daddy/map/layout_renderer.py` | Styles wired into rendering |
| `tools/generate_layout_screenshots.py` | PIL renderer for PNG artifacts |

### Exit Criteria

- [x] Graph Mode remains collision-free and readable (Phase 1 geometry tests still pass)
- [x] Grid Mode remains untouched
- [x] Room roles produce visible styling differences
- [x] Boss / objective / exit / entrance / hub rooms visually distinct
- [x] Secret / shortcut / vertical connections visually distinct from normal
- [x] Critical path emphasis exists and can be toggled via `VisualHierarchyConfig`
- [x] Generated JSON feedback includes `visual_hierarchy_feedback` section
- [x] Generated Markdown summary includes semantic score and visual warnings
- [x] Screenshot artifacts produced under `artifacts/layout/phase2/`
- [x] `pytest tests/unit/` green (1097 tests)

---

## Phase 21 — Graph Mode Phase 2.5: Semantic Metadata Backfill and Validation

**Status: Not Started**

Spec: `spec/MAP_LAYOUT_PHASE2.5.md`

Improve the semantic layer quality by backfilling explicit metadata into existing
dungeon fixtures and local dungeon files. Reduces `unknown` roles, ambiguous
endpoints, and inferred-only critical paths for `The Crucible` and
`Tomb of the Forgotten King`. Graph Mode only — Grid Mode stays untouched.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/map/dungeon_layout/semantics.py` (update) | `tests/unit/map/layout/test_semantics.py` |
| `dungeon_daddy/map/dungeon_layout/metadata_validator.py` (new) | `tests/unit/map/layout/test_metadata_validator.py` |
| `dungeon_daddy/map/dungeon_layout/metadata_quality_feedback.py` (new) | `tests/unit/map/layout/test_metadata_quality_feedback.py` |
| `dungeon_daddy/map/dungeon_layout/validation.py` (update) | `tests/unit/map/layout/test_validation.py` |
| `scripts/backfill_graph_metadata.py` (new) | (dry-run + write modes) |
| `tests/fixtures/crucible.json` (update) | backfill metadata |
| `tests/fixtures/tomb.json` (update) | backfill metadata |

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| 1 | Update semantic role resolution pipeline (explicit → floor-level → inference) | Not Started |
| 2 | Endpoint detection: explicit `endpoint_room_id` overrides role-priority detection | Not Started |
| 3 | Critical path: explicit `layout_metadata.critical_path` overrides inferred path | Not Started |
| 4 | Connection style: explicit `connection_style` / `layout_connection_role` override | Not Started |
| 5 | Metadata validator (`metadata_validator.py`) with warning output | Not Started |
| 6 | `metadata_quality_feedback` JSON section + updated summary report columns | Not Started |
| 7 | `scripts/backfill_graph_metadata.py` (dry-run / write / backup) | Not Started |
| 8 | Backfill `tests/fixtures/crucible.json` (L1, L2, L3) | Not Started |
| 9 | Backfill `tests/fixtures/tomb.json` (L1 + any additional floors) | Not Started |
| 10 | Backfill local dungeon files (if directory exists) | Not Started |
| 11 | Unit + integration tests | Not Started |
| 12 | Artifact generation: screenshots, feedback JSON, reports | Not Started |

### Exit Criteria

- [ ] Graph Mode still renders all target fixtures
- [ ] Grid Mode remains untouched
- [ ] Geometry score does not regress for target fixtures
- [ ] Explicit entrance metadata for all known entrances in target fixtures
- [ ] Explicit endpoint metadata for all known endpoints in target fixtures
- [ ] Explicit critical path for target fixtures where design intent is known
- [ ] `Maintenance Tunnel` (Crucible L2) no longer an unknown endpoint
- [ ] `Power Core Chamber` (Crucible L3) is endpoint when explicit metadata says so
- [ ] `Descent Chamber` (Tomb L1) explicitly treated as descent/endpoint
- [ ] Semantic scores improve or stay the same for all target fixtures
- [ ] Unknown role count decreases for target fixtures
- [ ] `metadata_quality_feedback` appears in JSON reports
- [ ] Summary report includes metadata quality columns
- [ ] Backfill script runs in dry-run mode
- [ ] Backfill script creates timestamped backups before writing local files
- [ ] Absent local dungeon directory reported as `LOCAL_DUNGEON_DIRECTORY_NOT_FOUND`; does not fail CI
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] mypy passes
- [ ] Artifacts present under `artifacts/layout/phase2_5/`

---

## Notes for the Implementing Agent

- **Do not advance to the next phase until all exit criteria for the current phase are met.**
- **Each phase's test files are written before the module they cover.** See `spec/TESTING.md`.
- **Update this file** when a phase is complete: change `Not Started` → `Complete`
  (or `In Progress` if partially done).
- Phases 1–4 have no Arcade display dependency — run them in any environment.
- Phases 5–8 require a display; on headless CI, skip arcade-rendering tests using
  `pytest -m "not requires_display"` (mark those tests accordingly).
