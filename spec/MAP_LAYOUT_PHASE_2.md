# Dungeon Daddy Graph Mode — Phase 2 Map Visual Hierarchy & Semantic Presentation

> **Phase 20 closed — 2026-05-30.**
> All 10 steps complete. 1,097 tests passing. mypy zero errors.
> Artifacts in `artifacts/layout/phase2/`. See `spec/PROJECT_INDEX.md` for session log.

## Purpose

Phase 1 successfully moved the Dungeon Daddy map renderer away from fragile geometric output and toward clean, collision-free graph layouts. The current Graph Mode now produces readable room placement, clean routed connections, useful layout metrics, and generated feedback artifacts.

Phase 2 should build on that success without replacing the underlying approach.

The goal of Phase 2 is to make Graph Mode communicate dungeon meaning, player flow, room importance, and connection type through visual hierarchy while preserving the clean schematic layout achieved in Phase 1.

This work applies to **Graph Mode only**.

Do **not** modify the legacy Grid Mode. Grid Mode should remain available as a comparison baseline against the improved Graph Mode.

---

## Context

Dungeon Daddy currently has at least two visual map modes:

- **Grid Mode**: legacy map display style; leave untouched.
- **Graph Mode**: newer schematic room-and-connection visualization; Phase 2 target.

Phase 1 Graph Mode improvements appear successful. The test outputs show:

- no room overlaps
- no illegal connection crossings
- no label overlaps
- no offscreen geometry
- no excessive detours
- generated layout feedback JSON
- generated layout summary Markdown
- human review checklists

The remaining problem is not basic geometry.

The remaining problem is semantic presentation.

The map should no longer merely say:

> These rooms are connected.

It should begin to say:

> This is where the dungeon starts. This is the hub. This is the dangerous route. This is the objective. This is the secret path. This is the threshold to the next level.

---

## Design Principle

Graph Mode should remain a stylized schematic map using geometric shapes, labels, and routed lines.

Do not convert Graph Mode into a tile map.

Tiles may be useful in a future tactical-map mode, but they are not the correct solution for the current Graph Mode goal. The current objective is a readable, elegant, semantic dungeon overview.

---

## Non-Goals

Do not:

1. Modify legacy Grid Mode.
2. Replace the Phase 1 layout engine wholesale.
3. Convert the map to a tile-based dungeon renderer.
4. Introduce tactical movement grids.
5. Require pixel-art room rendering.
6. Add animated effects unless they are trivial and optional.
7. Break existing dungeon JSON compatibility.
8. Remove Phase 1 diagnostic output.
9. Sacrifice readability for style.
10. Hide layout problems behind decorative styling.

---

## Phase 2 Goals

Phase 2 should add the following capabilities to Graph Mode:

1. Room role styling.
2. Room shape grammar.
3. Connection style language.
4. Endpoint emphasis.
5. Improved semantic role inference and warnings.
6. Visual hierarchy scoring in generated feedback.
7. Screenshot/output artifact generation to support human review.
8. Comparison discipline: Grid Mode remains untouched for before/after reference.

---

## Core User Experience Target

After Phase 2, a user should be able to glance at a Graph Mode map and identify:

- where the floor starts
- the likely main route
- the hub, if any
- key/lock relationships, if present
- boss or objective rooms
- exits, stairs, elevators, descents, or transitions
- secret or abnormal connections
- hazardous or special routes

They should be able to do this before reading every room label.

---

## Required Architecture

### 1. Keep Graph Mode Isolated

All Phase 2 changes must be scoped to Graph Mode.

Expected approach:

- Add or extend Graph Mode renderer classes/modules.
- Add Graph Mode visual style configuration.
- Add Graph Mode-specific tests.
- Preserve existing Grid Mode behavior.

Do not refactor shared rendering code in a way that risks changing Grid Mode unless there is no alternative. If shared code must be touched, document why and add regression tests proving Grid Mode is unchanged.

