# Implementation Phases — 11 through 18 (+ Post-18 Stabilisation)

## Phase 11 â€” Design Mode Polish + Context Docs Foundation

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

**F-11 â€” Tree room path colouring**
- `DungeonTreePanel.set_active_loop(loop: Loop | None)` â€” stores the active loop for the current level
- `draw()` â€” room rows tinted: path A â†’ TEAL, path B â†’ VIOLET, both â†’ INDIGO, neither â†’ INK_3
- Wire: when `on_activate_loop` fires in `DesignView`, call `_tree.set_active_loop(loop)`

**F-12 â€” Design chat keyboard shortcuts**
- `ChatPanel.on_key_press(key, modifiers)` â€” Ctrl+Enter calls `_on_send()`; Enter inserts `\n`
- `DesignView.on_key_press()` routes to `self._chat.on_key_press()`

**F-13 â€” Inspector Settings Tab editable fields**
- Party size, party level, theme, level count, complexity segmented control all write back to
  `dungeon.meta` on change (in-memory; no auto-save)
- `InspectorPanel.set_on_settings_change(callback)` â€” fires with updated `DungeonMeta` on any edit

**F-14 â€” Activate loop â†’ tree highlight**
- `DesignView` passes `on_activate_loop=self._on_activate_loop` when constructing `InspectorPanel`
- `_on_activate_loop(loop_id)` looks up the loop and calls `self._tree.set_active_loop(loop)`

**C-1 â€” Context doc file structure + repo load/save**
- `ContextDocType` enum: `SETTING`, `PARTY`, `LEVEL_DESIGN`
- `DungeonRepository.load_context_doc(dungeon_name, doc_type, level_id=None) -> str`
- `DungeonRepository.save_context_doc(dungeon_name, doc_type, content, level_id=None)`
- Files live at: `{data_dir}/{dungeon_name}/setting.md`, `party.md`, `level_{N}_design.md`
- Level design doc format: plain markdown with `## Ecology`, `## Design Notes` headings;
  extensible â€” future phases can add `## Monsters` without breaking existing files

**C-2 â€” Wizard generates first-draft docs**
- After generation completes, `DesignView._finish_generation()` calls `_generate_context_docs()`
- `_generate_context_docs()` calls `DesignAgent` (or a dedicated prompt) to produce:
  - `setting.md` â€” dungeon world lore, atmosphere, factions, history (from `DungeonBrief`)
  - `party.md` â€” party backstory, motivations, hooks (from `DungeonBrief`)
  - `level_N_design.md` â€” per-level ecology and design notes (from each generated level)
- Docs are saved via `DungeonRepository.save_context_doc()`
- A "Writing context docsâ€¦" system bubble appears while generation runs

**C-3 â€” Context Docs UI**
- `InspectorPanel` Settings tab Context Docs rows show real word counts from loaded files
- `_context_doc_rects: list[tuple]` populated during `draw()` for hit-testing
- Clicking a row opens a `UITextArea` overlay (same pattern as Edit Memory overlay in Phase 9)
- Save writes the file via `save_context_doc()`; cancel discards; overlay has Save + Cancel buttons
- Status display: `âœ“ NNN words` (file exists, non-empty), `â—‹ pending` (file missing or empty)

### What was built

