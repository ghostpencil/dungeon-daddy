# Feature: Test Drive vs. Start Play

## Purpose

Two buttons in the Inspector footer launch Play Mode, but they serve different GM intentions:

| | Test Drive | Start Play / Continue Play |
|---|---|---|
| **Intent** | Explore a level informally | Begin or resume a true play session |
| **Saves play actions?** | No — all discarded on exit | Yes — persisted to disk |
| **Requires saved dungeon?** | No | Yes — dungeon must be saved to disk |

---

## Test Drive

### When it is available

- At least one level exists in the dungeon.
- The dungeon does **not** need to be saved to disk.

### What it does

1. Launches Play Mode with the current in-memory dungeon.
2. Creates a **transient** `SessionState` — not backed by any saved file.
3. The `dungeon_id` in the transient session is never used to write to disk.

### What is NOT persisted

- DM chat history (`play_transcript`)
- Room memory (`memory/level_<id>.md`)
- Loop activations (`active_loop_id`)
- Current floor and room position (`current_level_idx`, `current_room_id`, `visited_rooms`)

### Exit behavior

When the GM returns to Design Mode (Back to Design button):

- The transient `SessionState` is discarded.
- No files are written.
- The `Dungeon` object is unchanged — no deep copy needed because Test Drive never writes to the dungeon or to disk.

### UI notes

- Button label: **"Test Drive"** (ghost/secondary style — always).
- Enabled whenever at least one level exists.

---

## Start Play / Continue Play

### When it is available

- At least one level exists in the dungeon.
- The dungeon **must be saved to disk** — `dungeon.meta.save_name` must be set.
- If the dungeon is not yet saved, the button is **disabled** and shows a tooltip: _"Save dungeon first"_.

### Determining fresh start vs. continuation

The button label reflects whether prior session data exists:

| Condition | Label |
|---|---|
| No `session.json` **and** no room-memory files exist for this dungeon | **"Start Play →"** |
| A `session.json` **or** any room-memory file exists | **"Continue Play →"** |

Detection uses `DungeonRepository`:
- `repo.load_session(save_name)` — non-`None` → continuation.
- `repo.load_room_memory(save_name, level_id)` for any level — non-empty → continuation.
  (Either condition alone is sufficient.)

### What it does — fresh start

1. Launches Play Mode.
2. Creates a new `SessionState` with `dungeon_id = dungeon.meta.save_name`.
3. Writes `session.json` on first meaningful action (e.g. room click, DM message).

### What it does — continuation

1. Launches Play Mode.
2. Loads the existing `SessionState` from `session.json`.
3. Restores: `current_level_idx`, `current_room_id`, `visited_rooms`, `active_loop_id`, `play_transcript`.
4. Loads room memory for the restored level from `memory/level_<id>.md`.

### What is persisted

- DM chat history (`play_transcript` in `session.json`)
- Room memory (`memory/level_<id>.md`) — written when the GM saves the memory overlay
- Loop activations (`active_loop_id` in `session.json`)
- Current floor and room (`current_level_idx`, `current_room_id`, `visited_rooms` in `session.json`)

Session state is written to disk on every meaningful change (room click, DM message, loop activation, memory save).

### Exit behavior

When the GM returns to Design Mode:

- Current `SessionState` is written to disk before switching views.
- Play data remains on disk and is available for a future continuation.

---

## Inspector Panel Button States

```
┌───────────────────────────────────────┐
│  [Test Drive]        [Start Play →]   │  — dungeon unsaved, ≥1 level
│  [Test Drive]        [Continue Play →]│  — dungeon saved, prior session exists
│  [Test Drive]        [Start Play →]   │  — dungeon saved, no prior session
│  [Test Drive]        [Start Play →]   │  — dungeon saved, Start Play disabled
│                                       │     tooltip: "Save dungeon first"
└───────────────────────────────────────┘
```

- **Test Drive** — ghost/secondary style, enabled whenever ≥1 level exists.
- **Start Play / Continue Play** — primary style, disabled (greyed) when dungeon is not saved.

---

## Data Flow Summary

```
Test Drive clicked
  └─ window.launch_test_drive(dungeon)
       └─ play_view.load_dungeon_transient(dungeon)
            └─ creates SessionState(dungeon_id="__test_drive__", ...)
            └─ no repo writes at any point

Start/Continue Play clicked
  └─ window.launch_play_session(dungeon)
       └─ play_view.load_dungeon_session(dungeon, repo)
            ├─ [fresh]  creates new SessionState(dungeon_id=save_name)
            └─ [resume] loads SessionState from repo.load_session(save_name)
```

---

## Acceptance Criteria

### Test Drive

- [ ] Clicking "Test Drive" on an unsaved dungeon opens Play Mode.
- [ ] DM messages sent during Test Drive are visible in Play Mode but are gone when returning to Design Mode.
- [ ] Room memory written during Test Drive is gone when returning to Design Mode.
- [ ] Loop activations during Test Drive are not reflected after returning.
- [ ] No files are created or modified in the dungeons directory during a Test Drive session.

