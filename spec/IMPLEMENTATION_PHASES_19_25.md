# Implementation Phases — 19 through 25 (Map Layout)

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

**Status: Complete** — 1184 unit+integration tests passing. Closed 2026-05-30.

Spec: `spec/MAP_LAYOUT_PHASE2.5.md`

Improved the semantic layer quality by backfilling explicit metadata into existing
dungeon fixtures and local dungeon files. Reduced `unknown` roles from 9 to 0,
fixed ambiguous endpoints (Crucible L2 Maintenance Tunnel, Crucible L3 Power Core
Chamber), and added explicit critical paths for all target floors. Graph Mode only
— Grid Mode untouched.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/map/dungeon_layout/semantics.py` (update) | `tests/unit/map/layout/test_semantics.py` |
| `dungeon_daddy/map/dungeon_layout/metadata_validator.py` (new) | `tests/unit/map/layout/test_metadata_validator.py` |
| `dungeon_daddy/map/dungeon_layout/metadata_quality_feedback.py` (new) | `tests/unit/map/layout/test_metadata_quality_feedback.py` |
| `dungeon_daddy/map/dungeon_layout/validation.py` (update) | `tests/unit/map/layout/test_validation.py` |
| `dungeon_daddy/data/models.py` (update) | `LayoutMetadata` dataclass added |
| `dungeon_daddy/map/dungeon_layout/endpoint_emphasis.py` (update) | explicit `endpoint_room_id` override |
| `dungeon_daddy/map/dungeon_layout/seed_layout.py` (update) | explicit critical path override |
| `dungeon_daddy/map/dungeon_layout/connection_style.py` (update) | explicit style / role override |
| `scripts/backfill_graph_metadata.py` (new) | dry-run + write modes, timestamped backups |
| `scripts/generate_layout_screenshots_phase25.py` (new) | Phase 2.5 PNG artifact generator |
| `tests/fixtures/crucible.json` (update) | backfill metadata — all 3 levels |
| `tests/fixtures/tomb.json` (update) | backfill metadata — all 3 levels |

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| 1 | Update semantic role resolution pipeline (explicit → floor-level → inference) | **Done** |
| 2 | Endpoint detection: explicit `endpoint_room_id` overrides role-priority detection | **Done** |
| 3 | Critical path: explicit `layout_metadata.critical_path` overrides inferred path | **Done** |
| 4 | Connection style: explicit `connection_style` / `layout_connection_role` override | **Done** |
| 5 | Metadata validator (`metadata_validator.py`) with warning output | **Done** |
| 6 | `metadata_quality_feedback` JSON section + updated summary report columns | **Done** |
| 7 | `scripts/backfill_graph_metadata.py` (dry-run / write / backup) | **Done** |
| 8 | Backfill `tests/fixtures/crucible.json` (L1, L2, L3) | **Done** |
| 9 | Backfill `tests/fixtures/tomb.json` (L1 + additional floors) | **Done** |
| 10 | Backfill local dungeon files (if directory exists) | **Done** |
| 11 | Unit + integration tests | **Done** |
| 12 | Artifact generation: screenshots, feedback JSON, reports | **Done** |

### Exit Criteria

- [x] Graph Mode still renders all target fixtures
- [x] Grid Mode remains untouched
- [x] Geometry score does not regress for target fixtures (100.0 for all)
- [x] Explicit entrance metadata for all known entrances in target fixtures
- [x] Explicit endpoint metadata for all known endpoints in target fixtures
- [x] Explicit critical path for target fixtures where design intent is known
- [x] `Maintenance Tunnel` (Crucible L2) no longer an unknown endpoint
- [x] `Power Core Chamber` (Crucible L3) is endpoint when explicit metadata says so
- [x] `Descent Chamber` (Tomb L1) explicitly treated as descent/endpoint
- [x] Semantic scores improve or stay the same for all target fixtures
- [x] Unknown role count decreases for target fixtures (9 → 0)
- [x] `metadata_quality_feedback` appears in JSON reports
- [x] Summary report includes metadata quality columns
- [x] Backfill script runs in dry-run mode
- [x] Backfill script creates timestamped backups before writing local files
- [x] Absent local dungeon directory: local dir was present and patched; report includes skipped files
- [x] Unit tests pass
- [x] Integration tests pass
- [x] mypy passes
- [x] Artifacts present under `artifacts/layout/phase2_5/`

---

## Phase 22 — Graph Mode Phase 3: Interaction Polish + Phase 2.5 Cleanup

**Status: Complete** — 1280 unit+integration tests passing. Closed 2026-05-31.

Spec: `spec/MAP_LAYOUT_PHASE_3.md`

Added interaction polish to Graph Mode: hover states, room selection, focus mode, connection hover, room detail panel, recenter/clear controls. Also included two Phase 2.5 follow-up items: objective warning naming refinement and connection metadata backfill for all target fixtures and local dungeon files. Grid Mode untouched.

### Entry Conditions

- Phase 21 complete ✓
- 1184 unit+integration tests passing ✓
- Spec: `spec/MAP_LAYOUT_PHASE_3.md`

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/map/dungeon_layout/graph_view_state.py` (new) | `tests/unit/map/layout/test_graph_view_state.py` |
| `dungeon_daddy/map/dungeon_layout/hit_test.py` (new) | `tests/unit/map/layout/test_hit_test.py` |
| `dungeon_daddy/map/dungeon_layout/room_detail_panel.py` (new) | `tests/unit/map/layout/test_room_detail_panel.py` |
| `dungeon_daddy/map/dungeon_layout/style_resolver.py` (new) | `tests/unit/map/layout/test_style_resolver.py` |
| `dungeon_daddy/map/dungeon_layout/validation.py` (update) | `tests/unit/map/layout/test_validation.py` |
| `dungeon_daddy/map/dungeon_layout/room_style.py` (update) | `tests/unit/map/layout/test_room_style.py` |
| `dungeon_daddy/map/layout_renderer.py` (update) | `tests/unit/map/test_layout_renderer.py` |
| `dungeon_daddy/ui/panels/map_panel.py` (update) | `tests/unit/map/test_map_panel_layout.py` |
| `dungeon_daddy/views/play_view.py` (update) | (mouse motion routing) |
| `dungeon_daddy/data/models.py` (update) | (graph_notes, visual_priority fields) |
| `scripts/backfill_graph_metadata.py` (update) | (connection_patches support) |
| `scripts/generate_phase3_graph_artifacts.py` (new) | (artifact generation — no unit test) |
| `tests/fixtures/crucible.json` (update) | (connection metadata backfill) |
| `tests/fixtures/tomb.json` (update) | (connection metadata backfill) |

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| P3-1 | Phase 2.5 cleanup: refine objective warning naming (`MISSING_ENDPOINT_ROLE`, `NO_QUEST_OBJECTIVE_ROLE`, `ENDPOINT_IS_TRANSITION_ONLY`) in `validation.py` | **Done** — 4 new tests; severity tiering added |
| P3-2 | Connection metadata backfill for crucible + tomb fixtures and local dungeon files; visual parity gaps (border color, fill color, marker position) | **Done** — `apply_connection_patch` added; 36 connections patched across 6 levels; `border_color`/`fill_color` on `GraphRoomStyle`; marker y fixed; 9 new tests |
| P3-3 | `GraphViewState` model: camera, selected room, hovered room, hovered connection | **Done** — `CameraState` + `GraphViewState`; 12 new tests |
| P3-4 | Room hit testing (point-in-rect) + connection hit testing (tolerance distance; room wins over connection) | **Done** — `hit_test.py`; 9 new tests |
| P3-5 | Style resolution pipeline: base → semantic role → critical path → focus/fade → hover → selected | **Done** — `style_resolver.py`; 8 new tests |
| P3-6 | Room hover visual state: border brightens/thickens; restores on mouse-out unless room is selected | **Done** — `view_state` wired into `LayoutRenderer.draw()`; 4 new tests |
| P3-7 | Room selection + focus mode: connected rooms highlight, unrelated rooms/connections fade | **Done** — `_connected_room_ids` helper; edge fading at 40% alpha; 3 new tests |
| P3-8 | Connection hover: brightens/thickens near segment; tolerance-based hit testing | **Done** — `alpha+60` + `line_width+0.5`; 3 new tests |
| P3-9 | Room detail panel: fixed panel showing name, ID, role, connections, notes | **Done** — `room_detail_panel.py`; 24 new tests |
| P3-10 | Critical path emphasis: stronger visual state when selected room is on the critical path | **Done** — `selected_on_critical_path` flag; `+40 border_alpha` + `+0.5 width`; 3 new tests |
| P3-11 | Keyboard controls: R = recenter/reset view; Escape = clear selection | **Done** — `handle_key_press` in `map_panel.py`; 6 new tests |
| P3-12 | Artifact generation script + screenshot artifacts under `artifacts/layout/phase3/` | **Done** — 31 artifacts generated; `map_panel.py` wired with `GraphViewState`; 5 new tests |
| P3-13 | Integration tests: geometry/semantic/metadata scores do not regress; interaction states render without exception | **Done** — 4 new integration tests; 1279 passing |
| P3-14 | Output artifacts: `interaction_feedback` JSON per fixture, `phase3_feedback_summary.md`, `before_after_summary.md`, `connection_metadata_migration_report.md`, `implementation_summary.md` | **Done** — all 6 artifact types present; 1280 passing |

