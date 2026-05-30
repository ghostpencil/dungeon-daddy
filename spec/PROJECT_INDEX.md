# Dungeon Daddy — Project Index

## Phase

Phase: Phase 19 — Vector Map Layout Phase 1
Status: IN PROGRESS

849 unit/integration tests passing at phase start (excl. UI harness and 3 live-API tests).
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
| 8 | Validation tests + feedback reports | **Done** — `dungeon_layout/validation.py`, 17 tests |
| 9 | Debug overlay | Not Started |

## Next Session

Start **Step 9**: debug overlay.

- Spec: `spec/MAP_LAYOUT_PHASE_NEXT.md` (read Debug Overlay Requirements section)
- Read `spec/TESTING.md` then invoke TDD skill before writing tests
- Branch: `phase-19-vector-map-layout`
- Test count at session start: 962

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
