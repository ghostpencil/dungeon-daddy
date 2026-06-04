# Dungeon Daddy — Phase 33–37 World Reaction Spec Packet

## Purpose

This packet replaces the lighter Phase 33–35 planning packet with a stronger plan based on the current product decision:

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.  
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

The goal is to make the RPG service feel impactful and responsive without handing authoritative game-state mutation to the LLM.

## Core authority rule

The existing architecture rule remains absolute:

> The RPG engine and memory layer are authoritative. The LLM is advisory.

The LLM may narrate, frame choices, interpret tone, and eventually propose structured world reactions. It must not directly mutate authoritative state.

Authoritative state changes must go through deterministic services:

- `RpgService`
- `WorldReactionService`
- `MemoryRepository`
- `MemoryProjectionService` / existing memory projection boundary
- validated domain events
- DuckDB persistence
- structured Markdown memory files

## Updated phase sequence

| Phase | Name | Goal |
|---|---|---|
| 33 | Player-Controlled Action Loop | Make Play Mode resolve player-controlled actor actions through the RPG service and narrate with live context bundles. |
| 34 | Campaign RPG Data Deepening | Patch the two existing campaigns with RPG-ready player actors, NPCs, monsters, clocks, memories, and room threat hooks. |
| 35 | Deterministic World Reaction Service | Add a deterministic service that turns player outcomes into dungeon/NPC/monster reactions, clocks, stress, fallout, and memory events. |
| 36 | LLM-Proposed Reaction Drafts | Allow the LLM to propose structured reactions, but validate and apply them through deterministic services only. |
| 37 | Memory Approval and Playtest Curation | Add curated approval/edit/reject workflows for LLM-drafted memories and run an alpha playtest scenario across seeded campaigns. |

## How to use this packet

Copy the `spec/`, `docs/`, `tests/`, and `tools/` files into the repo.

Start Claude Code on **Phase 33 only**. Do not ask Claude to implement all phases at once.

Recommended branch:

```bash
git checkout main
git pull
git checkout -b phase-33-player-controlled-action-loop
```

Commit the specs before implementation:

```bash
git add spec docs tests tools
git commit -m "Add Phase 33-37 world reaction specs"
```

Then give Claude this kickoff prompt:

```text
We are starting Phase 33 only.

Read:
- CLAUDE.md
- spec/PROJECT_INDEX.md
- spec/PHASE_33_PLAYER_CONTROLLED_ACTION_LOOP.md
- docs/LLM_AUTHORITY_BOUNDARY.md
- tests/PHASE_33_37_TEST_PLAN.md
- spec/RPG_MEMORY_ARCHITECTURE.md only for dependency boundaries
- spec/RPG_MEMORY_DATA_MODEL.md only for current actor/context models
- spec/TESTING.md

Do not implement Phase 34, 35, 36, or 37 yet.
Do not give the LLM mutation tools.
Do not let UI panels write DuckDB directly.
Do not let the DM agent query RPG or memory repositories directly.

Before coding, produce a Phase 33 TDD slice checklist and stop.
```

## Why this packet exists

The previous plan was directionally correct but too light. It focused on context bundle handoff, provenance display, and memory approval. Those are useful, but they do not by themselves make Dungeon Daddy playable.

This packet moves the next work toward the real product vision:

1. Player choices are submitted as explicit action intents.
2. The RPG service resolves uncertainty.
3. A deterministic world reaction layer applies pressure from monsters, NPCs, hazards, and the dungeon.
4. Memory records meaningful consequences.
5. The LLM narrates the updated truth rather than inventing state.

That loop is the heart of Dungeon Daddy as a game.
