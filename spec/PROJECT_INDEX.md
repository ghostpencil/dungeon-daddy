# Dungeon Daddy — Project Index

## Phase

Phase: Phase 20 — Vector Map Layout Phase 2: Visual Hierarchy & Semantic Presentation
Status: **DONE** — All 10 steps complete. Phase 21 TBD.

Spec: `spec/MAP_LAYOUT_PHASE_2.md`

337 unit tests passing at Phase 19 close (excl. UI harness and live-API tests). mypy zero errors.
6 eval tests passing (run with `pytest -m eval` or `python tools/run_evals.py`).

Phase 20 session 1 (2026-05-30): Step 1 complete — 144 layout unit tests passing, 65 semantics tests (was 39).
Phase 20 session 2 (2026-05-30): Step 2 complete — `GraphRoomStyle` + `GraphRoomStyleResolver` in `dungeon_layout/room_style.py`, 11 new tests, 997 unit tests passing.
Phase 20 session 3 (2026-05-30): Step 3 complete — `GraphConnectionStyle` + `GraphConnectionStyleResolver` in `dungeon_layout/connection_style.py`, 11 new tests, 166 layout unit tests passing.
Phase 20 session 4 (2026-05-30): Step 4 complete — `EndpointEmphasisDetector` + `EndpointEmphasisResult` in `dungeon_layout/endpoint_emphasis.py`, 11 new tests, 1013 unit tests passing.
Phase 20 session 5 (2026-05-30): Step 5 complete — `CriticalPathPresenter` + `CriticalPathPresentationResult` in `dungeon_daddy/map/dungeon_layout/critical_path_style.py`, 5 new tests, 1024 unit tests passing.
Phase 20 session 6 (2026-05-30): Step 6 complete — `VisualHierarchyConfig` in `dungeon_daddy/map/dungeon_layout/visual_hierarchy_config.py`, 4 new tests, 186 layout unit tests passing.
Phase 20 session 7 (2026-05-30): Step 7 complete — `VisualHierarchyFeedbackReport` + `generate_visual_hierarchy_feedback` in `dungeon_layout/visual_hierarchy_feedback.py`, 10 new tests, 1032 unit tests passing, mypy zero errors.
Phase 20 session 8 (2026-05-30): Step 8 complete — `write_summary()` extended with `visual_reports` param, new table columns (Semantic Score, Geometry Score, Visual Warnings), `_human_review_checklist()` extended with 9 Phase 2 questions, 7 new tests, 1045 unit tests passing, mypy zero errors.
Phase 20 session 9 (2026-05-30): Step 9 complete — `LayoutResult` extended with `room_roles`, `edge_labels`, `critical_path` fields; `run_layout_pipeline` populates them; `LayoutRenderer` wires `GraphRoomStyleResolver`, `GraphConnectionStyleResolver`, `CriticalPathPresenter`, `VisualHierarchyConfig` — border weight, fill alpha, markers, and connection alpha now driven by semantic style, 7 new tests, 1109 unit tests passing, mypy zero errors.
Phase 20 session 10 (2026-05-30): Step 10 complete — `LayoutFeedbackReport.visual_hierarchy_feedback` field added; integration test generates and embeds visual hierarchy feedback + writes artifacts to `artifacts/layout/phase2/`; `tools/generate_layout_screenshots.py` (PIL renderer) produces 4 PNG screenshots; `implementation_summary.md` written; 2 new tests, 1097 unit+integration tests passing, mypy zero errors.

**Phase 20 complete — all 10 steps done.**

---

## Known Failures

_None._

---

## Phase 20 — Vector Map Layout Phase 2

Spec: `spec/MAP_LAYOUT_PHASE_2.md`

Add semantic visual hierarchy to Graph Mode: room role styling, connection type
language, endpoint emphasis, critical path presentation, and visual hierarchy
feedback artifacts. Phase 19 geometry and Grid Mode stay untouched.

### Progress