### Start Play (fresh)

- [ ] "Start Play →" is disabled when `dungeon.meta.save_name` is `None`.
- [ ] Clicking "Start Play →" on a saved dungeon opens Play Mode with a fresh session.
- [ ] `session.json` is written after the first meaningful play action.

### Continue Play (resume)

- [ ] The button label changes to "Continue Play →" when a session or room memory exists for the dungeon.
- [ ] Clicking "Continue Play →" restores current level, room, visited rooms, loop state, and play transcript.
- [ ] Room memory for the restored level is loaded into the DM context.

### Exit

- [ ] Returning from Test Drive to Design Mode discards all play data.
- [ ] Returning from Start/Continue Play to Design Mode writes session state to disk.

---

## Implementation Plan

> TDD order: write the failing test, then the minimal code to pass it, then refactor.
> Each step is one failing test + one code change unless noted otherwise.

---

### Affected Files

| File | Change |
|---|---|
| `dungeon_daddy/views/play_view.py` | Split `load_dungeon` → `load_dungeon_transient` + `load_dungeon_session`; add `_is_test_drive` flag; gate all repo writes |
| `dungeon_daddy/window.py` | Add `launch_play_session(dungeon)` alongside existing `launch_test_drive` |
| `dungeon_daddy/views/design_view.py` | Fix button routing (bug); add `_launch_start_play`; refresh inspector session state |
| `dungeon_daddy/ui/panels/inspector_panel.py` | Add `set_saved_state(is_saved, has_session)`; update `draw()` and `hit_start_play()` |
| `tests/unit/views/test_play_view.py` | New tests for transient vs. session load paths |
| `tests/unit/ui/panels/test_inspector_panel.py` | New tests for button states |
| `tests/unit/views/test_design_view.py` | New tests for split routing |

No new dependencies, no new models. `SessionState` already exists in `models.py`.
`DungeonRepository.load_session` / `save_session` / `load_room_memory` already exist.

---

### Step 1 — `PlayView`: split `load_dungeon` into transient and session variants

**Current state:** `load_dungeon(dungeon)` creates `SessionState(dungeon_id=dungeon.meta.title, ...)` but never writes to disk — it is already effectively transient. The bug is only that it is the only entry point.

**Changes to `play_view.py`:**

1. Add `self._is_test_drive: bool = False` to `__init__`.
2. Rename current `load_dungeon` → `load_dungeon_transient`. Inside it, set `self._is_test_drive = True` and use `dungeon_id = "__test_drive__"`.
3. Add `load_dungeon_session(dungeon: Dungeon) -> None`:
   - Sets `self._is_test_drive = False`.
   - `save_name = dungeon.meta.save_name` (caller guarantees it is set).
   - Calls `repo.load_session(save_name)` — if found, restores state; if not, creates fresh `SessionState(dungeon_id=save_name, current_level_idx=0)`.
   - When resuming: shows system message `"Resuming session — Level {n}: {name}."` and loads that level's map.
   - When fresh: shows existing welcome message.
4. Gate all repo-write calls on `not self._is_test_drive`:
   - `save_memory_overlay` → `_repo.save_room_memory` (already conditional on overlay; add the flag check)
   - `_handle_remember` / `_auto_remember` → `_repo.append_room_event`
5. Add `_save_session()` helper — writes `_repo.save_session(self._state)` if `not self._is_test_drive`.
6. Call `_save_session()` after: room click (state update), level change, loop activation, `save_memory_overlay`.
7. Call `_save_session()` from `on_hide_view` (flush before switching back to Design Mode).

**New tests (`test_play_view.py`):**

- `test_load_dungeon_transient_sets_flag` — `_is_test_drive` is True after transient load.
- `test_load_dungeon_transient_does_not_write_repo` — repo mock receives no write calls after transient load + room click + loop activation + memory save.
- `test_load_dungeon_session_fresh_creates_state` — fresh session: `SessionState.dungeon_id == save_name`.
- `test_load_dungeon_session_resumes_existing` — repo returns saved `SessionState`; level index and room are restored.
- `test_load_dungeon_session_saves_on_room_click` — `repo.save_session` called after click event.
- `test_load_dungeon_session_saves_on_hide` — `repo.save_session` called from `on_hide_view`.

---

### Step 2 — `DungeonDaddyWindow`: add `launch_play_session`

**Changes to `window.py`:**

- Add `launch_play_session(dungeon: Dungeon) -> None`:
  ```python
  def launch_play_session(self, dungeon: object) -> None:
      self._play_view.load_dungeon_session(dungeon)
      self.switch_to_play()
  ```
- Keep `launch_test_drive` unchanged (it will call `load_dungeon_transient` after Step 1).

**New test:** `test_launch_play_session_calls_load_and_switches` — mock `_play_view` and `switch_to_play`.

