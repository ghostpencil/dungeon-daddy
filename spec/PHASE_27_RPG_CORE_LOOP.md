# Phase 27 — RPG Core Loop

## Status

Proposed.

## Goal

Implement the headless RPG loop: action rolls, momentum, clocks, stress tracks, and lightweight actor state.

This phase should prove the game can resolve investigation, social, and combat actions without involving the LLM or UI.

## Required spec files to read

- `CLAUDE.md`
- `spec/PROJECT_INDEX.md`
- `spec/TESTING.md`
- `spec/RPG_SYSTEM_SPEC.md`
- `spec/RPG_MEMORY_ARCHITECTURE.md`

## Modules to update

```text
dungeon_daddy/rpg/dice.py
dungeon_daddy/rpg/actions.py
dungeon_daddy/rpg/clocks.py
dungeon_daddy/rpg/stress.py
dungeon_daddy/rpg/service.py
```

## What to build

1. Dice pool resolver:
   - accepts fixed dice for tests
   - accepts RNG for runtime
   - returns highest die and outcome band

2. Action resolver:
   - accepts `ActionRequest`
   - calculates dice pool from action rating, momentum spend, and modifiers
   - classifies result as `bad`, `partial`, `success`, or `critical`
   - returns an `ActionResolution`

3. Momentum helpers:
   - gain momentum
   - spend momentum
   - enforce cap
   - reject overspend

4. Clock helpers:
   - create clock
   - advance clock
   - prevent overflow beyond total unless explicitly allowed
   - mark completed

5. Stress helpers:
   - create four default PC tracks
   - mark stress
   - detect filled track
   - indicate fallout evaluation required without creating fallout yet

6. RPG service:
   - create actor
   - create scene clock
   - resolve action
   - apply stress
   - advance clock
   - emit domain events for each state change

## Do not build yet

- fallout table selection
- dungeon influence
- UI panels
- AI narration changes
- Markdown memory projection

## Example headless scenario

A PC studies a strange altar.

- `study` rating 2
- risk moderate
- effect standard
- fixed dice `[5, 2]`
- result partial
- ticks `Open the Choir Door` clock by 2
- marks 1 Weird stress
- emits `action.resolved`, `clock.advanced`, and `stress.marked`

## Tests

Recommended test files:

```text
tests/unit/rpg/test_actions.py
tests/unit/rpg/test_clocks.py
tests/unit/rpg/test_stress.py
tests/unit/rpg/test_service.py
tests/integration/test_rpg_core_loop.py
```

## Exit criteria

- A complete headless action can be resolved.
- Momentum spend changes dice pool and is capped.
- Clocks advance and complete correctly.
- Stress marks and detects filled tracks.
- Domain events are emitted for state changes.
- No UI changes required.
- Full test suite remains green.

