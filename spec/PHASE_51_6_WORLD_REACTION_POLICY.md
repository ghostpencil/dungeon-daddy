# Phase 51.6 — World Reaction Policy

**Status:** ✅ **SPEC FINALIZED — design locked, phase-scoped 2026-07-04. Ready to implement.**
**Type:** BUILD (bug-fix-driven engine work; dotted sub-phase, like 50.5/50.6/51.5).
**Depends on:** Phase 51.5 (the `Objective` service is the single intimacy-tick source — **D5**,
which this phase enforces *by construction*), the `activate`/transition seam (Phase 47/48), and the
Phase 35 world-reaction service (whose blunt miss behavior this **supersedes**).
**One-liner:** *Replace the "miss = every tagged clock +2" fan-out with a per-object reaction policy
(`scripted` / `ambient` / `inert`) plus a clock-category firewall, so a low-stakes miss moves the one
locally-plausible pressure clock — not three unrelated campaign clocks including `dungeon_intimacy`.*

> **Canonical design:** `spec/WORLD_REACTION_POLICY.md` (owner decisions locked 2026-07-01, amended
> 2026-07-04). **This file is the phase scope only** — slices, files, exit criteria. It does not
> re-derive the design; read the design spec first (§§1–10). Where the two differ, the design spec
> wins and this file is corrected.

> **Authority boundary (unchanged):** the LLM still proposes; the engine disposes. Scripted bindings
> are engine-authored and deterministic — the LLM never selects clock movement for plot objects. The
> firewall (§3 of the design) is what enforces Phase 51.5 **D5** here.

---

## 1. Why this phase exists (the bug)

A player did **STUDY** on the Toppled Artificer Statue (R1 lore fixture) and rolled a **Miss**. The
engine moved **four** things at once — two threat/faction clocks, one player-*positive* objective
clock ("Restore the Power Core", advanced on a *miss*), and the **`dungeon_intimacy`** clock (which
Phase 51.5 **D5** says moves *only* via the objective service). The one clock that should have
reacted — "Scorpion Nest Agitated" (room-scoped to R1) — did not, because `study` wasn't in its tag
list. Full root-cause audit: design spec §1 and §10.

Three defects, all fixed here **by construction**: (1) no blast-radius cap, (2) polarity ignored
(positive objective clock advanced on a miss), (3) invariant violation (intimacy bypassed its single
source). See design §1 / §8.

## 2. Decisions

All design decisions are locked in `spec/WORLD_REACTION_POLICY.md`. The one open item there —
**§9 "Phase scheduling (still open)"** — is resolved by this document:

| # | Decision | Resolution |
|---|---|---|
| **P1** | **Phase identity** | **Phase 51.6** — its own dotted sub-phase on a fresh branch off `main`. **Not** folded into Phase 51.5 (already shipped) and **not** merged into a combined reaction-systems phase with Phase 53. Ships to `main` on its own PR. |
| **P2** | **Sequencing** | Built now (owner-chosen next, 2026-07-04), **before** Tag Hygiene → Narrator Lookup. This phase stops *consuming* `action_tags` outside the ambient tier; the tag-taxonomy spec owns the underlying data cleanup (design §10.5). No dependency inversion — the two are independent. |

Design decisions inherited (do not re-open): sibling `object_reaction_bindings` table (design §5/§9),
`ClockCategory` enum prerequisite (§3), adverse-derived-from-category (§3), all three
`_apply_world_reaction` call sites wired (§7), migration `019` adds column + table together (§7/§9),
partial falls back to half-magnitude miss binding (§9).

## 3. Non-goals

- **No tag-taxonomy data cleanup.** Mis-seeded `action_tags` (design §10.5) are the tag-taxonomy
  spec's job. This phase only *stops reading* tags outside the ambient path.
- **No new clock-polarity field.** "Adverse" is derived from category (design §3).
- **No `ObjectTransition` changes.** Scripted consequences live in the new sibling table, not on
  transitions (design §5/§9). The deterministic `activate` transition side is untouched.
- **No Phase 53 monster-reaction work.** Threat behavior stays its own phase.
- **No UI feature.** Verification is manual GUI repro of the fixed bug; no new panels/widgets.

---

