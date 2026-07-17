# Dungeon Daddy — Agent Instructions

You are implementing **Dungeon Daddy**: a Python desktop application for game masters
running tabletop dungeon crawls. It is AI-powered, built on the Arcade 2D game engine,
and follows a cyber-arcane visual aesthetic.

---

# Core Rule — Minimize Context

Do NOT load all spec files.

At start, read only:
- CLAUDE.md
- spec/PROJECT_INDEX.md

Load other files only when needed.

---

# SDLC

The development process (phases → slices → TDD, owner halt points, the Gate) is defined
in `spec/SDLC.md`. Session commands that drive it:

- `/next-slice` — start a slice in a fresh session (orient, confirm scope, branch, TDD)
- `/end-slice` — close a slice (gate, code review, commit, PROJECT_INDEX, then `/clear`)
- `/end-phase` — close a phase (gate, owner UI review, PR, whole-arc review, merge)

A PostToolUse hook (`.claude/settings.json`) runs ruff + mypy on every edited `.py` file;
its feedback is blocking — fix it before moving on.

---

# Phase Discipline

Phase and status are in PROJECT_INDEX.md.

## If STABILIZATION
- Do not move to next phase
- No new features
- No architecture changes
- Only:
    - bug fixes
    - behavior fixes
    - UI fixes
    - test fixes
    - spec alignment

If unsure → ask

## If BUILD
- Work only within current phase
- Do not skip ahead

---

# Always-Active Rules

- TDD required (tests first)
- Small steps only (one behavior)
- No new libraries without approval
- Python 3.12+
- Use pathlib (no OS-specific paths)
- JSON must be readable (indent=2)
- LLM must use dependency injection

---

# Skills

## TDD Skill

When writing tests for a new phase or new feature, use the installed TDD skill.

**Before invoking the TDD skill, read `spec/TESTING.md`.** It defines the mock
policy, the integration vs. unit boundary, and the per-cycle checklist. Do not
rely on memory — load it fresh each time.

Use the TDD skill before:
- creating a new test file
- adding tests for a new module
- starting a new phase
- defining test strategy

Do not write phase tests from memory if the TDD skill applies.

For bug fixes during STABILIZATION:
- use the TDD skill only if adding or changing tests
- otherwise keep the fix minimal

---

## UI Testing

See `spec/UI_TESTING.md` — load only when writing or running UI harness tests.

---

## Commands

```
python -m dungeon_daddy          # start the app manually
python tools/arcade_stop.py      # stop a manually-started app window
```

---

# Spec Loading Rules

## IMPLEMENTATION_PHASES.md
Index only — lists all split files. Do not load the index to read phase specs.

Load the correct split file instead:

| File | Phases |
|---|---|
| `spec/IMPLEMENTATION_PHASES_1_10.md` | 1–10 |
| `spec/IMPLEMENTATION_PHASES_11_18.md` | 11–18 + Post-18 |
| `spec/IMPLEMENTATION_PHASES_19_25.md` | 19–25 (Map Layout) |
| `spec/IMPLEMENTATION_PHASES_26_32.md` | 26–32 (RPG Foundation) |
| `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` | 33–40+ (current + future) |

Load one of these only if:
- phase is unknown
- checking exit criteria for the current phase
- preparing the next phase

Otherwise: do not open

## TECH_STACK.md
Only if:
- adding libs
- using new library API

## TESTING.md
Only if:
- invoking the TDD skill (always read first)
- writing/modifying tests
- TDD questions
- writing or modifying a smoke test (`tools/smoke_test_phase*.py`) — read the
  Strategy A vs Strategy B guidance before starting

## ARCHITECTURE.md
Only if:
- creating/changing modules
- state/threading/view ownership

## DATA_MODEL.md
Only if:
- models or JSON work

## LLM_INTERFACE.md
Only if:
- providers or agents

## UI_SPEC.md
Only if:
- UI behavior or layout

## VISUAL_DESIGN.md
Only if:
- colors, fonts, drawing

## FEATURES.md
Only if:
- checking scope or acceptance criteria

## UI_TESTING.md
Only if:
- writing or running UI harness tests
- using `UITestHarness`, `computer-use-mcp`, or smoke tests

## RPG_MEMORY_ROADMAP.md
Only if:
- planning or reviewing RPG/memory phase sequence
- checking design thesis, chosen rules direction, or non-goals for the RPG system
- understanding module plan or dependency order between RPG phases

## RPG_MEMORY_ARCHITECTURE.md
Only if:
- creating or changing `rpg/` or `memory/` modules
- checking dependency direction between RPG, memory, UI, or LLM layers
- understanding domain event boundaries or threading rules for those systems

## RPG_MEMORY_DATA_MODEL.md
Only if:
- implementing or changing RPG/memory Pydantic models
- working with DuckDB schema or SQL migrations for RPG/memory tables
- working with Markdown front matter format or the tag taxonomy

## RPG_SYSTEM_SPEC.md
Only if:
- implementing dice, action rolls, momentum, clocks, stress tracks, or fallout mechanics
- checking RPG rules, action list, non-goals, or recovery rules

## MEMORY_SYSTEM_SPEC.md
Only if:
- implementing memory storage, retrieval, context bundles, or Markdown sync
- checking memory types, creation triggers, retrieval ranking, or LLM boundary rules

## BALANCE_NOTES.md
Only if:
- adjusting RPG constants, stress/clock/fallout thresholds, or game balance parameters

## SEED_RPG_STATE_REQUIREMENTS.md
Only if:
- implementing or modifying `tools/seed_rpg_state.py`
- seeding campaigns with RPG data

## docs/LLM_AUTHORITY_BOUNDARY.md
Only if:
- implementing LLM-facing interfaces or proposal validation
- checking what the LLM may or must not do

## MONSTER_REACTION_DESIGN.md
Only if:
- designing or implementing monster reactions / threat behavior (Phase 53)
- checking how monsters react in fights, the engine/LLM authority split, or boss phases

---

# Workflow (TDD)

For each task:

1. Write failing test
2. Implement minimal code
3. Refactor
4. Repeat

No large batches.

---

# Spec Rules

- If you open a spec → say which one
- Use only needed parts
- If spec conflicts with request → ask for override

---

# Output Rules

- Keep code minimal
- No unrelated changes
- No future features
- No assumptions

---

# Reference

Prototype exists:
- prototype/
- data/dungeon.js
- spec/samples/

Use as reference only. Do not port.

