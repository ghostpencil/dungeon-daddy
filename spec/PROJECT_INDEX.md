# Dungeon Daddy — Project Index

## Phase

Phase **50 / 50.5 / 50.6 — COMPLETE & merged to `main`** (Hybrid Action Model · Use-Noun-on-Noun
grammar · Chat Action Cockpit). Detail in git history + Phase History table below.

Phase **51 — Talk to the Dungeon: COMPLETE & merged to `main`** (PR #83, 2026-07-04) — live
dungeon-voice channel, recedable/latching intimacy clock, `DungeonVoiceAgent`, dungeon-persona
persistence, resonance points. Spec `spec/PHASE_51_TALK_TO_THE_DUNGEON.md`.

Phase **51.5 — Dungeon Objectives & Intimacy Tiers: COMPLETE & merged to `main`** (PR #83, together
with Phase 51 per D8, 2026-07-04) — the full intimacy ladder (objectives → latching tier index →
per-tier knowledge) plus the puzzle-obstacle multi-approach feature (Part A class-flavored contested
approaches; Part B the constrained DM-ruled obstacle authority) and container-loot. Decisions locked
D1–D8 (below). Spec `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md`.

Phase **51.6 — World Reaction Policy: COMPLETE & merged to `main`** (PR #88, merged 2026-07-05,
`c0e1cba`; also landed the mypy 348→0 sweep). Per-object `reaction_policy`
(`scripted`/`ambient`/`inert`) + `ClockCategory` firewall replace the blunt "miss = every tagged
clock +2" fan-out. Spec `spec/PHASE_51_6_WORLD_REACTION_POLICY.md` (design
`spec/WORLD_REACTION_POLICY.md`).

Phase **51.7 — PlayView Decomposition: COMPLETE & merged to `main`** (PR #89, merge commit
`5eadaaa`, merged 2026-07-06; owner GUI-verified). Incremental seam extraction of
`views/play_view.py` (2,765 → 1,491 lines) into a new `dungeon_daddy/play/` package
(`PlaySessionContext` + Action/Navigation/Dialogue/Memory/Narration coordinators;
`PlaySessionController` composition root, Slice 7). Folded in the two PR #88 deferred review items:
Slice 1 fixed the non-atomic world-reaction write; the WRP "all three call sites" spec language
was corrected (owner ruling 2026-07-05, `spec/WORLD_REACTION_POLICY.md` §7). Spec + slice plan:
`spec/PHASE_51_7_PLAYVIEW_DECOMPOSITION.md`.

Specs: 51.6 `spec/PHASE_51_6_WORLD_REACTION_POLICY.md` · 51.5 `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md` ·
51 `spec/PHASE_51_TALK_TO_THE_DUNGEON.md` · current/future `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`
(index `spec/IMPLEMENTATION_PHASES.md`).

---

## START HERE — next phase: Tag Hygiene → Narrator Lookup

**✅ Phase 51.7 — PlayView Decomposition: MERGED & CLOSED.** PR #89 merged to `main` 2026-07-06
(merge commit `5eadaaa`, branch deleted); `main` is up to date. `views/play_view.py` 2,765 → 1,491
lines; logic lives in the new `dungeon_daddy/play/` package (`PlaySessionContext` +
Action/Navigation/Dialogue/Memory/Narration coordinators + `PlaySessionController`). Owner
GUI-verified on the live Crucible. A 6-agent parallel PR review ran before merge — 1 regression
fixed (`fd101df`, repo-read failures now surface `REACTION_FAILURE_LINE`), 2 findings deferred
to this next phase (see the review block below). Full 51.7 slice history + deferred follow-ups
retained further down for reference.

**▶ NEXT — Phase: Tag Hygiene → Narrator Lookup.** Spec `spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md`
(the sequenced choice; item 2 below). Start by reading that spec for the slice plan. **Carry in the
two deferred PR #89 review findings** as early cleanup candidates: (2) the broad silent
`except Exception` catches in `actions.py` (`run_chat_action`, `on_resolve_action`) that hide
failed resolves/LLM calls from the GM; (3) extract an `ActiveCampaign(repo, campaign_id)` value /
`context.active_campaign()` accessor to collapse the 15+ hand-copied co-presence guards.

**Exit-criterion-1 — ✅ owner accepted 1491 lines (2026-07-06).** `views/play_view.py` landed at
**1491 lines** (from 1878), above the spec's "≤ ~900" but now containing *only* drawing / input
routing / layout / overlay-widget management / delegation — **criterion 1 met in spirit** (owner
ruling). The ~900 figure under-estimated the legitimate **input-routing** weight (the `_on_chat_send`
+ action-state/chip cluster ~250 lines, which criterion 1 explicitly says *stays* in PlayView) plus
the `_RpgSidePanel` UI class (~132 lines, legitimately "overlay-widget management"). A literal ≤900
would need an additional input-coordinator extraction that contradicts criterion 1's own "input
routing stays in PlayView" wording — **not pursued** (owner chose to accept 1491 over that follow-up).

