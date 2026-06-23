# Dungeon Daddy — Project Index

## Phase

Phase: **50 — Hybrid Action Model (BUILD — feature-complete, visual verify near done)**
Status: On branch **`phase-50`** (not pushed). All **8 slices (+5.1)** landed in code. Visual
verify **started 2026-06-22**; on-screen pass on **2026-06-23** confirmed the VNA dropdowns,
verb→noun filtering, and hybrid exit labels render, and surfaced a third round of fixes (the
**Study-narration + inventory** fixes below). Remaining: confirm the lock glyph + N/S orientation
on screen (low priority — both one-line swaps). Suite green (full unit run 2026-06-23).

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
- `f2d8fb1` Slice 8 — wire `VnaActionPanel` into PlayView + retire `how_chips`

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

## Phase 51 (planned) — "Use Noun on Noun" transitive grammar

Design pass done **2026-06-21** (memory: `project_phase51_use_on_grammar.md`). Extends the
Phase 50 VNA panel to transitive actions: give an item, use an item on an object/creature,
combine items. **Not started — gated behind Phase 50 visual verify (do not open until 50 closes).**

**Key finding — most of this already works at the engine layer:**
- **Key→door:** `RoomExit.requires_item_slug` + `exit_validator.py:14-20` already gate a
  `MoveParty` on a **held (not consumed)** key. Only gap: set that field on the R2→R4 lift
  exit — `tools/populate_crucible_level1.py` does **not** set it yet.
- **Use-item→object (guaranteed, e.g. fuse→Great Lift):** `ObjectTransition.requires_item_slug`
  + `command_validator.py:259-269` already gate `ActivateObject`. Gap: only the UI — `activate`
  is the deliberate Slice 8 gap (needs trigger selection).
- **Give:** `GiveItem(item_id, to_actor_id)` command already exists (`rpg/command.py:20`); needs
  a validator + the UI second-noun.

**Decision 1 — authority split = "roll for anything contested":** give / combine / key→door are
deterministic Player Commands; use-on-object routes to an action roll *if it could fail*;
use-on-creature / throw-at-monster are **always** an action roll (`resolve_card_roll` path) +
LLM-narrated reaction. (Consistent with the core authority rule below.)

**Decision 2 — contested signal = explicit flag on `ObjectTransition`:** add `contested: bool`
(+ optional `action_verb` naming the rating to roll). No inferring from trigger strings; engine
stays authoritative over success/fail.