## 4. Slice plan (TDD — read `spec/TESTING.md` first, use the TDD skill)

Prerequisite/type work first, then pure engine helpers, then the engine branch, then the seam, then
seeding, GUI verify last. **One behavior per slice; full suite green before the next.**

1. **`ClockCategory` enum + typed `category`** *(pure model, design §3)* — add
   `ClockCategory = Literal["objective","relationship","faction_pressure","dungeon_intimacy",
   "danger","pursuit","ritual"]`; type `ClockState.category` (`rpg/models.py:37`) with it. Accept
   `str | None` on read for back-compat; normalize/validate on write. Add pure `is_adverse(category)
   -> bool` (`category in {danger, pursuit, ritual}`). *Assert round-trip + unknown-string handling.*
2. **Clock-category normalization pass** *(data, design §3)* — a normalizer that maps seeded/live
   clock `category` strings to the enum (incl. recognizing `objective`, which no code knows today).
   Idempotent; covers the live Crucible clocks. *Assert every live/seeded clock lands on a valid
   enum member; unknown → explicit fallback, not silent.*
3. **`reaction_policy` + `ObjectReactionBinding` models** *(pure model, design §5/§7)* — add
   `reaction_policy: Literal["scripted","ambient","inert"] = "ambient"` to `RoomObject`; add
   `ObjectReactionBinding` (`binding_id, object_id, action_verb, outcome: Literal["miss","partial"],
   clock_slug: str|None, clock_delta, stress_track: str|None, stress_amount`), with `*` wildcard verb;
   `RoomObject.reaction_bindings: list[ObjectReactionBinding]`. *Assert round-trip + defaults.*
4. **Migration `019` + repo load/save** *(persistence, design §7)* — `019_reaction_policy.sql`:
   `reaction_policy` column on `room_objects` (DEFAULT `'ambient'`) **and** the
   `object_reaction_bindings` table, in one migration. Repo loads bindings with the object (like
   `transitions`). *Assert migration applies on an `018`-head DB; round-trip incl. bindings + policy.*
5. **Ambient selection rule** *(pure helper, design §4)* — `select_ambient_clock(active_clocks,
   room_id, level_id) -> ClockState | None`: gather active **adverse** clocks scoped to the party's
   room/level, pick the **single tightest-scoped** (room > level, ties by lowest clock id), caller
   advances **+1**; `None` → narration only, no mechanics. Ignores `action_tags` entirely. *Worked
   example test: statue-miss in R1 → "Scorpion Nest Agitated"; no local adverse clock → None.*
6. **Scripted binding resolution** *(pure/service, design §5/§9)* — `resolve_scripted_bindings(
   bindings, verb, outcome) -> list[Consequence]`: match verb (or `*`) × `outcome`; a `partial` with
   no authored row falls back to the object's `miss` binding at **half magnitude, rounded down (min 1
   if the miss binding is nonzero)**. *Assert verb/wildcard match, partial fallback math, empty →
   nothing.*
7. **Engine branch + firewall + cap** *(engine, design §3/§7)* — `world_reaction.py` branches on the
   acted-upon object's `reaction_policy`: `scripted` → authored bindings only; `ambient` → §4
   selection; `inert` → nothing. Remove `objective`/`relationship`/`faction_pressure`/
   `dungeon_intimacy` categories from any tag-matching path (firewall); enforce the blast-radius cap
   (ambient touches **≤1** clock). Stress moves to a scripted consequence
   (`stress_track`/`stress_amount` on a binding) — `stress_routing.py` no longer infers stress from
   the first matched clock's category on these paths. *Assert: intimacy/objective/relationship/faction
   clocks never move via reaction; scripted applies only authored deltas; ambient ≤1 clock.*
8. **Seam — wire the object through all three call sites** *(integration, design §7)* — pass the
   acted-upon `RoomObject` (policy + bindings) into `_apply_world_reaction` from
   `play_view._resolve_vna_roll` (`play_view.py:1799`, object already resolved one line above at
   `:1798`) **and** the two chat-action paths (`play_view.py:818`, `:983`). Cover the synthesized
   `current_level_id` string convention (`f"level-{idx+1}"`, `play_view.py:2071-2073`) so a level-id
   format change can't silently break ambient level-scope matching. *Integration test: STUDY-miss on
   the statue moves exactly one clock; a non-object action falls to the ambient rule.*
