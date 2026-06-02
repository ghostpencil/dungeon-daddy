# RPG + Memory Test Plan

## Testing posture

Follow the existing repo's testing philosophy:

- tracer-bullet TDD
- no broad test dumps
- use real internal objects whenever possible
- mock only external APIs, Arcade rendering, OS dialogs, and display-bound systems
- integration tests after unit-level behavior is proven

## Unit test order

1. RPG models
2. Dice helpers
3. Action resolver
4. Clocks
5. Stress tracks
6. Fallout evaluator
7. Memory models
8. Markdown store
9. DuckDB repository
10. Retrieval ranking
11. Context bundle builder
12. UI panel rendering/wiring

## Integration test scenarios

### Scenario 1 — Headless investigation

A PC studies an altar, partially succeeds, ticks a clue clock, and marks Weird stress.

Assertions:

- action resolution row created
- clock advanced
- stress marked
- domain events emitted

### Scenario 2 — Stress to fallout to memory

A PC fills Weird stress and triggers moderate fallout.

Assertions:

- fallout row created
- memory entry created
- Markdown file written
- tags include actor, track, fallout, and theme
- retrieval by actor returns fallout memory

### Scenario 3 — Restart persistence

Create campaign state, close repository, reopen repository.

Assertions:

- actor state preserved
- clocks preserved
- fallout preserved
- memory checksums preserved

### Scenario 4 — Context bundle selection

Given active actor, location, fallout, and open clock, generate context bundle.

Assertions:

- active fallout included
- location memory included
- irrelevant memory excluded
- provenance explains inclusion reasons

### Scenario 5 — UI smoke test

Run app, open Play Mode, resolve visible test action, confirm UI updates.

Assertions:

- screenshot before action
- screenshot after action
- stress/clock change visible
- no error bubble

## Golden fixtures

Create a small deterministic campaign fixture for tests:

```text
Campaign: Fixture Dungeon
PC: Mara Voss
NPC: Sister Elowen
Monster: Memory-Stitched Guardian
Location: Moonlit Cathedral
Clock: Open the Choir Door, 6 segments
Fallout: Dreams in the cathedral's voice
```

## Do not test by implementation detail

Avoid tests that only prove one internal method called another internal method.

Prefer tests that assert public behavior and durable state.

