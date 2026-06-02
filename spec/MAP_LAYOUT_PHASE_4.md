# Dungeon Daddy — Graph Mode Phase 4: Presentation, Detail Panel, and Dungeon Personality

**Status: Complete** — 1368 tests passing (2026-06-01)

## Purpose

Phase 4 should turn Graph Mode from a clean, semantic, interactive schematic into a more game-like dungeon interface.

Phases 1 through 3 created the foundation:

- **Phase 1** made Graph Mode geometrically readable and stable.
- **Phase 2** added semantic visual hierarchy for room roles and connection styles.
- **Phase 2.5** added authored metadata so the map does not rely only on name inference.
- **Phase 3** added interaction state, hover, selection, focus/fade behavior, keyboard actions, and room detail data assembly.

Phase 4 should build on that work without destabilizing it.

The core goal is:

> When a player opens Graph Mode, the map should feel like an intentional Dungeon Daddy game screen, not merely a debug graph.

This phase should preserve the clean overview quality of Graph Mode while adding presentation polish, a visible detail panel, stronger interaction affordances, and a first pass of Dungeon Daddy atmosphere.

Grid Mode must remain untouched.

---

## Scope Summary

Phase 4 includes:

1. Render the Phase 3 room detail panel visually in Graph Mode.
2. Strengthen hover and selected-room affordances.
3. Add role and connection markers/icons using simple geometric/text glyphs.
4. Add a restrained atmospheric frame/background treatment for Graph Mode.
5. Improve selected-room neighborhood presentation.
6. Improve connection presentation for `critical_path`, `locked`, `secret`, `shortcut`, `vertical`, and `optional_branch` roles.
7. Preserve all Phase 1–3 guarantees.
8. Produce assessment artifacts for screenshots, interaction states, detail panel states, and style feedback.

Phase 4 should not introduce memory-system behavior yet. It may prepare the detail panel and map state for future memory indicators, but actual memory persistence belongs to a later memory module phase.

---

## Non-Goals

Do not implement these in Phase 4:

- No tile-map conversion.
- No changes to Grid Mode.
- No memory database or memory module.
- No AI-generated room images.
- No procedural pixel art generation.
- No scene-card generation pipeline.
- No battle map / tactical map rendering.
- No complex animation framework.
- No audio or sound effects.
- No dependency on live OpenGL for test artifact generation.

Phase 4 should remain compatible with the current PIL artifact renderer so headless testing can continue.

---

## Design Principle

Graph Mode should remain an overview map, not a tactical dungeon map.

It should feel like:

> A stylized occult dungeon navigation interface.

Not:

> A literal architectural blueprint.

Not:

> A fully illustrated battle map.

Not:

> A generic network graph.

Keep the visual language schematic, readable, and moody.

---

## Existing Phase 3 Gaps to Address

The following Phase 3 limitations should be included in Phase 4.

### 1. Detail panel is data-only

Phase 3 added `build_room_detail`, but the detail panel is not visually rendered in the Arcade window.

Phase 4 must render a visible detail panel or detail card in Graph Mode.

### 2. Hover state is too subtle

Phase 3 hover technically works, but it is hard to see in static screenshots. Phase 4 should make hover more obvious without making the map noisy.

### 3. Connection hover is too subtle

Connection hover should visibly brighten and thicken. If possible, nearby connection labels should become more legible on hover.

### 4. Selected state needs stronger game feel

Selection currently works, but it can be more expressive. A selected room should feel intentionally focused.

### 5. Detail panel artifacts must show rendered UI

Phase 4 artifacts must include screenshots where the visible detail panel appears for selected rooms.

---

## Required User-Facing Behavior

### Default Graph Mode

In default state, the map should remain clean and readable.

Expected behavior:

- Room role styling remains visible.
- Critical path remains subtly emphasized.
- Connection roles are visible but not overpowering.
- Detail panel is hidden, collapsed, or shows a neutral instruction state such as:
  - `Select a room`
  - `Hover a room or connection`
  - `Graph Mode`

Do not clutter the map in the default state.

---

### Room Hover

When the mouse hovers over a room:

- The room border should brighten clearly.
- The room may receive a subtle outer glow or secondary outline.
- The room label should remain readable.
- The cursor/hover state should not permanently alter layout.
- Directly connected paths may brighten slightly.
- Unrelated rooms should not heavily fade on hover; keep hover lightweight.

Recommended hover effect:

- Border width +1.0 px compared to base.
- Border alpha/color noticeably brighter.
- Optional faint outer outline/glow.
- Fill alpha modestly increased.

