# Dungeon Daddy — Graph Mode Phase 3: Interaction Polish + Phase 2.5 Cleanup

**Status: Complete** — 1280 tests passing. Closed 2026-05-31.

All 14 implementation steps done. Artifacts under `artifacts/layout/phase3/`.
See `spec/IMPLEMENTATION_PHASES.md` Phase 22 for full step-by-step record.

---

## Purpose

Phase 1 made Graph Mode geometrically reliable.

Phase 2 made Graph Mode semantically readable.

Phase 2.5 added explicit authored metadata so Graph Mode no longer depends primarily on name-based inference.

**Phase 3 should make Graph Mode feel interactive, useful, and game-like.**

The goal is not to turn Graph Mode into a tile map. Grid Mode remains untouched as the old-style baseline. Graph Mode should continue to serve as the readable dungeon overview, but now the player should be able to explore the map through selection, hover, focus, highlighting, and contextual details.

---

## Current State

Graph Mode already has:

- clean geometric layout
- orthogonal routed connections
- connection label placement
- camera fitting
- semantic room roles
- room role styling
- critical path emphasis
- endpoint emphasis
- metadata validation
- explicit floor-level layout metadata
- explicit room-level layout metadata
- metadata migration support for:
  - `The Crucible`
  - `Tomb of the Forgotten King`
- generated feedback reports and screenshots

Grid Mode has intentionally remained unchanged so it can continue to serve as a comparison baseline.

---

## Phase 3 Goals

Phase 3 should add interaction polish to Graph Mode while preserving all Phase 1, Phase 2, and Phase 2.5 guarantees.

The user should be able to:

1. Hover over a room and immediately understand that it is interactive.
2. Select a room and see that room become the visual focus.
3. See connected rooms and paths highlighted when a room is selected.
4. See unrelated rooms and connections fade slightly when focus is active.
5. Open a lightweight room detail panel/card from Graph Mode.
6. Inspect connection information when hovering or selecting a connection.
7. Quickly reset/recenter the map view.
8. Visually distinguish normal map state, hover state, selected state, and focused path state.

The result should feel more like a game UI and less like a static generated diagram.

---

## Non-Goals

Do **not** do the following in Phase 3:

- Do not modify Grid Mode.
- Do not replace Graph Mode with tile rendering.
- Do not remove the existing semantic styling system.
- Do not change the dungeon JSON format in a breaking way.
- Do not require new metadata fields for existing dungeons to load.
- Do not introduce animation-heavy or shader-heavy behavior unless it is optional and well isolated.
- Do not make Graph Mode dependent on live Arcade/OpenGL behavior for generated artifact tests.
- Do not rewrite the Phase 1 routing engine.
- Do not alter the local dungeon files outside the existing target dungeons unless explicitly requested.

---

## Visual Rendering Gaps vs Phase 2.5 Artifact

The Phase 2.5 artifact screenshots (`artifacts/layout/phase2_5/crucible_l1_graph.png` etc.)
show a richer visual appearance than the current live `LayoutRenderer`. Three concrete gaps
were identified by comparing the artifact to the live Graph Mode:

### Gap 1 — Role-based border color

**Artifact:** each role has a distinct border color: teal for `entrance`, blue for `hub`,
orange for `hazard`.

**Live:** `LayoutRenderer` always uses the fixed constant `_ROOM_BORDER = (100, 120, 140)`.
`GraphRoomStyle` has no `border_color` field so color variation is impossible.

**Fix required:**
- Add `border_color: tuple[int, int, int]` to `GraphRoomStyle`.
- Populate it per-role in `_STYLES` in `room_style.py`.
- In `LayoutRenderer._draw_rooms`, use `(*style.border_color, style.border_alpha)` instead
  of `(*_ROOM_BORDER, style.border_alpha)`.

---

### Gap 2 — Role-based fill color

**Artifact:** role-specific fill colors are applied (e.g. dark brownish-red fill for `hazard`
R5 Trap Room).

**Live:** `LayoutRenderer` always uses the fixed constant `_ROOM_FILL = (30, 35, 45)`.
`GraphRoomStyle` has no `fill_color` field.

