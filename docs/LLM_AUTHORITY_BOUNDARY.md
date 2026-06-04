# LLM Authority Boundary

## Core rule

The LLM is advisory. The RPG engine, memory system, and deterministic world reaction services are authoritative.

The LLM may:

- narrate applied outcomes
- describe atmosphere
- speak as NPCs or the dungeon presence
- suggest possible consequences
- draft memory summaries
- draft proposed world reactions in a structured format
- explain choices to the player in in-world language

The LLM must not directly:

- advance clocks
- apply stress
- trigger fallout
- create authoritative memory entries
- change actor status
- kill, absorb, transform, or remove actors
- mutate DuckDB
- write Markdown memory files
- bypass validation
- directly call `RpgService` mutation methods
- directly call `MemoryRepository` write methods

## The engine disposes

Use this rule everywhere:

> The LLM may propose. The engine disposes.

A valid LLM-proposed reaction is not true until it has passed deterministic validation and has been applied by service code.

## Mutation flow

Correct flow:

```text
Player intent
  -> PlayerActionRequest
  -> RpgService resolves action
  -> WorldReactionService builds/validates/applies world reaction plan
  -> MemoryProjectionService records meaningful consequences
  -> ContextBundleBuilder builds updated context
  -> DungeonMasterAgent narrates applied truth
```

Incorrect flow:

```text
Player intent
  -> LLM decides result
  -> LLM directly advances clock / applies stress / writes memory
```

## Tool policy

Do not give the LLM direct mutation tools in Phase 33, 34, or 35.

In Phase 36, the LLM may receive proposal-only interfaces such as:

```text
propose_advance_clock(clock_id, ticks, reason)
propose_npc_reaction(actor_id, reaction_key, target_actor_id, reason)
propose_create_memory(title, summary, importance, tags)
propose_apply_consequence(actor_id, track_key, amount, reason)
```

These tools or structured outputs must produce proposals only. They must not commit state.

The application must validate proposals before applying them.

## Validation examples

A proposal must be rejected if:

- the target clock does not exist
- the target actor does not exist
- the target actor is player-controlled and the proposal tries to control their intent
- the target actor is inactive, dead, absorbed, or lost and the action requires active participation
- the ticks/stress amount exceeds permitted bounds
- the proposal attempts a severe permanent consequence without explicit service permission
- the proposal references a room, level, faction, or memory that is not in the campaign
- the proposal would contradict already-authoritative state

## Debugging requirement

Every applied world reaction must be explainable.

A developer should be able to answer:

- What player action caused this?
- What RPG outcome occurred?
- Which service proposed the reaction?
- Which validator approved it?
- Which domain events were written?
- Which memories were created or updated?
- Which facts were sent to the LLM afterward?