The hover effect must be visible in generated PNG artifacts.

---

### Room Selection

When a room is clicked/selected:

- Selected room receives strongest visual emphasis.
- Connected rooms remain clearly visible.
- Unrelated rooms fade but remain readable.
- Highlighted connections are obvious.
- The visible detail panel updates to the selected room.
- Critical path remains visible.
- If selected room is on the critical path, the critical path should be more legible.

Recommended selection effect:

- Selected room border width +2.0 px over base.
- Optional second outline or glow.
- Connected rooms receive medium emphasis.
- Unrelated rooms/connections fade to roughly 35–50% alpha.
- Selected room label and role marker should remain crisp.

---

### Connection Hover

When hovering near a connection:

- The connection line brightens and thickens.
- The connection label should be easier to read.
- If the connection has an authored `layout_connection_role`, that role should be reflected visually.
- The connected rooms may receive subtle endpoint highlights.

Recommended connection hover effect:

- Line width +1.0 px.
- Line alpha/color increased.
- Label alpha increased.
- Optional small endpoint markers.

---

### Keyboard Controls

Preserve Phase 3 controls:

- `R`: recenter/refit Graph Mode camera.
- `Escape`: clear selected room and return to overview state.

Optional but useful if easy:

- `Tab`: cycle selection through rooms in critical-path order.
- `Shift+Tab`: cycle backward.

Do not implement optional controls if they destabilize the system.

---

## Visible Room Detail Panel

### Requirement

Phase 4 must render a visible room detail panel in Graph Mode when a room is selected.

This can be implemented as:

- A right-side panel.
- A bottom panel.
- A floating card near the selected room.

Preferred: **right-side panel** or **bottom-right card**, because it keeps the graph itself stable and avoids overlapping rooms.

The panel must use existing `build_room_detail` data from Phase 3 rather than duplicating room-summary logic.

---

### Detail Panel Contents

At minimum, the panel must show:

- Room name.
- Room ID.
- Role / layout role.
- Visual priority, if present.
- Critical path status.
- Optional branch status, if present.
- Connected rooms.
- Connection labels/roles.
- `graph_notes`, if present.

Recommended format:

```text
ROOM
Receiving Hall
R1 · Entrance

Status
Critical Path: Yes
Visual Priority: Medium

Connections
→ Marketplace [critical path / arch]
→ Cargo Bay [optional branch / door]

Notes
Starting chamber. Introduces the level and leads toward the market hub.
```

Keep the panel concise. Do not dump raw JSON.

---

### Detail Panel Styling

The panel should feel consistent with Dungeon Daddy’s visual identity.

Recommended styling:

- Dark translucent background.
- Thin border using muted blue/gray.
- Selected room role accent color as a header line or small marker.
- Monospace or current UI font for labels.
- Clear section headers.
- No large blocks of tiny unreadable text.

The panel must not cover key rooms if avoidable. If the graph extends under it, it should be visually clear that the panel is UI overlay.

---

### Detail Panel Empty State

When no room is selected, show either no panel or a compact instruction panel.

If shown, empty state may include:

```text
GRAPH MODE
Select a room to inspect it.
Hover connections to inspect paths.
R recenter · Esc clear
```

---

## Role Markers and Icons

Do not depend on external image assets.

Use simple text markers or vector/geometric markers that can be drawn both in Arcade and in the PIL artifact renderer.

Suggested room markers:

| Role | Marker | Meaning |
|---|---|---|
| entrance | `IN` | Start / entry point |
| descent / stairs / elevator / transition | `↓` or `OUT` | Floor movement / transition |
| objective | `OBJ` | Objective / important point |
| boss | `BOSS` | Major encounter |
| hazard | `!` | Danger |
| key_room | `KEY` | Key / mechanism / control |
| treasure | `$` or `LOOT` | Reward / treasure |
| hub | `HUB` | Central routing node |
| corridor / hall | no marker or small line | Low priority passage |
| side_room | no marker | Optional support room |

Markers should be small and non-intrusive.

If a room has both role and priority, role marker wins.

---

## Connection Style Improvements

Phase 3 backfilled explicit connection metadata. Phase 4 should make those connection roles visually useful.

### Required connection roles

Support these connection role treatments:

| Connection Role | Visual Treatment |
|---|---|
| `critical_path` | Slightly brighter/thicker line by default; stronger when selected room is on path |
| `optional_branch` | Normal or slightly dimmer line |
| `locked` | Line with small gate/lock marker or label emphasis |
| `secret` | Dashed/faint line; brightens on hover/selection |
| `shortcut` | Dashed or angled style distinct from normal path |
| `vertical` | Small down/up marker, arrow, or stair marker |
| `normal` | Existing normal line |

Do not make all connections visually loud at once. Critical/locked/secret/vertical should be distinguishable, but the map should stay readable.

### Locked connections

Locked connections should be understandable at a glance.

Possible treatments:

- Small `LOCK` marker at midpoint.
- Tiny square/gate symbol across the line.
- Thicker label background.

### Secret / shortcut connections

Secret and shortcut connections should feel different from ordinary corridors.

Possible treatments:

- Dashed line.
- Lower default alpha.
- Brighten on hover/selection.
- Slightly warmer or stranger accent.

### Vertical connections

Vertical connections should indicate floor transition.

Possible treatments:

- `↓` or `↑` marker near the label.
- Slightly different line style.

---

## Atmospheric Treatment

Phase 4 should add a restrained atmosphere layer.

This should be subtle and optional/configurable.

### Goals

- Make Graph Mode feel like part of Dungeon Daddy.
- Add mood without reducing readability.
- Keep tests deterministic.

### Suggested atmosphere elements

- Slight vignette or darker outer background.
- Very subtle background grid/noise pattern.
- Thin frame around graph canvas.
- Soft accent glow around selected room.
- Slightly warmer/cooler fill colors based on room role.
- Optional faint “occult schematic” corner ticks or frame marks.

### Do not add

- Heavy animations.
- Random flicker in tests.
- Bright neon everywhere.
- Busy textures that reduce readability.
- External image dependencies.

Any procedural atmosphere must be deterministic for test artifacts.

---

## Configuration

Add or extend a configuration object for Graph Mode presentation.

Recommended name:

```python
GraphPresentationConfig
```

Possible fields:

```python
@dataclass
class GraphPresentationConfig:
    show_detail_panel: bool = True
    show_role_markers: bool = True
    show_connection_markers: bool = True
    enable_atmosphere: bool = True
    enable_hover_glow: bool = True
    enable_selection_glow: bool = True
    fade_unrelated_on_selection: bool = True
    detail_panel_position: str = "right"
```

Keep defaults enabled for Phase 4 artifact generation.

Tests should be able to disable presentation effects if needed.

---

## Architecture Guidance

### Preserve stable layout data

Do not mutate `LayoutResult` during hover, selection, panel rendering, or presentation styling.

Continue using the Phase 3 pattern:

- `LayoutResult` = stable layout geometry and semantic metadata.
- `GraphViewState` = camera/hover/selection state.
- Style resolver = derived render styling.
- Detail panel builder = derived panel data.

### Recommended additions

Possible modules:

```text
dungeon_daddy/map/dungeon_layout/graph_presentation_config.py
dungeon_daddy/map/dungeon_layout/detail_panel_renderer.py
dungeon_daddy/map/dungeon_layout/role_markers.py
dungeon_daddy/map/dungeon_layout/connection_markers.py
dungeon_daddy/map/dungeon_layout/atmosphere.py
```

Keep modules small and testable.

### Renderer integration

`LayoutRenderer` should orchestrate presentation rendering but should not contain large blocks of business logic.

Preferred flow:

```text
LayoutRenderer.draw(...)
  draw_atmosphere/background
  draw_connections
  draw_connection_markers
  draw_rooms
  draw_role_markers
  draw_labels
  draw_detail_panel if configured and selected
  draw_help/empty state if configured
```

The PIL artifact renderer should use the same presentation logic or equivalent shared style calculations.

---

## Test Requirements

All existing tests must continue passing.

Phase 4 must add tests for presentation behavior and detail panel rendering.

### Unit tests

Add or update tests for:

1. `GraphPresentationConfig`
   - defaults enabled
   - can disable detail panel
   - can disable atmosphere
   - can disable markers

2. Detail panel rendering/data formatting
   - selected room produces visible panel model
   - panel includes name, ID, role, connections, notes
   - long notes are wrapped or truncated safely
   - no raw JSON dump appears
   - empty state is available when no room selected, if implemented

3. Role markers
   - entrance marker resolves to `IN`
   - objective marker resolves to `OBJ`
   - boss marker resolves to `BOSS`
   - hazard marker resolves to `!`
   - key room marker resolves to `KEY`
   - transition/descent marker resolves correctly
   - unknown/side/corridor markers remain quiet