- **F-11** â€” `DungeonTreePanel.set_active_loop(loop)` added; room rows render `â–¶`/TEAL (path A), `â—‡`/VIOLET (path B), `â—†`/INDIGO (both), `â–¢`/INK_3 (neither). `INDIGO = (158, 100, 210)` added to `theme.py`. 5 new tests; 315 passing.
- **F-14** â€” `LoopsPanel` stores `_loop_rects` per loop row; click fires `activate_loop(loop_id)` â†’ `on_activate_loop` callback. `DesignView._on_loop_activated(loop_id)` searches dungeon levels for matching `Loop` and calls `_tree.set_active_loop(loop)`. Wired via `InspectorPanel(on_activate_loop=...)`. 3 new tests; 318 passing.
- **F-12** â€” `ChatPanel.handle_key_press(key, modifiers) -> bool` added: Ctrl+Enter calls `_do_send()` and returns `True` (consumed); all other keys return `False`. `DesignView.on_key_press` delegates to it. 5 new tests; 323 passing.
- **F-13** â€” `DungeonMeta` extended with `party_size=4`, `party_level=3`, `num_levels=3`, `complexity="Moderate"`. `InspectorPanel` gains `set_on_settings_change`, `on_settings_field_change`, `on_complexity_change`; complexity segment clicks wired via `_complexity_seg_rects`. 19 new tests; 342 passing.
- **C-1** â€” `ContextDocType(str, Enum)` added to `models.py` (`SETTING`, `PARTY`, `LEVEL_DESIGN`). `DungeonRepository.load_context_doc` / `save_context_doc` added; files at `{data_dir}/{dungeon_name}/setting.md`, `party.md`, `level_{N}_design.md`. 7 new tests; 349 passing.
- **C-2** â€” `dungeon_daddy/llm/context_docs.py` added: `generate_setting_doc`, `generate_party_doc`, `generate_level_design_doc`, `generate_all_context_docs`. `skip_existing=True` by default. 14 new tests; 363 passing.
- **C-3** â€” `ContextDocStatus`; `set_context_doc_statuses`; `_context_doc_rects` hit-test; `open/save/close_context_doc_overlay` in DesignView; `_refresh_context_doc_statuses` on load. 373 total tests.

### Exit Criteria

- [x] Tree room rows tinted by loop path membership; tint updates when loop is activated
- [x] Ctrl+Enter sends Design chat message; Enter inserts newline
- [x] Settings tab fields (party size/level, theme, levels, complexity) are editable; in-memory state updates
- [x] Activating a loop from Loops tab calls `on_activate_loop` â†’ tree colours update
- [x] `DungeonRepository` load/save context docs round-trips correctly; `tmp_path` used in tests
- [x] Wizard generates `setting.md` + `party.md` after all levels complete
- [x] `level_N_design.md` created per level with ecology + design notes
- [x] Context Docs UI shows real word counts (not hardcoded)
- [x] Click row â†’ edit overlay opens pre-filled; save persists; cancel discards
- [x] `pytest tests/unit/` green (373 tests)

---

## Phase 12 â€” Context Engineering

**Status: Complete**

Add intelligent context assembly so the LLM always receives the most relevant
dungeon information without exceeding its context budget. Uses compaction â€”
an LLM-generated dense summary â€” rather than truncation.

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
- `ContextCompactor(provider: LLMProvider)` â€” uses the injected provider to compress docs
- `compact(content: str, doc_type: ContextDocType) -> str` â€” returns a dense summary preserving
  all key facts; prompt is doc-type-aware (setting doc vs. party doc vs. level doc)
- Dirty-flag caching: compacted version stored as `{name}.compact.md` alongside the original;
  regenerated only when the source file is newer than the compact file

**ContextBuilder**
- `ContextBuilder(repo: DungeonRepository, compactor: ContextCompactor)`
- `build_design_context(dungeon, active_level_id=None) -> str` â€” assembles system prompt context:
  1. Structured dungeon meta (always, ~200 tokens)
  2. `setting.md` or `setting.compact.md` if over budget
  3. `party.md` or `party.compact.md` if over budget
  4. `level_N_design.md` for active level (or compact) if budget allows
- `build_play_context(dungeon, level, room, room_memory="") -> str` â€” assembles DM context:
  1. Current room + level ecology (always)
  2. `setting.md` compact (dungeon atmosphere)
  3. `party.md` compact (who the party is)
  4. Room memory (always, already small)
- `TOKEN_BUDGET = 3000` â€” approximate token ceiling for context block (1 token â‰ˆ 4 chars)
- Budget enforcement: each doc measured in chars; compact version used when `len(doc) / 4 > remaining_budget`

