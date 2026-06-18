# Dungeon Daddy — Project Index

## Phase

Phase: **47 — Room Contents (COMPLETE)**
Status: All 9 slices done + post-slice UI fixes (3 rounds). Branch `phase-47-items-in-rooms`. 2673 tests passing.
Spec: `spec/PHASE_47_ROOM_CONTENTS.md` (GitHub issue [#72](https://github.com/ghostpencil/dungeon-daddy/issues/72)).

Previous: Phase 46 complete (2026-06-17). Branch `phase-46-inventory-system`.
Next phase: **Phase 48 — Dungeon Navigation**.

---

### Next session — start Phase 48

**Step 0 — Close Phase 47.**
Open a PR for `phase-47-items-in-rooms → main` and merge it. All 2673 tests pass; no known failures.

**Step 1 — Branch.**
```
git checkout main && git pull
git checkout -b phase-48-dungeon-navigation
```

**Step 2 — Promote GitHub issue.**
On GitHub Projects #1 promote the Phase 48 draft card → real issue, apply label `phase-48`.

**Step 3 — Write the spec.**
Create `spec/PHASE_48_DUNGEON_NAVIGATION.md`. Reconcile the GitHub issue body with the 2026-06-17 design review notes below.

**What Phase 48 must deliver** (from `IMPLEMENTATION_PHASES_33_ONWARDS.md` + Phase 47 out-of-scope list):

- **`MoveToRoom` Player Command** — `actor_id`, `room_id`. Engine-authoritative; validates that `room_id` is reachable from the party's current room (an exit/connection exists in the dungeon data). Applies: update `party_location` in repo, emit `party.moved`.
- **Party location state** — `party_location: str | None` persisted in the campaign repo (new DB column or table). `set_party_location()` / `get_party_location()` helpers.
- **Party-presence gate** — `PickUpItem` and `ActivateObject` validators gain: reject when acting actor's party location ≠ item's `room_id` / object's `room_id`. Additive; Phase 47 validators currently skip this check.
- **`mark_level_items_inert` trigger** — call `RpgService.mark_level_items_inert(repo, campaign_id, level_id)` when the party exits a level (detected in `MoveToRoom` applier by comparing old-level vs new-level).
- **`current_room` context block extended** — `_fetch_current_room` in `context_bundle.py` gains `exits: [{room_id, connection_type}]` (from dungeon Connection objects) + `visited: bool` for each exit target. Phase 48 wires real `current_room_id` from `party_location` (Phase 47 still requires caller to pass it explicitly).
- **Room-visit fog-of-war** — track which rooms the party has entered (`visited_rooms: set[str]` in repo). `MoveToRoom` applier marks target room visited.

**Design constraints to lock in the spec:**
- `MoveToRoom` is a **Player Command** (not a proposal) — same channel as Phase 46/47.
- Provisional movement UI (minimal): Phase 50's Verb·Noun·Adverb Card input replaces it; keep Phase 48 UI thin.
- No diagonal/multi-hop movement this phase — one room at a time.
- Fog-of-war affects the `current_room` context block (exits annotated as `visited: bool`), not the dungeon template itself.
- `party_location` is campaign-scoped (one location per campaign, not per actor — party moves together).

**Step 4 — TDD.**
Invoke the TDD skill, read `spec/TESTING.md` first (per CLAUDE.md). Suggested slice order:
1. Party location model + persistence (`party_location` column, `get/set_party_location`)
2. `MoveToRoom` command — validator (reachability check against dungeon connections)
3. `MoveToRoom` applier — update location, emit `party.moved`, mark visited, trigger `mark_level_items_inert` on level change
4. Party-presence gate on `PickUpItem` / `ActivateObject` validators
5. `current_room` context block extended with exits + fog-of-war
6. `MoveToRoom` manifest + seed (starting room in manifest)
7. Campaign UI — movement panel (provisional, minimal)

---

**Last session (2026-06-18) — Phase 47 room-object form UX (round 3). Phase 47 DONE.**
- User feedback on the new-object form: slug should be system-generated, archetype should be selectable.
- **Slug auto-generated** — removed the SLUG input from `_build_room_object_form` (`campaign_edit_panel.py`). `_slugify()` module helper + new logic in `_collect_room_object_inputs`: slug derived from NAME on create (`"Iron Chest" → iron-chest`), preserved unchanged on edit (original stashed in `_extra_data["slug"]`). View `_on_form_save` rooms-new branch guards empty slug (nameless object not saved).
- **Archetype cycle picker** — replaced the static `ARCHETYPE: CONTAINER` label with a `[<] CONTAINER [>]` picker cycling all 7 archetypes (Arcade has no clean native dropdown; matches the app's existing `[-]/[+]` picker idiom). New generic choice-picker infra on `CampaignEditPanel`: `_choice_values` / `_choice_options` / `_choice_label_centers` (cleared in `clear()`, rendered in `draw()`), `_choice_row()` builder. `_collect_room_object_inputs` treats the choice index as source of truth and re-derives default transitions for the selected archetype.
- 6 new/updated panel tests; 2673 passing. (Note: dropdowns deferred to Phase 50 VNA cards — see memory `project_phase50_vna_dropdowns`.)

**Last session (2026-06-18) — Phase 47 rooms drill-down UI fixes (round 2). Phase 47 DONE.**
- Slice 9's room drill-down rendered the top-level room list but the *inner* level (objects inside a room) was unwired — `_start_new_item`, `_on_form_save`, `_delete_item_at` all lacked a `rooms` branch, and there was no way to leave a room.
- **Count badge** — `_section_counts()["rooms"]` now mirrors the visible list: dungeon-room count at the top level, placed-object count once drilled in (was always `len(room_objects)`, showing `0`).
- **Back navigation** — `CampaignListPanel.back_btn_at()` + `draw(..., breadcrumb=...)` renders a clickable `‹ <Room Name>` in the header; `CampaignView.on_mouse_press` clears `_selected_room_id` on breadcrumb click and on any nav-section click. Helpers `_room_name()` / `_level_id_for_room()` added.
- **+ ADD / save / delete wired** — `_start_new_item` rooms branch opens a blank `RoomObjectManifest` (room_id + level_id auto-derived); `_on_form_save` adds (new) / updates (edit); `_delete_item_at` removes via `remove_room_object`.
- 12 new/updated tests (panel + view); corrected the existing count test that encoded the buggy `len(room_objects)` behavior.

**Last session (2026-06-18) — Phase 47 post-slice UI bug fixes (4 bugs). Phase 47 DONE.**
- **Bug fix: ROOMS section always empty** — `new_seed_from_dungeon()` and `edit_seed()` in `window.py` loaded the manifest but never called `campaign_view.set_dungeon()`, so `_dungeon` stayed `None` and `_section_items()` returned `[]` for the rooms section. Both methods now load the dungeon via `_dungeon_repo.load(slug)` and call `set_dungeon()` after the manifest. 2 new tests in `test_window.py`; guard: `attached_dungeon_slug=None` added to existing edit_seed test.
- **Bug fix: Scroll direction inverted** — `_card_top()` in `campaign_list_panel.py` subtracted `scroll_offset`, pushing cards DOWN (lower y) instead of UP. Changed to `+ scroll_offset`. Updated 2 scroll-aware hit-test assertions whose expected y-values were built on the wrong sign.
- **Bug fix: Cards overlap header when scrolled** — `CampaignListPanel.draw()` now wraps the card loop in a scissor rect `(px, py, pw, ph - HEADER_H)` using `arcade.get_window().ctx.scissor` (same pattern as `map_panel.py`). No new tests (render-only).
- **Bug fix: Clicking a room does nothing** — `_select_item_at()` had no "rooms" branch. Added: when `_selected_room_id is None`, clicking a dungeon room calls `set_selected_room(room.id)` (drill-down); when a room is already selected, clicking a room object opens `show_room_object` form. 2 new tests in `test_campaign_view.py`.
- **Hotfix: `UnboundLocalError` on campaign load** — `import arcade` inside `draw()` shadowed the module-level import, breaking all earlier `arcade.*` calls in the same function scope. Removed the local import.
- 4 net new tests; 2655 passing.

**Last session (2026-06-18) — Phase 47 Slice 9 complete. Phase 47 DONE.**
- **Slice 9 DONE** — Campaign Seed editor UI. `CampaignEditPanel.show_room_object()` + `_build_room_object_form()` + `_collect_room_object_inputs()` added; `_collect_inputs()` dispatches to it for modes `room_object`/`new_room_object`. Form inputs: slug, display_name, description, initial_state; `_extra_data`: room_id, level_id, archetype, transitions (pre-populated via `default_transitions_for_archetype()`). `default_transitions_for_archetype()` module-level function with default SMs for all 7 archetypes. `CampaignListPanel`: "rooms" added to `_SECTION_LABELS`; `_draw_room_card()` (Room from dungeon) + `_draw_room_object_card()` (RoomObjectManifest); `_draw_card()` dispatches for "rooms" section by duck-typing (hasattr archetype). `CampaignView`: "rooms" added to `_SECTIONS`; `_init_state()` gains `_dungeon: Dungeon | None` + `_selected_room_id: str | None`; `set_dungeon()`, `set_selected_room()`, `add_room_object()`, `remove_room_object()` added; `_section_items()` for "rooms": no room selected → flattened dungeon rooms, room selected → objects filtered by room_id; `_section_counts()["rooms"]` = `len(room_objects)`. 25 new tests; 2651 passing.

**Last session (2026-06-18) — Phase 47 Slice 8 complete.**
- **Slice 8 DONE** — Context bundle `current_room` block. `ContextBundle.current_room: dict[str, Any]` field added to `models.py`. `ContextBundleBuilder.__init__` gains `current_room_id: str | None = None`; `build()` wires `_fetch_current_room(repo)`. Method returns `{}` when no room id; when set returns `{room_id, objects: [{slug, display_name, archetype, current_state, description}], loose_items: [{slug, display_name, description, status}]}`. Uses existing `get_objects_by_room` + `get_items_by_room`; filters `loose_items` to `item_type == "dungeon_item"`. New test file `tests/unit/memory/test_context_bundle_current_room.py` (6 tests). 2626 passing.

**Last session (2026-06-18) — Phase 47 Slice 7 complete.**
- **Slice 7 DONE** — Manifest + seed. `ItemManifest.room_id: str | None = None` added (loose item placement). `ObjectTransitionManifest` + `RoomObjectManifest` Pydantic models added to `manifest.py`; `CampaignManifest.room_objects` field added. `_seed_item` extended with loose path: when `room_id` set and no `owner_slug`, item seeds with `room_id` set and `owner_actor_id=None`; owner wins when both set. `_seed_room_object` added to `seeder.py` following `_seed_faction` idempotent pattern (skip/force/dry_run); derives `object_id="obj:{slug}:{object_slug}"`, `transition_id="tr:{slug}:{object_slug}:{i}"`, sets `current_state=initial_state`. Wired into `seed_from_manifest()`. 13 new tests (5 manifest, 2 seeder-item, 5 seeder-room-objects, 1 dry_run extra covered); 2620 passing.

**Last session (2026-06-18) — Phase 47 Slice 6 complete.**
- **Slice 6 DONE** — `ActivateObject` end-to-end integration test. `tests/integration/test_activate_object_e2e.py` (3 tests): (1) full pipeline success — validate accepts, apply fires `object.transitioned` + `item.spawned` + `clock.advanced`, repo state updated; (2) rejected command is no-op — missing key → validate rejects → zero events, object stays "locked", clock unchanged; (3) chained activate → pickup — after open spawns coin into room, `PickUpItem` validates + applies, coin owned by actor, `room_id` cleared. No new production code needed (Slices 3–5 already complete). 3 new tests; 2607 passing.

**Last session (2026-06-18) — Phase 47 Slice 5 complete.**
- **Slice 5 DONE** — `PickUpItem` + `DropItem` commands. Both added to `PlayerCommand` union in `command.py`. Validator branches: `PickUpItem` rejects unknown item, non-`dungeon_item`, inactive, already-owned, unknown actor, non-PC actor, actor at cap (≥10); accepts otherwise. `DropItem` rejects unknown item, unowned; accepts otherwise. Applier: `PickUpItem` → `update_item_owner(actor_id)` + `update_item_room(None)` + `item.picked_up` event; `DropItem` → `update_item_owner(None)` + `update_item_room(room_id)` + `item.dropped` event. Bug fix: `save_item` was not persisting `room_id` (field missing from INSERT); fixed + 1 new regression test. 16 new tests; 2604 passing.

**Last session (2026-06-18) — Phase 47 Slice 4 complete.**
- **Slice 4 DONE** — `ActivateObject` applier: `update_object_state(to_state)` + deterministic side-effects. Spawn: find unplaced inert item by `spawns_item_slug` (`owner_actor_id=None`, `room_id=None`), set `room_id=object.room_id` + `status="active"`, emit `item.spawned`; missing/already-placed slug is a logged no-op. Clock: find clock whose `clock_id` ends with `:{slug}`, tick via `RpgService.advance_clock`, persist via `update_clock_progress`, emit `clock.advanced`; missing slug is a logged no-op. Always emits `object.transitioned`. New repo helpers: `get_items_by_room(campaign_id, room_id)` (loose items only — `owner_actor_id IS NULL`), `update_item_room(item_id, room_id|None)`. Also updated `get_items` / `get_items_by_actor` / `_item_row_to_dict` to include `room_id` (index 12). 9 new tests; 2582 passing.

**Last session (2026-06-18) — Phase 47 Slice 3 complete.**
- **Slice 3 DONE** — State transition validation. `ActivateObject` command (`object_id`, `actor_id`, `trigger`) added to `rpg/command.py` and the `PlayerCommand` union. `validate_command` branch in `command_validator.py`: rejects unknown object; rejects when no transition matches `(from_state == current_state, trigger)`; rejects when the transition's `requires_item_slug` is not in the acting actor's **active** inventory (checks `get_items_by_actor`, slug + `status=="active"`). Accepts otherwise; rejections emit `command.rejected`. No side-effects (Slice 4). 8 new tests (7 in `test_command_validator.py`, 1 instantiation in `test_command.py`); 2579 passing.
- Committed Slices 1–2 (were uncommitted): models + migration `009_room_objects.sql` + repository CRUD. Added `*.duckdb` to `.gitignore`.

**Prior session (2026-06-18) — Phase 47 spec + issue promotion (no code).**
- Promoted the Phase 47 roadmap **draft card → GitHub issue [#72](https://github.com/ghostpencil/dungeon-daddy/issues/72)** (`convertProjectV2DraftIssueItemToIssue`); created + applied the `phase-47` label.
- Wrote **`spec/PHASE_47_ROOM_CONTENTS.md`** (none existed previously — confirmed via git history). Reconciles issue #72 with the 2026-06-17 review and locks 8 design decisions: room interactions are Player Commands (not proposals); transition side-effects are engine-internal deterministic; spawned items are pre-seeded inert rows; no party-location gate this phase (Phase 48); item placement extends `ItemManifest.room_id`; `current_room` context block is provided not discovered.
- **Audited Slices 1–2 against the design — both ✅, no rework.** Notes (non-blocking): `UNIQUE(campaign_id, slug)` on `room_objects` (consistent w/ items); `update_object_state` landed a slice early (harmless); `ObjectTransition` validity checked dynamically in Slice 3 (correct). 61 slice tests pass.
- Locked **slice ordering to issue #72** (Objects track first): next is Slice 3 — State transition validation.

**Prior session (2026-06-18) — Phase 47 Slice 2 complete.**
- **Slice 2 DONE** — `save_room_object` (upsert + transition child-row replace), `get_room_object` (by object_id), `get_objects_by_room` (by campaign_id + room_id), `update_object_state` (set current_state), `_room_object_row_to_dict` added to `MemoryRepository`. `RoomObject` import added to `repository.py`. New test file `tests/unit/memory/test_room_object_repository.py` (7 tests: round-trip, upsert dedup, room filter, empty-room guard, transitions nested, transitions replace on upsert, state update). 7 new tests; 2571 passing.
- **Slice 1 DONE** — `RoomObject` + `ObjectTransition` Pydantic models added to `dungeon_daddy/rpg/models.py`; `ObjectArchetype` Literal type (7 archetypes: container, door, mechanism, structure, trap, lore_fixture, resource); `RoomObject.description` non-empty validator. `Item.room_id: str | None = None` added. Migration `dungeon_daddy/data/migrations/009_room_objects.sql` creates `room_objects` + `object_transitions` tables; adds `room_id` column to `items`. `EXPECTED_TABLES` in `test_rpg_memory_migrations.py` updated; `test_items_table_has_room_id_column` added. 9 new tests; 2564 passing.

**Prior session (2026-06-17) — Phase 46 Slices 1–10 complete. Phase 46 DONE.**
- **Slice 10 DONE** — Manifest + seed: `ItemFeatureManifest` + `ItemManifest` added to `dungeon_daddy/campaign/manifest.py`; `CampaignManifest.items` field added. `_seed_item` added to `dungeon_daddy/campaign/seeder.py` following `_seed_faction` idempotent pattern — skips existing unless `force`, `dry_run` counts only, `owner_slug` resolves to `actor:{campaign_slug}:{owner_slug}`, `charges_current` initialises to `charges_max`. Wired into `seed_from_manifest()`. 8 new tests; 2555 passing.
- **Slice 9 DONE** — Character Sheet Panel UI: `set_inventory(kits, dungeon_items, equipped)` added to `CharacterSheetPanel`. Stores three lists; draw() renders KITS section (pip tracks for charges_current/charges_max reusing existing pip constants), ITEMS section (name + status color + `[L]` tag for level-bound), GEAR section (feature badges: `FIGHT +1` for rating_modifier, `VANISH [new]` for new_action). 5 new tests; 2547 passing.
- **Slice 8 DONE** — World-reaction item proposals: `GrantItemChange`, `StripItemChange`, `TransformItemChange` added to `ProposedChange` union in `proposal.py`. Validator gains `known_item_ids`, `known_item_slugs`, `dungeon_item_counts` params with branches for all three. Applier applies each immediately (grant → `update_item_owner`; strip → `update_item_status("lost")`; transform → `update_item_slug`); each emits its domain event (`item.granted`, `item.stripped`, `item.transformed`) + `proposal.applied`. New `update_item_slug` added to `MemoryRepository`. 18 new tests; 2542 passing.
- **Slice 7 DONE** — Context bundle inventory: `inventory: dict[str, Any]` added to `ContextBundle`; `_fetch_inventory(repo)` added to `ContextBundleBuilder.build()`. Per focus actor: kits (active class_kits), dungeon_items (all statuses + `level_bound` flag), equipped (is_equipped gear with features), `effective_actions` (base + equipped rating_modifier via `compute_effective_ratings`). 7 new tests; 2524 passing.

**Prior session (2026-06-17) — Phase 46 Slices 1–6 complete. Slice 7 was next.**
- **Slice 6 DONE** — Engine effect: `mark_level_items_inert(repo, campaign_id, level_id) -> list[str]` added to `service.py`. Queries all campaign items, sets `status="inert"` for active items whose `level_id` matches, returns affected ids. 2 new tests (happy path: two items marked; guard: different level and non-active items skipped); 2517 passing. Trigger wired in Phase 48.
- **Slice 5 DONE** — Equipped gear commands: `EquipItem` + `UnequipItem` added to `command.py` (`PlayerCommand` union now covers all 6 commands). Validator branch (shared for both): rejects unknown item, non-`equipped_gear` type, inactive status, no owner. Applier: `EquipItem` → `update_item_equipped(True)` + `item.equipped` event; `UnequipItem` → `update_item_equipped(False)` + `item.unequipped` event. `compute_effective_ratings(actor_id, base_ratings, repo) -> dict[str, int]` added to `service.py` — sums base + equipped `rating_modifier` features at read time, leaving stored base ratings untouched. 19 new tests; 2515 passing.
- **Slice 4 DONE** — Dungeon item commands: `ConsumeItem`, `GiveItem`, `TakeItem` added to `command.py` (full `PlayerCommand` union now covers all 4 commands). Validator gains branches for each: `ConsumeItem` rejects unknown/inactive; `GiveItem` rejects unknown item, unknown target, non-PC target, and target at dungeon-item cap (≤ 10); `TakeItem` rejects unknown and unowned. Applier applies mutations immediately: `item.consumed` / `item.transferred` / `item.removed` events. 20 new tests; 2496 passing.
- **Slice 3 DONE** — Player Command channel: `dungeon_daddy/rpg/command.py` (`ConsumeKitCharge` + `PlayerCommand` union); `command_validator.py` (`validate_command` → `CommandValidationResult`; rejects unknown item, non-kit, inactive, zero-charge; emits `command.rejected` event); `command_applier.py` (`apply_command` → `CommandApplyResult`; decrements charges, emits `kit.charge_consumed`; no-op on rejection); `refresh_kits(repo, actor_id)` added to `service.py` (restores active class_kit charges to max, skips inactive). `tests/unit/rpg/conftest.py` adds shared repo fixture. 10 new tests; 2476 passing.
- **Slice 2 DONE** — `save_item` (upsert + feature child-row replace), `get_items`, `get_items_by_actor`, `update_item_status`, `update_item_charges`, `update_item_equipped`, `update_item_owner` added to `MemoryRepository`. 9 new tests (round-trip, upsert dedup, actor-scoped query, feature nesting, feature replace on upsert, all 4 updaters); 2466 passing.
- **Slice 1 DONE** — `ItemFeature` + `Item` Pydantic models added to `dungeon_daddy/rpg/models.py`; migration `dungeon_daddy/data/migrations/008_items.sql` creates `items` + `item_features` tables. Invariants enforced: non-empty description, `class_kit` requires `charges_max ≥ 1` and `0 ≤ charges_current ≤ charges_max`, `class_kit`/`dungeon_item` reject features, `rating_modifier` requires non-null `modifier`, `new_action` requires `modifier=None`. 10 new tests; 2457 passing.

**Prior session (2026-06-17) — #65, #66, #67, and #68 complete; stabilization done.**
- **#68 DONE** — Library: 'Extract' button on Save cards extracts the save's `campaign.json` back into the seed library. `LibraryView.on_extract_seed()` delegates to `window.extract_seed(slug)`; `window.extract_seed()` loads the manifest from the save dir and calls `seed_library.save()`. Save cards now show ["Play", "Extract", "Delete"] buttons. 3 new tests; 2447 passing.
- **#67 DONE** — Library: show last-played date on Save cards. Added `DungeonRepository.get_last_played(slug)` (returns `session.json` mtime as `datetime | None`); `LibraryView._refresh_save_meta()` builds a per-slug lookup; `_draw_save_card()` renders "Played: Jun 17, 2026" or "Never played" in place of the slug line. 4 new tests; 2444 passing.
- **#66 DONE** — Play mode: prompt to save session on navigate away to Library. `on_mouse_press` in `PlayView` now calls `_ask_yes_no` when the Library pill is clicked with an active session; cancelling keeps the user in Play. No-session and non-Library pill clicks are unchanged. 5 new tests; 2440 passing.
- **#65 DONE** — Confirmation dialog before deleting a save game. `on_delete_save` in `LibraryView` now calls `window._ask_yes_no` before delegating to `window.delete_save`; cancelled confirmation leaves the save intact. 3 new tests (replace old single test); 2435 passing.
- All 6 stabilization items complete. Ready to merge to main and start Phase 46.

**Prior session (2026-06-17) — #64 complete; 4 stabilization items remain.**
- **#64 DONE** — Design mode: handle no-dungeon-loaded state gracefully. Fixed two bugs: (1) `on_show_view` was adding wizard greeting even on first-visit in edit mode; (2) `reset_to_wizard()` left stale chat messages, LLM histories, and generation state across sessions. Added `ChatPanel.clear_messages()` and updated `reset_to_wizard()` to clear all session state before re-greeting. 9 new tests; 2433 passing.
- **#63 DONE** — Removed hardcoded `Protagonist` PC actor from `_CampaignSeedSpec` in `tools/seed_rpg_state.py`. Generic `seed_campaign()` path now emits a warning directing users to `--seed-pack`. Tests updated (25 passing). Committed on `stabilization-post-45`.

**Prior session (2026-06-17) — stabilization branch + GitHub issue promotion.**
- Created branch `stabilization-post-45`.
- Promoted 6 post-Phase-45 draft cards to real GitHub issues (#63–#68) with `stabilization` label; deleted the original drafts from the project board.

**Prior session (2026-06-17) — added Phase 53 + sequencing review.** All design/docs only, no
code:
- **New Phase 53 — Threat Behavior & Monster Reactions.** Full design in
  `spec/MONSTER_REACTION_DESIGN.md`; draft card on GitHub Project #1; roadmap table extended to
  46–53 in `IMPLEMENTATION_PHASES_33_ONWARDS.md`; spec-loading row added to `CLAUDE.md`.
  Decisions: monsters never roll; engine bounds the eligible reaction set + all magnitudes, LLM
  selects one by `reaction_id` and narrates; depth-by-rank (standard = Model A instinct+tiers,
  elite/boss = Model B + clock-threshold boss phases); activates the inert `npc_reaction`
  channel. Hard deps all done (P34/35/36) — kept last as a soft "after Phase 50".
- **Sequencing review of 46–53.** Ordering is topologically valid — no phase precedes a hard
  dep, no renumbering needed. Recorded as the "Phase Dependencies & Sequencing (46–53)" matrix
  in `IMPLEMENTATION_PHASES_33_ONWARDS.md` (spine = `46→47→48→50`, `46→49→50`, `49→52`; 51 + 53
  are flexible pull-on-demand depth phases).

**Prior session (2026-06-17) — Phases 46–52 design review.** Logical coherence, Arcade
feasibility, design gaps. Sequencing sound; fits the architecture; no Arcade blockers.
Resolutions folded into the GitHub draft-issue bodies + the spec mirror
(`IMPLEMENTATION_PHASES_33_ONWARDS.md` → "Key design resolutions (2026-06-17 review)").
Three blocking resolutions to honour when building:
- **Player Commands vs LLM proposals** — new `rpg/command.py` (engine-authoritative) for
  move/pick-up/equip/activate/fulfil-milestone; the proposal union stays LLM-advisory only.
- **Adverbs → dice-pool deltas + side-effect flags** (no position/effect axis exists).
- **Recedable intimacy clock** — add signed `tick_clock` + `monotonic: bool = True` on
  `ClockState` (existing clocks default `monotonic=True`, unchanged).
No code changed yet; implementation begins when Phase 46 is defined.

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

None (test suite passes — 2673 tests as of 2026-06-18).

---

## Previous Phases

Phase 42 and earlier are complete. Full history in `spec/HISTORY.md`.

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Roadmap for Phases 47–53 (planned): GitHub Projects `ghostpencil/dungeon-daddy` #1, mirrored in the "Planned Roadmap — Phases 46–53" section of `IMPLEMENTATION_PHASES_33_ONWARDS.md`. Issue bodies hold the per-phase detail and the folded-in design resolutions; a detailed `spec/PHASE_NN_*.md` is written when each phase starts.
- Phase 47 spec: `spec/PHASE_47_ROOM_CONTENTS.md` (GitHub issue [#72](https://github.com/ghostpencil/dungeon-daddy/issues/72), label `phase-47`). Written 2026-06-18 after Slices 1–2 shipped; reconciles issue #72 with the 2026-06-17 review (room interactions are Player Commands, not proposals; transition side-effects are engine-internal) and contains an as-built audit of Slices 1–2 (both ✅). Slice order follows issue #72 (Objects track — transition validation — before the Items-in-rooms pickup track).
- Phase 53 (Threat Behavior & Monster Reactions, planned 2026-06-17): instinct-driven, engine-bounded monster reactions with no enemy turn; bosses escalate via clock thresholds. Full design in `spec/MONSTER_REACTION_DESIGN.md`; summary in `IMPLEMENTATION_PHASES_33_ONWARDS.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
- `protagonist` actor is defined in `seed_data/campaigns/the-crucible/rpg_seed.json` (use `--seed-pack` + `--force` to reset stress tracks); the generic `seed_campaign()` path no longer creates a placeholder actor.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates and seeds cleanly; 2 memory seeds).
- `tools/seed_rpg_state.py`: `actor_type="faction"` entries routed to `repo.save_faction()`; faction clock `owner_actor_id` cleared.
- Live campaigns migrated (2026-06-13): `The Crucible` — `desert-djinn-fragment` moved from `actors` to `factions` table.
- Playtest reports: `python -m tools.playtest_report <db_path> <campaign_id>` (requires `PYTHONPATH=.`).
- `proposal.applied` / `proposal.rejected` events now emitted; call sites must insert `result.rejection_events` into repo with correct `campaign_id` after `validate_proposal()`.
