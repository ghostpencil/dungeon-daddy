# Dungeon Daddy — Project Index

## Phase

Phase: **49 — Starting Playbooks (COMPLETE — all 6 slices done)**
Status: On branch `phase-49`. Test suite green — **2867 passing** (2026-06-19).
Next: **Phase 50** — Action Model / verb-adverb picker. See `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`.

Spec: `spec/PHASE_49_STARTING_PLAYBOOKS.md` (GitHub issue **#77**, label `phase-49`).
Prior phase spec: `spec/PHASE_48_DUNGEON_NAVIGATION.md` (full 10-slice scope + folded-in Slice 11).

**Phase 48 locked decisions** (still relevant — Phase 50 reuses the `how?` contract):
- `MoveParty(exit_id, how)` is a **Player Command** in `rpg/command.py` (not a proposal).
- **No `party_location` column** — session uses `current_room_id` / `visited_rooms` /
  `current_level_idx` (`data/models.py:195-197`); the engine is their sole writer.
- No LLM proposal may set those session fields or exit `status` (except approval-gated `BlockExit`).
- `how?`/adverb = modifier flags (dice-pool deltas + world-side-effect flags; no position/effect axis).

---

## This session (2026-06-19, Phase 49 Slices 0–6)

**Slice 6 COMPLETE** — Character Sheet panel playbook section. `CharacterSheetPanel` gained `set_playbook(Playbook | None)` and `set_abilities(list[ActorAbility])` setters. `draw()` renders three new sections when an actor is loaded: **PLAYBOOK** (display name), **ADVERBS** (signature adverb slugs from the live playbook), **ABILITIES** (display name per `ActorAbility`). `import arcade` moved to module level (consistent with project pattern; enables mocker patching). 10 new tests (Cycles 43–50) in `tests/unit/ui/test_character_sheet_panel_playbook.py`.

**Slice 5 COMPLETE** — Character creation UI. Playbook picker (`< / >` cycle buttons) added to `CampaignEditPanel._build_actor_form`. Picking a playbook pre-populates action ratings and stress track capacities in `_number_values` via `_apply_playbook_to_form`. `_collect_actor_inputs()` (new method, dispatched from `_collect_inputs()`) derives `playbook_slug` from the choice picker — `None` when sentinel "none" is selected. Actor with existing `playbook_slug` pre-selects the picker and pre-fills ratings/tracks at build time. 12 new tests (Cycles 31–42) in `tests/unit/ui/test_campaign_edit_panel_playbook.py`.

**Slice 4 COMPLETE** — seed-publish wiring. `_seed_actor` applies playbook on create/force: writes `actors.playbook_slug` + `tags`, seeds action ratings + stress tracks (from playbook when manifest empty), seeds kit as `class_kit` Item via `_seed_item`, seeds `actor_abilities` rows (kit → `source="kit"`, pool in `starting_abilities` → `source="playbook_start"`). Idempotent + `--force` + dry-run. 9 new tests (Cycles 22–30) in `tests/unit/campaign/test_seeder_playbook.py`. Also: `ActorManifest.playbook_slug`, `ActorState.playbook_slug`, `repo.save_actor`/`get_actor` extended with `playbook_slug` + `tags`; migration 011 adds `actors.tags TEXT DEFAULT '[]'`.

**Slice 3 COMPLETE** — `actor_abilities` DB table + repo CRUD. 8 new tests (Cycles 14–21).

- **Migration `011_actor_abilities.sql`**: creates `actor_abilities` table (PK: `actor_id` + `ability_slug`; `target_types` stored as JSON); adds `actors.playbook_slug TEXT` column. Applies cleanly on fresh and existing DBs.
- **`ActorAbility` Pydantic model** added to `rpg/models.py` (mirrors table columns; `target_types: list[str]` deserialised from JSON on read).
- **Repo methods on `MemoryRepository`**: `save_actor_ability(ActorAbility)` (upsert), `get_actor_abilities(actor_id) -> list[ActorAbility]`, `delete_actor_ability(actor_id, slug)`. JSON roundtrip of `target_types` verified.
- Tests in `tests/unit/memory/test_repository.py` class `TestActorAbilities`.

**Slice 2 COMPLETE** — `PlaybookLibrary` + `data/playbooks.json`. 7 new tests (Cycles 9–13).

- **`PlaybookLibrary`** added to `rpg/playbook.py`: `__init__` loads `dungeon_daddy/data/playbooks.json` via `importlib.resources`, validates each entry as `Playbook`; `list() -> list[Playbook]`; `get(slug) -> Playbook` (raises `KeyError` for unknowns).
- **`data/playbooks.json`** — four bundled playbooks: Fighter (fight/endure ×2, move ×1; Combat Gear; recklessly/brutally/with-discipline), Thief (move/tinker ×2, sense ×1; Thieves' Tools; silently/deftly/unseen), Priest (channel/study ×2, focus ×1; Holy Kit; reverently/austerely), Artificer (tinker/focus ×2, study ×1; Workshop Kit; precisely/experimentally). Each has one kit ability as `starting_abilities` and one `ability_pool` entry.
- Uses same `importlib.resources.files("dungeon_daddy.data")` pattern as `loop_patterns.json`.

**Slice 1 COMPLETE** — Playbook Pydantic schema. New `dungeon_daddy/rpg/playbook.py` + 11 tests in `tests/unit/rpg/test_playbook.py`.

- **Models:** `PlaybookStressTrack`, `SignatureAdverb`, `PlaybookAbility`, `PlaybookKit`, `Playbook` (all in `rpg/playbook.py`).
- **Validation:** action keys ∈ 9 universal verbs; ratings 0–3; `track_key` ∈ `{body,composure,bonds,weird}`; `target_types` ∈ `{npc,object,item,room,self,monster}`; `starting_abilities` slugs resolve in kit ∪ pool; no duplicate slugs across kit + pool.
- **Pure model tests only** — no I/O, no DB. 11 tests written red-first.

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

1. ~~**Slice 1 — Playbook Pydantic schema.**~~ **DONE** — `rpg/playbook.py`, 11 tests green.
2. ~~**Slice 2 — `PlaybookLibrary` + bundled JSON.**~~ **DONE** — `data/playbooks.json`, `PlaybookLibrary`, 7 tests green.
3. ~~**Slice 3 — `actor_abilities` schema + repo CRUD.**~~ **DONE** — migration `011`, `ActorAbility` model, 3 repo methods, 8 tests green.
4. ~~**Slice 4 — Seed-publish wiring.**~~ **DONE** — 9 tests green.
5. ~~**Slice 5 — Character creation UI**~~ **DONE** — playbook picker in actor form, 12 tests green.
6. ~~**Slice 6 — Character Sheet panel**~~ **DONE** — playbook/adverbs/abilities sections, 10 tests green.
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

None — full suite green (2867 tests as of 2026-06-19).

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Recent completed phases:

| Phase | Summary | Spec |
|---|---|---|
| 49 — Starting Playbooks | `Playbook` + nested models + `PlaybookLibrary`; `data/playbooks.json` (4 bundled playbooks); `actor_abilities` table + repo CRUD; seed-publish wiring (ratings/tracks/kit/tags/abilities); playbook picker in Seed editor; Character Sheet panel playbook/adverbs/abilities sections | `spec/PHASE_49_STARTING_PLAYBOOKS.md` |
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