---

### Step 3 — `InspectorPanel`: saved/session button state

**Changes to `inspector_panel.py`:**

1. Add two state fields in `__init__`:
   ```python
   self._is_saved: bool = False
   self._has_session: bool = False
   ```
2. Add `set_saved_state(self, is_saved: bool, has_session: bool) -> None` that sets the fields.
3. Update `draw()` footer section:
   - "Start Play →" label → `"Continue Play →"` when `_has_session` is True.
   - "Start Play →" / "Continue Play →" uses `TEAL` when saved, `TEAL_DIM` when not saved.
   - Text color: `INK_2` when saved, `INK_4` when not saved (visually disabled).
4. Update `hit_start_play()`:
   - Return `False` when `not self._is_saved` (regardless of click position).

**New tests (`test_inspector_panel.py`):**

- `test_start_play_disabled_when_not_saved` — `hit_start_play` returns False when `_is_saved=False` even if dungeon has levels.
- `test_start_play_enabled_when_saved` — returns True when `_is_saved=True` and cursor is over rect.
- `test_label_is_continue_play_when_has_session` — drawing is called with "Continue Play →" label (spy/mock `arcade.draw_text`).
- `test_label_is_start_play_when_no_session` — drawing is called with "Start Play →" label.

---

### Step 4 — `DesignView`: fix routing and refresh inspector state

**Changes to `design_view.py`:**

1. Fix the routing bug at line 202:
   ```python
   # Before (bug):
   if self._inspector.hit_test_drive(x, y) or self._inspector.hit_start_play(x, y):
       self._launch_test_drive()

   # After:
   if self._inspector.hit_test_drive(x, y):
       self._launch_test_drive()
   elif self._inspector.hit_start_play(x, y):
       self._launch_start_play()
   ```
2. Add `_launch_start_play(self) -> None`:
   ```python
   def _launch_start_play(self) -> None:
       if self._dungeon and self._dungeon.levels and self._dungeon.meta.save_name:
           self.window.launch_play_session(self._dungeon)
   ```
3. Add `_refresh_play_button_state(self) -> None`:
   - Checks `is_saved = bool(self._dungeon and self._dungeon.meta.save_name)`.
   - Checks `has_session` by calling `self._repo.load_session(save_name)` or checking `self._repo.load_room_memory(save_name, level.id)` for any level.
   - Calls `self._inspector.set_saved_state(is_saved, has_session)`.
4. Call `_refresh_play_button_state()` from:
   - `load_dungeon()` (after dungeon is set).
   - After a successful file save (wherever `dungeon.meta.save_name` is assigned).

**New tests (`test_design_view.py`):**

- `test_test_drive_click_calls_launch_test_drive` — inspector returns `hit_test_drive=True`; only `launch_test_drive` is called.
- `test_start_play_click_calls_launch_play_session` — inspector returns `hit_start_play=True`; only `launch_play_session` is called.
- `test_start_play_click_does_not_call_test_drive` — the two handlers are exclusive.
- `test_refresh_play_button_state_on_load` — `set_saved_state` is called when `load_dungeon` fires.

---

### Step 5 — Wire `launch_test_drive` → `load_dungeon_transient`

After Step 1 renames `load_dungeon` → `load_dungeon_transient`, update `window.py`:
```python
def launch_test_drive(self, dungeon: object) -> None:
    self._play_view.load_dungeon_transient(dungeon)
    self.switch_to_play()
```

This is a one-line rename. All existing smoke tests that exercise Test Drive continue to pass.

---

### Implementation Order Summary

```
Step 1a  test_play_view.py  —  write failing tests for transient/session split
Step 1b  play_view.py       —  implement load_dungeon_transient / load_dungeon_session / _save_session
Step 2a  test_window.py     —  write failing test for launch_play_session
Step 2b  window.py          —  add launch_play_session; update launch_test_drive call
Step 3a  test_inspector_panel.py  —  write failing tests for button state
Step 3b  inspector_panel.py —  add set_saved_state, update draw/hit_start_play
Step 4a  test_design_view.py —  write failing tests for routing split
Step 4b  design_view.py     —  fix routing, add _launch_start_play, add _refresh_play_button_state
```

Each lettered step is: write test → run (red) → write code → run (green) → commit.

---

### Out-of-scope for this feature

- Full chat-transcript restore on Continue Play (the `play_transcript` field in `SessionState` exists but replaying messages into `ChatPanel` is deferred).
- "Reset Session" UI (clear saved session).
- Multiple sessions per dungeon.

---

## Open Questions / Out of Scope

- **Session reset**: No UI to clear a session is specified here. A future feature could add "Reset Session" to the Play Mode menu.
- **Multiple sessions**: Only one session per dungeon is supported (the single `session.json`).
- **Dungeon save prompt**: If the GM clicks "Start Play →" while unsaved, a tooltip or disabled state is sufficient — no auto-save prompt is required in this feature.
