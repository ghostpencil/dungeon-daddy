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
Only if:
- phase is unknown
- checking exit criteria
- preparing next phase

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

