# Dungeon Daddy — Project Index

## Phase

Phase: Phase 19 — Vector Map Layout Phase 1
Status: **COMPLETE**

337 unit tests passing (excl. UI harness and live-API tests). mypy zero errors.
6 eval tests passing (run with `pytest -m eval` or `python tools/run_evals.py`).

---

## Known Failures

_None._

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