### 2. Preserve Phase 1 Layout Data

Phase 2 should consume and extend Phase 1 data, not discard it.

Continue using:

- layout template
- room roles
- critical path
- optional branches
- route feedback
- label feedback
- camera feedback
- warnings
- layout metrics

Add new semantic and visual hierarchy metadata on top of the existing feedback model.

---

## Room Role System

### Required Room Roles

Graph Mode should support at least these room roles:

```text
entrance
hub
boss
objective
exit
descent
elevator
stairs
key_room
lock_room
treasure
hazard
secret
corridor
hall
study
library
forge
utility
unknown
```

The existing role inference may already support some of these. Phase 2 should expand or formalize the role model.

### Role Sources

Room roles may come from:

1. Explicit room metadata in dungeon JSON.
2. Existing inferred roles from Phase 1.
3. Name-based inference.
4. Connection-based inference.
5. Layout-template context.

Explicit metadata must take priority over inference.

### Name-Based Inference Examples

Use room names to infer roles when explicit metadata is absent.

Examples:

| Name Contains | Suggested Role |
|---|---|
| entrance, entry, receiving hall, approach | entrance |
| hub, nexus, junction, crossroads | hub |
| boss, lair, throne, core chamber, sanctum | boss or objective |
| exit, descent, stairs, stair, elevator, shaft | exit/descent/elevator/stairs |
| key, control, lever, mechanism, switch | key_room |
| locked, sealed, gate, barrier | lock_room |
| treasury, reliquary, vault | treasure or objective |
| trap, hazard, anomaly, electrified, pit | hazard |
| library, scriptorium, archive | library/study |
| forge, foundry, molten, factory | forge |

Do not overfit the inference. When uncertain, use `unknown` and emit a warning rather than inventing false certainty.

---

## Room Visual Grammar

### Required Styling Concept

Rooms should no longer all appear visually equivalent.

Graph Mode should style rooms based on semantic role while preserving the existing clean rectangular schematic style.

At minimum, vary some combination of:

- border weight
- border brightness
- fill opacity
- fill shade
- label treatment
- size bias
- shape/proportion
- subtle internal marker/icon text
- double border for major rooms
- muted treatment for secondary rooms

Avoid making the map noisy.

### Role Styling Guidance

| Role | Visual Treatment |
|---|---|
| entrance | subtle start marker, slightly brighter border, optional small `IN` or stair marker |
| hub | larger or more centered, stronger border, visually stable anchor |
| boss | larger, heavier border, darker or more intense fill, destination-like treatment |
| objective | emphasized, but may be less aggressive than boss |
| exit/descent/stairs/elevator | threshold styling, compact but visually distinct, optional arrow/down marker |
| key_room | distinct accent border or small key/control marker |
| lock_room | gate-like styling, stronger border or lock marker |
| treasure | optional accent, should not overpower boss/objective |
| hazard | sharper/danger treatment, warning marker, but readable |
| secret | muted/faint style unless revealed; dashed or subtle border |
| corridor/hall/processional | elongated rectangle based on orientation |
| unknown | default room styling |

### Shape Grammar

If feasible, room shape should reflect room type.

Examples:

| Semantic Type | Shape Guidance |
|---|---|
| standard room | rectangle |
| hall/corridor/processional | elongated rectangle aligned to flow |
| hub | larger square or balanced rectangle |
| boss/objective | larger destination chamber, possibly double border |
| nook/study | smaller compact room |
| descent/elevator/stairs | compact square/threshold node |
| secret | smaller offset node or faded outline |

Do not distort rooms so severely that labels become unreadable.

### Label Improvements

Room labels may remain simple, but should support optional role indicators.

Example:

```text
Receiving Hall
R1 • Entrance
```

or:

```text
Prime Golem Lair
r7 • Boss
```

If role text clutters the map, support a debug/config flag to show or hide it.

