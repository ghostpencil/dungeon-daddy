# Dungeon Daddy — Project Index

## Phase

Phase **50 / 50.5 / 50.6 — COMPLETE & merged to `main`** (Hybrid Action Model · Use-Noun-on-Noun
grammar · Chat Action Cockpit). Detail in git history + Phase History table below.

Phase **51 — Talk to the Dungeon: FEATURE-COMPLETE & GUI-verified** on branch `phase-51` (live
dungeon-voice channel, intimacy clock, `DungeonVoiceAgent`, persona persistence, resonance points).
Spec `spec/PHASE_51_TALK_TO_THE_DUNGEON.md`.

Phase **51.5 — Dungeon Objectives & Intimacy Tiers: IN PROGRESS** on branch `phase-51` (extends 51;
**no merge to `main` until 51.5 is built** — owner decision). Spec `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md`,
decisions locked D1–D8 (below). Built & GUI-verified so far:
- **Slices 1–10 DONE & GUI-verified** — the full intimacy ladder (objectives → latching intimacy tier
  index → per-tier knowledge), seeded into the live Crucible. Condensed architecture below.
- **Puzzle-obstacle / multi-approach feature (#1+#2), Part A (Slices 1–4) DONE & committed + GUI-verified**
  — a class-flavored approach roll resolves an obstacle and completes its objective; the builder suggests
  the obstacle's approach verbs; the 4 Crucible obstacles author thematic contested approaches; both seeds
  reseed additively.
- **Container-loot feature + builder hit-test fix DONE, committed (`11e7eb6`) & GUI-verified**; live
  Crucible reseeded + new-game-reset (state below).
- **Part B (LLM authority expansion, Slices 5–7) IN PROGRESS** — **Slices 5–6 DONE & committed**
  (`8daece5`, `0665058`). **Next: Slice 7 (docs-only).** See START HERE.

Specs: 51.5 `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md` · 51 `spec/PHASE_51_TALK_TO_THE_DUNGEON.md` ·
current/future `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (index `spec/IMPLEMENTATION_PHASES.md`).

---

## START HERE — next session: Part B Slice 7 (docs-only)

**Part B = the DM-ruling authority expansion**: let the DM rule that an *off-script but plausibly-
described* action resolves an obstacle — the one narrowly-constrained exception to "the LLM never mutates
object state." It may push an obstacle only to its **authored** resolved state. **Build is done (Slices
5–6); only docs remain.**

### Done — Slice 5 (`8daece5`)
Constrained `ResolveObstacleChange` proposal type (`rpg/proposal.py`: `kind="resolve_obstacle"`,
`object_slug`, `to_state`, `reason`) + validator gate (`rpg/proposal_validator.py`): new optional
`obstacle_resolved_states: dict[slug→authored_state]` param; rejects unknown-obstacle refs and any
`to_state` ≠ the obstacle's authored resolved state (LLM can't invent states). Tests
`test_proposal_obstacle.py` (+4).

### Done — Slice 6 (`0665058`): wired into `play_view`'s proposal pipeline
`_run_proposal_pipeline` builds the obstacle-state map via new `_obstacle_resolved_states(campaign_id)`
(current room's `RoomObject`s → `{slug: obstacle_resolved_state(obj)}`, skip `None`) and passes it to
`validate_proposal`. Accepted `ResolveObstacleChange`s are applied by new `_apply_obstacle_proposals(...)`
through the deterministic `ActivateObject` seam (`_apply_vna_command`) — *not* `apply_low_risk_proposals`
(which correctly skips the kind) — so side-effects fire and `_advance_objectives()` re-runs. Gated on a
resolving outcome via new `rpg/obstacles.is_resolving_outcome`; `rpg/obstacles.resolving_trigger` maps the
LLM-named resolved state back to a converging transition's trigger. Tests
`test_play_view_obstacle_proposal.py` (+3, drive the real pipeline, mock only the LLM agent). Full unit
suite green (3195).

### Next — Slice 7 (docs)
Update `docs/LLM_AUTHORITY_BOUNDARY.md` + `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md` to record the
constrained object-state authority (the DM may resolve an obstacle, but only to its authored state).

### The feature (decisions locked)

- **#2 — multiple ways to solve an objective (Hybrid).** A room object's `current_state` changes via the
  deterministic `activate` verb; Part A added class-flavored **contested approaches** (Artificer *tinker*,
  Fighter *fight*, Thief *finesse*). Part B adds the LLM-ruled path for *any plausibly-described action*.
- **#1 — normalize completion (all paths → one COMPLETED objective).** An obstacle is a `RoomObject` in a
  "blocked" state with **multiple contested transitions converging on one canonical resolved state** (e.g.
  `gearworks: jammed ──{tinker|fight|endure}──▶ cleared`). The objective completes when the object reaches
  that state — `completion_satisfied`/`advance_objectives` are agnostic to *how* it changed.
- **Outcome→success mapping — LOCKED (owner, 2026-06-29):** full/critical → resolves; **partial → resolves
  with a complication**; miss → fails. Encoded in `rpg/obstacles.py` (`_RESOLVING_OUTCOMES`).

### The seam (Part A wired here; Slice 6 reuses it)

`play_view._resolve_vna_roll` calls `_maybe_resolve_obstacle(card, actor, resolution.outcome)`: on a
resolving roll whose verb matches a contested approach, it routes the matched transition through the
deterministic `ActivateObject` pipeline (`_apply_vna_command`), which applies `update_object_state` +
side-effects and re-runs `_advance_objectives()`. Pure decision logic lives in `rpg/obstacles.py`
(`obstacle_approaches`, `obstacle_approach_verbs`, `obstacle_resolved_state`, `resolve_obstacle_with_roll`).

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
reactions. It must not directly mutate authoritative state. *(Phase 51.5 Part B adds one
narrowly-constrained exception, gate built in Slice 5: the DM may propose resolving an obstacle,
but only to its authored resolved state — see START HERE.)*

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
- World Reaction Policy (design settled, **unscheduled** — new feature, do NOT fold into 51.5): per-object
  `reaction_policy` (`scripted`/`ambient`/`inert`) to replace the blunt "miss = every tagged clock +2"
  fan-out. Fixes a real bug (a STUDY-miss on the R1 statue moved 3 campaign clocks incl. the
  `dungeon_intimacy` clock, violating D5's single-source rule). Owner decisions locked 2026-07-01.
  Design: `spec/WORLD_REACTION_POLICY.md` (supersedes the miss behavior in
  `spec/PHASE_35_WORLD_REACTION_SERVICE.md`).
- Reseed-a-save gotchas: `--campaigns-dir` for the saves dir; `PYTHONPATH=.` for the populate scripts;
  close the app first (DuckDB is single-writer).
- New-game reset (dev/playtest): `python -m tools.reset_crucible_new_game` reverts play progress on the
  live Crucible (party→R1/L1, clocks→0, ladder→initial, objects→seed state, stress→0, items reseated,
  memories/events wiped) while keeping the authored campaign + dungeon persona docs. Auto-backs up
  `campaign.duckdb` + `session.json` first; close the app first.
- Evals: `pytest -m eval` (live API, paid, non-deterministic); baseline `python tools/run_evals.py`.
