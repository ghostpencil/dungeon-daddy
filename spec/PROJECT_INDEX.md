# Dungeon Daddy — Project Index

## Phase

Phase: **48 — Dungeon Navigation (IN PROGRESS)**
Status: Slice 10 complete — Play-mode UI. New `ui/how_chips.build_how_chips(*, max_sense, one_way, ritual_connector, armed_trap_clock)` (contextual chips, restricted to keys in `HOW_MODIFIER_FLAGS`); new `ui/panels/exit_list_panel.ExitListPanel` (display + `_layout()`/`handle_click` hit-testing → click-to-move via `set_move_callback`); new `ui/fog_of_war.fog_of_war_label` wired into `map/graph_renderer.py` (unvisited rooms show `?`, current always revealed). PlayView: new **EXITS** tab (`_TAB_EXITS=5`, `_TAB_DBG`→6) + `_refresh_exits()` + `_on_exit_move(exit_id, how)` → `apply_move_party` → narrate. 25 new tests. 2772 tests passing (2026-06-19). Slice 11 (party-presence gate) is all that remains.
Spec: `spec/PHASE_48_DUNGEON_NAVIGATION.md` (full 10-slice scope + folded-in Slice 11).

Previous: Phase 47 — Room Contents — COMPLETE (merged to `main`, PR #73, 2026-06-18). 2673 tests passing.

**Slice order** (full detail in the spec):
1. `RoomExit` + `RoomExitSeed` models; `room_exits` schema + migration `010_room_exits.sql`
2. Seed publish — derive exits from dungeon `connections`; seed overrides; repo CRUD
3. Exit-condition validator (item / object-state / clock / memory) → structured failure
4. `MoveParty(exit_id, how)` command — validate + apply (location, one-way seal, visited)
5. Post-move world reaction — `how?`/adverb → modifier flags
6. Level connector transition — `current_level_idx` update + `mark_level_items_inert` trigger
7. `DiscoverExit` — hidden-exit reveal + passive hint (`sense >= 2`)
8. `UnlockExit` / `SealExit` (engine-internal) + `BlockExit` (world-reaction proposal)
9. Room context bundle builder — exits + hint + fog-of-war + `resonance_point`
10. Play-mode UI — provisional exit-list panel + fog-of-war map (thin; replaced by Phase 50 Card)
11. Party-presence gate on `PickUpItem` / `ActivateObject` (folded-in Phase 47 deferral)

**Locked decisions** (reconciled from issue #74 + 2026-06-17 review — see spec for rationale):
- `MoveParty(exit_id, how)` is a **Player Command** in `rpg/command.py` (not a proposal); supersedes the old `MoveToRoom(actor_id, room_id)` working name.
- **No new `party_location` column** — session already has `current_room_id` / `visited_rooms` / `current_level_idx` (`data/models.py:195-197`); engine becomes their sole writer.
- No LLM proposal may set those session fields or exit `status` (except approval-gated `BlockExit`).
- `how?`/adverb = modifier flags (dice-pool deltas + world-side-effect flags; no position/effect axis) — the exact contract Phase 50 reuses across all verbs.

---

### Next session — Phase 48, Slice 11 (final slice)

Read `spec/TESTING.md` first, then invoke the TDD skill (per CLAUDE.md).

**Slice 11 — Party-presence gate (folded-in Phase 47 deferral)**

From the spec (`PHASE_48_DUNGEON_NAVIGATION.md`, locked decision #4):
- Additive check in the `PickUpItem` / `ActivateObject` validators (`command_validator.py`): reject when the acting actor's party location (`current_room_id`) ≠ the item's / object's `room_id`.
- Additive only — Phase 47 validators currently skip this check and must stay green.
- This completes Phase 48; after it, run the full suite and prepare the phase-close PR.

**Slice 10 — DONE** (provisional exit-list panel + click-to-move + fog-of-war map). Note: `armed_trap_clock` chip surfacing (`recklessly` for trap rooms) was left at default `False` — a minor throwaway-UI gap, the engine flag mapping exists if needed.

**Slice order** (full detail in the spec):
1. `RoomExit` + `RoomExitSeed` models; `room_exits` schema + migration `010_room_exits.sql`
2. Seed publish — derive exits from dungeon `connections`; seed overrides; repo CRUD
3. Exit-condition validator (item / object-state / clock / memory) → structured failure
4. `MoveParty(exit_id, how)` command — validate + apply (location, one-way seal, visited)
5. Post-move world reaction — `how?`/adverb → modifier flags
6. Level connector transition — `current_level_idx` update + `mark_level_items_inert` trigger
7. `DiscoverExit` — hidden-exit reveal + passive hint (`sense >= 2`)
8. `UnlockExit` / `SealExit` (engine-internal) + `BlockExit` (world-reaction proposal)
9. Room context bundle builder — exits + hint + fog-of-war + `resonance_point` ✅
10. Play-mode UI — provisional exit-list panel (labels, status indicators, `how?` row) + fog-of-war map treatment. Minimal; replaced by the Card in Phase 50.
11. Party-presence gate on `PickUpItem` / `ActivateObject` (folded-in Phase 47 deferral)

**Locked decisions** (reconciled from issue #74 + 2026-06-17 review — see spec for rationale):
- `MoveParty(exit_id, how)` is a **Player Command** in `rpg/command.py` (not a proposal); supersedes the old `MoveToRoom(actor_id, room_id)` working name.
- **No new `party_location` column** — session already has `current_room_id` / `visited_rooms` / `current_level_idx` (`data/models.py:195-197`); engine becomes their sole writer.
- No LLM proposal may set those session fields or exit `status` (except approval-gated `BlockExit`).
- `how?`/adverb = modifier flags (dice-pool deltas + world-side-effect flags; no position/effect axis) — the exact contract Phase 50 reuses across all verbs.

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

None — test suite passes (2737 tests as of 2026-06-18).

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Recent completed phases:

| Phase | Summary | Spec |
|---|---|---|
| 47 — Room Contents | Items in rooms + interactive objects (state-machine archetypes); `ActivateObject`/`PickUpItem`/`DropItem` commands; `current_room` context block; Campaign Seed editor UI | `spec/PHASE_47_ROOM_CONTENTS.md` |
| 46 — Inventory System | `Item`/`ItemFeature` models; class-kit/dungeon/gear commands; `compute_effective_ratings`; `mark_level_items_inert`; world-reaction item proposals; Character Sheet UI | issue #71 |
| 45 — Campaign Pipeline | Three on-disk libraries; publish pipeline; Library home screen; 4-pill navigation | `spec/PHASE_45_CAMPAIGN_PIPELINE.md` |
| 44 — Playtest Telemetry | `dungeon_daddy/reporting/`; `proposal.applied`/`proposal.rejected` events; `tools/playtest_report.py` | `spec/PHASE_44_PLAYTEST_TELEMETRY.md` |
| 43 — Faction System | `FactionManifest`, `FactionState` in DuckDB, `AdjustReputationChange`, faction reputations in `ContextBundle` | `spec/PHASE_42_ADDITION_FACTION_SYSTEM.md` |

Per-session implementation logs are in git history and the auto-memory (`project_phase_status.md`).

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: current/future in `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`; index at `spec/IMPLEMENTATION_PHASES.md`. Spec-loading rules and skills: `CLAUDE.md` (canonical).
- Roadmap for Phases 49–53 (planned): GitHub Projects `ghostpencil/dungeon-daddy` #1, mirrored in `IMPLEMENTATION_PHASES_33_ONWARDS.md`. Issue bodies hold per-phase detail + folded-in design resolutions; a `spec/PHASE_NN_*.md` is written when each phase starts.
- Phase 53 (Threat Behavior & Monster Reactions, planned): engine-bounded monster reactions, no enemy turn; bosses escalate via clock thresholds. Design: `spec/MONSTER_REACTION_DESIGN.md`.
- Playtest reports: `python -m tools.playtest_report <db_path> <campaign_id>` (requires `PYTHONPATH=.`).
- `protagonist` actor: `seed_data/campaigns/the-crucible/rpg_seed.json` (use `--seed-pack` + `--force` to reset). Generic `seed_campaign()` no longer creates a placeholder actor.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates + seeds cleanly).
- `proposal.applied` / `proposal.rejected` events: call sites must insert `result.rejection_events` into repo with the correct `campaign_id` after `validate_proposal()`.
