# Dungeon Daddy — Project Index

## Phase

**STABILIZATION / cleanup.** All feature phases through **51.8** are complete and merged to `main`. The
owner-decided cleanup slice (2026-07-17) is underway on branch `chore/cleanup-51-8-hardening`:
**items 1–5 are DONE** (commit `09af3b8`, same day — see START HERE); items 6–11 plus the deferred pile
remain. Phase 52 (Milestone Advancement) and Phase 53 (Monster Reactions) stay deferred behind the cleanup.

Recently merged (newest first — full detail in the Phase History table + each `spec/PHASE_*.md`, and git):

- **51.8 Phase B — Narrator Lookup Tool** (PR #92, merge `13e14f2`, 2026-07-17). Read-only `lookup_world`
  LLM tool so the narrator can answer about entities/places/events **not** in its scene context: `rooms`
  as a first-class entity (migration `022`), `search_entities` + `LookupService`, provider `complete_round`
  transport, agent-owned `run_tool_loop`, both agent + coordinator seams, DBG-tab provenance, live eval.
  A 5-agent whole-arc review before merge found + fixed one CRITICAL L7-redirect bug and 5 more batches
  (see START HERE). Spec `spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md`.
- **51.8 Phase A — Tag Hygiene** (PR #90, `6c899cc`, 2026-07-11). Namespaced tag taxonomy (`memory/tags.py`,
  migrations `020`/`021`), seed + Crucible-world tagging, tag-based scene-scoped retrieval, the `# Related
  Lore` pre-fetch. Same spec.
- **51.7 — PlayView Decomposition** (PR #89, `5eadaaa`, 2026-07-06). `views/play_view.py` 2,765 → 1,491
  lines; logic extracted into `dungeon_daddy/play/` (`PlaySessionContext` + Action/Navigation/Dialogue/
  Memory/Narration coordinators + `PlaySessionController`). Spec `spec/PHASE_51_7_PLAYVIEW_DECOMPOSITION.md`.
- **51.6 — World Reaction Policy** (PR #88, `c0e1cba`, 2026-07-05; also the mypy 348→0 sweep). Per-object
  `reaction_policy` (`scripted`/`ambient`/`inert`) + `ClockCategory` firewall replace the "miss = every
  tagged clock +2" fan-out. Spec `spec/PHASE_51_6_WORLD_REACTION_POLICY.md` (design `spec/WORLD_REACTION_POLICY.md`).
- **51 + 51.5 — Talk to the Dungeon / Dungeon Objectives & Intimacy Tiers** (PR #83, 2026-07-04). Specs
  `spec/PHASE_51_TALK_TO_THE_DUNGEON.md`, `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md`.

---

## START HERE — Cleanup Slice (OWNER-DECIDED 2026-07-17)

The deferred pile grew big enough across Phases A + B to justify a slice of its own. Work happens on
`chore/cleanup-51-8-hardening` (branched off `main` 2026-07-17). **Next slice up: items 6–11 below**
(confirm scope with the owner; the list is a menu, not a mandate).

**✅ DONE — items 1–5 (commit `09af3b8`, 2026-07-17, TDD + code-reviewed):**
1. ~~`LookupService` → search-only Protocol ctor~~ — ctor now takes the public, runtime-checkable
   `EntitySearch` Protocol (`memory/lookup.py`); §8 "read-only by construction" is compiler-enforced.
2. ~~Split `ToolCapableProvider`~~ — done as a **standalone** runtime-checkable Protocol
   (`supports_tools` + `complete_round`), not `(LLMProvider, Protocol)` inheritance: it is exactly the
   seam `run_tool_loop` needs, and the existing agent-test fakes (no `stream`/`last_usage`) satisfy it.
   `AnthropicProvider` gained `last_usage → None` and satisfies base `LLMProvider` again (pinned by
   isinstance contract tests). Agents + `ObservingProvider` share one `provider_supports_tools` TypeGuard.
3. ~~`TypedDict` for the `search_entities` row~~ — `EntityRow` (`memory/models.py`) + `LookupResult`
   envelope (`memory/lookup.py`), threaded through all 3 readers; shape pinned by one test.
4. ~~Tool-name dispatch in `run_tool_loop`~~ — unknown names never reach the executor; error tool-result
   + warning log; per-call-id result message still emitted.
5. ~~Telemetry `try/finally`~~ — failed `complete`/`complete_round` calls now write a record. The slice
   review CONFIRMED and fixed two bugs in the naive version: failed calls record **zeroed** tokens
   (inner `last_usage` is stale on failure; recording it double-counted the prior call in
   `tools/llm_cost_report.py`), and a telemetry write error is swallowed+logged on the failure path so it
   cannot mask the in-flight `LLMError`.

**Deferred from the items 1–5 slice review (2026-07-17):**
- **`ObservingProvider.stream` failure telemetry** — still records only on successful exhaustion; a
  mid-stream raise leaves no record (same class of gap item 5 fixed for the other two methods; needs a
  decision on how to treat partially-yielded streams).
- **tools→executor dispatch map in `run_tool_loop`** — the name gate stops hallucinated names, but all
  known tools still route to the single `executor`; when a second real tool ships, replace the callable
  with a `{name: executor}` mapping so cross-tool misroutes become impossible.
- **`_Lookup` Protocol duplication** (`llm/lookup_tool.py`) — restates `LookupService.lookup`'s full
  signature (deliberate llm→memory layering; revisit only if the layering rule changes), and `_fail`
  hand-builds the `{results, omitted, error}` envelope instead of using `LookupResult`.

**Remaining cleanup backlog (from the Phase B whole-arc review):**
6. **Wrap the B5 eval fixture in `ObservingProvider`** — it builds a bare `OpenAIProvider`, but production
   wires `ObservingProvider(OpenAIProvider(...))`; wrapping the fixture drives the true production stack for ~free.
7. **`bundle_entity_ids` gaps** — omits the party's own actor + inventory ids (a PC lookup is never flagged
   redundant), and it's pinned against a hand-written dict, not a real `ContextBundleBuilder` output (rename
   a key in `build_room_noun_context` and L7 dies silently, suite green).
8. **`campaign_id` fallback divergence** — `narration.py`'s `campaign_id or state.dungeon_id` vs
   `dialogue.py`'s `active_campaign()` disagree about a missing id; neither pinned; the narration path would
   run `WHERE campaign_id = NULL` → 0 hits, no error.
9. **Rooms-seed raise takes exit backfill down with it** — `_seed_rooms` runs before `_seed_exits` in
   `seed_from_manifest`, wrapped in `backfill_exits_if_empty`'s swallow → a save loads with zero exits + one
   log line. Untested.
10. **`field_validator("tags")` on `RoomState`** — the only model in `rpg/models.py` with no validator;
    wiring the existing `validate_tag` makes the taxonomy invariant unbypassable.
11. **Test-seam tightenings** — `test_dialogue_lookup.py` tests a private method where narration drives the
    public seam; `_set_debug_bundle` (`controller.py:519`) has the latent `__new__` fragility B4e fixed in
    its sibling; `seeder.py`/`seed_rpg_state.py` duplicate the ~15-line skip/force block (lift to a helper).

**Design question surfaced (owner-facing, not pure cleanup — flag before touching):**
- **The DM `lookup_world` path is model-driven only.** There is **no free-form DM chat in regular rooms**
  (owner design); the Play input is the Action sentence, and free conversation only happens via the **dungeon
  voice in special rooms**. So the DM lookup fires autonomously during **action-outcome narration**, never
  from a player question — and the player-driven voice path never had the L7 bug (its overlap set is
  memory-ids only). Net: the L7 fix is correct but has **no clean player-driven GUI surface**. Worth an owner
  decision on whether the DM lookup path should be surfaced/prompted at all, or left as model-discretion
  narration enrichment.

**From the Phase A deferred pile + earlier:**
- `_collect_anchor_tags` (`memory/context_bundle.py`) still does **not** read the `rooms` table, so a room's
  own `tags`/`quest_role` don't drive the T7 `# Related Lore` pre-fetch (B0 groundwork with no consumer yet).
- `views/play_view.py`'s `lookup_section_lines()` render line stays **unpinned** (A6 precedent) — the natural
  time to pin both DBG render lines is whenever the DBG tab gets UI-harness coverage.
- Phase A items: room-id gate self-disable logging (`seed_rpg_state.py` when `dungeon.json` absent); a shared
  `field_validator("tags")` across Item/RoomObject/Objective/ClockState; the engine write→read round-trip
  integration test (**Gap A** — write via `record_dungeon_exchange`/`advance_objectives`/`discover_exit`,
  read back through `ContextBundleBuilder`, assert resurfacing); LOW items (co-referenced-clock `trigger_tags`
  last-writer-wins; DBG panel hides found-then-fully-trimmed lore; `seed_pack.py` docstring imprecision).
- **Optional tag-hygiene data pass** (live-data, not code): old saves' gameplay memories carry pre-taxonomy
  **bare tags** (`knowledge`, `arcane`, …) that don't participate in scene-scoped retrieval; a `normalize_tag`
  pass over existing `memory_tags` would fold them into the canonical vocabulary.

*The Phase B whole-arc review (2026-07-15, 5 agents) that produced items 1–11 is recorded in git — commit
`5dcb849` (fixes) and PR #92's body. The CRITICAL find was the L7 redirect: `bundle_entity_ids` treated the
whole `ContextBundle` as the model's context while `build_prompt` rendered only a subset, so a lookup for a
monster standing in the room came back "already in your context" with nothing behind it. Fixed by rendering
the missing sections; pinned by `test_every_bundle_entity_id_is_described_in_the_system_prompt`. Merged on
the test evidence — the L7 fix has no clean player-driven GUI surface (see the design question above).*

---

### Live Crucible save — facts for any future verify

- Save at `C:\Users\ljfan\AppData\Local\DungeonDaddy\saves\The Crucible`; campaign id `campaign:the-crucible`;
  party at **R1 (Receiving Hall)**; Scorpion Swarm present. **19 rooms** present (11 lore-tagged), **8 approved
  memories** — verified by direct DB inspection 2026-07-15. No reseed needed for `lookup_world`.
- **Three levels, distinct room-ids by case/padding:** L1 `R1`–`R5`, L2 `r01`–`r06`, L3 `r1`–`r8`. `r1` (L3
  Control Nexus) ≠ `R1` (L1 entrance). Populate scripts cover L1–L2 only; L3 is base-seed. Reviewers keep
  false-flagging L3 `r1`/`r7`/`r8` seed refs as typos — verify against `tests/fixtures/crucible.json` first.
- **The app runs `gpt-4o`** (`window.py::_DEFAULT_OPENAI_MODEL`, override `DUNGEON_DADDY_MODEL`), wiring
  `ObservingProvider(OpenAIProvider(...))` — the same model the B5 eval runs on, so the tool is genuinely
  live in-app.
- **Reseed / new-game reset gotchas:** `--campaigns-dir` for the saves dir; `PYTHONPATH=.` for the populate
  scripts; **close the app first** (DuckDB is single-writer). `python -m tools.reset_crucible_new_game`
  reverts play progress (party→R1/L1, clocks→0, ladder→initial, objects→seed, stress→0, items reseated,
  memories/events wiped) while keeping authored campaign + persona docs; auto-backs up `campaign.duckdb` +
  `session.json`. An **existing** save that already has exits skips `backfill`, so rooms/exits added by a
  later phase need a manual reseed on live saves.

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** the RPG engine and memory layer are authoritative; the LLM is advisory. It may
narrate, frame choices, interpret tone, and propose structured world reactions — it must not directly mutate
authoritative state. Two narrowly-constrained, validator-gated exceptions exist, both in
`docs/LLM_AUTHORITY_BOUNDARY.md`: (1) Phase 51.5 Part B — the DM may propose resolving an obstacle, but only
to its **authored** resolved state; (2) the Phase 51.8 read-tools note — a read tool (`lookup_world`) returns
**data, not proposals** and is read-only by construction.

```text
The LLM may propose. The engine disposes.
```

---

## Known Failures

**None.** Full unit/integration suite green (**3861 passed**, 8 eval deselected; ruff + mypy(strict, 172)
clean as of cleanup items 1–5, `09af3b8`). Evals are excluded from the default run (`addopts = "-m 'not eval'"`;
run with `pytest -m eval` — live API, paid, non-deterministic).

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Full 33–51.5 phase write-ups: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`.
Recent completed phases:

| Phase | Summary | Spec / PR |
|---|---|---|
| 51.8 B — Narrator Lookup Tool | Read-only `lookup_world`: `rooms` first-class entity + migration `022`; `search_entities` + `LookupService`; provider `complete_round` transport (`LLMToolDef`/`LLMToolCall`/`LLMRoundResult`); agent-owned `run_tool_loop`; both agent + coordinator seams; DBG-tab provenance; live eval. Whole-arc review fixed a CRITICAL L7-redirect bug + 5 batches | `spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md` (PR #92, `13e14f2`) |
| 51.8 A — Tag Hygiene | Namespaced tag taxonomy (`memory/tags.py`, `validate_tag`/`normalize_tag`, migrations `020`/`021`); seed + Crucible-world tagging; tag-based scene-scoped retrieval; `# Related Lore` pre-fetch | same spec (PR #90, `6c899cc`) |
| 51.7 — PlayView Decomposition | `views/play_view.py` 2,765→1,491 lines; `dungeon_daddy/play/` package (`PlaySessionContext` + Action/Navigation/Dialogue/Memory/Narration coordinators + `PlaySessionController`) | `spec/PHASE_51_7_PLAYVIEW_DECOMPOSITION.md` (PR #89, `5eadaaa`) |
| 51.6 — World Reaction Policy | Per-object `reaction_policy` (`scripted`/`ambient`/`inert`) + `ObjectReactionBinding` + migration `019`; `ClockCategory` firewall; kills the "miss = every tagged clock +2" fan-out. Also the mypy 348→0 sweep | `spec/PHASE_51_6_WORLD_REACTION_POLICY.md` (PR #88, `c0e1cba`) |
| 51.5 — Dungeon Objectives & Intimacy Tiers | `Objective`/`ObjectiveCompletion` + migration `018`; deterministic `advance_objectives` (single intimacy-tick source, latching tier ladder + per-tier knowledge); puzzle-obstacle Parts A+B (`rpg/obstacles.py`, `ResolveObstacleChange`); container-loot | `spec/PHASE_51_5_DUNGEON_OBJECTIVES.md` (PR #83) |
| 51 — Talk to the Dungeon | Live dungeon-voice channel at resonance points; `DungeonVoiceAgent`; recedable/latching intimacy clock (migrations `016`/`017`); dungeon-persona persistence; ◆ THE CRUCIBLE chat treatment | `spec/PHASE_51_TALK_TO_THE_DUNGEON.md` (PR #83) |
| 50.6 — Chat Action Cockpit | In-chat Action Builder (V·N·T·A slot chips + popups); "Things Here" clickable room overlay; retired the right-panel ACTION + EXITS tabs | `spec/PHASE_50_6_CHAT_ACTION_COCKPIT.md` (PR #82) |
| 50.5 — Use Noun on Noun | Grammar → `Verb · Noun · [Target] · Adverb`; `TRANSITIVE_VERBS`; `CombineItems` + migrations `013`/`014`; `GiveItem` validator; `activate`/`look` wired | `spec/PHASE_50_5_USE_ON_GRAMMAR.md` (PR #81) |
| 50 — Hybrid Action Model | Verb·Noun·Adverb *Card*; `ActionCard` + `validate_card`; `resolve_card`/`resolve_card_roll`; `VnaActionPanel`; hybrid exit labels | `spec/PHASE_50_HYBRID_ACTION_MODEL.md` (issue #80) |
| 49 — Starting Playbooks | `Playbook` + `PlaybookLibrary`; `data/playbooks.json`; `actor_abilities` table + migration `011`; seed-publish wiring; Character Sheet panel | `spec/PHASE_49_STARTING_PLAYBOOKS.md` (issue #77) |
| 48 — Dungeon Navigation | `RoomExit` + `room_exits` (migration `010`); `MoveParty`; level transitions; `Discover/Unlock/Seal/BlockExit`; room context bundle; exit-list panel + fog-of-war map | `spec/PHASE_48_DUNGEON_NAVIGATION.md` |
| 47 — Room Contents | Items + interactive objects (state-machine archetypes, migration `009`); `ActivateObject`/`PickUpItem`/`DropItem`; `current_room` context | `spec/PHASE_47_ROOM_CONTENTS.md` |
| 46 — Inventory System | `Item`/`ItemFeature` (migration `008`); class-kit/dungeon/gear commands; `compute_effective_ratings` | issue #71 |
| 45 — Campaign Pipeline | Three on-disk libraries; publish pipeline; Library home screen | `spec/PHASE_45_CAMPAIGN_PIPELINE.md` |

Per-session implementation logs are in git history and the auto-memory (`project_phase_status.md`).

### Phase 51.5 — locked decisions (D1–D8, still authoritative)

D1 objectives-only intimacy (chat no longer ticks; tiers latch) · D2 first-class `Objective` model (also
seeds Phase 52 Milestones) · D3 full 3–4-tier Crucible ladder · D4 deterministic completion keyed to world
state, engine-evaluated after each command (no event bus) · D5 the objective service is the single
intimacy-tick source · D6 the `dungeon_intimacy` clock is a latching tier index · D7 per-tier
`reveals_knowledge` (flat `reveal_knowledge` kept deprecated) · D8 51 + 51.5 merged to `main` together.

---

## Notes

- **SDLC formalized (2026-07-17):** process in `spec/SDLC.md`; session commands `/plan-phase`,
  `/next-slice`, `/end-slice`, `/end-phase` in `.claude/commands/`; blocking ruff+mypy
  PostToolUse hook in `.claude/settings.json`.
- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: current/future in `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`; index at
  `spec/IMPLEMENTATION_PHASES.md`. Spec-loading rules and skills: `CLAUDE.md` (canonical).
- **Next phases (planned, deferred behind the cleanup slice):** Phase 52 (Milestone Advancement — beats,
  ranks-to-5, `FulfillMilestone`, LLM milestone detection, `actor_beats`) and Phase 53 (Threat Behavior &
  Monster Reactions — engine-bounded, no enemy turn, boss phases via clock thresholds; design
  `spec/MONSTER_REACTION_DESIGN.md`). GitHub Projects #1; a `spec/PHASE_NN_*.md` is written when each starts.
- **WRP live-data gotcha (still relevant):** `apply_seed_pack` writes UUID5 clock ids
  (`rpg.seed_pack.derive_clock_id`), not `campaign.seeder._clock_id`'s `clock:{campaign}:{slug}` string form.
  `world_reaction._find_clock_by_slug` matches **both** — any new code resolving a clock by slug on the
  Crucible must account for the UUID5 convention (else scripted CLOCK bindings silently no-op on real saves).
- **CI does not gate merges.** The `Tests`/`Type-check` workflows run on push-to-`main` / PRs-to-`main`, but
  no branch protection requires them. mypy has a green strict baseline (172 files) — a new error is a genuine
  regression; keep new code strictly typed.
- **Commands:** `python -m dungeon_daddy` (start app); `python tools/arcade_stop.py` (stop a manually-started
  window); `pytest -m eval` for live evals (`python tools/run_evals.py` for the baseline).
