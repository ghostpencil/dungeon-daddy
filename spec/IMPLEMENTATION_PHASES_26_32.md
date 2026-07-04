# Implementation Phases — 26 through 32 (RPG + Memory Foundation)

## Phase 26 — RPG + Memory Foundation

**Status: Complete** — 1480 unit+integration tests passing. Closed 2026-06-02.

Spec: `spec/PHASE_26_RPG_MEMORY_FOUNDATION.md`

Create module skeletons, base models, migration runner, DuckDB repository shell, and Markdown memory store shell.

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| 26-1 | Add RPG and memory module skeletons | Done |
| 26-2 | Add base RPG and memory models | Done |
| 26-3 | Add DuckDB migration runner | Done |
| 26-4 | Add `001_rpg_memory_foundation.sql` migration | Done |
| 26-5 | Add Markdown memory store shell | Done |
| 26-6 | Add repository health check and domain event insert | Done |
| 26-7 | Add unit/integration tests for foundation modules | Done |

---

## Phase 27 — RPG Core Loop

**Status: Complete** — 1511 unit+integration tests passing. Closed 2026-06-02.

Spec: `spec/PHASE_27_RPG_CORE_LOOP.md`

Implement headless Charge-style action resolution, momentum, clocks, stress tracks, and RPG service orchestration.

---

## Phase 28 — Memory Persistence

**Status: Complete** — 1546 unit+integration tests passing. Closed 2026-06-02.

Spec: `spec/PHASE_28_MEMORY_PERSISTENCE.md`

Persist campaigns, sessions, scenes, actors, actions, clocks, domain events, memory entries, Markdown files, tags, and links.

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| 28-1 | Campaign / actor / stress track / action rating persistence | Done |
| 28-2 | Clock + action resolution persistence | Done |
| 28-3 | Memory entry CRUD — save, get, tags, links, checksum update | Done |
| 28-4 | Sync report — missing file, invalid front matter, checksum mismatch, orphan Markdown/DB | Done |
| 28-5 | Deterministic retrieval — by actor, location, tag, importance rank | Done |
| 28-6 | Integration roundtrip — RPG state + memory survive restart | Done |

### Post-Phase 28 — Campaign-Dungeon Link

Add `dungeon_slug` column to `campaigns` table via migration `002_dungeon_slug.sql`.

This links each campaign row to the dungeon folder it was started from (`DungeonRepository` uses folder name as the dungeon identifier). The `dungeon_slug` records which dungeon design the campaign is running — it is the folder name under `dungeons_dir`, not a file path.

| Step | Task | Status |
|---|---|---|
| 28-X1 | Add `002_dungeon_slug.sql` migration — `ALTER TABLE campaigns ADD COLUMN dungeon_slug TEXT` | Not Started |
| 28-X2 | Add `save_campaign` overload / update to accept `dungeon_slug` param | Not Started |
| 28-X3 | Update `get_campaign` to return `dungeon_slug` in the result dict | Not Started |
| 28-X4 | Tests: save campaign with dungeon_slug, retrieve, confirm round-trip | Not Started |

---

## Phase 29 — Fallout + Dungeon Influence

**Status: Complete** — 1568 unit+integration tests passing. Closed 2026-06-02.

Spec: `spec/PHASE_29_FALLOUT_AND_DUNGEON_INFLUENCE.md`

Implement Body, Composure, Bonds, and Weird fallout; intimacy risk; dungeon influence; and memory projection for consequences.

---

## Phase 29.5 — Campaign Save Folder Rename

**Status: Complete** — 1575 tests passing. Closed 2026-06-03.

No spec file yet. This is a structural rename with no new game behaviour.

### Background

Currently the save folder structure is `<dungeons_dir>/<dungeon_name>/`. The primary entity is the dungeon; campaign save data (DuckDB, Markdown memory, session state) is attached to it.

The intended end state is that the **campaign** is the primary save entity: `<campaigns_dir>/<campaign_slug>/`. A GM's "save file" is their campaign name, not the dungeon design name. Multiple campaigns can run the same dungeon by cloning the dungeon folder first.

### What to build

| Step | Task |
|---|---|
| 29.5-1 | `DungeonRepository.clone_dungeon(source_slug, dest_slug)` — copies `dungeon.json` and all context docs (`setting.md`, `party.md`, `level_*_design.md`); does NOT copy `session.json`, `campaign.duckdb`, `memory/`, `rpg-memory/` |
| 29.5-2 | Rename `AppConfig.dungeons_dir` → `AppConfig.campaigns_dir`; update all call sites |
| 29.5-3 | Rename `DungeonRepository.__init__(dungeons_dir)` parameter → `campaigns_dir`; update all call sites |
| 29.5-4 | Convention: campaign folder name = campaign `slug`; `dungeon_slug` column on `campaigns` table becomes a "source template" reference only |
| 29.5-5 | Update `DungeonRepository.list_dungeons()` → `list_campaigns()`; deprecation alias kept for one phase |
| 29.5-6 | Migration guide note in `spec/HISTORY.md` — folder rename is breaking for existing save data; instruct users to rename their `dungeons/` directory to `campaigns/` |
| 29.5-7 | Full test suite green; no behaviour change for existing dungeons/campaigns |

