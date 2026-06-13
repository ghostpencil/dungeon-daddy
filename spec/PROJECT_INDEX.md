# Dungeon Daddy — Project Index

## Phase

Phase: 42 — Campaign Authoring UI
Status: **NOT STARTED**

Branch: `phase-41-ai-campaign-drafting` (to be merged; next branch: `phase-42-campaign-authoring-ui`)

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is advisory. It may narrate, frame choices, interpret tone, and propose structured world reactions. It must not directly mutate authoritative state.

---

## Known Failures

None (test suite passes — 2266 tests as of 2026-06-13).

---

## Previous Phases

Phase 41 and earlier are complete. Full history in `spec/HISTORY.md`.

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
- `protagonist` actor is in `seed_data/campaigns/the-crucible/rpg_seed.json`; `--force` resets its stress tracks.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates and seeds cleanly).
