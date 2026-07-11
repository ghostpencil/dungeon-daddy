# Tag Taxonomy & Narrator Lookup Tool — Implementation Spec (proposed)

**Status:** Draft 2026-07-04. Decision points **T1–T7** (taxonomy & pre-fetch) and **L1–L7**
(lookup tool). **All of Part 1 is now OWNER-DECIDED: T1–T6 ratified 2026-07-08** (as proposed,
no changes); T7 was already owner-decided 2026-07-04. The tool loop is **agent-owned** (provider
stays pure transport, L3) and retrieval is **two-tier** — deterministic pre-fetch by default, the
tool reserved for topics not scoped by the nouns/lore in the room (T7 + L7). Part 2's L1/L2/L4–L7
remain *proposed* (ratify at Phase B start). **Phase A in progress** (branch
`feat/phase-51.8-tag-hygiene`).

> **⚠ Post-51.7 reference remap (added 2026-07-08).** This spec was drafted **2026-07-04**,
> two days before the **Phase 51.7 PlayView decomposition** (merged 2026-07-06, PR #89) moved the
> play-mode logic out of `views/play_view.py` (2,765 → 1,491 lines) into the `dungeon_daddy/play/`
> package (five coordinators + `PlaySessionController`). **Every `views/play_view.py:NNNN` reference
> below is pre-refactor and stale.** The verified current locations (2026-07-08):
>
> | Spec reference (2026-07-04) | Current location |
> |---|---|
> | `play_view.py:1517` — 2nd `MemoryRetriever.query()` caller (§1.3, §5.2) | **`play/dialogue.py:250`** — `DialogueCoordinator.recent_memories()` |
> | `play_view.py:2206` — `_spawn_dm_thread` (§9, §10 L5) | **`play/narration.py:246`** — `NarrationCoordinator.spawn_dm_thread` |
> | `play_view.py:1442-1457` — voice worker (§10 L5) | **`play/narration.py`** `spawn()` + `play/dialogue.py` |
> | `play_view.py:2171-2204` — bundle build on main thread (§10 L5) | **`play/narration.py:205`** `build_context_bundle`, called *before* the thread launches → the "bundle built on the main thread" premise **still holds** |
> | `play_view.py:1909` — `_run_proposal_pipeline` (§11) | **`play/actions.py:582`** — `ActionOrchestrator.run_proposal_pipeline` |
>
> **The rest of the spec is unaffected:** `memory/context_bundle.py`, `memory/retrieval.py`,
> `memory/repository.py`, `rpg/models.py`, `rpg/seed_pack.py`, `tools/seed_rpg_state.py`, the
> `populate_crucible_*` scripts, `llm/provider.py`, and `llm/agents/*` were **not** touched by 51.7
> — their line numbers below are still approximately correct. In particular T7's pre-fetch (§5, the
> highest-value Phase A slice) lives entirely in `ContextBundleBuilder`
> (`memory/context_bundle.py`), which the refactor never touched. Net effect: **Phase A is
> essentially unaffected; Phase B's agent/threading wiring (§10 L5) now targets the
> `NarrationCoordinator`/`DialogueCoordinator` ports — a cleaner, DI-friendly seam than the old
> inline `play_view` thread sites.**

Two features, **strictly sequenced**: Part 1 (tag hygiene) is a hard prerequisite for Part 2
(the narrator lookup tool). A lookup tool built on today's tag data would query a mostly-empty,
mutually-incompatible tag space (§1).

**Relationship to other specs:** independent of `spec/WORLD_REACTION_POLICY.md` (which can ship
first — its ambient rule deliberately ignores tags). Extends the taxonomy in
`spec/RPG_MEMORY_DATA_MODEL.md` §Tag-taxonomy from memories-only to all world entities.
Preserves `docs/LLM_AUTHORITY_BOUNDARY.md` (the lookup tool is read-only — §8).

---

## 1. Motivation — the tag audit (2026-07-04)

An audit of tag usage across models, migrations, seeds, and retrieval found the word "tag"
covering **four unrelated concepts**, and most of the pipeline broken at write- or read-time:

1. **Actor tags are silently dropped at seed time.** Every richly-tagged NPC/PC in the seed
   JSON lands in DuckDB with `[]`: both seed paths call `save_actor(...)` without the tags
   argument (`rpg/seed_pack.py:140`, `tools/seed_rpg_state.py:418,429` →
   `memory/repository.py:156` defaults `'[]'`). The dungeon-voice prompt's "Tags:" line
   (`llm/agents/dungeon_voice_agent.py:85-86`) is therefore always blank for seeded actors.
2. **Three spellings of the actor namespace.** Spec taxonomy says `actor:pc:mara`
   (`RPG_MEMORY_DATA_MODEL.md`); Crucible/Tomb seeds use `actor:protagonist:kira-dawnseeker`
   and `actor:dungeon:golem-a7`; the default seeder emits two-segment `actor:protagonist`
   (`tools/seed_rpg_state.py:125-131`).
3. **Tag-based retrieval is never exercised in production.** Both production callers invoke
   `MemoryRetriever.query()` with **no arguments** (`memory/context_bundle.py:54`,
   `play/dialogue.py:250` — `recent_memories()`, ex-`play_view.py:1517`) — retrieval is
   importance-only in practice. When `query()` *is*
   given filters it builds two-part `actor:{id}` / `location:{slug}` (`memory/retrieval.py:22-24`),
   which cannot match the seeds' three-part tags. The retrieval tests assert the spec form
   (`actor:pc:mara`) that no seed uses — tests validate a taxonomy nobody seeds.
4. **Dead and mis-wired seed vocabularies.** `SeedActor.threat_tags` is read nowhere
   (`rpg/seed_pack.py:51` only). `SeedRoomThreat.trigger_tags` (`"noise"`, `"touch_artifact"`)
   are written into clock `action_tags` (`seed_pack.py:181`) where they can never match an
   action verb — those clocks silently never advance. The two seed paths also disagree
   (`seed_rpg_state.seed_campaign_with_pack` ignores `room_threats` entirely).
5. **World entities are untagged.** `RoomObject`, `Item`, `Objective` have no tags field at
   all (`rpg/models.py:187,250,289`; migrations `008`/`009`/`018` have no tags column) —
   memories are heavily tagged, the world they describe is not.
6. **No text search exists.** No `LIKE`/`ILIKE`/FTS anywhere in the persistence layer; the
   spec's "flattened search text" (`MEMORY_SYSTEM_SPEC.md`) was never implemented. The only
   text search is a Python substring filter in the debug inspector
   (`views/memory_inspector_panel.py:67`).
7. **Room-ID references are inconsistent** in seed data (`"R1"`, `"r01"`, `"r1"`, `"r04"` for
   scope/location references — mixed case and zero-padding).

---

# PART 1 — TAG HYGIENE

## 2. One taxonomy, all entities

**T1 (ratified 2026-07-08): a single namespaced, colon-delimited controlled vocabulary applies to the
descriptive `tags` field of every entity** — memories, actors, factions, objects, items,
objectives, and clocks. Bare un-namespaced tags (`"fighter"`, `"boss"`) are invalid.

**T2 (ratified 2026-07-08): canonical namespace families** (extends `RPG_MEMORY_DATA_MODEL.md`):

| Family | Form | Notes |
|---|---|---|
| `actor:` | `actor:pc:<slug>` · `actor:npc:<slug>` · `actor:dungeon:<slug>` | `pc`/`npc` per spec; **`dungeon` ratified** (already seeded) for the dungeon persona |
| `location:` | `location:<room_id>` | room_id must exist in the dungeon model (§4) |
| `level:` | `level:<level_id>` | |
| `theme:` | `theme:<slug>` | |
| `thread:` | `thread:<slug>` | |
| `clock:` | `clock:<clock_slug>` | **ratified** — already in seeds, absent from spec |
| `object:` | `object:<object_slug>` | new — world objects |
| `item:` | `item:<item_slug>` | new |
| `faction:` | `faction:<slug>` | new |
| `objective:` | `objective:<slug>` | new |
| `trait:` | `trait:<slug>` | new — replaces bare descriptive tags (`trait:boss`, `trait:construct`, `trait:veteran`) |
| `fallout:` / `track:` / `emotion:` | per existing spec | unchanged |