### Exit Criteria

- [x] Grid Mode remains untouched
- [x] Graph Mode still passes all Phase 1 geometry invariants (score 100.0 for all fixtures)
- [x] Phase 2.5 semantic + metadata scores do not regress
- [x] Room hover changes visual state; restores on mouse-out
- [x] Room selection works; connected rooms and connections are highlighted
- [x] Unrelated rooms and connections fade in focus mode
- [x] Room detail panel shows metadata and connections for selected room
- [x] Recenter (R) and clear selection (Escape) keyboard controls work
- [x] Phase 2.5 warning naming refined (`MISSING_ENDPOINT_ROLE`, `NO_QUEST_OBJECTIVE_ROLE`, `ENDPOINT_IS_TRANSITION_ONLY`)
- [x] Connection metadata backfilled for crucible + tomb fixtures and local dungeon files
- [x] Required output artifacts generated under `artifacts/layout/phase3/`
- [x] `pytest tests/unit/` green (1280 passing)

---

## Phase 23 — Graph Mode Phase 4: Presentation, Detail Panel, and Dungeon Personality

**Status: Complete** — 1368 unit+integration tests passing. Closed 2026-06-01.

Spec: `spec/MAP_LAYOUT_PHASE_4.md`

Turn Graph Mode from a clean semantic schematic into a game-like dungeon interface. Build on Phase 3 without destabilising it. Grid Mode must remain untouched.

