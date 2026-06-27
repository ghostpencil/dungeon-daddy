# Phase 51.5 — Dungeon Objectives & Intimacy Tiers

**Status:** ✅ **SPEC FINALIZED — all decisions locked (2026-06-27). Ready to implement.** Branch
`phase-51` (extension of Phase 51, no merge to `main` until this is built — owner decision
2026-06-27).
**Type:** BUILD (Phase 51 extension; sibling-foundation to Phase 52 Milestone Advancement).
**Depends on:** Phase 51 (Talk to the Dungeon — the live dungeon-voice channel, intimacy clock,
`DungeonVoiceAgent`, persona persistence, resonance points). All of that is DONE & GUI-verified.
**One-liner:** *Ground the dungeon channel in deterministic state — a tiered intimacy ladder where
completing in-engine objectives (restoring dungeon subsystems) unlocks knowledge, and the dungeon
reacts to who is speaking.*

> **Authority boundary (unchanged, non-negotiable):** the dungeon-voice LLM still only narrates. It
> reads grounded facts (systems status, who is speaking, the current objective hint) but **never**
> completes objectives, ticks the intimacy clock, mutates subsystem state, or writes authoritative
> memory. The **engine** completes objectives and ticks intimacy deterministically; the LLM just
> talks about it.

---

## 1. Problem / Opportunity (from the 2026-06-27 playtest)

The Phase 51 channel is live and the *dialogue* is good, but it's **hollow** — the dungeon has no
concrete facts to talk about, so the conversation isn't useful. Three concrete gaps surfaced:

1. **No grounded state.** Asking the (robotic forge-mind) dungeon for a "systems assessment" gets
   improvisation, not facts — there is no model of the Crucible's subsystems or their status.
2. **No character awareness.** The dungeon can't react to *who* is speaking — the agent is fed only
   `actor.slug` (`"kira"`), never the playbook. An Artificer addressing a machine-dungeon should
   matter, and it can't.
3. **No objectives / no progression hook.** The dungeon kept demanding "authorization" with no way
   to provide it, because there's nothing behind it. Intimacy advances `+1` per chat exchange
   ("talk enough → unlock") rather than by *achieving* something. There are no quests, secrets, or
   objectives keyed to intimacy levels.

