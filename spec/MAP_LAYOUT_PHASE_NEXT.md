# Dungeon Daddy Map Layout Improvement Phase

> **Status: COMPLETE** — All steps done (2026-05-30). 332 unit tests passing. mypy zero errors.

## Phase Title

**Vector Map Layout Phase 1: Semantic Placement, Orthogonal Routing, Labels, and Camera Framing**

## Purpose

Dungeon Daddy currently renders dungeon maps as geometric room shapes connected by lines. This is the correct direction for the project. Do **not** migrate to tile-based maps for this phase.

The current maps are readable in small cases, but they still feel like generic node diagrams rather than intentionally composed dungeon maps. The next improvement phase should focus on making the vector map renderer understand dungeon structure, room roles, connection semantics, and camera framing.

The goal is not to create a perfect graph drawing engine. The goal is to make Dungeon Daddy maps feel visually authored, stable, readable, and aligned with the game's existing JSON dungeon structure.

---

## Core Decision

Remain with the current **vector / geometric shape map approach**:

- rectangular or shaped room bodies
- line or polyline connections
- text labels
- pan and zoom camera
- semantic map tags
- JSON graph as source of truth

Do **not** convert the dungeon viewer to a traditional tile map unless a later gameplay mode requires room-scale movement, collision, tactical combat, or tile-authored interiors.

For the current Dungeon Viewer, tiles would introduce unnecessary quantization and complexity. The maps are meant to communicate structure, progression, relationships, and dungeon logic. Vector graph rendering is the better fit.

---

## Current Problems Observed

The existing maps show several recurring issues:

1. **Rooms are placed as generic graph nodes rather than dungeon components.**
   - Entrances do not always feel like starts.
   - Boss rooms and destination rooms do not always feel like endpoints.
   - Hub rooms are not always visually dominant or centered.

2. **Connections avoid some collisions but do not yet feel intentionally routed.**
   - Some lines are diagonal when orthogonal routes would be clearer.
   - Some routes create awkward large detours.
   - Some connections visually graze or crowd nearby rooms.

3. **Connection labels are placed too casually.**
   - Labels sometimes float awkwardly.
   - Labels can land near room borders or screen edges.
   - Labels are not yet treated as collision-aware objects.

4. **Camera framing is fragile.**
   - Some maps start partially offscreen.
   - Large rooms or distant endpoints can break initial composition.
   - UI/HUD space and world map space are not fully separated.

5. **Semantic map tags are underused.**
   - Tags such as `hub_spoke`, `lock_key`, `secret_shortcut`, `pursuit`, `gambit`, or similar should influence layout decisions.
   - These tags should become part of the layout grammar.

---

## High-Level Architecture

Implement the map renderer as a derived layout pipeline.

The JSON dungeon graph remains the source of truth. The renderer should produce derived layout data from that graph.

```text
Dungeon JSON
   ↓
Semantic analysis
   ↓
Room role classification
   ↓
Template / grammar selection
   ↓
Room placement
   ↓
Port generation
   ↓
Obstacle-aware edge routing
   ↓
Label placement
   ↓
Camera bounds and render cache
   ↓
Arcade rendering
```

The renderer must not mutate the authored dungeon graph. It may cache derived layout output.

---

## Recommended Module Structure

Create or refactor toward the following module structure:

```text
dungeon_layout/
  models.py
  semantics.py
  seed_layout.py
  refine_layout.py
  ports.py
  route_orthogonal.py
  labels.py
  camera_fit.py
  render_cache.py
  validation.py

tests/
  fixtures/
    the_crucible_l1.json
    the_crucible_l2.json
    the_crucible_l3.json
    tomb_l2_hall_of_bound_servants.json
    tomb_l3_kings_tomb.json
  test_layout_invariants.py
  test_routing.py
  test_labels.py
  test_camera_fit.py
```

If the existing project structure differs, adapt the names while preserving this separation of responsibilities.

---

## Phase Scope

This phase should implement a focused vertical slice, not a full rewrite.

### In Scope

- Semantic room role detection.
- Layout template selection.
- Critical-path-first room placement.
- Port generation for rooms.
- Obstacle-aware orthogonal routing.
- Greedy connection label placement.
- Camera auto-fit based on final layout bounds.
- Layout validation tests.
- Debug overlay support.

