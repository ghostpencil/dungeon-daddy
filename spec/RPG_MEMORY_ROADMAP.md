# RPG + Memory Roadmap

## Purpose

Dungeon Daddy is moving from dungeon design and AI-assisted play into a deeper game system: player/NPC/monster state, narrative action resolution, health/stress, fallout, and durable campaign memory.

This roadmap defines the recommended phase order. The RPG and memory systems are tightly related, but they must not be built as one tangled feature. Build a small rules core first, then persist it, then make fallout write durable memory, then allow the AI Dungeon Master to consume that memory.

## Design thesis

Dungeon Daddy is not a tactical combat simulator.

It is a consequence engine for intimate supernatural adventure.

The rules should answer:

- What is the character trying to do?
- What are they risking?
- What does it cost?
- What changes in the dungeon?
- What does the dungeon remember?
- How does the character come back different?

## Chosen rules direction

Use a Charge-style narrative core:

- fiction-first action rolls
- small action list
- momentum
- clocks
- player-facing consequences
- NPCs and monsters represented by lightweight threat models rather than full tactical stat blocks

Add a custom Dungeon Daddy fallout subsystem:

- Body stress
- Composure stress
- Bonds stress
- Weird stress
- minor / moderate / severe fallout
- dungeon influence and intimacy risk
- fallout as durable narrative memory

## High-level module plan

Add new modules without disrupting existing map, LLM, and UI modules.

```text
dungeon_daddy/
  rpg/
    __init__.py
    models.py              # Pydantic/dataclass RPG models
    dice.py                # deterministic roll helpers
    actions.py             # action keys, ratings, action roll resolver
    clocks.py              # clock helpers
    stress.py              # stress track helpers
    fallout.py             # fallout evaluator and fallout catalog
    service.py             # RPGService orchestration API

  memory/
    __init__.py
    models.py              # memory records, tags, links, context bundle models
    repository.py          # DuckDB repository
    markdown_store.py      # Markdown file read/write + front matter
    sync.py                # Markdown -> DuckDB sync and validation
    retrieval.py           # deterministic memory search and ranking
    context_bundle.py      # LLM-ready bundle builder

  data/
    migrations/
      001_rpg_memory_foundation.sql
      002_memory_fts.sql

  ui/
    panels/
      character_sheet_panel.py
      scene_state_panel.py
      memory_inspector_panel.py
      fallout_panel.py
```

## Phase sequence

| Phase | Name | Goal |
|---|---|---|
| 25 | RPG + Memory Foundation | Create module skeletons, base models, migration runner, and seed data without changing Play Mode behavior. |
| 26 | RPG Core Loop | Implement action rolls, momentum, clocks, stress tracks, NPC/monster threat clocks, and a headless playable loop. |
| 27 | Memory Persistence | Add DuckDB + Markdown memory storage, tags, links, session/event records, and restart-safe state. |
| 28 | Fallout + Dungeon Influence | Add custom fallout, Weird stress, intimacy risk, dungeon emotional state, and memory-writing consequences. |
| 29 | Play Mode UI + Debug Tools | Add character sheets, clocks, fallout display, memory inspector, and GM controls to Play Mode. |
| 30 | Context Bundles + AI Integration | Feed selected RPG state and memory into DungeonMasterAgent through a context bundle service. |
| 31 | Stabilization + Balancing | Harden tests, smoke tests, data repair tools, balancing fixtures, and documentation. |

## Dependency principle

Do not build UI before the headless service exists.

Do not build AI integration before deterministic retrieval exists.

Do not build complex fallout before basic stress tracks and clocks are persistent.

## Success criteria for the whole roadmap

The roadmap is successful when a play session can do all of the following:

1. Load a dungeon.
2. Load or create PCs.
3. Enter a room.
4. Resolve an investigation, social action, or combat action.
5. Apply stress and tick clocks.
6. Trigger fallout when appropriate.
7. Write the fallout and event to memory.
8. Restart the app.
9. Retrieve the relevant memory on a future room visit.
10. Pass that memory to the AI Dungeon Master as structured context.
11. Display enough state in the UI that a GM can understand what happened.

