# Dungeon Daddy — Project Index

## Phase

Phase: **49 — Starting Playbooks (IN PROGRESS — Slice 0 done)**
Status: On branch `phase-49`. Test suite green — **2810 passing** (2026-06-19).
Next: **Slice 1** — Playbook Pydantic schema (`rpg/playbook.py`). TDD per `spec/TESTING.md` + TDD skill.

Spec: `spec/PHASE_49_STARTING_PLAYBOOKS.md` (GitHub issue **#77**, label `phase-49`).
Prior phase spec: `spec/PHASE_48_DUNGEON_NAVIGATION.md` (full 10-slice scope + folded-in Slice 11).

**Phase 48 locked decisions** (still relevant — Phase 50 reuses the `how?` contract):
- `MoveParty(exit_id, how)` is a **Player Command** in `rpg/command.py` (not a proposal).
- **No `party_location` column** — session uses `current_room_id` / `visited_rooms` /
  `current_level_idx` (`data/models.py:195-197`); the engine is their sole writer.
- No LLM proposal may set those session fields or exit `status` (except approval-gated `BlockExit`).
- `how?`/adverb = modifier flags (dice-pool deltas + world-side-effect flags; no position/effect axis).

---

## This session (2026-06-19, Phase 49 Slice 0)

**Slice 0 COMPLETE** — party marker survives level-stepper browsing. Committed `975a771` on `phase-49`.

- **Root cause fixed:** `_on_level_change` (`play_view.py`) was writing `current_level_idx` and
  `current_room_id` directly, violating the Phase 48 sole-writer rule. Party location was wiped
  on every map browse.
- **Fix:** `_viewed_level_idx` (int, on `PlayView`) tracks which level is displayed. `_on_level_change`
  updates only `_viewed_level_idx`; party session fields are untouched. `MapPanel.load` accepts an
  optional `viewed_level_idx` param (defaults to `state.current_level_idx`); `draw` passes
  `party_room_id=None` when browsing a non-party level; `update_state` syncs the viewed level after
  a real `MoveParty`. DM history is no longer cleared on map browse.
- **Tests:** 7 new tests (`test_play_view_level_browse.py` × 4; `test_map_panel_party_marker.py` × 3
  new); 2 old tests corrected (were asserting the bug as expected behavior).

**Prior this day (already merged):** Phase 49 spec drafted + GitHub issue #77 created; party
marker uses position-marker icon tinted GOLD (PR #76); `game-icon-finder` skill added.

**Resolved decisions (settled 2026-06-19):**
- **R1** new `actor_abilities` table (legacy `abilities` table dormant — left untouched).
- **R2** new module `rpg/playbook.py` (`Playbook` + nested models + `PlaybookLibrary`).
- **R3** signature adverbs derived-live from `playbook_slug`, never persisted per-actor.
- **R4** PC stress capacity = **4**; ratings 0–3; `cost_type="momentum"` schema-only.

---

## Outstanding / Next session

1. **Slice 1 — Playbook Pydantic schema.** New `rpg/playbook.py` with `Playbook` + all nested
   models. Pure model tests (no I/O); validation rules: verb keys ∈ 9 universal verbs, ratings
   0–3, track keys ∈ `{body,composure,bonds,weird}`, `starting_abilities` slugs resolve within
   kit+pool, adverb `target_types` from controlled set. Read `spec/TESTING.md` + invoke TDD skill.
2. **Slice 2 — `PlaybookLibrary` + bundled JSON.** Loader + `data/playbooks.json` with the four
   playbooks (Fighter, Thief, Priest, Artificer). Parse + validate tests.
3. **Slices 3–6** — see `spec/PHASE_49_STARTING_PLAYBOOKS.md` slice plan.
4. **Tomb of the Forgotten King save needs the exit backfill** — close the app, then
   `python -m tools.backfill_room_exits "<save dir>" --force` (rewrites `room_exits`
   plus exit labels/status). The Crucible is already backfilled.
4. **Optional follow-up (own small slice):** a backfill-on-load step so pre-Phase-48
   campaigns self-heal without the script.
5. **Minor:** `armed_trap_clock` chip surfacing (`recklessly` for trap rooms) left at
   default `False` — throwaway-UI gap; engine flag mapping exists if needed.

Pre-Phase-48 campaigns: fog-of-war needs no migration (reads `visited_rooms`; old saves
look fully-revealed). The EXITS panel needs `room_exits`, which only seed at publish —
old saves need the backfill above.

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

None — full suite green (2803 tests as of 2026-06-19).

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Recent completed phases:

| Phase | Summary | Spec |
|---|---|---|
| 48 — Dungeon Navigation | `RoomExit` model + `room_exits` schema; `MoveParty` command; exit-condition validator; level transitions; `DiscoverExit`/`UnlockExit`/`SealExit`/`BlockExit`; room context bundle; Play-mode exit-list panel + fog-of-war map; party-presence gate on `PickUpItem`/`ActivateObject` | `spec/PHASE_48_DUNGEON_NAVIGATION.md` |
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
- Exit backfill (pre-Phase-48 campaigns): `python -m tools.backfill_room_exits ["<save dir>"] [--dry-run] [--force]`. Close the app first (DuckDB is single-writer). Saves live under `%LOCALAPPDATA%\DungeonDaddy\saves\<name>\`.
- UI icons: `dungeon_daddy/assets/ui/icons/` (white/transparent PNG + SVG source); attribution in `CREDITS.json`. Fetch new ones with the `game-icon-finder` skill.
- `protagonist` actor: `seed_data/campaigns/the-crucible/rpg_seed.json` (use `--seed-pack` + `--force` to reset). Generic `seed_campaign()` no longer creates a placeholder actor.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates + seeds cleanly).
- `proposal.applied` / `proposal.rejected` events: call sites must insert `result.rejection_events` into repo with the correct `campaign_id` after `validate_proposal()`.