**T3 (ratified 2026-07-08): validation at write time.** A `validate_tag(tag: str) -> str` helper
(`memory/tags.py`, new) checks namespace membership and shape; repo save paths call it.
Unknown namespaces raise on save in dev/seed paths; on *read*, unknown tags are passed
through (old saves must still load).

**T4 (locked by nature): `ClockState.action_tags` is NOT part of this taxonomy.** It is a
verb gate consumed by the world-reaction engine, slated for retirement outside the ambient
tier by `spec/WORLD_REACTION_POLICY.md`. This spec does not touch it beyond the seed fix (§4).

**T5 (ratified 2026-07-08): kill the dead vocabularies.** Delete `SeedActor.threat_tags` (never read);
stop writing `trigger_tags` into clock `action_tags` (`seed_pack.py:181`) — instead convert
them to descriptive `trait:` tags on the threat's clock. Aligns with WORLD_REACTION_POLICY §10.5.

**T6 (ratified 2026-07-08): memory-tag normalization migration** (`020_tag_taxonomy.sql` + a Python data
pass for slug resolution):

| Old form | New form |
|---|---|
| `actor:protagonist:<slug>` | `actor:pc:<slug>` |
| `actor:protagonist` (two-segment) | `actor:pc:<protagonist-slug>` resolved per campaign; if unresolvable, keep + log |
| `actor:dungeon:<slug>` | unchanged (ratified) |
| `clock:<slug>` | unchanged (ratified) |
| bare tags on actors/factions | `trait:<slug>` |

## 3. Schema & model changes

- **Migration `020_tag_taxonomy.sql`:** add `tags TEXT DEFAULT '[]'` to `room_objects`,
  `items`, `objectives`. (`actors`/`factions` already have the column — migrations `011`/`007`.)
- **Models:** add `tags: list[str] = []` to `RoomObject`, `Item`, `Objective`
  (`rpg/models.py`), matching the existing `ActorState.tags`/`FactionState.tags` shape.
- **Repo:** thread `tags` through the save/get methods for objects, items, objectives
  (`memory/repository.py`), mirroring the faction pattern (`repository.py:906`).

## 4. Seed-path and seed-data fixes

1. **Fix the actor-tags drop:** `apply_seed_pack` (`rpg/seed_pack.py:140`) and both
   `seed_rpg_state` call sites (`:418,429`) pass `tags=` through to `save_actor`.
2. **Normalize seed JSONs** (`seed_data/**/rpg_seed.json`): actor tags → `trait:`/`level:`
   forms; memory tags → T6 canonical forms.
3. **Room-ID validation:** seed-time check that every `scope_room_id` / `location_slug`
   exactly matches a `Room.room_id` in the dungeon model — fail loudly on `r1`-vs-`R1`
   mismatches instead of silently never scoping.
4. **Tag the Crucible world:** the populate scripts (`tools/populate_crucible_level1.py`,
   `tools/populate_crucible_dungeon_channel.py`) assign taxonomy tags to every object, item,
   and objective (e.g. the Coolant Loop Manifold: `object:coolant-loop-manifold`,
   `theme:the-machine-remembers`, `thread:restore-the-power-core`, `level:level-1`).
   Idempotent, preserves play progress (same discipline as the 51.5 seeds).

## 5. Make retrieval actually use tags

1. **Fix tag construction:** `MemoryRetriever.query` builds actor tags from the actor record
   (`actor_type` → `pc|npc|dungeon` middle segment) instead of two-part `actor:{id}`
   (`memory/retrieval.py:22-24`).
2. **Pass filters in production:** `context_bundle._fetch_memories` and
   `play/dialogue.py:250` (`recent_memories()`, ex-`play_view.py:1517`) pass current-room
   `location:` and present-actor `actor:` tags, keeping
   the existing importance-pinning and budget trim. **Behavior change** — bundle contents
   shift from importance-only to relevance-filtered; needs its own slice + integration test.
3. **Align the tests** with the canonical taxonomy (they currently assert `actor:pc:mara`
   against seeds that never produce it — after T6 the spec form is real).

