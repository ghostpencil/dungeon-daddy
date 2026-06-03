# Dungeon Daddy — Project Index

## Phase

Phase: 29 — Fallout + Dungeon Influence
Status: **Complete** (2026-06-02) — Spec: `spec/PHASE_29_FALLOUT_AND_DUNGEON_INFLUENCE.md`

---

## Next Steps

| Step | Task | Status |
|---|---|---|
| 29-1 | Fallout evaluator — `evaluate_fallout()`, severity ladder, stress reset | Done |
| 29-2 | Fallout catalog — 12 entries (4 tracks × 3 severities) | Done |
| 29-3 | Weird fallout special hooks — `dungeon_influence`, `write_memory`, `dungeon_knowledge_tag` | Done |
| 29-4 | Intimacy risk — `apply_intimacy_risk()`, Weird stress cost, cost tags per benefit type | Done |
| 29-5 | Fallout persistence — `save_fallout_record` / `get_fallout_records` in `MemoryRepository` | Done |
| 29-6 | Weird fallout Markdown — `write_fallout_markdown()` with correct front matter and tags | Done |

---

### Step Detail

#### 26-1 — Module skeletons

Create empty Python packages and placeholder module files. No logic yet.

**New directories / `__init__.py` files:**
- `dungeon_daddy/rpg/__init__.py`
- `dungeon_daddy/memory/__init__.py`
- `tests/unit/rpg/__init__.py`
- `tests/unit/memory/__init__.py`

**Placeholder source files (empty or `# TODO` stubs):**
- `dungeon_daddy/rpg/models.py`
- `dungeon_daddy/rpg/dice.py`
- `dungeon_daddy/rpg/actions.py`
- `dungeon_daddy/rpg/clocks.py`
- `dungeon_daddy/rpg/stress.py`
- `dungeon_daddy/rpg/service.py`
- `dungeon_daddy/memory/models.py`
- `dungeon_daddy/memory/repository.py`
- `dungeon_daddy/memory/markdown_store.py`
- `dungeon_daddy/memory/sync.py`

**Exit check:** `python -c "import dungeon_daddy.rpg; import dungeon_daddy.memory"` succeeds, full test suite still green.

---

#### 26-2 — Base RPG and memory models (TDD, tracer-bullet)

All model work uses real Pydantic v2. No mocks needed. Follow Red→Green→Refactor per behavior.

**Test file:** `tests/unit/rpg/test_models.py`

Tracer bullets (one at a time):

1. `ActorState` constructs with required fields; `status` defaults to `"active"`.
2. `StressTrack` stores `filled` count; rejects negative values.
3. `ClockState` stores `segments` and `filled`; `filled` cannot exceed `segments`.
4. `ActionRating` stores a single `action_key` and `rating` (0–3 range).
5. `ActionResolution` has outcome literal (`"critical"`, `"full"`, `"partial"`, `"miss"`).
6. `FalloutRecord` stores track, severity, and status literals.

**Test file:** `tests/unit/memory/test_models.py`

Tracer bullets:

1. `MemoryEntry` constructs with `id`, `type`, `title`; `status` defaults to `"active"`.
2. `DomainEvent` requires `event_type` and `campaign_id`; `occurred_at` auto-sets.
3. `ContextBundle` validates `mode` is one of the four literals.

**Source files:** `dungeon_daddy/rpg/models.py`, `dungeon_daddy/memory/models.py`

---

#### 26-3 — DuckDB migration runner (TDD)

**Prerequisite:** `duckdb` added to `pyproject.toml` dependencies (approval required).

Migration runner lives in `dungeon_daddy/memory/repository.py` as a standalone `MigrationRunner` class (or top-level functions). It does **not** touch any existing `data/repository.py`.

**Test file:** `tests/unit/memory/test_repository.py`

Tracer bullets:

1. Runner accepts a `migrations_dir: Path` and a `db_path: Path`. Returns list of `.sql` files sorted by name.
2. Runner applies one migration against a `tmp_path` DuckDB; creates `schema_migration` table on first run.
3. Runner records the migration name and timestamp in `schema_migration` after applying.
4. Running the same migration a second time is a no-op (idempotent). `schema_migration` has exactly 1 row.

**Source file:** `dungeon_daddy/memory/repository.py` (add `MigrationRunner`)

---

#### 26-4 — SQL migration file

**File:** `dungeon_daddy/data/migrations/001_rpg_memory_foundation.sql`

Tables to create (all with `IF NOT EXISTS`):