**Agent integration**
- `DesignAgent._build_context()` replaced by `ContextBuilder.build_design_context()`
- `DungeonMasterAgent._build_context()` replaced by `ContextBuilder.build_play_context()`
- Both agents receive `ContextBuilder` via dependency injection at construction

### Exit Criteria

- [x] `ContextCompactor.compact()` calls provider exactly once and returns non-empty string
- [x] Compact file is written alongside source; not regenerated when source is unchanged
- [x] `ContextBuilder` assembles context within `TOKEN_BUDGET` chars Ã— 4
- [x] When a doc fits in budget, full doc is used; when it exceeds, compact version is used
- [x] `DesignAgent` and `DungeonMasterAgent` use `ContextBuilder`; tests verify context includes setting doc content
- [x] No real API calls in unit tests (provider mocked)
- [x] `pytest tests/unit/` green

---

## Phase 13 â€” Incremental Context Docs + Wizard Save-Name

**Status: Complete**

433 unit tests passing after post-phase stabilisation.

### What was built

- `DungeonMeta.save_name: str | None = None` + `effective_name` property (`save_name or title`)
- `ContextBuilder` and `window.save_dungeon()` use `effective_name`
- `DesignView._write_setting_party_docs()` â€” called at brief-parse time
- `DesignView._write_level_design_doc(level)` â€” called after each level passes validation
- `DesignView._continue_to_generation()` extracted; `_context_overwrite_confirmed` + `_awaiting_name_choice` flags
- `_on_chat_send` intercepts `_awaiting_name_choice` before normal routing
- Post-phase stabilisation: `File â†’ Open...` (Ctrl+O), per-dungeon folder layout, auto-migration, open error dialog, removed "+ Add level" button

### Exit Criteria

- [x] `DungeonMeta.save_name` field present; `None` falls back to `title` everywhere
- [x] `ContextBuilder` and `save_dungeon()` use `save_name or title`
- [x] `setting.md` and `party.md` written immediately after Phase 1 resolves
- [x] `level_N_design.md` written after each level passes validation
- [x] Inspector context doc rows update in real time as wizard progresses
- [x] If `setting.md` pre-exists, GM prompted once to overwrite or provide a new save name
- [x] `pytest tests/unit/` green (433 tests)

---

## Phase 14 â€” Obstacle-Aware Map Connection Routing

**Status: Complete**

481 unit tests passing.

### What was built

- `dungeon_daddy/map/routing.py` â€” pure geometry helpers: `get_room_rect`, `get_room_port`, `line_intersects_rect`, `path_intersects_any_room`, `calculate_path_length`, `select_port_direction`, `straight_path_blocked`, `route_orthogonal`, `route_detour`, `route_waypoints`, `is_route_problematic`; `CONNECTION_OBSTACLE_MARGIN = 16`
- `GridRenderer._port_screen()` + updated `draw()` â€” edge-port routing, orthogonal/detour/waypoint paths
- `Connection.waypoints: list[dict] | None = None` â€” optional manual waypoints in JSON
- `GridRenderer(debug_routing=True)` â€” draws TEAL port dots at endpoints, TEAL waypoint dots, EMBER segments for problematic routes

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

## Phase 15 â€” Localized Connection Routing Refinement

**Status: Complete**

576 unit tests passing.

### Entry Conditions

- Phase 14 complete âœ“
- 481 unit tests passing âœ“
- Spec: `spec/FEATURE_MAP_CONNECTION_ROUTING_2.md`
- Validation test already written â€” do not rewrite it
- Second fixture `tests/fixtures/tomb.json` added (48 additional validation cases, all passing)

### Scope

