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
**Slices 1–10 DONE & GUI-verified** (the full intimacy ladder is built and seeded into the live
Crucible). Now building the **puzzle-obstacle / multi-approach feature (#1+#2)**: **Part A Slices 1–3
DONE & committed** (engine win — a class-flavored approach roll can resolve an obstacle and complete its
objective; the builder now suggests the obstacle's approach verbs). **Next session: Part A Slice 4**
(re-author + reseed the Crucible obstacles) — plan in START HERE.

Specs: 51.5 `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md` · 51 `spec/PHASE_51_TALK_TO_THE_DUNGEON.md` ·
current/future `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (index `spec/IMPLEMENTATION_PHASES.md`).

---

## START HERE — next session: puzzle-style objective solving, Part A Slice 4

Multi-approach objective solving (#1 + #2) is **in progress**. **Part A Slices 1–3 are DONE & committed**
(`5e3c0d2`, `4c34b16`, + this session): the pure obstacle helpers + the locked outcome mapping are built,
a successful class-flavored approach roll now resolves an obstacle's state and completes its objective,
and the in-chat Action Builder now suggests the selected obstacle's approach verbs (filtered to what the
acting actor can attempt). **Next: Part A Slice 4** (re-author the Crucible obstacles + reseed
**additively**), then Part B (the LLM authority expansion). Full unit suite green (3175).

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
- **Outcome→success mapping — LOCKED (owner, 2026-06-29):** full/critical → resolves; **partial →
  resolves with a complication**; miss → fails.

### The seam (Slices 1–2 wired here)

`play_view._resolve_vna_roll` now calls `_maybe_resolve_obstacle(card, actor, resolution.outcome)`:
on a resolving roll whose verb matches a contested approach, it routes the matched transition through
the deterministic `ActivateObject` pipeline (`_apply_vna_command`), which applies `update_object_state`
+ side-effects and re-runs `_advance_objectives()`. Pure decision logic lives in `rpg/obstacles.py`.
`_on_activate_submit` still routes contested transitions to `_resolve_vna_roll`.

### Slice plan (TDD; sequenced so Part A is a verifiable win on its own)

**Part A — authored class approaches (engine-deterministic, no authority change):**
1. ✅ **DONE** (`5e3c0d2`) Pure helpers + validation in new `rpg/obstacles.py`: `obstacle_approaches`
   (contested transitions out of `current_state`, each tagged `action_verb`) + `obstacle_resolved_state`
   (single shared `to_state`; `None` if not an obstacle; `ValueError` on divergence).
2. ✅ **DONE** (`4c34b16`) Roll path resolves obstacle state: pure `resolve_obstacle_with_roll` +
   `ObstacleRollResolution` (locked mapping); `play_view._maybe_resolve_obstacle` (called from
   `_resolve_vna_roll`) routes the matched transition through the `ActivateObject` pipeline so
   side-effects apply and `_advance_objectives()` re-runs. Tests: `test_play_view_obstacle.py` (3) +
   obstacle units (9).
3. ✅ **DONE** (this session) Surface the obstacle's approach verbs as suggested actions in the builder:
   `obstacle_approach_verbs` (obstacles.py) + `approach_verbs` on each object in `build_room_noun_context`
   (thin view-model — no raw transitions) + `VnaActionPanel.selected_noun_approach_verbs()` +
   `InChatActionBuilder` clickable **TRY** row (approaches ∩ actor's offered verbs; click fills the Verb
   slot, keeps the obstacle noun). Tests: builder (+5), panel (+3), context (+2), obstacles (+2).
4. **← NEXT** Re-author the 4 Crucible obstacles with class-flavored approaches → one resolved state;
   update the seed **additively** (preserve the adopted `gearworks` state — don't reset it to jammed).

**Part B — DM ruling for off-script plausible actions (the authority expansion):**
5. New constrained `ResolveObstacleChange` proposal type — validator permits pushing an obstacle only
   to its **authored** resolved state (the LLM can't invent states); applied on a successful roll.
6. Feed obstacle context into the proposal pipeline so the DM can rule a described action resolves it.
7. Update `docs/LLM_AUTHORITY_BOUNDARY.md` + the Phase 51.5 spec to record the constrained
   object-state authority.

### Session state

- **Prior session (puzzle-obstacle Part A Slices 1–2):** built `rpg/obstacles.py` + the roll-path
  resolution and committed (`5e3c0d2`, `4c34b16`).
- **This session (Part A Slice 3):** surfaced the obstacle's approach verbs as clickable suggested
  actions in the in-chat builder (obstacles helper → context enrichment → panel accessor → builder TRY
  row). Full unit suite green (3175). No GUI verify yet for the new mechanic (Slice 4 reseeds the
  Crucible obstacles first, then verify in-app).
- **Live Crucible state (2026-06-29):** tier 0 `clear-the-gearworks` **completed** (`gearworks`
  cleared); tier 1 `restore-the-coolant-loop` **active** (`coolant-loop` still **ruptured** → needs
  `restored`); tier 2 `recharge-the-arcane-conduits` **locked** but `arcane-conduits` already **charged**
  (banked — **cascade-completes** once tier 1 finishes); tier 3 `stabilize-the-core-containment`
  **locked** (`core-containment` failing). Intimacy clock **1/4 latching**. `great-lift` powered,
  `trap-lever` active. Live save 0 drafts / 18 approved. Backups incl.
  `campaign.duckdb.bak-slice10-applied-*` / `…-lift-demote-*`.
- **Slices 1–10 GUI-verify (DONE, prior session):** owner confirmed "Fixes verified. The Dungeon
  dialogue is accurate." — truthful systems status (vs live DB), dungeon names its want, lift modeled as
  one object, no memory review queue (`apply_low_risk_proposals` writes `approved`), dungeon states
  object/objective locations. Commits `ee27a72` / `e042dfd` / `69e4303` (and `27be4f9`).

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
- **Post-S10 fixes (2026-06-29):** Great Lift modeled as one object — L2 `great-lift-upper` demoted to
  `lore_fixture` so the lift reports once (`ee27a72`); `apply_low_risk_proposals` writes `approved` so
  no AI memory hits a review queue (`e042dfd`); dungeon-voice context carries subsystem + objective
  **locations** (`located_systems_status`/`object_location`, agent + prompt + `play_view._room_labels`
  / `next_objective_location`) so it can say where the task is and answer "which room is X" (`69e4303`).

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
