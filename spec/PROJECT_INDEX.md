# Dungeon Daddy — Project Index

## Phase

Phase: **49 — Starting Playbooks (SPEC DRAFTED — not started; no code yet)**
Status: On `main`. Test suite green — **2803 passing** (2026-06-19). Phase 48 COMPLETE (merged, PR #75).
Next: **Begin Phase 49 implementation** — start with **Slice 0** (party-marker level-browse bug fix), then the playbook slices.

Spec: `spec/PHASE_49_STARTING_PLAYBOOKS.md` (GitHub issue **#77**, label `phase-49`).
Prior phase spec: `spec/PHASE_48_DUNGEON_NAVIGATION.md` (full 10-slice scope + folded-in Slice 11).

**Phase 48 locked decisions** (still relevant — Phase 50 reuses the `how?` contract):
- `MoveParty(exit_id, how)` is a **Player Command** in `rpg/command.py` (not a proposal).
- **No `party_location` column** — session uses `current_room_id` / `visited_rooms` /
  `current_level_idx` (`data/models.py:195-197`); the engine is their sole writer.
- No LLM proposal may set those session fields or exit `status` (except approval-gated `BlockExit`).
- `how?`/adverb = modifier flags (dice-pool deltas + world-side-effect flags; no position/effect axis).

---

## This session (2026-06-19, Phase 49 planning)

**Phase 49 spec drafted + promoted to a GitHub issue. No code written.**
- `spec/PHASE_49_STARTING_PLAYBOOKS.md` — start-of-phase reconciliation spec (full scope,
  data model, seed/publish wiring, UI, 6-slice plan + Slice 0, resolved decisions, exit criteria).
- GitHub issue **#77** created (new `phase-49` label), body mirrors the spec.
- Sourced from Project #1 card; no prior Phase 49 issue existed (not a duplicate).

**Resolved decisions (the 4 open questions, settled this session):**
- **R1** new `actor_abilities` table (legacy `abilities` table is dormant — no Python reader/
  writer — left untouched, no destructive migration).
- **R2** new module `rpg/playbook.py` (`Playbook` + nested models + `PlaybookLibrary`).
- **R3** signature adverbs are **derived-live** from `playbook_slug`, never persisted per-actor;
  only abilities persist (Phase 52 mutates them).
- **R4** per `BALANCE_NOTES.md`: PC stress capacity = **4** (card's example `body:6` superseded);
  ratings 0–3; `cost_type="momentum"` schema-only (momentum still untracked).

**Slice 0 — folded-in bug fix (Phase 48 navigation, documented not built).**
- *Party-location marker lost when browsing levels.* The ▲▼ level-stepper `_on_level_change`
  (`play_view.py:1296`) writes the party's canonical fields directly
  (`current_level_idx = new_idx`, `current_room_id = None`), wiping party location and breaking
  the Phase 48 sole-writer invariant. The map then draws `party_room_id=None` (`map_panel.py:424`).
- *Fix:* add a view-only `viewed_level_idx` independent of `current_level_idx`; arrows change only
  the viewed level; draw the marker only when `viewed_level_idx == party_level_idx`; viewed level
  follows the party on real `MoveParty`/connector moves. May land on its own branch.

**Previously this day (already merged):** party marker uses the game-icons.net **position-marker**
icon tinted GOLD (PR #76); new global `game-icon-finder` skill. Arcade gotcha:
`draw_texture_rect(color=...)` needs an `arcade.types.Color`, not a raw RGB tuple — mocked unit
tests do not catch this.

---

## Outstanding / Next session

1. **Implement Phase 49** (issue #77, spec `spec/PHASE_49_STARTING_PLAYBOOKS.md`). Suggested
   order: **Slice 0** (party-marker level-browse bug) → Slices 1–4 (engine/data spine) →
   Slices 5–6 (UI). TDD per `spec/TESTING.md` + TDD skill. Create the `phase-49` branch.
2. **Uncommitted on `main`:** `spec/PHASE_49_STARTING_PLAYBOOKS.md` (new) + this `PROJECT_INDEX.md`
   edit. Commit on a branch (repo convention) before starting code.
3. **Tomb of the Forgotten King save needs the exit backfill** — close the app, then
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