**Fix required:**
- Add `fill_color: tuple[int, int, int]` to `GraphRoomStyle`.
- Populate it per-role in `_STYLES` in `room_style.py`.
- In `LayoutRenderer._draw_rooms`, use `(*style.fill_color, style.fill_alpha)` instead of
  `(*_ROOM_FILL, style.fill_alpha)`.

---

### Gap 3 — Marker text position

**Artifact:** role badge text ("IN", "↓", "!") is rendered at the **top** of the room box,
above the room name.

**Live:** marker text is drawn at `wy + wh * 0.15` — near the **bottom** of the room box,
below the room name.

**Fix required:**
- Change the marker draw call in `LayoutRenderer._draw_rooms` to position the text near the
  top inside edge of the room (e.g. `wy + wh * 0.82` with `anchor_y="center"`, or
  `wy + wh - small_padding` with `anchor_y="top"`).

---

These three gaps should be addressed together as a single step before the interaction
styling pipeline (Step 5), since the interaction style resolution order builds on top of
the base role style.

---

## Required Phase 2.5 Cleanup Included in Phase 3

Two small Phase 2.5 follow-up items should be included in this phase.

### 1. Refine objective warning naming

Current behavior can report `MISSING_OBJECTIVE_ROLE` on floors whose endpoint is a valid `descent` or `transition` room.

This is technically acceptable, but the warning language is misleading.

Update the warning logic so it distinguishes between:

- no valid endpoint at all
- valid endpoint exists but no quest/combat/objective room exists
- endpoint is a transition/descent rather than an objective

Recommended warning categories:

```text
MISSING_ENDPOINT_ROLE
NO_QUEST_OBJECTIVE_ROLE
ENDPOINT_IS_TRANSITION_ONLY
```

Expected behavior:

- If a floor has an explicit valid endpoint such as `descent`, `transition`, `elevator`, `stairs`, or `exit`, it should **not** warn that the destination is ambiguous.
- If a floor has no `boss`, `objective`, or `key_room`, it may warn with `NO_QUEST_OBJECTIVE_ROLE`, but this should be lower severity than missing endpoint.
- For floors intentionally ending in travel, `ENDPOINT_IS_TRANSITION_ONLY` should be informational or low severity.

This is a scoring/reporting cleanup, not a visual layout change.

### 2. Add optional explicit connection metadata for target fixtures/maps

Phase 2.5 added connection style override machinery but did not backfill explicit connection metadata.

Phase 3 should add connection-level metadata for the existing target fixtures and local dungeon files where useful.

Target files:

- `tests/fixtures/crucible.json`
- `tests/fixtures/tomb.json`
- `C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons\The Crucible\dungeon.json`
- `C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons\Tomb of the Forgotten King\dungeon.json`

Recommended optional fields on connection objects:

```json
{
  "connection_style": "normal",
  "layout_connection_role": "critical_path",
  "graph_notes": "Main path from entry to hub."
}
```

Use connection metadata only where it helps. Avoid noisy metadata for every connection if the label-based inference is already sufficient.

Useful roles/styles:

```text
normal
critical_path
optional_branch
secret
locked
vertical
hazard
transition
shortcut
```

Connection style resolution order should remain:

1. explicit `connection_style`
2. explicit `layout_connection_role`
3. label alias
4. default `normal`

---

## Interaction Requirements

### 1. Hover behavior for rooms

When the mouse is over a room in Graph Mode:

- the room border should brighten or thicken slightly
- the room fill may brighten subtly
- the cursor should indicate interactivity if supported
- the room label should remain readable
- no layout should move
- no permanent selection should occur until click

Hover behavior should be visually clear but not distracting.

#### Acceptance Criteria

- Hovering a room changes its visual state.
- Moving off the room restores the default state unless the room is selected.
- Hover state stacks cleanly with semantic role styling.
- Hovering one room does not cause unrelated map elements to jump, resize unexpectedly, or re-layout.

---

### 2. Room selection behavior

Clicking a room in Graph Mode should select it.

When a room is selected:

