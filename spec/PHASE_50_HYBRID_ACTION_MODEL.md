# Phase 50 — Hybrid Action Model

Status: **COMPLETE & merged to `main`** (started 2026-06-20, finished 2026-06-23; branch `phase-50`, issue #80).
Depends on: 47 (room contents), 48 (navigation + `how?` contract), 49 (playbooks).
Roadmap source: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (Phase 50 rows + "Key design
resolutions" 2026-06-17).

> **Done 2026-06-23.** All 8 slices (+5.1) shipped; the `VnaActionPanel` (Verb·Noun·Adverb
> Card panel) is wired into PlayView, replacing the provisional `how_chips` strip. On-screen
> visual verify passed: VNA dropdowns + verb→noun filtering, hybrid exit labels, Study
> narration + inventory, lock glyph, and compass/exit-label orientation (final fix `796314a` —
> exit directions now derive from the **rendered layout** coords + an 8-point y-up compass,
> not raw `dungeon.json` grid). Suite green. Two **deliberate carry-outs** (not bugs, decide
> in Phase 50.5): the `activate` verb isn't wired (needs trigger selection), and
> push-yourself/momentum controls are absent from the VNA surface. See `spec/PROJECT_INDEX.md`
> "Outstanding / Next session" for the full verify log.

---

## Thesis

The player's input becomes a structured **Verb · Noun · Adverb** grammar — a *Card*. The
Card is the **input-dual of an `LLMReactionProposal`**: the player declares an action
through bounded, engine-offered choices; the engine resolves it; the LLM only narrates the
result. This canonicalizes the Player-Command vs. LLM-advisory split that Phases 46–48
referenced forward.

- **Verb** — what you do. One of 9 universal verbs (`fight, move, tinker, study, focus,
  sway, sense, channel, endure`) ∪ class verbs surfaced from the actor's live
  `actor_abilities` (`surfaces_as_verb=true`).
- **Noun** — what you target. A concrete entity in the current room: object, loose item,
  carried item, NPC, monster, exit, `self`, or `room`.
- **Adverb** — how you do it. Universal adverb pool (the existing `HOW_MODIFIER_FLAGS`
  keys, filtered by target/world) ∪ the actor's playbook **signature adverbs** (derived
  live from `playbook_slug`, filtered by the noun's `target_type`).

A resolved Card produces **either**:
1. a **`PlayerCommand`** (`rpg/command.py`) when the verb maps to an engine-authoritative
   mutation already built (`move` → `MoveParty`, pick up → `PickUpItem`, activate →
   `ActivateObject`, equip → `EquipItem`, …), **or**
2. an **action roll** (`fight`/`study`/`sway`/…) resolved by the existing roll system
   against a clock / stress track, surfaced as a result the LLM narrates.

The adverb contributes **dice-pool deltas + world-side-effect flags** in both paths
(reusing `HOW_MODIFIER_FLAGS`); it has **no position/effect axis**.

---

## Non-goals (this phase)

- No new roll mechanics — reuse the highest-of-d6 pool already in `rpg/`.
- No enemy turn / initiative (per `RPG_SYSTEM_SPEC.md` non-goals).
- No milestone/advancement growth of the verb list — that is Phase 52 (the providers read
  the **live** `actor_abilities` set, so Phase 52 grows them with no rewiring here).
- No freeform "talk to the dungeon" channel — that is Phase 51.
- Do not let any Card set `current_room_id` / exit `status` outside the existing
  command + approval-gated paths (Phase 48 locked decision).

---

## Locked contracts reused (do not re-derive)

| Contract | Where | Note |
|---|---|---|
| 9 universal verbs | `rpg/playbook.py:9` `_UNIVERSAL_VERBS` | single source of truth |
| Adverb → flags | `rpg/move_party.py:16` `HOW_MODIFIER_FLAGS` | durable; UI surfaces a subset |
| Signature adverbs | `data/playbooks.json` per playbook + `SignatureAdverb` model | derived live, not persisted per-actor |
| Class verbs | `actor_abilities` rows where `surfaces_as_verb=true` | live, mutable set (migration 011) |
| Player commands | `rpg/command.py` `PlayerCommand` union | input-dual of a proposal |
| Target types | `playbook.py:13` `_VALID_TARGET_TYPES` | `npc, object, item, room, self, monster` |

---

## Slice plan (TDD, one behavior each)

> Read `spec/TESTING.md` and invoke the TDD skill before each new test file.

**Slice 1 — Verb provider.** `rpg/action_options.py::available_verbs(actor_abilities,
*, room_context) -> list[VerbOption]`. Universal verbs always present; class verbs appended
from abilities with `surfaces_as_verb=true`. Pure function, no DB. *(unit)*

**Slice 2 — Noun provider.** *(DONE)* `available_nouns(room_context, actor) ->
list[NounOption]`, each carrying `target_type`. Sources: room objects, loose items, carried
items, NPCs/monsters, exits, plus synthetic `self` and `room`. **Scope note:** the
`current_room` block had no NPC/monster presence, so this slice also added actor
room-presence (migration `012_actor_room.sql`: `actors.room_id`; `get_actors_by_room`) and
enriched `_fetch_current_room` with `npcs`/`monsters`/`exits` — *not* the original "no new
query" plan. Provider is forgiving of absent source keys. *(unit)*

**Slice 3 — Adverb provider.** `available_adverbs(playbook_slug, *, target_type,
world_flags) -> list[AdverbOption]`. Universal pool filtered to keys in `HOW_MODIFIER_FLAGS`
+ signature adverbs from the playbook filtered by `target_type`. Reuses the `how_chips`
surfacing logic where it overlaps. *(unit)*

**Slice 4 — Card model + validation.** `ActionCard(verb, noun_id, adverb)` Pydantic model;
`validate_card(card, options) -> CardError | None` rejects a verb/noun/adverb not in the
offered sets (engine-bounded, mirrors proposal validation). *(unit)*

**Slice 5 — Card → PlayerCommand resolution.** `resolve_card(card, ...)` maps a Card whose
verb is an engine mutation to the right `PlayerCommand` (`move`→`MoveParty(how=adverb)`,
etc.), carrying the adverb through as `how`. *(unit + 1 integration)*

**Slice 6 — Card → action roll resolution.** For non-command verbs, build the dice pool
(actor rating + adverb `dice:±N` flags + momentum), roll, return outcome tier + applied
world-side-effect flags. Reuse the existing roll module. *(unit + 1 integration)*

**Slice 7 — UI Card panel.** Replace the provisional `how_chips` strip with a VNA panel of
**real dropdowns/comboboxes** (Verb, Noun, Adverb) per auto-memory
`project_phase50_vna_dropdowns`. Driven by the Slice 1–3 providers; submit builds a Card →
Slice 4 validation → Slice 5/6 resolution. *(ui-test harness)*

**Slice 8 — Wire into PlayView + cleanup.** Replace the exit-list `how?` chip flow with the
Card panel for the full action surface; keep movement working. Remove/retire `how_chips`
only once the panel covers its cases. *(integration + ui-test)*

---

## Open questions to resolve at slice start

1. **Verb→command map location.** New `rpg/action_resolution.py`, or extend `command.py`?
   (Lean: new module; `command.py` stays a pure model file.)
2. **Where the action roll lives.** Confirm the existing roll entry point and whether
   Card resolution calls it directly or emits an intermediate "roll request".
3. **Panel placement.** Does the VNA panel replace the exit-list panel, or sit beside it?
   (Movement is just `verb=move`, so the exit list may fold into the Noun dropdown.)

These are answered per-slice, not up front.
