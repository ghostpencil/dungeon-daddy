# Dungeon Daddy — Project Index

## Phase

Phase **50 — Hybrid Action Model: COMPLETE & merged to `main`** (2026-06-23).
PR **#79** merged (`2d4ed79`); branch deleted; issue **#80** closed; roadmap board → Done.
Visual-verified on screen (VNA dropdowns, verb→noun filtering, hybrid exit labels, lock glyph,
compass orientation). Full suite green; evals excluded from the default run.

**Next session → Phase 50.5 (Use Noun on Noun)** — spec written
(`spec/PHASE_50_5_USE_ON_GRAMMAR.md`), implementation not started. See below.

Specs: current/future phases in `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (index:
`spec/IMPLEMENTATION_PHASES.md`). Phase 50 spec: `spec/PHASE_50_HYBRID_ACTION_MODEL.md`.

**Contracts Phase 50.5 reuses (Phase 48, still locked):**
- `MoveParty(exit_id, how)` is a **Player Command** in `rpg/command.py` (not a proposal).
- **No `party_location` column** — session uses `current_room_id` / `visited_rooms` /
  `current_level_idx` (`data/models.py:195-197`); the engine is their sole writer.
- No LLM proposal may set those session fields or exit `status` (except approval-gated `BlockExit`).
- `how?`/adverb = modifier flags (dice-pool deltas + world-side-effect flags; no position/effect axis).
- **Phase 49 background:** signature adverbs derived live from `playbook_slug` (not persisted);
  `actor_abilities` (migration `011`) is the live, mutable set the action providers read.

---

## START HERE next session — Phase 50.5 (planned): "Use Noun on Noun" transitive grammar

> A **dynamic add-on to Phase 50** (grew out of Phase 50 visual verify), numbered 50.5 to mark
> that it was **not** in the original roadmap and has **no GitHub issue**. Distinct from the
> roadmap's **Phase 51 ("Talk to the Dungeon")**, which remains its own future phase.
> Full design memory: `project_phase50_5_use_on_grammar.md`. Spec **written**:
> `spec/PHASE_50_5_USE_ON_GRAMMAR.md` (9-slice TDD plan). Implementation **not started.**

**Plan approved 2026-06-23. Spec + 9-slice TDD plan are authoritative in
`spec/PHASE_50_5_USE_ON_GRAMMAR.md`** — read it, not this section, for the full design (thesis,
the 3 locked decisions, the per-slice contracts, and the 4 open questions). Don't re-derive
here. Grammar extends to `Verb · Noun · [Target] · Adverb`; most behavior already exists at the
engine layer (key→door, use-item→object, `GiveItem`) so the phase is mostly UI wiring + a few
commands/validators + one model flag. **Unblocked — Phase 50 is closed.**

**▶ Next action (fresh context): Slice 1 — optional Target on the grammar.** Read
`spec/TESTING.md`, invoke the TDD skill, then: add `target_id: str | None = None` to
`ActionCard` (`rpg/action_options.py:100`); mark which verbs are transitive; extend
`validate_card` to require a Target for transitive verbs and reject one for intransitive verbs.
Pure model/validation — no UI, no DB. Then proceed down the slice plan in the spec.

**Two Phase 50 carry-outs that 50.5 absorbs** (decisions, not bugs): `activate` verb not wired
(Slice 5 adds trigger selection; today `_on_vna_submit` posts a "not wired yet" message); and
push-yourself/momentum controls are absent from the VNA surface (**out of scope** here per the
spec's non-goals unless a slice needs them).

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

**None.** Full unit/integration suite green. The previously-flaky generator eval is resolved
(`26e95a3`, 2026-06-23): evals are excluded from the default run (`addopts = "-m 'not eval'"` —
run with `pytest -m eval`), and `test_generator_level_passes_validation` now mirrors production's
3-retry regenerate-with-errors budget instead of asserting one-shot validity.

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Recent completed phases:

| Phase | Summary | Spec |
|---|---|---|
| 50 — Hybrid Action Model | Verb·Noun·Adverb action *Card* (input-dual of a proposal); `ActionCard` + `validate_card`; `resolve_card`/`resolve_card_roll` (`rpg/action_resolution.py`); `VnaActionPanel` wired into PlayView (retired `how_chips`); hybrid exit labels via 8-point layout-coord compass (`rpg/exit_labels.py`) | `spec/PHASE_50_HYBRID_ACTION_MODEL.md` (issue #80) |
| 49 — Starting Playbooks | `Playbook` + nested models + `PlaybookLibrary`; `data/playbooks.json` (4 bundled playbooks, kit ability + first pool ability granted at start); `actor_abilities` table + repo CRUD; seed-publish wiring (ratings/tracks/kit/tags/abilities); playbook picker in Seed editor; Character Sheet panel playbook/adverbs/abilities sections | `spec/PHASE_49_STARTING_PLAYBOOKS.md` (issue #77) |
| 48 — Dungeon Navigation | `RoomExit` model + `room_exits` schema; `MoveParty` command; exit-condition validator; level transitions; `DiscoverExit`/`UnlockExit`/`SealExit`/`BlockExit`; room context bundle; Play-mode exit-list panel + fog-of-war map; party-presence gate on `PickUpItem`/`ActivateObject` | `spec/PHASE_48_DUNGEON_NAVIGATION.md` |
| 47 — Room Contents | Items in rooms + interactive objects (state-machine archetypes); `ActivateObject`/`PickUpItem`/`DropItem` commands; `current_room` context block; Campaign Seed editor UI | `spec/PHASE_47_ROOM_CONTENTS.md` |
| 46 — Inventory System | `Item`/`ItemFeature` models; class-kit/dungeon/gear commands; `compute_effective_ratings`; `mark_level_items_inert`; world-reaction item proposals; Character Sheet UI | issue #71 |
| 45 — Campaign Pipeline | Three on-disk libraries; publish pipeline; Library home screen; 4-pill navigation | `spec/PHASE_45_CAMPAIGN_PIPELINE.md` |

Per-session implementation logs are in git history and the auto-memory (`project_phase_status.md`).

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: current/future in `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`; index at `spec/IMPLEMENTATION_PHASES.md`. Spec-loading rules and skills: `CLAUDE.md` (canonical).
- Roadmap for Phases 51–53 (planned): GitHub Projects `ghostpencil/dungeon-daddy` #1, mirrored in `IMPLEMENTATION_PHASES_33_ONWARDS.md`. Issue bodies hold per-phase detail; a `spec/PHASE_NN_*.md` is written when each phase starts. (Phase 50.5 is **not** on the roadmap and has no issue.)
- Phase 53 (Threat Behavior & Monster Reactions, planned): engine-bounded monster reactions, no enemy turn; bosses escalate via clock thresholds. Design: `spec/MONSTER_REACTION_DESIGN.md`.
- Evals: `pytest -m eval` (live API, paid, non-deterministic); baseline tooling `python tools/run_evals.py` (count-based comparison).
- Playtest reports: `python -m tools.playtest_report <db_path> <campaign_id>` (requires `PYTHONPATH=.`).
- Exit backfill (pre-Phase-48 campaigns): `python -m tools.backfill_room_exits ["<save dir>"] [--dry-run] [--force]`. Close the app first (DuckDB is single-writer). Saves live under `%LOCALAPPDATA%\DungeonDaddy\saves\<name>\`.
- UI icons: `dungeon_daddy/assets/ui/icons/` (white/transparent PNG + SVG source); attribution in `CREDITS.json`. Fetch new ones with the `game-icon-finder` skill.
- `protagonist` actor: `seed_data/campaigns/the-crucible/rpg_seed.json` (use `--seed-pack` + `--force` to reset). Generic `seed_campaign()` no longer creates a placeholder actor.
- Crucible Level 1 content: `tools/populate_crucible_level1.py` (re-run 2026-06-23) — idempotent upserts of 11 objects, 7 loose items, 4 monsters, 1 NPC into the live save (`%LOCALAPPDATA%\DungeonDaddy\saves\The Crucible\campaign.duckdb`; close app first). Every object/item carries a `description`; Notice Board (R2) holds the sharpened Brakkus key clue. Puzzle chain R1 journal → R2 lift-warden-key → R3 lift-fuse → R4 Great Lift. The R2→R4 lift exit's `requires_item_slug` is **not** set, so the key/door gate is inert until Phase 50.5 sets it.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates + seeds cleanly).
- `proposal.applied` / `proposal.rejected` events: call sites must insert `result.rejection_events` into repo with the correct `campaign_id` after `validate_proposal()`.