- the selected room receives a stronger border or glow-like outline
- directly connected rooms are visually highlighted
- connections from the selected room are highlighted
- unrelated rooms and connections fade slightly but remain visible
- selected state persists until another room is selected or selection is cleared

Selection should work independently from hover.

#### Acceptance Criteria

- Clicking a room selects it.
- Clicking another room changes selection.
- Clicking empty map space clears selection, unless the existing UI convention uses a different clear action.
- Selected room remains visibly selected even when the mouse moves away.
- Selected room styling does not erase role styling.
- Connected-room highlight is visible but less dominant than selected-room highlight.

---

### 3. Connection hover and selection

Connections should become inspectable.

When hovering over a connection path:

- the connection should brighten or thicken subtly
- its label should become more readable if currently faint
- optional tooltip/detail text may appear

Clicking a connection may select it or open connection details. If implementing full connection selection is too much for Phase 3, hover-only is acceptable, but this must be documented in the implementation summary.

Connection hit testing should use a tolerance radius around line segments, not exact pixel matching.

#### Acceptance Criteria

- The user can hover near a connection and receive visual feedback.
- Connection hover detection works on horizontal and vertical segments.
- Connection hover does not interfere with room hover when the pointer is clearly inside a room.
- Connection labels remain readable.
- Explicit connection metadata appears in detail output if present.

---

### 4. Room detail card / panel

Selecting a room should expose more information than the room label.

Implement one of the following:

- a small floating detail card near the selected room
- a fixed side panel within the Graph Mode UI
- a bottom information panel

Prefer a fixed panel if it is simpler and less likely to overlap map content.

The detail panel should include, where available:

- room name
- room ID
- room role / layout role
- visual priority
- whether it is on the critical path
- whether it is an optional branch
- short description or summary if available
- graph notes if available
- connected rooms
- connection labels/styles to adjacent rooms

Do not overload the panel. It should be concise.

#### Example Panel Content

```text
Receiving Hall
ID: R1
Role: Entrance
Priority: Medium
Critical Path: Yes

Connections:
- Marketplace — arch — critical path
- Cargo Bay — door — optional branch

Notes:
Primary entry point for Crucible Level 1.
```

#### Acceptance Criteria

- Selecting a room shows detail information.
- Detail panel updates when another room is selected.
- Detail panel clears or collapses when selection is cleared.
- Detail panel uses explicit metadata when present.
- Detail panel falls back gracefully when metadata is missing.

---

### 5. Focus mode behavior

When a room is selected, Graph Mode should enter a mild focus mode.

In focus mode:

- selected room is highest priority
- directly connected rooms are second priority
- selected room connections are highlighted
- unrelated rooms and connections fade to a lower alpha
- critical path may remain somewhat visible even if unrelated

The fade should be subtle. The player should still understand the whole floor.

#### Acceptance Criteria

- Focus mode makes the selected room and its neighborhood easier to understand.
- Unrelated elements remain visible enough to preserve context.
- Critical path does not disappear completely.
- Focus mode can be cleared.

---

### 6. Path highlight behavior

Add a way to visually highlight the critical path more clearly on demand.

Options:

- always-on subtle critical path emphasis, already present from Phase 2
- toggleable stronger critical path highlight
- automatic stronger critical path highlight when selecting an entrance, endpoint, objective, or boss room

Minimum requirement:

- Keep current subtle critical path emphasis.
- Add a stronger state when the selected room is on the critical path.

#### Acceptance Criteria

- Critical path is still visually distinguishable after Phase 3.
- Selecting a critical-path room makes the critical path easier to follow.
- Optional branches remain visible but secondary.

---

### 7. Recenter / reset view action

Add or wire a Graph Mode action to reset the camera/view to the fitted floor bounds.

This may be:

- a keyboard shortcut
- a UI button
- reuse of an existing navigation control

Suggested keyboard shortcut:

```text
R = recenter/reset Graph Mode view
Escape = clear selection / close detail panel
```

Do not break existing pan/zoom behavior.

#### Acceptance Criteria

