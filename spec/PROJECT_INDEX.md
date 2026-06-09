# Dungeon Daddy — Project Index

## Phase

Phase: 37.1 — RPG Intent and Consequence Stabilization
Status: **Not Started**

Branch: `phase-37-1-intent-stabilization` (to be created)

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

- [ ] 37.1.1 — Intent plumbing audit (`PlayerActionPanel`, `ActionRequest`, `ActionResolution`, `world_reaction`, `stress_routing`)
- [ ] 37.1.2 — Regression tests for intent preservation end-to-end
- [ ] 37.1.3 — Intent-sensitive stress routing tests (keyword precedence)
- [ ] 37.1.4 — Proposal application audit (LLM memory stays draft; deterministic consequences not duplicated)
- [ ] 37.1.5 — Debug tab visibility: distinguish deterministic reaction from LLM proposal result
- [ ] Smoke artifact `artifacts/play_mode/phase37_1/intent_consequence_summary.json`

---

## Known Failures

_None._

---

## Previous Phases

Phase 37 and earlier are complete. Full history in `spec/HISTORY.md`.

Last recorded test count: **1814 unit passing** (Phase 37, 2026-06-08).

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
