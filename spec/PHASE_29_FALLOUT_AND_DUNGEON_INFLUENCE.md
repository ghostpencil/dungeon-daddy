# Phase 29 — Fallout + Dungeon Influence

## Status

Proposed.

## Goal

Implement the custom Dungeon Daddy fallout subsystem and connect it to memory.

This phase is where the system becomes emotionally specific to Dungeon Daddy.

## Required spec files to read

- `CLAUDE.md`
- `spec/PROJECT_INDEX.md`
- `spec/TESTING.md`
- `spec/RPG_SYSTEM_SPEC.md`
- `spec/MEMORY_SYSTEM_SPEC.md`
- `spec/RPG_MEMORY_DATA_MODEL.md`

## Modules to add or update

```text
dungeon_daddy/rpg/fallout.py
dungeon_daddy/rpg/stress.py
dungeon_daddy/rpg/service.py
dungeon_daddy/memory/repository.py
dungeon_daddy/memory/markdown_store.py
```

## Fallout tracks

- Body
- Composure
- Bonds
- Weird

## Fallout severity

- Minor
- Moderate
- Severe

## Dungeon influence concepts

Add first-pass support for:

- dungeon emotional state
- intimacy risk
- dungeon-known vulnerabilities
- dungeon leverage hooks

These should be represented as records/tags/memory, not hidden prompt text.

## What to build

1. Fallout evaluator:
   - detects filled stress track
   - determines severity
   - creates `FalloutRecord`
   - resets or reduces stress according to first-pass rule

2. Fallout catalog:
   - original Dungeon Daddy fallout examples for each track and severity
   - mechanical hook templates
   - memory summary templates

3. Weird stress special behavior:
   - Weird fallout can create dungeon knowledge tags
   - Weird fallout can change dungeon emotional state
   - Weird fallout should always write memory

4. Intimacy risk:
   - accepting comfort, healing, guidance, refuge, or visions from the dungeon can clear stress or grant advantage
   - cost may include Weird stress, dungeon bond, vulnerability tag, or influence clock progress

5. Memory projection:
   - fallout creates `memory_entry` type `fallout`
   - fallout writes Markdown file
   - fallout links to actor, scene, session, and source action
   - fallout applies tags such as `track:weird`, `fallout:active`, `theme:guilt`

## Do not build yet

- rich UI editing of fallout
- full balancing pass
- LLM-generated fallout tables
- player-facing character creation flow

## Tests

Recommended test files:

```text
tests/unit/rpg/test_fallout.py
tests/unit/rpg/test_intimacy_risk.py
tests/integration/test_fallout_memory_projection.py
tests/integration/test_weird_fallout_dungeon_influence.py
```

## Exit criteria

- Filling each stress track can trigger appropriate fallout.
- Minor, moderate, and severe fallout are represented distinctly.
- Weird fallout writes dungeon influence memory.
- Fallout is linked to source action, actor, scene, and session.
- Fallout appears in retrieval by actor and tag.
- Full test suite remains green.