### Modules

| Module | Test File |
|---|---|
| `dungeon_daddy/map/dungeon_layout/graph_presentation_config.py` (new) | `tests/unit/map/layout/test_graph_presentation_config.py` |
| `dungeon_daddy/map/dungeon_layout/detail_panel_renderer.py` (new) | `tests/unit/map/layout/test_detail_panel_renderer.py` |
| `dungeon_daddy/map/dungeon_layout/role_markers.py` (new) | `tests/unit/map/layout/test_role_markers.py` |
| `dungeon_daddy/map/dungeon_layout/connection_markers.py` (new) | `tests/unit/map/layout/test_connection_markers.py` |
| `dungeon_daddy/map/dungeon_layout/atmosphere.py` (new) | `tests/unit/map/layout/test_atmosphere.py` |
| `dungeon_daddy/map/dungeon_layout/style_resolver.py` (update) | `tests/unit/map/layout/test_style_resolver.py` |
| `dungeon_daddy/map/layout_renderer.py` (update) | `tests/unit/map/test_layout_renderer.py` |
| `scripts/generate_phase4_graph_artifacts.py` (new) | (artifact generation — no unit test) |

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| P4-1 | `GraphPresentationConfig` dataclass with all toggles; defaults all enabled | **Done** |
| P4-2 | Visible detail panel rendered in Graph Mode using existing `build_room_detail` data | **Done** |
| P4-3 | Strengthen hover (border +1 px, brighter alpha, optional glow) and selected-room styling (border +2 px, second outline) | **Done** |
| P4-4 | Role markers: small text glyphs (`IN`, `OBJ`, `BOSS`, `!`, `KEY`, `↓`, `HUB`) drawn in room boxes | **Done** |
| P4-5 | Connection markers: `critical_path` (brighter/thicker), `locked` (lock marker), `secret`/`shortcut` (dashed/faint), `vertical` (arrow marker) | **Done** |
| P4-6 | Restrained atmosphere layer: vignette, subtle background, thin frame, deterministic and configurable | **Done** |
| P4-7 | Artifact generation script and all required screenshots + JSON reports under `artifacts/layout/phase4/` | **Done** |
| P4-8 | Integration tests: regression checks for geometry, semantic, metadata, interaction scores; Grid Mode untouched | **Done** |