### Out of Scope

- Tile map conversion.
- Full procedural room interior generation.
- Tactical combat grid support.
- Complex third-party layout engine integration as the primary solution.
- Perfect global graph optimization.
- Animated corridor routing.
- Artistic room illustrations.

---

## Room Role Classification

Each room should have a layout role. The role may come from explicit JSON metadata or be inferred from room tags, names, connections, or floor structure.

Recommended roles:

```text
entrance
exit
hub
boss
objective
key_room
lock_room
treasure
hazard
secret
utility
corridor
side_room
transition
unknown
```

### Role Rules

Use explicit metadata first.

Example:

```json
{
  "id": "r7",
  "name": "Prime Golem Lair",
  "layout_role": "boss"
}
```

If explicit metadata is missing, infer from available data.

Suggested inference rules:

- A room with `entrance`, `entry`, `stair`, `landing`, or `arrival` in its name or tags may be `entrance` or `transition`.
- A room with `boss`, `lair`, `throne`, `core`, or `final` in its name or tags may be `boss` or `objective`.
- A room with high graph degree may be `hub`.
- A room connected by a secret connection may be `secret` or part of a `secret_shortcut` route.
- A room with `key`, `control`, `lever`, or `mechanism` may be `key_room`.
- A room with `locked`, `gate`, `sealed`, or `descent` may be `lock_room` or `exit`.

Do not overfit name inference. Explicit JSON metadata must win.

---

## Layout Template Selection

The layout engine should select a map grammar before placing rooms.

Supported templates for this phase:

```text
linear
hub_spoke
branch_merge
lock_key
boss_endcap
loop
freeform
```

### Template Selection Rules

Use explicit floor tags first.

Example:

```json
{
  "floor_tags": ["hub_spoke", "pursuit"]
}
```

If no explicit tag exists, infer from graph shape:

- `hub_spoke`: one room has much higher degree than others.
- `branch_merge`: paths split from a source and rejoin near a destination.
- `linear`: most rooms have degree 1 or 2 and there is a clear start/end chain.
- `lock_key`: floor has key/control room and locked/objective room.
- `boss_endcap`: boss/objective room is near the end of the main path.
- `loop`: graph contains a meaningful cycle.
- `freeform`: fallback when no strong structure is detected.

---

## Critical Path First Placement

The renderer should place the critical path first, then attach branches.

### Critical Path Definition

The critical path is the main route through the floor.

Preferred source order:

1. Explicit designer-provided path metadata.
2. Path from entrance to boss/objective/exit.
3. Longest meaningful path through the graph.
4. Fallback to BFS/DFS ordering from entrance or highest-priority room.

### Placement Principles

- Entry rooms should anchor the start of the composition.
- Boss/objective/exit rooms should anchor the end of the composition.
- Hub rooms should be central in hub-spoke layouts.
- Key rooms should appear before lock rooms in lock-key layouts.
- Branches should attach cleanly to the critical path.
- Optional rooms should not visually dominate the main path.
- Secret shortcuts should not distort the primary map composition.

---

## Template Placement Rules

### Linear

Use a left-to-right or top-to-bottom progression.

```text
Entry → Room → Room → Objective/Exit
```

Requirements:

- Maintain consistent spacing.
- Keep the main route visually monotonic.
- Avoid unnecessary vertical oscillation.

### Hub-Spoke

Place the hub near the center.

```text
        Room
          |
Room — Hub — Room
          |
        Room
```

Requirements:

- Highest-degree hub room should be centered.
- Spokes should be distributed around the hub.
- Important spokes may be placed to the right or top depending on progression direction.
- Secret or optional spokes should be visually secondary.

### Branch-Merge

Use a clear split and reconvergence shape.

```text
          Branch A
         /        \
Entry —            — Merge → Objective
         \        /
          Branch B
```

Requirements:

- Branches must be visually separated.
- Merge room must be clear.
- The endpoint must read as the destination.

### Lock-Key

Show key/control logic clearly.

```text
Entry → Hub/Path → Gate/Lock → Objective
          |
       Key Room
```

Requirements:

- Key/control room should visually precede lock/objective room.
- Locked route should have distinct styling.
- If a secret shortcut exists, style it as secondary.

### Boss-Endcap

Boss or final rooms should be visually terminal.

