# Dungeon Daddy — Project Index

## Phase

Phase: Stabilization — Post-Phase 45 polish (in progress)
Status: **STABILIZATION** — branch `stabilization-post-45`; 6 cleanup items; Phase 46 starts after merge.

Previous: Phase 45 complete (2026-06-14). 2436 tests passing.
Next: Phase 46 — Inventory System (PENDING, `spec/PHASE_46_*.md` to be written when stabilization merges)

**Last session (2026-06-17) — #63 complete; 5 stabilization items remain.**
- **#63 DONE** — Removed hardcoded `Protagonist` PC actor from `_CampaignSeedSpec` in `tools/seed_rpg_state.py`. Generic `seed_campaign()` path now emits a warning directing users to `--seed-pack`. Tests updated (25 passing). Committed on `stabilization-post-45`.
- 5 open items remaining (all `Todo` on project board):
  - #64 Design mode: handle no-dungeon-loaded state gracefully
  - #65 Add confirmation dialog before deleting a save game
  - #66 Play mode: prompt to save session on navigate away to Library
  - #67 Library: show last-played date on Save cards
  - #68 Add 'Extract as Seed' action to Saves in Library
- Next: #64 (Design mode no-dungeon state).

**Prior session (2026-06-17) — stabilization branch + GitHub issue promotion.**
- Created branch `stabilization-post-45`.
- Promoted 6 post-Phase-45 draft cards to real GitHub issues (#63–#68) with `stabilization` label; deleted the original drafts from the project board.

**Prior session (2026-06-17) — added Phase 53 + sequencing review.** All design/docs only, no
code:
- **New Phase 53 — Threat Behavior & Monster Reactions.** Full design in
  `spec/MONSTER_REACTION_DESIGN.md`; draft card on GitHub Project #1; roadmap table extended to
  46–53 in `IMPLEMENTATION_PHASES_33_ONWARDS.md`; spec-loading row added to `CLAUDE.md`.
  Decisions: monsters never roll; engine bounds the eligible reaction set + all magnitudes, LLM
  selects one by `reaction_id` and narrates; depth-by-rank (standard = Model A instinct+tiers,
  elite/boss = Model B + clock-threshold boss phases); activates the inert `npc_reaction`
  channel. Hard deps all done (P34/35/36) — kept last as a soft "after Phase 50".
- **Sequencing review of 46–53.** Ordering is topologically valid — no phase precedes a hard
  dep, no renumbering needed. Recorded as the "Phase Dependencies & Sequencing (46–53)" matrix
  in `IMPLEMENTATION_PHASES_33_ONWARDS.md` (spine = `46→47→48→50`, `46→49→50`, `49→52`; 51 + 53
  are flexible pull-on-demand depth phases).

**Prior session (2026-06-17) — Phases 46–52 design review.** Logical coherence, Arcade
feasibility, design gaps. Sequencing sound; fits the architecture; no Arcade blockers.
Resolutions folded into the GitHub draft-issue bodies + the spec mirror
(`IMPLEMENTATION_PHASES_33_ONWARDS.md` → "Key design resolutions (2026-06-17 review)").
Three blocking resolutions to honour when building:
- **Player Commands vs LLM proposals** — new `rpg/command.py` (engine-authoritative) for
  move/pick-up/equip/activate/fulfil-milestone; the proposal union stays LLM-advisory only.
- **Adverbs → dice-pool deltas + side-effect flags** (no position/effect axis exists).
- **Recedable intimacy clock** — add signed `tick_clock` + `monotonic: bool = True` on
  `ClockState` (existing clocks default `monotonic=True`, unchanged).
No code changed yet; implementation begins when Phase 46 is defined.

---

### Phase 45 — Campaign Pipeline (COMPLETE)
Spec: `spec/PHASE_45_CAMPAIGN_PIPELINE.md`
Branch: `phase-45-campaign-pipeline`

Three on-disk libraries (`dungeons/`, `campaign_seeds/`, `saves/`); publish pipeline
(Design → attach seed → publish → Play); Library home screen as startup/hub; one-time
migration of existing `campaigns/*`; post-phase removal of top-level menu bar (4-pill
navigation: Library / Design / Campaign / Play). 9 TDD slices, 2436 tests passing.

---

### Phase 44 — Playtest Telemetry and Balance Reports (COMPLETE)
Spec: `spec/PHASE_44_PLAYTEST_TELEMETRY.md`
Branch: `phase-44-playtest-telemetry` (merged into main 2026-06-13)

New `dungeon_daddy/reporting/` module with Pydantic models, aggregation queries, and
`build_report()`. Two new domain events: `proposal.applied` and `proposal.rejected`. CLI
tool `tools/playtest_report.py` prints formatted balance reports. 6 TDD slices, 33 new
tests. Post-phase stabilization: removed Grid/Tiles map modes, renamed Graph → Map,
repositioned RPG/Edit-Memory buttons to title bar, pruned low-value tests. 2393 tests.

---

### Phase 43 — Faction System (COMPLETE)
Spec: `spec/PHASE_42_ADDITION_FACTION_SYSTEM.md`
Branch: `phase-43-faction-system` (merged into main 2026-06-13)

New `FactionManifest` model (replaces `ActorManifest` for factions); named reputation
tiers (hostile/cold/neutral/warm/allied); `FactionState` persisted in DuckDB;
`AdjustReputationChange` in LLM proposal system; faction reputations included in
`ContextBundle`; faction-specific Campaign UI edit form and list cards. 7 TDD slices.

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks,
> consequences, and narration. The human player controls the player side: one or more
> player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is
advisory. It may narrate, frame choices, interpret tone, and propose structured world
reactions. It must not directly mutate authoritative state.

---

## Known Failures

None (test suite passes — 2436 tests as of 2026-06-14).

---

## Previous Phases

Phase 42 and earlier are complete. Full history in `spec/HISTORY.md`.

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Roadmap for Phases 46–53 (planned): GitHub Projects `ghostpencil/dungeon-daddy` #1, mirrored in the "Planned Roadmap — Phases 46–53" section of `IMPLEMENTATION_PHASES_33_ONWARDS.md`. Next: Phase 46 (Inventory). Issue bodies hold the per-phase detail and (as of 2026-06-17) the folded-in design resolutions; a detailed `spec/PHASE_46_*.md` is written when Phase 46 starts.
- Phase 53 (Threat Behavior & Monster Reactions, planned 2026-06-17): instinct-driven, engine-bounded monster reactions with no enemy turn; bosses escalate via clock thresholds. Full design in `spec/MONSTER_REACTION_DESIGN.md`; summary in `IMPLEMENTATION_PHASES_33_ONWARDS.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
- `protagonist` actor is defined in `seed_data/campaigns/the-crucible/rpg_seed.json` (use `--seed-pack` + `--force` to reset stress tracks); the generic `seed_campaign()` path no longer creates a placeholder actor.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates and seeds cleanly; 2 memory seeds).
- `tools/seed_rpg_state.py`: `actor_type="faction"` entries routed to `repo.save_faction()`; faction clock `owner_actor_id` cleared.
- Live campaigns migrated (2026-06-13): `The Crucible` — `desert-djinn-fragment` moved from `actors` to `factions` table.
- Playtest reports: `python -m tools.playtest_report <db_path> <campaign_id>` (requires `PYTHONPATH=.`).
- `proposal.applied` / `proposal.rejected` events now emitted; call sites must insert `result.rejection_events` into repo with correct `campaign_id` after `validate_proposal()`.