**T7 (OWNER-DECIDED 2026-07-04): deterministic related-lore pre-fetch is the DEFAULT path.**
The context bundle gains a tag-driven expansion step, engine-side, zero LLM plumbing:

1. Collect the scene's anchor entities: room objects/items/exits, present actors, the active
   objective (the same nouns `build_room_noun_context` already assembles,
   `memory/context_bundle.py:194-253`).
2. Union their tags; retrieve memories/lore sharing those tags via the (now-fixed)
   `MemoryRetriever.query(tags=...)` — ranked by tag-hit count, then importance, then recency.
3. Append under a distinct bundle section (`# Related Lore`) with its own sub-budget
   (~400 of the 2000 bundle tokens; importance-pinning and trim discipline unchanged), and
   record counts in bundle `provenance` like existing sections.

This covers the in-scene case deterministically and testably — the lookup tool (Part 2) is
*only* for what pre-fetch cannot see (§6). Pre-fetch ships in Phase A; it is valuable even
if Part 2 never ships.

---

# PART 2 — NARRATOR LOOKUP TOOL

## 6. Concept — two-tier retrieval (OWNER-DECIDED 2026-07-04)

Retrieval for the narrator agents (`DungeonMasterAgent`, `DungeonVoiceAgent`) is **two-tier**:

| Tier | Mechanism | Covers | Cost |
|---|---|---|---|
| **Default: pre-fetch** (T7) | Engine-side, deterministic tag expansion into the bundle's `# Related Lore` section | Everything scoped by the nouns/lore **in the room**: objects, items, present actors, active objective, and memories tagged to them | Zero latency, zero LLM plumbing, fully testable |
| **Escalation: `lookup_world` tool** | Model-initiated mid-turn read-only DuckDB search by name/id/**tags** | Only topics **not scoped by the room's nouns/lore**: an off-scene NPC the player mentions, distant lore, a past event no in-room tag reaches | One extra model round; agent-owned loop (§9) |

The scoping rule is the contract: **if pre-fetch could have surfaced it, the tool must not be
called for it.** The tool exists precisely for references that no in-room tag can reach —
player-introduced topics, cross-level lore, entities elsewhere in the dungeon. Enforcement is
prompt-first with soft telemetry enforcement (L7, §10).

Tags are the hook in both tiers — they link memories to the world entities they describe,
which is exactly what Part 1 makes true.

This *complements* the World Reaction Policy: that spec narrows what the LLM may **decide**;
this one widens what it may **know**. Same doctrine — the engine decides, the LLM narrates,
now with better recall.

## 7. The tool

**L1 (proposed): one tool, `lookup_world`.**

```json
{
  "name": "lookup_world",
  "description": "Search this campaign's world database. ONLY for entities, places, or past events NOT covered by your context (current room contents, present actors, Related Lore). Never look up something already in your context. Returns matching entities and memories with their tags.",
  "parameters": {
    "query":        "optional substring, matched case-insensitively against names and slugs",
    "tags":         "optional list of canonical tags (OR semantics); e.g. ['actor:npc:mira-coldwell', 'theme:guilt']",
    "entity_types": "optional filter: actor|object|item|clock|objective|faction|memory|room",
    "limit":        "max results, default 8, cap 20"
  }
}
```

At least one of `query`/`tags` is required. Results are compact JSON rows:
`{entity_type, id, slug, display_name, room_id, tags, snippet}` — `snippet` is the
description/summary truncated to ~200 chars. Deterministic ranking: exact slug match >
tag-hit count > (memories only) importance DESC, created_at DESC. Total tool-result budget
~1,200 tokens; overflow rows dropped with a `"+N more"` marker.

**L2 (proposed): backend = one new repo method**, `MemoryRepository.search_entities(
campaign_id, query=None, tags=None, entity_types=None, limit=8)` — `ILIKE '%q%'` over
`slug`/`display_name` (first `LIKE` in the codebase; DuckDB supports `ILIKE` natively) union'd
across the entity tables, plus exact tag membership (JSON-list `tags` columns and the
`memory_tags` join table). A thin `LookupService` wraps it and formats tool results;
`MemoryRetriever` stays untouched.

## 7.1 Rooms as a first-class campaign entity (OWNER-DECIDED 2026-07-11)

Rooms were the one scene anchor **not** in the campaign DuckDB — authored only in the dungeon
JSON (`data.models.Room`, via `DungeonRepository`), reachable at retrieval time only indirectly
(memories tagged `location:<room_id>`). Every other noun (object/item/actor/clock/objective/
faction) is a first-class, taggable, searchable DuckDB row. To let `lookup_world` and the T7
pre-fetch treat rooms symmetrically — and to give a room's authored setting lore / quest role a
home — Slice B0 adds a **`rooms` table** to the campaign DB.

**Design (owner decisions 2026-07-11):**
- **Runtime projection, not a move.** The table is seeded from the dungeon + campaign seed like
  every other entity. Geometry/layout (`x/y/w/h`, loop roles, graph notes) **stays in the dungeon
  JSON** — the map renderer + layout system remain its readers; the `rooms` table does not
  duplicate it. It holds only the campaign-facing, searchable fields.
- **Columns** (mirroring the `actors`/`objectives` conventions): `room_id` (grid id — `R1`,
  `r01`, …), `campaign_id`, `level_id`, `slug`, `display_name`, `room_type`, `summary`
  (inline setting-lore text for fast retrieval), `quest_role` (the room's role in the quest),
  `markdown_path` + `checksum` (pointer to the full authored lore body with front matter, mirroring
  `memory_entries`), `tags` (JSON, namespaced taxonomy).
- **Lore lives in both places:** a short `summary` column for inline/quick lookup **and** a
  `markdown_path`/`checksum` to the full body — same split as `memory_entries`.
- **Quest role in both places:** an authoritative `quest_role` column **and** namespaced tags
  (`quest:*`/`thread:*`) so the role also drives tag retrieval (column = truth, tags = reach).
- **Quest role sourcing (OWNER-DECIDED 2026-07-11): hybrid.** The seed path *derives* the default
  `quest_role` from the dungeon room's `main_loop_role` (`entry`/`goal`/`obstacle`/`clue`/`bypass`/…),
  and an authored per-room override wins. Rationale: the literal "derive from objectives" has no data
  source — `Loop.objective_room_ids` is empty in every shipped dungeon and RPG `Objective` entities carry
  no room link, whereas `main_loop_role` *is* the room's authored role in the quest layout. Rooms lacking
  it (e.g. the tomb sample) get `None`. In practice the derived roles were kept for the Crucible (already
  meaningful); the populate scripts author only lore `tags`.
- **Seed-path reach (Slice B0, implemented 2026-07-11):** the projection runs in `apply_seed_pack(levels=)`,
  `seed_campaign_with_pack` (when `dungeon.json` present), **and** the app's new-game `seed_from_manifest`
  (already passed the dungeon). New campaigns get rooms on first load via `backfill.py` (same seam as exits);
  a reseed respects skip/`force` and never clobbers populate-authored `tags`/`quest_role`. Crucible lore tags
  are enriched by the populate scripts through the shared `enrich_room_tags` helper.
- Model `RoomState` (`rpg/models.py`, beside `ActorState`/`FactionState`/`ClockState`); repo
  `save_room`/`get_rooms`/`get_room`; migration `022_rooms.sql` (bare SQL, no `--` comments — the
  runner splits on `;`) with the standard migration tests (applies-on-prev-head, idempotent-from-
  scratch, back-compat reads).
- **Connections** stay in the existing `room_exits` table (migration `010`; already first-class
  with gating). No tags / no memory-retrieval — a room's *traversal* graph is not thematic lore.
  Add read helpers (`get_exits_by_room` already exists) only if `lookup_world` needs to surface
  them.

## 8. Authority boundary — why this is clean

`docs/LLM_AUTHORITY_BOUNDARY.md` restricts **mutation** only: every prohibition is a write
(advance clocks, apply stress, mutate DuckDB, call repo *write* methods). Reads are already
how the LLM is fed. The boundary's tool policy ("tools must produce proposals only, must not
commit state") governs *mutating* tools; a lookup returns **data, not proposals**, and sits
below that policy. **Hard rule: the tool executor is read-only** — it holds a `LookupService`
that exposes no write method, and the LLM never sees SQL. Add a short "Read tools" note to
`docs/LLM_AUTHORITY_BOUNDARY.md` codifying this when the phase lands.

## 9. Provider extension (the real capability gap)

There is **no tool-use plumbing anywhere today**: `LLMProvider` (`llm/provider.py:22`) is
`complete`/`stream` only; no `tools=` param, no `tool_calls` parsing, no request→tool→request
loop (repo-wide grep: zero hits). Every LLM call is single-shot.

**L3 (OWNER-DECIDED 2026-07-04): the tool loop is AGENT-OWNED — the provider stays pure
transport.** The provider never executes app code; it gains one new method that sends tools
and returns *either* text or tool-call requests. The loop (execute → append result →
resubmit) lives in the agent layer, written once as a shared helper.

**Provider-neutral types** (`llm/provider.py` — pinned here so both providers translate from
one shape):

```python
@dataclass
class LLMToolDef:
    name: str
    description: str
    parameters: dict          # JSON Schema; providers translate to their native format

@dataclass
class LLMToolCall:
    call_id: str
    name: str
    arguments: dict

@dataclass
class LLMRoundResult:
    text: str | None          # set when the model answered
    tool_calls: list[LLMToolCall]   # non-empty when the model wants tools run
```

`LLMMessage` gains two optional fields for the loop's message history: role `"tool"` with
`tool_call_id: str | None` (a tool result), and `tool_calls: list[LLMToolCall] | None` on
assistant messages. Providers translate both directions (OpenAI: `tools=` /
`response.tool_calls` / `role="tool"`; Anthropic later: `input_schema` / `tool_use` /
`tool_result`).

**New protocol method** (keeping `complete`/`stream` untouched — existing agents unaffected):

```python
def complete_round(
    self,
    messages: list[LLMMessage],
    system: str = "",
    tools: list[LLMToolDef] | None = None,
    max_tokens: int = 1024,
) -> LLMRoundResult: ...
```

**Shared loop helper** (`llm/tool_loop.py`, agent-layer code — not on the provider):

```python
def run_tool_loop(provider, messages, system, tools,
                  executor: Callable[[LLMToolCall], str],
                  max_rounds: int = 2, max_tokens: int = 1024) -> str
```

Calls `complete_round`; on `tool_calls`, runs `executor` per call, appends the results,
resubmits; on the last round resubmits **without** `tools` to force a plain answer. Agents
call `run_tool_loop`; no agent reimplements the loop.

- Capability detection: `getattr(provider, "supports_tools", False)` property — agents fall
  back to plain `complete()` when absent. DI is preserved: agents receive the provider *and*
  the executor injected; they never construct either.
- **L4 (proposed): budgets.** `max_rounds=2`, per-call row cap (§7), tool errors are
  returned to the model as an error string (never raise through the turn); if the loop
  exhausts rounds the model must answer with what it has.

## 10. Agent & threading integration

- `DungeonMasterAgent.respond(...)` and `DungeonVoiceAgent.respond(...)` gain an optional
  `lookup` seam: when the provider `supports_tools` and an executor is injected, call
  `run_tool_loop(...)`; else exactly today's `complete` path. System prompts get a short
  "when to look things up" section restating the §6 contract: *only* for topics not covered
  by the room's nouns or the `# Related Lore` section (an off-scene NPC the player names,
  distant lore, a past event outside the room's tag reach) — never for anything already in
  context.
- The context bundle (now including T7's pre-fetched `# Related Lore`) stays primary — the
  tool is the escalation path for what pre-fetch cannot see, not a replacement for the
  bundle. Bundle budget (2000 tokens) unchanged.
- **L7 (proposed): scoping enforcement.** Prompt-first (the §6 contract in the tool
  description and system prompt), backed by two mechanical layers:
  1. *Soft (telemetry):* the executor compares each lookup's hits against the entity ids
     already in the bundle; overlapping lookups are logged as `redundant_lookup` in the L6
     provenance so prompt drift is visible and tunable.
  2. *Redirect (cheap hard-stop):* when **every** hit of a lookup was already in the bundle,
     the executor returns `"Already in your context — do not look this up again."` instead of
     rows, ending the round without burning the budget on duplicates.
  No hard pre-filter on the query itself — the model may legitimately search a tag that
  *partially* overlaps the scene; only full-overlap results are redirected.
- **L5 (proposed): threading.** The whole request→tool→request cycle runs inside the existing
  per-view daemon worker thread (`NarrationCoordinator.spawn_dm_thread`, `play/narration.py:246`;
  the generic voice worker via `NarrationCoordinator.spawn()` + `play/dialogue.py`). Tool queries
  execute DuckDB **reads from that worker thread** — today's convention builds the bundle on the
  main thread (`build_context_bundle` runs synchronously in `spawn_dm_thread` *before* the thread
  launches, `play/narration.py:205,264`), so this is
  new. Approach: the shared connection is guarded by a `threading.Lock` owned by
  `MemoryRepository`, and tool queries go through `conn.cursor()` under that lock. (A second
  `read_only=True` connection is NOT assumed safe while the app holds the write connection —
  verify in a spike before choosing it.)
- **L6 (proposed): observability.** Every tool call is logged (query, tags, hit count) and
  surfaced in the transcript debug panel the way proposal provenance already is — so a bad
  narration can be traced to what the model looked up (mirrors `MEMORY_SYSTEM_SPEC.md`
  provenance discipline).

## 11. Non-goals

- **No write tools, ever** — proposals stay on the existing propose→validate→apply pipeline
  (`ActionOrchestrator.run_proposal_pipeline`, `play/actions.py:582`, ex-`play_view.py:1909`).
- No vector/semantic search, no embeddings — exact tags + ILIKE substring only.
- No LLM-visible SQL; no cross-campaign search.
- No DuckDB FTS extension in v1 (revisit if ILIKE+tags proves insufficient).
- No tool use in the generator/design-side agents (out of scope).

## 12. Phasing & slices (TDD per `spec/TESTING.md`; use the TDD skill)

> **Post-51.7 correction (2026-07-08):** slice targets below reflect the current `play/` package
> (see the remap banner at the top). Two former `play_view.py` sites are now coordinator methods:
> A5's second retrieval caller is `DialogueCoordinator.recent_memories()` (`play/dialogue.py:250`),
> and B4's agent/threading wiring targets `NarrationCoordinator`/`DialogueCoordinator` ports.

**Slice 0 — cleanup warm-up** (carry-in from the deferred PR #89 review; sequenced first because
it directly serves Phase A's retrieval slices):
- Extract `ActiveCampaign(repo, campaign_id)` value / `PlaySessionContext.active_campaign()`
  accessor to collapse the 15+ hand-copied `(mem_repo, campaign_id)` co-presence guards
  (`play/dialogue.py:243-246 recent_memories`, `play/actions.py:597-599 run_proposal_pipeline`,
  `play/narration.py:213 build_context_bundle`, `reaction_applier`, `navigation`, `controller`).
  A5/A6 add more retrieval sites; landing the accessor first means they consume it clean.
- Narrow the two broad `except Exception` catches in `play/actions.py` (`run_chat_action`,
  `on_resolve_action`) to post a GM-visible system line instead of only logging.

**Phase A — Tag Hygiene** (no LLM changes, independently valuable):
1. `validate_tag` + namespace vocabulary (`memory/tags.py`) — pure unit slice.
2. Migration `020` + model/repo `tags` for objects/items/objectives.
3. Seed-path fixes (actor-tags drop, `threat_tags`/`trigger_tags` removal, room-ID validation).
4. Seed-data normalization + Crucible world tagging (idempotent populate-script updates).
5. Retrieval: canonical tag construction (`memory/retrieval.py`) + **both** production callers pass
   filters — `context_bundle._fetch_memories` (`context_bundle.py:54`) **and**
   `DialogueCoordinator.recent_memories()` (`play/dialogue.py:250`, ex-`play_view.py:1517`).
   Behavior change — own slice + integration test on bundle contents; realign the retrieval tests
   to the canonical taxonomy.
6. **T7 pre-fetch:** the `# Related Lore` bundle section (anchor-entity tag union → memory
   retrieval → sub-budget + provenance) in `ContextBundleBuilder` (`memory/context_bundle.py`,
   untouched by 51.7) — deterministic, integration-tested on bundle output.

**Phase B — Narrator Lookup Tool** (requires A):
0. **Rooms as a first-class campaign entity (owner-directed 2026-07-11; see §7.1).** New `rooms`
   table + `RoomState` model + `save_room`/`get_rooms`/`get_room` (migration `022_rooms.sql` with the
   standard migration tests). Seed path plants a room record per dungeon room. Prereq for room
   lookups in slice 1. Connections stay in the existing `room_exits` table (no tags).
1. `MemoryRepository.search_entities` + `LookupService` (unit + roundtrip tests, fake data) —
   unions the DuckDB entity tables **incl. `rooms`** (B0), so `entity_type="room"` needs no
   cross-repo seam.
2. Provider transport: `LLMToolDef`/`LLMToolCall`/`LLMRoundResult`, `complete_round` on the
   protocol + `OpenAIProvider` translation (unit-test with a `FakeProvider` scripting
   `tool_calls`; no live API in the default suite).
3. `run_tool_loop` helper (`llm/tool_loop.py`) — loop, round budget, error-as-string,
   final forced-plain round (pure unit slice with `FakeProvider`).
4. Agent integration (scoped prompts, L7 redirect/telemetry) + worker-thread lock story +
   observability panel line — the `lookup` executor injects through the
   `NarrationCoordinator`/`DialogueCoordinator` ports (`play/narration.py spawn_dm_thread`/`spawn`,
   `play/dialogue.py`), **not** raw `play_view` methods; the worker thread these coordinators
   already own is the single seam the DuckDB-read lock guards.
5. Optional `pytest -m eval`: one live eval that an *out-of-scene* lore question triggers a
   lookup and lands the fact in the narration — and that an in-room question does **not**.

Ordering vs. World Reaction Policy: WRP first (fixes a live bug, no dependency on tags),
then A, then B. A and WRP touch different engine surfaces and could run in either order if
scheduling prefers.

## 13. Decision summary (owner to confirm)

| # | Decision | Proposed |
|---|---|---|
| T1 | One namespaced taxonomy for all entities' descriptive tags | **OWNER-DECIDED 2026-07-08** |
| T2 | Namespace families incl. ratifying `actor:dungeon:`/`clock:`, new `object:`/`item:`/`faction:`/`objective:`/`trait:` | **OWNER-DECIDED 2026-07-08** |
| T3 | `validate_tag` at write time; permissive on read | **OWNER-DECIDED 2026-07-08** |
| T4 | `action_tags` stays outside the taxonomy (dies with WRP) | **OWNER-DECIDED 2026-07-08** |
| T5 | Delete `threat_tags`; stop `trigger_tags`→`action_tags`; convert to `trait:` | **OWNER-DECIDED 2026-07-08** |
| T6 | Normalization migration mapping (protagonist→pc etc.) | **OWNER-DECIDED 2026-07-08** |
| T7 | Deterministic `# Related Lore` pre-fetch is the default retrieval path | **OWNER-DECIDED 2026-07-04** |
| L1 | Single `lookup_world` tool, name+tags+types params, out-of-scene mandate only | **OWNER-DECIDED 2026-07-11** |
| L2 | One repo method `search_entities` (ILIKE + exact tags) behind `LookupService` | **OWNER-DECIDED 2026-07-11** |
| L3 | Agent-owned loop: provider = transport (`complete_round` + neutral types), loop in `llm/tool_loop.py` | **OWNER-DECIDED 2026-07-04** |
| L4 | Budgets: 2 tool rounds, 8-row default, ~1.2k-token results, errors-as-strings | **OWNER-DECIDED 2026-07-11** |
| L5 | Tool loop + DuckDB reads on the worker thread behind a repo-owned lock (shared conn + `threading.Lock`; read-only 2nd conn not pursued) | **OWNER-DECIDED 2026-07-11** |
| L6 | Log + debug-panel provenance for every lookup | **OWNER-DECIDED 2026-07-11** |
| L7 | Scoping enforcement: prompt contract + redundant-lookup telemetry + full-overlap redirect (no hard pre-filter) | **OWNER-DECIDED 2026-07-11** |
