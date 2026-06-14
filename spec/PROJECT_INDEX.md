# Dungeon Daddy — Project Index

## Phase

Phase: 44 — Playtest Telemetry and Balance Reports
Spec: `spec/PHASE_44_PLAYTEST_TELEMETRY.md`
Status: **COMPLETE** — All 6 slices done (2026-06-13). 2435 tests passing.
Branch: `phase-44-playtest-telemetry`

Summary: New `dungeon_daddy/reporting/` module with Pydantic models, aggregation queries, and `build_report()`. Two new domain events: `proposal.applied` (emitted per applied change in `proposal_applier.py`) and `proposal.rejected` (via `ValidationResult.rejection_events` on the pure validator). CLI tool `tools/playtest_report.py` prints formatted balance reports. 6 TDD slices, 33 new tests.

Slice 1 complete (2026-06-13):
- `dungeon_daddy/reporting/__init__.py`, `models.py` — all 8 Pydantic model classes
- 4 tests in `tests/unit/reporting/test_models.py`

Slice 2 complete (2026-06-13):
- `dungeon_daddy/reporting/queries.py` — `action_usage`, `outcome_breakdown`, `stress_distribution`
- `tests/unit/reporting/conftest.py` — repo fixture (mirrors `tests/unit/memory/conftest.py`)
- 7 tests in `tests/unit/reporting/test_queries.py`

Slice 3 complete (2026-06-13):
- `dungeon_daddy/reporting/queries.py` — `clock_activity`, `fallout_frequency`
- 6 new tests in `tests/unit/reporting/test_queries.py`

Slice 4 complete (2026-06-13):
- `dungeon_daddy/rpg/proposal_validator.py` — `ValidationResult.rejection_events: list[DomainEvent]`; emits `proposal.rejected` per rejected change (campaign_id="" — call site fills in before inserting)
- `dungeon_daddy/rpg/proposal_applier.py` — emits `proposal.applied` per applied `CreateMemoryChange` and `AdjustReputationChange`
- `dungeon_daddy/reporting/queries.py` — `proposal_stats`, `memory_stats`
- 3 new tests in `tests/unit/rpg/test_proposal_validator.py`; 2 new tests in `tests/unit/rpg/test_proposal_applier.py`; 3 new tests in `tests/unit/reporting/test_queries.py`
- Fixed pre-existing failure: `test_example_bone_cathedral_manifest_seeds_cleanly` expected 3 memory seeds but manifest has 2

Slice 5 complete (2026-06-13):
- `dungeon_daddy/reporting/reporter.py` — `build_report(repo, campaign_id) -> PlaytestReport`
- 4 tests in `tests/unit/reporting/test_reporter.py`

Slice 6 complete (2026-06-13):
- `tools/playtest_report.py` — `format_report()` + `main()` CLI
- 4 tests in `tests/unit/tools/test_playtest_report.py`

---

### Phase 43 — Faction System (COMPLETE)
Spec: `spec/PHASE_42_ADDITION_FACTION_SYSTEM.md`
Status: **COMPLETE** — All 7 slices done (2026-06-13). 2402 tests passing.
Summary: New `FactionManifest` model (replaces `ActorManifest` for factions); named reputation tiers (hostile/cold/neutral/warm/allied); `FactionState` persisted in DuckDB; `AdjustReputationChange` in LLM proposal system; faction reputations included in `ContextBundle`; faction-specific Campaign UI edit form (no action ratings/stress tracks); 7 TDD slices.

Slice 1 complete (2026-06-13):
- `FactionManifest` added to `campaign/manifest.py`; `tier` validator 0–4; `reputation` literal
- `CampaignManifest.factions` changed from `list[ActorManifest]` to `list[FactionManifest]`
- `"faction"` removed from `ActorManifest.actor_type` literal
- `campaign/validator.py` — action rating / stress track checks skipped for factions
- `campaign/seeder.py` — seeds only `world_actors` at this point; faction seeding added in Slice 3
- `views/campaign_view.py` — `add_actor` routes by `isinstance(FactionManifest)` not `actor_type`
- `examples/campaign_manifests/bone-cathedral.json` migrated to new faction shape
- All affected tests updated (test_campaign_manifest, test_manifest_patch, test_campaign_manifest_validator, test_campaign_view, integration tests)