### Exit Criteria

- [x] All existing tests continue to pass
- [x] New Phase 4 tests pass
- [x] Grid Mode remains untouched
- [x] Geometry score does not regress (100.0 for all target fixtures)
- [x] Metadata and interaction scores do not regress
- [x] A selected room visibly opens or updates a readable detail panel
- [x] Hover and selected states are obvious in generated PNG screenshots
- [x] Special connection roles (`locked`, `secret`, `shortcut`, `vertical`) are visually distinguishable
- [x] Role markers appear in room boxes and are non-intrusive
- [x] Atmosphere layer is present, deterministic, and does not reduce readability
- [x] `GraphPresentationConfig` can disable each presentation effect independently
- [x] Required artifacts generated under `artifacts/layout/phase4/`
- [x] `pytest tests/unit/` green (1368 passing)

---

## Phase 24 — Graph Mode Phase 4.1: Cleanup

**Status: Complete** — 1395 unit+integration tests passing. Closed 2026-06-02.

Spec: `spec/MAP_LAYOUT_PHASE_4_1.md`

Small cleanup pass on Phase 23 (Phase 4). No new features. No redesign. Grid Mode must remain untouched.

### Goals

1. Preserve improved Phase 4 visibility level.
2. Prevent the room detail panel from covering the selected room and its connected paths.
3. Improve framing for long linear floors (especially Crucible L3).
4. Fix Crucible L2 connection marker gaps.
5. Keep all Phase 1–4 guarantees intact.
6. Produce required artifacts for human review.

### Modules

| Module | Notes |
|---|---|
| `dungeon_daddy/map/dungeon_layout/detail_panel_renderer.py` (update) | Smart panel placement (Option A/B/C from spec) |
| `dungeon_daddy/map/dungeon_layout/validation.py` (update) | Visibility + panel-placement feedback fields |
| `dungeon_daddy/map/layout_renderer.py` (update) | Long-linear floor framing logic |
| `scripts/generate_phase4_1_graph_artifacts.py` (new) | Artifact generation — no unit test |
| `tests/unit/map/layout/` (update) | Detail panel placement, long-floor framing, Crucible L2 marker scoring, visibility feedback |

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| 4.1-1 | Detail panel placement: avoid covering selected room and connected paths | **Done** |
| 4.1-2 | Long linear floor framing: detect wide-vs-tall layout, improve padding / viewport bias | **Done** |
| 4.1-3 | Crucible L2 marker scoring: fix or justify non-penalized result | **Done** |
| 4.1-4 | Visibility feedback fields: add to presentation feedback JSON | **Done** |
| 4.1-5 | Artifact generation: screenshots + JSON feedback under `artifacts/layout/phase4_1/` | **Done** |
| 4.1-6 | Markdown summaries: `phase4_1_feedback_summary.md`, `before_after_summary.md`, `implementation_summary.md` | **Done** |

