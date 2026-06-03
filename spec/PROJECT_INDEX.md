# Dungeon Daddy — Project Index

## Phase

Phase: 31 — Context Bundles + AI Integration
Status: **Complete** — Spec: `spec/PHASE_31_CONTEXT_BUNDLES_AND_AI_INTEGRATION.md`

Next phase: 32 — Stabilization + Balancing (`spec/PHASE_32_STABILIZATION_AND_BALANCING.md`)

---

## Next Steps

| Step | Task | Status |
|---|---|---|
| 31-1 | Module skeletons | Complete |
| 31-2 | Memory retrieval (TDD) | Complete |
| 31-3 | Context bundle generator (TDD) | Complete |
| 31-4 | DM agent update (TDD) | Complete |
| 31-5 | Memory provenance debug display (TDD) | Complete |
| 31-6 | Integration tests | Complete |
| 31-7 | Smoke test | Complete |

---

### Step Detail

#### 31-1 — Module skeletons

Create empty Python files for the two new memory modules.

**New files:**
- `dungeon_daddy/memory/retrieval.py`
- `dungeon_daddy/memory/context_bundle.py`

**Exit check:** `python -c "from dungeon_daddy.memory import retrieval, context_bundle"` succeeds; full test suite still green.

---

#### 31-2 — Memory retrieval (TDD)

**Test file:** `tests/unit/memory/test_retrieval.py`

Tracer bullets:
1. `MemoryRetriever` accepts a `MemoryRepository` and a campaign ID.
2. `.query(tags=[], actor_ids=[], location_slug=None)` returns a list of `MemoryEntry` objects matching any filter.
3. Results are ranked by importance (descending), then recency.
4. `.query()` with no filters returns all active entries for the campaign.
5. Entries with status `"archived"` are excluded unless `include_archived=True` is passed.
6. Token budget trim: `.trim_to_budget(entries, max_tokens)` returns a prefix of entries whose estimated token count stays within budget, and records how many were omitted.

**Source file:** `dungeon_daddy/memory/retrieval.py`

---

#### 31-3 — Context bundle generator (TDD)

**Test file:** `tests/unit/memory/test_context_bundle.py`

Tracer bullets:
1. `ContextBundleBuilder` accepts `campaign_id`, `scene_id`, `mode`, `focus_actor_ids`, `token_budget`.
2. `.build(repo)` returns a `ContextBundle` with `bundle_id`, `campaign_id`, `scene_id`, `mode`.
3. `scene_brief` field is populated from the scenes table (title, location slug, status).
4. `mechanical_state` includes each focus actor's action ratings, momentum, and stress tracks.
5. `active_fallout` lists all non-resolved fallout records for focus actors.
6. `open_clocks` lists all clocks with status `"open"` for the campaign.
7. `memory_cards` are retrieved via `MemoryRetriever`, ranked, and trimmed to token budget.
8. `provenance` records how many memories were retrieved, how many trimmed, and the filter criteria used.
9. `must_remember` entries (importance ≥ 9) are always included regardless of budget.

**Source file:** `dungeon_daddy/memory/context_bundle.py`

---

#### 31-4 — DM agent update (TDD)

**Test file:** `tests/unit/llm/test_dm_agent_context_bundle.py`

Tracer bullets:
1. `DMAgent.build_prompt(context_bundle=None)` returns the existing prompt when no bundle is passed (no regression).
2. When a bundle is provided, the system prompt includes the scene brief and mechanical state.
3. Memory cards are injected as a numbered list with title, summary, and importance.
4. Active fallout and open clocks are appended as a mechanical context block.
5. LLM output is returned as-is; no RPG or memory state is mutated.
6. If the bundle has draft memory content, it is labelled `[DRAFT]` in the prompt.

**Source file:** `dungeon_daddy/llm/agents/dm_agent.py`

No real API call in unit tests — inject a mock LLM provider.

---

#### 31-5 — Memory provenance debug display (TDD)

Update the debug controls panel to show the most recently built context bundle.

**Test file:** `tests/unit/ui/test_debug_controls.py` (extend existing)

Tracer bullets:
1. `DebugControls` accepts an optional `last_bundle: ContextBundle | None`.
2. When `last_bundle` is set, rendering includes a "Context bundle" section showing `bundle_id`, memory card count, and trimmed count.
3. Each memory card is listed with title and reason for inclusion (tag match, importance, actor match).
4. When `last_bundle` is None, the section shows "No bundle built yet".

**Source file:** `dungeon_daddy/ui/panels/debug_controls.py` (extend)

---

#### 31-6 — Integration tests

**Test files:**
- `tests/integration/test_context_bundle_retrieval.py`
- `tests/integration/test_dm_agent_with_rpg_memory_context.py`

Tests (no mocks for RPG/memory layer; mock LLM provider):
1. `ContextBundleBuilder.build()` against a real `tmp_path` DuckDB populates all bundle fields from seeded data.
2. Retriever query filters by tag, actor, and location against real DB rows.
3. Token budget trim leaves `provenance.omitted_count` accurate.
4. `DMAgent` with a real bundle builds a prompt that contains the scene brief text.
5. `DMAgent` fallback (no bundle) still returns a valid prompt — existing behavior not broken.
6. No existing tests regress (run full suite).

---

#### 31-7 — Smoke test

**File:** `tools/smoke_test_phase31.py`

Script flow:
1. Create a test campaign DB in `tmp_path`; seed actors, clocks, fallout, and memory entries.
2. Build a context bundle for a seeded scene.
3. Print bundle summary (scene brief, mechanical state, memory card count, provenance).
4. Build a DM prompt from the bundle using a mock provider; print first 200 chars.
5. Assert bundle fields are non-empty; assert prompt contains scene brief.
6. Save bundle JSON artifact to `artifacts/play_mode/phase31/bundle_sample.json`.

