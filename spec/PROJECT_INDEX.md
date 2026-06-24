# Dungeon Daddy — Project Index

## Phase

Phase **50 — Hybrid Action Model: COMPLETE & merged to `main`** (2026-06-23).
Phase **50.5 — Use Noun on Noun: COMPLETE & merged to `main`** (PR #81, 2026-06-24).
Phase **50.6 — Chat Action Cockpit: IN PROGRESS** — Slices 1–3 committed; Slice 4 implemented
(uncommitted) on branch `phase-50.6` (2026-06-24).

Specs: current/future phases in `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (index:
`spec/IMPLEMENTATION_PHASES.md`). Phase 50.5 spec: `spec/PHASE_50_5_USE_ON_GRAMMAR.md`.
Phase 50.6 spec: `spec/PHASE_50_6_CHAT_ACTION_COCKPIT.md`.

---

## START HERE next session — Phase 50.6, Slice 5

**First: commit Slice 4** (implemented but uncommitted — see Slice 4 entry below for the diff).
Then continue with Slice 5.

Spec is `spec/PHASE_50_6_CHAT_ACTION_COCKPIT.md` (read it; design decisions are locked in §3).
Phase 50.6 is a **BUILD add-on** (dynamic, like 50.5 — not on the 51–53 roadmap, no issue).
Goal: close the action loop in the left chat column — move the Action Builder out of the right
RPG panel into the chat, and turn the map room overlay into a clickable "Things Here" noun picker.

Mostly a relocation + re-skin: `VnaActionPanel`'s pure-logic core is reused verbatim; only the
Arcade widget layer is rebuilt, plus 3 new pure helpers. 11-slice TDD plan in spec §9.

**Work is on branch `phase-50.6`** (off `main`; not yet pushed/PR'd). Use the TDD skill
(read `spec/TESTING.md` first).

**Slot-widget decision (locked, 2026-06-24):** the in-chat builder's V/N/T/A slots are
**custom-drawn chips that open a popup list on click** — NOT a cycle picker, NOT native
`arcade.gui.UIDropdown` (re-affirms Phase 50 feedback; see auto-memory
`project_phase50_vna_dropdowns`). The right-panel ACTION tab is **kept alongside** the new
in-chat builder until Slice 9 retires it.

- **Slice 1 — DONE** (commit `e6b6a6e`): `verbs_for_noun` pure helper (inverse of
  `noun_sources_for_verb`) in `rpg/action_options.py` + 4 unit tests. Full rpg unit suite green.
- **Slice 2 — DONE** (commit `ef1193b`): `action_preview` pure helper + `ActionPreview`
  dataclass (spec §4.5) in `rpg/action_options.py` + 10 unit tests. `likely_roll`/`requires_roll`
  (skill/class verbs + use-on-creature roll; move/pick-up/equip/activate/give/combine/look +
  use-on-self deterministic), templated `risk` from live room threats, `memory_tags`. **§11
  resolved:** Memory line uses **canonical** `MEMORY_SYSTEM_SPEC` type names (event/fallout/
  location/dungeon_state/relationship), not the mockup's flavor words. Full rpg unit suite green.
- **Slice 3 — DONE** (commit `eb4a475`): `room_things` view-model + `RoomThings`/
  `ThingsSection`/`RoomThing` dataclasses (spec §5.2) in `rpg/action_options.py` + 13 unit
  tests. Groups `available_nouns` into ordered EXITS/OBJECTS/CREATURES/ITEMS; rows carry
  `(noun_id, label, glyph, status, status_color)`. status_color → existing `draw_chip` tokens
  (teal/ember/gold/default); objects get hazard glyph `⚠` when disturbed/armed; creatures
  prefer `disposition` over actor `status`; key-gated open exits read "locked"; items gold;
  synthetic self/room (+ ally party) dropped; empty sections omitted. Full rpg unit suite green.
- **Slice 4 — DONE (uncommitted; first widget slice):** Builder widget relocation (spec §4.1–4.3).
  New `dungeon_daddy/ui/panels/action_builder.py` → `InChatActionBuilder`, which **reuses
  `VnaActionPanel`'s Arcade-free logic core verbatim** (`*_labels()`/`select_*_by_label()`/
  `submit()`) and adds only a presentational layer: wrapped command sentence ("`<Actor>` will
  [VERB] the [NOUN] [ADVERB]"; transitive verbs grow a Target slot with connector "on the"/"to"),
  **custom-drawn slot chips that open a popup list on click** (popup-row click selects + closes;
  outside-click dismisses; action button calls `submit()`). 10 unit tests
  (`tests/unit/ui/panels/test_action_builder.py`): slots order, transitive target slot, popup
  open/select/dismiss, button-submits-valid-card, and a `draw()`-records-hit-rects test (mocks
  the draw primitives → guards draw/hit-test agreement headlessly). Wired in:
  `chat_panel.py` draws the builder band below the actor mini-card in play mode (band adds
  ~156px; `_builder_extra_h`/`set_action_builder`; routes `on_mouse_press`; popup drawn **last**
  so it overlays the card/messages), and `play_view.py` builds `InChatActionBuilder(self._rpg_vna)`
  so `_refresh_vna_panel()` feeds it and `submit()` routes through `_on_vna_submit`. ACTION tab
  kept alongside. Full UI+views unit suite green (935). **Caveats:** `ROLL` button label is a
  placeholder (Slice 6 makes it adaptive ROLL/DO/MOVE/LOOK via `action_preview`); band height not
  yet responsive/collapsible (Slice 11). **Not done:** ui-test-harness visual check — user
  verifies the GUI manually (`python -m dungeon_daddy` → Play mode, room loaded).
- **Slice 5 — NEXT:** Suggested-verbs row (spec §4.4) — quick-select chips below the sentence,
  **filtered by the selected noun** via the ready `verbs_for_noun` helper; clicking a chip sets
  the Verb slot (same as the verb popup); inapplicable verbs render disabled (`INK_4`), capped at
  ~5 by relevance. Add to `InChatActionBuilder` (chips + hit-testing) reusing the rect-list
  pattern; unit-test chip selection + disabled state.
- Then slices 6–11 (preview render + adaptive button, overlay, overlay→builder link, retire
  ACTION tab, SAY/ASK swap stub, polish + smoke test).

After 50.6: **Phase 51 — Talk to the Dungeon** (roadmap; 50.6 carves the SAY/ASK input seam).
Write `spec/PHASE_51_*.md` when starting.

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

**None.** Full unit/integration suite green. The previously-flaky generator eval is resolved
(`26e95a3`, 2026-06-23): evals are excluded from the default run (`addopts = "-m 'not eval'"` —
run with `pytest -m eval`), and `test_generator_level_passes_validation` now mirrors production's
3-retry regenerate-with-errors budget instead of asserting one-shot validity.

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Recent completed phases:

| Phase | Summary | Spec |
|---|---|---|
| 50.5 — Use Noun on Noun | Grammar → `Verb · Noun · [Target] · Adverb`; `TRANSITIVE_VERBS`; `CombineItems` + migrations `013`/`014`; `GiveItem` validator; `activate` wired; `look` verb; Target dropdown; key-unlock persists; fuse consumed; map level-refresh fix | `spec/PHASE_50_5_USE_ON_GRAMMAR.md` |
| 50 — Hybrid Action Model | Verb·Noun·Adverb action *Card* (input-dual of a proposal); `ActionCard` + `validate_card`; `resolve_card`/`resolve_card_roll` (`rpg/action_resolution.py`); `VnaActionPanel` wired into PlayView (retired `how_chips`); hybrid exit labels via 8-point layout-coord compass (`rpg/exit_labels.py`) | `spec/PHASE_50_HYBRID_ACTION_MODEL.md` (issue #80) |
| 49 — Starting Playbooks | `Playbook` + nested models + `PlaybookLibrary`; `data/playbooks.json` (4 bundled playbooks, kit ability + first pool ability granted at start); `actor_abilities` table + repo CRUD; seed-publish wiring (ratings/tracks/kit/tags/abilities); playbook picker in Seed editor; Character Sheet panel playbook/adverbs/abilities sections | `spec/PHASE_49_STARTING_PLAYBOOKS.md` (issue #77) |
| 48 — Dungeon Navigation | `RoomExit` model + `room_exits` schema; `MoveParty` command; exit-condition validator; level transitions; `DiscoverExit`/`UnlockExit`/`SealExit`/`BlockExit`; room context bundle; Play-mode exit-list panel + fog-of-war map; party-presence gate on `PickUpItem`/`ActivateObject` | `spec/PHASE_48_DUNGEON_NAVIGATION.md` |
| 47 — Room Contents | Items in rooms + interactive objects (state-machine archetypes); `ActivateObject`/`PickUpItem`/`DropItem` commands; `current_room` context block; Campaign Seed editor UI | `spec/PHASE_47_ROOM_CONTENTS.md` |
| 46 — Inventory System | `Item`/`ItemFeature` models; class-kit/dungeon/gear commands; `compute_effective_ratings`; `mark_level_items_inert`; world-reaction item proposals; Character Sheet UI | issue #71 |
| 45 — Campaign Pipeline | Three on-disk libraries; publish pipeline; Library home screen; 4-pill navigation | `spec/PHASE_45_CAMPAIGN_PIPELINE.md` |

Per-session implementation logs are in git history and the auto-memory (`project_phase_status.md`).

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: current/future in `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`; index at `spec/IMPLEMENTATION_PHASES.md`. Spec-loading rules and skills: `CLAUDE.md` (canonical).
- Roadmap for Phases 51–53 (planned): GitHub Projects `ghostpencil/dungeon-daddy` #1, mirrored in `IMPLEMENTATION_PHASES_33_ONWARDS.md`. Issue bodies hold per-phase detail; a `spec/PHASE_NN_*.md` is written when each phase starts. (Phase 50.5 is **not** on the roadmap and has no issue.)
- Phase 53 (Threat Behavior & Monster Reactions, planned): engine-bounded monster reactions, no enemy turn; bosses escalate via clock thresholds. Design: `spec/MONSTER_REACTION_DESIGN.md`.
- Evals: `pytest -m eval` (live API, paid, non-deterministic); baseline tooling `python tools/run_evals.py` (count-based comparison).
- Playtest reports: `python -m tools.playtest_report <db_path> <campaign_id>` (requires `PYTHONPATH=.`).
- Exit backfill (pre-Phase-48 campaigns): `python -m tools.backfill_room_exits ["<save dir>"] [--dry-run] [--force]`. Close the app first (DuckDB is single-writer). Saves live under `%LOCALAPPDATA%\DungeonDaddy\saves\<name>\`.
- UI icons: `dungeon_daddy/assets/ui/icons/` (white/transparent PNG + SVG source); attribution in `CREDITS.json`. Fetch new ones with the `game-icon-finder` skill.
- `protagonist` actor: `seed_data/campaigns/the-crucible/rpg_seed.json` (use `--seed-pack` + `--force` to reset). Generic `seed_campaign()` no longer creates a placeholder actor.
- Crucible Level 1 content: `tools/populate_crucible_level1.py` (re-run 2026-06-24) — idempotent upserts of 11 objects, 7 loose items, 4 monsters, 1 NPC, and 3 exits into the live save (`%LOCALAPPDATA%\DungeonDaddy\saves\The Crucible\campaign.duckdb`; close app first). Puzzle chain: R1 journal → R2 lift-warden-key → R2→R4 door (key-gated, permanently unlocked on use) → R3 lift-fuse → R4 Great Lift (fuse-gated, consumed on power-up) → Level 2 r01.
- Crucible Level 2 content: `tools/populate_crucible_level2.py` (run 2026-06-24) — Great Lift upper landing in r01 (`state=ready`) + open `r01→R4` vertical connector exit (return to Level 1). Re-run to reset.
- Level-crossing exits: `to_level_id` encodes the **0-based list index** of the target level (not the 1-based level ID used for data scoping). `"level:0"` = Level 1 (index 0), `"level:1"` = Level 2 (index 1). `connector_type` must be set for `apply_move_party` to honour `to_level_id`.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates + seeds cleanly).
- `proposal.applied` / `proposal.rejected` events: call sites must insert `result.rejection_events` into repo with the correct `campaign_id` after `validate_proposal()`.
