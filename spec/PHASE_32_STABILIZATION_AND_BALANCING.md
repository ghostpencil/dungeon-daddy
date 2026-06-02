# Phase 32 — Stabilization + Balancing

## Status

Proposed.

## Goal

Stabilize the integrated RPG + memory + AI flow before adding new major features.

This phase is about confidence, repairability, balancing, and documentation.

## Required spec files to read

- `CLAUDE.md`
- `spec/PROJECT_INDEX.md`
- `spec/TESTING.md`
- `spec/UI_TESTING.md`
- all RPG/memory specs relevant to the failing or stabilizing area

## What to build

1. Golden fixtures:
   - small campaign fixture
   - one PC
   - one NPC
   - one monster
   - one dungeon emotional state
   - one investigation scene
   - one social scene
   - one combat scene
   - one Weird fallout case

2. Golden context bundle snapshots:
   - fixed DB + Markdown state
   - deterministic expected context bundle
   - snapshot test for retrieval order and provenance

3. Repair tools:
   - validate DuckDB/Markdown sync
   - rebuild memory search projection
   - export campaign state
   - import campaign state fixture

4. Balance pass:
   - action ratings feel useful from 0–3
   - momentum cap prevents hoarding
   - stress tracks fill often enough to matter but not constantly
   - fallout feels story-generative, not punitive
   - Weird stress is tempting, dangerous, and memorable

5. Documentation:
   - GM-facing RPG rules summary
   - developer-facing architecture summary
   - troubleshooting guide
   - migration/back-up notes

## Tests

Recommended tests:

```text
tests/integration/test_rpg_memory_full_pipeline.py
tests/integration/test_context_bundle_snapshots.py
tests/integration/test_memory_repair_tools.py
tools/smoke_test_phase31.py
```

## Exit criteria

- End-to-end action -> stress -> fallout -> memory -> context -> DM narration path works.
- Restart does not lose campaign state.
- Sync validator catches and reports drift.
- Golden context bundle snapshots are stable.
- UI smoke test covers at least one RPG action and one visible memory/fallout result.
- Documentation is sufficient for Claude Code to continue future phases without re-deriving architecture.
- Full test suite remains green.