| Table | Key columns |
|---|---|
| `schema_migration` | `name TEXT PK`, `applied_at TIMESTAMP` |
| `campaigns` | `campaign_id`, `slug`, `title`, `status`, `created_at` |
| `sessions` | `session_id`, `campaign_id`, `session_number`, `played_at` |
| `scenes` | `scene_id`, `campaign_id`, `session_id`, `location_slug`, `status` |
| `actors` | `actor_id`, `campaign_id`, `actor_type`, `slug`, `display_name`, `status` |
| `action_ratings` | `actor_id`, `action_key`, `rating` |
| `stress_tracks` | `actor_id`, `track_key`, `capacity`, `filled` |
| `abilities` | `actor_id`, `ability_key`, `value` |
| `clocks` | `clock_id`, `campaign_id`, `label`, `segments`, `filled`, `status` |
| `action_resolutions` | `resolution_id`, `campaign_id`, `scene_id`, `actor_id`, `action_key`, `outcome`, `resolved_at` |
| `fallout` | `fallout_id`, `campaign_id`, `actor_id`, `track_key`, `severity`, `status` |
| `memory_entries` | `memory_id`, `campaign_id`, `type`, `title`, `summary`, `status`, `importance`, `markdown_path`, `checksum` |
| `memory_tags` | `memory_id`, `tag` |
| `memory_links` | `from_id`, `to_id`, `link_type` |
| `domain_events` | `event_id`, `campaign_id`, `event_type`, `payload TEXT`, `occurred_at TIMESTAMP` |

No foreign-key enforcement in first pass (DuckDB supports it but keep schema simple).

---

#### 26-5 — Markdown memory store shell (TDD)

**Test file:** `tests/unit/memory/test_markdown_store.py`

All tests use `tmp_path`. No mocks needed.

Tracer bullets:

1. `write_memory(path, front_matter, body)` creates a file. File starts with `---`.
2. `read_memory(path)` returns `(front_matter: dict, body: str)`. Round-trip preserves all front matter keys.
3. `compute_checksum(path)` returns a hex string; calling it twice on the same file returns the same string.
4. `validate_front_matter(data)` raises `ValueError` if any of `id`, `type`, `campaign_id`, `updated_at` are missing.
5. Front matter with unknown extra keys passes validation (forward-compatible).

**Source file:** `dungeon_daddy/memory/markdown_store.py`

Front matter format: YAML between `---` delimiters. Use stdlib `re` + `json`/manual parsing, or PyYAML if already approved. (Check before using PyYAML — not currently in deps.)

---

#### 26-6 — Repository health check and domain event insert (TDD)

**Test file:** `tests/unit/memory/test_repository.py` (extend existing file)

Tracer bullets:

1. `MemoryRepository(db_path)` opens a DuckDB connection; `.health_check()` returns `True`.
2. After `.initialize_schema(migrations_dir)`, all expected tables exist.
3. `.insert_domain_event(event: DomainEvent)` writes one row to `domain_events`.
4. `.get_domain_events(campaign_id)` retrieves the inserted event by campaign.
5. `.list_migrations()` returns names of applied migrations from `schema_migration`.
6. `.close()` releases the connection; subsequent calls to `.health_check()` raise or return `False`.

**Source file:** `dungeon_daddy/memory/repository.py` (add `MemoryRepository` class)

---

#### 26-7 — Integration tests for migration runner

**Test file:** `tests/integration/test_rpg_memory_migrations.py`

Tests (all against `tmp_path` DuckDB — no mocks):

1. Migration runner applies `001_rpg_memory_foundation.sql` against a fresh DB; `schema_migration` has 1 row.
2. Running the runner again on the same DB is idempotent; `schema_migration` still has 1 row.
3. All tables from Step 26-4 exist after migration.
4. `MemoryRepository.insert_domain_event()` + `.get_domain_events()` round-trip works post-migration.
5. No existing Play Mode tests regress (run full suite).

### Phase 25 Completed Steps (archived)

| Step | Task |
|---|---|
| ~~VP-1~~ | ~~Asset loading infrastructure — safe load helper for background PNG + 6 frame PNGs; log-once on missing; path resolution from package root~~ — **Done** |
| ~~VP-2~~ | ~~Background image — draw `background_graph_default.png` in `MapPanel`, Graph mode only, scissor-clipped, scaled to viewport, over solid fallback~~ — **Done** |
| ~~VP-3~~ | ~~Room frame textures — load and draw centered 136×96 frame PNGs in `LayoutRenderer._draw_rooms()`, scaled by zoom~~ — **Done** |
| ~~VP-4~~ | ~~Frame selection logic — `frame_current` > `frame_hover` > `frame_default`; stub hooks for memory/danger/locked frames~~ — **Done** |
| ~~VP-5~~ | ~~Regression pass — Grid mode, Tiles mode, zoom/pan, hit testing, selection, detail panel, existing tests all green~~ — **Done** |

### Phase 24 Completed Steps (archived)

| Step | Task |
|---|---|
| ~~4.1-1~~ | ~~Detail panel placement — avoid covering selected room and its connected paths~~ — **Done** |
| ~~4.1-2~~ | ~~Long linear floor framing — detect wide-vs-tall layout; improve padding/viewport bias for Crucible L3~~ — **Done** |
| ~~4.1-3~~ | ~~Crucible L2 marker scoring — fix marker application or justify zero-marker result without penalty~~ — **Done** |
| ~~4.1-4~~ | ~~Visibility feedback fields — add to presentation feedback JSON for all four target fixtures~~ — **Done** |
| ~~4.1-5~~ | ~~Artifact generation — screenshots + JSON feedback under `artifacts/layout/phase4_1/`~~ — **Done** |
| ~~4.1-6~~ | ~~Markdown summaries — `phase4_1_feedback_summary.md`, `before_after_summary.md`, `implementation_summary.md`~~ — **Done** |