```text
Entry → Approach → Antechamber → Boss Room
```

Requirements:

- Boss room must not be visually buried in the middle of the graph.
- Boss room should have extra margin.
- Boss connection should be emphasized.

### Loop

Use a ring-like or rectangular loop layout.

Requirements:

- Preserve cycle readability.
- Avoid crossing the loop with unrelated connections.
- Secret shortcuts may cross the loop only if styled distinctly.

### Freeform

Use current placement logic as fallback, but still apply:

- collision prevention
- orthogonal routing
- label placement
- camera fit

---

## Room Spacing Rules

Use role-aware spacing.

Recommended defaults:

```text
minimum_room_gap = 48
major_room_gap = 72
boss_room_margin = 96
hub_spoke_radius = 220
branch_lane_gap = 180
label_padding = 8
connection_clearance = 16
```

These values should be configurable.

Rules:

- Rooms must not overlap.
- Normal connection lines must not pass through unrelated rooms.
- Important rooms should have more breathing room.
- Small transition rooms should not be isolated too far away unless intentional.
- Large rooms should reserve extra clearance.

---

## Port Generation

Connections should not originate from room centers.

Each room should expose side ports:

```text
      top
       |
left — room — right
       |
     bottom
```

Each room should generate at least these ports:

```text
top
bottom
left
right
```

Large rooms may generate multiple ports per side:

```text
top_left
top_center
top_right
right_upper
right_center
right_lower
bottom_left
bottom_center
bottom_right
left_upper
left_center
left_lower
```

### Port Selection Rules

- Prefer ports facing the target room.
- Prefer ports aligned with the selected layout grammar.
- Avoid ports that immediately route into another room.
- Reuse ports carefully; avoid too many connections from the exact same point.
- Locked, secret, or special connections may use special glyph ports.

---

## Obstacle Model

Treat room rectangles as obstacles for routing.

Before routing, inflate each room rectangle by a configurable clearance amount.

```text
inflated_rect = room_rect + connection_clearance
```

Normal connections may touch the source and target room ports, but must not intersect any other inflated room rectangle.

### Obstacle Rules

- Source and target rooms are excluded from route blocking after the route exits/enters through valid ports.
- All other rooms are blocking obstacles.
- Labels should also be treated as soft obstacles during label placement.
- Optional debug view should display inflated obstacle rectangles.

---

## Orthogonal Routing

Normal dungeon connections should be routed as orthogonal polylines whenever possible.

Avoid raw diagonal lines for standard doors, halls, and arches.

Allowed normal route shapes:

```text
straight horizontal
straight vertical
horizontal → vertical
vertical → horizontal
horizontal → vertical → horizontal
vertical → horizontal → vertical
```

### Routing Strategy

For each edge:

1. Generate candidate source ports.
2. Generate candidate target ports.
3. Try cheap candidate paths first.
4. Reject paths that intersect unrelated inflated room rectangles.
5. Score valid paths.
6. Choose the lowest-score path.
7. If no cheap path works, use a waypoint/A* fallback.
8. Simplify the selected polyline.
9. Store routed path points in the render cache.

### Route Score

Use a scoring function instead of only valid/invalid checks.

Suggested scoring:

```text
score =
  total_length * 1.0
  + bend_count * 24
  + room_crossings * 100000
  + near_room_penalty * 20
  + port_side_penalty * 14
  + shared_path_penalty * 18
  + label_conflict_penalty * 10
  + excessive_detour_penalty * 30
```

The exact values can be tuned after visual testing.

### Excessive Detour Prevention

Avoid routes that technically work but create huge rectangular loops or perimeter boxes.

Penalize routes that:

- travel far outside the bounding box between source and target
- visually enclose unrelated rooms
- have very high length compared to direct distance
- create map-border-like paths
- add more than three bends without necessity

---

## Special Connection Styles

Not all connections should obey the same visual grammar.

Recommended styles:

```text
normal: orthogonal solid line
locked: orthogonal line with gate marker or heavier stroke
secret: dashed or dimmed route
shortcut: curved or dashed secondary route
impossible: curved/glowing/unstable route
one_way: arrow or directional marker
vertical_transition: stair/elevator glyph
```

### Important Rule

Impossible geometry should look intentional.

