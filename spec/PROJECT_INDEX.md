# Dungeon Daddy — Project Index

## Phase

Phase: 35.6 — Stress Routing by Action Intent
Status: **Complete (2026-06-06)**

Branch: `phase-35.6-stress-routing`

_Phase 35.6 complete (2026-06-06). All 8 TDD slices done: `intent` field on ActionRequest/ActionResolution, `stress_routing.py` with `choose_stress_track()`, routing wired into `compute_world_reaction()`, clock category/level mapping, intent keyword mapping, PlayView capacity fix, non-body stress world-reaction tests. 1738 unit tests passing. Existing campaign seeds already have the right category/clock_level metadata — no seed changes needed._

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is advisory. The LLM may narrate, frame choices, interpret tone, and eventually propose structured world reactions. It must not directly mutate authoritative state.

---

## Phase 33–37 Roadmap

| Phase | Name | Goal |
|---|---|---|
| **33** | Player-Controlled Action Loop | Make Play Mode resolve player-controlled actor actions through the RPG service and narrate with live context bundles. |
| 34 | Campaign RPG Data Deepening | Patch the two existing campaigns with RPG-ready player actors, NPCs, monsters, clocks, memories, and room threat hooks. |
| 35 | Deterministic World Reaction Service | Add a deterministic service that turns player outcomes into dungeon/NPC/monster reactions, clocks, stress, fallout, and memory events. |
| 35.5 | Clock Scoping | Make clocks room-scoped and action-tagged so they only advance when contextually relevant. |
| **35.6** | Stress Routing by Action Intent | Replace hard-coded body stress with deterministic track selection driven by clock category, action key, and intent keywords. |
| 36 | LLM-Proposed Reaction Drafts | Allow the LLM to propose structured reactions, but validate and apply them through deterministic services only. |
| 37 | Memory Approval and Playtest Curation | Add curated approval/edit/reject workflows for LLM-drafted memories and run an alpha playtest scenario across seeded campaigns. |

Full phase specs in `spec/IMPLEMENTATION_PHASES.md`.

---

## Next Steps — Phase 36

Spec: `spec/IMPLEMENTATION_PHASES.md` (Phase 36 — LLM-Proposed Reaction Drafts)

Allow the LLM to propose structured reactions, but validate and apply them through deterministic services only.

## Known Failures

_None._

## Bug Fixes (post-Phase 24)

