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

## Phase 19 + Wiring Complete (2026-05-30)

All 9 pipeline steps done + pipeline wired into map panel. 948 unit tests passing. mypy zero errors.

### Wiring summary (this session)

| Item | Status | Files |
|---|---|---|
| Pipeline entry point (`LayoutResult` + `run_layout_pipeline`) | **Done** | `dungeon_layout/__init__.py`, 5 tests |
| `LayoutRenderer` (rooms, edges, labels via Arcade) | **Done** | `map/layout_renderer.py`, 5 tests |
| `MapPanel.load()` caches `LayoutResult` per level | **Done** | `map_panel.py` |
| `MapPanel` draws via `LayoutRenderer` on Graph tab | **Done** | `map_panel.py` |
| Camera fit (`_fit_layout_camera`) on Graph tab activate / load | **Done** | `map_panel.py`, 3 tests |
| `D` key toggles `DebugOverlay.enabled` | **Done** | `map_panel.py`, 3 tests |

## Next Session

The Graph view is now fully wired. Possible next steps:
- Visual polish: room name labels, role-coloured room fills, entrance/exit icons
- Room hover/click: clicking a room in Graph view selects it and shows its details
- Phase 20 (check `spec/IMPLEMENTATION_PHASES.md` for what comes after Phase 19)

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
