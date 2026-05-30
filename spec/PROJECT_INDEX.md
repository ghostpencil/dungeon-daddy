# Dungeon Daddy — Project Index

## Phase

Phase: Phase 19 — Vector Map Layout Phase 1
Status: **COMPLETE** (2026-05-30)

929 unit tests passing at phase end (excl. UI harness and 3 live-API tests). mypy zero errors.
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

## Phase 19 Complete

All 9 steps done. 929 unit tests passing (+ integration tests).

## Next Session

**Goal: Wire the dungeon_layout pipeline into the Arcade map panel (Graph view).**

The layout pipeline (Steps 1–9) is fully built and tested but not connected to the running app.
Everything lives in `dungeon_daddy/map/dungeon_layout/`. The map panel lives in
`dungeon_daddy/ui/panels/map_panel.py` and currently uses `GridRenderer` and `LoopOverlay`.

### What needs to happen

1. **Run the pipeline on level load** — when the Graph tab is active and a level loads,
   call the pipeline: `semantics → seed_layout → ports → route_orthogonal → labels → camera_fit`
   to produce `rooms`, `edges`, `labels`, `bounds`. Cache the result; don't recalculate every frame.

2. **Render the layout** — add a `LayoutRenderer` (new) that draws the pipeline output
   (room rects, routed polylines, label text) using Arcade, replacing or augmenting the
   current `GraphRenderer` when the Graph tab is active.

3. **Apply the camera fit** — use `LayoutBounds` from `camera_fit.py` to set the initial
   pan/zoom when a level loads in Graph view. Respect manual pan/zoom after that.

4. **Wire the debug overlay toggle** — add a keyboard shortcut (e.g. `D`) or button that
   sets `DebugOverlay.enabled` and calls `LayoutDebugRenderer.draw()` after the normal render.

### Key files to read at session start
- `dungeon_daddy/ui/panels/map_panel.py` — where rendering hooks go
- `dungeon_daddy/map/dungeon_layout/__init__.py` — pipeline entry point (currently empty)
- `dungeon_daddy/map/dungeon_layout/seed_layout.py` — main layout entry
- `dungeon_daddy/map/layout_debug_renderer.py` — debug overlay renderer (already built)
- `spec/ARCHITECTURE.md` — before adding new modules or changing state ownership
- `spec/TESTING.md` — before writing any new tests

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
