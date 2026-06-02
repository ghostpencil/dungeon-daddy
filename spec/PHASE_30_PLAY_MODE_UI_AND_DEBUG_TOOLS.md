# Phase 30 — Play Mode UI + Debug Tools

## Status

Proposed.

## Goal

Expose RPG and memory state in Play Mode without making the UI responsible for business logic.

This phase makes the system usable by a GM.

## Required spec files to read

- `CLAUDE.md`
- `spec/PROJECT_INDEX.md`
- `spec/ARCHITECTURE.md`
- `spec/TESTING.md`
- `spec/UI_SPEC.md`
- `spec/UI_TESTING.md` if writing smoke tests
- `spec/RPG_MEMORY_ARCHITECTURE.md`

## UI modules to add

```text
dungeon_daddy/ui/panels/character_sheet_panel.py
dungeon_daddy/ui/panels/scene_state_panel.py
dungeon_daddy/ui/panels/fallout_panel.py
dungeon_daddy/ui/panels/memory_inspector_panel.py
```

## Existing modules to update

```text
dungeon_daddy/views/play_view.py
dungeon_daddy/ui/panels/map_panel.py
dungeon_daddy/ui/panels/chat_panel.py
```

## What to build

1. Character sheet panel:
   - current PC/NPC/monster selection
   - action ratings
   - momentum
   - stress tracks
   - active fallout
   - abilities
   - tags

2. Scene state panel:
   - current scene title/location
   - open clocks
   - active actors
   - recent actions
   - current risk/effect selector for action resolution

3. Fallout panel:
   - active fallout list
   - severity/track/status
   - mechanical hooks
   - linked memory path

4. Memory inspector:
   - search by tag/actor/location
   - show title, summary, status, importance
   - open Markdown body in read-only view
   - show sync warnings

5. Debug controls:
   - resolve sample action
   - add stress
   - advance clock
   - generate sync report
   - create test memory note

## UI design constraints

- Do not obscure the current map selection.
- Keep Play Mode usable at 1400x900.
- Prefer collapsible panels/tabs over permanent clutter.
- The map remains primary. Character/memory tools are supporting panels.

## Service boundary

The UI may call:

- `RPGService.resolve_action()`
- `RPGService.apply_stress()`
- `RPGService.advance_clock()`
- `MemoryRepository.search_memories()` through an application-level method
- `MemorySyncService.validate()` through an application-level method

The UI must not directly execute SQL or write Markdown files.

## Tests

Recommended tests:

```text
tests/unit/ui/test_character_sheet_panel.py
tests/unit/ui/test_scene_state_panel.py
tests/unit/ui/test_fallout_panel.py
tests/unit/ui/test_memory_inspector_panel.py
tests/integration/test_play_mode_rpg_wiring.py
tools/smoke_test_phase29.py
```

Follow existing UI testing guidance. Take screenshots after actions intended to have visible effects.

## Exit criteria

- Play Mode displays actor stress, momentum, and active fallout.
- A GM can resolve a simple action from UI controls.
- Clock and stress changes are visible after the action.
- Memory inspector can find fallout/memory created in earlier phases.
- Debug UI can validate sync state.
- Smoke test captures before/after screenshots for visible UI changes.
- Full test suite remains green.

