# Phase 26 — RPG + Memory Foundation

## Status

Proposed.

## Goal

Create the foundation for RPG and memory work without changing existing Play Mode behavior.

This phase is about module boundaries, models, migration scaffolding, and testable services. It should not yet alter the live DM flow.

## Required spec files to read

- `CLAUDE.md`
- `spec/PROJECT_INDEX.md`
- `spec/ARCHITECTURE.md`
- `spec/TESTING.md`
- `spec/RPG_MEMORY_ROADMAP.md`
- `spec/RPG_MEMORY_ARCHITECTURE.md`
- `spec/RPG_MEMORY_DATA_MODEL.md`

## Modules to add

```text
dungeon_daddy/rpg/__init__.py
dungeon_daddy/rpg/models.py
dungeon_daddy/rpg/dice.py
dungeon_daddy/rpg/actions.py
dungeon_daddy/rpg/clocks.py
dungeon_daddy/rpg/stress.py
dungeon_daddy/rpg/service.py

dungeon_daddy/memory/__init__.py
dungeon_daddy/memory/models.py
dungeon_daddy/memory/repository.py
dungeon_daddy/memory/markdown_store.py
dungeon_daddy/memory/sync.py

dungeon_daddy/data/migrations/001_rpg_memory_foundation.sql
```

## What to build

1. RPG model skeletons:
   - `ActorState`
   - `ActionRating`
   - `StressTrack`
   - `ClockState`
   - `Ability`
   - `ActionRequest`
   - `ActionResolution`

2. Memory model skeletons:
   - `MemoryEntry`
   - `MemoryTag`
   - `MemoryLink`
   - `DomainEvent`
   - `ContextBundle`

3. Migration runner:
   - locates `.sql` files in `dungeon_daddy/data/migrations/`
   - applies unapplied migrations
   - records migrations in `schema_migration`
   - supports tmp_path testing

4. DuckDB repository shell:
   - open/close connection
   - initialize schema
   - health check
   - insert domain event
   - list migrations

5. Markdown store shell:
   - write memory Markdown with front matter
   - read memory Markdown
   - compute SHA-256 checksum
   - validate required front matter fields

## Do not build yet

- live Play Mode UI changes
- action roll UI
- fallout generation
- AI context bundle integration
- full memory search
- full-text search

## Tests

Follow tracer-bullet TDD.

Recommended test files:

```text
tests/unit/rpg/test_models.py
tests/unit/rpg/test_dice.py
tests/unit/memory/test_models.py
tests/unit/memory/test_markdown_store.py
tests/unit/memory/test_repository.py
tests/integration/test_rpg_memory_migrations.py
```

Use real DuckDB against `tmp_path` if DuckDB is already approved as a dependency. If DuckDB is not yet in requirements, stop and request approval before adding it.

## Exit criteria

- New modules import cleanly.
- Migration runner applies `001_rpg_memory_foundation.sql` once and records it.
- Running migration twice is idempotent.
- Markdown store round-trips a front-matter memory file.
- Repository can insert and retrieve a domain event.
- No existing Play Mode behavior changes.
- Full test suite remains green.