- User can recenter the Graph Mode map after panning.
- User can clear selected room and return to normal overview state.
- Camera fit still contains all rooms, routes, and labels.

---

### 8. Keyboard and accessibility-friendly controls

If feasible, add basic keyboard navigation between rooms.

Minimum viable option:

- Escape clears selection.
- R recenters.

Nice-to-have:

- Tab cycles rooms.
- Enter opens/selects focused room.
- Arrow keys move selection across connected rooms where graph direction is clear.

Do not overbuild keyboard navigation in Phase 3. Keep it safe and testable.

---

## Rendering and Architecture Requirements

### 1. Maintain Graph Mode isolation

All Phase 3 behavior should be scoped to Graph Mode.

Grid Mode must not change.

Do not add interaction behavior to Grid Mode unless explicitly required by shared UI infrastructure, and if unavoidable, document it clearly.

### 2. Separate interaction state from layout state

Do not store hover/selection state inside static layout results.

Recommended separation:

```text
LayoutResult      = stable geometry + semantic data
GraphViewState    = camera, selected room, hovered room, hovered connection
GraphRenderStyle  = computed visual state from semantic style + interaction state
```

Interaction should not mutate dungeon data.

### 3. Preserve deterministic layout artifacts

Generated test screenshots should be deterministic.

If hover/selection screenshots are generated, the selected room and hovered room should be specified explicitly by fixture config or artifact generation command.

### 4. Hit testing

Implement hit testing using stable layout geometry.

Room hit test:

- point within room rectangle

Connection hit test:

- point within tolerance distance of any segment
- tolerance should be configurable
- room hit test should win over connection hit test when both match

### 5. Styling priority order

Final visual styling should be resolved in a predictable order.

Recommended order:

1. base graph style
2. semantic role style
3. critical path style
4. focus/fade state
5. hover state
6. selected state

Selected state should always be visually dominant.

---

## Data and Metadata Requirements

### 1. Preserve existing metadata

Do not remove Phase 2.5 metadata.

Do not rename existing fields unless there is a migration and compatibility layer.

### 2. Add connection metadata where useful

Backfill explicit connection metadata only for:

- test fixtures for The Crucible and Tomb
- local dungeon files for The Crucible and Tomb

Do not patch unrelated dungeons.

### 3. Backups for local dungeon writes

Before modifying local dungeon files under:

```text
C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons
```

create timestamped backups, as done in Phase 2.5.

---

## Required Test Guidance

### Unit Tests

Add or update unit tests for:

1. Room hit testing
   - point inside room
   - point outside room
   - boundary behavior

2. Connection hit testing
   - horizontal segment
   - vertical segment
   - multi-segment orthogonal route
   - tolerance behavior
   - room hit priority over connection hit

3. Graph interaction state
   - hover room set/clear
   - select room set/replace/clear
   - hover connection set/clear
   - Escape clears selection
   - recenter action invokes camera fit/reset behavior

4. Style resolution
   - selected room overrides hover
   - hover does not override selected
   - focus fade applies to unrelated rooms
   - connected rooms are highlighted
   - critical path remains visible in focus mode

5. Detail panel data assembly
   - room metadata appears
   - connected rooms appear
   - connection labels/styles appear
   - missing metadata falls back gracefully

6. Phase 2.5 cleanup
   - `descent` endpoint does not incorrectly raise ambiguous destination warning
   - `transition` endpoint does not incorrectly raise ambiguous destination warning
   - no objective room produces lower-severity `NO_QUEST_OBJECTIVE_ROLE` or equivalent
   - explicit connection style overrides label alias

### Integration Tests

Add or update integration tests for the layout pipeline and Graph Mode renderer using these fixtures:

- `crucible_l1`
- `crucible_l2`
- `crucible_l3`
- `tomb_l1`

Each integration test should verify:

- geometry score remains 100.0
- no overlaps
- no illegal crossings
- no offscreen geometry
- semantic score does not regress from Phase 2.5 baseline
- metadata score does not regress from Phase 2.5 baseline
- interactive states can be rendered without exceptions
- detail panel data can be produced for selected room

Recommended minimum semantic baselines:

