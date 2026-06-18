# Phase 47 — Room Contents: Items in Rooms + Interactive Objects

**Status: In progress** (Slices 1–2 complete)
GitHub issue: [#72](https://github.com/ghostpencil/dungeon-daddy/issues/72)
Branch: `phase-47-items-in-rooms`

> This spec was reconstructed from issue #72 (promoted from the Phase 47 roadmap draft card on
> 2026-06-18) after Slices 1–2 had already shipped. It documents the canonical design, audits
> the as-built code against it, and locks the remaining slices. Where the issue body and the
> 2026-06-17 design review disagree, the review wins (see Locked decisions).

## Goal

Place **items** and **interactive objects** into rooms as part of a campaign seed.

- **Items in rooms** are loose: a `dungeon_item` with `owner_actor_id = None` and `room_id` set.
  A character can **pick it up** (sets `owner_actor_id`, clears `room_id`) or **drop it** back.
- **Objects** are room *fixtures* — chests, doors, levers, altars, traps, murals, healing pools.
  They cannot be carried. Each has a structured **state machine**: a designer picks an archetype
  and gets a default set of state transitions for free, customisable per transition. Activating
  an object can change its state, **spawn an item** into the room, and **advance a clock**.

The dungeon *template* stays generic. Room contents are defined **per campaign seed**, so the
same dungeon can hold different items and objects in different campaigns.

## Why

Phases 33–46 gave the engine actors, stress, clocks, factions, fallout, and a per-actor
inventory — but rooms were empty. There is nothing in a room to find, open, pull, examine, or
trip over. Room contents are the **noun layer of place**: the things Phase 50's
Verb·Noun·Adverb action model surfaces as targets, and the things Phase 48's navigation moves a
party between. Phase 47 is the first half of that ("what is in this room"); Phase 48 adds the
second ("how do I get to the next room").

## Locked design decisions

The 9 TDD slices in the issue body predate the 2026-06-17 Phase 46–52 design review. Where they
conflict, the review wins. These decisions also apply senior-level simplicity.

