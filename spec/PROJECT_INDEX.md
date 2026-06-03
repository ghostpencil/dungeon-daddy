# Dungeon Daddy — Project Index

## Phase

Phase: 32 — Stabilization + Balancing
Status: **Complete** — Spec: `spec/PHASE_32_STABILIZATION_AND_BALANCING.md`

---

## Next Steps

| Step | Task | Status |
|---|---|---|
| 32-1 | Golden fixtures | Complete |
| 32-2 | Golden context bundle snapshots | Complete |
| 32-3 | Repair tools | Complete |
| 32-4 | Balance pass | Complete |
| 32-5 | Documentation | Complete |
| 32-6 | Smoke test + full pipeline test | **Complete** |

---

### Step Detail

#### 32-1 — Golden fixtures

Create a reusable in-memory/tmp campaign fixture for all Phase 32 tests.

**Contents:**
- One campaign with `dungeon_slug`
- One PC (Sable, action ratings spread across all tracks)
- One NPC (informant, low threat)
- One monster (Shard Golem, combat-capable)
- One dungeon emotional state (Dread, intensity 7)
- Three scenes: investigation, social, combat — each with location slugs and status
- One open clock (5-segment ritual)
- One active fallout (Sable, Stress track: Physical, severity moderate)
- One Weird fallout case (Sable, Weird track, severity severe)
- Several memory entries at varying importance (including one importance ≥ 9)

**Deliverable:** `tests/fixtures/phase32_campaign.py` — a helper function `seed_campaign(repo)` that seeds all the above into a `MemoryRepository` and returns IDs.

**Exit check:** Full test suite green; `seed_campaign` importable from fixture module.

---

#### 32-2 — Golden context bundle snapshots

Verify that retrieval order and provenance are deterministic against the golden fixture.

**Test file:** `tests/integration/test_context_bundle_snapshots.py`

Tracer bullets:
1. Build a context bundle from the golden fixture for the combat scene with Sable as focus actor.
2. Assert `memory_cards` order is stable across multiple builds (same seed → same order).
3. Assert `must_remember` contains the importance ≥ 9 entry regardless of token budget.
4. Assert `provenance.retrieved` + `provenance.omitted` equals total active memory count.
5. Assert `scene_brief.location_slug` matches the seeded combat scene.
6. Assert `mechanical_state` contains Sable's action ratings and stress tracks.
7. Assert `active_fallout` lists both fallout records for Sable.

**Exit check:** Snapshot test stable across two consecutive runs with identical seed.

---

#### 32-3 — Repair tools

Scripts in `tools/` for diagnosing and repairing campaign state.

**Files:**
- `tools/validate_campaign.py` — checks DuckDB/Markdown sync; reports any memory entries in DB without a corresponding `.md` file and vice versa
- `tools/rebuild_memory_projection.py` — drops and rebuilds the memory search projection from raw rows
- `tools/export_campaign.py` — exports full campaign state to a JSON bundle (actors, clocks, fallout, memory entries, scenes)
- `tools/import_campaign_fixture.py` — imports a JSON bundle into a new campaign DB (used to restore from export or load a test fixture)

**Test file:** `tests/integration/test_memory_repair_tools.py`

Tracer bullets:
1. `validate_campaign` against a clean golden fixture reports zero drift.
2. `validate_campaign` against a fixture with a deliberately missing `.md` file reports exactly that entry as drifted.
3. `export_campaign` produces a JSON bundle with all expected top-level keys.
4. `import_campaign_fixture` round-trips: export then import yields equivalent DB state.

---

#### 32-4 — Balance pass

Review RPG mechanical constants against the design thesis (see `spec/RPG_SYSTEM_SPEC.md`).

**Focus areas:**
- Action ratings 0–3: does rating 0 still contribute meaningfully? Does rating 3 feel powerful?
- Momentum cap: does it prevent hoarding without making momentum feel pointless?
- Stress track fill rate: does stress accumulate at a pace that matters but isn't constant punishment?
- Fallout severity: does mild fallout feel story-generative? Does severe fallout feel weighty but survivable?
- Weird stress: is the risk/reward ratio tempting enough? Does max Weird feel catastrophic and memorable?

**Deliverable:** Document findings in `spec/BALANCE_NOTES.md`. Apply any constant or threshold changes as targeted edits to the relevant modules. Add or adjust tests to lock in the tuned values.

---

#### 32-5 — Documentation

**Files to create:**
- `docs/GM_RULES.md` — GM-facing RPG summary: actions, momentum, stress, fallout, clocks, Weird. One page.
- `docs/ARCHITECTURE.md` — developer-facing system map: module list, dependency direction, threading rules, DB schema overview. Enough for Claude Code to continue future phases without re-deriving architecture.
- `docs/TROUBLESHOOTING.md` — common problems and fixes: DB drift, missing migrations, provider key issues, arcade window not launching.
- `docs/MIGRATION.md` — how to back up a campaign, apply a migration, and restore from export.

---

#### 32-6 — Smoke test + full pipeline test

**Test file:** `tests/integration/test_rpg_memory_full_pipeline.py`

End-to-end path: action roll → stress applied → fallout triggered → memory entry created → context bundle built → DM prompt generated.

Tracer bullets:
1. Seed golden fixture; perform an action roll that applies stress to Sable.
2. Assert stress track incremented.
3. Trigger fallout via `FalloutEngine`; assert fallout record created.
4. Create a memory entry referencing the fallout event; assert it appears in the next bundle.
5. Build a context bundle; assert the new memory card is present.
6. Pass bundle to `DMAgent.build_prompt()`; assert fallout title appears in prompt.
7. Assert full test suite remains green (1686 + new tests passing).

**Smoke script:** `tools/smoke_test_phase32.py` — interactive run of the above path; prints summary and saves artifact to `artifacts/play_mode/phase32/`.

---

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
