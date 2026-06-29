# Dungeon Daddy — Project Index

## Phase

Phase **50 / 50.5 / 50.6 — COMPLETE & merged to `main`** (Hybrid Action Model · Use-Noun-on-Noun
grammar · Chat Action Cockpit). Per-slice detail is in git history.

Phase **51 — Talk to the Dungeon: FEATURE-COMPLETE & GUI-verified** on branch `phase-51`. The live
dungeon-voice channel, the intimacy clock, `DungeonVoiceAgent`, Markdown-backed / DB-referenced
persona persistence, and resonance points are all built. Spec
`spec/PHASE_51_TALK_TO_THE_DUNGEON.md`.

Phase **51.5 — Dungeon Objectives & Intimacy Tiers: IN PROGRESS** on branch `phase-51` (extends 51;
**no merge to `main` until 51.5 is built** — owner decision). Driven by the 2026-06-27 playtest: the
channel was hollow. Spec `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md`, decisions locked D1–D8.
**Slices 1–10 DONE & committed** (the full intimacy ladder is built and seeded into the live Crucible),
plus three post-Slice-10 fixes this session. **Next session: the puzzle-obstacle / multi-approach
feature (#1+#2) — plan in START HERE.**

Specs: 51.5 `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md` · 51 `spec/PHASE_51_TALK_TO_THE_DUNGEON.md` ·
current/future `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (index `spec/IMPLEMENTATION_PHASES.md`).

---

## START HERE — next session: puzzle-style objective solving (#1 + #2)

Three playtest issues were raised 2026-06-28/29. **#3 (approved memories)** and the **systems-status
prompt fix** are DONE & committed (`27be4f9`) — GUI-verification of both is pending. **#1 + #2 are
planned and greenlit but not yet built** — that is next session's work.

### The feature (decisions locked)

- **#2 — multiple ways to solve an objective (Hybrid).** Today a room object's `current_state` only
  changes via the deterministic `activate` verb (fires the first transition matching `current_state`);
  **action rolls cannot change object state** (no object-state proposal type; the authority boundary
  forbids the LLM from touching object state). We want: an obstacle solvable by class-flavored
  approaches (Artificer **tinker**, Fighter **strong blow**, Thief **sleight/finesse**) *and* any
  plausibly-described action.
- **#1 — normalize completion (all paths → one COMPLETED objective).** An obstacle is a `RoomObject`
  in a "blocked" state with **multiple contested transitions that all converge on one canonical
  resolved state** (e.g. `gearworks: jammed ──{tinker|fight|finesse}──▶ cleared`). The objective
  completes when the object reaches that state — `completion_satisfied`/`advance_objectives` are
  already agnostic to *how* it changed — so the objective stays uniformly `completed`.
- **Outcome→success mapping (proposed, confirm before building):** full/critical → resolves; partial
  → resolves **with a complication**; miss → fails. (Owner may prefer partial = fail.)

### The seam

`play_view._resolve_vna_roll` (around `dungeon_daddy/views/play_view.py:1729`) computes a roll
`resolution` (`.outcome`), applies a world reaction, runs the LLM proposal pipeline, and narrates —
but **never touches `object_state`**. That is where the new mechanic plugs in. `_on_activate_submit`
(~`:1631`) routes contested transitions to `_resolve_vna_roll`; `_apply_vna_command` (~:1691) is the
deterministic path that already calls `_advance_objectives()` (~:1713).

### Slice plan (TDD; sequenced so Part A is a verifiable win on its own)

**Part A — authored class approaches (engine-deterministic, no authority change):**
1. Pure helper + validation: an obstacle's approaches all converge to one resolved state.
2. Extend the roll path: on a **successful** roll whose verb matches a contested transition on the
   target, the engine applies `update_object_state` + side-effects (spawns_item / advances_clock),
   then re-runs `_advance_objectives()`.
3. Surface the obstacle's approach verbs as suggested actions in the builder.
4. Re-author the 4 Crucible obstacles with class-flavored approaches → one resolved state; update the
   seed **additively** (preserve the adopted `gearworks` state — don't reset it to jammed).

**Part B — DM ruling for off-script plausible actions (the authority expansion):**
5. New constrained `ResolveObstacleChange` proposal type — validator permits pushing an obstacle only
   to its **authored** resolved state (the LLM can't invent states); applied on a successful roll.
6. Feed obstacle context into the proposal pipeline so the DM can rule a described action resolves it.
7. Update `docs/LLM_AUTHORITY_BOUNDARY.md` + the Phase 51.5 spec to record the constrained
   object-state authority.

### Session state (2026-06-29)

- **GUI-verify done this session:** systems-status truthfulness confirmed against the **live DB**
  (every reported state matched). Found + fixed one data bug: the **Great Lift** was two `room_objects`
  rows with divergent states (L1 `powered` / L2 `ready`) — the L2 row (`great-lift-upper`, inert, gated
  nothing) showed as a 2nd subsystem and the LLM collapsed the duplicate. Per owner decision (*demote the
  duplicate*), `great-lift-upper` re-archetyped `mechanism → lore_fixture` (state→`present`, deferring
  description); the L1 `great-lift` mechanism stays the single canonical lift that gates the vertical
  exit. Seed `tools/populate_crucible_level2.py` + new regression test
  `tests/unit/tools/test_populate_crucible_level2.py`; **live save re-seeded** (backup
  `campaign.duckdb.bak-lift-demote-*`). Systems status now reports a coherent 6 subsystems.
- **No review queue (owner decision):** approving AI changes is work, not gameplay — the AI impacts the
  world directly; we tune/limit behavior, not gate it. `apply_low_risk_proposals` was the last play-time
  writer still persisting `draft` (the rest already wrote `approved`); now writes `approved`
  (`e042dfd`). Drafts are inert anyway (retrieval reads only `approved`).
- **Dungeon knows object locations (new):** the dungeon-voice context now carries each subsystem's and
  the active objective's **`Level N — Room Name`** location, so it can answer "which room is X" and name
  *where* the task it wants is. New pure helpers `located_systems_status` / `object_location`
  (`rpg/dungeon_channel.py`); agent renders `(located in …)` + a `Location:` line + a system-prompt rule
  to state locations plainly (no deflecting); `play_view._room_labels` resolves room_id→label from the
  dungeon model and feeds `_dungeon_systems_status` / new `next_objective_location`.
- **Housekeeping:** deleted 32 inert `draft` memories from the live Crucible save (backup
  `campaign.duckdb.bak-predelete-drafts-*`); 14 approved memories intact.
- **Committed:** Slice 9 (`4ed5bfe`), Slice 10 (`4ba27e1`), dungeon-channel fixes (`27be4f9`), lift
  one-object fix (`ee27a72`), auto-approve memories (`e042dfd`); dungeon-location feature pending commit.
- **Live Crucible save IS seeded** with the ladder (backup `campaign.duckdb.bak-slice10-applied-*`).
  Current live state: `gearworks` **jammed** (tier 0 active — to complete it now, go to **R4** and
  **Activate** it; the multi-approach work is what makes tinker/smash/finesse also work);
  `arcane-conduits` **charged** out of order (tier 2 locked → banked; it will **cascade-complete** once
  tiers 0 and 1 are done, since `advance_objectives` re-evaluates a freshly-activated tier in the same
  pass); `coolant-loop` ruptured, `core-containment` failing; intimacy clock **0/4 latching**.
- **Pending GUI-verify (next launch — prompt loads fresh, no save mutation needed):** (a) ✅ done —
  systems assessment lists all subsystems truthfully (verified vs live DB; lift now reports once); (b)
  the dungeon no longer claims state that isn't real and names its want instead of re-asking; (c)
  dungeon memories are approved (no curation queue) and feed back across sittings.

### Phase 51.5 — what's built (Slices 1–10, condensed)

Models/helpers first, then service, context/LLM, wiring, seed:
- **S1–S2** `Objective`/`ObjectiveCompletion` models + `ObjectiveManifest` + migration `018_objectives.sql`
  + repo (`save_objective`/`get_objectives`/`update_objective_status`).
- **S3** pure `completion_satisfied(completion, world_state)`; **S4** `advance_objectives(repo,
  campaign_id)` service (`rpg/objectives.py`) — completes satisfied active objectives, ticks the
  latching intimacy clock (the **single** tick source, D5), activates the next tier, records a memory.
- **S5** dropped the per-chat intimacy tick (`record_dungeon_exchange` now only records memory).
- **S6** `dungeon_systems_status(room_objects)`; **S7** `unlocked_knowledge(objectives)` /
  `active_objective(objectives)` (all in `rpg/dungeon_channel.py`).
- **S8** `DungeonVoiceAgent` gains `# Who Is Speaking` / `# Systems Status` / `# What You Want Next` /
  `# This Conversation So Far`; `play_view._dungeon_agent_inputs` assembles them (reads repo fresh
  each turn).
- **S9** (`4ed5bfe`) `play_view._apply_vna_command` → new `_advance_objectives()` after each command,
  posts a `"dungeon"` bubble per tier-up.
- **S10** (`4ba27e1`) seeded the full Crucible ladder — **hybrid sourcing, 4 tiers, channel opens at
  tier 0** (owner decisions 2026-06-28). Tier 0 **adopts** the existing `gearworks` (jammed→cleared);
  tiers 1–3 author fresh L2 subsystems (`coolant-loop` r02 ruptured→restored, `arcane-conduits` r03
  dormant→charged, `core-containment` r05 failing→stabilized). 4 `Objective`s (tier 0 `active`, rest
  `locked`; `advances_clock_slug="dungeon_intimacy"`) + per-tier `reveals_knowledge` (the 5 forge-mind
  secrets across tiers). Intimacy clock re-segmented **latching** (`segments=4`, `filled=#completed`,
  `monotonic=True`). New gate constant `CHANNEL_OPEN_THRESHOLD=0.0` in `dungeon_channel.py` opens the
  channel cryptic at tier 0 (resolves §6; `INTIMACY_THRESHOLD` left for the deprecated flat band).
  Seed (`tools/populate_crucible_dungeon_channel.py`) is idempotent + preserves play progress.
- **Post-S10 fixes** (`27be4f9`): faithful systems-status prompt; dungeon memories written `approved`.

### Phase 51.5 — locked decisions (D1–D8)

D1 objectives-only intimacy (chat no longer ticks; tiers latch) · D2 first-class `Objective` model
(also seeds Phase 52 Milestones) · D3 full 3–4-tier Crucible ladder · D4 deterministic completion
keyed to world state, engine-evaluated after each command (no event bus) · D5 the objective service
is the single intimacy-tick source · D6 the `dungeon_intimacy` clock is a latching tier index · D7
per-tier `reveals_knowledge` (flat `reveal_knowledge` kept deprecated for back-compat) · D8 stays
Phase 51.5 on `phase-51`; 51 + 51.5 merge to `main` together once built.

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks,
> consequences, and narration. The human player controls the player side: one or more
> player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is
advisory. It may narrate, frame choices, interpret tone, and propose structured world
reactions. It must not directly mutate authoritative state. *(Phase 51.5 #2 Part B will add a
narrowly-constrained exception: the DM may propose resolving an obstacle, but only to its
authored resolved state — see START HERE.)*

---

## Known Failures

**None.** Full unit/integration suite green. The previously-flaky generator eval is resolved
(`26e95a3`, 2026-06-23): evals are excluded from the default run (`addopts = "-m 'not eval'"` —
run with `pytest -m eval`), and `test_generator_level_passes_validation` now mirrors production's
3-retry regenerate-with-errors budget instead of asserting one-shot validity.

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Recent completed phases:

| Phase | Summary | Spec |
|---|---|---|
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
- Roadmap for Phases 51–53 (planned): GitHub Projects `ghostpencil/dungeon-daddy` #1, mirrored in
  `IMPLEMENTATION_PHASES_33_ONWARDS.md`. A `spec/PHASE_NN_*.md` is written when each phase starts.
- Phase 53 (Threat Behavior & Monster Reactions, planned): engine-bounded monster reactions, no enemy
  turn; bosses escalate via clock thresholds. Design: `spec/MONSTER_REACTION_DESIGN.md`.
- Reseed-a-save gotchas: `--campaigns-dir` for the saves dir; `PYTHONPATH=.` for the populate scripts;
  close the app first (DuckDB is single-writer). Live saves at
  `C:\Users\ljfan\AppData\Local\DungeonDaddy\saves`.
- Evals: `pytest -m eval` (live API, paid, non-deterministic); baseline `python tools/run_evals.py`.