```text
crucible_l1 >= 78.0
crucible_l2 >= 82.2
crucible_l3 >= 82.8
tomb_l1 >= 81.0
```

Recommended metadata baseline:

```text
all fixtures >= 85.0
```

### UI / Screenshot Tests

If live Arcade UI tests are available, run them. If headless testing is required, generate deterministic PIL screenshots as in Phase 2 and Phase 2.5.

For each target fixture, generate at least these screenshots:

1. default Graph Mode state
2. selected entrance room
3. selected hub or central room, if present
4. selected endpoint room
5. selected hazard or boss room, if present
6. connection hover sample, if supported by screenshot renderer

For example:

```text
artifacts/layout/phase3/crucible_l1_default.png
artifacts/layout/phase3/crucible_l1_select_R1.png
artifacts/layout/phase3/crucible_l1_select_R2.png
artifacts/layout/phase3/crucible_l1_select_R4.png
artifacts/layout/phase3/crucible_l1_select_R5.png
```

---

## Required Output Artifacts

Claude Code must produce the following artifacts for review.

### 1. Implementation summary

Create:

```text
artifacts/layout/phase3/implementation_summary.md
```

Include:

- files changed
- new modules added
- interaction behavior implemented
- keyboard controls implemented
- detail panel behavior implemented
- Phase 2.5 cleanup performed
- Grid Mode confirmation
- test results
- known limitations

### 2. Interaction feedback JSON per fixture

Create one JSON report per fixture:

```text
artifacts/layout/phase3/crucible_l1.interaction_feedback.json
artifacts/layout/phase3/crucible_l2.interaction_feedback.json
artifacts/layout/phase3/crucible_l3.interaction_feedback.json
artifacts/layout/phase3/tomb_l1.interaction_feedback.json
```

Each report should include:

```json
{
  "fixture_name": "crucible_l1",
  "geometry_score": 100.0,
  "semantic_score": 78.0,
  "metadata_score": 85.0,
  "interaction_score": 0.0,
  "default_state": {
    "renders_without_error": true,
    "selected_room_id": null,
    "hovered_room_id": null,
    "hovered_connection_id": null
  },
  "selection_tests": [
    {
      "selected_room_id": "R1",
      "selected_room_role": "entrance",
      "detail_panel_available": true,
      "connected_room_ids": ["R2", "R3"],
      "highlighted_connection_ids": ["R1→R2", "R1→R3"],
      "unrelated_rooms_faded": true,
      "critical_path_visible": true,
      "warnings": []
    }
  ],
  "hover_tests": [
    {
      "hovered_room_id": "R1",
      "hover_visual_applied": true,
      "warnings": []
    }
  ],
  "connection_hover_tests": [
    {
      "connection_id": "R1→R2",
      "hover_visual_applied": true,
      "label_visible": true,
      "warnings": []
    }
  ],
  "detail_panel_tests": [
    {
      "room_id": "R1",
      "contains_name": true,
      "contains_role": true,
      "contains_connected_rooms": true,
      "contains_graph_notes": true,
      "warnings": []
    }
  ],
  "warnings": []
}
```

### 3. Phase 3 summary report

Create:

```text
artifacts/layout/phase3/phase3_feedback_summary.md
```

Include a table with:

```text
Fixture
Geometry Score
Semantic Score
Metadata Score
Interaction Score
Default Screenshot
Selection Screenshots Generated
Warnings
Status
```

Also include a human review checklist with Phase 3-specific questions:

- Does selected-room focus make the map easier to understand?
- Are connected rooms obvious without overwhelming the map?
- Are unrelated rooms faded enough but still readable?
- Is the detail panel useful and not too noisy?
- Are room hover states clear?
- Are connection hover states clear?
- Is the critical path easier to follow after selecting a critical room?
- Does the map still feel clean compared to Grid Mode?
- Did interaction polish make the map feel more game-like?

### 4. Screenshot artifacts

Create screenshot artifacts under:

```text
artifacts/layout/phase3/
```

Minimum set:

