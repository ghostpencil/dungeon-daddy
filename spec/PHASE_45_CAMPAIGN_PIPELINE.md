# Phase 45 — Campaign Pipeline: Dungeon Library → Campaign Seeds → Save Games

**Status: Complete (2026-06-14) — 2436 tests passing**
Branch: `phase-45-campaign-pipeline`

## Goal

Wire the three existing modes (Design, Campaign, Play) into a real authoring →
publishing → playing pipeline backed by three on-disk libraries. A user designs a
**Dungeon** (reusable template), attaches and edits a **Campaign Seed** against it, then
**publishes** a self-contained **Save Game** (`dungeon + seed + live state`) and plays it.

## Why

The three modes work in isolation but nothing carries one mode's output to the next.
Today everything for a "campaign" is jammed into one folder (`campaigns/<name>/`) mixing
the dungeon template, manifest, RPG DB, and live play state. There is no reusable dungeon
library, no way to attach a campaign to a dungeon, and no publish step. `CampaignManifest`
already has a `dungeon_slug` field but no UI sets it and nothing instantiates a playable
game from it.

## Locked design decisions

1. **Three on-disk libraries** — `dungeons/`, `campaign_seeds/`, `saves/`.
2. **Snapshot saves** — publish *copies* the dungeon + seed into the save; the save is
   self-contained and immune to later library edits.
3. **Auto-migrate** existing `campaigns/*` into the new layout once, idempotently.
4. **Dedicated Library home screen** as the landing/hub view.

This ends STABILIZATION and opens BUILD Phase 45.

---

## Target storage layout

```
DungeonDaddy/
  dungeons/<dungeon-slug>/
    dungeon.json
    setting.md, party.md, level_*_design.md
  campaign_seeds/<seed-slug>/
    campaign.json            # CampaignManifest (dungeon_slug -> a dungeons/ entry)
  saves/<save-slug>/
    dungeon.json             # snapshot copy
    campaign.json            # snapshot copy of the seed
    campaign.duckdb          # seeded from the manifest at publish time
    session.json             # live play state
    memory/level_*.md
    assets/portraits/
  campaigns/                 # legacy; migrated then marked done
```

## Mode semantics after this change

- **Design** edits a **Dungeon** from `dungeons/`; save → `dungeons/<slug>/`.
- **Campaign** edits a **Campaign Seed** from `campaign_seeds/`, with an **Attach Dungeon**
  picker (lists `dungeons/`) and a **Publish** action.
- **Play** runs a **Save Game** from `saves/`.
- **Library** (new) is the hub: browse all three; launch the right mode for a selection.

---

## Reuse (do NOT re-implement)

- `DungeonRepository` (`dungeon_daddy/data/repository.py`) — dungeon.json + context docs +
  session + room memory CRUD. Instantiate twice: rooted at `dungeons_dir` and `saves_dir`.
- `DungeonRepository.clone_dungeon()` — copies `dungeon.json` + context docs, excludes live
  state. Extend to copy **across two roots** for publish.
- `seed_from_manifest()` (`dungeon_daddy/campaign/seeder.py`) — seeds DuckDB from a manifest.
- `validate_manifest()` (`dungeon_daddy/campaign/validator.py`) — gate before publish.
- `MemoryRepository` + `dungeon_daddy/data/migrations/` — create/seed `campaign.duckdb`.
- `CampaignManifest` (`dungeon_daddy/campaign/manifest.py`) — already the seed model.

---

## TDD Slices

> Read `spec/TESTING.md` before each new test file; use the TDD skill for new modules.
> Read `spec/UI_TESTING.md` before Slice 6 (Library view).

### Slice 0 — Config & directories

**Files modified/created:**
- `dungeon_daddy/config.py`
- `tests/unit/test_config.py`

**Acceptance criteria:**
- `AppConfig` exposes `dungeons_dir`, `campaign_seeds_dir`, `saves_dir` properties under
  `user_data_dir`.
- `ensure_dirs()` creates all three (plus existing `campaigns_dir`); idempotent.

---

### Slice 1 — Dungeon library wiring

**Files modified:**
- `dungeon_daddy/window.py` (construct dungeon-library repo at `dungeons_dir`; point
  `open_dungeon`, `save_dungeon`, context-doc generation there)
- relevant tests under `tests/unit/` for window save/open routing

**Acceptance criteria:**
- Saving a dungeon in Design mode writes to `dungeons/<slug>/dungeon.json`.
- Open-dungeon picker lists entries from the dungeons library.
- Context docs generate into the dungeon-library folder.

---

### Slice 2 — Campaign Seed library

**Files created:**
- `dungeon_daddy/campaign/seed_library.py`
- `tests/unit/campaign/test_seed_library.py`

**Acceptance criteria:**
- `CampaignSeedLibrary(seeds_dir)` exposes `list()`, `load(slug) -> CampaignManifest`,
  `save(manifest)`, `exists(slug)`.
- `save` writes `campaign_seeds/<slug>/campaign.json` (indent=2, readable).
- Round-trip: `save(m)` then `load(m.slug)` returns an equal manifest.
- `load` of a missing slug raises `FileNotFoundError`; `list()` returns sorted slugs.

---

### Slice 3 — Attach dungeon + seed persistence in Campaign mode

**Files modified:**
- `dungeon_daddy/views/campaign_view.py` (use `CampaignSeedLibrary` for load/save; add an
  **Attach Dungeon** picker listing dungeon-library slugs; show attached dungeon name)
- `tests/unit/.../test_campaign_view*.py`

**Acceptance criteria:**
- Attaching a dungeon sets `manifest.dungeon_slug` and surfaces the name in the UI.
- Saving persists the seed to the seed library (not an arbitrary file path).
- Loading a seed restores `dungeon_slug` and all manifest fields.
- A seed with no attached dungeon cannot be published (enforced in Slice 4).

