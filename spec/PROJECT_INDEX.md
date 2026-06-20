# Dungeon Daddy — Project Index

## Phase

Phase: **50 — Hybrid Action Model (BUILD — in progress)**
Status: On branch **`phase-50`** (not pushed). Slices **1–7 + 5.1 of 8** complete;
**Slice 8** (wire `VnaActionPanel` into PlayView, retire `how_chips`) next. Suite green (2941).

Spec: **`spec/PHASE_50_HYBRID_ACTION_MODEL.md`** (8-slice plan, no GitHub issue yet).
Roadmap: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (Phase 50 rows). Prior phase spec:
`spec/PHASE_49_STARTING_PLAYBOOKS.md` (GitHub issue **#77**).

Phase 50 commits (on top of pre-phase cleanup, all on `phase-50`):
- `da3c2b6` Slice 1 — verb provider + spec
- `48447a0` Slice 2 — noun provider + actor room-presence
- `0f99981` Slice 3 — adverb provider
- `9c3b65a` Slice 4 — `ActionCard` model + `validate_card`
- `68d7060` Slice 5 — Card → `PlayerCommand` resolution (`rpg/action_resolution.py`)
- `e9a339b` Slice 5.1 — noun `noun_id` now the full `object_id`/`item_id`
- `971f8ca` Slice 6 — Card → action roll resolution (`resolve_card_roll`)
- `40a72a3` Slice 7 — `VnaActionPanel` (VNA Card panel + dropdowns)

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

**START HERE → Phase 50 Slice 8 — wire `VnaActionPanel` into PlayView + retire `how_chips`.**
Swap the Slice 7 panel into the action surface and remove the provisional `how?` chip flow
once the panel covers its cases (movement must keep working).

Concrete pointers for Slice 8 (gathered this session — verify before relying):
- **Panel to wire:** `dungeon_daddy/ui/panels/vna_action_panel.py` (`VnaActionPanel`). It
  exposes `set_context(*, actor_abilities, room_context, actor, playbook_slug, world_flags,
  library=None)` (calls the Slice 1–3 providers, defaults each slot, computes adverbs for the
  default noun), `select_*` / `select_*_by_label` / `*_labels()` / `selected_*_label()` (the
  dropdown adapter — `UIDropdown` options are plain strings), `build_card()`, and `submit()`
  (validates via `validate_card`; on success fires `set_submit_callback(card)`, else stores
  `_last_error: CardError`). It already has `setup_widget(manager,x,y,w,h)` /
  `teardown_widget(manager)` / `draw(x,y,w,h)` matching the `_RpgSidePanel` convention
  (`play_view.py:185-213`), building 3 `UIDropdown`s + a SUBMIT button. **The Arcade widget
  build is unverified visually** — exercise it via the ui-test harness / a manual run and
  expect layout polish (the `draw()` label rows vs. dropdown y-offsets are approximate).
- **Submit → resolution:** on the `set_submit_callback`, route the `ActionCard` through Slice
  5 `resolve_card(...)` (mutation verbs → `PlayerCommand`) / Slice 6 `resolve_card_roll(...)`
  (skill verbs → roll). `resolve_card` returns `None` for skill verbs, so try it first then
  fall back to the roll path.
- **What to retire:** the `how?` chip strip — `dungeon_daddy/ui/how_chips.py`
  (`build_how_chips`), surfaced via `ExitListPanel.set_how_chips` and called from
  `PlayView._refresh_exits` (`views/play_view.py:983`/`:1010`). The current action UI being
  replaced: `dungeon_daddy/ui/panels/player_action_panel.py` (`PlayerActionPanel`, the
  `_TAB_ACTION` tab in `_RpgSidePanel`, `play_view.py:357`/`:189`/`:209`).
- **`set_context` inputs in PlayView:** `actor_abilities` from the live `actor_abilities`
  table; `room_context` from `build_room_context(...)` (already built in `_refresh_exits`);
  `actor` dict needs `actor_id`/`display_name`/`carried_items`; `playbook_slug` from the
  actor; `world_flags` mirror the `_refresh_exits` chip gates (`can_sense`/`one_way`/
  `ritual_connector`/`armed_trap`).

**Slice 7 done — `VnaActionPanel` (`40a72a3`).** New `dungeon_daddy/ui/panels/vna_action_panel.py`:
the Play-mode Verb·Noun·Adverb Card panel. Pure-logic core is unit-tested without Arcade
(`tests/unit/ui/panels/test_vna_action_panel.py`, 16 tests): `set_context` populates the
Slice 1–3 provider option sets and defaults each slot; `select_noun` **recomputes the adverb
pool** from the chosen noun's `target_type`; a label↔slug adapter feeds plain-string
`UIDropdown`s; `submit()` builds + validates an `ActionCard` (`validate_card`) and either fires
the submit callback or stores a `CardError` (out-of-bounds slot blocks dispatch — engine-bounded).
The Arcade `setup_widget`/`teardown_widget`/`draw` build (3 `UIDropdown`s + SUBMIT, matching the
`_RpgSidePanel` convention) ships in the same file but is **not yet visually verified** — Slice 8
wires it into PlayView and polishes layout. Suite green (2941).

**Slice 6 done (this session) — Card → action roll resolution.** Added
`resolve_card_roll(card, *, campaign_id, actor, momentum_spend=0, push_yourself=False,
intent=None, fixed=None) -> CardRoll` to `rpg/action_resolution.py` (the dual of
`resolve_card`): for a non-mutation verb it sizes the pool from the actor's rating
(`actor["actions"][verb]`) + the adverb's `dice:±N` flag deltas, calls the existing roller
**directly** (`rpg/actions.py::resolve_action`, per open question 2), and returns a
`CardRoll(resolution, side_effect_flags)` — outcome tier on `resolution`, the adverb's
non-dice `HOW_MODIFIER_FLAGS` as world-side-effects. Raises `ValueError` for a mutation verb
(move/pick-up/equip/activate). **Design note:** no shipping adverb encodes a `dice:±N` flag
yet (all current `HOW_MODIFIER_FLAGS` are world-side-effects), so the delta is 0 in
production today; `_split_adverb_flags` implements the convention so Phase 52 / `BALANCE_NOTES`
can add dice deltas with no rewiring. Unit tests (`tests/unit/rpg/test_action_resolution.py`:
pool from rating, side-effect pass-through, `dice:±N` delta via monkeypatch, momentum,
mutation-verb guard) + 1 e2e (`tests/integration/test_card_resolution_e2e.py`:
`fight` Card through real providers → `validate_card` → roll). Suite green (2921).

**Slice 5.1 done — noun id-scheme fix (slug → full id).** Closed the gap found while writing
the Slice 5 integration test: `_fetch_current_room` (`memory/context_bundle.py`) now includes
the full `object_id`/`item_id` on the `objects`/`loose_items` dicts, and `available_nouns`
(`rpg/action_options.py`) emits those as `noun_id` — `NounOption` gained a `slug` field for
display (objects/items only; npcs/monsters/exits already keyed on full ids). So
`PickUpItem`/`EquipItem`/`ActivateObject` now receive the id the engine expects.
**`carried_items`** also emits `item_id`, but nothing populates `actor["carried_items"]` in
production yet (consumed only by the provider; wired in Slice 7 UI). New e2e tests
(`tests/integration/test_card_resolution_e2e.py`) drive the real `ContextBundleBuilder →
available_nouns → validate_card → resolve_card → validate_command → apply_command` and assert
an item is actually picked up / an object actually transitions. Downstream check: no
production reader besides the noun provider touched those object/item dicts.

Open question 2 (roll entry point) is now **resolved**: Card resolution calls the roller
(`resolve_action`) **directly** — see the Slice 6 note above.

**Slice 5 done — `68d7060`:** new `rpg/action_resolution.py` with
`resolve_card(card, *, actor_id, trigger=None) -> PlayerCommand | None`:
`move`→`MoveParty(exit_id=noun_id, how=adverb)`, `pick-up`→`PickUpItem`, `equip`→`EquipItem`,
`activate`→`ActivateObject` (raises if no `trigger`); other verbs → `None` (Slice 6 path).
Verb-slug constants (`VERB_MOVE`/`VERB_PICK_UP`/`VERB_EQUIP`/`VERB_ACTIVATE`) live in
`action_options.py` as the single source of truth; `available_verbs` now also surfaces the
three interaction verbs (`kind="interaction"`) so those Cards are pickable. Integration test
drives the full grammar→engine chain on the move path.

**Slice 3 design note (carry forward):** `available_adverbs` is **self-contained in the
engine** — it mirrors the `ui/how_chips` surfacing logic but depends only on
`rpg.move_party.HOW_MODIFIER_FLAGS`, *not* on `ui/how_chips` (that would invert the rpg→ui
layering). `how_chips` is retired in Slice 8, so the small overlap is intentional and
temporary. World-flag gates: `stealthily`←`can_sense`, `deliberately`←`one_way`,
`reverently`←`ritual_connector`, `recklessly`←`armed_trap`. Signature adverbs are deduped
against the universal set.

Recently resolved (both 2026-06-20; kept for provenance — nothing open here now):
1. ~~**Tomb of the Forgotten King** save needs an exit-label re-write.~~ **Resolved 2026-06-20.**
   Verified the save's 36 `room_exits` already match the current seeder output exactly
   (`exit_type`/`label`/`status` all aligned — 0 diffs vs derived-from-`dungeon.json`), so the
   `--force` backfill is now a pure no-op here. The Crucible is likewise backfilled. *(Note: the
   `--dry-run` path ignores `--force` — seeder.py:593 only counts new-vs-existing — so a dry-run
   can never preview a force re-write; diff the DB against derived exits instead.)*
2. ~~**Optional self-heal extension** for stale labels on load.~~ **Resolved 2026-06-20 (`c028860`).**
   Added `refresh_exit_labels(repo, dungeon_path)` (`campaign/backfill.py`) + narrow
   `MemoryRepository.update_exit_label(exit_id, label, exit_type)`; wired into the save-load
   path (`window.py`) right after `backfill_exits_if_empty`. It re-derives each **existing**
   exit's `label`/`exit_type` from `dungeon.json` and updates only where they differ.
   **Deliberately never touches `status`** — that is live runtime state mutated by
   `discover_exit`/`unlock_exit`/`seal_exit`/`block_exit` (via `update_exit_status`), so a
   status refresh on load would clobber discovered/unlocked/sealed exits. Status corrections
   therefore remain the manual `--force` script's job. Tests:
   `tests/unit/campaign/test_backfill_exits.py` (corrects stale label, **preserves runtime
   status**, no-op when correct, never creates missing rows).

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