Recommended:

- Default: room name + id remains visible.
- Debug overlay: role and layout metadata visible.

---

## Connection Style Language

Connections should communicate more than adjacency.

### Required Connection Types

Support at least these styles:

```text
normal
hall
arch
door
locked
secret
shortcut
vertical
hazard
impossible
```

Existing connection labels such as `door`, `hall`, `arch`, `hole`, `secret_shortcut`, `lock_key`, and `pursuit` should map into this style language.

### Connection Styling Guidance

| Connection Type | Visual Treatment |
|---|---|
| normal | standard solid line |
| door | solid line, optional small door tick/marker |
| hall | standard or slightly longer clean corridor line |
| arch | solid line with subtle arch marker or label treatment |
| locked | thicker or gated line; lock marker near midpoint |
| secret/shortcut | dashed, faint, curved, or lower-opacity line |
| vertical | line with up/down/stair/elevator marker |
| hazard | warning treatment, broken line, or hazard marker |
| impossible | visually distinct from normal routing; may be curved/diagonal/faint/glowing if supported |

### Important Rule

Secret, shortcut, vertical, hazardous, and impossible connections should look intentionally different.

They should not look like accidental bad routing.

### Connection Labels

Continue preserving labels, but improve semantic styling:

- `secret_shortcut` should not dominate the map.
- `lock_key` should be visually associated with lock/key relationship if possible.
- `pursuit` should be visible but not treated like a normal passage.
- Label placement should continue using Phase 1 label collision checks.

---

## Endpoint Emphasis

Graph Mode should emphasize meaningful endpoint rooms.

Endpoint candidates include:

- boss rooms
- objective rooms
- exits
- descents
- elevators
- stairs
- locked destination rooms
- core chambers
- throne rooms

If the graph has a clear critical path, the final room on that path should be evaluated as a visual endpoint.

### Endpoint Rules

The endpoint should:

1. Have enough spacing from adjacent rooms.
2. Have stronger visual treatment than ordinary rooms.
3. Read as a destination or threshold.
4. Not visually merge with the previous room.
5. Be included in visual hierarchy feedback.

### Example

In a branch-and-merge tomb map:

```text
Ossuary Approach → branching rooms → Processional → Throne of Bone
```

`Throne of Bone` should visually feel like the culmination.

---

## Critical Path Presentation

If a critical path is available, Graph Mode should be able to visually distinguish it from optional branches.

This does not need to be dramatic.

Possible approaches:

- slightly brighter line treatment on critical path
- slightly stronger room borders for critical path rooms
- subtle fade of optional branches
- debug overlay only, if default styling feels too busy

Required behavior:

- Do not make optional branches unreadable.
- Do not make the critical path look like an active selection unless the UI intends that.
- Provide a configuration flag to enable/disable critical path emphasis.

---

## Configuration Requirements

Add a Graph Mode visual hierarchy configuration object or equivalent constants.

It should control:

```text
show_role_debug_labels
emphasize_critical_path
style_secret_connections
style_endpoint_rooms
style_room_roles
enable_shape_grammar
enable_connection_markers
enable_visual_hierarchy_feedback
```

Defaults should favor readability and modest styling.

---

## Generated Feedback Output Requirements

Phase 2 must extend the existing generated feedback artifacts.

For each test fixture, generate or update a `.layout_feedback.json` file containing all Phase 1 fields plus a new Phase 2 section.

### Required New JSON Section

Add a `visual_hierarchy_feedback` section similar to:

```json
{
  "visual_hierarchy_feedback": {
    "roles_styled": true,
    "connection_styles_applied": true,
    "critical_path_emphasized": true,
    "endpoint_emphasized": true,
    "shape_grammar_applied": true,
    "semantic_score": 87.5,
    "room_style_feedback": [
      {
        "room_id": "R2",
        "room_name": "Marketplace",
        "role": "hub",
        "style_key": "hub",
        "expected_visual_priority": "high",
        "actual_visual_priority": "high",
        "warnings": []
      }
    ],
    "connection_style_feedback": [
      {
        "connection_id": "R1→R2",
        "label": "arch",
        "connection_type": "arch",
        "style_key": "arch",
        "warnings": []
      }
    ],
    "endpoint_feedback": {
      "endpoint_room_id": "R4",
      "endpoint_role": "exit",
      "is_emphasized": true,
      "has_sufficient_spacing": true,
      "warnings": []
    },
    "critical_path_feedback": {
      "critical_path": ["R1", "R2", "R4"],
      "is_visually_distinguished": true,
      "warnings": []
    }
  }
}
```

Exact schema may vary, but the output must contain enough information for review.

### New Warning Categories

Add warning categories where applicable:

```text
MISSING_SEMANTIC_ROLE
AMBIGUOUS_ENTRANCE_ROLE
AMBIGUOUS_ENDPOINT_ROLE
ENDPOINT_NOT_EMPHASIZED
HUB_NOT_EMPHASIZED
BOSS_NOT_EMPHASIZED
KEY_ROOM_NOT_DISTINCT
LOCK_ROOM_NOT_DISTINCT
SECRET_CONNECTION_NOT_DISTINCT
VERTICAL_CONNECTION_NOT_DISTINCT
CRITICAL_PATH_NOT_DISTINGUISHED
ROOM_STYLE_NOT_APPLIED
CONNECTION_STYLE_NOT_APPLIED
SHAPE_GRAMMAR_NOT_APPLIED
VISUAL_PRIORITY_CONFLICT
ROLE_INFERENCE_LOW_CONFIDENCE
```

Warnings should be useful, not noisy.

Do not fail a test merely because a room role is unknown unless that unknown role prevents the layout from communicating start, destination, or required structure.

---

## Markdown Summary Output Requirements

Update the generated Markdown summary to include Phase 2 fields.

Expected file:

```text
layout_feedback_summary.md
```

or, if preserving Phase 1 summary separately:

```text
layout_visual_hierarchy_summary.md
```

The summary must include:

| Fixture | Template | Critical Path | Semantic Score | Geometry Score | Visual Warnings | Status |
|---|---|---|---:|---:|---|---|

Also include a human review checklist for each fixture.

### Required Human Review Questions

For each fixture, include:

- Does the entrance feel like the start of the map?
- Does the endpoint/objective feel like the destination?
- Are boss/objective rooms visually more important than ordinary rooms?
- Are hub rooms visually stable and central?
- Are key rooms visually distinct without overpowering the map?
- Are locked rooms or locked connections understandable?
- Are secret/shortcut connections visually distinct from normal corridors?
- Are vertical travel connections visually distinct?
- Does the critical path read more clearly than optional branches?
- Did any Phase 2 styling make the map noisier or uglier?
- Does Graph Mode remain cleaner and more useful than Grid Mode for overview reading?

---

## Screenshot / Artifact Requirements

Claude Code must produce artifacts that can be reviewed after implementation.

At minimum, produce:

1. Updated `.layout_feedback.json` for each fixture.
2. Updated Markdown feedback summary.
3. Screenshots of Graph Mode for each test fixture after Phase 2.
4. If feasible, screenshots of Grid Mode for the same fixtures, unchanged, for comparison.
5. Optional debug screenshots with role labels and connection style annotations enabled.

### Required Screenshot Naming

Use deterministic names if possible:

```text
artifacts/layout/phase2/crucible_l1_graph.png
artifacts/layout/phase2/crucible_l1_graph_debug.png
artifacts/layout/phase2/crucible_l1_grid_baseline.png
artifacts/layout/phase2/crucible_l2_graph.png
artifacts/layout/phase2/crucible_l3_graph.png
artifacts/layout/phase2/tomb_l1_graph.png
```

