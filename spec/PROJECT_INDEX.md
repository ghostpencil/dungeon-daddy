# Dungeon Daddy — Project Index

## Phase

Phase: 33 — (not yet defined)
Status: **Ready to plan** — Phase 32 closed out 2026-06-03. See `docs/PHASE_32_CLOSEOUT.md`.

---

## Next Steps

Phase 33 not yet scoped. Top deferred items from Phase 32 closeout:

| Priority | Item | Notes |
|---|---|---|
| 1 | Wire `ContextBundleBuilder` into `PlayView._spawn_dm_thread` | Bundle built but never passed to `agent.respond()` — DM still uses room-memory-only path during live play |
| 2 | Memory provenance in Debug tab | `bundle.provenance` data available; UI not wired |
| 3 | LLM-drafted memory entry approval flow | `[DRAFT]` label renders in prompt; persist/approve logic not implemented |

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

---

## Previous Phases

| Phase | Status | Tests |
|---|---|---|
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