### Phase 23 Completed Steps (archived)

| Step | Task |
|---|---|
| ~~1~~ | ~~`GraphPresentationConfig` dataclass — all toggles, defaults enabled~~ — **Done** |
| ~~2~~ | ~~Visible detail panel in Graph Mode (right-side/bottom-right card)~~ — **Done** |
| ~~3~~ | ~~Strengthen hover and selected-room styling; improve style resolver~~ — **Done** |
| ~~4~~ | ~~Role markers: `IN`, `OBJ`, `BOSS`, `!`, `KEY`, `↓`, `HUB` drawn in room boxes~~ — **Done** |
| ~~5~~ | ~~Connection markers: `critical_path`, `locked`, `secret`/`shortcut` (dashed), `vertical`~~ — **Done** |
| ~~6~~ | ~~Restrained atmosphere layer: vignette, subtle background, thin frame~~ — **Done** |
| ~~7~~ | ~~Artifact generation script + screenshots and JSON reports under `artifacts/layout/phase4/`~~ — **Done** |
| ~~8~~ | ~~Integration tests: geometry, semantic, metadata, interaction score regressions; Grid Mode untouched~~ — **Done** |

### Phase 22 Completed Steps (archived)

| Step | Task |
|---|---|
| ~~1~~ | ~~Phase 2.5 cleanup: refine objective warning naming in `validation.py`~~ — **Done** (1188 passing) |
| ~~2~~ | ~~Connection metadata backfill for `crucible.json`, `tomb.json`, and local dungeon files~~ — **Done** (1199 passing) |
| ~~2a~~ | ~~Renderer visual parity: role-based border color, fill color, marker position~~ — **Done** (1194 passing) |
| ~~3~~ | ~~`GraphViewState` model~~ — **Done** (1211 passing) |
| ~~4~~ | ~~Room + connection hit testing~~ — **Done** (1220 passing) |
| ~~5~~ | ~~Style resolution pipeline~~ — **Done** (1228 passing) |
| ~~6~~ | ~~Room hover visual state~~ — **Done** (1232 passing) |
| ~~7~~ | ~~Room selection + focus mode~~ — **Done** (1235 passing) |
| ~~8~~ | ~~Connection hover~~ — **Done** (1238 passing) |
| ~~9~~ | ~~Room detail panel (`room_detail_panel.py`)~~ — **Done** (1262 passing) |
| ~~10~~ | ~~Critical path emphasis when selected room is on path~~ — **Done** (1265 passing) |
| ~~11~~ | ~~Keyboard controls: R = recenter, Escape = clear selection~~ — **Done** (1271 passing) |
| ~~12~~ | ~~Artifact generation script + screenshots under `artifacts/layout/phase3/`~~ — **Done** (1276 passing) |
| ~~13~~ | ~~Integration tests: geometry/semantic/metadata scores do not regress~~ — **Done** (1279 passing) |
| ~~14~~ | ~~Output artifacts: feedback JSON, summary MDs, migration report~~ — **Done** (1280 passing) |

---

## Known Failures

_None._

## Bug Fixes (post-Phase 24)

| Date | Fix |
|---|---|
| 2026-06-02 | Atmosphere frame misalignment — `_draw_atmosphere` was centering on `(canvas_w/2, canvas_h/2)` instead of `(viewport_x + canvas_w/2, viewport_y + canvas_h/2)`, causing the frame to draw relative to screen origin rather than the map panel. Fixed in `layout_renderer.py:_draw_atmosphere`. 1395 passing. |

---

## Previous Phases

| Phase | Status | Tests |
|---|---|---|
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

Each dungeon lives at `<dungeons_dir>/<dungeon_name>/`. The campaign's DuckDB and Markdown memory files live in the same folder. The `campaigns` table has a `dungeon_slug` column (added post-Phase 28) that records which dungeon folder the campaign belongs to.

```
<dungeons_dir>/
  <dungeon_name>/
    dungeon.json        ← dungeon design
    session.json        ← play session state
    campaign.duckdb     ← MemoryRepository (RPG state + memory)
    memory/             ← room play notes (level_N.md)
    rpg-memory/         ← Phase 28 Markdown narrative memory
    setting.md          ← AI context docs
    party.md
    level_N_design.md
```

### Phase 29.5 — Campaign Save Folder Rename (planned, post-Phase 29)

After Phase 29 is stable, rename the save structure so the **campaign** is the primary save entity. The GM's "save file" becomes the campaign name, not the dungeon name. Key changes:
- `AppConfig.dungeons_dir` → `campaigns_dir`
- Folder name = campaign `slug`
- `DungeonRepository.clone_dungeon(source, dest)` added for running same dungeon with a new group
- `dungeon_slug` column becomes "source template" reference only

See `spec/IMPLEMENTATION_PHASES.md` Phase 29.5 for full detail.