| Task | Feature | Status | Notes |
|---|---|---|---|
| LR-1 | Add `get_local_bounds` | **Done** | `routing.py`: bounding rect of both rooms + `ROUTE_BOUNDING_MARGIN = 4` |
| LR-2 | Update `_score_path` | **Done** | Escape penalty, detour-ratio penalty, bend Ã— 100, length Ã— 10; `INTERSECTION_WEIGHT = 5000` |
| LR-3 | Fix `route_detour` candidates | **Done** | Waypoints clamped to local bounds; `fy == ty` degenerate case generates 5-point above/below paths; `fx == tx` symmetric fix also added |
| LR-4 | Update `route_orthogonal` | **Done** | Passes `local_bounds` + `direct_distance` into `_score_path` |
| LR-5 | Add constants | **Done** | `ROUTE_BOUNDING_MARGIN=4`, `INTERSECTION_WEIGHT=5000`, `ESCAPE_WEIGHT=500`, `MAX_DETOUR_RATIO=5.0`, `MAX_BEND_COUNT=6` |
| LR-6 | Degenerate unit test | **Done** | `test_routing.py::test_route_detour_degenerate_horizontal_alignment_avoids_blocker` |

### What was built

- **LR-5** â€” Constants added to `routing.py`: `ROUTE_BOUNDING_MARGIN=4`, `INTERSECTION_WEIGHT=5000`, `ESCAPE_WEIGHT=500`, `MAX_DETOUR_RATIO=5.0`, `MAX_BEND_COUNT=6`.
- **LR-1** â€” `get_local_bounds(from_room, to_room, margin=ROUTE_BOUNDING_MARGIN) -> Rect` added; returns bounding rect of both rooms expanded by margin.
- **LR-2** â€” `_score_path` updated: new formula `intersections * 5000 + length * 10 + bends * 100 + escape_penalty + detour_ratio_penalty`. Two private helpers added: `_escape_distance` and `_detour_ratio_penalty`.
- **LR-3** â€” `route_detour` clamps all four bypass positions to `local_bounds`. For `fy == ty`: replaces degenerate left/right with 5-point above/below paths that step vertically first. `fx == tx` symmetric case also handled.
- **LR-4** â€” `route_orthogonal` computes `local` and `direct_dist` and passes both into `_score_path`.
- **LR-6** â€” Synthetic unit test with a blocker directly between two horizontally-aligned rooms plus top/bottom walls that force left/right candidates; confirms the degenerate fix avoids the blocker.

### Post-Phase-15 Bug Fix

| Fix | What changed |
|---|---|
| `hit_test_connection` uses actual route path | Was testing straight center-to-center line; now mirrors `draw()` logic (waypoints â†’ detour-if-blocked â†’ straight port-to-port) and tests each segment. Bent connections are now clickable. 576 tests. |

### Exit Criteria

- [x] `tests/unit/map/test_routing_validation.py` â€” all 102 tests pass (was 99/102)
- [x] `L3/r5â†’r6` stays within local bounds (still flagged problematic, but local)
- [x] Degenerate `fy == ty` case covered by synthetic unit test in `test_routing.py`
- [x] Constants exported from `routing.py`
- [x] `pytest tests/unit/` green (576 tests)

---

## Phase 16 â€” DM Stateful Conversation

**Status: Complete**

598 unit tests passing.

### Entry Conditions

- Phase 15 complete âœ“
- 576 unit tests passing âœ“
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
| SC-2 | History compaction â€” drop oldest turns | Budget 2 000 tokens; drop oldest user+assistant pairs |
| SC-3 | Clear on level change + `/clear` command | `_dm_history = []`; post `"ðŸ’¬ Conversation cleared."` system message |
| SC-4 | Increase `DMAgent` `max_tokens` 512 â†’ 1 024 | `dm_agent.py` respond call |
| SC-5 | `[REMEMBER]` tag parsing + auto-remember | `_extract_remember()` in `play_view.py`; strip tag, call `append_room_event`, post `ðŸ“ Noted:` |
| SC-6 | Update `DungeonMasterAgent` `SYSTEM_PROMPT` | Add auto-remember guidance; tag format and usage rules |

### Exit Criteria