If the project has an established artifact folder, use that instead, but document the final locations.

### Screenshot Requirements

Screenshots should show:

- full map visible
- Graph Mode selected
- room labels readable
- connection labels readable where possible
- no manual pan/zoom unless required by the existing test harness
- debug screenshots should include role/styling annotations if implemented

---

## Required Test Fixtures

Use the existing Phase 1 fixtures at minimum:

```text
crucible_l1
crucible_l2
crucible_l3
tomb_l1
```

If available, also test:

```text
tomb_l2
king_tomb_l3
hall_of_bound_servants
```

Do not skip existing fixtures merely because the styling code is not exercised. Add role metadata or inference tests as needed.

---

## Automated Test Requirements

### 1. Geometry Regression Tests

All Phase 1 geometry tests must continue to pass:

- no room overlap
- no illegal connection crossings
- no label overlaps
- no offscreen geometry
- no excessive detours
- routes contained by camera bounds
- labels contained by camera bounds

Phase 2 must not regress Phase 1.

### 2. Grid Mode Regression Test

Add or preserve tests proving Grid Mode is untouched.

At minimum:

- Grid Mode can still render without exception.
- Existing Grid Mode screenshots or rendering outputs are not modified by Graph Mode changes.
- Graph Mode-only style configuration does not affect Grid Mode.

If snapshot tests are available, compare Grid Mode snapshots before/after. If not, add a smoke test.

### 3. Role Inference Tests

Add tests for name-based and metadata-based role inference.

Examples:

```text
Receiving Hall -> entrance
Central Hub -> hub
Prime Golem Lair -> boss
Power Core Chamber -> objective or boss
Elevator Shaft -> elevator/exit
Sealed Descent -> descent/exit
Conveyor Control -> key_room
Throne of Bone -> boss/objective
Reliquary -> treasure/objective depending context
Trap Room -> hazard
```

Explicit metadata should override name inference.

### 4. Room Styling Tests

Add tests confirming that role styles resolve correctly.

Examples:

- boss room receives boss style key
- hub room receives hub style key
- entrance room receives entrance style key
- unknown room receives default style key
- secret room receives secret style key

Tests may validate style keys/config values rather than pixel output.

### 5. Connection Styling Tests

Add tests confirming connection labels map to connection style keys.

Examples:

```text
door -> door style
hall -> hall style
arch -> arch style
hole -> vertical or hazard/impossible depending current semantics
secret_shortcut -> secret/shortcut style
lock_key -> locked/key relationship style
pursuit -> special/non-standard style
```

### 6. Visual Hierarchy Feedback Tests

Add tests confirming that generated feedback includes:

- `visual_hierarchy_feedback`
- `room_style_feedback`
- `connection_style_feedback`
- `endpoint_feedback`
- `critical_path_feedback`
- semantic score
- relevant warnings

### 7. Endpoint Emphasis Tests

For fixtures with objective/boss/exit/descent roles, test that endpoint emphasis is detected.

If endpoint is missing, test that the correct warning is emitted.

### 8. Critical Path Presentation Tests

If critical path emphasis is enabled, test that critical path rooms/connections receive the appropriate style flags.

Do not require visual pixel comparison unless the project already supports it.

---

## Acceptance Criteria

Phase 2 is successful when:

1. Graph Mode remains collision-free and readable.
2. Grid Mode remains untouched and usable.
3. Room roles produce visible styling differences.
4. Boss/objective/exit rooms are visually emphasized.
5. Entrance rooms read more clearly as starting points.
6. Hub rooms read as organizing centers.
7. Secret/shortcut/vertical/special connections are visually distinct from ordinary corridors.
8. Critical path emphasis exists and can be enabled/disabled.
9. Generated JSON feedback includes visual hierarchy evaluation.
10. Generated Markdown summary includes visual hierarchy review prompts.
11. Screenshots are produced for human review.
12. Existing Phase 1 test fixtures still pass geometry tests.
13. New Phase 2 semantic tests pass.
14. The visual style remains restrained, readable, and consistent with Dungeon Daddy's current geometric schematic presentation.