The opportunity (owner's design thesis, 2026-06-27): **gate intimacy on completing deterministic
in-engine objectives**, give each intimacy tier authored knowledge/secrets, and let the dungeon
*react to the speaker* and *tell the player what it wants next*. "Restoration of a subsystem unlocks
the next intimacy level" — deterministic, engine-driven, inside the authority boundary.

## 2. Goal

> Standing at a resonance point, the player talks to the dungeon. The dungeon **knows who is
> speaking** (reacts to the Artificer), can give a **truthful systems assessment** of its own
> subsystems, and **dangles a concrete objective** ("restore the coolant loop and I will grant you
> the next authorization"). The player completes that objective in the deterministic game engine
> (restores the subsystem); the **engine** advances intimacy one tier; the dungeon now reveals the
> next tier's knowledge/secrets and names the next objective. Intimacy is a **ladder climbed by
> doing**, not by chatting.

---

## 3. Decisions

All decisions **locked** with the product owner 2026-06-27 — D1–D3 chosen directly, D4–D8 proposed by
the implementer and signed off.

| # | Decision | Resolution | Status |
|---|---|---|---|
| **D1** | **Intimacy progression model** | **Objectives only; tiers latch.** Intimacy advances *only* when an objective completes. Chat no longer ticks intimacy. Once a tier is earned it is permanent (no receding). | 🔒 locked |
| **D2** | **Objective modeling** | **First-class `Objective` model** (new Pydantic type + DuckDB table + service) — *not* a thin reuse of `RoomObject`. Designed to also serve as the foundation for Phase 52 (Milestone Advancement). | 🔒 locked |
| **D3** | **Crucible content scope** | **Full ladder** — author 3–4 tiers end-to-end (3–4 subsystems to restore, knowledge/secrets per tier, the Artificer hook) so the design is playable and evaluable. | 🔒 locked |
| **D4** | **What completes an objective** | An objective's completion condition is **deterministic and keyed to existing world state**, primarily a **subsystem `RoomObject` reaching a target state** (e.g. `restored`). The engine **evaluates by querying world state** after each command resolution (matches the existing hard-wired-orchestration pattern; no new event bus). Subsystems are the *thing you fix*; objectives are the *tracked goal*. | 🔒 locked |
| **D5** | **Single source of truth for the intimacy tick** | The **objective service** ticks the intimacy clock on completion — **not** the object transition's `advances_clock_slug` (which stays available for other clocks). Avoids double-counting. | 🔒 locked |
| **D6** | **Intimacy clock semantics** | The campaign's `dungeon_intimacy` clock becomes a **tier index**: `segments = number of tiers`, `filled = completed objectives`, **latching** (Phase 51's `monotonic=False` flip is reverted for this clock — it only climbs). The recedable-clock machinery stays in the codebase, unused here. | 🔒 locked |
| **D7** | **Knowledge model** | Replace the flat `dungeon_knowledge: list[str]` + `reveal_knowledge` slice with **per-tier authored knowledge** on each objective (`reveals_knowledge`). At tier *T* the dungeon may draw on knowledge from **all completed tiers**, and is told the **active (next) objective's hint**. `dungeon_knowledge`/`reveal_knowledge` are kept (deprecated, back-compat) but no longer the primary path. | 🔒 locked |
| **D8** | **Phase identity** | **Phase 51.5** (dotted sub-phase, like 50.5/50.6). Stays on `phase-51`; the whole Phase 51 + 51.5 work merges to `main` together once 51.5 is built. | 🔒 locked |

---

## 4. Design

Three pillars, mapped to the three playtest gaps. Pillars 1–2 are small context additions; Pillar 3
is the new machinery.

### 4.1 Pillar 1 — Character-aware dungeon (gap #2)

`play_view._dungeon_agent_inputs` already has the acting actor; it passes only `actor.slug`. Extend
it to pass character facts, and extend `DungeonVoiceAgent` to inject a `# Who Is Speaking` section.

- New agent kwargs: `actor_name: str`, `actor_playbook: str | None`, optionally
  `actor_tags: list[str]` / a short ability summary. All already accessible in `play_view`
  (`PlaybookLibrary().get(actor.playbook_slug)`, `repo.get_actor_abilities`, `actor.tags`).
- `dungeon_voice_system.txt` gains an instruction: *react to who is speaking; a character's playbook
  and tags are salient to the dungeon* (e.g. an Artificer is of special interest to a machine-mind).
- **In-session memory:** also feed the running `DialogueSession.turns` so the dungeon remembers the
  current conversation (today only *approved* long-term memories feed back, and the channel's own
  drafts never loop — so within a sitting it has amnesia). Long-term memory path unchanged.

*No new model. Pure context plumbing + one prompt edit.*

### 4.2 Pillar 2 — Grounded systems status (gap #1, first half)

Model the Crucible's subsystems as `RoomObject`s (archetype `mechanism`/`structure`) with meaningful
states (e.g. `offline`→`online`, `damaged`→`restored`) and a `restore` transition.

- New pure helper `rpg/dungeon_channel.py: dungeon_systems_status(room_objects) -> list[(name,
  state)]` — a deterministic snapshot of the dungeon's subsystems and their current states.
- `DungeonVoiceAgent` gains a `# Systems Status` section so "give me a systems assessment" returns
  *true* facts the persona narrates over (it may still color/withhold per intimacy, but the facts are
  real).
- Source of subsystem objects: the campaign's `room_objects` (already persisted/queryable via
  `repo.get_objects_by_room`). A small query gathers the subsystem-tagged objects across the dungeon.

### 4.3 Pillar 3 — Objectives & the intimacy ladder (gaps #1 second half + #3) — *the new machinery*

#### 4.3.1 `Objective` model (D2)

New Pydantic model (proposed home: `dungeon_daddy/rpg/models.py`, beside `ClockState`/`RoomObject`):

```python
class ObjectiveCompletion(BaseModel):
    kind: Literal["object_state", "item_obtained", "room_reached"]  # extensible
    target_slug: str            # object slug / item slug / room id
    required_state: str | None = None   # for object_state, e.g. "restored"

class Objective(BaseModel):
    objective_id: str
    campaign_id: str
    slug: str
    title: str                  # "Restore the Coolant Loop"
    description: str            # player/LLM-facing hint ("the dungeon wants this")
    tier_index: int            # which intimacy tier this objective gates (0-based)
    status: Literal["locked", "active", "completed"] = "locked"
    completion: ObjectiveCompletion
    advances_clock_slug: str | None = None   # usually "dungeon_intimacy"
    reveals_knowledge: list[str] = []         # secrets unlocked when this tier is reached
```

Persistence: new migration **`018_objectives.sql`** (`objectives` + a child table or JSON column for
`completion`/`reveals_knowledge`, matching the house pattern used for `room_objects`/`transitions`).
Repo gains `save_objective`, `get_objectives(campaign_id)`, `update_objective_status`.

#### 4.3.2 Objective service (D4, D5) — deterministic completion

New service `dungeon_daddy/rpg/objectives.py`:

- `advance_objectives(repo, campaign_id) -> list[ObjectiveResult]` — for each **active** objective,
  evaluate its `completion` against current world state (e.g. `object_state` → query the target
  object's `current_state == required_state`). On satisfaction:
  1. mark the objective `completed`;
  2. `tick_clock(intimacy, +1)` and persist (the **single** intimacy tick source, D5);
  3. flip the **next** tier's objective `locked → active`;
  4. draft a `MemoryEntry` (type `dungeon_state`, status `draft`) — "objective complete" (reuses the
     Phase 51 D4 engine-draft path).
- Invoked from `play_view` **after each command resolution** (the existing orchestration seam where
  `object.transitioned` etc. already land) — cheap (a handful of active objectives). No event bus.
- Pure-where-possible: the *evaluation* predicate (`completion satisfied?` given world state) is a
  pure helper, unit-tested without a repo; the service wraps it with persistence.

#### 4.3.3 Intimacy as a tier index (D6)

The seeded `dungeon_intimacy` clock: `segments = #tiers`, `filled = #completed objectives`, latching.
`dungeon_channel_available` (resonance + threshold) is unchanged mechanically, but the threshold can
be low/zero so the channel opens at tier 0 (cryptic) and *content* is what tiers gate. The Phase 51
`record_dungeon_exchange` intimacy tick is **removed** (chat no longer advances intimacy); it still
drafts the per-exchange memory.

#### 4.3.4 Knowledge by tier (D7)

The dungeon's available knowledge at tier *T* = union of `reveals_knowledge` for all **completed**
objectives (tiers `0..T-1`), plus the **active** objective's `description` fed as the *next-objective
hint*. `DungeonVoiceAgent` is fed:
- `# Knowledge you may draw on` — the unlocked-secrets union (replaces the `reveal_knowledge` slice);
- `# What You Want Next` — the active objective's hint, so the dungeon can *name the quest* (fixes
  the "demanded authorization with no hint" gap).

### 4.4 Updated LLM input contract (`DungeonVoiceAgent.respond`)

Additions to the Phase 51 §4.4 bundle (all engine-computed, all read-only for the LLM):

```
# Who Is Speaking      actor_name + playbook (+ tags / key abilities)
# Systems Status       [(subsystem, state), ...]              (§4.2)
# Knowledge you may draw on   union of completed tiers' reveals_knowledge   (§4.3.4)
# What You Want Next    active objective description (the dangled quest)    (§4.3.4)
# Recent Memories       (unchanged) + in-session DialogueSession.turns      (§4.1)
```

### 4.5 Data-model / manifest authoring (D3 seeding)

`CampaignManifest` gains `dungeon_objectives: list[ObjectiveManifest]`. Each entry authors a tier:
`slug`, `title`, `description`, `tier_index`, `completion` (kind/target/state), `reveals_knowledge`.
The Crucible seed (`tools/populate_crucible_*` / `populate_crucible_dungeon_channel.py`) authors:
- 3–4 **subsystem `RoomObject`s** (broken→restorable) across L1–L2 rooms;
- 3–4 **objectives**, one per tier, each completed by restoring its subsystem;
- the `dungeon_intimacy` clock re-segmented to `#tiers`, latching (D6);
- per-tier `reveals_knowledge` (secrets that pay off the Artificer hook and the forge-mind premise).

### 4.6 UI (minimal this phase)

Primarily a *content/depth* phase, not a UI phase. Minimal surface:
- The dungeon's replies already render in the distinct `◆ THE CRUCIBLE` bubble (Phase 51 Slice 9) —
  unchanged.
- *(Optional, decide during build)* a small **intimacy/tier indicator** or an objective line in the
  dungeon channel header so the player can see progress. Could also lean on the dungeon simply
  *telling* you (via `# What You Want Next`) and defer any HUD. Smoke test optional (50.6 precedent).

---

## 5. Non-goals

- **No generic quest log / quest UI** — objectives are dungeon-intimacy-scoped this phase. (A general
  quest surface is later.)
- **No LLM-driven completion** — objectives complete only via deterministic engine evaluation (D4).
- **No continuous subsystem health** — subsystems are discrete-state (`broken`/`restored`), reusing
  the existing `RoomObject` state machine; no 0–100% damage model.
- **No Phase 52 milestone work** — the `Objective` model is *designed to be reusable* for Phase 52 but
  playbook beats/ranks/ability-unlocks are out of scope here.
- **No corruption proposals** — Phase 51 D5 scaffold posture is unchanged.
- **No new LLM library/provider.**

---

## 6. Open balance questions (→ `BALANCE_NOTES.md`)

