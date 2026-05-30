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
| 2 | Room role classification + template selection | Not Started |
| 3 | Critical-path-first seed layout | Not Started |
| 4 | Port generation | Not Started |
| 5 | Obstacle-aware orthogonal routing | Not Started |
| 6 | Label placement | Not Started |
| 7 | Camera auto-fit | Not Started |
| 8 | Validation tests + feedback reports | Not Started |
| 9 | Debug overlay | Not Started |

## Next Session

Start **Step 2**: room role classification + template selection.

- New module: `dungeon_daddy/map/dungeon_layout/semantics.py`
- Test file: `tests/unit/map/layout/test_semantics.py`
- Read `spec/TESTING.md` then invoke TDD skill before writing tests
- Roles: `entrance`, `exit`, `hub`, `boss`, `objective`, `key_room`, `lock_room`, `treasure`, `hazard`, `secret`, `utility`, `corridor`, `side_room`, `transition`, `unknown`
- Templates: `linear`, `hub_spoke`, `branch_merge`, `lock_key`, `boss_endcap`, `loop`, `freeform`
- Explicit JSON metadata wins over inference; inference uses name/tag keywords + graph degree
- Branch: `phase-19-vector-map-layout`
- Test count at session start: 849

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
