# Phase 48 — Dungeon Navigation: Room Exits, Party Location, and Level Connectors

**Status: COMPLETE** (2026-06-19 — 2799 tests passing)
GitHub issue: [#74](https://github.com/ghostpencil/dungeon-daddy/issues/74) (label `phase-48`)
Branch: `phase-48-dungeon-navigation` (merged to `main`)

> This spec is the reconciliation deliverable for Phase 48 (Step 3 of the Phase-47-closeout
> plan in `PROJECT_INDEX.md`). It targets the **full** 10-slice scope from issue #74, with the
> leaner `PROJECT_INDEX.md` "Next session" notes folded in as **Locked decisions** below. Where
> the issue body and the 2026-06-17 design review (or the codebase as-built) disagree, the
> review/codebase wins — same rule as the Phase 47 spec.

## Goal

Add an **authoritative movement model** so the engine — not the LLM — controls where the party
can go. This phase completes the core playable loop:

> **enter room → inspect/interact → resolve actions → move**

The engine tracks party location, available exits, blocked/locked/hidden paths, discovered
routes, and level connectors. Movement is a **validated engine action** (a Player Command); the
LLM only narrates the result.

## Why

Phase 47 filled rooms with items and interactive objects (the *noun layer of place*) but left
the party unable to leave the room. Phase 48 adds the second half: **how do I get to the next
room**. It also activates the durable exit-state schema that later phases build on — Phase 50
(Hybrid Action Model) reuses this phase's engine and the `how?`→modifier-flag contract verbatim,
formalising MOVE as `verb=move` with the `how?` chips becoming **adverbs**.

## Locked design decisions

These reconcile issue #74 with the 2026-06-17 design review and the codebase as-built. They
take precedence over the issue body wherever they conflict.

1. **`MoveParty(exit_id, how)` is a Player Command, not an LLM proposal** (Gap 1 of the review).
   It lives in the engine-authoritative `rpg/command.py` channel built in Phase 46/47 and
   applies immediately on a valid command. The issue's Slice 4 wording "`MoveParty` proposal" is
   superseded — it is a **command**. The `PROJECT_INDEX.md` working name `MoveToRoom(actor_id,
   room_id)` is **superseded by `MoveParty(exit_id, how)`**: the party moves as a unit (no
   `actor_id`), and movement targets an **exit**, not a room id directly, so conditions and
   `one_way`/`how?` semantics attach to the traversal.

2. **No new `party_location` repo column.** Session state already carries the canonical fields
   (`dungeon_daddy/data/models.py`): `current_room_id: str | None`, `visited_rooms: list[str]`,
   `current_level_idx: int`. Phase 48 makes the engine the *sole* authority over these — it
   validates every move against `current_room_id` and is the only writer. The `PROJECT_INDEX.md`
   note proposing a new `party_location` column is dropped in favour of these existing fields.

3. **No LLM proposal may set `current_room_id`, `visited_rooms`, or `current_level_idx`** — nor
   exit `status` — except through the validated command/engine channel. `BlockExit` is the one
   world-reaction that touches exits, and it stays an approval-gated `LLMReactionProposal`.

4. **Party-presence gate on `PickUpItem` / `ActivateObject`** (Phase 47 out-of-scope item,
   explicitly deferred to Phase 48). The validators in `command_validator.py` gain an additive
   check: reject when the acting actor's party location (`current_room_id`) ≠ the item's /
   object's `room_id`. This is folded in as **Slice 11** (the issue's 10 slices omitted it). It
   is additive — Phase 47 validators currently skip this check and stay green.

5. **`mark_level_items_inert` trigger.** The Phase 46 engine effect
   `RpgService.mark_level_items_inert(repo, campaign_id, level_id)` already exists. Phase 48
   wires the **trigger**: the `MoveParty` applier calls it when a connector move changes
   `current_level_idx` (level just left). This is Slice 6.

6. **`how?`/adverb is mechanically load-bearing — implement as modifier flags, not branches.**
   Each `how?` contributes a set of modifier flags into the resolution context; the move
   resolver reads only the flags it cares about. Flags are **dice-pool deltas** (`dice:±1`,
   `push`) plus **world-side-effect flags** (`suppress_entry_ticks`, `force_trap_trigger`, …) —
   never `position:+1`/`effect:-1` (the roll system has no position/effect axis). Phase 50
   reuses this contract verbatim and only widens the table across all verbs.

