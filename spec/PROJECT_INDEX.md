# Dungeon Daddy — Project Index

## Phase

Phase: **50 — Hybrid Action Model (BUILD — in progress)**
Status: On branch **`phase-50`** (decision made: **build Phase 50 on top of** the 4 cleanup
commits — *not* PR'd separately). Slice 1 of 8 complete. Suite green (Slice-1 file: 3 passing;
full suite was **2870 passing** at phase start, 2026-06-20).

`phase-50` holds 4 *pre-phase cleanup* commits on top of `main` (`8599eb7`), **not pushed**,
then new Phase 50 work:
- `fa54b20` feat(load): self-heal empty `room_exits` on save load
- `9be98cd` test(play-view): fix stale `_load_player_actors` setup
- `21256ef` feat(play-view): surface Recklessly chip for armed-trap rooms
- `00fb1c8` docs(index): refresh PROJECT_INDEX
- `da3c2b6` feat(phase-50): action Card verb provider + spec (Slice 1)

Spec: **`spec/PHASE_50_HYBRID_ACTION_MODEL.md`** (authored this session; 8-slice plan, no
GitHub issue yet). Roadmap: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (Phase 50 rows).
Prior phase spec: `spec/PHASE_49_STARTING_PLAYBOOKS.md` (GitHub issue **#77**, label `phase-49`).

**Phase 48 locked decisions** (still relevant — Phase 50 reuses the `how?` contract):
- `MoveParty(exit_id, how)` is a **Player Command** in `rpg/command.py` (not a proposal).
- **No `party_location` column** — session uses `current_room_id` / `visited_rooms` /
  `current_level_idx` (`data/models.py:195-197`); the engine is their sole writer.
- No LLM proposal may set those session fields or exit `status` (except approval-gated `BlockExit`).
- `how?`/adverb = modifier flags (dice-pool deltas + world-side-effect flags; no position/effect axis).

---

## Phase 49 decisions Phase 50 depends on

Full detail: `spec/PHASE_49_STARTING_PLAYBOOKS.md` + git `94c5fcb`.
- Signature adverbs derived live from `playbook_slug` — not persisted per-actor.
- `actor_abilities` table (migration `011`) is the live, mutable set Phase 50 reads.

---

## Outstanding / Next session

**START HERE → Phase 50 Slice 2 — Noun provider.** In `dungeon_daddy/rpg/action_options.py`
add `available_nouns(room_context, actor) -> list[NounOption]`, each carrying `target_type`
(`npc/object/item/room/self/monster`). Sources: room objects, loose items, carried items,
NPCs/monsters, exits, plus synthetic `self` + `room`. Read the Phase 47/48 `current_room`
context block — no new query. Then Slice 3 (adverb provider), Slice 4 (Card model + validation),
Slice 5 (Card → PlayerCommand), Slice 6 (Card → action roll), Slice 7 (UI VNA dropdown panel —
per auto-memory `project_phase50_vna_dropdowns`), Slice 8 (wire into PlayView, retire `how_chips`).
Full slice plan + locked contracts table in **`spec/PHASE_50_HYBRID_ACTION_MODEL.md`**.

**Slice 1 — DONE (committed `da3c2b6`).** `dungeon_daddy/rpg/action_options.py`
`available_verbs(actor_abilities) -> list[VerbOption]`: 9 universal verbs (always,
`kind="universal"`, reads canonical `playbook._UNIVERSAL_VERBS`) + class verbs from
`ActorAbility` rows with `surfaces_as_verb=True` (`kind="class"`, label=`display_name`).
3 tests in `tests/unit/rpg/test_action_options.py`. Interface kept minimal — no room/playbook
gating yet (add when a test demands it).

Still open (not blocking Phase 50):
1. **Tomb of the Forgotten King** save needs an exit-label re-write — close the app, then
   `python -m tools.backfill_room_exits "<save dir>" --force` (rewrites `room_exits` labels/status).
   This `--force` re-write is **separate** from the on-load self-heal (which only fires for **empty**
   exit tables — both current saves already have 36 exits). The Crucible is already backfilled.
2. **Optional self-heal extension:** the on-load backfill only fills *empty* tables; it does not
   correct stale labels/status (that still needs the manual `--force` script). Could fold a
   label-refresh into load if it becomes a recurring pain.

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

None — full suite green (2026-06-20).

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Recent completed phases:

| Phase | Summary | Spec |
|---|---|---|
| 49 — Starting Playbooks | `Playbook` + nested models + `PlaybookLibrary`; `data/playbooks.json` (4 bundled playbooks, kit ability + first pool ability granted at start); `actor_abilities` table + repo CRUD; seed-publish wiring (ratings/tracks/kit/tags/abilities); playbook picker in Seed editor; Character Sheet panel playbook/adverbs/abilities sections | `spec/PHASE_49_STARTING_PLAYBOOKS.md` |
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
