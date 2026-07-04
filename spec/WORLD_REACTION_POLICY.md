# World Reaction Policy — Design Spec (proposed)

**Status:** Design settled (owner decisions locked, 2026-07-01; amended 2026-07-04).
**Scheduled as Phase 51.6** (phase-scoped 2026-07-04) — slice plan, files-in-scope, and exit
criteria in `spec/PHASE_51_6_WORLD_REACTION_POLICY.md`. This file remains the canonical design.

**Supersedes** the blunt miss-consequence behavior in `spec/PHASE_35_WORLD_REACTION_SERVICE.md`.
**Depends on / preserves** the `docs/LLM_AUTHORITY_BOUNDARY.md` rule and Phase 51.5 **D5**
(the objective service is the single intimacy-tick source).

**Amended 2026-07-04** — a code-grounded design review resolved the §9 open items: scripted
bindings get a **sibling table** (not a transition extension), the §3 firewall gets a
**`ClockCategory` enum prerequisite**, "adverse" is **derived from category** (no new field),
and the seam fix covers **all three** `_apply_world_reaction` call sites. Audit findings the
original draft missed are in §10.

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

**Prerequisite (resolved 2026-07-04): a `ClockCategory` type.** Today `ClockState.category`
is a free-form `str | None` (`rpg/models.py:37`) with no enum and no validation — and
`objective` is not a recognized category string anywhere in code (`stress_routing.py`'s
`_CLOCK_CATEGORY_TO_STRESS` knows `danger/pursuit/ritual/relationship/faction_pressure/
dungeon_intimacy` but not `objective`). The firewall cannot be built on unvalidated author
strings — that fragility is what caused the original bug. This phase therefore starts by:

1. Adding `ClockCategory = Literal["objective","relationship","faction_pressure",
   "dungeon_intimacy","danger","pursuit","ritual"]` and typing `ClockState.category` with it
   (`str | None` accepted on read for back-compat; normalized on write).
2. A data pass normalizing the categories of seeded/live clocks to the enum.

**"Adverse" is derived, not stored (resolved 2026-07-04).** `ClockState` has no polarity
field, and we do not add one. A clock is *adverse* iff `category ∈ {danger, pursuit,
ritual}`. The category enum does double duty — firewall membership *and* polarity — which is
one new concept instead of two. If a future clock needs adverse semantics outside those three
categories, that is a new category, not a polarity flag.

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

A `scripted` object authors **outcome-tiered** consequences per approach verb:

```
approach verb × outcome tier → [ advance <clock_slug> ±N , apply <track> +N ]
```

**Representation (resolved 2026-07-04): a sibling table, NOT a transition extension.** The
original draft leaned toward extending `ObjectTransition`, but the code review killed that:
`ObjectTransition` (`rpg/models.py:237-247`) has **no outcome-tier dimension and no stress
field** — it models deterministic state changes (`from_state`/`to_state`/`trigger`), a
different axis from roll consequences. And a `scripted` object needs miss consequences on
verbs that have **no transition at all** (e.g. STUDY the Great Lift). So:

- New model `ObjectReactionBinding` (`rpg/models.py`) + table `object_reaction_bindings`:
  `binding_id, object_id, action_verb, outcome (Literal["miss","partial"]), clock_slug
  (nullable), clock_delta, stress_track (nullable), stress_amount`. A verb may bind `*` as a
  wildcard (any verb on this object). Success/critical tiers are intentionally absent — the
  success side already flows through transitions (`advances_clock_slug`) and the objective
  service (D5).
- `RoomObject` gains `reaction_bindings: list[ObjectReactionBinding]` (loaded with the
  object, like `transitions`).

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
  `RoomObject` (`rpg/models.py`) + `ClockCategory` (§3) + `ObjectReactionBinding` (§5).
- **Migration `019_reaction_policy.sql`** (current head is `018_objectives.sql`): the
  `reaction_policy` column on `room_objects` (default `'ambient'`) **and** the
  `object_reaction_bindings` table, in one migration.
- **Bindings authoring:** the Crucible bindings live in the two seeds
  (`tools/populate_crucible_level1.py`, `tools/populate_crucible_dungeon_channel.py`).
- **Engine:** `rpg/world_reaction.py` — branch on the acted-upon object's policy: `scripted`
  → apply authored bindings only; `ambient` → §4 selection; `inert` → nothing. Apply the §3
  firewall to the tag-matching path. Enforce the blast-radius cap.