---

## Known Failures

_None._

## Step 31-7 Completion Notes

- `tools/smoke_test_phase31.py` — 8 behaviors; real DuckDB via `tempfile.TemporaryDirectory`; mock LLM provider
  - Builds context bundle from seeded campaign (scene, actor, clock, fallout, memory entries)
  - Verifies scene_brief, mechanical_state, memory_cards, must_remember, active_fallout, open_clocks, provenance
  - Verifies `DMAgent.build_prompt(bundle)` injects location slug and memory card title into prompt
  - Saves bundle JSON artifact to `artifacts/play_mode/phase31/bundle_sample.json`
- Bug fixed: `dm_agent.py` `build_prompt()` used `c['name']` for clock label but repo dict key is `label` → changed to `c.get('label', c.get('name', ''))`
- Manual UI regression tests all passed (6/6): Play Mode launch, DM chat fallback, RPG panel all tabs, DBG tab, MEM search input, tab switch/reopen
- 1686 passing (no new tests added; bug fix only)

## Step 31-6 Completion Notes

- `tests/integration/test_context_bundle_retrieval.py` — 10 tests; real DuckDB via `tmp_path`; no LLM mocks
  - `TestContextBundleBuilderIntegration`: all bundle fields populated from seeded data (scene_brief, mechanical_state, open_clocks, active_fallout, memory_cards, must_remember)
  - `TestMemoryRetrieverFilters`: query by tag, location_slug, no-filter; archived excluded
  - `TestTokenBudgetTrim`: provenance omitted count accurate with tiny budget
- `tests/integration/test_dm_agent_with_rpg_memory_context.py` — 5 tests; real bundle from real DB; mock LLM provider
  - build_prompt with real bundle contains scene location slug and memory card title
  - fallback (no bundle) returns system prompt unchanged
  - respond() with real bundle sets system to contain scene location; without bundle returns provider output
- 1686 passing

## Step 31-5 Completion Notes

- `DebugControls.set_bundle(bundle: ContextBundle)` stores bundle as `_last_bundle`
- `DebugControls.bundle_section_lines() -> list[str]` returns header (`bundle_id`, card count, trimmed count) + one line per card (`title [importance|retrieved]`)
- Reason derived from `must_remember`: if `memory_id` in `must_remember` → `"importance"`, otherwise `"retrieved"`
- When `_last_bundle` is None → returns `["No bundle built yet"]`
- 4 new tests in `tests/unit/ui/test_debug_controls.py`; 1671 passing

## Step 31-4 Completion Notes

- `DungeonMasterAgent.build_prompt(context_bundle=None)` added to `dungeon_daddy/llm/agents/dm_agent.py`
- No bundle → returns `self._system_prompt` unchanged
- With bundle → appends `# Scene` (location_slug + status), `# Memory` (numbered list: title, summary, importance; `[DRAFT]` prefix when `card["draft"] is True`), `# Mechanical Context` (active fallout + open clocks)
- `respond()` gained `context_bundle=None` parameter; calls `build_prompt(context_bundle)` as base system prompt
- 11 new tests in `tests/unit/llm/test_dm_agent_context_bundle.py`
- All existing DM agent tests green; 1667 passing

## Step 31-3 Completion Notes

- `ContextBundleBuilder` in `dungeon_daddy/memory/context_bundle.py`: accepts `campaign_id`, `scene_id`, `mode`, `focus_actor_ids`, `token_budget`
- `.build(repo)` returns a `ContextBundle` (from `memory/models.py`) with all fields populated:
  - `scene_brief` — queried from `scenes` table (`scene_id`, `location_slug`, `status`; no title column in schema)
  - `mechanical_state` — per focus actor: action ratings + stress tracks (no momentum in schema)
  - `active_fallout` — non-resolved fallout for focus actors
  - `open_clocks` — clocks with `status="active"` for the campaign
  - `memory_cards` — retrieved via `MemoryRetriever`, budget-trimmed; importance ≥ 9 entries pinned and always included
  - `must_remember` — list of `memory_id` strings for importance ≥ 9 entries
  - `provenance` — `retrieved`, `omitted`, `focus_actor_ids`
- 9 new tests in `tests/unit/memory/test_context_bundle.py::TestContextBundleBuilder`
- 1656 passing

## Step 31-2 Completion Notes

- Added `dungeon_daddy/data/migrations/003_memory_created_at.sql` — adds `created_at TIMESTAMP` to `memory_entries`
- `MemoryEntry` model gained `created_at: datetime | None` field
- New `MemoryRetriever` class in `retrieval.py`: `.query(tags, actor_ids, location_slug, include_archived)` → `list[MemoryEntry]` ranked by importance desc then recency desc; `.trim_to_budget(entries, max_tokens)` → `(kept, omitted_count)`
- Old `MemoryRetrieval` class retained (unchanged); all existing tests green
- 7 new tests in `tests/unit/memory/test_retrieval.py::TestMemoryRetriever`

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
| Phase 31 — Context Bundles + AI Integration | **Complete** (2026-06-03) | 1686 passing |
| Phase 31 step 31-5 — Memory provenance debug display (TDD) | **Complete** (2026-06-03) | 1671 passing |
| Phase 31 step 31-4 — DM agent update (TDD) | **Complete** (2026-06-03) | 1667 passing |
| Phase 31 step 31-3 — Context bundle generator (TDD) | **Complete** (2026-06-03) | 1656 passing |
| Phase 31 step 31-2 — Memory retrieval (TDD) | **Complete** (2026-06-03) | 1646 passing |
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