1. **Room interactions are Player Commands, not LLM proposals** (Gap 1 of the review).
   `PickUpItem`, `DropItem`, and `ActivateObject` extend the engine-authoritative
   `rpg/command.py` channel built in Phase 46 — they apply immediately on a valid command, with
   no approval gate, because the player authorised them. The issue body's "pickup proposal
   type" / "proposal types" wording is superseded: these are **commands**. The LLM-advisory
   `LLMReactionProposal` union carries only genuine *world*-driven object changes (e.g. "a
   tremor reseals the door"); **no proposal may set `room_id` or `current_state`**.

2. **Transition side-effects are engine-internal deterministic consequences, not proposals.**
   On a successful `ActivateObject`, the transition's `spawns_item_slug` and
   `advances_clock_slug` fire directly inside the command applier (decision #1's channel),
   each emitting a domain event. They are *not* separate proposals and need no approval.

3. **Spawned items are pre-seeded, not minted.** `spawns_item_slug` references an item that was
   already seeded into the campaign at publish time as a hidden/unplaced row
   (`owner_actor_id = None`, `room_id = None`, `status = "inert"`). On spawn the engine sets that
   item's `room_id = <object's room>` and `status = "active"`. This reuses the `items` table,
   avoids a parallel item-template catalog, and keeps the "few, authored, memorable items"
   principle from Phase 46. If the referenced slug is missing or already placed, the spawn is a
   logged no-op (the transition still applies).

4. **No party-location gate this phase.** There is no party/room-occupancy state until Phase 48
   (Dungeon Navigation). Therefore Phase 47 commands do **not** verify that the acting actor is
   *in* the object's / item's room. `PickUpItem` checks only that the item is loose and the cap
   holds; `ActivateObject` checks only the transition validity and inventory requirement. The
   "actor must be present in the room" gate is added in Phase 48, additively.

5. **The dungeon-item cap (≤ 10) is enforced on pickup**, reusing the Phase 46 rule (counts
   active `dungeon_item`s owned by the actor). Kits and gear never count.

6. **Item *placement* extends `ItemManifest`; objects get their own manifest.** Rather than the
   issue's separate `room_items: list[RoomItemPlacement]` registry (which would duplicate item
   definitions), add an optional `room_id` to the existing `ItemManifest`: an item is either
   owned (`owner_slug`) or placed in a room (`room_id`), never both. Objects need a genuinely new
   shape, so add `RoomObjectManifest` + `CampaignManifest.room_objects`. This is preserve-and-
   extend over the Phase 46 manifest, zero parallel registry.

7. **The `current_room` context block is provided, not discovered.** Phase 47 adds a net-new
   `current_room` block to `ContextBundle` (objects + loose items). Because party location does
   not exist yet (#4), the builder takes an optional `current_room_id`; when set, it populates
   the block, otherwise the block is empty. Phase 48 wires the room id from real party location,
   and extends the block with exits + fog-of-war; Phase 50 reads it for noun surfacing. The
   block grows **additively** across 47 → 48 → 50.

8. **Build minimal, extend the existing triad.** No new generic "interaction framework".
   `command.py` / `command_validator.py` / `command_applier.py` each gain the three new command
   branches alongside the Phase 46 ones, in the same style.

This opens **BUILD Phase 47**.

---

## Data model (as built — Slices 1–2)

### Pydantic models — `dungeon_daddy/rpg/models.py`

```python
ObjectArchetype = Literal[
    "container", "door", "mechanism", "structure", "trap", "lore_fixture", "resource"
]

class ObjectTransition(BaseModel):
    transition_id: str
    object_id: str
    from_state: str
    to_state: str
    trigger: str                          # e.g. "open", "unlock", "force", "activate", "examine"
    requires_item_slug: str | None = None # item that must be in the acting actor's inventory
    spawns_item_slug: str | None = None   # item placed into the room on transition (decision #3)
    advances_clock_slug: str | None = None

class RoomObject(BaseModel):
    object_id: str
    campaign_id: str
    room_id: str
    level_id: str
    slug: str
    display_name: str
    archetype: ObjectArchetype
    description: str                       # non-empty (validator)
    current_state: str
    transitions: list[ObjectTransition] = Field(default_factory=list)
```

`Item` gained `room_id: str | None = None` (loose-in-room marker; `None` = carried/unplaced).

### Object archetypes + default state machines (designer reference)

| Archetype | States | Notes |
|---|---|---|
| `container` | `sealed → opened`; locked variant `sealed → locked → unlocked → opened` | spawns items on open; force path `locked → broken` |
| `door` | `locked → unlocked → open` or `closed → open` | `unlock` needs a key slug; force `locked → broken` |
| `mechanism` | `inactive → activated`, or toggle `on ↔ off` | levers/valves/buttons; triggers clocks or linked doors |
| `structure` | `intact → damaged → destroyed`; altars `intact → activated` | destroy/activate can spawn items or tick clocks |
| `trap` | `armed → triggered → spent`, or `armed → disarmed` | disarm needs a tinker/study roll (modelled as `requires_item_slug` or a future verb gate) |
| `lore_fixture` | `unexamined → examined` | murals/inscriptions; `examine` reveals memory seeds or clues |
| `resource` | `available → depleted` | healing pools/conduits; depletion can tie to kit refreshes |

> The archetype only constrains the *enum*. The concrete transitions are authored per object
> (seed-time), so a designer can deviate from the defaults above. The validator (Slice 3) checks
> a requested trigger against the object's **own** transition rows, not the table above.

### DuckDB schema — `dungeon_daddy/data/migrations/009_room_objects.sql`

```sql
ALTER TABLE items ADD COLUMN IF NOT EXISTS room_id TEXT;

CREATE TABLE IF NOT EXISTS room_objects (
    object_id     TEXT PRIMARY KEY,
    campaign_id   TEXT NOT NULL,
    room_id       TEXT NOT NULL,
    level_id      TEXT NOT NULL,
    slug          TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    archetype     TEXT NOT NULL,
    description   TEXT NOT NULL,
    current_state TEXT NOT NULL,
    UNIQUE(campaign_id, slug)
);

CREATE TABLE IF NOT EXISTS object_transitions (
    transition_id       TEXT PRIMARY KEY,
    object_id           TEXT NOT NULL,
    from_state          TEXT NOT NULL,
    to_state            TEXT NOT NULL,
    trigger             TEXT NOT NULL,
    requires_item_slug  TEXT,
    spawns_item_slug    TEXT,
    advances_clock_slug TEXT
);
```

### Repository CRUD — `dungeon_daddy/memory/repository.py` (Slice 2 done)

Mirrors `save_item`/`get_items` (upsert on `object_id`; transitions written as child rows and
fully replaced on upsert):

- `save_room_object(obj) -> None`
- `get_room_object(object_id) -> dict | None` (transitions nested)
- `get_objects_by_room(campaign_id, room_id) -> list[dict]` (ordered by `display_name`)
- `update_object_state(object_id, new_state) -> None`
- `_room_object_row_to_dict(row)` helper

ID convention: `obj:{campaign_slug}:{object_slug}`, `tr:{...}` (mirrors `item:` / `actor:`).

---

## As-built audit — Slices 1–2 (reviewed 2026-06-18)

Verdict: **both slices faithfully implement the design; no rework required.** 61 tests pass
(`tests/unit/memory/test_room_object_repository.py`, `tests/unit/rpg/test_models.py`).

### Slice 1 — models + schema ✅
- `RoomObject` / `ObjectTransition` / `ObjectArchetype` match the issue's data model column-for-
  column; `Item.room_id` added.
- 7 archetypes as a `Literal`; `RoomObject.description` non-empty validator; archetype rejection
  and empty-description tests present.
- Migration `009_room_objects.sql` creates both tables + `ALTER TABLE items ADD COLUMN ... room_id`;
  `EXPECTED_TABLES` updated and a `room_id`-column migration test added.

### Slice 2 — repository CRUD ✅
- `save_room_object` upserts on `object_id` and fully replaces transition child rows (mirrors
  `save_item`); `get_room_object` nests transitions; `get_objects_by_room` filters by
  `(campaign_id, room_id)` ordered by `display_name`; `update_object_state` lands.
- 7 tests: round-trip, upsert dedup, room filter, empty-room guard, transitions nested,
  transitions replaced on upsert, state update.

### Notes / latent items (not blockers)
- **`UNIQUE(campaign_id, slug)` on `room_objects`** is not in the issue's column list but is the
  correct, consistent choice (matches `items` / `factions`). Caveat: `save_room_object` upserts on
  `object_id` only, so two *different* `object_id`s sharing one `(campaign_id, slug)` would raise a
  constraint error rather than upsert — identical to the `items` table's behaviour, and acceptable
  (slugs are authored unique per campaign).
- **`ObjectTransition` has no field validators** (e.g. non-empty `trigger`/`from_state`). Transitions
  are seed-authored; trigger validity is enforced *dynamically* against the object's own rows in the
  Slice 3 validator, which is the right place. No model-level change needed.
- **`update_object_state` landed in Slice 2** though it is logically the Slice 4 applier's primitive.
  Harmless (it is just a single-column updater) and already test-covered.
- **No campaign-wide object query** (`get_objects_by_campaign`) yet — not needed until the seed/
  bundle slices; add if a slice requires it.

---

## Player Command channel — extend `rpg/command.py`

```python
class PickUpItem(BaseModel):
    kind: Literal["pick_up_item"] = "pick_up_item"
    item_id: str
    actor_id: str           # the PC taking the item

class DropItem(BaseModel):
    kind: Literal["drop_item"] = "drop_item"
    item_id: str
    room_id: str            # where it lands

class ActivateObject(BaseModel):
    kind: Literal["activate_object"] = "activate_object"
    object_id: str
    actor_id: str           # the PC interacting (for requires_item_slug check)
    trigger: str            # e.g. "open", "unlock", "examine"
```

These join the `PlayerCommand` discriminated union alongside the Phase 46 commands.

### Validator — `rpg/command_validator.py`

| Command | Reject when | Accept |
|---|---|---|
| `PickUpItem` | item unknown · not a `dungeon_item` · `status != "active"` · already owned (`owner_actor_id` set) · acting actor at the ≤10 `dungeon_item` cap · actor unknown / not a PC | otherwise |
| `DropItem` | item unknown · not owned (`owner_actor_id` is None) | otherwise |
| `ActivateObject` | object unknown · no transition matches `(from_state == current_state, trigger)` · transition's `requires_item_slug` not in the actor's **active** inventory | otherwise |

Rejections emit a `command.rejected` `DomainEvent` (same shape as Phase 46).

### Applier — `rpg/command_applier.py`

| Command | Mutation | Domain event(s) |
|---|---|---|
| `PickUpItem` | `owner_actor_id = actor_id`, `room_id = None` | `item.picked_up` |
| `DropItem` | `owner_actor_id = None`, `room_id = room_id` | `item.dropped` |
| `ActivateObject` | `update_object_state(to_state)`; then deterministic side-effects (decision #2) | `object.transitioned` (+ `item.spawned`, `clock.advanced` when applicable) |

`ActivateObject` side-effects, in order, all engine-internal:
1. `spawns_item_slug` → find the campaign item with that slug that is unplaced
   (`room_id is None`, no owner); set `room_id = object.room_id`, `status = "active"`; emit
   `item.spawned`. Missing/already-placed slug → logged no-op.
2. `advances_clock_slug` → resolve the campaign clock by slug and tick it via the existing clock
   advance path; emit `clock.advanced`. Missing slug → logged no-op.

New repository helper(s) needed: `get_items_by_room(campaign_id, room_id)` and
`update_item_room(item_id, room_id | None)`. Pickup/drop compose `update_item_owner` (Phase 46)
with `update_item_room`. (Prefer two small, single-column updaters over a combined method, to
match the existing `update_item_*` family.)

---

## World-reaction proposals (unchanged channel, optional small extension)

Genuinely *world*-driven object changes the DM narrates (a quake reseals a gate, rot collapses a
bridge) remain `LLMReactionProposal`s, approval-gated, and must route a state change through a
dedicated validated member rather than touching `current_state` directly. Phase 47 does **not**
require adding such a member unless a playtest needs it; if added later it follows the Phase 46
`*Change` pattern (e.g. `SetObjectStateChange(object_id, new_state, reason)`), validated against
the object's transition graph. **Out of scope by default for this phase.**

---

## Context bundle — `memory/context_bundle.py`

Add a net-new `current_room` block (decision #7).

- `ContextBundle` gains `current_room: dict[str, Any] = Field(default_factory=dict)`.
- `ContextBundleBuilder.__init__` gains `current_room_id: str | None = None`.
- `build()` calls `_fetch_current_room(repo)`:

```
current_room:
  room_id: <id>
  objects:      [{ slug, display_name, archetype, current_state, description }]
  loose_items:  [{ slug, display_name, description, status }]   # dungeon_items with room_id == this room, owner None
```

Empty `{}` when `current_room_id` is None. Read-only — the LLM references it in narration but
never mutates room contents. Phase 48 extends this block with exits + fog-of-war; Phase 50 reads
it for noun surfacing.

---

## Seed / campaign manifest

### `dungeon_daddy/campaign/manifest.py`

```python
# ItemManifest gains (decision #6):
room_id: str | None = None      # place a loose item in a room (mutually exclusive with owner_slug)

class ObjectTransitionManifest(BaseModel):
    from_state: str
    to_state: str
    trigger: str
    requires_item_slug: str | None = None
    spawns_item_slug: str | None = None
    advances_clock_slug: str | None = None

class RoomObjectManifest(BaseModel):
    slug: str
    display_name: str
    room_id: str
    level_id: str
    archetype: Literal["container","door","mechanism","structure","trap","lore_fixture","resource"]
    description: str
    initial_state: str
    transitions: list[ObjectTransitionManifest] = Field(default_factory=list)

# CampaignManifest gains:
room_objects: list[RoomObjectManifest] = Field(default_factory=list)
```

### `dungeon_daddy/campaign/seeder.py`

- Extend `_seed_item` so an item with `room_id` set seeds as loose (`owner_actor_id = None`,
  `room_id` set). Owner and room are mutually exclusive (validate or prefer `owner_slug`).
- Add `_seed_room_object(...)` following `_seed_faction`'s idempotent pattern (skip existing
  unless `force`; `dry_run` counts only). Derive `object_id`/`transition_id` from slugs; set
  `current_state = initial_state`. Wire into `seed_from_manifest()`.

---

## Campaign Seed editor UI (Slice 9)

Extend the campaign authoring UI:

- **Room picker** — browse rooms from the attached dungeon (level → room tree).
- **Per room**: a loose-item list (place/remove `dungeon_item`s into the room) and an object list
  (add/edit/remove objects).
- **Object form** — pick archetype → default state machine auto-populated → customise
  `display_name`, `description`, `initial_state`, and per-transition labels/effects
  (`requires_item_slug`, `spawns_item_slug`, `advances_clock_slug`).

Follow the Phase 42/43 authoring-UI patterns and `UI_TESTING.md` (state-in / draw-assertions-out;
mock only Arcade rendering). No rules live in the widget — it edits manifest data.

---

## Reuse (do NOT re-implement)

- **Phase 46 command triad** (`command.py` / `command_validator.py` / `command_applier.py`) —
  extend the union + add branches; do not fork.
- **`save_item` / item updaters** — template for `update_item_room`; the cap rule already exists.
- **`save_room_object`** (Slice 2) — already mirrors `save_item`'s upsert + child-row replace.
- **Clock advance service** — reuse for `advances_clock_slug`; do not write a new ticker.
- **`_seed_faction` / `_seed_item`** — idempotent seeding pattern for `_seed_room_object`.
- **`_fetch_inventory` / `faction_reputations`** — template for `_fetch_current_room`.
- **`DomainEvent`** — every applied command + side-effect emits one (Authority Boundary §Debugging).

---

## Phase slices (TDD)

Canonical order from issue #72. Slices 1–2 are complete (audited below). The remaining work
splits into two **independent tracks** — the *Objects* track (3, 4, 6) and the *Items-in-rooms*
track (5) — that can be sequenced either way; this spec keeps the issue order.

1. ✅ **`RoomObject` + `ObjectTransition` models + DB schema.** `009_room_objects.sql`; `room_id`
   on `items`; 7 archetypes; non-empty description; tables in `EXPECTED_TABLES`.
2. ✅ **Repository object CRUD.** `save_room_object` (+ transition child rows), `get_room_object`,
   `get_objects_by_room`, `update_object_state`. Round-trip, upsert dedup, transition replace.
3. **State transition validation.** `ActivateObject` validator: valid `(from_state, trigger)`
   match, `requires_item_slug` present in actor inventory, invalid transition rejected. (No
   side-effects yet.)
4. **Transition side-effects.** `ActivateObject` applier: `update_object_state`; spawn item into
   room (decision #3); advance clock by slug; emit `object.transitioned` / `item.spawned` /
   `clock.advanced`.
5. **`PickUpItem` / `DropItem` commands.** Validator (loose-item + cap), applier
   (`update_item_owner` + `update_item_room`), `item.picked_up` / `item.dropped`.
6. **`ActivateObject` end-to-end.** Validate → apply → side-effects integration over a real repo
   (locked container with key → opened → spawns item → ticks clock).
7. **Manifest + seed.** `ItemManifest.room_id`, `RoomObjectManifest`,
   `CampaignManifest.room_objects`; `_seed_item` loose path + `_seed_room_object`; idempotent
   (`dry_run`/`force`).
8. **Context bundle `current_room` block.** `current_room_id` param + `_fetch_current_room`
   (objects + loose items); empty when no room id.
9. **Campaign Seed editor UI.** Room picker, item placement, object form.

> Slices 3–6 replace the issue's "proposal type" wording with the Command-channel design
> (decision #1). Transition side-effects (4) are engine-internal, not proposals (decision #2).

### Slice-ordering note (PROJECT_INDEX vs issue)

`PROJECT_INDEX.md` recorded the next slice as "Slice 3 — `PickUpItem`", i.e. the Items-in-rooms
track first. Issue #72 orders the Objects track first (transition validation as Slice 3). The two
tracks are independent (decision #4 removes the only cross-dependency). This spec follows the
**issue order**; if we prefer pickup-first, swap slice 5 ahead of 3–4 with no rework. PROJECT_INDEX
should be corrected to whichever order we commit to.

---

## Exit criteria

- `009_room_objects.sql` applied; `room_objects` + `object_transitions` tables and `items.room_id`
  present in seeded saves. ✅ (Slice 1)
- A campaign manifest can place loose items in rooms and define objects with state machines; the
  seeder writes them idempotently.
- Player can pick up a loose item (cap enforced) and drop it back; each applies immediately and
  emits a domain event.
- Player can activate an object: state advances along a valid transition, `requires_item_slug` is
  enforced, and `spawns_item_slug` / `advances_clock_slug` fire as deterministic engine effects.
- Invalid transitions and missing required items are rejected with `command.rejected`.
- Context bundles include the `current_room` block (objects + loose items) when a room id is
  supplied.
- Campaign Seed editor can place items and author objects per room.
- Full suite green; new tests cover every slice. Update `spec/PROJECT_INDEX.md`.

## Out of scope (later phases)

- Party/room occupancy and the "actor must be present" gate; room exits, connectors, fog-of-war —
  **Phase 48**.
- Level-transition *trigger* for `mark_level_items_inert` (Phase 46 mechanism) — **Phase 48**.
- `examine`/disarm resolved through a dice roll rather than a flat command — folds into the
  Verb·Noun·Adverb action model — **Phase 50**.
- Object nouns surfaced as selectable action targets — **Phase 50**.
- World-driven `SetObjectStateChange` proposal member — add only if a playtest needs it.
