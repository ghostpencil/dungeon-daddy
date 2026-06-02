# Dungeon Daddy Graph Mode — Phase 4.1 Cleanup

**Status: Complete** — 1395 tests passing. Closed 2026-06-02.
Post-phase bug fix: atmosphere frame misalignment (`layout_renderer.py:_draw_atmosphere`).

## Purpose

Phase 4 successfully made Graph Mode feel more like a usable game interface by adding the visible room detail panel, stronger hover/selection treatment, role markers, connection markers, and atmospheric presentation.

After reviewing the Phase 4 screenshots in the live Dungeon Daddy UI, the next step is a small cleanup pass. This is **not** a new feature phase. Do not redesign Graph Mode. Do not add major new UI systems. The goal is to preserve the successful Phase 4 work while fixing the remaining usability issues.

## Scope

This cleanup applies only to **Graph Mode**.

Grid Mode must remain untouched. Grid Mode exists as the comparison baseline and should not receive Phase 4.1 behavior, styling, rendering, or layout changes.

## High-Level Goals

1. Preserve the improved Phase 4 visibility level.
2. Prevent the room detail panel from covering important map content when possible.
3. Improve framing for long linear floors, especially Crucible Level 3.
4. Fix any remaining connection marker gaps, especially Crucible Level 2.
5. Keep all Phase 1–4 guarantees intact.
6. Produce artifacts that make human review easy.

## Current Observations

The live Graph Mode screenshots show that the visibility improvements were worthwhile. The map is now much more readable than the first Phase 4 artifact screenshots. The UI has retained the intended dark-fantasy mood without burying room labels and connection labels.

However, several cleanup items remain:

- The detail panel can overlap map content.
- Long horizontal floors can still feel cramped or partially cut off.
- Crucible Level 2 previously scored lower on presentation because connection markers were not applied.
- The current brightness/readability level should be preserved and protected by tests or feedback artifacts.

## Non-Goals

Do **not** do the following in this phase:

- Do not redesign Graph Mode layout algorithms.
- Do not change Grid Mode.
- Do not add scene art, generated images, room thumbnails, or pixel art.
- Do not implement the memory module.
- Do not add animated effects.
- Do not introduce a large new UI framework.
- Do not remove the right-side/overlay detail panel unless replacing it with an equivalent tested panel behavior.
- Do not make the map darker again.

---

# 1. Preserve Improved Visibility

## Requirement

The post-Phase-4 visibility tuning must be preserved. The map should remain readable at normal Dungeon Daddy window size.

Room labels, role markers, room IDs, connection labels, and detail panel text should be readable without requiring the user to zoom in excessively.

## Guidance

Avoid overly aggressive vignette or fade values. Atmospheric effects should support mood but must not hide information.

The default Graph Mode should read as:

```text
Dark fantasy game UI, not debug schematic, but still readable.
```

It should not read as:

```text
Dark atmospheric screen where map information is buried.
```

## Acceptance Criteria

- Default Graph Mode screenshots remain visibly brighter than the original Phase 4 artifact screenshots.
- Room names are readable in default view for normal-sized rooms.
- Connection labels are readable when not deliberately faded.
- Detail panel text is readable.
- Selected room and hovered room states remain obvious.
- Unrelated rooms fade during selection, but remain identifiable.

## Tests / Feedback

Add or update presentation feedback checks to include:

```json
{
  "visibility_feedback": {
    "room_labels_readable": true,
    "connection_labels_readable": true,
    "detail_panel_text_readable": true,
    "atmosphere_not_too_dark": true,
    "unrelated_rooms_still_identifiable_when_faded": true
  }
}
```

This can be heuristic/code-level, but the generated screenshots are the real review artifact.

---

# 2. Detail Panel Placement Cleanup

## Problem

The Phase 4 detail panel is useful, but it can overlap rooms and connections. This is acceptable as a first pass, but it should now be improved.

## Requirement

The detail panel should avoid covering the selected room and its most important connected paths whenever reasonable.

## Preferred Behavior

Implement one of the following approaches, in order of preference:

### Option A — Docked Right Panel When Space Allows

If there is enough horizontal room, reserve or use a right-side panel area so the panel does not float over the map.

### Option B — Smart Floating Panel

If a docked panel is not feasible, keep the floating panel but choose a position that avoids:

- the selected room
- directly connected rooms
- highlighted connections
- critical-path segments near the selected room
- viewport edges

### Option C — Current Panel With Collision Avoidance

If full smart placement is too much for this cleanup, add simple collision avoidance:

1. Try preferred panel location.
2. Check against selected room rectangle and connected room rectangles.
3. If overlapping, try alternate positions:
   - right side
   - left side
   - below selected room
   - above selected room
4. Clamp to viewport.

## Panel Must Still Include

- Room name
- Room ID and role
- Critical path status
- Visual priority
- Optional branch status if available
- Connected rooms
- Connection labels and connection roles
- Graph notes

## Acceptance Criteria