Slice 2 complete (2026-06-13):
- `FactionState` added to `rpg/models.py`
- `dungeon_daddy/data/migrations/007_factions.sql` — creates `factions` table with `UNIQUE(campaign_id, slug)`
- `MemoryRepository.save_faction()` — upserts by `faction_id`
- `MemoryRepository.get_factions(campaign_id)` — returns list of dicts scoped by campaign
- `MemoryRepository.update_faction_reputation(faction_id, delta_steps)` — steps through tiers, clamps at endpoints
- 9 new tests: `tests/unit/rpg/test_faction_state.py`, `tests/unit/memory/test_faction_repository.py`

Slice 3 complete (2026-06-13):
- `SeedFaction` model added to `rpg/seed_pack.py`; `SeedPack.factions` field added
- `derive_faction_id()` with isolated UUID namespace (`_FACTION_NS`)
- `apply_seed_pack()` extended to handle factions — inserts only new factions (checks by `faction_id`), does NOT reset runtime reputation on re-seed
- `ApplyResult.factions_applied` counter added
- `campaign/seeder.py` — `_faction_id()` helper + `_seed_faction()` added; `seed_from_manifest()` now seeds factions from `CampaignManifest.factions` with same idempotency rule
- 14 new tests in `tests/unit/rpg/test_seed_pack.py`; 2 new integration tests in `tests/integration/test_campaign_authoring_cli.py`
- 2380 tests passing

Slice 4 complete (2026-06-13):
- `AdjustReputationChange` added to `rpg/proposal.py`; added to `ProposedChange` discriminated union
- `validate_proposal()` gains `known_faction_slugs: set[str] | None = None`; rejects unknown slugs
- `proposal_applier.py` handles `AdjustReputationChange` — looks up faction by slug, calls `update_faction_reputation()`, emits `reputation_changed` domain event
- 6 new tests in `tests/unit/rpg/test_proposal_faction.py`
- 2386 tests passing

Slice 5 complete (2026-06-13):
- `faction_reputations: list[dict]` added to `ContextBundle` in `memory/models.py`
- `ContextBundleBuilder._fetch_faction_reputations()` added; filters to `status="active"` only
- Called in `build()` — bundles `slug`, `display_name`, `reputation`, `goal`, `tier`, `status` per faction
- 4 new tests in `tests/unit/memory/test_context_bundle_factions.py`
- 2390 tests passing

Slice 6 complete (2026-06-13):
- `show_faction()` / `_build_faction_form()` / `_collect_faction_inputs()` added to `CampaignEditPanel`
- Fields: NAME, SLUG, CONCEPT (h=80), GOAL (h=60), REPUTATION picker (steps through tier list), TIER picker (0–4)
- `_collect_inputs()` dispatches to `_collect_faction_inputs()` for faction/new_faction modes
- `_collect_faction_inputs()` converts `reputation_idx` → tier name string
- `campaign_view.py`: `_select_item_at()` / `_start_new_item()` route factions to `show_faction()` not `show_actor()`
- `campaign_view.py`: `_on_form_save()` handles factions as `FactionManifest` (no action_ratings/stress_tracks)
- 6 new tests in `tests/unit/ui/test_campaign_panels.py`

Slice 7 complete (2026-06-13):
- `_draw_faction_card()` added to `CampaignListPanel`: name (serif), FACTION chip (gold), reputation chip (ember/default/teal/gold), tier label (mono), concept (italic), NO action ratings row
- `_REPUTATION_CHIP` and `_TIER_LABELS` constants added to `campaign_list_panel.py`
- `_draw_card()` routes "factions" to `_draw_faction_card()` (separate from actor card path)
- `_ACTOR_CHIP` dict cleaned of `"faction"` entry (dead code after Slice 1)
- 6 new tests in `tests/unit/ui/test_campaign_panels.py`
- 2402 tests passing

