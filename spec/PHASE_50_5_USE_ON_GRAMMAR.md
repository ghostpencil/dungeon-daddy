# Phase 50.5 — "Use Noun on Noun" Transitive Grammar

Status: **NOT STARTED** (design pass done 2026-06-21 / 2026-06-23). Branch: TBD.
Depends on: 47 (room contents), 48 (navigation + exit gating), 49 (playbooks), 50 (VNA panel).

> A **dynamic add-on to Phase 50**, not on the roadmap and **with no GitHub issue**. It grew
> out of the Phase 50 visual verify. Distinct from the roadmap's **Phase 51 ("Talk to the
> Dungeon")**, which remains its own future phase. Design memory:
> `project_phase50_5_use_on_grammar.md`.

---

## Thesis

Phase 50 gave the player a **Verb · Noun · Adverb** Card with a *single* noun. Phase 50.5
extends that grammar to **transitive** actions — ones that need a **second noun (Target)**:

- **Give** an item to an actor — `give <item> to <actor>`.
- **Use** an item on an object or creature — `use <fuse> on <Great Lift>`,
  `use <key> on <door>`, `use <vial> on <Brakkus>`.
- **Combine** two items — `combine <item> with <item>`.
- **Look** at any noun — free, read-only, no second noun, no dice.

The grammar becomes `Verb · Noun · [Target] · Adverb`, where **Target is present only for
transitive verbs**. Everything else from Phase 50 is unchanged: the Card is still the
input-dual of an `LLMReactionProposal`, the engine still resolves, the LLM still only narrates.

**Key finding — most of this already works at the engine layer.** The phase is mostly UI
wiring plus a couple of new commands/validators and one model flag:

| Capability | Already built | Gap |
|---|---|---|
| Key → door (held, not consumed) | `RoomExit.requires_item_slug` + `exit_validator.py:14` | Set the field on the R2→R4 lift exit (`populate_crucible_level1.py` doesn't) |
| Use item → object (guaranteed, e.g. fuse → Great Lift) | `ObjectTransition.requires_item_slug` + `command_validator.py:259` | Wire the `activate` verb (needs trigger selection) |
| Give item → actor | `GiveItem(item_id, to_actor_id)` command (`command.py:20`) | Validator + UI Target noun |

---

## Decisions (locked at design)

**Decision 1 — authority split = "roll for anything contested."**
- **Deterministic Player Commands** (no roll): `give`, `combine`, `key → door`.
- **Use-on-object** routes to an action roll *only if it could fail* (see Decision 2).
- **Use-on-creature / throw-at-monster** are **always** an action roll (`resolve_card_roll`
  path) + LLM-narrated reaction.

Consistent with the core authority rule: the RPG engine is authoritative over success/fail;
the LLM is advisory and narrates the result.

**Decision 2 — contested signal = explicit flag on the transition.**
Add `contested: bool = False` (+ optional `action_verb: str | None` naming the rating to
roll) to `ObjectTransition` (`rpg/models.py:223`). A use-on-object whose transition is
`contested=True` routes through the roll path; otherwise it stays a deterministic
`ActivateObject` command. **No inferring contestedness from trigger strings** — the engine
stays authoritative.

**Decision 3 — free `look` / `examine` verb (no roll).**
Surfaced during Phase 50 verify: studying the Warden's Notice Board forced a dice roll, which
feels wrong for plain reading. Add a **`look` verb** that resolves **read-only** — a **third
route** in `_on_vna_submit` (play_view.py:1157) alongside mutation-commands and skill-rolls
(it is neither). It pulls the noun's **authoritative `description`** and hands it to the LLM
as ground truth: **no dice, no state change, any noun.**
- `study` stays the **roll-based** verb that risks something but can reveal *hidden* info.
- `look` **complements** Decision 2: `look` = free info made explicit; `contested` =
  normally-free action made risky. Chosen over a per-object "study-needs-no-roll" flag (which
  left one verb behaving two ways on hidden data — unpredictable to the player).
- **Authority:** readable text must be **seeded `description`** (it can gate puzzles, e.g. R1
  journal → warden key); never LLM-invented. Plumbing already exists post-Phase-50:
  `build_room_noun_context` carries each object's `description`, and `dm_agent.build_prompt`
  renders a `# Room Contents` block.

---

## Non-goals (this phase)

- No freeform "talk to the dungeon" channel — that is Phase 51.
- No new roll mechanics — reuse `resolve_card_roll` / `resolve_action`.
- No enemy turn / initiative (per `RPG_SYSTEM_SPEC.md`).
- No position/effect axis on the adverb (Phase 50 decision stands).
- Do not let any Card set `current_room_id` / exit `status` outside the existing command +
  approval-gated paths (Phase 48 locked decision).
- No push-yourself / momentum surface on the panel — that carry-out is tracked but **out of
  scope** here unless a slice needs it.

---

## Locked contracts reused (do not re-derive)

| Contract | Where | Note |
|---|---|---|
| `GiveItem(item_id, to_actor_id)` | `rpg/command.py:20` | exists; needs a validator |
| `ConsumeItem(item_id, reason)` | `rpg/command.py:14` | exists; no verb wired |
| `ActivateObject(object_id, actor_id, trigger)` | `rpg/command.py:53` | the use-on-object command |
| Object transition gate | `command_validator.py:259` | already checks `requires_item_slug` (held, active) |
| Exit item gate | `exit_validator.py:14` | already checks `requires_item_slug` (held, not consumed) |
| Card → command map | `action_resolution.py:resolve_card` | extend for give/combine/look routing |
| Verb→noun source filter | `action_options.py:_VERB_NOUN_SOURCES` | add transitive verbs + Target sources |
| `ActionCard(verb, noun_id, adverb)` | `action_options.py:100` | add optional `target_id` |

**Consumption semantics (carry-in):** `requires_item_slug` gates on a **held, active** item
and **never consumes** it today (keys stay held). Fuses/draughts that should be *spent* need
an explicit `ConsumeItem` step — name which transitions consume vs. merely require when the
slice lands.

---

## Slice plan (TDD, one behavior each)

> Read `spec/TESTING.md` and invoke the TDD skill before each new test file.

**Slice 1 — Grammar: optional Target.** Add `target_id: str | None = None` to `ActionCard`;
mark which verbs are transitive; extend `validate_card` to require a Target for transitive
verbs and reject one for intransitive verbs. Pure model/validation. *(unit)*

**Slice 2 — `contested` flag on `ObjectTransition`.** Add `contested: bool = False` and
`action_verb: str | None = None` to the model + DuckDB schema/migration + repo read/write.
Default keeps every existing transition deterministic. *(unit + 1 integration on the repo)*

**Slice 3 — Give validator.** `validate_command` accepts `GiveItem` when the giver holds the
item (active) and `to_actor_id` is a real actor in the party/room; rejects otherwise with a
`command.rejected` event. *(unit)*

**Slice 4 — `CombineItems` command + validator.** New `CombineItems(item_a_id, item_b_id,
actor_id)` in `command.py`; validator checks both items held + active; applier resolves the
result (consume inputs / spawn output — define the data source). *(unit + 1 integration)*

**Slice 5 — Wire `activate` (closes the Phase 50 carry-out).** Give the panel a
trigger-selection step so `resolve_card` can supply the `trigger` it already requires
(`action_resolution.py:57`). Deterministic transitions apply as `ActivateObject`; `contested`
transitions route to `resolve_card_roll` (Decision 1 + 2). *(unit + ui-test)*

**Slice 6 — Crucible key/door + fuse/lift puzzle live.** Set `requires_item_slug` on the
R2→R4 lift exit in `tools/populate_crucible_level1.py` so the key gates the door and the fuse
gates the Great Lift end-to-end. *(integration; re-run the populate script)*

**Slice 7 — Item-on-creature + consume/self.** Use-on-creature / throw-at-monster ride the
`resolve_card_roll` path with the Target as the creature noun; use-on-self / consume route to
`ConsumeItem`. Define each verb's command vs. roll routing in `resolve_card`. *(unit + 1
integration)*

**Slice 8 — `look` verb (Decision 3).** Add the `look` verb; route it as the **third branch**
of `_on_vna_submit`: fetch the noun's authoritative `description` and hand it to the LLM as
ground truth — no dice, no command, no state change. *(unit + ui-test)*

**Slice 9 — UI Target dropdown + cleanup.** Add the Target combobox to `VnaActionPanel`,
shown only for transitive verbs and populated by source (actors for `give`, items for
`combine`, objects/creatures for `use`). Submit builds the `target_id`. *(ui-test harness)*

> Order is a starting point; transitive UI (9) may interleave with the command slices it
> exercises. Confirm per-slice, not up front.

---

## Open questions to resolve at slice start

1. **Combine result source.** Where does `CombineItems` read its output item / recipe from —
   a new `requires_item_slug`-style field, a recipe table, or a per-item feature? (Lean:
   smallest data addition that the Crucible content can express.)
2. **Give Target scope.** Only party actors, or any actor in the room (NPCs included)? Phase
   48 added `actors.room_id`; decide whether `give` to an NPC is in scope or Phase 51.
3. **`look` output shape.** Does `look` post a system bubble + an LLM narration turn (like the
   roll path), or only feed the description into the next DM prompt? Confirm against the
   Phase 50 verify-fix that already names the noun in skill-roll messages.
4. **Consume vs. require per transition.** Which Crucible transitions consume the item (fuse)
   vs. merely require it held (key)? Needs a per-transition signal or an explicit
   `ConsumeItem` follow-up in the applier.

These are answered per-slice, not up front.
