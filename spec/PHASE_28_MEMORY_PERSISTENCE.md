# Phase 28 — Memory Persistence

## Status

Proposed.

## Goal

Persist RPG state and narrative memory across app restarts using DuckDB and Markdown.

This phase makes the system durable but does not yet implement custom fallout.

## Required spec files to read

- `CLAUDE.md`
- `spec/PROJECT_INDEX.md`
- `spec/TESTING.md`
- `spec/MEMORY_SYSTEM_SPEC.md`
- `spec/RPG_MEMORY_DATA_MODEL.md`

## Modules to update

```text
dungeon_daddy/memory/repository.py
dungeon_daddy/memory/markdown_store.py
dungeon_daddy/memory/sync.py
dungeon_daddy/memory/retrieval.py
```

## What to build

1. DuckDB persistence for:
   - campaigns
   - sessions
   - scenes
   - actors
   - actor actions
   - actor stress tracks
   - clocks
   - action resolutions
   - domain events

2. Memory entries:
   - create memory entry
   - update memory entry
   - link memory to actor/scene/session/location
   - tag memory
   - retrieve by ID

3. Markdown memory files:
   - create file from memory entry
   - parse front matter
   - validate ID/type/status/tags
   - calculate checksum
   - update DB checksum

4. Sync report:
   - missing file
   - invalid front matter
   - DB checksum mismatch
   - orphan Markdown file
   - orphan DB row

5. Deterministic retrieval:
   - search by actor
   - search by location
   - search by tag
   - search active fallout placeholder type, even before fallout implementation
   - rank by importance and exact matches

## Do not build yet

- full-text search extension unless included as a tiny separate vertical slice
- AI context bundles
- UI memory inspector
- automatic repair of sync drift
- custom fallout generation

## Tests

Recommended test files:

```text
tests/unit/memory/test_repository_memory_entries.py
tests/unit/memory/test_markdown_frontmatter.py
tests/unit/memory/test_sync.py
tests/unit/memory/test_retrieval.py
tests/integration/test_memory_persistence_roundtrip.py
```

## Exit criteria

- A campaign with actors, scene, clocks, and action resolutions survives app/repository restart.
- A memory entry writes both DuckDB row and Markdown file.
- Markdown file can be re-parsed and validated.
- Retrieval by actor/location/tag returns deterministic results.
- Sync report catches deliberately broken fixtures.
- No Play Mode UI dependency.
- Full test suite remains green.