| Date | Fix |
|---|---|
| 2026-06-02 | Atmosphere frame misalignment — `_draw_atmosphere` was centering on `(canvas_w/2, canvas_h/2)` instead of `(viewport_x + canvas_w/2, viewport_y + canvas_h/2)`, causing the frame to draw relative to screen origin rather than the map panel. Fixed in `layout_renderer.py:_draw_atmosphere`. 1395 passing. |
| 2026-06-03 | MEM tab had no interactive search input — `MemoryInspectorPanel.draw()` only rendered a drawn box. Added `setup_widget`/`teardown_widget` to create a real `arcade.gui.UIInputText` via `_RpgSidePanel` (which now holds a `UIManager` ref). Widget lifecycle tied to tab switching and RPG panel open/close. |
| 2026-06-03 | MEM search input placeholder text lost when widget present — added manual placeholder draw in `draw()` when widget text is empty. |
| 2026-06-03 | Map keyboard shortcuts (D=debug, R=recenter) fired while typing in MEM search — fixed `on_key_press` in `PlayView` to return early when `self._rpg_open and self._rpg_side._active == 3`. |
| 2026-06-03 | "Edit Memory" button unclickable when RPG panel open — RPG panel click absorption (`if x >= rpg_x`) had no y-bound, swallowing title-bar clicks. Added `and y < content_h` guard. 1639 passing. |
| 2026-06-04 | ACTION tab intent label overlapped widget — `setup_widget` missing 18px actor-name row offset; `draw()` was rendering "Intent:" inside the widget bounds. Fixed by adding `cur_y -= 18` in `setup_widget`. |
| 2026-06-04 | ACTION key buttons permanently selected — button styles fixed at creation, never refreshed on click. Added `_action_btn_refs` dict; `on_click` now updates all button styles via `btn.style = _btn_style(...)`. |
| 2026-06-04 | RESOLVE crash — `RpgService.resolve_action` returns `tuple[ActionResolution, DomainEvent]` but `_format_result` received the tuple directly. Fixed tuple unpacking in `_on_resolve_action`. 1761 passing. |
| 2026-06-04 | RESOLVE produced no narration — `_on_resolve_action` stored result but never appended to DM history or spawned narration thread. Added history append + `_spawn_dm_thread` call after successful resolution. |
| 2026-06-05 | ACTION tab had no actor cycling UI — `_actor_idx` field existed but no prev/next buttons were built. Added `<`/`>` arcade GUI buttons at the actor name row in `setup_widget`; click handlers cycle `_actor_idx` and rebuild widgets. Actor count shown as `(N/total)` in label. |
| 2026-06-05 | ACTION tab buttons showed no action ratings — `_load_player_actors` built `ActorState` without fetching ratings from DB (`get_actor_action_ratings` never called). Fixed in `play_view.py`; button labels in `setup_widget` now read from `current_actor.actions` and display e.g. `FIGHT 2`. Widgets rebuild on actor switch so ratings refresh. 1787 passing (2 pre-existing UI-harness integration failures unrelated). |
| 2026-06-05 | DEBUG tab showed no context bundle or clocks — `_draw_debug_tab` never rendered bundle data. Added `clock_section_lines()` to `DebugControls` and called it in the draw method. Bundle now built eagerly when DBG tab is clicked. |
| 2026-06-05 | MEM tab search showed no results — `_rpg_memory.set_entries()` was never called; panel was always empty. Added `_load_memory_entries()` to `PlayView`; triggered on MEM tab click. Also fixed `entry.id` → `entry.memory_id` crash in `memory_inspector_panel.py`. |
| 2026-06-05 | DM narrated wrong actor after RESOLVE — action message to DM history had no actor name, so LLM defaulted to the first listed actor (Kira). Fixed in `_on_resolve_action`: actor display name now prefixed to the message (e.g. `Talvas the Wanderer [SENSE] ...`). |
| 2026-06-05 | World reaction applied body stress to all PC actors on miss/partial — `compute_world_reaction` iterated all `pc_actors` with no filter. Fixed by skipping actors whose `actor_id != resolution.actor_id`. 1688 passing (unit). |
| 2026-06-05 | DBG tab clock/reaction lines cut off at ~36 chars — `arcade.draw_text` has no max-width. Added `_wrap_debug_line()` helper in `play_view.py`; long lines wrap with preserved indentation. |
| 2026-06-06 | `seed_campaign_with_pack` saved clocks without metadata — `save_clock` was called with only `label`+`segments`, all Phase 35.5 fields (clock_level, scope_room_id, action_tags, etc.) were dropped. Fixed clock section in `seed_campaign_with_pack`; added `delete_clock` to repo and stale-clock cleanup on `--force`. 2 new tests. |
| 2026-06-06 | DBG tab froze app on clock display — `_wrap_debug_line` entered infinite loop when continuation indent spaces were found by `rfind`, producing the same string each iteration. Fixed by tracking `cur_min` and bumping it to `len(cont)` after first wrap. 7 new tests. |
| 2026-06-06 | Character/faction clock display showed UUID instead of actor name — `owner_actor_id` is a UUID5 with no reverse mapping. Fixed `ContextBundleBuilder._fetch_open_clocks` to enrich each clock dict with `owner_display_name` via `repo.get_actor()`; `debug_controls.clock_section_lines` prefers `owner_display_name`. 3 new tests. |
| 2026-06-06 | Seed file `scope_room_id` / `location_slug` used human slugs, not dungeon room IDs — `scope_room_id: "receiving-hall"` never matched `current_room_id: "R1"`, so room clocks were silently never scoped. Fixed both campaign seed files with actual room IDs (`R1`, `r01`, `3-A`, `2-B`, etc.). |
| 2026-06-06 | Level clocks advanced on wrong dungeon level — `compute_world_reaction` had no `level_id` filter; level-2 clocks advanced on level-1 actions. Added `current_level_id` param (derived as `f"level-{idx+1}"`) to `compute_world_reaction` and `react_to_resolution`; threaded through `PlayView._apply_world_reaction`. 5 new tests. |
| 2026-06-06 | `ClockState` in `_apply_world_reaction` missing `level_id` and other metadata — construction only passed `scope_room_id`+`action_tags`, so `clock.level_id` was always `None` and the new level filter never fired. Fixed by passing all metadata fields from the DB row. |

---

## Previous Phases

