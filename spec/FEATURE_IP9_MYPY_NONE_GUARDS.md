# IP-9 — Fix mypy None-Guard Issues (6 Deferred Files)

_Written: 2026-05-27. Deferred from IP-1 (CI gate) stabilisation sprint._

**Priority:** Medium (quality debt)  
**Effort:** Small–Medium (1–2 hours)  
**Phase:** Post-18 Stabilisation (current)  
**GitHub:** https://github.com/ghostpencil/dungeon-daddy/issues/2

---

## Background

When IP-1 added mypy to CI, six files were placed under
`[[tool.mypy.overrides]] ignore_errors = true` in `pyproject.toml` because
fixing them during STABILIZATION would have been too risky — the issues require
structural None-guard changes, not just annotation style.

This file tracks each file's issues and acceptance criteria so the work can be
done safely in small, test-backed steps.

---

## Files and Primary Issues

| File | Error count | Root cause |
|---|---|---|
| `views/design_view.py` | 43 | None deref on `Dungeon \| None`, agent `\| None` attrs |
| `views/play_view.py` | 19 | None deref on `SessionState \| None`, bad assignments |
| `data/repository.py` | 15 | `Path \| None` used without guard throughout |
| `window.py` | 7 | Dict invariance, missing annotation |
| `llm/agents/dm_agent.py` | 22 | All params typed `object`; attribute access fails |
| `ui/panels/map_panel.py` | 7 | None deref on `Level \| None`, untyped callbacks |

---

## Implementation Steps

### Step 1 — `data/repository.py` (lowest risk)

Add `assert self._dungeons_dir is not None` at the top of each method that
accesses `self._dungeons_dir`. These are internal pre-conditions that will
never fire at runtime given the class invariant, but satisfy mypy.

TDD checklist:
- [ ] Confirm existing tests cover each guarded method
- [ ] Add guard assertions; run `mypy dungeon_daddy/data/repository.py`
- [ ] `pytest tests/unit/data/test_repository.py` green

### Step 2 — `llm/agents/dm_agent.py`

Import `Room`, `Level`, `Dungeon`, `Loop` from `dungeon_daddy.data.models` and
replace all `object` parameter types with concrete types.

TDD checklist:
- [ ] Read current method signatures; list each `object`-typed param
- [ ] Replace types one method at a time; run mypy after each
- [ ] `pytest tests/unit/llm/test_dm_agent.py` green

### Step 3 — `views/design_view.py`

Add None guards before attribute access:

```python
if self._dungeon is None:
    return
```

Also tighten agent attrs from `object | None` to concrete types
(`DungeonWizardAgent | None`, etc.) — this was partially done in Phase 18-B
but the mypy override masked remaining issues.

TDD checklist:
- [ ] Run `mypy dungeon_daddy/views/design_view.py 2>&1 | head -60` to list errors
- [ ] Fix None-deref guards first (easiest)
- [ ] Fix concrete agent types second
- [ ] `pytest tests/unit/views/test_design_view.py` green

### Step 4 — `views/play_view.py`

Same pattern as `design_view.py`: None guards on `SessionState | None` and
fix any bad assignments that mypy flags.

TDD checklist:
- [ ] Run `mypy dungeon_daddy/views/play_view.py 2>&1 | head -40`
- [ ] Add guards; fix assignments
- [ ] `pytest tests/unit/views/test_play_view.py` green

### Step 5 — `window.py`

Two categories:
1. Dict invariance — change `dict[str, object]` param to `Mapping[str, LoopPattern]`
2. One missing annotation on a function

TDD checklist:
- [ ] Run mypy on file; identify the 7 errors
- [ ] Fix each; confirm no test regression

### Step 6 — `ui/panels/map_panel.py`

None guards on `Level | None` + fix `on_click` redefinition pattern (mypy
flags re-binding a typed callback attribute).

TDD checklist:
- [ ] Run mypy on file
- [ ] Add guards; fix callback typing
- [ ] `pytest tests/unit/ui/test_map_panel.py` green

### Step 7 — Remove overrides

Remove all 6 entries from `[[tool.mypy.overrides]]` in `pyproject.toml`.
Run `mypy dungeon_daddy` — must be zero errors for these 6 files.

---

## Acceptance Criteria

- [x] `mypy dungeon_daddy` passes with zero per-file overrides for these 6 files
- [x] `pytest tests/unit/` fully green (824 tests passing)
- [x] No new features or runtime behaviour introduced
- [x] CI `mypy` step passes without the overrides

---

## Status — COMPLETE (2026-05-27)

| Step | File | Status |
|---|---|---|
| 1 | `data/repository.py` | DONE |
| 2 | `llm/agents/dm_agent.py` | DONE |
| 3 | `views/design_view.py` | DONE |
| 4 | `views/play_view.py` | DONE |
| 5 | `window.py` | DONE |
| 6 | `ui/panels/map_panel.py` | DONE |
| 7 | Remove pyproject.toml overrides | DONE |

### What was done (Step 5 — `window.py`)
- Added `DungeonMasterAgent | None` return type to `_build_dm_agent`
- Added proper typed tuple return for `_build_agents`
- Added TYPE_CHECKING imports for all agent and model types
- Typed `open_dungeon` params as `Callable[[], str | None] | None` and `Callable[[str], None] | None`
- Typed `launch_test_drive` / `launch_play_session` params as `Dungeon`

### What was done (Step 6 — `ui/panels/map_panel.py`)
- Added type args to `_tab_style` return (`dict[str, UIFlatButton.UIStyle]`)
- Added `assert lvl is not None` in `_draw_level_overlay`
- Added `# type: ignore[no-untyped-call]` for arcade `trigger_render()` calls
- Moved `# type: ignore[no-redef]` to decorator line for second `on_click`

### What was done (Step 6 — also `llm/telemetry.py`)
- Added `last_usage` property to `ObservingProvider` delegating to `self._inner.last_usage`
- This satisfies the `LLMProvider` protocol so all four agent factory calls typecheck

### What was done (Step 6 — also `llm/agents/wizard_agent.py`)
- Changed `loop_patterns: dict[str, object]` to `Mapping[str, LoopPattern]` (covariant, fixes dict invariance)
- Removed stale `# type: ignore[attr-defined]` on pattern attribute access

### What was done (Step 7)
- Removed the entire `[[tool.mypy.overrides]]` block from `pyproject.toml`
- `mypy dungeon_daddy` now clean across all 47 files with zero overrides