A weird connection should never look like a routing bug. If it crosses space, curves strangely, or ignores ordinary obstacle rules, it must use a visual style that clearly marks it as special.

---

## Label Placement

Connection labels must be placed after routes are calculated.

Each label should be treated as a rectangle for collision checks.

### Edge Label Candidate Generation

For each routed connection:

1. Identify eligible line segments.
2. Prefer the longest clean segment.
3. Generate candidates at 25%, 50%, and 75% along the segment.
4. Try offsets above/below or left/right of the segment.
5. Score candidates.
6. Pick the lowest-score label position.

### Label Score

Penalize labels that:

- overlap room rectangles
- overlap other labels
- sit too close to room borders
- sit offscreen or near viewport edges
- obscure connection bends
- appear closer to the wrong connection than their own

### Room Labels

Room labels should remain centered inside rooms for now.

Longer-term, room labels may support:

- title + subtitle
- role icon
- status markers
- revealed/unrevealed states

---

## Camera Auto-Fit

Camera framing should happen after room placement, routing, and label placement.

Compute final world bounds from:

- room rectangles
- routed connection points
- edge labels
- room labels if outside room bounds
- important debug overlays only when debug mode is active

Then apply margin and fit the camera.

### Requirements

- Map should start fully visible.
- HUD should not be included in world bounds.
- Use separate world and HUD cameras if not already doing so.
- Camera should not constantly refit during minor changes.
- Manual pan/zoom should not be overridden unless the map is reloaded or reset.

### Suggested Behavior

- On level load: auto-fit map.
- On window resize: refit unless user has manually panned/zoomed.
- On reset view button: refit map.
- During manual pan: do not auto-fit.

---

## Arcade Rendering Guidance

The renderer should favor batched rendering.

Recommended Arcade rendering approach:

- Use `ShapeElementList` or equivalent batched shape strategy for static room shapes and connection lines.
- Use `arcade.Text` objects instead of repeatedly calling immediate text drawing functions.
- Separate world rendering from HUD rendering.
- Cache derived geometry until the dungeon layout changes.
- Do not recalculate routes every frame.

Suggested render layers:

```text
background_grid
connection_shadow
connection_lines
connection_labels
room_fills
room_outlines
room_labels
room_markers
selection_highlight
debug_overlay
hud
```

Rooms should generally draw above connection lines so connections do not visually cut through room bodies.

---

## Validation and Testing

Add layout invariant tests.

### Required Invariants

For every test fixture:

- No room rectangles overlap.
- No normal connection intersects an unrelated room rectangle.
- Every normal connection starts and ends at valid ports.
- Edge labels do not overlap room bodies unless no valid position exists.
- Camera fit bounds contain all rooms and routed connection geometry.
- Layout output is deterministic for the same input and seed.

### Recommended Debug Metrics

For each rendered floor, calculate:

```text
room_overlap_count
illegal_connection_crossing_count
edge_crossing_count
average_route_length
average_bend_count
max_bend_count
label_overlap_count
offscreen_geometry_count
layout_score
```

Display these in a debug panel or write them to logs during tests.

---

## Debug Overlay Requirements

Add a debug overlay toggle showing:

- room bounding boxes
- inflated obstacle boxes
- selected ports
- routed polyline points
- label bounding boxes
- camera fit bounds
- route score per edge
- illegal crossing highlights

This will make future layout work much easier to diagnose.

---

## Suggested First Fixtures

Use real problem maps from the current Dungeon Daddy output.

Recommended initial fixtures:

1. **The Crucible - Level 1**
   - Tests excessive detour avoidance.
   - Tests diagonal-to-orthogonal conversion.

2. **The Crucible - Level 2**
   - Tests hub-spoke layout.
   - Good compact vertical slice.

3. **The Crucible - Level 3**
   - Tests large-room spacing and camera framing.
   - Tests boss/objective presentation.

4. **Tomb of the Forgotten King - Hall of Bound Servants**
   - Tests branching exploration layout.
   - Tests entry/transition/destination readability.

5. **Tomb of the Forgotten King - The King's Tomb**
   - Tests branch-merge and boss-endcap layout.
   - Tests endpoint spacing.


---

## Generated Test Feedback Collection

Claude Code must extend the automated tests so they collect useful diagnostic feedback after layout generation. These tests should not only pass or fail. They should also produce a compact, reviewable artifact that helps a human judge whether the layout actually improved.