---

## Implementation Suggestions

### Suggested Modules / Components

The exact codebase structure may differ, but consider adding or extending components like:

```text
GraphRoomRoleInferer
GraphRoomStyleResolver
GraphConnectionStyleResolver
GraphVisualHierarchyAnalyzer
GraphLayoutFeedbackWriter
GraphMapScreenshotTestHarness
```

Keep these small and testable.

### Suggested Data Flow

```text
Dungeon JSON
  -> Phase 1 layout/template/route generation
  -> room role inference
  -> connection type inference
  -> visual style resolution
  -> Graph Mode rendering
  -> visual hierarchy feedback generation
  -> screenshots and summaries
```

### Suggested Style Resolution Model

Use style keys rather than hard-coding every rendering decision inline.

Example:

```python
room_style = room_style_resolver.resolve(room_role, room_metadata, debug_flags)
connection_style = connection_style_resolver.resolve(connection_label, connection_metadata)
```

A style object might contain:

```python
@dataclass
class GraphRoomStyle:
    key: str
    border_width: float
    border_alpha: int
    fill_alpha: int
    size_bias: float
    shape_type: str
    show_marker: bool
    marker_text: str | None
    priority: str
```

And:

```python
@dataclass
class GraphConnectionStyle:
    key: str
    line_width: float
    alpha: int
    dashed: bool
    marker_type: str | None
    priority: str
```

Do not use this exact structure if it conflicts with the existing codebase, but preserve the idea: resolve semantics into style objects before drawing.

---

## Visual Restraint Guidelines

The map should not become visually loud.

Prefer:

- subtle differences
- clean borders
- modest markers
- readable labels
- consistent color palette
- simple shape differences

Avoid:

- too many colors
- heavy icons everywhere
- thick lines across the whole map
- excessive glow
- cluttered debug labels in normal mode
- making every room look special

Important rooms should stand out because ordinary rooms remain quiet.

---

## Dungeon Daddy Tone Alignment

The Graph Mode map should remain a functional developer/player overview, but its visual language should support Dungeon Daddy's identity over time.

Future phases may add more mood:

- occult industrial styling
- impossible geometry indicators
- living dungeon motifs
- candlelit/warm room accents
- cold machinery accents
- seductive/cosmic horror visual language

For Phase 2, do not overreach. Establish the semantic foundation first.

---

## Manual Review Instructions After Implementation

After implementing Phase 2, run the layout fixture generation and provide the following back to the project owner for review:

1. Phase 2 Graph Mode screenshots.
2. Debug Graph Mode screenshots if available.
3. Unchanged Grid Mode baseline screenshots if available.
4. Updated `.layout_feedback.json` files.
5. Updated Markdown summary.
6. Short implementation summary.
7. List of files changed.
8. Notes on any design compromises.
9. Any fixtures where Phase 2 styling made the map worse.
10. Any warnings that remain unresolved.

### Required Implementation Summary Format

Produce a short Markdown implementation note:

```text
artifacts/layout/phase2/implementation_summary.md
```

Include:

```markdown
# Phase 2 Implementation Summary

## What Changed
- ...

## What Stayed Untouched
- Grid Mode: untouched / smoke-tested
- Phase 1 routing: unchanged / modified only where noted

## Test Results
- ...

## Generated Artifacts
- ...

## Known Issues
- ...

## Questions for Human Review
- ...
```

---

## Final Instruction

Implement Phase 2 as an incremental improvement to Graph Mode, not as a rewrite.

Protect the success of Phase 1.

Protect legacy Grid Mode as a comparison baseline.

Prioritize readability over decoration.

Produce enough artifacts that a human reviewer can judge whether the map now communicates dungeon meaning, not merely graph correctness.
