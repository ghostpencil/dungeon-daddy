# Monster Reaction / Threat Behavior Design

**Status:** Design (no implementation). Target phase: **Phase 53 — Threat Behavior &
Monster Reactions** (`spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`, GitHub Project #1).

This document specifies how monsters "take actions and react in fights" in a way that makes
combat feel alive **without** introducing an enemy turn, initiative, a grid, or any of the
other tactical-combat non-goals in `RPG_SYSTEM_SPEC.md:17-31`.

---

## 1. Problem

Today every monster reacts identically. An action resolution produces a **generic**
deterministic consequence — a flat clock tick + PC stress
(`dungeon_daddy/rpg/world_reaction.py`) — and the LLM may emit an `npc_reaction` string that
is **pure narration and is never mechanically applied** (`rpg/proposal_applier.py` skips it).
A Bone Hound and a Gaslight Wraith are mechanically indistinguishable; their personality
lives only in prose the engine ignores.

The `RPG_SYSTEM_SPEC.md:120-134` monster model — Instinct, Actions, Stress it inflicts,
Fallout tendencies — is currently unimplemented. This design realizes it.

## 2. Principle — reactions, not turns

A monster **never takes a turn and never rolls dice**. It **reacts** to the player's action
when that roll gives it an opening.

```
one player action → one ActionResolution → at most one monster reaction
```

This preserves the no-initiative / no-enemy-turn non-goal (reaffirmed in the 2026-06-17
review, `IMPLEMENTATION_PHASES_33_ONWARDS.md:1218`). The only currencies a reaction spends
are the ones the engine already has: **stress tracks, clocks, and tags.** No new combat
resource, no AC, no damage dice.

### Authority split (hybrid)
- **Engine** computes the set of *eligible* reactions **and every magnitude**. It owns all math.
- **LLM** selects one reaction **by id** from that set and writes the fiction. It owns flavor
  and choice-within-constraints — never numbers.

This is exactly the `docs/LLM_AUTHORITY_BOUNDARY.md` contract: "the LLM may propose; the
engine disposes."

## 3. Depth by rank

| Rank | Model | Behavior |
|---|---|---|
| `minion` / `standard` | **A** | Instinct + a small reaction menu keyed to outcome tier and action tags. |
| `elite` / `boss` | **B** | Model A **plus** boss phases: clock thresholds unlock higher reaction tiers. |

Model **C** (per-monster special abilities, cooldowns, conditional move trees) is **out of
scope** until playtests prove a specific need (`RPG_SYSTEM_SPEC.md:31`). A boss (Model B) is
simply a Model-A monster with extra tiers — **same schema, no special-casing.**

## 4. Data model (authored, catalog-bounded)

### `ThreatReaction`
Authored on the monster (in the seed pack and the monster's Markdown profile).

```python
class ThreatReaction(BaseModel):
    reaction_id: str
    flavor: str                      # short fiction hint for the LLM ("drags you down")
    trigger_outcomes: list[Literal["miss", "partial", "full", "critical"]]
    trigger_action_tags: list[str] = []   # optional; empty = any action verb
    # Effects — one or more, all bounded by a shared severity catalog:
    stress: ReactionStressEffect | None = None     # {track_key, severity}
    clock: ReactionClockEffect | None = None        # {target, clock_ref, severity}
    tag: str | None = None                          # condition applied to PC or scene
    tier: int = 0                    # 0 = base (Model A); >0 = boss phase (Model B)
    priority: int = 0                # engine ordering for deterministic fallback
```

**Magnitudes are never authored as raw numbers.** Effects carry a
`severity ∈ {minor, moderate, severe}` that maps centrally to amounts/ticks — mirroring the
existing fallout catalog. This keeps all balance in `BALANCE_NOTES.md` and makes it
impossible for authors *or the LLM* to invent magnitudes.

### Monster fields (extend `ActorState` / `SeedActor`)
- `instinct: str` — already on `SeedActor` (currently unused). Surface it; it is the fiction
  anchor the LLM must honor when selecting a reaction.
- `rank: Literal["minion", "standard", "elite", "boss"]` — drives which model applies.
- `reactions: list[ThreatReaction]`.
- `phase_thresholds: list[int] = []` — boss/elite only; resistance-clock fill levels that
  unlock each successive tier.

### Boss phases reuse existing clock state — no new persistent field
A boss owns a resistance clock (`ClockState.owner_actor_id`, already present). The **active
tier** is *derived* on each resolution:

```python
active_tier = sum(1 for t in phase_thresholds if t <= resistance_clock.filled)
```

Escalation is therefore a pure function of the clock the players are already filling. There is
no "current phase" field to persist, migrate, or get out of sync.

## 5. Engine — `ThreatReactionService` (deterministic)

Runs in the world-reaction flow, alongside/after `compute_world_reaction`:

1. Identify the scene's reacting monster and compute its `active_tier` from its resistance clock.
2. Filter `reactions` to those where: `resolution.outcome ∈ trigger_outcomes`,
   action tags match (or `trigger_action_tags` is empty), and `tier <= active_tier`.
3. Resolve each survivor's `severity` fields → concrete bounded effects. The result is the
   **eligible reaction set**; each candidate carries its precomputed mechanical effect.
4. Emit the eligible set as candidates for LLM selection, and record a deterministic
   **fallback** = the highest-`priority` candidate.

### No double-application
When a monster reaction fires, **it is** the consequence — the generic stress-routing path in
`world_reaction.py` is **suppressed** for that resolution. The generic path still runs when no
monster reaction is eligible (environmental hazards, traps, social scenes with no monster).
This keeps the change **additive**, not a rewrite of the world-reaction engine.

## 6. LLM channel — activate the existing `npc_reaction`

`NpcReactionChange` already exists in `rpg/proposal.py` but is inert. This phase makes it real.

1. `DungeonMasterAgent.request_proposal()` passes the **eligible candidates**
   (`reaction_id` + `flavor` + the monster's `instinct`) into the proposal request.
2. The LLM returns a chosen `reaction_id` (from the set) + `narration_hint`. It selects and
   narrates; it supplies **no numbers**.
3. `validate_proposal()` rejects any `reaction_id ∉` eligible set, plus the existing rule that
   a reaction may not target a player actor.
4. `proposal_applier` applies the **engine-precomputed** effect for that id (clock / stress /
   tag) and emits a `reaction.fired` domain event.
5. **Fallback:** if the LLM omits the field or returns an invalid id, the engine applies the
   deterministic highest-`priority` candidate. The game never stalls and unit tests stay
   deterministic (no live LLM required).

## 7. Trigger window

Reactions normally fire on **miss / partial** (the player gave the monster an opening). A
reaction **may** also be authored with `full` / `critical` in `trigger_outcomes` to fire on a
player success — e.g. a boss retreats, reshapes the room, or ticks a *different* clock. Today
`world_reaction.py` gives the monster nothing on a full success; this opt-in keeps the default
behavior intact while letting set-piece monsters stay dynamic even when the player wins.

## 8. Balance (new section for `BALANCE_NOTES.md`)

- **Severity → stress amount:** `minor = +1`, `moderate = +2` (consistent with the existing
  `_STRESS_AMOUNT` scale where `miss = +2`; track cap = 4 so `moderate` is half a track).
  `severe` is reserved for boss tiers.
- **Severity → clock ticks:** small fixed map (e.g. `minor = +1`, `moderate = +2`).
- **Boss `phase_thresholds` defaults:** e.g. a 6-segment resistance clock unlocks tier 1 at
  `filled ≥ 3` and tier 2 at `filled ≥ 5`.

Magnitudes deliberately match the current world-reaction numbers so this feature does **not**
inflate difficulty; it redistributes the same consequence budget into characterful flavors.

## 9. Worked examples

**Bone Hound — `rank: standard` (Model A).** Instinct: *"run down the wounded."*
- `partial` → flavor "snaps at your heels", Body **minor**, tag `prone`.
- `miss` → flavor "drags you down", Body **moderate**.

**Gaslight Wraith — `rank: boss` (Model B).** Instinct: *"make you doubt what's real."*
6-segment resistance clock, `phase_thresholds: [3, 5]`.
- **Tier 0** (clock 0–2): `partial` → Weird **minor**, tag `unsettled`.
- **Tier 1** (clock ≥3): `miss` → Weird **moderate**, ticks a named *"Lost in the Mirror"* clock.
- **Tier 2** (clock ≥5): even on a player **full** success → flavor "the room exhales and
  rearranges", tag `room_shifted`, ticks the escape clock. (The "reacts even when you win" case.)

## 10. Honors the non-goals

- **No initiative / no enemy turn:** reactions ride the player's roll cadence; one action →
  at most one reaction.
- **No monster rolls:** reactions are flat, catalog-bounded effects.
- **No grid / AC / damage dice:** effects spend only stress, clocks, and tags.
- **Lightweight monsters:** a standard monster needs only an instinct + ~3 reactions; bosses
  add tiers. Authoring effort scales with the creature's importance.

## 11. Dependencies & placement

All foundations already exist: monster actors (Phase 34), the world-reaction service
(Phase 35), and the `npc_reaction` proposal channel (Phase 36, currently inert). Cleanest to
build **after Phase 50** canonicalizes the Player-Command vs LLM-advisory split
(`IMPLEMENTATION_PHASES_33_ONWARDS.md:1201-1206`), since monster reactions live on the
LLM-advisory channel — but the work could be pulled earlier if desired.

## 12. Test plan (for the eventual TDD phase)

- Eligible-set filtering by outcome tier, action tag, and active tier.
- Deterministic fallback selection (highest priority) when no/invalid LLM choice.
- `validate_proposal()` rejects an out-of-set `reaction_id`.
- Boss `active_tier` correctly derived from resistance-clock fill (threshold crossings).
- No stress double-application: a fired reaction suppresses the generic world-reaction stress
  path for that resolution; the generic path still runs when no reaction is eligible.
- `reaction.fired` domain event emitted with the applied effect.
