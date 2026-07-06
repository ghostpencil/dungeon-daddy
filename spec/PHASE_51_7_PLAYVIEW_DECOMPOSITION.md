# Phase 51.7 — PlayView Decomposition (incremental seam extraction)

**Status:** BUILD (started 2026-07-05, branch `feat/phase-51.7-playview-decomp`).
**Owner decisions locked 2026-07-05:** phase-scoped with this spec; coordinators live in a new
`dungeon_daddy/play/` package; the WRP "all three call sites" spec language is corrected (see
`spec/WORLD_REACTION_POLICY.md` §7 seam bullet, amended 2026-07-05).

**Not a feature phase.** No behavior changes except the one deferred PR #88 fix folded into
Slice 1 (atomic world-reaction writes + user-facing failure line). Every slice keeps the full
suite green and is independently PR-able.

---

## 1. Motivation — the audit (2026-07-05)

`views/play_view.py` is **2,765 lines / ~110 methods** and is no longer drawing code. It
coordinates: action resolution, world reactions, proposal validation + application, objective
advancement, LLM narration, context-bundle construction, direct memory loads/saves, memory
approval persistence, command application, room movement, and dialogue routing.

Measured responsibility clusters:

| Cluster | ~Lines | Fate |
|---|---|---|
| View/drawing/layout (`on_draw`, input handlers, `_build_ui`, overlay UI, `_RpgSidePanel`) | ~650 | stays in `PlayView` |
| Action orchestration (`_on_vna_submit` dispatch tree, roll/proposal/obstacle/reaction paths) | ~800 | `ActionOrchestrator` |
| Dialogue / dungeon voice (Phase 51 block) | ~350 | `DialogueCoordinator` |
| Session/actor state (`load_dungeon_*`, roster, acting actor, panel-refresh fan-out) | ~300 | `PlaySessionContext` + controller |
| Navigation (`_on_exit_move`, room-click move, `_focus_party_room`) | ~250 | `NavigationCoordinator` |
| Narration/LLM plumbing (`_dm_history`, `_spawn_dm_thread`, `_build_context_bundle`, queue) | ~200 | `NarrationCoordinator` |
| Memory (`/remember`, auto-remember, MEM-tab persistence) | ~200 | `MemoryCoordinator` |

Findings beyond line count (each with its killing slice):

1. **Domain state inside UI widgets.** The party roster's source of truth is
   `PlayerActionPanel._actors` — a private widget attribute reached into 9× across the file;
   likewise `VnaActionPanel._nouns` (4×). → Slice 0.
2. **The `dungeon/state → level → room` lookup idiom is duplicated ~9×.** → Slice 0
   (`current_room()` accessor).
3. **The 4-line narration-entry idiom** (`_compact_history` → append history → `set_busy` →
   `_spawn_dm_thread`) **is duplicated 8×.** → Slice 2 (`request_narration`).
4. **Deferred PR #88 fix:** `_apply_world_reaction` spans compute + multiple sequential DB
   writes inside a broad `except Exception → None`; a mid-loop error half-applies state and
   shows the GM nothing. → Slice 1 (one transaction + user-facing failure line).
5. **`DMResult` drain in `on_update`** mixes DM-narration and dungeon-voice routing via a
   `dungeon: bool` flag. → Slices 2–3 (each coordinator owns its drain routing).