The goal is to make every fixture-based layout test answer these questions:

```text
What layout template was selected?
What room roles were inferred?
What critical path was chosen?
What routes were generated?
Where did the layout score well or poorly?
What visual risks remain even if the invariant tests pass?
```

### Required Feedback Artifact

For each fixture test, write a JSON feedback report to a test output directory such as:

```text
test_outputs/layout_feedback/<fixture_name>.layout_feedback.json
```

The report should be deterministic for the same input and seed.

Recommended structure:

```json
{
  "fixture_name": "the_crucible_l1",
  "seed": 12345,
  "layout_template": "linear",
  "template_confidence": 0.82,
  "room_roles": {
    "receiving_hall": "entrance",
    "marketplace": "hub",
    "cargo_bay": "side_room",
    "trap_room": "hazard",
    "elevator_shaft": "exit"
  },
  "critical_path": [
    "receiving_hall",
    "marketplace",
    "elevator_shaft"
  ],
  "optional_branches": [
    ["marketplace", "cargo_bay", "trap_room"]
  ],
  "layout_metrics": {
    "room_overlap_count": 0,
    "illegal_connection_crossing_count": 0,
    "edge_crossing_count": 1,
    "average_route_length": 184.5,
    "average_bend_count": 1.4,
    "max_bend_count": 3,
    "label_overlap_count": 0,
    "offscreen_geometry_count": 0,
    "excessive_detour_count": 0,
    "layout_score": 87.2
  },
  "route_feedback": [
    {
      "connection_id": "marketplace_to_elevator",
      "style": "normal",
      "source_port": "bottom_center",
      "target_port": "top_center",
      "bend_count": 2,
      "route_length": 212.0,
      "direct_distance": 166.0,
      "detour_ratio": 1.28,
      "score": 245.0,
      "warnings": []
    }
  ],
  "label_feedback": [
    {
      "connection_id": "marketplace_to_elevator",
      "label": "elevator",
      "placement_segment_index": 1,
      "overlaps_room": false,
      "overlaps_other_label": false,
      "near_viewport_edge": false,
      "score": 12.0,
      "warnings": []
    }
  ],
  "camera_feedback": {
    "fit_bounds": [0, 0, 1200, 800],
    "contains_all_rooms": true,
    "contains_all_routes": true,
    "contains_all_labels": true,
    "margin_applied": 80
  },
  "warnings": [],
  "human_review_notes": []
}
```

### Required Per-Fixture Summary

At the end of the test run, generate one summary file:

```text
test_outputs/layout_feedback/layout_feedback_summary.md
```

The summary should be written for a human reviewer. It should include:

- fixture name
- selected layout template
- inferred entrance, hub, boss/objective, and exit if found
- critical path
- top three layout warnings
- before/after comparison note placeholder
- pass/fail status for invariants
- overall layout score

Example summary row:

```markdown
| Fixture | Template | Critical Path | Warnings | Score | Status |
|---|---|---|---|---:|---|
| The Crucible L1 | linear | Receiving Hall → Marketplace → Elevator Shaft | 1 edge crossing, 0 illegal crossings, 0 excessive detours | 87.2 | PASS |
```

### Visual Snapshot Output

If the project already has a screenshot or headless render capability, each fixture test should also produce a PNG snapshot:

```text
test_outputs/layout_feedback/screenshots/<fixture_name>.png
```

If screenshot generation is not currently available, do not block the layout implementation. Instead:

1. Add a TODO in the summary file.
2. Ensure the JSON feedback contains enough geometry to reproduce the layout visually later.

The JSON should include final room rectangles, routed polylines, label boxes, and camera bounds either directly or in a linked debug geometry file.

### Warning Categories

Generated test feedback should classify warnings using stable category names.

Recommended warning categories:

```text
ROOM_OVERLAP
ILLEGAL_ROOM_CROSSING
EDGE_CROSSING
EXCESSIVE_DETOUR
TOO_MANY_BENDS
LABEL_ROOM_OVERLAP
LABEL_LABEL_OVERLAP
LABEL_NEAR_EDGE
OFFSCREEN_GEOMETRY
WEAK_TEMPLATE_CONFIDENCE
MISSING_ENTRANCE_ROLE
MISSING_OBJECTIVE_ROLE
HUB_NOT_CENTRAL
BOSS_NOT_TERMINAL
SECRET_ROUTE_DOMINATES_LAYOUT
CAMERA_BOUNDS_INCOMPLETE
```