7. **Provisional UI is throwaway; the engine is not.** Slice 10 ships a minimal exit-list panel
   sufficient to make the loop playable. Phase 50's Card primitive replaces it but reuses this
   phase's engine, command, and `how?`→flag mapping. Keep the panel thin — do not invest polish
   Phase 50 will delete.

---

## Exit Model

Exits are **derived from the dungeon's `connections` at seed publish time** and stored as runtime
state in DuckDB. The dungeon template defines topology (`Connection` objects:
`from_room`/`to_room`/`type` — see `data/models.py`); the campaign seed defines status, labels,
and conditions. The engine owns exit state.

### Exit statuses

| Status | Meaning |
|---|---|
| `open` | Passable without condition |
| `locked` | Passable only after conditions are met |
| `blocked` | Physically impassable — requires a specific action to clear |
| `hidden` | Not visible until discovered via sense or study |
| `discovered` | Was hidden; now visible and passable |
| `one_way` | Passable from this side only; status flips to `sealed` after use |
| `sealed` | Permanently closed — was one-way and has been used, or collapsed |

### Exit conditions (optional, combinable)

- `requires_item_slug` — a specific item must be in the acting actor's inventory
- `requires_object_state` (+ `requires_object_id`) — a named object in the current room must be
  in a specific state (e.g. door object at `unlocked`)
- `requires_clock_slug` + `requires_clock_min_filled` — a clock must be at or above a fill level
  (or `completed`)
- `requires_memory_slug` — a specific approved memory entry must exist

---

## Movement as an Action

The provisional panel shows a list of visible exits with labels, status indicators, and a
`how?` row:

```
[Exit list]
  -> North Door        (open)
  -> East Archway      (open)
  -> Spiral Stair v    (locked — requires iron key)
  -> ???               (1 hidden exit detected)

[How?]  cautiously   quickly   boldly   stealthily
```

`how?` affects the **world reaction applied after a successful move** — not whether movement
succeeds.

### `how?` chips → modifier flags

| how? | modifier flags | requires |
|---|---|---|
| cautiously | `suppress_entry_ticks`, `trap_chance:-1` | — |
| quickly | `tick_move_clock`, `disturb_occupants` | — |
| boldly | `occupants_aware`, `advance_npc_reaction` | — |
| stealthily | `suppress_all_entry_ticks` | `sense >= 1` |
| reverently | `intimacy:+`, ritual-connector eligible | — |
| recklessly | `skip_condition_checks`, `force_trap_trigger` | — |
| deliberately | `confirm_one_way` | — |

Chips are surfaced **contextually** — not all chips appear for every exit:
- One-way exit: always shows `deliberately`
- Ritual connector: shows `reverently`, `humbly`
- Room with armed trap clock: shows `cautiously`, `recklessly`
- Hidden passage: shows `stealthily`, `carefully`

The chosen `how?` **and** the resolved effects are both passed to the LLM for narration — the
engine resolves first, the LLM narrates the result.

---

## Engine Validation Sequence

1. Confirm exit exists from `current_room_id` and is `open` or `discovered`.
2. Evaluate all exit conditions (item, object state, clock, memory).
3. If any condition fails, return a **structured failure** — e.g.
   `{ reason: "locked", missing: "iron-key", label: "Spiral Stair" }`. No movement applied.
4. Apply pre-move effects: consume `one_way` (set status `sealed`); if a trap clock is armed and
   `how = recklessly`, trigger the clock to completion.
5. Update `current_room_id` → `to_room_id`.
6. Mark `to_room_id` visited (append to `visited_rooms` if absent).
7. Apply post-move world reaction from the `how?` modifier flags (clock ticks, NPC awareness).
8. If the move crossed a level connector, update `current_level_idx` and call
   `mark_level_items_inert` for the level just left.
9. Rebuild the room context bundle for the new room.
10. LLM narrates: exit label + `how` + applied effects + outcome + new room description.

---

## Party Movement Model

