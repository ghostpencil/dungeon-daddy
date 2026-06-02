# Memory System Specification

## Goal

Create a durable memory system that allows Dungeon Daddy to remember:

- what happened
- who was involved
- where it happened
- what changed mechanically
- what changed emotionally
- what unresolved threads remain
- what the dungeon learned about the characters

## Architecture

Use DuckDB for structured state and Markdown for human-readable narrative memory.

DuckDB remembers what things are.

Markdown remembers what they mean.

## Memory types

Initial memory types:

- `actor`
- `scene`
- `event`
- `fallout`
- `location`
- `thread`
- `lore`
- `relationship`
- `dungeon_state`

## Storage layout

Recommended Markdown folders:

```text
memory/
  campaigns/
    <campaign_slug>/
      actors/
        pcs/
        npcs/
        monsters/
      locations/
        levels/
        rooms/
      events/
        sessions/
        major-events/
      fallout/
      threads/
      relationships/
      dungeon-consciousness/
      lore/
```

## Memory creation triggers

Create or update memory when:

- a session starts or ends
- a scene starts or ends
- a major action resolves
- a stress track fills
- fallout is triggered
- fallout is resolved
- a character forms or damages a bond
- the dungeon learns a vulnerability
- a clue is discovered
- a quest/thread changes state
- a room changes state

## Retrieval strategy

Use deterministic retrieval before AI summarization.

Inputs:

- current campaign
- current session
- current scene
- current room/location
- active actors
- active fallout
- open clocks
- active threads
- user query or DM request

Ranking signals:

- exact actor match
- exact location match
- active fallout
- active thread
- tag overlap
- recency
- importance
- status
- optional full-text score

## Context bundle

The context bundle is the only memory object the AI Dungeon Master should receive.

It must include:

- scene brief
- mechanical state
- active fallout
- open clocks
- must-remember facts
- selected memory cards
- provenance

Provenance must say why each memory was included.

## Markdown sync

The system must detect:

- missing Markdown file for DB record
- Markdown ID mismatch
- changed checksum
- invalid front matter
- tag drift
- orphan Markdown file
- orphan DB record

First-pass behavior:

- validation report only
- do not auto-delete
- allow explicit repair command later

## LLM boundary

The LLM may draft:

- memory summaries
- scene recaps
- fallout descriptions
- NPC emotional interpretation
- dungeon response suggestions

The app must approve and persist through deterministic services.

Do not let free-form LLM text directly mutate DuckDB state.

