# World Reaction Policy — Design Spec (proposed)

**Status:** Design settled (owner decisions locked, 2026-07-01). **Not yet scheduled** —
this is a new feature area outside the Phase 51.5 slice plan. Implementation is engine
work and must be phase-scoped before starting.

**Supersedes** the blunt miss-consequence behavior in `spec/PHASE_35_WORLD_REACTION_SERVICE.md`.
**Depends on / preserves** the `docs/LLM_AUTHORITY_BOUNDARY.md` rule and Phase 51.5 **D5**
(the objective service is the single intimacy-tick source).

---

## 1. Motivation — the audit that triggered this

A player did **STUDY** on the **Toppled Artificer Statue** (R1, a lore fixture) and rolled a
**Miss**. The deterministic world-reaction engine applied **four** effects at once:

- The Factory Learns What You Fear **+2**
- Restore the Power Core **+2**
- Mira's Guild Agenda Surfaces **+2**
- Mira Coldwell **weird +2**

Root cause (`dungeon_daddy/rpg/world_reaction.py`): on a miss the engine advances **every**
active clock whose `action_tags` list contains the action key (`study`) and whose scope
matches — by a hardcoded **+2**, with **no cap** on how many clocks fire — **and** applies
**+2** stress to one routed track. `study` happened to be in three clocks' tag lists, so all
three moved.

Three distinct defects:

1. **No blast-radius cap.** One low-stakes action moved three campaign clocks.
2. **Polarity ignored.** "Restore the Power Core" is a **player-positive objective clock**; it
   advanced on a *miss* (and a crit would tick it *back* — the engine treats all clocks as
   threat clocks: `critical → −1`).
3. **Invariant violation.** "The Factory Learns What You Fear" is a `dungeon_intimacy` clock.
   Phase 51.5 **D5** says intimacy moves **only** via objective completion. The tag fan-out
   advanced it directly — bypassing the single-source rule.

Relevance was decided by a static `action_tags` list, not by the fiction or the target. The
one clock that *should* have reacted — **"Scorpion Nest Agitated"** (room-scoped to R1) — did
not, because `study` isn't in its tags, even though the narrated fiction (statue groans, sand
erupts, floor trembles, scorpions present) is exactly what agitates a nest.

---

## 2. The model — reaction policy per object

Every `RoomObject` carries a `reaction_policy`. It governs the **world-reaction / skill-roll**
side of interacting with the object (not the deterministic `activate`-transition side, which is
already authored and specific).

| Policy | Behavior | LLM latitude | Game flow |
|---|---|---|---|
| **`scripted`** | Only the object's **authored bindings** fire (verb × outcome → specific clock/consequence). No tag fan-out. | Narrate the decided truth only | Deterministic, logical |
| **`ambient`** | Loose path: **≤1** tick on the **nearest adverse clock** (see §4); never quest/relationship/faction/intimacy. | Creative narration | Low-impact only |
| **`inert`** | Pure flavor. Zero mechanics. | Fully creative | None |

**Default:** existing/unmarked objects are `ambient`. Plot and hazard objects are promoted
explicitly (§6).

Design intent (owner): *plot/quest objects need logical deterministic control; low-impact
scenery can be supported a bit creatively.* `scripted` controls both the LLM (it can only
narrate an already-decided outcome) and the game flow (plot clocks move only where authored).

---

## 3. The clock-category firewall

The global `action_tags` matching **survives only for the ambient tier**, and only for
**adverse, locally-scoped** clocks. These clock categories are **removed** from tag-matching
entirely and may move **only** via scripted bindings or their own service:

- `objective` (quest progress — player-positive; advances on success, authored)
- `relationship` (character reveals — authored)
- `faction_pressure` (faction forces — authored)
- `dungeon_intimacy` (**D5**: objective service only)