| Phase | Status | Tests |
|---|---|---|
| Phase 35.6 — Stress Routing by Action Intent | **Complete** (2026-06-06) | 1738 unit passing |
| Phase 35.5 — Clock Scoping, Clock Levels, Campaign Seed Upgrades | **Complete** (2026-06-06) | 1698 unit passing (post-bugfix) |
| Phase 35 — Deterministic World Reaction Service | **Complete** (2026-06-05) | 1818 passing |
| Phase 34 — Campaign RPG Data Deepening | **Complete** (2026-06-05) | 1802 passing |
| Phase 33 — Player-Controlled Action Loop | **Complete** (2026-06-04) | 1761 passing; live-app verified end-to-end |
| Phase 32 — Closeout pass | **Complete** (2026-06-03) | 1704 passing (excl. evals); see `docs/PHASE_32_CLOSEOUT.md` |
| Phase 32 step 32-6 — Smoke test + full pipeline test | **Complete** (2026-06-03) | 1708 passing |
| Phase 32 step 32-5 — Documentation | **Complete** (2026-06-03) | 1698 passing |
| Phase 32 step 32-4 — Balance pass | **Complete** (2026-06-03) | 1698 passing |
| Phase 32 step 32-3 — Repair tools | **Complete** (2026-06-03) | 1698 passing |
| Phase 32 step 32-2 — Golden context bundle snapshots | **Complete** (2026-06-03) | 1694 passing |
| Phase 31 — Context Bundles + AI Integration | **Complete** (2026-06-03) | 1686 passing |
| Phase 30 — Play Mode UI + Debug Tools | **Complete** (2026-06-03) | 1639 passing |
| Phase 29.5 — Campaign Save Folder Rename | **Complete** (2026-06-02) | 1575 passing |
| Phase 29 — Fallout + Dungeon Influence | **Complete** (2026-06-02) | 1568 passing |
| Phase 28 — Memory Persistence | **Complete** (2026-06-02) | 1549 passing |
| Phase 27 — RPG Core Loop | **Complete** (2026-06-02) | 1511 passing |
| Phase 26 — RPG + Memory Foundation | **Complete** (2026-06-02) | 1480 passing |
| Phase 25 — Map Visual Polish Phase 1 | **Complete** (2026-06-02) | 1410 passing |
| Phase 24 — Graph Mode Phase 4.1: Cleanup | **Complete** (2026-06-02) | 1395 passing (post-fix) |
| Phase 23 — Graph Mode Phase 4: Presentation, Detail Panel, Dungeon Personality | **Complete** (2026-06-01) | 1368 passing |
| Phase 22 — Graph Mode Phase 3: Interaction Polish | **Complete** (2026-05-31) | 1280 passing |
| Phase 21 — Graph Mode Phase 2.5: Semantic Metadata Backfill | **Complete** (2026-05-30) | 1184 passing |
| Phase 20 — Map Layout Visual Hierarchy (Phase 2) | **Complete** (2026-05-30) | 1097 passing |
| Phase 19 — Map Layout Phase 1 | **Complete** (2026-05-30) | 337 map tests |
| Post-Phase 18 — IP-1 through IP-9, MC-1 | **Complete** (2026-05-27) | 849 passing |
| Phase 18 — Python Code Quality Stabilisation | **Complete** | 664 passing |
| Phases 1–17 | **Complete** | — |

_Full session history in `spec/HISTORY.md`._

---

## Notes

- Player controls the player side: one or more player-controlled actors.
- Dungeon Daddy controls the dungeon, monsters, NPCs, factions, clocks, secrets, and consequences.
- The LLM is advisory. It may narrate or propose, but deterministic services apply authoritative state.
- World reactions implemented in Phase 35 via `WorldReactionService`.
- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
- RPG + Memory roadmap begins at Phase 26. See `spec/RPG_MEMORY_ROADMAP.md`.
- The RPG engine and memory layer are authoritative; the LLM is advisory.
- Use `spec/RPG_MEMORY_ARCHITECTURE.md`, `spec/RPG_MEMORY_DATA_MODEL.md`, `spec/RPG_SYSTEM_SPEC.md`, and `spec/MEMORY_SYSTEM_SPEC.md` only when relevant to the active task.

### Save Folder Structure (current)

Each campaign lives at `<campaigns_dir>/<campaign_slug>/`. The campaign's DuckDB and Markdown memory files live in the same folder. The `campaigns` table has a `dungeon_slug` column that records which dungeon design the campaign is running.

```
<campaigns_dir>/
  <campaign_slug>/
    dungeon.json        ← dungeon design (copied from source on clone)
    session.json        ← play session state
    campaign.duckdb     ← MemoryRepository (RPG state + memory)
    memory/             ← room play notes (level_N.md)
    rpg-memory/         ← Phase 28 Markdown narrative memory
      actors/
      events/
      fallout/
    setting.md          ← AI context docs (copied on clone)
    party.md
    level_N_design.md
```