**Decision 3 — free `look`/`examine` verb (no roll), decided 2026-06-23.** Surfaced from Phase 50
visual verify: studying the Warden's Notice Board forced a dice roll, which feels wrong for plain
reading. Resolution: add a **`look` verb** that resolves *read-only* — a **third route** in
`_on_vna_submit` alongside mutation-commands and skill-rolls (it is neither). It pulls the noun's
**authoritative `description`** and hands it to the LLM as ground truth to narrate; **no dice, no
state change**, works on any noun. `study` stays the **roll-based** verb that risks something but
can reveal *hidden* info (a secret/ward). This is the **complement** of Decision 2's `contested`
flag, not a replacement: `look` makes free info explicit/predictable; `contested` makes a normally
free action risky on a specific object. Chosen over the alternative (a per-object "study-needs-no-
roll" flag) because that left the same verb behaving two ways on hidden data — unpredictable to the
player — and gave no general "just glance at it" affordance. **Authority note:** the readable text
must be **seeded `description`** (it can gate puzzles, e.g. R1 journal → warden key), never
LLM-invented; the LLM narrates *from* it. The plumbing this rides on now exists post-Phase-50:
`build_room_noun_context` carries each object's `description`, and `dm_agent.build_prompt` renders a
`# Room Contents` block (added in the Phase 50 verify-fix that also named the noun in skill-roll
messages — see Phase 50 notes).

**Slice sketch:** (1) grammar `Verb–Noun–[Target]–Adverb`, Target dropdown only for transitive
verbs; (2) new `CombineItems` command + validators for Give/Combine; (3) `contested` flag on
`ObjectTransition`; (4) wire `activate` (closes the Slice 8 gap); (5) set `requires_item_slug`
on the R2→R4 lift exit so the Crucible demos the key/door + fuse/lift puzzle; (6) item-on-creature
+ consume/self ride the roll path; (7) `look` verb — free read-only route surfacing the noun's
`description` (Decision 3). Spec file `spec/PHASE_51_*.md` **not yet written**.

**Also missing from the original four cases** (fold into the spec): use-item→creature (vs give),
use-item→self/consume (`ConsumeItem` exists, no verb), and explicit consumption semantics
(keys held vs fuses/draughts consumed — `requires_item_slug` never consumes today).

---

## Outstanding / Next session

**START HERE → finish Phase 50 visual verification (on-screen pass).** All 8 slices + two
verify-fix rounds are in code; the suite is green. The user verifies the GUI themselves
(do **not** drive with computer-use). Launch `python -m dungeon_daddy`, open the RPG side
panel → **ACTION** tab, and confirm on screen:
1. The three dropdowns + SUBMIT render; selecting a **Noun** re-populates the **Adverb**
   dropdown. (Layout polish may still be needed — `draw()` label rows vs. dropdown y-offsets
   are approximate; `vna_action_panel.py`.)
2. **Verb filters Noun** (verify-fix 1): with **Move** selected the Noun list shows **only
   exits** (not objects/monsters/self/"This room"); `pick-up`→loose items, `equip`→carried,
   `activate`→objects.
3. **Move refreshes the panel** (verify-fix 2): after a move the Noun list shows the **new**
   room's exits, not the old room's.
4. **Exit labels** (verify-fix 1+2): same-type doors are disambiguated — `Door East` while
   unexplored, `Door -> <Room Name>` once visited; a locked door shows the **lock glyph**.
   - ⚠ **OPEN — confirm the lock glyph renders.** `LOCK_PREFIX` is U+1F512 (🔒), an *emoji*
     codepoint; Arcade/pyglet may render it as a box in the UI font (JetBrains Mono / Inter).
     If it doesn't render, swap the `LOCK_PREFIX` constant in `rpg/exit_labels.py` to a
     text marker (e.g. `" (locked)"` suffix) or a drawn icon beside the row. One-line change.
   - ⚠ **OPEN — confirm N/S orientation.** `compass_direction` assumes grid `+y` = south
     (north up). If North/South come out swapped in the Crucible, flip the two N/S branches
     in `rpg/exit_labels.py`. (Disambiguation is correct either way; only the name is wrong.)

**Study-narration + inventory fixes (2026-06-23, on `phase-50`).** Found during the on-screen
verify pass: studying the Warden's Notice Board rolled `study` but the LLM invented lore instead
of relaying the board's seeded text. Three layers of the same root cause — the object's
`description` never reached the DM — were fixed:
- **Noun named in the skill-roll message.** `_resolve_vna_roll` (`play_view.py`) sent the DM
  `"<actor> [STUDY] <adverb> — <outcome>"` with **no target**. Now resolves the noun's label via
  new `VnaActionPanel.noun_label_for(noun_id)` → `"<actor> [STUDY] Warden's Notice Board (quickly)
  — PARTIAL"`.
- **`# Room Contents` rendered in the DM prompt.** `dm_agent.build_prompt` ignored the bundle's
  `current_room`; it now lists each object's `display_name` + `description` so the DM narrates from
  ground truth, not confabulation.
- **Bundle actually populated.** The real bug: `_build_context_bundle` (`play_view.py`) built
  `ContextBundleBuilder` **without `current_room_id`**, so `current_room` came back `{}` and the
  block above never had data in live play. Now passes `self._state.current_room_id`.
- **Carried items surface as nouns.** `_refresh_vna_panel` hardcoded `carried_items=[]`; now pulls
  `get_items_by_actor(actor_id)`, so picked-up items appear in the **Equip** noun list.
- **Crucible seed:** Notice Board `description` sharpened to a concrete key clue (Warden Brakkus →
  "the lift-key stays at the watch-stall here in the market"); re-seeded 2026-06-23.
- Tests: `test_play_view_vna.py` (carried-item noun, noun-in-DM-message, `_build_context_bundle`
  populates `current_room`), `test_dm_agent_context_bundle.py` (room-object description rendered).
- **Still LLM-narrated** — a `study` partial/miss may still soften the clue; deterministic
  surfacing of read-text is the deferred **`look` verb** (Phase 51 Decision 3).

**Visual-verify fixes (2026-06-22, on `phase-50`):**
- **Verb→Noun filtering.** `NounOption` gained a `source` tag (exit/loose_item/carried_item/
  object/npc/monster/self/room) and `action_options.noun_sources_for_verb()` maps each mutation
  verb to its allowed sources (skill verbs → unrestricted). `VnaActionPanel` filters the Noun
  dropdown to the verb's sources, defaults the Noun to the first visible option, and rebuilds the
  Noun+Adverb dropdowns when the Verb changes (new `_visible_nouns`/`_reset_noun_for_verb`; verb
  `on_change` now rebuilds the widget like the noun handler).
- **Hybrid exit labels + hide undiscovered exits.** New pure module **`rpg/exit_labels.py`**:
  `compass_direction(from_room, to_room)` (grid centres, `+x`=E/`+y`=S) and
  `exit_noun_label(...)` → `Door <Direction>` unexplored, `Door -> <name>` once the destination
  is in `visited_rooms`, with a `LOCK_PREFIX` (🔒) prefix for `locked`/`blocked` exits (`one_way`
  excluded). Wired in `play_view._prepare_vna_exits` (called from `_refresh_vna_panel`), which
  also **drops hidden/sealed exits** via the new shared `PLAYER_KNOWN_EXIT_STATUSES` frozenset in
  `rpg/room_context.py` (= visible ∪ locked). Degrades gracefully when no dungeon is loaded
  (`_current_level_rooms` returns `({}, None)` → plain base label).
- **Refresh-after-move.** `_on_exit_move` now calls `_refresh_vna_panel()`; `_refresh_vna_panel`
  rebuilds the live ACTION dropdowns via new `_RpgSidePanel.refresh_action_widget()` (no-op
  unless ACTION is the active tab).
- Tests: `test_action_options.py` (source field + `noun_sources_for_verb`), `test_vna_action_panel.py`
  (`TestNounsFilteredByVerb`), new `test_exit_labels.py` (compass, hybrid label, lock marker),
  `test_play_view_vna.py` (hidden-exit exclusion, direction/visited-name labels, move-refresh).

Two **deliberate gaps** carried out of Slice 8 (decide in a follow-up, not bugs):
- **`activate` verb is not wired** — it needs a trigger-selection step the panel does not
  supply; `_on_vna_submit` posts a "not wired yet" system message instead of crashing
  (`views/play_view.py`). Wiring it means surfacing the object's available transition trigger.
- **Push-yourself / momentum-spend controls are gone from the action surface** — the VNA
  panel rolls with `push_yourself=False`/`momentum_spend=0`. Those sliders lived in the old
  `PlayerActionPanel` ACTION-tab UI the VNA panel replaced. (`PlayerActionPanel` is still the
  headless holder for the chat action-card flow, which also hardcodes 0/False.)

**Slice 8 done — `f2d8fb1` (wire `VnaActionPanel` + retire `how_chips`).** Wiring lives in
`views/play_view.py`:
- `_refresh_vna_panel()` (+ `_acting_actor`/`_room_world_flags`) assembles `set_context`
  inputs; the enriched room-noun block comes from new `build_room_noun_context(repo,
  campaign_id, room_id)` (`memory/context_bundle.py`; `_fetch_current_room` delegates to it).
- `_on_vna_submit(card)` routes via Slice 5 `resolve_card`: `move`→`_on_exit_move`;
  `pick-up`/`equip`→`_apply_vna_command` (validate+apply); skill verbs→`_resolve_vna_roll`
  (Slice 6 `resolve_card_roll` + the existing world-reaction/proposal/narration downstream).
- ACTION tab now hosts `self._rpg_vna` (`_RpgSidePanel`); submit callback wired in `__init__`;
  tab-click calls `_refresh_vna_panel()` **before** `set_active` builds the dropdowns.
- `how_chips` retired: `ui/how_chips.py` + test deleted; `ExitListPanel` is now read-only
  (chips/click-to-move/`set_move_callback` removed); `_refresh_exits` + the `_TAB_EXITS` click
  handler cleaned. Tests: `tests/unit/views/test_play_view_vna.py` (6: context populate,
  move/skill/pick-up submit routing, activate-warn).

_Note: if the panel opens with ACTION as the active tab at startup (not the default CHAR tab),
the dropdowns build before `_refresh_vna_panel` runs and show empty until re-clicked —
`_RpgSidePanel.setup` cannot call back into PlayView. Low-priority; default tab is CHAR._

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

None blocking — full suite green (2026-06-22, after the visual-verify fixes): 2963 passed.
`tests/evals/test_generator_evals.py::test_generator_level_passes_validation` is **flaky**
(non-deterministic LLM generator eval); it failed once in a full run and passed standalone on
re-run. Not related to the verify-fix work.

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
- Crucible Level 1 content: `tools/populate_crucible_level1.py` (re-run 2026-06-23) — idempotent upserts of 11 objects, 7 loose items, 4 monsters, 1 NPC into the live save (`%LOCALAPPDATA%\DungeonDaddy\saves\The Crucible\campaign.duckdb`; close app first). Every object/item carries a `description`; Notice Board (R2) holds the sharpened Brakkus key clue. Puzzle chain R1 journal → R2 lift-warden-key → R3 lift-fuse → R4 Great Lift. The R2→R4 lift exit's `requires_item_slug` is **not** set, so the key/door gate is inert until Phase 51 sets it.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates + seeds cleanly).
- `proposal.applied` / `proposal.rejected` events: call sites must insert `result.rejection_events` into repo with the correct `campaign_id` after `validate_proposal()`.