- Selecting a room does not cover that selected room with the detail panel.
- Selecting a hub does not hide most of its immediate connections.
- Panel remains readable.
- Panel stays inside viewport bounds.
- Panel behavior works for Crucible L1, Crucible L2, Crucible L3, and Tomb L1.

## Tests / Feedback

Add detail-panel placement checks to the feedback JSON:

```json
{
  "detail_panel_placement_feedback": {
    "panel_inside_viewport": true,
    "panel_overlaps_selected_room": false,
    "panel_overlaps_connected_rooms": false,
    "panel_overlaps_highlighted_connections": false,
    "fallback_position_used": false,
    "warnings": []
  }
}
```

If avoiding all highlighted connections is not possible, it may be a warning rather than a failure. Overlapping the selected room should be treated as a failure.

---

# 3. Long Linear Floor Framing

## Problem

Crucible Level 3 is a long linear floor. It is readable, but it can feel horizontally cramped or partially cut off depending on window size and selected room.

## Requirement

Improve Graph Mode camera framing for long linear floors without breaking compact floors.

## Guidance

The renderer should detect when a graph is much wider than it is tall and apply framing behavior that keeps the linear route readable.

Possible approaches:

### A. Better Auto-Fit Padding

When the layout is very wide, increase horizontal padding and ensure both endpoints are visible if possible.

### B. Selected Room Recenter

When a room is selected on a long linear floor, gently center or bias the viewport toward the selected room while keeping the path context visible.

### C. Optional Mini Refit Mode

If auto-fit cannot show everything clearly, prioritize:

1. selected room
2. directly connected rooms
3. next/previous critical path rooms
4. endpoint direction

Do not zoom so far out that labels become unreadable.

## Acceptance Criteria

- Crucible L3 default view shows the linear progression more cleanly than before.
- Selecting `r1`, `r3`, `r7`, or `r8` keeps the selected room visible and readable.
- The detail panel does not hide the selected room.
- Long linear maps should not become so zoomed out that text becomes unreadable.
- Compact maps like Crucible L1 and Tomb L1 should not be harmed.

## Tests / Feedback

Add long-floor framing feedback:

```json
{
  "long_floor_framing_feedback": {
    "is_long_linear_floor": true,
    "default_view_endpoints_visible": true,
    "selected_room_visible": true,
    "selected_room_readable": true,
    "critical_path_context_visible": true,
    "labels_readable_after_fit": true,
    "warnings": []
  }
}
```

For non-linear floors, include:

```json
{
  "long_floor_framing_feedback": {
    "is_long_linear_floor": false
  }
}
```

---

# 4. Crucible L2 Connection Marker Cleanup

## Problem

Phase 4 feedback showed Crucible L2 had a lower presentation score because connection markers were not applied.

## Requirement

Fix marker detection/application for Crucible L2 connections where applicable.

At minimum, verify whether the following should show markers:

- vertical / transition / floor movement
- critical path
- hazard path
- special connection roles

Do not invent markers where the metadata does not justify them. If Crucible L2 legitimately has no marker-worthy connections, update the scoring logic so the fixture is not penalized incorrectly.

## Acceptance Criteria

One of the following must be true:

1. Crucible L2 connection markers are correctly applied and presentation score reaches 100, or
2. Crucible L2 is correctly determined to have no marker-worthy connections and the feedback explains why without penalizing the fixture.

## Tests / Feedback

Update Crucible L2 presentation feedback:

```json
{
  "marker_feedback": {
    "role_markers_applied": true,
    "connection_markers_applied": true,
    "marker_worthy_connections_detected": 1,
    "marker_worthy_connections_rendered": 1,
    "warnings": []
  }
}
```

Or, if no marker-worthy connections exist:

```json
{
  "marker_feedback": {
    "role_markers_applied": true,
    "connection_markers_applied": false,
    "marker_worthy_connections_detected": 0,
    "marker_worthy_connections_rendered": 0,
    "not_penalized_reason": "No marker-worthy connections in fixture metadata",
    "warnings": []
  }
}
```

---

# 5. Preserve Existing Guarantees

## Required Score Preservation

Phase 4.1 must not regress the prior scores.

Expected minimums:

```text
Geometry:      100.0 for all target fixtures
Metadata:      100.0 for all target fixtures
Interaction:   100.0 for all target fixtures
Presentation:  100.0 for crucible_l1, crucible_l3, tomb_l1
Presentation:  100.0 or justified non-penalized result for crucible_l2
```

Semantic scores do not need to increase in this phase, but they must not decrease.

## Target Fixtures

Run all relevant checks against:

- `crucible_l1`
- `crucible_l2`
- `crucible_l3`
- `tomb_l1`

If existing test fixtures include other levels from The Crucible and Tomb of the Forgotten King, run the non-screenshot automated checks against them too.

---

# 6. Required Artifacts

Generate artifacts under:

```text
artifacts/layout/phase4_1/
```

Use this exact folder unless the project already has a naming convention that requires a variant.