### Why defer

This is a pure rename. It touches `AppConfig`, `DungeonRepository`, and all call sites but adds no new game capability. Doing it mid-build (before Phase 29 fallout is stable) adds noise. Run it as a clean, dedicated pass once Phase 29 is closed.

### Save folder layout (target state)

```
<campaigns_dir>/
  <campaign_slug>/          ← folder name IS the campaign save name
    dungeon.json            ← dungeon design (copied from source template on clone)
    session.json            ← play session state
    campaign.duckdb         ← MemoryRepository — RPG state + narrative memory
    memory/                 ← existing room play notes (level_N.md)
    rpg-memory/             ← Phase 28 Markdown narrative memory files
      actors/
      events/
      fallout/
    setting.md              ← AI context docs (copied on clone)
    party.md
    level_N_design.md
```

---

## Phase 30 — Play Mode UI + Debug Tools

**Status: Complete** — 1639 unit+integration tests passing. Closed 2026-06-03.

Spec: `spec/PHASE_30_PLAY_MODE_UI_AND_DEBUG_TOOLS.md`

Expose RPG state, clocks, fallout, and memory in Play Mode using panels and debug tools. Added CharacterSheetPanel, SceneStatePanel, FalloutPanel, MemoryInspectorPanel, and DebugControls behind a collapsible RPG side panel with five tabs (CHAR / SCENE / FALLOUT / MEM / DBG). Smoke test passes all 8 behaviors.

---

## Phase 31 — Context Bundles + AI Integration

**Status: Complete** — 1686 unit+integration tests passing. Closed 2026-06-03.

Spec: `spec/PHASE_31_CONTEXT_BUNDLES_AND_AI_INTEGRATION.md`

Built `MemoryRetriever` (tag/actor/location filtering, importance+recency ranking, token budget trim), `ContextBundleBuilder` (assembles `ContextBundle` from real DuckDB: scene brief, mechanical state, fallout, clocks, memory cards, provenance), `DMAgent.build_prompt(context_bundle)` (injects bundle into system prompt), and `DebugControls.set_bundle()` / `bundle_section_lines()` for provenance display. Bug fix: `dm_agent.build_prompt()` clock label key was `name`; repo uses `label`. Context bundle not yet wired into live app UI flow — wiring is a Phase 32+ concern.

---

## Phase 32 — Stabilization + Balancing

**Status: Complete** — 1708 unit+integration tests passing. Closed 2026-06-03.

Spec: `spec/PHASE_32_STABILIZATION_AND_BALANCING.md`

Hardened end-to-end tests, smoke tests, golden fixtures, sync repair tools, balance pass, and documentation. All six steps complete.

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| 32-1 | Golden fixtures (`tests/fixtures/phase32_campaign.py`) | Done |
| 32-2 | Golden context bundle snapshots (`tests/integration/test_context_bundle_snapshots.py`) | Done |
| 32-3 | Repair tools (`validate_campaign`, `rebuild_memory_projection`, `export_campaign`, `import_campaign_fixture`) | Done |
| 32-4 | Balance pass — constants locked in `spec/BALANCE_NOTES.md` | Done |
| 32-5 | Documentation (`docs/GM_RULES.md`, `ARCHITECTURE.md`, `TROUBLESHOOTING.md`, `MIGRATION.md`) | Done |
| 32-6 | Full pipeline test + smoke script (`test_rpg_memory_full_pipeline.py`, `smoke_test_phase32.py`) | Done |

### Exit Criteria

- [x] End-to-end action → stress → fallout → memory → context → DM narration path works
- [x] Sync validator catches and reports drift
- [x] Golden context bundle snapshots are stable
- [x] Documentation sufficient for future phases without re-deriving architecture
- [x] Full test suite remains green (1708 passing)

---

## Notes for the Implementing Agent

- **Do not advance to the next phase until all exit criteria for the current phase are met.**
- **Each phase's test files are written before the module they cover.** See `spec/TESTING.md`.
- **Update this file** when a phase is complete: change `Not Started` → `Complete`
  (or `In Progress` if partially done).
- Phases 1–4 have no Arcade display dependency — run them in any environment.
- Phases 5–8 require a display; on headless CI, skip arcade-rendering tests using
  `pytest -m "not requires_display"` (mark those tests accordingly).

---