4. Connection markers
   - locked connection produces lock/gate marker
   - secret connection produces dashed/faint treatment
   - shortcut connection is distinct from normal
   - vertical connection produces transition marker
   - critical path connection is emphasized without overpowering

5. Style resolver improvements
   - hover state is stronger than default
   - selected state is stronger than hover
   - unrelated fade remains readable
   - selected room remains readable against atmosphere

6. Hit testing non-regression
   - room still wins over connection
   - hover state does not break selection state
   - Escape clears selection
   - R recenter still works

### Integration tests

Add integration tests for:

1. Graph Mode rendering with detail panel enabled.
2. Graph Mode rendering with selected room and detail panel.
3. Graph Mode rendering with hover and selection states.
4. Connection marker rendering for locked/secret/shortcut/vertical connections.
5. Grid Mode untouched / no grid renderer changes.
6. Phase 1 geometry invariants still pass.
7. Phase 2 semantic scores do not regress.
8. Phase 2.5 metadata scores do not regress.
9. Phase 3 interaction scores do not regress.

### Regression thresholds

Phase 4 should preserve:

- Geometry score: 100.0 for target fixtures.
- Metadata score: 100.0 for target fixtures.
- Interaction score: 100.0 for target fixtures, unless scoring rubric changes and the reason is documented.
- Semantic score should not regress materially.

If semantic score changes due only to scoring improvements, document it in the before/after summary.

---

## Required Assessment Artifacts

Generate all artifacts under:

```text
artifacts/layout/phase4/
```

Artifacts must be deterministic and suitable for visual review.

### Required screenshots

For each target fixture:

- `crucible_l1`
- `crucible_l2`
- `crucible_l3`
- `tomb_l1`

Generate:

1. Default overview state.
2. Hovered room state for at least one important room.
3. Hovered connection state for at least one authored special connection, where available.
4. Selected entrance room with detail panel visible.
5. Selected hub/objective/boss room with detail panel visible.
6. Selected endpoint/descent/transition room with detail panel visible.
7. Selected hazard room with detail panel visible, where available.

Specific screenshot recommendations:

#### Crucible L1

- `crucible_l1_default.png`
- `crucible_l1_hover_R2.png`
- `crucible_l1_hover_connection_R2_R4_locked.png`
- `crucible_l1_select_R1_detail.png`
- `crucible_l1_select_R2_detail.png`
- `crucible_l1_select_R4_detail.png`
- `crucible_l1_select_R5_detail.png`

#### Crucible L2

- `crucible_l2_default.png`
- `crucible_l2_hover_r02.png`
- `crucible_l2_hover_connection_r05_r06_vertical_or_critical.png`
- `crucible_l2_select_r01_detail.png`
- `crucible_l2_select_r02_detail.png`
- `crucible_l2_select_r03_detail.png`
- `crucible_l2_select_r05_detail.png`
- `crucible_l2_select_r06_detail.png`

#### Crucible L3

- `crucible_l3_default.png`
- `crucible_l3_hover_r7.png`
- `crucible_l3_hover_connection_r4_r5_secret.png`
- `crucible_l3_hover_connection_r7_r8_critical.png`
- `crucible_l3_select_r1_detail.png`
- `crucible_l3_select_r3_detail.png`
- `crucible_l3_select_r7_detail.png`
- `crucible_l3_select_r8_detail.png`

#### Tomb L1

- `tomb_l1_default.png`
- `tomb_l1_hover_1-C.png`
- `tomb_l1_hover_connection_1-C_1-E_shortcut.png`
- `tomb_l1_select_1-A_detail.png`
- `tomb_l1_select_1-B_detail.png`
- `tomb_l1_select_1-C_detail.png`
- `tomb_l1_select_1-E_detail.png`

### Required JSON reports

Produce one JSON report per fixture:

```text
crucible_l1.presentation_feedback.json
crucible_l2.presentation_feedback.json
crucible_l3.presentation_feedback.json
tomb_l1.presentation_feedback.json
```

Each report should include:

```json
{
  "fixture_name": "crucible_l1",
  "geometry_score": 100.0,
  "semantic_score": 78.0,
  "metadata_score": 100.0,
  "interaction_score": 100.0,
  "presentation_score": 0.0,
  "detail_panel_feedback": {
    "renders_when_room_selected": true,
    "empty_state_available": true,
    "contains_room_name": true,
    "contains_room_role": true,
    "contains_connected_rooms": true,
    "contains_graph_notes": true,
    "warnings": []
  },
  "marker_feedback": {
    "role_markers_applied": true,
    "connection_markers_applied": true,
    "locked_connection_marker_count": 0,
    "secret_connection_marker_count": 0,
    "shortcut_connection_marker_count": 0,
    "vertical_connection_marker_count": 0,
    "warnings": []
  },
  "atmosphere_feedback": {
    "enabled": true,
    "does_not_reduce_readability": true,
    "warnings": []
  },
  "hover_feedback": {
    "room_hover_visible": true,
    "connection_hover_visible": true,
    "warnings": []
  },
  "selection_feedback": {
    "selected_room_visible": true,
    "connected_rooms_visible": true,
    "unrelated_rooms_still_readable": true,
    "warnings": []
  },
  "warnings": []
}
```

### Required Markdown summaries

Generate:

```text
phase4_feedback_summary.md
before_after_summary.md
implementation_summary.md
```

#### `phase4_feedback_summary.md`

Include:

- Fixture table with Geometry, Semantic, Metadata, Interaction, Presentation scores.
- Screenshot count per fixture.
- Warning count per fixture.
- Human review checklist.

#### `before_after_summary.md`

Compare Phase 3 to Phase 4:

- Geometry score delta.
- Semantic score delta.
- Metadata score delta.
- Interaction score delta.
- Presentation score, new in Phase 4.
- Notes about hover visibility, selected state, detail panel rendering, connection markers, and atmosphere.

#### `implementation_summary.md`

Include:

- Modules added.
- Modules changed.
- Tests added.
- Commands run.
- Test result count.
- Generated artifacts list.
- Known limitations.
- Confirmation that Grid Mode was untouched.

---

## Human Review Checklist

Include this checklist in the generated Phase 4 summary:

- [ ] Does Graph Mode now feel more like a game UI than a debug schematic?
- [ ] Is the visible detail panel useful?
- [ ] Is the detail panel readable at normal window size?
- [ ] Does the detail panel avoid overwhelming the map?
- [ ] Is room hover now clearly visible?
- [ ] Is selected-room focus clearly visible?
- [ ] Are unrelated rooms faded enough but still readable?
- [ ] Are role markers helpful or too noisy?
- [ ] Are locked/secret/shortcut/vertical connections visually distinct?
- [ ] Does the atmosphere improve mood without hurting readability?
- [ ] Does Crucible L3 still read clearly as a linear progression toward boss/objective?
- [ ] Does Tomb L1 make the shortcut/hazard route readable?
- [ ] Does Graph Mode remain cleaner and more useful than Grid Mode for overview reading?
- [ ] Did Phase 4 introduce any visual clutter?

---

## Success Criteria

Phase 4 is successful if:

- [x] All existing tests pass.
- [x] New Phase 4 tests pass.
- [x] Grid Mode remains untouched.
- [x] Geometry does not regress.
- [x] Metadata and interaction scores do not regress.
- [x] A selected room visibly opens or updates a readable detail panel.
- [x] Hover and selected states are obvious in screenshots.
- [x] Special connection roles are visually distinguishable.
- [x] Graph Mode feels more like a game interface while remaining readable.
- [x] Required artifacts are produced under `artifacts/layout/phase4/`.

---

## Recommended Implementation Order

### Step 1 — Add presentation config

Create or extend a config object for detail panel, markers, hover glow, selection glow, and atmosphere toggles.

### Step 2 — Render visible detail panel

Use existing `build_room_detail` data.

Add unit tests before/with implementation.

### Step 3 — Strengthen hover and selection styling

Improve style resolver rather than hardcoding in renderer.

Update tests and screenshot artifacts.

### Step 4 — Add role markers

Implement small marker resolver and renderer.

Keep markers subtle.

### Step 5 — Add connection markers/styles

Use explicit `layout_connection_role` / `connection_style` metadata added in Phase 3.

Prioritize locked, secret, shortcut, vertical, and critical_path.

### Step 6 — Add restrained atmosphere layer

Keep deterministic and configurable.

Do not hurt readability.

### Step 7 — Generate artifacts

Generate all required screenshots and reports.

### Step 8 — Run full tests

Run full test suite and include results in implementation summary.

---

## Notes for Claude Code

Prefer incremental, testable changes.

Do not rewrite the layout engine.

Do not alter room coordinates to make styling easier.

Do not remove existing feedback fields. Add new Phase 4 feedback fields.

Keep all Phase 4 presentation effects additive and configurable.

When in doubt, favor readability over drama.

Dungeon Daddy can become atmospheric, but the map still has to help the player understand the dungeon.