## Required Screenshots

For each target fixture, generate:

### Crucible L1

- `crucible_l1_default.png`
- `crucible_l1_select_R1_detail.png`
- `crucible_l1_select_R2_detail.png`
- `crucible_l1_select_R4_detail.png`
- `crucible_l1_select_R5_detail.png`

### Crucible L2

- `crucible_l2_default.png`
- `crucible_l2_hover_r02.png`
- `crucible_l2_hover_connection_marker_candidate.png`
- `crucible_l2_select_r01_detail.png`
- `crucible_l2_select_r02_detail.png`
- `crucible_l2_select_r03_detail.png`
- `crucible_l2_select_r05_detail.png`
- `crucible_l2_select_r06_detail.png`

### Crucible L3

- `crucible_l3_default.png`
- `crucible_l3_select_r1_detail.png`
- `crucible_l3_select_r3_detail.png`
- `crucible_l3_select_r7_detail.png`
- `crucible_l3_select_r8_detail.png`

### Tomb L1

- `tomb_l1_default.png`
- `tomb_l1_hover_1-C.png`
- `tomb_l1_hover_connection_1-C_1-E_shortcut.png`
- `tomb_l1_select_1-A_detail.png`
- `tomb_l1_select_1-B_detail.png`
- `tomb_l1_select_1-C_detail.png`
- `tomb_l1_select_1-E_detail.png`

## Required JSON Feedback

Generate:

- `crucible_l1.presentation_feedback.json`
- `crucible_l2.presentation_feedback.json`
- `crucible_l3.presentation_feedback.json`
- `tomb_l1.presentation_feedback.json`

Each JSON file should include:

```json
{
  "fixture_name": "...",
  "geometry_score": 100.0,
  "semantic_score": 0.0,
  "metadata_score": 100.0,
  "interaction_score": 100.0,
  "presentation_score": 100.0,
  "visibility_feedback": {},
  "detail_panel_feedback": {},
  "detail_panel_placement_feedback": {},
  "marker_feedback": {},
  "atmosphere_feedback": {},
  "hover_feedback": {},
  "selection_feedback": {},
  "long_floor_framing_feedback": {},
  "warnings": []
}
```

Use actual semantic scores from the current pipeline.

## Required Markdown Summaries

Generate:

- `phase4_1_feedback_summary.md`
- `before_after_summary.md`
- `implementation_summary.md`

### `phase4_1_feedback_summary.md`

Include:

- score table
- screenshot count
- warning count
- Crucible L2 marker status
- long linear floor status for Crucible L3
- detail panel overlap status
- human review checklist

### `before_after_summary.md`

Compare Phase 4 to Phase 4.1:

- visibility/readability changes
- detail panel placement changes
- Crucible L2 marker changes
- Crucible L3 framing changes
- any regressions

### `implementation_summary.md`

Include:

- files changed
- modules changed
- tests added/updated
- exact test command run
- full test count
- known limitations
- confirmation that Grid Mode was not modified

---

# 7. Human Review Checklist

Add this checklist to `phase4_1_feedback_summary.md`:

```markdown
## Human Review Checklist

- [ ] Is the map readable at normal window size?
- [ ] Did Phase 4.1 preserve the improved brightness from the live UI screenshots?
- [ ] Does the atmosphere still improve mood without making the map too dark?
- [ ] Does the detail panel avoid covering the selected room?
- [ ] Does the detail panel avoid hiding important connected paths when possible?
- [ ] Is Crucible L2 connection marker behavior correct?
- [ ] Does Crucible L3 frame better as a long linear floor?
- [ ] Are selected rooms immediately obvious?
- [ ] Are hovered rooms and hovered connections obvious enough?
- [ ] Are unrelated faded rooms still readable enough?
- [ ] Did this cleanup avoid adding new visual clutter?
- [ ] Does Graph Mode still feel cleaner and more useful than Grid Mode for overview reading?
```

---

# 8. Testing Guidance

Run the full test suite unless the project has a documented faster workflow for layout-only changes.

At minimum, run:

```bash
pytest
```

Also run any existing artifact generation command for Phase 4/Phase 4.1 screenshots.

If screenshot generation is script-based, update the script to support `phase4_1` output without overwriting Phase 4 artifacts.

## Test Expectations

- All existing tests must pass.
- New tests should cover detail panel placement logic.
- New tests should cover long linear floor framing detection/behavior.
- New tests should cover Crucible L2 marker scoring logic.
- New tests should cover visibility feedback fields.

---

# 9. Completion Criteria

Phase 4.1 is complete when:

1. Grid Mode is unchanged.
2. All tests pass.
3. Required screenshots are generated.
4. Required JSON feedback files are generated.
5. Required Markdown summaries are generated.
6. Detail panel no longer covers the selected room in target screenshots.
7. Crucible L3 is better framed or documented with clear limitations.
8. Crucible L2 marker scoring is fixed or justified.
9. The map remains visibly readable and not overly dark.