9. **Seed the Crucible policy map + bindings** *(seed, design §6)* — author the §6 object→policy map
   and the scripted miss/partial bindings across the two seeds (`tools/populate_crucible_level1.py`,
   `tools/populate_crucible_dungeon_channel.py`). Idempotent; preserves play progress. *Assert seeded
   policies/bindings match §6; re-run is a no-op.*
10. **Manual GUI verify** *(no automated UI)* — on the live Crucible, reproduce the original bug:
    STUDY the Toppled Artificer Statue in R1 and miss → **only** "Scorpion Nest Agitated" **+1**;
    the Power Core / Factory-Learns / Mira / `dungeon_intimacy` clocks stay put. Owner verifies.

---

## 5. Files in scope (anticipated)

| Area | File | Change |
|---|---|---|
| Models | `dungeon_daddy/rpg/models.py` | + `ClockCategory`; type `ClockState.category`; + `is_adverse`; + `reaction_policy` on `RoomObject`; + `ObjectReactionBinding` + `RoomObject.reaction_bindings` |
| Migration | `dungeon_daddy/data/migrations/019_reaction_policy.sql` *(new)* | `reaction_policy` column on `room_objects` (DEFAULT `'ambient'`) + `object_reaction_bindings` table |
| Repo | `dungeon_daddy/memory/repository.py` | load/save `reaction_policy` + `reaction_bindings`; category normalization on read/write |
| Engine | `dungeon_daddy/rpg/world_reaction.py` | policy branch; ambient selection; firewall; blast-radius cap; scripted-binding application |
| Stress | `dungeon_daddy/rpg/stress_routing.py` | stress becomes a scripted binding consequence, not an inferred byproduct on these paths |
| View | `dungeon_daddy/views/play_view.py` | pass acted-upon `RoomObject` into `_apply_world_reaction` at all three call sites (`:1799`, `:818`, `:983`); level-scope string convention |
| Seed | `tools/populate_crucible_level1.py`, `tools/populate_crucible_dungeon_channel.py` | §6 policy map + scripted bindings; idempotent |
| Data pass | *(normalizer — repo or a small `tools/` script)* | normalize live/seeded clock categories to `ClockCategory` |

---

## 6. Acceptance (when 51.6 is done)

- **The bug is dead:** a STUDY-miss on the R1 statue advances **only** the room-scoped adverse clock
  ("Scorpion Nest Agitated" +1). The Power Core, Factory-Learns-What-You-Fear, Mira, and
  `dungeon_intimacy` clocks do **not** move.
- **Firewall holds:** `objective` / `relationship` / `faction_pressure` / `dungeon_intimacy` clocks
  can never move through the reaction engine — only via scripted bindings or their own service.
  `dungeon_intimacy` moves **only** via the objective service (Phase 51.5 **D5**), enforced by
  construction.
- **Policy is honored:** `scripted` objects fire only authored bindings (no fan-out); `ambient`
  objects touch **≤1** locally-scoped adverse clock; `inert` objects apply zero mechanics.
- **Polarity is correct:** a positive objective clock never advances on a miss, and the ambient path
  never rolls a clock back (crit-rollback survives only where a scripted binding authors a negative
  delta).
- **`ClockCategory` is enforced:** categories are a validated enum, not free-form strings; live and
  seeded clocks normalize to it.
- Migration `019` applies cleanly on an `018`-head DB; the Crucible seeds are idempotent and preserve
  play progress. All pre-existing tests stay green; new behavior is TDD-covered.

---

## 7. Relationship to adjacent work

- **Phase 51.5 (shipped):** enforces **D5** here by construction — this is the phase that makes D5
  *true for the reaction engine*, not just the chat path.
- **Tag Hygiene → Narrator Lookup (next, `spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md`):** owns the
  `action_tags` data cleanup (design §10.5). This phase merely stops consuming tags outside the
  ambient tier — independent, no ordering dependency (P2).
- **Phase 53 (Threat Behavior & Monster Reactions, planned):** deliberately **not** merged with this
  phase (P1). Scripted bindings give Phase 53 a natural place to author monster-reaction consequences
  later, but no Phase 53 work happens here.