```text
crucible_l1_default.png
crucible_l1_select_R1.png
crucible_l1_select_R2.png
crucible_l1_select_R4.png
crucible_l1_select_R5.png

crucible_l2_default.png
crucible_l2_select_r01.png
crucible_l2_select_r02.png
crucible_l2_select_r03.png
crucible_l2_select_r05.png
crucible_l2_select_r06.png

crucible_l3_default.png
crucible_l3_select_r1.png
crucible_l3_select_r3.png
crucible_l3_select_r7.png
crucible_l3_select_r8.png

tomb_l1_default.png
tomb_l1_select_1-A.png
tomb_l1_select_1-B.png
tomb_l1_select_1-C.png
tomb_l1_select_1-E.png
```

If connection hover screenshots are supported, also produce:

```text
crucible_l1_hover_connection_R1_R2.png
crucible_l2_hover_connection_r05_r06.png
crucible_l3_hover_connection_r7_r8.png
tomb_l1_hover_connection_1-C_1-E.png
```

### 5. Before/after comparison

Create:

```text
artifacts/layout/phase3/before_after_summary.md
```

Compare Phase 2.5 to Phase 3.

Include:

- geometry score delta
- semantic score delta
- metadata score delta
- new interaction score
- warning changes
- screenshots generated
- known visual regressions, if any

### 6. Metadata migration report, if connection metadata is written

If local dungeon connection metadata is updated, create:

```text
artifacts/layout/phase3/connection_metadata_migration_report.md
```

Include:

- fixture files changed
- local files changed
- backups created
- connections patched
- skipped files
- dry-run command output summary
- write command output summary

---

## Suggested Interaction Score

Add an `interaction_score` from 0 to 100.

Suggested scoring:

```text
+20 room hover works
+20 room selection works
+15 connected rooms/edges highlight
+15 unrelated map elements fade in focus mode
+15 detail panel/card works
+10 recenter/clear controls work
+5 connection hover works
```

If connection hover is not implemented in Phase 3, cap the score at 95 and document this limitation.

---

## Commands to Run

Run the full test suite:

```bash
python -m pytest
```

Run type checking if used by the project:

```bash
mypy .
```

Run artifact generation commands. If a script exists, extend it; otherwise create one.

Suggested command shape:

```bash
python scripts/generate_phase3_graph_artifacts.py --output artifacts/layout/phase3
```

If local dungeon files are patched with connection metadata, run dry-run first:

```bash
python scripts/backfill_graph_metadata.py --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" --dungeons "The Crucible" "Tomb of the Forgotten King" --dry-run
```

Then write only after dry-run looks correct:

```bash
python scripts/backfill_graph_metadata.py --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" --dungeons "The Crucible" "Tomb of the Forgotten King" --write
```

---

## Success Criteria

Phase 3 is successful if:

1. Grid Mode remains untouched.
2. Graph Mode still passes all Phase 1 geometry invariants.
3. Phase 2.5 semantic and metadata scores do not regress.
4. Room hover works.
5. Room selection works.
6. Focus mode makes selected-room relationships easier to understand.
7. Detail panel/card is useful and concise.
8. Recenter/clear selection controls work.
9. Required artifacts are generated.
10. The resulting screenshots feel more like a game UI than Phase 2.5.

---

## Human Review Guidance

After implementation, review the generated screenshots and reports.

For each fixture, answer:

1. Is the default map still clean?
2. Does selecting the entrance help explain where the floor starts?
3. Does selecting the hub/objective/boss clarify the floor structure?
4. Do connected rooms and connections pop visually?
5. Do unrelated rooms fade without disappearing?
6. Is the detail panel actually useful during play?
7. Does the map feel more interactive and game-like?
8. Did any new styling make the map too noisy?
9. Does Graph Mode remain preferable to Grid Mode for overview reading?

---

## Notes for Claude Code

Be incremental.

Do not rewrite working layout code.

Preserve the clean schematic quality achieved in Phases 1–2.5. Phase 3 should add interactivity and usability, not clutter.

When in doubt, prefer subtle interaction states over flashy ones.

The user is happy with Graph Mode’s direction. Protect what already works.