| Step | Task | Status |
|---|---|---|
| 1 | Expand room role vocabulary + name inference rules | **Done** — `dungeon_layout/semantics.py`, 65 tests (was 39) |
| 2 | `GraphRoomStyle` + `GraphRoomStyleResolver` | **Done** — `dungeon_layout/room_style.py`, 11 tests |
| 3 | `GraphConnectionStyle` + `GraphConnectionStyleResolver` | **Done** — `dungeon_layout/connection_style.py`, 11 tests |
| 4 | Endpoint emphasis detection + spacing check | **Done** — `dungeon_layout/endpoint_emphasis.py`, 11 tests |
| 5 | Critical path presentation flags + config toggle | **Done** — `dungeon_layout/critical_path_style.py`, 5 tests |
| 6 | `VisualHierarchyConfig` constants object | **Done** — `dungeon_layout/visual_hierarchy_config.py`, 4 tests |
| 7 | `visual_hierarchy_feedback` JSON section + new warning categories | **Done** — `dungeon_layout/visual_hierarchy_feedback.py`, 10 tests |
| 8 | Markdown summary update (semantic score, visual warnings) | **Done** — `dungeon_layout/validation.py`, 7 new tests |
| 9 | Wire styles into `LayoutRenderer` (border weight, fill, markers) | **Done** — `map/layout_renderer.py` + `dungeon_layout/__init__.py`, 7 tests |
| 10 | Artifact generation: screenshots + `implementation_summary.md` | **Done** — `artifacts/layout/phase2/`, `tools/generate_layout_screenshots.py`, 2 new tests |

---

## Phase 19 — Vector Map Layout Phase 1

Spec: `spec/MAP_LAYOUT_PHASE_NEXT.md`

Improving the dungeon map renderer from a generic node graph to a semantically-aware,
visually authored dungeon schematic. Rooms placed by role, connections routed orthogonally,
labels placed collision-aware, camera auto-fits on load.

### Progress

| Step | Task | Status |
|---|---|---|
| 1 | Geometry models | **Done** — `dungeon_layout/models.py`, 21 tests |
| 2 | Room role classification + template selection | **Done** — `dungeon_layout/semantics.py`, 39 tests |
| 3 | Critical-path-first seed layout | **Done** — `dungeon_layout/seed_layout.py`, 4 tests |
| 4 | Port generation | **Done** — `dungeon_layout/ports.py`, 7 tests |
| 5 | Obstacle-aware orthogonal routing | **Done** — `dungeon_layout/route_orthogonal.py`, 7 tests |
| 6 | Label placement | **Done** — `dungeon_layout/labels.py`, 6 tests |
| 7 | Camera auto-fit | **Done** — `dungeon_layout/camera_fit.py`, 6 tests |
| 8 | Validation tests + feedback reports | **Done** — `dungeon_layout/validation.py`, 17 unit tests + 13 integration tests |
| 9 | Debug overlay | **Done** — `dungeon_layout/debug_overlay.py` + `map/layout_debug_renderer.py`, 9 tests |
| W | Pipeline wiring into map panel | **Done** — `dungeon_layout/__init__.py`, `map/layout_renderer.py`, `map_panel.py`, 19 tests |
| 10 | Room name labels in Graph view | **Done** — `layout_renderer.py` + `room_names` on `LayoutResult`, 1 test |
| 11 | Room click + selection highlight | **Done** — `map_panel.py` hit-test + `LayoutRenderer` teal outline, 6 tests |
| B1 | Room label two-line fix | **Done** — `layout_renderer.py`: name + room ID on separate centred lines |
| B2 | Room click → Dungeon Chat | **Done** — `on_room_select` callback + `play_view._on_graph_room_select` |
| B3 | Connection click → Dungeon Chat | **Done** — edge hit-test + `on_connection_select` callback + `play_view._on_graph_connection_select` |

### Phase 19 closed (2026-05-30)

All 11 steps + wiring milestone + 3 post-close bug fixes done. 337 unit tests passing. mypy zero errors.

- Room labels: name on line 1, room ID on line 2, both centre-aligned (`multiline=True`)
- Room click/selection: teal outline + fires `on_room_select` → triggers DM describe in Dungeon Chat
- Connection click: polyline hit-test (8-unit tolerance) → fires `on_connection_select` → chat message
- `_point_near_segment` helper + `_EDGE_TOL` constant in `map_panel.py`

---

## Previous Milestone — Stable Release (2026-05-27)

All 10 improvement plan items (IP-1 through IP-9, MC-1) complete. Codebase is
lint-clean (`ruff`), fully type-checked (`mypy` zero errors, zero overrides),
and at 74% test coverage with a 70% CI gate.

_Full session history in `spec/HISTORY.md`._

---

## Notes

- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
- Improvement plan: `spec/IMPROVEMENT_PLAN.md`.
