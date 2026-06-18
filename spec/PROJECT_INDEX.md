# Dungeon Daddy — Project Index

## Phase

Phase: **46 — Inventory System (COMPLETE)**
Status: All 10 slices complete. Branch `phase-46-inventory-system`. 2555 tests passing.

Previous: Phase 45 complete (2026-06-14). Stabilization post-45 complete (2026-06-17).
Spec: `spec/PHASE_46_INVENTORY_SYSTEM.md`. Issue [#70](https://github.com/ghostpencil/dungeon-daddy/issues/70).
Next: Phase 47 — Items in Rooms.

**Last session (2026-06-17) — Phase 46 Slices 1–10 complete. Phase 46 DONE.**
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

None (test suite passes — 2555 tests as of 2026-06-17).

---

## Previous Phases

Phase 42 and earlier are complete. Full history in `spec/HISTORY.md`.

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Roadmap for Phases 47–53 (planned): GitHub Projects `ghostpencil/dungeon-daddy` #1, mirrored in the "Planned Roadmap — Phases 46–53" section of `IMPLEMENTATION_PHASES_33_ONWARDS.md`. Next: Phase 47 (Items in Rooms). Issue bodies hold the per-phase detail and the folded-in design resolutions; a detailed `spec/PHASE_47_*.md` is written when Phase 47 starts.
- Phase 53 (Threat Behavior & Monster Reactions, planned 2026-06-17): instinct-driven, engine-bounded monster reactions with no enemy turn; bosses escalate via clock thresholds. Full design in `spec/MONSTER_REACTION_DESIGN.md`; summary in `IMPLEMENTATION_PHASES_33_ONWARDS.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
- `protagonist` actor is defined in `seed_data/campaigns/the-crucible/rpg_seed.json` (use `--seed-pack` + `--force` to reset stress tracks); the generic `seed_campaign()` path no longer creates a placeholder actor.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates and seeds cleanly; 2 memory seeds).
- `tools/seed_rpg_state.py`: `actor_type="faction"` entries routed to `repo.save_faction()`; faction clock `owner_actor_id` cleared.
- Live campaigns migrated (2026-06-13): `The Crucible` — `desert-djinn-fragment` moved from `actors` to `factions` table.
- Playtest reports: `python -m tools.playtest_report <db_path> <campaign_id>` (requires `PYTHONPATH=.`).
- `proposal.applied` / `proposal.rejected` events now emitted; call sites must insert `result.rejection_events` into repo with correct `campaign_id` after `validate_proposal()`.