The party moves **as a unit** — all characters are always in the same room. No scouting, no
splitting. This keeps the context bundle and world reaction simple and avoids state
fragmentation. (Revisit post-Phase 52 if playtesting demands it.)

---

## Hidden Exit Discovery

Hidden exits surface through `sense` or `study` actions targeting the **room itself**. On
success (`DiscoverExit`, engine-internal):
- Status changes `hidden` → `discovered`.
- A memory entry is created (e.g. *"Talvas found a concealed passage behind the tapestry in the
  Cargo Bay."*).
- The exit appears in the exit list immediately.

**Passive hint:** if any actor has `sense >= 2`, the UI shows a *count* of hidden exits in the
current room without revealing them ("1 hidden exit detected") — a meaningful scout advantage
with no roll.

---

## Level Connectors

Special exits that transition the party between dungeon levels. They carry all the regular exit
condition types plus a `connector_type` driving UI treatment and narration tone.

| Connector type | Description | Common conditions |
|---|---|---|
| `stair_up` / `stair_down` | Standard dungeon stairs | Usually open |
| `lift` | Mechanical elevator | Clock condition (power required) |
| `ritual_gate` | Ritual transition | Item + memory + `reverently` |
| `shaft` | One-way drop | Rope item to reverse; `one_way` status |
| `dream_bridge` | Surreal passage | Intimacy clock threshold |
| `sealed_door` | Permanently closed until triggered | Object state + memory |

### Level transition flow

1. Party moves through the connector — engine validates conditions as normal.
2. `current_level_idx` updates in session.
3. Map view transitions to the new level.
4. Room context bundle rebuilt for the entry room of the new level.
5. LLM narrates with connector-appropriate tone (a ritual gate is weightier than stairs).
6. Level-bound items (Phase 47) belonging to the level just left are marked `inert`.

---

## Fog of War

Rooms are either visited or unvisited.

- `visited_rooms` (already in session.json) becomes **authoritative** this phase.
- The map renderer shows visited rooms normally; exits to unvisited rooms render as directional
  arrows with a `?` destination (label + direction shown, destination hidden until entered).
- Returning to a visited room does **not** re-trigger room-entry effects (clocks/traps already
  spent).

---

## Data Model

### New `room_exits` table (DuckDB) — migration `010_room_exits.sql`

| Column | Type | Notes |
|---|---|---|
| `exit_id` | uuid | |
| `campaign_id` | str | |
| `from_room_id` | str | |
| `to_room_id` | str | |
| `level_id` | str | level the exit belongs to |
| `label` | str | display name: "North Door", "Spiral Stair" |
| `exit_type` | enum | `door`, `arch`, `stair`, `shaft`, `gate`, `tunnel`, `passage` |
| `connector_type` | enum? | null for intra-level exits |
| `status` | enum | `open`, `locked`, `blocked`, `hidden`, `discovered`, `one_way`, `sealed` |
| `requires_item_slug` | str? | |
| `requires_object_id` | uuid? | |
| `requires_object_state` | str? | |
| `requires_clock_slug` | str? | |
| `requires_clock_min_filled` | int? | |
| `requires_memory_slug` | str? | approved memory entry that must exist |

### Pydantic models (`rpg/models.py`)

```python
class RoomExit(BaseModel):
    exit_id: str
    campaign_id: str
    from_room_id: str
    to_room_id: str
    level_id: str
    label: str
    exit_type: str = "door"
    connector_type: str | None = None
    status: str = "open"
    requires_item_slug: str | None = None
    requires_object_id: str | None = None
    requires_object_state: str | None = None
    requires_clock_slug: str | None = None
    requires_clock_min_filled: int | None = None
    requires_memory_slug: str | None = None
```

### CampaignManifest additions (`campaign/manifest.py`)

```python
class RoomExitSeed(BaseModel):
    from_room_id: str
    to_room_id: str
    label: str
    exit_type: str = "door"
    connector_type: str | None = None
    status: str = "open"
    requires_item_slug: str | None = None
    requires_object_id: str | None = None
    requires_object_state: str | None = None
    requires_clock_slug: str | None = None
    requires_clock_min_filled: int | None = None
    requires_memory_slug: str | None = None

# Added to CampaignManifest:
room_exits: list[RoomExitSeed] = []
```

Seed publish derives exits from dungeon `connections` as `open` by default, then overlays any
seed-defined overrides (status, conditions, labels).

### Session state (existing — no schema change)

- `current_room_id` — engine validates every move against it; engine is the sole writer.
- `visited_rooms` — engine appends on a successful move.
- `current_level_idx` — engine updates on a level transition.

---

## Room Context Bundle (post-movement)

Rebuilt after every move and passed into every LLM call. Extends the Phase 47 `current_room`
block (objects + loose items) with exits, the hidden-exit hint, fog-of-war, and
`resonance_point`.

```
current_room:
  id, name, description, level_id
  resonance_point: bool

visible_exits:                 (open + discovered only)
  - { label, status, exit_type, connector_type?, to_room_name? }

locked_exits:                  (shown greyed with reason)
  - { label, status, reason, missing_condition }

hidden_exit_hint: int          (count only, shown if any actor has sense >= 2)

objects: [{ name, archetype, current_state }]
loose_items: [{ name, description }]
actors_present: [{ name, actor_type, status }]
```

---

## Player Commands & World Reactions

| Action | Channel | Description |
|---|---|---|
| `MoveParty(exit_id, how)` | **Player Command** | Engine validates conditions and applies movement (incl. `how`/adverb flags); LLM narrates only |
| `DiscoverExit(exit_id)` | Engine-internal | Successful sense/study flips `hidden → discovered` |
| `UnlockExit(exit_id)` | Engine-internal | Object transition or item use flips `locked → open` |
| `SealExit(exit_id)` | Engine-internal | One-way exit used — applied automatically on the Move |
| `BlockExit(exit_id)` | **World-reaction proposal** | DM-suggested collapse/block of an exit — stays in `LLMReactionProposal`, approval-gated |

`MoveParty` lives in `rpg/command.py`. No LLM proposal may set `current_room_id`,
`visited_rooms`, `current_level_idx`, or exit `status` (except `BlockExit`, gated).

---

## Phase Slices (TDD)

Slices 1–10 follow issue #74; **Slice 11** folds in the deferred Phase 47 presence gate.

1. **`RoomExit` + `RoomExitSeed` models; `room_exits` schema + migration `010_room_exits.sql`.**
2. **Seed publish** — derive exits from dungeon `connections` (open default); apply seed
   overrides. Repository CRUD (`save_room_exit`, `get_exits_by_room`, `update_exit_status`).
3. **Exit-condition validator** — item / object-state / clock / memory checks; structured
   failure response (`{reason, missing, label}`). No mutation.
4. **`MoveParty` command** — validate (Slice 3) + apply: location update, `one_way` sealing,
   `visited_rooms` append; emits `party.moved`. Engine is sole writer of session fields.
5. **Post-move world reaction** — `how?`/adverb → modifier flags; move resolver consumes the
   flags it cares about. (This is the contract Phase 50 reuses for all verbs.)
6. **Level connector transition** — `current_level_idx` update; trigger `mark_level_items_inert`
   for the level just left.
7. **`DiscoverExit`** — sense/study surfaces a hidden exit; passive hint for `sense >= 2`;
   memory entry created.
8. **`UnlockExit` / `SealExit` (engine-internal) + `BlockExit` (world-reaction proposal).**
9. **Room context bundle builder** — full post-movement context (exits, hint, fog-of-war,
   `resonance_point`) extending the Phase 47 `current_room` block.
10. **Play-mode UI** — provisional exit-list panel (labels, status indicators, `how?` row) +
    fog-of-war map treatment. Minimal; replaced by the Card in Phase 50.
11. **Party-presence gate** (folded-in Phase 47 deferral) — `PickUpItem` / `ActivateObject`
    validators reject when actor's `current_room_id` ≠ item's/object's `room_id`. Additive.

---

## Out of scope (deferred)

- **Adverbs across all verbs / the Card UI primitive** — Phase 50. This phase ships only `how?`
  on MOVE and the modifier-flag contract Phase 50 generalises.
- **Individual character positioning / scouting / party splitting** — possibly post-Phase 52.
- **Monster reactions to movement** (`advance_npc_reaction` flag is *set* here but the reaction
  behaviour itself) — Phase 53.