`spec/ARCHITECTURE.md` still describes the pre-RPG PlayView ("ChatPanel + MapPanel + DM
agent") — it is amended in Slice 7 to the target below.

---

## 2. Target architecture

```
PlayView (arcade.View — drawing, input routing, layout, overlay UI only)
   ↓ user events only
PlaySessionController (composition root — introduced LAST, Slice 7)
   ├── ActionOrchestrator        # card dispatch, rolls, proposals, obstacles, world reaction
   ├── NavigationCoordinator     # exit moves, room click-to-move, focus, level view
   ├── DialogueCoordinator       # dungeon-voice + NPC channels, session, agent inputs
   ├── MemoryCoordinator         # /remember, auto-remember, MEM-tab approve/reject persist
   └── NarrationCoordinator      # DM history, compaction, context bundle, worker threads, queue
        ↓
domain services / repositories (rpg/, memory/, llm/, data/) — unchanged
```

- **Package:** `dungeon_daddy/play/` (new). Coordinators do not import `arcade`. Dependency
  direction: `views → play → (rpg | memory | llm | data)`. Never `play → views`.
- **Ports, not the view:** coordinators receive narrow callables/protocols —
  `post_message(role, text)`, `request_narration(text)`, `refresh_panels(...)` — plus the
  shared `PlaySessionContext`. No coordinator holds a `PlayView` reference.
- **Controller last (owner decision):** extract 2–3 coordinators against the view directly;
  introduce `PlaySessionController` only once real interfaces exist (avoid speculative
  shell-first design).
- **Threading rules unchanged** (`ARCHITECTURE.md`): one active LLM call per view, results via
  thread-safe queue drained by `on_update`, DuckDB writes on the main thread only.
  `NarrationCoordinator` owns the queue + busy flag; `PlayView.on_update` calls its
  `poll()`.

## 3. Slice plan

Each slice: TDD (tests first — read `spec/TESTING.md`, use the TDD skill for new test
modules), full suite green, ruff + mypy(strict) clean, one commit (PR-able unit). Existing
`tests/unit/views/test_play_view_*.py` stay green throughout; tests migrate module-by-module
as their subject moves.

- **Slice 0 — `PlaySessionContext`** (`play/session_context.py`): dungeon, session state,
  mem_repo, campaign_id, **actor roster** (moved out of `PlayerActionPanel._actors`; panels
  become pure displays fed by the context), acting-actor selection, `current_level()`,
  `current_room()`, synthesized `current_level_id` (`f"level-{idx+1}"` — keep the pinned
  guard test). Kills findings 1–2. Pure mechanical; no behavior change.
- **Slice 1 — extract `_apply_world_reaction` → `play/reaction_applier.py` + the deferred
  PR #88 atomicity fix:** clock + stress writes wrapped in **one DuckDB transaction**; on
  failure post a user-facing `"⚠ Reaction could not be fully applied."` system line (keep the
  logged traceback). The only behavioral change in the phase.
- **Slice 2 — `NarrationCoordinator`** (`play/narration.py`): owns `_dm_history`,
  `_compact_history`, `_build_context_bundle`, `_spawn_dm_thread`, `DMResult` queue +
  `_llm_busy`; exposes `request_narration(msg)` (kills the 8× idiom) and `poll()`.
- **Slice 3 — `DialogueCoordinator`** (`play/dialogue.py`): `DialogueSession`, begin/end,
  room-change close, dungeon/NPC line routing, `_dungeon_agent_inputs` + its 8 context
  assemblers, `_apply_dungeon_reply`. Voice-agent thread hands results through the
  narration queue path it already uses.
- **Slice 4 — `ActionOrchestrator`** (`play/actions.py`): the `_on_vna_submit` dispatch tree,
  look/activate/use branches, `_resolve_vna_roll`, `_run_chat_action`/`_on_resolve_action`,
  `_apply_vna_command`, `_maybe_resolve_obstacle`, `_run_proposal_pipeline` +
  `_apply_obstacle_proposals`, `_advance_objectives`. Uses Slice 1's reaction applier.
- **Slice 5 — `NavigationCoordinator`** (`play/navigation.py`): `_on_exit_move`, the
  room-click move branch, `_on_graph_room_select`, `_focus_party_room`,
  `_current_level_rooms`/`_prepare_vna_exits` layout-label helpers.
- **Slice 6 — `MemoryCoordinator`** (`play/memory_coordinator.py`): `/remember`,
  `_extract_remember`/`_auto_remember`, `_load_memory_entries`, MEM-tab commit persistence,
  level-memory overlay load/save (overlay *widgets* stay in the view).
- **Slice 7 — `PlaySessionController`** (`play/controller.py`): composition root wiring the
  five coordinators + context; `PlayView` keeps only drawing/input/layout. **Amend
  `spec/ARCHITECTURE.md`** (module tree, PlayView responsibilities, threading section
  pointing at `NarrationCoordinator`). Manual GUI verify (owner) closes the phase.

## 4. Non-goals

- No new features, no UI changes, no new libraries.
- No changes to domain services (`rpg/`, `memory/`) beyond the Slice 1 transaction seam in
  the repository if one is needed (e.g. a `transaction()` context manager on
  `MemoryRepository`).
- No DesignView decomposition (separate, smaller problem — future candidate).
- Do not port the prototype.

## 5. Exit criteria

1. `views/play_view.py` ≤ ~900 lines, containing only drawing, input routing, layout,
   overlay-widget management, and delegation to the controller.
2. No UI widget holds domain state (`PlayerActionPanel._actors` reach-ins gone; roster lives
   in `PlaySessionContext`).
3. `dungeon_daddy/play/` coordinators import no `arcade`.
4. Deferred PR #88 item 1 fixed: world-reaction writes atomic + user-facing failure line
   (unit test: mid-write failure → no partial state, failure line posted).
5. Full suite green, ruff + mypy(strict) clean at every slice boundary.
6. Owner manual GUI verify on the live Crucible: an action roll, an exit move, a dungeon-voice
   exchange, `/remember`, and a memory approve all behave exactly as before.