Edit form and delete X cleanup (2026-06-13):
- Clock edit form: added labels NAME / SLUG / SEGMENTS / FILLED / STAKES above each input
- Threat edit form: added labels LOCATION / DESCRIPTION above each input
- Lore edit form: added TEXT label above the textarea
- Delete ✕ on hovered cards: size increased (DELETE_ZONE_SIZE 16→20, font TEXT_SM→TEXT_BASE)
- All list-panel type chips shifted 16px left (`-PAD_MD-52` was `-PAD_MD-36`) so the ✕ no longer overlaps the chip
- 2402 tests still passing

Faction card QA fix (2026-06-13):
- Reputation chip center adjusted from `x + PAD_MD + 4` → `x + PAD_MD + 36`; left edge now lands at `x + PAD_MD`, inside the card bounds
- Tier label x offset adjusted to `x + PAD_MD + 80` to match

Post-slice additions (not in original spec, added during manual QA):
- Action ratings row rendered on actor cards (`_draw_actor_card`)
- Actor edit form fully labeled with NAME/SLUG/CONCEPT/ACTION RATINGS/STRESS TRACKS sections
- All 9 action keys editable (fight, move, tinker, study, focus, sway, sense, channel, endure)
- All 4 stress track capacities editable (body, composure, bonds, weird); defaults to 0 for new actors
- `_parse_rating_keys` + `_parse_stress_keys` helpers in `campaign_view.py` handle form→manifest round-trip
- `actor_type` preserved via `_extra_data` on edit panel (no UI selector yet — always "pc" for new actors)

Nav panel fix (2026-06-13):
- `_SECTION_META["player_side"]` label changed from "PLAYER SIDE" to "PARTY"

Edit panel bug fixes (2026-06-13, found during manual QA):
- `_FIELD_H` 22→26, `_ROW_H` 18→22: fixed text clipping in input fields at Windows DPI scaling
- All widget coordinates cast to `int` (in `_widget_y`, `_add_input`, `_add_save_cancel`): reduced sub-pixel jitter on hover
- Action ratings and stress track rows replaced with `[-] value [+]` number pickers (`_number_row` closure in `_build_actor_form`); eliminates `UIInputText` hover-redraw jitter entirely; values stored in `_number_values`, drawn via `_number_label_centers` in `draw()`, merged in `_collect_inputs()`
- Concept textarea enlarged from h=36 to h=80; arcade multiline `UIInputText` handles scroll natively

Branch: `phase-43-faction-system` (merged into main 2026-06-13)

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is advisory. It may narrate, frame choices, interpret tone, and propose structured world reactions. It must not directly mutate authoritative state.

---

## Known Failures

None (test suite passes — 2435 tests as of 2026-06-13).

---

## Previous Phases

Phase 41 and earlier are complete. Full history in `spec/HISTORY.md`.

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
- `protagonist` actor is in `seed_data/campaigns/the-crucible/rpg_seed.json`; `--force` resets its stress tracks.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates and seeds cleanly; 2 memory seeds).
- `tools/seed_rpg_state.py`: `actor_type="faction"` entries routed to `repo.save_faction()`; faction clock `owner_actor_id` cleared.
- Live campaigns migrated (2026-06-13): `The Crucible` — `desert-djinn-fragment` moved from `actors` to `factions` table.
- Playtest reports: `python -m tools.playtest_report <db_path> <campaign_id>` (requires `PYTHONPATH=.`).
- `proposal.applied` / `proposal.rejected` events now emitted; call sites must insert `result.rejection_events` into repo with correct `campaign_id` after `validate_proposal()`.
