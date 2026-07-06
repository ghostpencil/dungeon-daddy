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

Phase **51.7 — PlayView Decomposition: BUILD, started 2026-07-05** on
`feat/phase-51.7-playview-decomp`. Incremental seam extraction of `views/play_view.py`
(2,765 lines / ~110 methods / 7 responsibility clusters) into a new `dungeon_daddy/play/`
package (`PlaySessionContext` + Action/Navigation/Dialogue/Memory/Narration coordinators;
`PlaySessionController` composition root last). Folds in the two PR #88 deferred review items:
Slice 1 fixes the non-atomic world-reaction write; the WRP "all three call sites" spec language
is corrected (owner ruling 2026-07-05, `spec/WORLD_REACTION_POLICY.md` §7). Spec + slice plan:
`spec/PHASE_51_7_PLAYVIEW_DECOMPOSITION.md`.

Specs: 51.6 `spec/PHASE_51_6_WORLD_REACTION_POLICY.md` · 51.5 `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md` ·
51 `spec/PHASE_51_TALK_TO_THE_DUNGEON.md` · current/future `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`
(index `spec/IMPLEMENTATION_PHASES.md`).

---

## START HERE — Phase 51.7 PlayView Decomposition in BUILD

**PR #88 merged to `main` 2026-07-05 (`c0e1cba`) — Phase 51.6 fully closed.** Current work:
**Phase 51.7 — PlayView Decomposition** on `feat/phase-51.7-playview-decomp` — spec + slice plan
in `spec/PHASE_51_7_PLAYVIEW_DECOMPOSITION.md`. Both PR #88 deferred review items are resolved
or scheduled: the spec-language item is **closed** (owner ruled 2026-07-05: only noun-carrying
paths pass `acted_object`; `spec/WORLD_REACTION_POLICY.md` §7 amended), and the non-atomic
`_apply_world_reaction` write is **Slice 1** of 51.7. Next slice to build: **Slice 0 —
`PlaySessionContext`**. After 51.7: Tag Hygiene → Narrator Lookup remains the sequenced choice
(item 2 below).

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
