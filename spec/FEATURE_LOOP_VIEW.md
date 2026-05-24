# Feature Spec — Play Mode Loop Guidance (Phase 17)

## Overview

Loops are designed in Design Mode but invisible to the GM during play. The loop overlay
code and `active_loop_id` field already exist, but there is no mechanism to activate a
loop from Play Mode, and the DM Agent has no loop awareness.

This phase adds three focused features to close that gap.

---

## F-27 · Loop Toggle Strip

**Description:** A row of pill buttons in the bottom-right of the map canvas, one per loop
on the current level. Clicking a pill activates that loop — setting `active_loop_id` —
which triggers the LoopOverlay to draw Path A (teal) and Path B (violet) on the map.
Clicking the active pill deactivates it. Only one loop can be active at a time.

**Where:** Bottom-right overlay within the map canvas, visible only when `level.loops` is
non-empty.

**Acceptance criteria:**

- Strip is not drawn when the current level has no loops
- Strip renders one pill per loop in `level.loops`
- Each pill displays the loop's pattern name (e.g. `lock_key`) and a `MAIN`/`SUB` chip
- Clicking an inactive pill sets `active_loop_id` to that loop's `id` and highlights the pill
- Clicking the active pill sets `active_loop_id` to `None` (deactivates overlay)
- Activating a new pill while another is active deactivates the previous one first
- On level change, the strip resets — no pill is active

**Callback:** `MapPanel` exposes `on_activate_loop: Callable[[str | None], None]`.
`PlayView` wires this to update `self._session.active_loop_id` and post the system message
(F-28). `MapPanel` does not own session state directly.

**Tests to write first:** `tests/unit/ui/panels/test_map_panel_loop_strip.py`

```
test_strip_hidden_when_no_loops
test_strip_shows_one_pill_per_loop
test_clicking_pill_calls_on_activate_loop_with_id
test_clicking_active_pill_calls_on_activate_loop_with_none
test_activating_second_loop_replaces_first
```

---

## F-28 · Loop Activation System Message

**Description:** When the GM activates a loop via the toggle strip, a system bubble appears
in the play chat summarising the loop so the GM has an in-play reference without switching
to Design Mode.

**Acceptance criteria:**

- Activating a loop posts a system message to the play chat containing:
  - Loop pattern name (human-readable from catalog, e.g. "Lock & Key")
  - Loop `explanation` text
  - Entry room name → Goal room name (resolved from room IDs to room names)
  - Path A as a `→`-joined sequence of room names
  - Path B as a `→`-joined sequence of room names
- Deactivating a loop posts a short system message: `"Loop overlay cleared."`
- Room IDs in `path_a` / `path_b` are resolved to room names via the current level
- If a room ID does not resolve (corrupt data), the ID is shown as-is (no crash)
- No LLM call is made — this is a synchronous system message only

**Message format:**

```
── lock_key · Lock & Key ──
The party must find the key to unlock the goal room.
Entry: Receiving Hall  ·  Goal: Elevator Shaft
Path A: Receiving Hall → Marketplace → Elevator Shaft
Path B: Receiving Hall → Cargo Bay → Marketplace → Elevator Shaft
```

**Tests to write first:** `tests/unit/views/test_play_view_loop_activation.py`

```
test_activate_loop_posts_system_message
test_system_message_contains_explanation
test_system_message_contains_entry_and_goal_names
test_system_message_contains_path_a_as_room_names
test_system_message_contains_path_b_as_room_names
test_deactivate_loop_posts_cleared_message
test_unknown_room_id_shown_as_id
```

---

## F-29 · DM Agent Loop Context

**Description:** `DungeonMasterAgent.respond()` accepts an optional `active_loop` parameter.
When set, `_build_context` appends an `# Active Loop` section to the system prompt so the
DM can narrate with awareness of the loop structure — which paths the current room sits on,
where the entry and goal are, and what the overall pattern means.

**Signature change:**

```python
def respond(
    self,
    history: list[LLMMessage],
    room: object,
    level: object,
    dungeon: object,
    room_memory: str = "",
    level_id: int | None = None,
    active_loop: object | None = None,   # NEW — Loop | None
) -> str:
```

**Context section appended when `active_loop` is not None:**

```
# Active Loop
Pattern: Lock & Key
Explanation: The party must find the key to unlock the goal room.
Entry: Receiving Hall  |  Goal: Elevator Shaft
Current room appears on: Path A, Path B      ← or "not on either path"
Path A: Receiving Hall → Marketplace → Elevator Shaft
Path B: Receiving Hall → Cargo Bay → Marketplace → Elevator Shaft
```

**Acceptance criteria:**

- When `active_loop=None`, no `# Active Loop` section is added (no regression)
- When `active_loop` is set, the section is appended after the dungeon block
- `Current room appears on` correctly lists A, B, both, or neither
- Room IDs in path lists are resolved to room names via `level.rooms`
- `PlayView` passes `self._session.active_loop_id` resolved to the `Loop` object when
  calling `dm_agent.respond()` for both room-entry narration and GM chat turns
- Existing tests pass unchanged (default `active_loop=None`)

**Tests to write first:** `tests/unit/agents/test_dm_agent_loop.py`

```
test_respond_without_loop_omits_loop_section
test_respond_with_loop_includes_loop_section
test_loop_context_includes_pattern_and_explanation
test_loop_context_includes_entry_and_goal
test_current_room_on_path_a_only
test_current_room_on_path_b_only
test_current_room_on_both_paths
test_current_room_on_neither_path
test_path_rooms_resolved_to_names
```

---

## Implementation Order

1. **F-29 first** — pure logic, no UI, easiest to unit-test in isolation
2. **F-27** — strip UI in `MapPanel`; wired via callback
3. **F-28** — system message posted in `PlayView.on_activate_loop()`

All three are independent enough to be written in one session with TDD.

---

## What Is NOT in Scope

- Showing multiple loop overlays simultaneously
- Editing loops from Play Mode
- Loop progress tracking (marking rooms as visited per-path)
- Any changes to Design Mode loop editor
- New library dependencies
