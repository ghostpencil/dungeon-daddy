# Dungeon Daddy — Project Index

## Phase

Phase: 44 — Stabilization
Status: **COMPLETE** — All stabilization items done (2026-06-13). 2393 tests passing.
Branch: `main`

### Stabilization log

**Item 4 complete (2026-06-13): Prune low-value tests**
- Deleted 10 tests across 4 categories: 3 Grid-mode negative tests (removed feature), `test_map_panel_background.py` (entire file — pure mock-wiring), `test_dm_error_result_shows_error_bubble` (duplicate of canonical test), 4 call-count-only tests in `test_layout_renderer.py`
- 2393 tests passing

**Item 3 complete (2026-06-13): Reposition RPG and Edit Memory buttons to title bar**
- `chrome.py` — exported `PILLS_CLUSTER_W = 286` (total width of the three mode pills)
- `play_view.py` — `_compute_rpg_toggle_rect` and `_compute_edit_btn_rect` now position buttons immediately left of the pills cluster (order: Edit Memory | RPG | Design | Campaign | Play); removed stale `_PLAY_BADGE_W = 100` placeholder
- Buttons remain play-mode only (drawn in `PlayView.on_draw` only — no change needed for Design/Campaign views)
- 2403 tests passing

**Item 2 complete (2026-06-13): Rename "Graph" map variant button to "Map"**
- `map_panel.py` — `_VARIANT_TABS` → `["Map"]`; `_active_variant` default → `"Map"`; all `== "Graph"` / `!= "Graph"` comparisons updated to `"Map"`
- `tests/unit/map/test_map_panel_layout.py` — 7 `_active_variant = "Graph"` → `"Map"`
- `tests/unit/ui/panels/test_map_panel_background.py` — `"Graph"` → `"Map"` (default arg + 2 test calls)
- `tests/unit/ui/test_map_panel_zoom.py` — `"Graph"` → `"Map"` (click and assert)
- 45 affected tests passing

**Item 1 complete (2026-06-13): Remove Grid and Tiles map modes**
- `dungeon_daddy/map/tiles_renderer.py` — deleted
- `tests/unit/map/test_grid_renderer.py` — deleted (17 tests)
- `tests/unit/map/test_tiles_renderer.py` — deleted (9 tests)
- `map_panel.py` — `_VARIANT_TABS` → `["Graph"]`; default variant → `"Graph"`; `_center_level()` removed; `load()` always calls `_fit_layout_camera()`; draw condition simplified; tab width calculation fixed
- `window.py` — View menu stripped to Graph only; `set_map_variant()` simplified
- `play_view.py` — switched to `GraphRenderer`; `on_variant_change=None`
- Deleted orphaned tests: `test_variant_tab_click_fires_callback`, `test_background_not_drawn_in_grid_mode`, `test_set_map_renderer_updates_map_panel`, 3 `_center_level()` zoom/pan tests
- Updated `test_variant_tab_click_no_callback_does_not_raise` mock count (4→2 buttons)
- `GridRenderer` kept as internal base class (inherited by `GraphRenderer`, used by `LoopOverlay`)
- 2403 tests passing

---

### Phase 44 — Playtest Telemetry and Balance Reports (COMPLETE)
Spec: `spec/PHASE_44_PLAYTEST_TELEMETRY.md`
Branch: `phase-44-playtest-telemetry` (merged into main 2026-06-13)

New `dungeon_daddy/reporting/` module with Pydantic models, aggregation queries, and `build_report()`. Two new domain events: `proposal.applied` and `proposal.rejected`. CLI tool `tools/playtest_report.py` prints formatted balance reports. 6 TDD slices, 33 new tests.

---

### Phase 43 — Faction System (COMPLETE)
Spec: `spec/PHASE_42_ADDITION_FACTION_SYSTEM.md`
Branch: `phase-43-faction-system` (merged into main 2026-06-13)

New `FactionManifest` model (replaces `ActorManifest` for factions); named reputation tiers (hostile/cold/neutral/warm/allied); `FactionState` persisted in DuckDB; `AdjustReputationChange` in LLM proposal system; faction reputations included in `ContextBundle`; faction-specific Campaign UI edit form and list cards. 7 TDD slices.

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is advisory. It may narrate, frame choices, interpret tone, and propose structured world reactions. It must not directly mutate authoritative state.

---

## Known Failures

None (test suite passes — 2393 tests as of 2026-06-13).

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