---

### Slice 4 — Publish service (core of the pipeline)

**Files created:**
- `dungeon_daddy/campaign/publish.py`
- `tests/unit/campaign/test_publish.py`

**API:** `publish_save(manifest, dungeons_dir, saves_dir, save_slug, migrations_dir) -> str`

**Steps:** validate manifest (abort on errors / missing `dungeon_slug`) → create
`saves/<save_slug>/` → copy `dungeon.json` + context docs from
`dungeons/<manifest.dungeon_slug>/` (cross-root copy helper extracted from `clone_dungeon`)
→ copy manifest to `saves/<save_slug>/campaign.json` → create `campaign.duckdb`,
`initialize_schema`, `save_campaign(...)`, `seed_from_manifest(...)` → write initial
`session.json` = `SessionState(dungeon_id=save_slug)`.

**Acceptance criteria:**
- Publishing an invalid manifest (or one with empty `dungeon_slug`) raises and writes
  nothing.
- After publish, `saves/<slug>/` contains `dungeon.json`, `campaign.json`,
  `campaign.duckdb`, `session.json`.
- `campaign.duckdb` contains the manifest's actors / clocks / factions / memory seeds.
- **Snapshot independence:** editing the source `dungeons/<dungeon_slug>/dungeon.json`
  after publish does not change the published save's `dungeon.json`.
- Publishing twice to distinct `save_slug`s yields two independent saves.

---

### Slice 5 — Play loads Save Games

**Files modified:**
- `dungeon_daddy/window.py` (save repo at `saves_dir`; `launch_save_game(save_slug)`;
  `_attach_rpg_context` resolves `saves/<slug>/campaign.duckdb` + `assets/portraits`)
- `dungeon_daddy/views/play_view.py` (session keyed by save slug; loads from save folder)
- `dungeon_daddy/views/design_view.py` (keep Test Drive; remove the old "Start Play" path)
- relevant tests

**Acceptance criteria:**
- `launch_save_game(slug)` loads the save's dungeon + session and attaches its DuckDB.
- Session round-trips to `saves/<slug>/session.json`.
- Room memory reads/writes under `saves/<slug>/memory/`.
- Test Drive (transient, no save) remains available from Design mode; the old "Start Play"
  from Design is superseded by the publish pipeline.

---

### Slice 6 — Library home screen (new view)

**Files created:**
- `dungeon_daddy/views/library_view.py`
- supporting panels under `dungeon_daddy/ui/panels/` as needed
- `tests/unit/.../test_library_view*.py` (per `spec/UI_TESTING.md`)

**Files modified:**
- `dungeon_daddy/ui/chrome.py` (Library navigation — Home button or 4th pill)
- `dungeon_daddy/window.py` (show Library on startup)

**Acceptance criteria:**
- Library shows three sections — **Dungeons**, **Campaign Seeds**, **Saves** — populated
  from the respective repos/libraries.
- Card actions fire the correct window methods:
  - Dungeon → *Open in Designer*, *New Seed from this dungeon*.
  - Seed → *Edit*, *Publish* (creates a save, then opens Play).
  - Save → *Play*, *Delete*.
  - Global *New Dungeon* → Design wizard.
- Library is the startup view; navigation back to Library works from each mode.

---

### Slice 7 — One-time migration of existing `campaigns/*`

**Files modified/created:**
- `dungeon_daddy/data/repository.py` (new `migrate_campaigns_to_libraries`, alongside the
  existing `migrate_legacy_layout`)
- `tests/unit/.../test_migration*.py`

**Acceptance criteria:**
- For each `campaigns/<name>/`: `dungeon.json` + context docs are copied to
  `dungeons/<name>/`, and the folder (dungeon, duckdb, session, memory, assets) becomes
  `saves/<name>/`; if a manifest is present/derivable, `campaign_seeds/<name>/campaign.json`
  is written.
- Migration marks completion (rename source to `campaigns.migrated/` or drop a marker) so a
  second run is a no-op.
- Idempotent: running twice produces the same result and raises nothing.

---

### Slice 8 — Window startup & mode-launch integration

**Files modified:**
- `dungeon_daddy/window.py` (own dungeon repo, `CampaignSeedLibrary`, save repo; run
  migration in `__init__`; Library startup; library actions call the correct launches)
- integration/smoke test under `tools/` or `tests/`

**Acceptance criteria:**
- Happy path end-to-end: Library → *New Dungeon* → save in Design → Campaign → *Attach
  Dungeon* → add actors/clocks → *Save seed* → *Publish* → Play opens the new save with map,
  chat, and RPG panels populated.
- `tools/seed_campaign_rpg.py` still works (shares `seed_from_manifest`).

---

## Exit Criteria

- All 9 slices (0–8) complete.
- Full test suite passes (no regressions).
- Manual run (`python -m dungeon_daddy`): Library opens on startup; the full
  design → attach → publish → play flow works; published save survives a later edit of its
  source dungeon (snapshot independence).
- A pre-existing `campaigns/the-crucible/` migrates into both `dungeons/` and `saves/`;
  re-launch is a no-op.

## Risks / notes

- **Large phase** — land slices incrementally. Slices 0–5 deliver the functional pipeline;
  6–8 add the home screen and migration.
- **Repository reuse vs. churn** — instantiating `DungeonRepository` at two roots avoids a
  wholesale rewrite; the seed library and publish are the only genuinely new modules.
- **Snapshot trade-off** — a dungeon bugfix won't reach existing saves by design.
- **Migration safety** — never delete `campaigns/*` in place until copies are verified; mark
  completion to guarantee idempotence.