- [x] DM call for message B includes message A and prior DM response in its history
- [x] History clears on level change; `/clear` resets and confirms in chat
- [x] Oldest turn pair dropped (not split) when history exceeds 2 000 tokens
- [x] Room-entry auto-describe appends to and reads from the same `_dm_history`
- [x] `[REMEMBER: ...]` tag stripped from chat display; text written to `memory/level_N.md`
- [x] `ðŸ“ Noted: <text>` system message appears after auto-remember
- [x] Manual `/remember <text>` continues to work unchanged
- [x] `pytest tests/unit/` green (598 tests)

---

## Phase 17 â€” Play Mode Loop Guidance

**Status: Complete**

621 unit tests passing.

### Entry Conditions

- Phase 16 complete âœ“
- 598 unit tests passing âœ“
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
| LV-1 | F-29 Â· DM Agent Loop Context | `active_loop` param + loop section injected into system prompt |
| LV-2 | F-27 Â· Loop Toggle Strip | pill rects, toggle logic, `on_activate_loop` callback |
| LV-3 | F-28 Â· Loop Activation System Message | system bubble with explanation, entry/goal, path A/B |

### What was built

- **LV-1** â€” `DungeonMasterAgent.respond()` gains `active_loop` param; loop section (entry, goal, path A/B rooms) injected into system prompt when loop is active. 9 tests.
- **LV-2** â€” `MapPanel` draws loop pill chips; toggle logic updates `state.active_loop_id`; `on_activate_loop` callback fired. 5 tests.
- **LV-3** â€” On loop activation, a system bubble is posted to chat with loop name, entry/goal, and path A/B descriptions. 9 tests.

Smoke test fixes (found during `smoke_test_phase17.py`):
- `MapPanel.draw()` was missing pill rendering â€” added `draw_chip` calls
- `on_activate_loop` was not updating `state.active_loop_id` â€” fixed; `LoopOverlay` now responds to toggle

### Exit Criteria

- [x] Loop toggle strip renders pill chips for each loop in the active level
- [x] Clicking a pill toggles the active loop; `LoopOverlay` updates
- [x] Activating a loop posts a system bubble with entry/goal/path details
- [x] `DungeonMasterAgent` system prompt includes loop context when a loop is active
- [x] `pytest tests/unit/` green (621 tests)

---

## Phase 18 â€” Python Code Quality Stabilisation

**Status: Complete**

Address the type-safety, error-handling, and maintainability gaps identified in
the Python Pro assessment (2026-05-18). No new features. No new runtime behaviour.
All changes must be covered by existing or updated tests.

### Scope

| # | File(s) | Issue | Change |
|---|---------|-------|--------|
| 18-A | `dungeon_daddy/views/design_view.py` | `_design_mode` is a bare `str` â€” typos are silent | Add `DesignMode(str, Enum)` to `data/models.py`; replace all string literals in `design_view.py` |
| 18-B | `dungeon_daddy/views/design_view.py` | Agent constructor params typed `object \| None` | Replace with concrete types: `WizardAgent \| None`, `DungeonGeneratorAgent \| None`, `DesignAgent \| None` |
| 18-C | `dungeon_daddy/data/models.py` | `sub_loop_roles: list[dict] \| None` â€” unvalidated structure | Add `SubLoopRole(BaseModel)` with `role: str`; update `Room.sub_loop_roles: list[SubLoopRole] \| None` |
| 18-D | `dungeon_daddy/data/models.py` | `Connection.waypoints: list[dict] \| None` â€” unvalidated | Add `Waypoint(BaseModel)` with `x: float`, `y: float`; update `Connection.waypoints: list[Waypoint] \| None` |
| 18-E | `dungeon_daddy/llm/provider.py` | `LLMMessage.role: str` â€” accepts any string | Change to `role: Literal["user", "assistant", "system"]` |
| 18-F | `dungeon_daddy/views/design_view.py:358` | `except Exception: pass` silently swallows errors | Replace with `except Exception: _log.warning(...)` |
| 18-G | `dungeon_daddy/views/design_view.py:604` | Thread targets typed `history: list` | Tighten to `list[LLMMessage]`; `dungeon: object` â†’ `Dungeon` |
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
| `pyproject.toml` | (tooling config â€” no test file) |

