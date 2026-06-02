# Phase 31 — Context Bundles + AI Integration

## Status

Proposed.

## Goal

Integrate the RPG and memory systems with the AI Dungeon Master through a deterministic context bundle service.

The AI should receive concise, relevant, provenance-backed context. It should not query memory directly and should not own state.

## Required spec files to read

- `CLAUDE.md`
- `spec/PROJECT_INDEX.md`
- `spec/LLM_INTERFACE.md`
- `spec/TESTING.md`
- `spec/MEMORY_SYSTEM_SPEC.md`
- `spec/RPG_MEMORY_ARCHITECTURE.md`

## Modules to add or update

```text
dungeon_daddy/memory/retrieval.py
dungeon_daddy/memory/context_bundle.py
dungeon_daddy/llm/agents/dm_agent.py
dungeon_daddy/views/play_view.py
```

## What to build

1. Context bundle generator:
   - accepts campaign ID, scene ID, mode, focus actors, token budget
   - gathers current scene, actors, stress, fallout, clocks, room/location, active threads
   - retrieves relevant memories
   - ranks and trims results
   - records provenance

2. DM agent update:
   - accept optional `ContextBundle`
   - include mechanical state and memory cards in system/user prompt construction
   - preserve existing room memory behavior until new bundle path is verified

3. Memory provenance display:
   - show selected memories in debug panel
   - show reason for inclusion
   - show omitted memories count if token budget trims output

4. LLM write boundary:
   - AI may draft memory summaries or consequences
   - deterministic service persists approved state
   - generated memory drafts should be marked as draft until approved or auto-accepted by explicit rule

## Context bundle shape

```json
{
  "bundle_id": "ctx_0051",
  "campaign_id": "camp_dungeondaddy",
  "scene_id": "scn_cathedral_02",
  "mode": "run_scene",
  "scene_brief": {},
  "mechanical_state": {},
  "active_fallout": [],
  "open_clocks": [],
  "must_remember": [],
  "memory_cards": [],
  "provenance": {}
}
```

## Tests

Recommended tests:

```text
tests/unit/memory/test_context_bundle.py
tests/unit/llm/test_dm_agent_context_bundle.py
tests/integration/test_context_bundle_retrieval.py
tests/integration/test_dm_agent_with_rpg_memory_context.py
```

No real API call during unit tests.

## Exit criteria

- Context bundle includes active actor state, clocks, fallout, and relevant memories.
- Bundle provenance explains memory selection.
- DM agent can build a prompt with a context bundle.
- Existing DM behavior still works when no context bundle is provided.
- LLM output does not directly mutate RPG or memory state.
- Full test suite remains green.