Warnings should include enough context to diagnose the problem.

Example:

```json
{
  "category": "EXCESSIVE_DETOUR",
  "severity": "medium",
  "connection_id": "receiving_hall_to_marketplace",
  "message": "Route detour ratio is 3.4, which may create a large rectangular corridor artifact.",
  "data": {
    "route_length": 680.0,
    "direct_distance": 200.0,
    "detour_ratio": 3.4
  }
}
```

### Human Review Checklist Output

Generate a small checklist in the Markdown summary for each fixture. This is not an automated pass/fail requirement. It is meant to guide visual review after Claude Code finishes.

For each fixture, include these prompts:

```markdown
### Human Review: The Crucible L1

- [ ] Does the entrance feel like the start of the map?
- [ ] Does the objective/exit feel like the destination?
- [ ] Are normal connections readable as corridors rather than arbitrary graph lines?
- [ ] Are there any giant rectangular detours?
- [ ] Do connection labels sit in understandable places?
- [ ] Does the camera frame the entire floor on load?
- [ ] Did any layout choice make the map uglier even though tests passed?
```

### Fixture-Specific Feedback Expectations

Collect the following targeted notes in the generated summary:

#### The Crucible - Level 1

Focus feedback on:

- whether the giant rectangular corridor artifact was eliminated or reduced
- whether the elevator connection is routed cleanly
- whether the main path reads clearly
- whether any route still visually encloses unrelated rooms

#### The Crucible - Level 2

Focus feedback on:

- whether the central hub is actually central
- whether spokes are balanced around the hub
- whether diagonal-looking normal connections were replaced with cleaner orthogonal routes
- whether optional rooms are visually secondary

#### The Crucible - Level 3

Focus feedback on:

- whether the boss/objective relationship is visually clear
- whether the lower control/key route reads as related to the upper boss/core route
- whether large rooms have enough breathing room
- whether camera framing includes all rooms and labels

#### Tomb of the Forgotten King - Hall of Bound Servants

Focus feedback on:

- whether Stair Landing feels like the entry point
- whether Sealed Descent feels like a destination/threshold
- whether the branching exploration structure reads clearly
- whether small destination rooms feel detached or properly connected

#### Tomb of the Forgotten King - The King's Tomb

Focus feedback on:

- whether the branch-and-merge structure is clear
- whether symmetry is improved where appropriate
- whether Throne of Bone feels terminal and important
- whether Throne of Bone no longer visually merges with Processional

### Regression Comparison Support

If baseline images or prior metric files exist, compare the new output against them.

At minimum, the generated feedback should support later before/after comparison by recording:

- layout score
- room overlap count
- illegal connection crossing count
- edge crossing count
- excessive detour count
- label overlap count
- offscreen geometry count
- selected template
- critical path

Do not require perfect visual improvement from metrics alone. Metrics are diagnostic support. Human visual review remains part of the acceptance process.

### Test Failure Behavior

Invariant failures should fail tests.

Examples that should fail:

- room overlap
- normal connection through unrelated room
- invalid port endpoint
- camera bounds excluding room geometry
- nondeterministic layout for same seed

Visual quality warnings should not automatically fail tests unless they violate a hard invariant.

Examples that should warn but not fail:

- edge crossing between two legal connections
- route with high detour ratio
- weak template confidence
- label placed in a suboptimal but legal location
- boss room not strongly terminal according to heuristic

This distinction is important. The test suite should protect correctness while still collecting feedback for layout tuning.
---

## Acceptance Criteria

This phase is complete when the following are true:

1. At least three real dungeon floor fixtures render using the new pipeline.
2. Room roles are either read from metadata or inferred consistently.
3. At least four layout templates are supported:
   - `linear`
   - `hub_spoke`
   - `branch_merge`
   - `boss_endcap` or `lock_key`