Ambient-eligible categories: `danger`, `pursuit`, `ritual` (adverse), **and** only when the
clock is room- or level-scoped (see §4). Dungeon-level adverse clocks (e.g. "Arcane Overload
Building", "Party Detected") are *not* ambient-eligible — they move only via scripted bindings.

This firewall is load-bearing, not cosmetic: it is what fixes defects #2 and #3 from §1 by
construction.

---

## 4. Ambient selection rule (locked)

When an **`ambient`** object's action **misses** (or partials with a consequence):

1. Gather active **adverse** clocks (`danger`/`pursuit`/`ritual`) whose scope covers the
   party's current room or level.
2. Pick the **single tightest-scoped** one: room > level. Ties broken deterministically
   (e.g. lowest clock id).
3. Advance it by **+1**. Ignore `action_tags` — ambient is the loose path, so a plausible
   local pressure reacts regardless of which verb was used.
4. If no adverse local clock exists, apply **no** mechanical consequence — narration only.

No stress on the ambient path by default (stress is a `scripted` consequence). Worked example:
STUDY-miss on the statue in R1 → "Scorpion Nest Agitated" **+1**. Nothing else moves.

---

## 5. Scripted bindings

A `scripted` object authors **outcome-tiered** consequences per approach verb. Shape (final
representation TBD in implementation — likely on the object's transitions, which already carry
`advances_clock_slug` / `spawns_item_slug` / `requires_item_slug`):

```
approach verb × outcome tier → [ advance <clock_slug> ±N , apply <track> +N ]
```

- **Success side** is usually already handled: subsystem obstacles complete their objective
  (objective service ticks intimacy, D5); deterministic transitions carry `advances_clock_slug`.
  Scripted authoring mainly fills the **miss/partial** side.
- **Magnitude:** a miss defaults to **one** consequence (the spec's original PHASE_35 intent
  was "advance danger clock by 2 **OR** apply stress + advance clock" — an *either/or*, which
  the code violated by doing both across many clocks). Amounts are author-chosen; consider
  scaling to clock size (a +2 on a 4-segment clock is 50%; on an 8-segment, 25%).
- **Stress** is capacity-4; treat +2 as heavy (a *push* costs only +1). Reserve +2 for
  genuinely dangerous authored fiction (e.g. a sprung trap).

Example (Coolant Loop Manifold, `scripted`):
- `tinker`/`channel` **success** → objective completes → intimacy ticks (existing path).
- `tinker`/`channel` **miss** → advance `arcane-overload-building` **+1** (authored adverse).
  No fan-out to unrelated clocks.

---

## 6. The Crucible — object → policy map (game-designer pass)

**`scripted`** (plot/quest gate, intimacy chain, and hazards needing deterministic harm):

| Object | Room | Rationale |
|---|---|---|
| The Great Lift | R4 | Mission gate (power → descend). Already deterministic; stop miss fan-out. |
| Sand-Choked Gearworks | R4 | Tier-0 intimacy objective (adopted obstacle). |
| Coolant Loop Manifold | r02 | Tier-1 intimacy objective. |
| Arcane Conduit Array | r03 | Tier-2 intimacy objective. |
| Core Containment Ring | r05 | Tier-3 intimacy objective (climax). |
| Arcane Resonance Node | r04 | Dungeon-voice channel site — interaction opens the channel. |
| Spring-Spike Floor Plates | R5 | Trap — trigger applies authored **Body** stress. |
| Dart-Wall Vents | R5 | Trap — trigger applies authored **Body** stress. |
| Trap Control Lever | R5 | Trap-system control — deterministic. |

**`ambient`** (scenery / lore / containers): Toppled Artificer Statue (R1), Warden's Notice
Board (R2), Cargo Manifest Terminal (R3), Half-Buried Supply Locker (R1), Collapsed Market
Stall (R2), Sealed Dwarven Cargo Crate (R3).

**`inert`:** none for now (reserved for pure-flavor set dressing).

---

## 7. Data model & code impact (implementation sketch)

- **Model:** add `reaction_policy: Literal["scripted","ambient","inert"] = "ambient"` to
  `RoomObject` (`rpg/models.py`) + a migration on `room_objects`.
- **Bindings:** decide representation for outcome-tiered scripted consequences (extend
  `ObjectTransition`, or a sibling table). Author the Crucible bindings in the two seeds
  (`tools/populate_crucible_level1.py`, `tools/populate_crucible_dungeon_channel.py`).
- **Engine:** `rpg/world_reaction.py` — branch on the acted-upon object's policy: `scripted`
  → apply authored bindings only; `ambient` → §4 selection; `inert` → nothing. Apply the §3
  firewall to the tag-matching path. Enforce the blast-radius cap.
- **Stress routing:** `rpg/stress_routing.py` — stress becomes a scripted consequence, not an
  incidental byproduct of the first matched clock's category.
- **Seam:** `play_view._resolve_vna_roll` already calls `_apply_world_reaction`; it must pass
  the acted-upon object (policy + bindings) so the engine can branch.
- **Non-object actions** (no target object) fall to the ambient rule (§4) by default.

## 8. Invariants preserved

- **D5:** intimacy (`dungeon_intimacy`) moves only via the objective service. Enforced by §3.
- **Authority boundary:** the LLM still proposes; the engine disposes. Scripted bindings are
  engine-authored, deterministic; the LLM never selects clock movement for plot objects.

## 9. Open items

- Exact binding representation (transition extension vs sibling table).
- Whether partials get a softer scripted consequence than misses (per-object authoring).
- Migration/back-compat for saves whose `room_objects` predate `reaction_policy` (default
  `ambient` on read).
- **Phase scheduling:** this is a new feature; owner to slot it (its own phase, or folded into
  a reaction-systems phase). Do not implement under Phase 51.5 without an explicit scope
  decision.