- Number of tiers (3 vs 4) and what each gates.
- The intimacy threshold for the channel to *open at all* (tier 0 cryptic vs. locked until tier 1).
- How much of the systems status the dungeon reveals at low intimacy (it may *lie* / withhold even
  about true facts — that's persona, not gating).
- Whether completing an objective should also draft a *higher-importance* memory than a chat exchange.

---

## 7. Slice plan (TDD — read `spec/TESTING.md` first, use the TDD skill)

Pure models/helpers first, service next, context/LLM, then seeding, UI last. One behavior per slice,
suite green before the next.

1. **`Objective` model + manifest field** — `Objective`/`ObjectiveCompletion`/`ObjectiveManifest`
   Pydantic models; `CampaignManifest.dungeon_objectives`; round-trip/validation. *(pure model)*
2. **Migration + repo** — `018_objectives.sql`; `save_objective`/`get_objectives`/
   `update_objective_status`; round-trip incl. `completion` + `reveals_knowledge`. *(persistence)*
3. **Completion predicate** — pure `completion_satisfied(completion, world_state) -> bool` for
   `object_state` (extensible to item/room). *(pure helper)*
4. **Objective service** — `advance_objectives(repo, campaign_id)`: completes satisfied actives, ticks
   intimacy (D5, single source), unlocks next tier, drafts memory. Assert clock persisted, next tier
   activated, memory drafted, **no LLM path touched**. *(service)*
5. **Drop chat intimacy tick** — remove the per-exchange intimacy tick from `record_dungeon_exchange`
   (keep the memory draft); keep tests green. *(behavior change)*
6. **Systems-status helper** — pure `dungeon_systems_status(room_objects)`. *(pure helper)*
7. **Tier knowledge + next-objective** — pure helpers: unlocked-knowledge union over completed tiers;
   active-objective lookup. *(pure helpers)*
8. **Agent context** — `DungeonVoiceAgent` gains `# Who Is Speaking` / `# Systems Status` /
   `# What You Want Next`; `_dungeon_agent_inputs` assembles them (playbook, systems, tier knowledge,
   active objective, in-session turns). Tested with a fake provider — assert the assembled prompt
   carries the new sections. *(LLM seam)*
9. **PlayView wiring** — call `advance_objectives` after command resolution; feed the new agent
   inputs. *(integration)*
10. **Seed the full ladder** — author the Crucible's 3–4 subsystems + objectives + re-segmented
    latching intimacy clock + per-tier knowledge (D3). Idempotent populate script + tests. *(seed)*
11. *(optional)* **Tier/objective HUD** — small indicator in the dungeon channel. Manual GUI verify.

---

## 8. Files in scope (anticipated)

| Area | File | Change |
|---|---|---|
| Models | `dungeon_daddy/rpg/models.py` | + `Objective` / `ObjectiveCompletion` |
| Manifest | `dungeon_daddy/campaign/manifest.py` | + `ObjectiveManifest`, `CampaignManifest.dungeon_objectives` |
| Migration | `dungeon_daddy/data/migrations/018_objectives.sql` | + `objectives` table |
| Repo | `dungeon_daddy/memory/repository.py` | + `save_objective`/`get_objectives`/`update_objective_status` |
| Service | `dungeon_daddy/rpg/objectives.py` *(new)* | `advance_objectives`, `completion_satisfied` |
| Helpers | `dungeon_daddy/rpg/dungeon_channel.py` | + `dungeon_systems_status`, tier-knowledge / active-objective helpers |
| Exchange | `dungeon_daddy/memory/dungeon_exchange.py` | drop intimacy tick (keep memory draft) |
| Agent | `dungeon_daddy/llm/agents/dungeon_voice_agent.py` + `prompts/dungeon_voice_system.txt` | + Who-Is-Speaking / Systems-Status / What-You-Want-Next sections + react-to-speaker instruction |
| View | `dungeon_daddy/views/play_view.py` | call `advance_objectives` post-command; richer `_dungeon_agent_inputs` |
| Seed | `tools/populate_crucible_dungeon_channel.py` (+ manifest) | subsystems, objectives, re-segmented latching clock, per-tier knowledge |

---

## 9. Acceptance (when 51.5 is done)

- The dungeon **names who is speaking** and reacts to their playbook (the Artificer hook lands).
- Asking for a **systems assessment** yields true subsystem states (persona may color them).
- The dungeon **names a concrete next objective**; the player restores that subsystem in the engine;
  the **engine** advances intimacy one tier; the next tier's knowledge unlocks and the next objective
  is named. Chatting alone does **not** advance intimacy.
- Objective completion is deterministic and engine-side; the LLM never completes objectives, ticks
  intimacy, or writes authoritative state.
- A full 3–4 tier ladder is playable in the Crucible.
- All pre-existing tests stay green; new behavior is TDD-covered.

---

## 10. Relationship to Phase 52 (Milestone Advancement)

Phase 52 (planned) is "playbook beats, ranks to 5, ability unlocks" — a deterministic *completion →
unlock* system for PCs. This phase's `Objective` model is the **same shape** (a tracked, deterministic
completion that unlocks something). Design `Objective` general enough that Phase 52 milestones can be
modeled as objectives (or a shared base) rather than a parallel system. Flag this seam; do **not**
build Phase 52 here.
