# Dungeon Daddy — Project Index

## Phase

Phase: 46 — Not yet defined
Status: **PENDING**

Previous: Phase 45 complete (2026-06-14). 2436 tests passing.
Spec: `spec/PHASE_45_CAMPAIGN_PIPELINE.md`

---

### Phase 45 — Campaign Pipeline (COMPLETE)
Spec: `spec/PHASE_45_CAMPAIGN_PIPELINE.md`
Branch: `phase-45-campaign-pipeline`

Three on-disk libraries (`dungeons/`, `campaign_seeds/`, `saves/`); publish pipeline
(Design → attach seed → publish → Play); Library home screen as startup/hub; one-time
migration of existing `campaigns/*`; post-phase removal of top-level menu bar (4-pill
navigation: Library / Design / Campaign / Play). 9 TDD slices, 2436 tests passing.

---

### Phase 44 — Playtest Telemetry and Balance Reports (COMPLETE)
Spec: `spec/PHASE_44_PLAYTEST_TELEMETRY.md`
Branch: `phase-44-playtest-telemetry` (merged into main 2026-06-13)

New `dungeon_daddy/reporting/` module with Pydantic models, aggregation queries, and
`build_report()`. Two new domain events: `proposal.applied` and `proposal.rejected`. CLI
tool `tools/playtest_report.py` prints formatted balance reports. 6 TDD slices, 33 new
tests. Post-phase stabilization: removed Grid/Tiles map modes, renamed Graph → Map,
repositioned RPG/Edit-Memory buttons to title bar, pruned low-value tests. 2393 tests.

---

### Phase 43 — Faction System (COMPLETE)
Spec: `spec/PHASE_42_ADDITION_FACTION_SYSTEM.md`
Branch: `phase-43-faction-system` (merged into main 2026-06-13)

New `FactionManifest` model (replaces `ActorManifest` for factions); named reputation
tiers (hostile/cold/neutral/warm/allied); `FactionState` persisted in DuckDB;
`AdjustReputationChange` in LLM proposal system; faction reputations included in
`ContextBundle`; faction-specific Campaign UI edit form and list cards. 7 TDD slices.

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks,
> consequences, and narration. The human player controls the player side: one or more
> player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is
advisory. It may narrate, frame choices, interpret tone, and propose structured world
reactions. It must not directly mutate authoritative state.

---

## Known Failures

None (test suite passes — 2436 tests as of 2026-06-14).

---

## Previous Phases

Phase 42 and earlier are complete. Full history in `spec/HISTORY.md`.

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
- `protagonist` actor is in `seed_data/campaigns/the-crucible/rpg_seed.json`; `--force` resets its stress tracks.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates and seeds cleanly; 2 memory seeds).
- `tools/seed_rpg_state.py`: `actor_type="faction"` entries routed to `repo.save_faction()`; faction clock `owner_actor_id` cleared.
- Live campaigns migrated (2026-06-13): `The Crucible` — `desert-djinn-fragment` moved from `actors` to `factions` table.
- Playtest reports: `python -m tools.playtest_report <db_path> <campaign_id>` (requires `PYTHONPATH=.`).
- `proposal.applied` / `proposal.rejected` events now emitted; call sites must insert `result.rejection_events` into repo with correct `campaign_id` after `validate_proposal()`.