### Required Score Preservation

```
Geometry:      100.0 for all target fixtures
Metadata:      100.0 for all target fixtures
Interaction:   100.0 for all target fixtures
Presentation:  100.0 for crucible_l1, crucible_l3, tomb_l1
Presentation:  100.0 or justified non-penalized result for crucible_l2
```

### Target Fixtures

- `crucible_l1`, `crucible_l2`, `crucible_l3`, `tomb_l1`

### Exit Criteria

- [x] Grid Mode unchanged
- [x] All tests pass (1395 passing, up from 1368)
- [x] Detail panel does not cover selected room in target screenshots
- [x] Crucible L3 framing improved (wide-vs-tall detection + viewport bias)
- [x] Crucible L2 marker scoring fixed (zero marker-worthy connections; not penalized)
- [x] Map remains visibly readable and not overly dark
- [x] Required screenshots generated under `artifacts/layout/phase4_1/`
- [x] Required JSON feedback files generated
- [x] Required Markdown summaries generated

---

## Phase 25 — Map Visual Polish Phase 1: Background + Room Frame Assets

**Status: Complete** — 1410 unit+integration tests passing. Closed 2026-06-02.

Spec: `spec/MAP_VISUAL_POLISH_PHASE_1.md`

Add asset-backed visual polish to the Play Mode Graph map. No layout behavior changes. Grid Mode and Tiles Mode must remain untouched.

### Modules

| Module | Notes |
|---|---|
| `dungeon_daddy/ui/panels/map_panel.py` (update) | Background texture loading + draw |
| `dungeon_daddy/map/layout_renderer.py` (update) | Room frame texture loading + draw in `_draw_rooms` |

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| VP-1 | Asset loading infrastructure — safe load helper for background PNG + 6 frame PNGs; log-once on missing; path resolution from package root | Not Started |
| VP-2 | Background image — draw `background_graph_default.png` in `MapPanel`, Graph mode only, scissor-clipped, scaled to viewport, over solid `BG_0` fallback | Not Started |
| VP-3 | Room frame textures — load and draw centered 136Ã—96 frame PNGs in `LayoutRenderer._draw_rooms()`, scaled by zoom, after existing outlines, before label text | Not Started |
| VP-4 | Frame selection logic — `frame_current` > `frame_hover` > `frame_default`; stub hooks for memory/danger/locked | Not Started |
| VP-5 | Regression pass — Grid mode, Tiles mode, zoom/pan, hit testing, selection, detail panel, existing tests all green | Not Started |

### Asset Paths

```
dungeon_daddy/assets/ui/map/background_graph_default.png   (1780Ã—1584 px)
dungeon_daddy/assets/ui/map/room_frames/frame_default.png  (136Ã—96 px)
dungeon_daddy/assets/ui/map/room_frames/frame_current.png
dungeon_daddy/assets/ui/map/room_frames/frame_hover.png
dungeon_daddy/assets/ui/map/room_frames/frame_locked.png
dungeon_daddy/assets/ui/map/room_frames/frame_memory.png
dungeon_daddy/assets/ui/map/room_frames/frame_danger.png
```

### Exit Criteria

- [x] `background_graph_default.png` loaded once; drawn only in Graph mode filling the map viewport
- [x] Background is beneath atmosphere overlay, rooms, and edges
- [x] Missing background file: logs warning once, falls back to `BG_0`, no crash
- [x] Frame PNGs loaded once; each Graph room shows a centered 136Ã—96 frame scaled by zoom
- [x] `frame_current.png` used when `rect.room_id == selected_room_id`
- [x] `frame_hover.png` used when `rect.room_id == view_state.hovered_room_id` (current wins)
- [x] `frame_default.png` used for all other rooms
- [x] Missing frame assets: fall back to existing primitive rectangles, no crash
- [x] Hit testing, camera fitting, routing, detail panel, and selection unchanged
- [x] Grid Mode and Tiles Mode unaffected
- [x] `pytest tests/unit/` green (1410 passing)

---