**Slice 7 — what shipped (branch `feat/phase-51.7-playview-decomp`, uncommitted):**
New `play/controller.py` (`PlaySessionController` + `PlayHost` structural protocol, no `arcade`).
The controller is the composition root: it **receives** the shared `PlaySessionContext` (still owned
by the view's Slice 0 session bridge — one instance, verified) and **owns** the five coordinators +
the session-facade methods extracted from the view (`load_dungeon_*` / `set_rpg_context` /
`save_session` / `load_player_actors` / `sync_debug_level_id` + the domain→panel refresh fan-out
`refresh_vna_panel` / `refresh_right_panel_from_actors` / `refresh_chat_mini_card` /
`refresh_memory_state` / `room_world_flags`). Coordinator ports route through the view's delegators
(`host._X` — the input-surface seam the view tests spy/stub); facade methods call sibling controller
methods directly (one documented exception: `set_rpg_context` routes `_load_player_actors` through
the host because a test stubs that delegator). `PlayView` keeps thin delegators + a lazy
`_ensure_controller()` bridge; the five `_ensure_*` factory methods collapsed into it. 5 new unit
tests (`tests/unit/play/test_controller.py`); one test's patch target moved
(`build_actor_mini_card` now lives in `play.controller`). **`spec/ARCHITECTURE.md` amended** (module
tree adds `play/`; PlayView responsibilities; threading → `NarrationCoordinator`). Behavior-preserving;
`play_view.py` 1878 → 1491. Full suite green (**3529 passed**), ruff + mypy(strict, 168 files) clean.
**5-angle `/code-review high`:** zero correctness bugs (extraction verified "remarkably faithful");
applied the one converged cleanup (removed the gratuitous `load_dungeon_*` → host bounce). Deferred
(low, not blocking): a latent context-staleness seam if `view._session` is *reassigned after* the
controller is built (not reachable today — mirrors the Slice 2–6 pattern; a `_session.setter` guard
would harden it); the `getattr`/`setattr` seam for 4 view-only attrs kept off `PlayHost` for
`__new__` ergonomics; two pre-existing smells moved verbatim (`load_dungeon_*` copy-paste; a double
`refresh_chat_mini_card` on non-empty actor load).

**Deferred follow-ups (not blocking):** the Slice 4 `get_debug` port hands play a UI panel type
(TYPE_CHECKING-only; two narrow callables would be cleaner, but the debug-gates-proposal-pipeline
coupling is pre-existing); Slice 5 `set_viewed_level` is a write-only `setattr` port poking
view-only map-paging state (the deliberate documented seam — could be tightened when the
controller lands in Slice 7); Slice 5 `current_level_rooms -> tuple[dict[str, Any], Any]` erases
the x/y/w/h/name structural contract (`_PositionedRoom`) — a `Protocol` return type would restore
it (pre-existing, moved verbatim).

**PR #89 parallel review (6 agents, 2026-07-06) — 1 fixed, 2 deferred to next phase:**
- ✅ **Fixed (regression):** `reaction_applier.apply` had broadened its guard to swallow repo
  *read* failures (`get_clocks` / `get_actor_stress_tracks`) that pre-51.7 propagated — silently
  skipping the world reaction with no GM feedback. Split reads into their own guard that surfaces
  `REACTION_FAILURE_LINE` (compute stays contained-silent). Test
  `test_read_failure_is_contained_and_posts_failure_line`; full suite green.
- ⏳ **Deferred → next phase:** (2) the two broad `except Exception` catches in `actions.py`
  (`run_chat_action` ~L375, `on_resolve_action` ~L423) log but post no user line — a failed
  resolve/proposal/LLM call is invisible to the GM (pre-existing from `main`; add a system line +
  narrow the catch). (3) the `(mem_repo, campaign_id)` co-presence guard is hand-checked 15+ times
  across `reaction_applier`/`dialogue`/`actions`/`controller`/`navigation` — extract an
  `ActiveCampaign(repo, campaign_id)` value / `context.active_campaign()` accessor (both the
  type-design and simplify agents flagged this independently; highest-value low-risk cleanup).
- Other review notes (non-blocking, candidates for a Slice 8 follow-up): drop
  `NarrationCoordinator.is_busy`'s public setter; promote `PlayHost`'s panel-private reach-ins
  (`_rpg_vna._nouns`, `_rpg_action._build_request`) to public methods; add logging to the silent
  swallows in `navigation.current_level_rooms` and `controller.set_rpg_context`; add `ui` to the
  repeated dependency-direction docstring; controller.py test gaps (`room_world_flags`,
  contested `on_activate_submit`, repo-close-on-swap).

After 51.7: Tag Hygiene → Narrator Lookup remains the sequenced choice (item 2 below).

**Phase 51.7 slice progress (branch `feat/phase-51.7-playview-decomp`):**
- ✅ **Slice 0 — `PlaySessionContext`** (2026-07-06). New `dungeon_daddy/play/` package
  (imports no `arcade`); `play/session_context.py` owns dungeon/session-state/`mem_repo`/
  `campaign_id`/actor roster + `current_level()`/`current_room()`/`current_level_id`/
  `acting_actor()`. Kills audit findings 1–2: the roster moved out of `PlayerActionPanel._actors`
  (~9 reach-ins now read `self._session.actors`); the `dungeon→level→room` current-room idiom
  (6 sites) + both `f"level-{idx+1}"` synth sites route through the context. `PlayView` bridges
  via lazy properties (`_dungeon`/`_state`/`_mem_repo`/`_rpg_campaign_id` delegate to
  `self._session`) so the context is the single source of truth without churning ~60 read sites
  or breaking the `__new__` test pattern; mypy strict still narrows them. Pure mechanical, no
  behavior change. 13 new unit tests (`tests/unit/play/test_session_context.py`); ~10 view-test
  files migrated their roster setup to `view._session.set_actors(...)`. Full suite green
  (**3421 passed**), ruff + mypy(strict) clean.
- ✅ **Slice 1 — `ReactionApplier` + atomic world-reaction writes** (2026-07-06, `415b880`).
  `PlayView._apply_world_reaction` (~80 lines) extracted to `play/reaction_applier.py`
  (`ReactionApplier`, no `arcade`); the view keeps a thin per-call delegator wiring the
  `post_system`/`on_reaction` ports. **Folds in the deferred PR #88 fix:** clock + stress writes
  run in one DuckDB transaction — a mid-write failure rolls back (no partial state) and posts
  `"⚠ Reaction could not be fully applied."`. New re-entrant `MemoryRepository.transaction()`
  (the one repo seam the non-goals permit): nested calls join the outer txn (no nested `BEGIN` —
  safe for Slice 4's reuse), `_in_transaction` always cleared. **Review-hardened** (`/code-review
  high`, 7 findings): precise failure-line semantics (reads + compute are guarded but degrade
  silently → a read-time DB error no longer escapes uncaught at the `_resolve_vna_roll` call site;
  only an atomic *write* failure posts the line, fixing the misleading "not fully applied" wording
  on compute failures); `_sync_actor_stress` creates a missing track so an unseeded-track binding
  shows in the panel without reload; `ClockState(**r)` (stops silently dropping `monotonic`);
  magic capacity `4` → `_DEFAULT_STRESS_CAPACITY` + dict lookup. Deliberately **kept the
  authoritative per-actor DB read** (`StressTrack(**t)`) over reusing in-memory `actor.stress` —
  capacity lives in the DB and the two can diverge (a low-value efficiency finding not worth a
  capacity-correctness regression). 5 new tests (3 applier: compute-fail-silent,
  read-fail-contained, new-track-synced; 2 repo: nested-txn commit/rollback); the one behavioral
  change in the phase. Full suite green (**3431 passed**), ruff + mypy(strict) clean.
- ✅ **Slice 2 — `NarrationCoordinator`** (2026-07-06). New `play/narration.py` (no `arcade`) —
  `NarrationCoordinator` + `DMResult` (moved out of `play_view`, re-exported for the existing
  `from …play_view import DMResult` sites). Owns the DM-narration plumbing: `_dm_history` +
  `compact_history` (token budget 2000), `build_context_bundle`, `spawn_dm_thread`, the `DMResult`
  queue + `_llm_busy`. **Public seam:** `request_narration(msg)` collapses the **8× (10 sites)**
  narration-entry idiom (`_compact_history` → append user → `set_busy(True)` → `_spawn_dm_thread`),
  and `poll()` drains + routes the queue (error / dungeon-reply / DM narration) — the drain moved
  out of `on_update`. A generic `spawn(worker)` serves the dungeon-voice channel
  (`_send_dungeon_line`). Side effects flow through narrow **ports** (all late-bound lambdas reading
  live view state — `on_busy`/`post_dm`/`post_system`/`on_dungeon_reply`/`extract_remember`/
  `auto_remember`/`on_bundle_built`); no `PlayView` reference. `play_view` 2759 → 2679 lines.
  Coordinator is lazily materialized with get+set bridge properties (`_dm_history`/`_llm_busy`/
  `_result_queue`/`_active_thread`) — the Slice 0 pattern — so the `__new__` test factories stay
  unchanged. Behavior-preserving (busy-flag ordering, compact-before-append, room/level
  re-resolution via the session, error-before-dungeon routing all match the original inline code).
  13 new unit tests (`tests/unit/play/test_narration.py`); the direct-reference view tests migrated
  to the `view._narration.*` seam. **Review-hardened** (`/code-review high`, 3 findings applied):
  all four bound-method ports made late-bound lambdas (uniform + fixes a latent test-ordering
  fragility); `spawn_dm_thread` restored the original `assert state/dungeon` + non-optional `repo`
  (no silent stranded-spinner path); the `history` setter aliases the assigned list (preserving the
  old `_dm_history = <list>` semantics). Full suite green (**3444 passed**), ruff + mypy(strict) clean.
- ✅ **Slice 3 — `DialogueCoordinator`** (2026-07-06, `9eff1d6`). New `play/dialogue.py` (no
  `arcade`) — `DialogueCoordinator` + `DialogueSession` (moved out of `play_view`, re-exported for
  the `from …play_view import DialogueSession` sites). Owns the dungeon-voice + NPC dialogue seam:
  the open channel, begin/end + room-change close, per-`kind` line routing (`send_line`/
  `send_npc_line`/`send_dungeon_line`), the §4.4 `agent_inputs` context assembly + its
  subsystem/objective/knowledge/room-label helpers, the intimacy-clock read, `begin_dungeon_dialogue`
  gate, `set_persona`, and the `apply_dungeon_reply` engine side-effect (reply bubble +
  engine-authored exchange memory). Side effects flow through narrow **late-bound ports**
  (`post_message`/`set_dialogue_mode`/`set_busy`/`get_room_context`/`get_acting_actor`/
  `get_voice_agent`/`get_narration`); no `PlayView` reference. The dungeon-voice call still runs on a
  worker thread handed to the **Slice 2 `NarrationCoordinator`** (`spawn`); its dungeon-marked
  `DMResult` routes back through `poll()` → `on_dungeon_reply` port → the view's `_apply_dungeon_reply`
  delegator → `apply_dungeon_reply` (no narration change). `PlayView` keeps thin **delegators** (its
  input-routing surface: call sites, the `window.set_dungeon_persona` API, the narration port) + the
  bridged state (`_dialogue`/`_dungeon_voice`/`_dungeon_knowledge`) so the existing view tests and the
  `__new__` factories stay unchanged; coordinator lazily materialized (the Slice 0/2 pattern).
  Behavior-preserving; `play_view.py` 2679 → 2478 lines. 29 new unit tests
  (`tests/unit/play/test_dialogue.py`) exercise the coordinator directly against a real
  `MemoryRepository` + a recording chat port. **`/code-review high` clean** (2 correctness finder
  angles — port-fidelity line-by-line + cross-file/threading tracer — no findings). Full suite green
  (**3473 passed**), ruff + mypy(strict) clean.
- ✅ **Slice 4 — `ActionOrchestrator`** (2026-07-06, `c15dd65`). New `play/actions.py` (no
  `arcade`) — `ActionOrchestrator` (16 late-bound ports) owns the action seam: the
  `on_vna_submit` dispatch tree (dialogue gate, look/activate/use branches), the card-roll path,
  validated-command application + objective advancement, the obstacle seams (contested approaches
  + DM-ruled resolutions), the LLM proposal pipeline, and world-reaction application (via the
  Slice 1 `ReactionApplier`); `describe_spawned_loot` moved here. `PlayView` keeps thin delegators
  for real callers + a lazy `_ensure_actions` bridge (the Slice 0/2/3 pattern) so the view tests +
  `__new__` factories stay unchanged; behavior-preserving, `play_view.py` 2478 → ~2030 lines.
  25 new unit tests (`tests/unit/play/test_actions.py`) exercise the orchestrator directly (real
  `MemoryRepository`, real `RpgService`, recording ports). **Review-hardened** (8-angle
  `/code-review high`, verified fix list applied): stale view-method spies migrated to the
  `view._actions` seam (the negative asserts were vacuous post-extraction, incl. the Phase 38
  smoke Behavior 14 spy); `get_nouns` port guarded so a `__new__` view degrades to `[]`; 7 dead
  view delegators (+ unused `ValidationResult` import) deleted; `on_look_submit` noun-label loop
  collapsed into `_noun_label_for`; `on_exit_move` port made keyword-shaped (`item_slug=`);
  `DebugControls(RpgService())` over `MagicMock()` (TESTING.md); the 3 `describe_spawned_loot`
  tests moved to mirror the module. Also folded in a **Slice 0 carryover**: the smoke
  `_make_view_with_chip` never migrated its roster to the `_session` seam (Behavior 13 read the
  actor id, not the display name — red on the WIP commit); one-line `view._session.set_actors(...)`
  fix, phase-38 smoke now all-green. Full suite green (**3498 passed**), ruff + mypy(strict) clean.
- ✅ **Slice 5 — `NavigationCoordinator`** (2026-07-06, `c99007c` + review `9801650`). New
  `play/navigation.py` (no `arcade`) — `NavigationCoordinator` (11 late-bound ports) owns the
  navigation seam: `on_exit_move` (engine-validated party move via `apply_move_party`, reject
  warning, map/scene/selection follow, vna refresh, save, move narration, incl. the level-change
  `map.load` + viewed-level tracking), `on_graph_room_select` (enter a clicked room + "We enter …"
  narration), `focus_party_room` (reflect the saved room on load/resume, no narration), and the
  layout-label helpers `prepare_vna_exits`/`current_level_rooms` (`_PositionedRoom` moved here).
  Side effects flow through narrow ports (`post_message`/`request_narration`/`set_selected_room`/
  `set_current_room`/`set_scene`/`load_level`/`update_map_state`/`set_viewed_level`/
  `end_dialogue_on_room_change`/`refresh_vna_panel`/`save_session`); no `PlayView` reference.
  `PlayView` keeps thin delegators (its input-routing surface — the `on_room_select` wiring,
  `_refresh_vna_panel`'s exit-label call) + a lazy `_ensure_navigation` bridge; the direct-index
  level lookups became bounds-checked `session.current_level()`/`current_room()` accessors.
  Behavior-preserving; `play_view.py` 2030 → 1899 lines (dropped the now-unused `dataclass`
  import). 9 new unit tests (`tests/unit/play/test_navigation.py`) exercise the coordinator
  directly (real `MemoryRepository`, recording ports); existing view tests stay green via the
  delegators. **`/code-review high` — no correctness bugs** (3 angles converged: the extraction is
  faithful); 2 low-severity quality fixes applied (`9801650`): a `_reflect_room(room, level, *,
  select)` helper for the map-cursor + chat + scene trio duplicated across 3 methods, and
  `set_viewed_level` moved inside the `level is not None` guard so paging can't point at a level the
  map never loaded. Full suite green (**3507 passed**), ruff + mypy(strict) clean.
- ✅ **Slice 6 — `MemoryCoordinator`** (2026-07-06, `df6a2a6`). New `play/memory_coordinator.py`
  (no `arcade`, 7 late-bound ports) owns the memory seam: `extract_remember`, `handle_remember`
  (`/remember`), `auto_remember` (`[REMEMBER: …]` hook), `load_memory_entries` (MEM-panel
  population), `persist_pending_commit` (MEM-tab approve/reject), and the level-memory overlay
  persistence (`has_level_memory`/`load_level_memory`/`save_level_memory`). The two remember paths
  are de-duped behind a `_record_room_event` helper. The overlay *widgets* (`_open_overlay_ui`/
  `_draw_overlay_*`) stay in the view — the coordinator owns only the persistence behind them. Side
  effects flow through narrow ports (`post_message`/`append_room_event`/`load_room_memory`/
  `save_room_memory`/`set_entries`/`pop_pending_commit`/`refresh_memory_state`); no `PlayView`
  reference. `PlayView` keeps thin delegators (its input-routing surface — `/remember` routing, the
  MEM-click handler, the overlay open/save/close widget lifecycle) + a lazy `_ensure_memory` bridge;
  dropped the now-dead `import re`, `_REMEMBER_RE`, and the `MemoryEntry` import. Direct-index level
  lookups became bounds-checked `session.current_level()`/`current_room()` accessors (crash →
  graceful no-op on a corrupt out-of-range save; the accepted Slice 5 approach). Behavior-preserving;
  `play_view.py` 1899 → 1878 lines. 17 new unit tests (`tests/unit/play/test_memory_coordinator.py`)
  exercise the coordinator directly (real `DungeonRepository` + `MemoryRepository` + recording
  ports); existing view tests stay green via the delegators. **`/code-review high` — extraction
  verified faithful** (2 finder angles: line-by-line/removed-behavior + reuse/conventions —
  message strings, `_refresh_memory_state`-only-on-`/remember` ordering, `save_memory_overlay`
  no-close-on-null-state, campaign_id fallback, port arg shapes all byte-checked); 1 quality fix
  applied inline (the narration `extract_remember`/`auto_remember` ports stay pointed at the view
  delegators, consistent with the other narration ports + the four other memory seams, so the
  wrappers remain production-reachable). Full suite green (**3524 passed**), ruff + mypy(strict) clean.
- ✅ **Slice 7 — `PlaySessionController`** (2026-07-06, uncommitted; the phase-closing slice). New
  `play/controller.py` — composition root wiring the five coordinators + the shared
  `PlaySessionContext` (received, not owned) + the session-facade methods lifted from the view; the
  `PlayHost` structural protocol keeps `play → views` uncrossed. The view's five `_ensure_*` factory
  methods collapsed into a lazy `_ensure_controller()` bridge; thin delegators remain the tested input
  surface. 5 new unit tests; `spec/ARCHITECTURE.md` amended; `play_view.py` 1878 → **1491**
  (criterion-1 ≤900 not met — see the ⚠ note above). Full suite green (**3529 passed**), ruff +
  mypy(strict) clean; 5-angle `/code-review high` found no correctness bugs. **Open:** owner GUI
  verify (criterion 6) + commit/PR.

1. **Phase 51.6 — World Reaction Policy — ✅ COMPLETE (PR #88 open, review-hardened).** Fixed a
   real bug (a STUDY-miss moved 3 clocks incl. `dungeon_intimacy`, violating D5). Per-object
   `reaction_policy` (`scripted`/`ambient`/`inert`) + `ClockCategory` firewall replace the
   "miss = every tagged clock +2" fan-out. **Slice 10 GUI verify passed** (owner, 2026-07-05).
   Phase scope/exit criteria `spec/PHASE_51_6_WORLD_REACTION_POLICY.md`; design canonical
   `spec/WORLD_REACTION_POLICY.md`.

   **PR #88 opened 2026-07-05** (`feat/phase-51.6-wrp` → `main`; bundles the mypy 348→0 sweep).
   Ran `/pr-review-toolkit:review-pr all parallel` (5 agents). No merge-blockers found (firewall
   holds by construction). **Hardening commit `419713e`** applied 4 converging findings:
   (a) `world_reaction` now **logs** when a scripted binding names an unresolvable / firewalled
   `dungeon_intimacy` clock (was a silent no-op — the f5ab7b1 observability gap); an inactive
   target stays quiet; (b) `is_adverse` narrowed to `ClockCategory | None` so mypy catches any
   caller that skips `normalize_clock_category`; (c) `ObjectReactionBinding` pairing validator
   rejects silent-no-op shapes (slug w/o nonzero delta, stress w/o amount; all-empty stays legal);
   (d) new integration test `tests/integration/test_crucible_reaction_bindings_resolve.py` seeds
   the real Crucible (seed pack + both populate scripts) and pins that **every scripted CLOCK
   binding resolves to an active adverse clock via the uuid5 id path** — the end-to-end check
   Slice 10's manual verify skipped. Also: fixed the stale "Phase 35" `world_reaction` module
   header and **deleted the now-dead `rpg/stress_routing.py` + its test** (world_reaction dropped
   its only production import). Suite green (**3408 passed** — the 3430→3408 delta is the removed
   `test_stress_routing.py`, offset by +8 new hardening tests), ruff + mypy(strict) clean.

   **Deferred from PR #88 review — both now dispositioned (2026-07-05):** item 1 is Phase 51.7
   Slice 1; item 2 is closed (spec corrected). Historical detail:
   - **Non-atomic, user-silent write** in `play_view._apply_world_reaction` (`:2133-2170`):
     pre-existing broad `try/except Exception → return None` spans compute **and** multiple
     sequential DB writes (clock + stress). A mid-loop DB error half-applies state and shows the
     GM nothing (it does log a traceback). WRP newly routes scripted clock+stress writes through
     it, raising the stakes. Fix = wrap the writes in one transaction and/or surface a user-facing
     "reaction could not be fully applied" line. Own change (behavioral), not a hardening tweak.
   - **Spec-language decision (code-reviewer #1) — ✅ CLOSED (owner ruled (a), 2026-07-05):**
     §7 said "all THREE `_apply_world_reaction` call sites must pass `acted_object`," but only
     noun-carrying paths can — the two chat paths (`:829`, `:994`) have no noun by construction
     and correctly fall to the ambient rule with `acted_object=None`. Spec corrected
     (`spec/WORLD_REACTION_POLICY.md` §7 seam bullet, amended 2026-07-05); any future
     noun-carrying chat path must wire the object per the Slice 8 pattern. No code change.
   - Minor (nice-to-have): `CLOCK_CATEGORIES` via `get_args(ClockCategory)` to kill the
     Literal/tuple duplication; a `RoomObject` validator rejecting non-empty `reaction_bindings`
     when `reaction_policy != "scripted"`; move `derive_clock_id` to a shared id helper so the
     engine need not import `seed_pack`.

   **Slice progress (branch `feat/phase-51.6-wrp`) — ALL COMPLETE:**
   - ✅ **Slice 1 — `ClockCategory` enum + typed `category` + `is_adverse`** (`rpg/models.py`,
     `tests/unit/rpg/test_models.py`). `ClockCategory` Literal (7 members); `ClockState.category`
     typed `ClockCategory | str | None` — enum intent for the firewall, `str` still accepted so
     pre-normalization saves/seeds load (confirmed live seeds carry non-enum `threat`/`escalation`/
     `environment` — Slice 2 maps those). Pure `is_adverse()` = category ∈ {danger,pursuit,ritual}.
     Full suite green (3385 passed).
   - ✅ **Slice 2 — clock-category normalization pass** (data) (`rpg/models.py`,
     `tests/unit/rpg/test_models.py`, `tests/unit/rpg/test_seed_pack.py`). `CLOCK_CATEGORIES`
     (runtime tuple) + pure `normalize_clock_category()` (None→None; canonical members idempotent;
     synonyms `threat`/`environment`→`danger`, `escalation`→`pursuit`; **unknown → `faction_pressure`
     fallback** — a firewall-protected, non-adverse member so an unrecognized clock can never become
     ambient-eligible) + `is_known_clock_category()` (the "not silent" flag for data passes). Seed
     coverage guard in `TestCampaignSeedFilesValidate` confirms every shipped Crucible/tomb clock
     category normalizes onto the enum. Full suite green (3396 passed).
   - ✅ **Slice 3 — `reaction_policy` + `ObjectReactionBinding` models** (pure model) (`rpg/models.py`,
     `tests/unit/rpg/test_models.py`). `RoomObject.reaction_policy: Literal["scripted","ambient",
     "inert"] = "ambient"` + `RoomObject.reaction_bindings: list[ObjectReactionBinding]`. New
     `ObjectReactionBinding` (`binding_id, object_id, action_verb` with `*` wildcard, `outcome:
     Literal["miss","partial"]`, `clock_slug: str|None`, `clock_delta: int=0`, `stress_track:
     str|None`, `stress_amount: int=0`) — miss/partial tiers only (success/critical flow through
     transitions + the objective service, D5). Round-trip + defaults + validation covered. Full
     suite green (3407 passed).
   - ✅ **Slice 4 — migration `019` + repo load/save** (persistence) (`019_reaction_policy.sql`,
     `memory/repository.py`, `tests/integration/test_rpg_memory_migrations.py`,
     `tests/unit/memory/test_room_object_repository.py`). One migration adds the `reaction_policy`
     column on `room_objects` (DEFAULT `'ambient'`, DuckDB backfills old rows) **and** the
     `object_reaction_bindings` table. Repo `save_room_object` upserts policy + delete-then-insert
     bindings (like `transitions`); all three SELECTs carry `reaction_policy`;
     `_room_object_row_to_dict` loads `reaction_bindings` and coalesces NULL policy → `ambient` for
     pre-019 rows. Tests: 019 applies on an `018`-head DB (old row reads `ambient`, bindings table
     present), column-present, round-trip incl. policy + bindings, default-when-unset, upsert
     replaces bindings. Full suite green (3412 passed).
   - ✅ **Slice 5 — ambient selection rule** (pure helper) (`rpg/world_reaction.py`,
     `tests/unit/rpg/test_world_reaction.py`). `select_ambient_clock(active_clocks, room_id,
     level_id) -> ClockState | None` — gathers active **adverse** clocks (`is_adverse` ∘
     `normalize_clock_category`, so pre-normalization synonyms like `threat` still count) scoped
     to the party's room/level, returns the single **tightest-scoped** one (room > level, ties by
     lowest `clock_id`); firewalled categories (`objective`/`relationship`/`faction_pressure`/
     `dungeon_intimacy`) and dungeon/quest scope are never eligible; ignores `action_tags`;
     `None` → narration only. Both spec worked examples covered (statue-miss in R1 → "Scorpion
     Nest Agitated"; none → `None`) + room-over-level, tie-break, firewall, dungeon-scope,
     inactive-skip, synonym. Full suite green (3421 passed).
   - ✅ **Slice 6 — scripted binding resolution** (pure helper) (`rpg/world_reaction.py`,
     `tests/unit/rpg/test_world_reaction.py`). New `Consequence` frozen dataclass (resolved
     effect: `clock_slug`/`clock_delta`/`stress_track`/`stress_amount`) +
     `resolve_scripted_bindings(bindings, verb, outcome) -> list[Consequence]` — matches on
     `outcome` **and** verb (`action_verb == verb` or `*` wildcard); a `partial` with no
     authored partial row falls back to the matching `miss` binding(s) at **half magnitude,
     rounded toward zero (min 1 when the miss value is nonzero; 0 stays 0)**, applied
     independently to `clock_delta` and `stress_amount`; no match → `[]` (no fan-out).
     9 tests: verb match, wildcard, non-matching verb/outcome skip, empty→nothing,
     authored-partial-wins, half-miss fallback, min-1-nonzero, zero-stays-zero. Full suite
     green (3430 passed).
   - ✅ **Slice 7 — engine branch + firewall + cap** (engine) (`rpg/world_reaction.py`,
     `tests/unit/rpg/test_world_reaction.py`, `tests/unit/rpg/test_service.py`,
     `tests/integration/test_clock_scoping_integration.py`). `compute_world_reaction` gains
     `acted_object: RoomObject | None` and branches on `reaction_policy`: `scripted`→authored
     `reaction_bindings` only (via `resolve_scripted_bindings`; `dungeon_intimacy` never moved
     here even if a binding names it — D5 firewall by construction; stress authored on the
     binding); `ambient` (default, incl. all non-object actions)→**≤1** `+1` tick on the nearest
     local adverse clock (`select_ambient_clock`), miss/partial only, never rolls back, no
     stress; `inert`→zero mechanics. Removed the tag-matching path, `_CLOCK_TICKS`/
     `_STRESS_AMOUNT`, and the `choose_stress_track` call (`stress_routing.py` itself untouched —
     its own unit tests still cover the pure helper). Superseded Phase 35 tag-fan-out tests
     rewritten to the ambient contract. Full suite green (3414 passed).
   - ✅ **Slice 8 — seam: wire the object through the call sites** (integration/view)
     (`rpg/service.py`, `views/play_view.py`, `tests/unit/rpg/test_service.py`,
     `tests/unit/views/test_play_view_vna.py`, `tests/unit/views/test_play_view_bundle.py`).
     `react_to_resolution` gains `acted_object` (forwards to `compute_world_reaction`);
     `_apply_world_reaction(resolution, acted_object=None)` forwards it; new
     `_resolve_acted_object(noun_id)` maps a card noun → `RoomObject` (policy + bindings from the
     repo) or `None` for item/actor/unknown/no-repo; `_resolve_vna_roll` resolves `card.noun_id`
     and passes it in. The two chat-action paths (`:818`, `:983`) are intent/action-key based (no
     noun) so they keep the default `acted_object=None` — the "non-object action → ambient" case.
     Tests: service threads scripted binding (not ambient); `_resolve_acted_object` returns
     policy/None cases; `_apply_world_reaction` end-to-end (real service + repo) — scripted object
     moves **only** its bound clock, non-object action moves the ambient clock, and a guard test
     pins the synthesized `f"level-{idx+1}"` level-scope convention (`:2071-2073`);
     `_resolve_vna_roll` spy confirms the object is threaded. Full suite green (3422 passed).
   - ✅ **Slice 9 — seed the Crucible policy map + bindings** (seed, design §6)
     (`tools/populate_crucible_level1.py`, `tools/populate_crucible_dungeon_channel.py`,
     `tests/unit/tools/test_populate_crucible_level1.py`,
     `tests/unit/tools/test_populate_crucible_dungeon_channel.py`). Authored the §6
     object→policy map + scripted miss bindings. **Level 1** (`_rb` helper + `_obj` policy/
     bindings params): `great-lift`→`arcane-overload-building +1`, `gearworks`→`party-detected
     +1`, `spike-plates`→Body +2, `dart-vents`→Body +1 (all `*`-verb miss), `trap-lever`
     scripted with **no** binding (deterministic control); the six scenery/lore/container
     objects stay `ambient` (model default). **Level 2** (`_Rung.miss_clock_slug/_delta` +
     bindings in `_subsystem_object`): `coolant-loop`/`arcane-conduits`→`arcane-overload-building
     +1`, `core-containment`→`+2` (climax), `arcane-resonance-node`→Weird +1. Every clock delta
     targets an **adverse** clock; a guard test pins that **no binding names a firewalled clock**
     (`the-dungeon-learns-you`/`restore-the-power-core`/`mira-guild-agenda-surfaces`/
     `djinn-reclaims-the-engines`). `save_room_object` delete-then-inserts bindings, so reseed is
     a no-op and preserves play state (upsert `current_state`). 7 new tests; full suite green
     (**3429 passed**). ruff + mypy(strict) clean.
   - ✅ **Follow-up fix — scripted clock bindings resolve uuid5-seeded ids**
     (`rpg/world_reaction.py`, `tests/unit/rpg/test_world_reaction.py`, commit `f5ab7b1`).
     Live-save prep exposed a Slice 7 gap: `_find_clock_by_slug` matched only the
     `clock:{campaign}:{slug}` string form (`campaign.seeder._clock_id`), but the path that
     actually seeded the live Crucible — `rpg.seed_pack.apply_seed_pack` — writes
     `uuid5(campaign_slug:slug)` ids, so **every scripted CLOCK binding silently no-opped on the
     real save** (the §5 Coolant-Loop example would not have fired). Fix also matches
     `derive_clock_id(campaign_slug, slug)`. Ambient selection + stress bindings were unaffected
     (no slug lookup). Verified live: all three bound slugs now resolve to their UUID clocks.
   - 🟢 **Live save PREPPED for Slice 10 (2026-07-05):** the live Crucible
     (`…/DungeonDaddy/saves/The Crucible/campaign.duckdb`) was migrated `018→019` (via
     `initialize_schema`) and reseeded with both populate scripts — policies/bindings now match
     §6 (statue `ambient`/no binding; gates/hazards/subsystems `scripted`; firewalled clocks
     untouched). Play state preserved (new-game: R1/L1, ladder tier 0 active, intimacy 0/4, R1
     "Scorpion Nest Agitated" active 0/4). Backup: `campaign.duckdb.bak-phase516-slice9-20260705-141458`.
   - ✅ **Slice 10 — manual GUI verify** (no automated UI): owner-verified **green** on the live
     Crucible (2026-07-05) — an ambient statue miss **and** partial in R1 tick **only** "Scorpion
     Nest Agitated" **+1**; the Power Core / Factory-Learns / Mira / `dungeon_intimacy` clocks stay
     put. (Confirmed intended: the ambient path ticks +1 on `miss` **and** `partial` per design §4 —
     a flat +1, not half; half-magnitude is scripted-partial-fallback only.) Live save then reset to
     a fresh new-game (party R1/L1, clocks 0, ladder tier 0) via `tools.reset_crucible_new_game`
     (backup `campaign.duckdb.bak-newgame-20260705-142851`) — the reset preserves
     policies/bindings (it only touches `current_state`).
2. **Then: Tag Hygiene → Narrator Lookup Tool** — new two-part spec
   `spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md` (draft 2026-07-04): Phase A unifies the tag
   taxonomy and fixes the broken tag pipeline (audit: actor tags dropped at seed time, three
   actor-namespace spellings, retrieval never passes tags, untagged world entities); Phase B
   gives the narrator agents a read-only `lookup_world` DuckDB tool. Owner-decided: **agent-owned
   tool loop** (provider stays pure transport) and **two-tier retrieval** (deterministic
   `# Related Lore` pre-fetch by default; tool only for out-of-scene topics). Remaining
   T/L decision points to ratify at phase start. Sequenced after WRP.
3. **Phase 52 (Milestone Advancement)** or **Phase 53 (Threat Behavior)** — next roadmap phases
   (`spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`).

Reference on the just-shipped 51.5 work (live Crucible state, condensed architecture, locked decisions
D1–D8) is retained below.

> Full per-slice build detail (Parts A + B, the `ResolveObstacleChange` gate, and the `ActivateObject`
> resolution seam) is in git history and canonical in `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md` (§11) +
> `docs/LLM_AUTHORITY_BOUNDARY.md`.

### Live Crucible state (2026-07-01, post container-loot reseed + new-game reset)
Fresh new-game — party in **R1/L1**, only R1 visited, empty transcript; ladder at **tier 0
`clear-the-gearworks` active**, tiers 1–3 locked; all clocks **0** (intimacy 0/4). Container-loot
coherent: `supply-locker` **closed** with `open|force → spawns travel-journal`; `travel-journal`
**inert/unplaced**. Backups: `campaign.duckdb.bak-containerloot-reseed-20260701-133213` (pre-reseed) +
`…bak-newgame-20260701-133542` (pre-reset). Live saves at `C:\Users\ljfan\AppData\Local\DungeonDaddy\saves`.

### Phase 51.5 — what's built (Slices 1–10, condensed architecture)

- **Models/repo:** `Objective`/`ObjectiveCompletion` (`rpg/models.py`) + `ObjectiveManifest` + migration
  `018_objectives.sql` + repo (`save_objective`/`get_objectives`/`update_objective_status`).
- **Service (`rpg/objectives.py`):** pure `completion_satisfied(completion, world_state)`; `advance_objectives(
  repo, campaign_id)` — completes satisfied active objectives, ticks the **latching** intimacy clock (the
  *single* tick source, D5), activates the next tier, drafts a memory. Chat no longer ticks intimacy.
- **Channel helpers (`rpg/dungeon_channel.py`):** `dungeon_systems_status` / `located_systems_status`,
  `unlocked_knowledge`, `active_objective`, `CHANNEL_OPEN_THRESHOLD=0.0` (channel opens cryptic at tier 0).
- **Agent/LLM:** `DungeonVoiceAgent` gains `# Who Is Speaking` / `# Systems Status` / `# What You Want Next`
  / `# This Conversation So Far` (+ object/objective **locations**); `play_view._dungeon_agent_inputs`
  assembles them fresh each turn.
- **Wiring:** `play_view._apply_vna_command` → `_advance_objectives()` after each command, posts a
  `"dungeon"` bubble per tier-up. AI memories written `approved` (no review queue,
  `apply_low_risk_proposals`).
- **Seed:** `tools/populate_crucible_dungeon_channel.py` (+ level1 seed) — 4-tier ladder (`gearworks`,
  `coolant-loop`, `arcane-conduits`, `core-containment`), per-tier `reveals_knowledge`, latching intimacy
  clock; idempotent + preserves play progress.

### Phase 51.5 — locked decisions (D1–D8)

D1 objectives-only intimacy (chat no longer ticks; tiers latch) · D2 first-class `Objective` model (also
seeds Phase 52 Milestones) · D3 full 3–4-tier Crucible ladder · D4 deterministic completion keyed to world
state, engine-evaluated after each command (no event bus) · D5 the objective service is the single
intimacy-tick source · D6 the `dungeon_intimacy` clock is a latching tier index · D7 per-tier
`reveals_knowledge` (flat `reveal_knowledge` kept deprecated) · D8 stays Phase 51.5 on `phase-51`; 51 +
51.5 merge to `main` together once built.

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks,
> consequences, and narration. The human player controls the player side: one or more
> player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is
advisory. It may narrate, frame choices, interpret tone, and propose structured world
reactions. It must not directly mutate authoritative state. *(Phase 51.5 Part B added one
narrowly-constrained, validator-gated exception: the DM may propose resolving an obstacle, but only to
its authored resolved state — see `docs/LLM_AUTHORITY_BOUNDARY.md`.)*

---

## Known Failures

**None.** Full unit/integration suite green (3195). The previously-flaky generator eval is resolved
(`26e95a3`, 2026-06-23): evals are excluded from the default run (`addopts = "-m 'not eval'"` —
run with `pytest -m eval`), and `test_generator_level_passes_validation` mirrors production's
3-retry regenerate-with-errors budget instead of asserting one-shot validity.

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Recent completed phases:

| Phase | Summary | Spec |
|---|---|---|
| 51.6 — World Reaction Policy | Per-object `reaction_policy` (`scripted`/`ambient`/`inert`) + `ObjectReactionBinding` sibling table + migration `019`; `ClockCategory` enum firewall (adverse = danger/pursuit/ritual); `rpg/world_reaction.py` ambient (≤1 local adverse clock, +1 on miss/partial) vs scripted (authored bindings only, `dungeon_intimacy` never moved — D5 by construction); Crucible §6 policy/binding seed; uuid5 clock-id resolution fix; PR-review hardening (silent-no-op logging, `is_adverse`/binding-validator firewall-by-construction, live-seed resolution integration test). Kills the "miss = every tagged clock +2" fan-out | `spec/PHASE_51_6_WORLD_REACTION_POLICY.md` (PR #88, `feat/phase-51.6-wrp` → `main`) |
| 51.5 — Dungeon Objectives & Intimacy Tiers | `Objective`/`ObjectiveCompletion` + migration `018`; deterministic `advance_objectives` (single intimacy-tick source, latching tier ladder + per-tier knowledge); puzzle-obstacle Parts A+B (`rpg/obstacles.py`, `ResolveObstacleChange`); container-loot via `spawns_item_slug` | `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md` (PR #83) |
| 51 — Talk to the Dungeon | Live dungeon-voice channel at resonance points; `DungeonVoiceAgent`; recedable/latching intimacy clock (migrations `016`/`017`); dungeon-persona persistence (Markdown + DuckDB refs); ◆ THE CRUCIBLE chat treatment | `spec/PHASE_51_TALK_TO_THE_DUNGEON.md` (PR #83) |
| 50.6 — Chat Action Cockpit | In-chat Action Builder (V·N·T·A slot chips + popups); "Things Here" clickable room overlay (click exit = auto-move, item = auto-pickup); retired the right-panel ACTION + EXITS tabs; dynamic/collapsible builder band | `spec/PHASE_50_6_CHAT_ACTION_COCKPIT.md` (PR #82) |
| 50.5 — Use Noun on Noun | Grammar → `Verb · Noun · [Target] · Adverb`; `TRANSITIVE_VERBS`; `CombineItems` + migrations `013`/`014`; `GiveItem` validator; `activate` wired; `look` verb; Target dropdown | `spec/PHASE_50_5_USE_ON_GRAMMAR.md` (PR #81) |
| 50 — Hybrid Action Model | Verb·Noun·Adverb action *Card*; `ActionCard` + `validate_card`; `resolve_card`/`resolve_card_roll` (`rpg/action_resolution.py`); `VnaActionPanel`; hybrid exit labels (`rpg/exit_labels.py`) | `spec/PHASE_50_HYBRID_ACTION_MODEL.md` (issue #80) |
| 49 — Starting Playbooks | `Playbook` + `PlaybookLibrary`; `data/playbooks.json`; `actor_abilities` table + repo CRUD; seed-publish wiring; playbook picker; Character Sheet panel | `spec/PHASE_49_STARTING_PLAYBOOKS.md` (issue #77) |
| 48 — Dungeon Navigation | `RoomExit` + `room_exits` schema; `MoveParty`; level transitions; `Discover/Unlock/Seal/BlockExit`; room context bundle; exit-list panel + fog-of-war map | `spec/PHASE_48_DUNGEON_NAVIGATION.md` |
| 47 — Room Contents | Items + interactive objects (state-machine archetypes); `ActivateObject`/`PickUpItem`/`DropItem`; `current_room` context; Campaign Seed editor | `spec/PHASE_47_ROOM_CONTENTS.md` |
| 46 — Inventory System | `Item`/`ItemFeature`; class-kit/dungeon/gear commands; `compute_effective_ratings`; world-reaction item proposals; Character Sheet UI | issue #71 |
| 45 — Campaign Pipeline | Three on-disk libraries; publish pipeline; Library home screen | `spec/PHASE_45_CAMPAIGN_PIPELINE.md` |

Per-session implementation logs are in git history and the auto-memory (`project_phase_status.md`).

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: current/future in `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`; index at
  `spec/IMPLEMENTATION_PHASES.md`. Spec-loading rules and skills: `CLAUDE.md` (canonical).
- Roadmap for Phases 52–53 (planned): GitHub Projects `ghostpencil/dungeon-daddy` #1, mirrored in
  `IMPLEMENTATION_PHASES_33_ONWARDS.md`. A `spec/PHASE_NN_*.md` is written when each phase starts.
- Phase 53 (Threat Behavior & Monster Reactions, planned): engine-bounded monster reactions, no enemy
  turn; bosses escalate via clock thresholds. Design: `spec/MONSTER_REACTION_DESIGN.md`.
- World Reaction Policy → **Phase 51.6 — ✅ COMPLETE, verified & PR'd (#88), review-hardened
  (2026-07-05)** (branch `feat/phase-51.6-wrp`; do NOT fold into 51.5): per-object `reaction_policy`
  (`scripted`/`ambient`/`inert`) replaced the blunt "miss = every tagged clock +2" fan-out; fixed the
  bug (a STUDY-miss on the R1 statue moved 3 campaign clocks incl. `dungeon_intimacy`, violating D5).
  All 10 slices + GUI verify green. Phase scope: `spec/PHASE_51_6_WORLD_REACTION_POLICY.md`; design
  canonical: `spec/WORLD_REACTION_POLICY.md` (supersedes the miss behavior in
  `spec/PHASE_35_WORLD_REACTION_SERVICE.md`).
  - **Live-data gotcha (found + fixed during Slice 9/10):** `apply_seed_pack` writes UUID5 clock ids
    (`rpg.seed_pack.derive_clock_id`), not `campaign.seeder._clock_id`'s `clock:{campaign}:{slug}`
    string form. `world_reaction._find_clock_by_slug` now matches **both**, else scripted CLOCK
    bindings silently no-op on real saves (commit `f5ab7b1`). Any new code resolving a clock by slug
    on the Crucible must account for the UUID5 convention.
- Tag Taxonomy & Narrator Lookup (draft 2026-07-04, sequenced after WRP):
  `spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md` — Phase A tag hygiene (single namespaced taxonomy,
  migration `020`, seed/retrieval fixes, `# Related Lore` pre-fetch), Phase B read-only narrator
  lookup tool (`complete_round` provider transport + agent-owned loop in `llm/tool_loop.py`).
- Reseed-a-save gotchas: `--campaigns-dir` for the saves dir; `PYTHONPATH=.` for the populate scripts;
  close the app first (DuckDB is single-writer).
- New-game reset (dev/playtest): `python -m tools.reset_crucible_new_game` reverts play progress on the
  live Crucible (party→R1/L1, clocks→0, ladder→initial, objects→seed state, stress→0, items reseated,
  memories/events wiped) while keeping the authored campaign + dungeon persona docs. Auto-backs up
  `campaign.duckdb` + `session.json` first; close the app first.
- Evals: `pytest -m eval` (live API, paid, non-deterministic); baseline `python tools/run_evals.py`.
- **mypy baseline swept 348 → 0** (2026-07-05, branch `feat/phase-51.6-wrp`, commit `4985898`):
  the CI `Type-check` step (`python -m mypy dungeon_daddy`, strict) had been red for a long time.
  Annotation-only fixes across 41 files + ~18 real type-safety fixes (None-guards, Literal
  tightening, canonical `LLMMessage` import, list/dict invariance splits). None were active
  runtime bugs. ruff clean, full suite green. **CI still does not gate merges** (the `Tests`
  workflow only runs on push-to-`main` / PRs-to-`main`, and no branch protection requires it), so
  no GitHub run has executed the sweep yet — it'll run when this branch is PR'd/merged. To keep
  mypy green, new code must stay strictly typed; a new error is now a genuine regression.