### What to build

**18-A â€” `DesignMode` enum**
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

**18-C / 18-D â€” Typed Pydantic sub-models**
- Add `SubLoopRole(BaseModel)` with `role: str`
- Add `Waypoint(BaseModel)` with `x: float`, `y: float`
- Update `Room` and `Connection`; existing JSON round-trips must still pass
- `_coerce_sub_loop_roles` in `generator_agent.py` must be updated to produce dicts
  that Pydantic will coerce into `SubLoopRole` objects

**18-E â€” `LLMMessage.role` Literal**
- `Literal["user", "assistant", "system"]` covers all three roles used across agents
- Any test that constructs `LLMMessage(role="dm", ...)` must be updated to `"system"` or an
  appropriate role (check each call site)

**18-J â€” `pyproject.toml` tooling config**
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

## Post-Phase 18 â€” Stabilisation Fixes

**Status: Complete** â€” 664 unit tests passing after all fixes below.

### Smoke Test Verification Fixes (2026-05-17)

| File | Fix |
|---|---|
| `smoke_test_phase3.py`, `smoke_test_phase5.py` | DPI calibration tolerance `< 10` â†’ `< 30` (Win11 invisible resize chrome adds 16 px to `GetWindowRect` width) |
| `smoke_test_phase11.py` | Replaced stale `OS_TITLEBAR_H` constant import with `os_titlebar_h()` function |
| `smoke_test_phase13.py` | Behavior 3b: 10 s pre-send wait (let wizard LLM finish streaming before "overwrite"); replaced fixed 25 s sleep with 5 s poll loop (up to 60 s) |

### Bug Fixes (2026-05-22 / 2026-05-23)

| Date | File | Fix |
|---|---|---|
| 2026-05-22 | `views/play_view.py` | Memory button gate changed from `_has_memory` to `self._dungeon is not None` â€” button now visible on all floors when a dungeon is loaded, not only floors with pre-existing stored memory |
| 2026-05-22 | `llm/agents/dm_agent.py` | DM system prompt: replaced "use sparingly" opt-in framing with opt-out framing; added "marking a location, manipulating objects" as explicit examples â€” DM now reliably tags concrete party actions with `[REMEMBER: ...]` |
| 2026-05-23 | `ui/panels/inspector_panel.py` | Theme field replaced with multi-line text area (4 visible lines, word-wrap, scrollbar, mouse-wheel scroll); `_wrap_text` + `on_mouse_scroll` added; design_view routes mouse scroll to inspector first |
| 2026-05-23 | `ui/panels/inspector_panel.py` | Pattern Library: fall back to `LoopPatternCatalog.load_bundled()` when `dungeon.loop_patterns` is empty â€” fixes empty library for dungeons saved before the field was populated (e.g. The Crucible) |

---

## Post-Phase 18 â€” IP-9: mypy None-Guard Fixes (6 Deferred Files)

**Status: Complete** â€” 824 unit tests passing.

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
| 7 | `pyproject.toml` â€” remove all 6 `ignore_errors` overrides | DONE |

Also fixed as part of step 6: `llm/telemetry.py` (`ObservingProvider.last_usage` property added) and `llm/agents/wizard_agent.py` (`Mapping[str, LoopPattern]` replaces `dict[str, object]`).

### Exit Criteria

- [x] `mypy dungeon_daddy` passes with zero per-file overrides for these 6 files
- [x] `pytest tests/unit/` fully green (824 tests)
- [x] CI mypy step passes without the overrides

---

## Post-Phase 18 â€” Improvement Plan (IP-1 through IP-9, MC-1)

**Status: Complete** â€” 849 unit/integration tests passing. Stable release declared 2026-05-27.

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


