# Dungeon Daddy — Project Index

## Phase

Phase: 37.1 — RPG Intent and Consequence Stabilization
Status: **Complete** — all 37.1.1–37.1.5 done

Branch: `phase-37-1-intent-stabilization`

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is advisory. It may narrate, frame choices, interpret tone, and propose structured world reactions. It must not directly mutate authoritative state.

---

## Phase 37.1 — Planned Work

### Goal

Ensure player intent is faithfully carried from the UI through action resolution, world reaction, stress routing, proposal pipeline, and debug display.

Full spec: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` — search for "Phase 37.1".

### Tasks

- [x] 37.1.1 — Intent plumbing audit (`PlayerActionPanel`, `ActionRequest`, `ActionResolution`, `world_reaction`, `stress_routing`)
  - Fixed: `PlayerActionPanel._build_request()` was silently dropping `intent`; now passes `intent=intent` to `ActionRequest`
  - All other links in the chain were already correct
- [x] 37.1.2 — Regression tests for intent preservation end-to-end
  - Added `test_world_reaction.py`: `test_intent_routes_stress_when_no_clock_overrides`, `test_clock_category_wins_over_intent`
  - Added `tests/unit/views/test_play_view_intent.py`: live-style PlayView → ActionResolution intent threading (2 tests)
- [x] 37.1.3 — Intent-sensitive stress routing tests (keyword precedence)
  - Added 4 tests: study/ritual/dungeon/voice→weird, move/protect/ally/promise→bonds, tinker/fear/nightmare/truth→composure, clock-category-danger beats intent-ritual
- [x] 37.1.4 — Proposal application audit (LLM memory stays draft; deterministic consequences not duplicated)
  - Confirmed: `CreateMemoryChange` always saved with `status="draft"` (test added)
  - Fixed: `ApplyConsequenceChange` was being applied when track matched deterministic — now always skipped to prevent duplication
  - Fixed: `proposal_section_lines()` now surfaces skipped count and per-item `[SKIPPED]` lines
- [x] 37.1.5 — Debug tab visibility: distinguish deterministic reaction from LLM proposal result
  - Added `last_action_section_lines()`: actor, action, intent, dice, outcome
  - Rebuilt `reaction_section_lines()` from structured `clock_lines`/`stress_lines` with "Deterministic reaction" header
  - Added `parse_status` field to `ValidationResult`; surfaced in `proposal_section_lines()`
- [x] Smoke artifact `artifacts/play_mode/phase37_1/intent_consequence_summary.json`
- [x] Post-37.1 fixes (same session)
  - `play_view.py`: wired `last_action_section_lines()` into debug render; removed old inline `Last action: outcome` line; unified all four sections into one loop
  - `dm_system.txt`: added outcome interpretation block so DM narrates PARTIAL/MISS as complications, not clean successes

---

## Next Phase

**Phase 38 — Chat-Centered RPG Interaction Refactor**
Spec: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` — search for "Phase 38".
Goal: Move the primary player action loop from the right-side RPG panel into the Dungeon Chat experience.

---

## Known Failures

_None._

---

## Previous Phases

Phase 37.1 and earlier are complete. Full history in `spec/HISTORY.md`.

Last recorded test count: **1839 unit passing** (Phase 37.1 step 37.1.5, 2026-06-09).

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