4. Normal connections use port-based orthogonal routing.
5. Normal connections do not pass through unrelated rooms.
6. Excessive rectangular detours are penalized and avoided where a better route exists.
7. Connection labels are placed after routing and avoid obvious collisions.
8. Camera auto-fit frames the full map on level load.
9. Debug overlay can show rooms, inflated obstacles, ports, routes, labels, and camera bounds.
10. Automated tests validate core layout invariants.
11. Fixture-based layout tests generate JSON feedback reports for human review.
12. Fixture-based layout tests generate a Markdown feedback summary with warnings, metrics, and human review checklists.
13. Where screenshot generation exists, fixture tests save rendered layout snapshots; otherwise, they save enough debug geometry to reproduce the layout later.
14. The map viewer still uses vector/geometric rendering, not tiles.
15. Existing pan/zoom functionality continues to work.

---

## Implementation Order

Recommended order for Claude Code:

### Step 1: Add Geometry Models

Create data structures for:

- room rectangle
- inflated room rectangle
- port
- route segment
- routed edge
- label box
- layout bounds

### Step 2: Add Room Roles and Template Selection

Implement semantic analysis for room roles and floor templates.

### Step 3: Implement Critical Path Seed Layout

Start with deterministic placement for:

- linear
- hub_spoke
- branch_merge
- boss_endcap

Do not worry about perfect compaction yet.

### Step 4: Generate Ports

Add side ports to rooms and expose them to the router.

### Step 5: Implement Orthogonal Routing

Start with cheap candidate dogleg routing.

Only add A* or waypoint fallback after the basic candidate router is stable.

### Step 6: Add Label Placement

Place labels after routes are selected.

### Step 7: Add Camera Fit

Calculate final layout bounds and fit the world camera.

### Step 8: Add Validation Tests and Feedback Reports

Add invariant tests, fixture-based regression checks, JSON layout feedback reports, and a Markdown feedback summary suitable for human review.

### Step 9: Add Debug Overlay

Make routing and layout decisions visible.

### Step W: Wire Pipeline into Map Panel

Connect the layout pipeline to the Arcade map panel (Graph tab).

- `dungeon_daddy/map/dungeon_layout/__init__.py` — `LayoutResult` dataclass + `run_layout_pipeline(level)` entry point.
- `dungeon_daddy/map/layout_renderer.py` — `LayoutRenderer` draws rooms, edges, and labels via Arcade.
- `MapPanel.load()` caches `LayoutResult` per level; Graph tab calls `LayoutRenderer`.
- `MapPanel._fit_layout_camera()` centres layout bounds in the viewport on Graph tab activation.
- `D` key toggles `DebugOverlay.enabled`.
- Cross-level stair connections filtered silently before port/routing stages.

**Status: Done (2026-05-30).**

### Step 10: Room Name Labels in Graph View — **Done (2026-05-30)**

- `room_names: dict[str, str]` added to `LayoutResult` (default empty dict).
- `run_layout_pipeline` populates it from `level.rooms`.
- `LayoutRenderer._draw_rooms()` calls `arcade.draw_text` centred in each rect using `FONT_UI` / `TEXT_XS`.

### Step 11: Room Click and Selection Highlight — **Done (2026-05-30)**

- `_selected_room_id: str | None` on `MapPanel`; reset to `None` on `load()`.
- `MapPanel.handle_mouse_press()` hit-tests layout-space rects when Graph/select mode active; toggles selection on same-room click.
- `LayoutRenderer.draw()` accepts `selected_room_id`; draws teal 2px outline over the selected room.

---

## Notes for Claude Code

Prioritize correctness and readability over cleverness.

Do not introduce a large external graph layout engine as a hard dependency in this phase. NetworkX, Graphviz, ELK, Shapely, Kiwi, or OR-Tools may be useful later, but this phase should first establish a clean internal pipeline that can be tested and improved.

If a third-party library is already used in the project, it may be reused. Otherwise, prefer simple project-local geometry utilities first.

The goal is to make the maps feel more intentional, not to chase a mathematically perfect layout.

---

## Final Design Principle

Dungeon Daddy maps should not look like arbitrary node graphs.

They should look like readable, stylized dungeon schematics where:

- the entrance feels like the beginning
- the objective feels like the destination
- hubs feel central
- branches feel intentional
- secrets feel mysterious but readable
- impossible geometry feels deliberate
- the camera frames the dungeon confidently

The JSON defines the dungeon. The renderer should reveal its structure.