- **Stress routing:** `rpg/stress_routing.py` — stress becomes a scripted consequence
  (`stress_track`/`stress_amount` on a binding), not an incidental byproduct of the first
  matched clock's category.
- **Seam (all THREE call sites, resolved 2026-07-04):** `_apply_world_reaction` is called
  from `play_view._resolve_vna_roll` (`play_view.py:1799`) **and** from the two chat-action
  paths (`play_view.py:818`, `:983`). All three must pass the acted-upon `RoomObject` (policy
  + bindings), or the untouched paths silently keep the old fan-out. Note the object is
  already resolved one line above the VNA call site (`_maybe_resolve_obstacle`,
  `play_view.py:1798`) — the wiring exists; it is dropped at the seam today.
- **Level-scope caveat:** the seam synthesizes `current_level_id` as `f"level-{idx+1}"`
  (`play_view.py:2071-2073`); the §4 level-scope match inherits this string convention.
  Cover it with an integration test so a level-id format change can't silently break
  ambient selection.
- **Non-object actions** (no target object) fall to the ambient rule (§4) by default.

## 8. Invariants preserved

- **D5:** intimacy (`dungeon_intimacy`) moves only via the objective service. Enforced by §3.
- **Authority boundary:** the LLM still proposes; the engine disposes. Scripted bindings are
  engine-authored, deterministic; the LLM never selects clock movement for plot objects.

## 9. Open items

- ~~Exact binding representation~~ **RESOLVED 2026-07-04:** sibling table
  `object_reaction_bindings` (§5) — `ObjectTransition` has no outcome-tier/stress dimension,
  and scripted objects need consequences on verbs with no transition.
- ~~Whether partials get a softer scripted consequence than misses~~ **RESOLVED 2026-07-04:**
  per-object authoring via the `outcome` column (`miss` vs `partial` rows). A `partial` row is
  optional; if absent, a partial-with-consequence falls back to the object's `miss` binding at
  **half magnitude, rounded down** (min 1 if the miss binding is nonzero) — so authors write
  one row for simple objects and two when the fiction differs.
- ~~Migration/back-compat~~ **RESOLVED 2026-07-04:** migration `019` adds the column with
  DEFAULT `'ambient'`; model default covers pre-migration reads. Nothing is retro-promoted —
  the §6 scripted promotions happen only in the Crucible seeds.
- ~~Phase scheduling~~ **RESOLVED 2026-07-04: Phase 51.6**, its own dotted sub-phase on a
  fresh branch off `main` (not folded into the shipped 51.5, not merged with Phase 53). Full
  slice plan, files-in-scope, and exit criteria: `spec/PHASE_51_6_WORLD_REACTION_POLICY.md`.

## 10. Code-audit findings (2026-07-04) — behaviors the original draft missed

Confirmed against the working tree; these inform the build but change no locked decision.

1. **Empty `action_tags` matches EVERYTHING.** The gate is
   `if clock.action_tags and resolution.action_key not in clock.action_tags`
   (`world_reaction.py:54`) — a clock with an empty tag list fires on *every* action. The
   live fan-out is broader than §1's "contains the action key" framing. The ambient rule
   ignores tags, so this dies with the old path — but audits of old saves should know
   empty-tag clocks were universal matchers.
2. **`full` outcome is a silent no-op for clocks** (`_CLOCK_TICKS["full"] = 0`, guard at
   `world_reaction.py:58-59`). This is intended and preserved: success consequences flow
   through transitions/objectives, not the reaction engine.
3. **`critical → −1` on all matched clocks** (`world_reaction.py:17`), clamped at 0 — the
   concrete polarity defect of §1. Under the new model, crit-rollback survives only where a
   scripted binding authors a negative `clock_delta`; the ambient path never rolls back.
4. **Stress routing precedence today** (`stress_routing.py:92-119`): explicit track (never
   passed) → first matched clock's `category` → first matched clock's `clock_level` → intent
   keywords → action default → `"body"`. The whole chain is bypassed on the new paths: ambient
   applies no stress; scripted stress is authored on the binding.
5. **Mis-seeded `action_tags`:** `apply_seed_pack` writes room-threat `trigger_tags` (values
   like `"noise"`, `"touch_artifact"`) into clock `action_tags` (`rpg/seed_pack.py:181`),
   where they can never match an action verb — those clocks silently never advance today.
   The tag-taxonomy spec (`spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md`) owns the data cleanup;
   this phase just stops consuming `action_tags` outside the ambient tier.
