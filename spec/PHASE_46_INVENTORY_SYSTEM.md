# Phase 46 — Inventory System: Class Kits, Dungeon Items, Equipped Gear

**Status: Not started**
GitHub issue: [#70](https://github.com/ghostpencil/dungeon-daddy/issues/70)
Branch (planned): `phase-46-inventory-system`

## Goal

A narrative-first inventory system with three distinct item categories — **Class Kits**,
**Dungeon Items**, and **Equipped Gear**. No junk items: every item earns its place through
narrative, mechanical, puzzle, emotional, or progression value. The inventory is small enough
that a player remembers every item they hold.

This phase also introduces the **Player Command** channel (`rpg/command.py`) — the
engine-authoritative, input-dual of the existing LLM-advisory `LLMReactionProposal`. Phase 46
is the first consumer of that channel; Phases 48 and 50 extend it (movement, the action Card).

## Why

The RPG engine tracks actors, stress, clocks, factions, and fallout, but a party has nothing
to *carry, use, or equip*. There is no notion of a repeatable class capability (lockpicking,
healing), no significant stateful objects (quest/puzzle/magic items), and no gear that changes
what a character can do. Inventory is the missing noun layer that Phases 47 (room contents),
48 (navigation conditions), and 50 (the Verb·Noun·Adverb action model) all build on.

## Locked design decisions

These resolve tensions inside the issue body itself (the 9 TDD slices predate the 2026-06-17
design review; where they conflict, the review wins) and apply senior-level simplicity.

1. **Player actions are Commands, not Proposals.** Player-initiated inventory changes go
   through a new engine-authoritative channel `rpg/command.py`, mirroring the proposal triad
   but with **no approval gate** — a valid command applies immediately because the player
   authorised it. The LLM-advisory `LLMReactionProposal` union must **not** carry
   player-initiated inventory actions (LLM Authority Boundary, Gap 1 of the review).

2. **Three channels, cleanly separated:**

   | Channel | Module | Approval | Members |
   |---|---|---|---|
   | **Player Command** | `rpg/command.py` | immediate on valid | `ConsumeKitCharge`, `EquipItem`, `UnequipItem`, `ConsumeItem`, `GiveItem`, `TakeItem` |
   | **World-reaction proposal** | `rpg/proposal.py` (extend union) | GM-approved draft | `TransformItemChange`, `GrantItemChange`, `StripItemChange` |
   | **Engine-internal effect** | service functions | deterministic, not a proposal | `refresh_kits(...)`, `mark_level_items_inert(...)` |

   Distinct names per channel avoid the issue's `GiveItem`/`RemoveItem` collision: a *player*
   transfer is the `GiveItem`/`TakeItem` **command**; a *world* grant/strip is the
   `GrantItemChange`/`StripItemChange` **proposal**.

3. **Build the command module minimal, not generic.** `rpg/command.py` ships only the
   inventory commands plus the discriminated-union + validator + applier triad. Do **not**
   build a speculative generic command framework — Phases 48 (`MoveParty`) and 50 (the Card)
   extend it when they arrive.

4. **Equip/unequip never mutates base action ratings.** Equipping flips `is_equipped` only.
   The *effective* rating an actor uses is computed at read time:
   `effective = base + Σ(equipped rating_modifiers)`. This keeps equip/unequip perfectly
   reversible and prevents stored-value drift.

5. **`new_action` gear features are stored and surfaced, not yet selectable.** A piece of gear
   that "unlocks a new action choice" is persisted (`item_features`) and shown as a badge on
   the character sheet, but there is no verb picker to *select* it until Phase 50. Phase 46
   delivers the data + display; Phase 50 consumes it. Only `rating_modifier` features have a
   live mechanical effect this phase.

6. **The inventory cap (≤ 10) applies to `dungeon_item` only.** Class kits and equipped gear
   do not count against it.

7. **`MarkItemInert` mechanism now, trigger later.** Phase 46 ships
   `mark_level_items_inert(repo, campaign_id, level_id)` with a direct unit test. The
   *trigger* (fire it on level transition) is wired by Phase 48. Inert is one-way this phase.

8. **`room_id` on items is deferred to Phase 47.** In Phase 46 every item is actor-owned
   (`owner_actor_id` set). Phase 47 adds the `room_id` column and the items-in-rooms /
   pickup flow. The `items` schema leaves room for it but does not implement it.

9. **Safe zones reuse `Room.tags`.** Rather than add an `is_safe_zone` boolean to the dungeon
   template, mark safe rooms with the tag `"safe_zone"` (the `Room` model already has
   `tags: list[str]`). Zero migration, keeps the dungeon template generic. Rest checks
   `"safe_zone" in current_room.tags`.

This opens **BUILD Phase 46**.

---

## Data model

### Pydantic models — `dungeon_daddy/rpg/models.py`

Added alongside `FactionState` / `FalloutRecord`, following the same flat-model style.

```python
class ItemFeature(BaseModel):
    feature_id: str
    item_id: str
    feature_type: Literal["new_action", "rating_modifier"]
    action_key: str                 # e.g. "cleave" (new_action) or "fight" (rating_modifier)
    modifier: int | None = None     # set for rating_modifier; None for new_action

class Item(BaseModel):
    item_id: str
    campaign_id: str
    slug: str
    display_name: str
    item_type: Literal["class_kit", "dungeon_item", "equipped_gear"]
    description: str                 # narrative description — required (no junk items)
    owner_actor_id: str | None = None   # None = unowned (room placement: Phase 47)
    level_id: str | None = None         # set for level-bound items
    status: Literal["active", "consumed", "inert", "lost"] = "active"
    charges_current: int | None = None  # class_kit only
    charges_max: int | None = None      # class_kit only
    is_equipped: bool = False           # equipped_gear only
    features: list[ItemFeature] = Field(default_factory=list)  # gear only
```

**Invariants** (Pydantic validators, mirroring `StressTrack`/`ClockState`):
- `class_kit` requires `charges_max ≥ 1` and `0 ≤ charges_current ≤ charges_max`.
- `equipped_gear` may carry `features`; `class_kit`/`dungeon_item` carry none.
- `rating_modifier` features require a non-null `modifier`; `new_action` features require
  `modifier is None`.
- `description` must be non-empty.

### DuckDB schema — `dungeon_daddy/data/migrations/008_items.sql`

Two tables, matching the `007_factions.sql` style (TEXT ids, JSON columns as TEXT,
`UNIQUE(campaign_id, slug)`).

```sql
CREATE TABLE IF NOT EXISTS items (
    item_id         TEXT PRIMARY KEY,
    campaign_id     TEXT NOT NULL,
    slug            TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    item_type       TEXT NOT NULL,
    description     TEXT NOT NULL,
    owner_actor_id  TEXT,
    level_id        TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    charges_current INTEGER,
    charges_max     INTEGER,
    is_equipped     BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(campaign_id, slug)
);

CREATE TABLE IF NOT EXISTS item_features (
    feature_id   TEXT PRIMARY KEY,
    item_id      TEXT NOT NULL,
    feature_type TEXT NOT NULL,
    action_key   TEXT NOT NULL,
    modifier     INTEGER
);
```

> `room_id TEXT` is intentionally **omitted** here; Phase 47 adds it via `009_*.sql`.

### Repository CRUD — `dungeon_daddy/memory/repository.py`

Mirror the faction methods (`save_faction`/`get_factions`). `save_item` upserts via
`ON CONFLICT (item_id)`; features are written as child rows.

- `save_item(item: Item) -> None` — upsert item + replace its `item_features` rows.
- `get_items(campaign_id) -> list[dict]` — all items for a campaign (features nested).
- `get_items_by_actor(actor_id) -> list[dict]` — an actor's held items (status-filtered by caller).
- `update_item_status(item_id, status) -> None`
- `update_item_charges(item_id, charges_current) -> None`
- `update_item_equipped(item_id, is_equipped) -> None`
- `update_item_owner(item_id, owner_actor_id) -> None`

ID convention: `item:{campaign_slug}:{item_slug}` (mirrors `actor:` / `clock:` / `faction:`).

---

## Player Command channel — `rpg/command.py` (new)

Mirrors `rpg/proposal.py` exactly so the boundary discipline is identical and the module is
unit-testable without the GUI.

```python
class ConsumeKitCharge(BaseModel):
    kind: Literal["consume_kit_charge"] = "consume_kit_charge"
    item_id: str
    reason: str

class EquipItem(BaseModel):
    kind: Literal["equip_item"] = "equip_item"
    item_id: str

class UnequipItem(BaseModel):
    kind: Literal["unequip_item"] = "unequip_item"
    item_id: str

class ConsumeItem(BaseModel):
    kind: Literal["consume_item"] = "consume_item"
    item_id: str
    reason: str

class GiveItem(BaseModel):          # player hands an item to another party member
    kind: Literal["give_item"] = "give_item"
    item_id: str
    to_actor_id: str

class TakeItem(BaseModel):          # player removes/drops an item they own
    kind: Literal["take_item"] = "take_item"
    item_id: str

PlayerCommand = Annotated[Union[...], Field(discriminator="kind")]
```

### Validator — `rpg/command_validator.py`

Returns a `CommandValidationResult` (accepted / rejected + `rejection_events`), shaped like
`ValidationResult`. Enforced invariants (shared intent with the proposal validator — the
engine bounds both channels):

- `item_id` exists in the campaign.
- `ConsumeKitCharge`: item is a `class_kit`, `status == "active"`, `charges_current > 0`.
- `EquipItem`/`UnequipItem`: item is `equipped_gear`, `status == "active"`, owned by an actor.
- `ConsumeItem`: item `status == "active"`.
- `GiveItem`: target actor exists and is a **player-side** actor; receiving it must not push
  the target over the dungeon-item cap (≤ 10 `dungeon_item`s).
- `TakeItem`: item is owned by the acting actor.

### Applier — `rpg/command_applier.py`

`apply_commands(result, repo, campaign_id) -> CommandApplyResult`. Each accepted command
mutates state **immediately** and emits a domain event for explainability (Authority Boundary
debugging requirement):

| Command | Mutation | Domain event |
|---|---|---|
| `ConsumeKitCharge` | `charges_current -= 1` | `kit.charge_consumed` |
| `EquipItem` | `is_equipped = True` | `item.equipped` |
| `UnequipItem` | `is_equipped = False` | `item.unequipped` |
| `ConsumeItem` | `status = "consumed"` | `item.consumed` |
| `GiveItem` | `owner_actor_id = to_actor_id` | `item.transferred` |
| `TakeItem` | `status = "lost"` | `item.removed` |

No approval gate; no `proposal.applied`/`proposal.rejected` events (those belong to the
proposal channel). Command rejections emit `command.rejected`.

---

## World-reaction proposals — extend `rpg/proposal.py`

These are genuine *world* reactions (NPC gift, theft, a magic item activating), so they stay
LLM-advisory and approval-gated. Add three members to `ProposedChange`:

- `GrantItemChange(item_slug, to_actor_id, reason)` — the world gives the party an item.
- `StripItemChange(item_id, reason)` — the world removes/destroys an item (theft, decay).
- `TransformItemChange(item_id, new_slug, reason)` — a magic item activates / changes form.

`validate_proposal()` gains rules for each (unknown item/actor → reject; cap respected on
grant). They flow through the existing draft/approval path — **not** auto-applied. The applier
gains the corresponding branches. No player-owned inventory may be mutated by a proposal that
isn't one of these world-driven changes routed through validation.

---

## Engine-internal effects (service functions, not proposals)

In `rpg/service.py` (or a small `rpg/inventory.py` if `service.py` is already large — prefer
keeping it cohesive):

- `refresh_kits(repo, actor_id) -> list[str]` — sets `charges_current = charges_max` for the
  actor's active `class_kit` items; returns refreshed item ids. Called by the **rest** entry
  point when `"safe_zone" in current_room.tags`, and (later) by location-locked actions.
- `mark_level_items_inert(repo, campaign_id, level_id) -> list[str]` — sets `status = "inert"`
  for all active items whose `level_id` matches. Returns affected ids. **Trigger wired in
  Phase 48**; this phase exposes and tests the function directly.

Rest itself is minimal in Phase 46: a `rest()` path that gates on the safe-zone tag and calls
`refresh_kits`. No elaborate rest UI — Phase 50's Card absorbs action surfacing.

---

## Context bundle — `memory/context_bundle.py`

Add an `inventory` section to `ContextBundle`, mirroring `faction_reputations`. Per focus
actor, surface the held inventory so the LLM can reference it in narration (read-only —
the LLM never mutates it):

```
inventory:
  <actor_id>:
    kits:           [{ slug, display_name, charges_current, charges_max }]
    dungeon_items:  [{ slug, display_name, description, status, level_bound }]
    equipped:       [{ slug, display_name, features: [...] }]
    effective_actions: { <action_key>: base+modifiers, ... }   # rating_modifier features applied
```

- Add `inventory: dict[str, Any] = Field(default_factory=dict)` to the `ContextBundle` model.
- Add `_fetch_inventory(repo)` to `ContextBundleBuilder.build()`.
- `effective_actions` is the only place rating modifiers are realised — base ratings in
  `mechanical_state` stay untouched (decision #4).

---

## Seed / campaign manifest

### `dungeon_daddy/campaign/manifest.py`

```python
class ItemFeatureManifest(BaseModel):
    feature_type: Literal["new_action", "rating_modifier"]
    action_key: str
    modifier: int | None = None

class ItemManifest(BaseModel):
    slug: str
    display_name: str
    item_type: Literal["class_kit", "dungeon_item", "equipped_gear"]
    description: str
    owner_slug: str | None = None       # references a world_actor slug
    level_id: str | None = None
    charges_max: int | None = None      # class_kit
    is_equipped: bool = False           # equipped_gear
    features: list[ItemFeatureManifest] = Field(default_factory=list)

# CampaignManifest gains:
items: list[ItemManifest] = Field(default_factory=list)
```

### `dungeon_daddy/campaign/seeder.py`

Add `_seed_item(...)` following `_seed_faction`'s idempotent pattern (skip existing unless
`force`; `dry_run` counts only). `owner_slug` resolves to `actor:{campaign_slug}:{owner_slug}`;
`charges_current` initialises to `charges_max`. Wire it into `seed_from_manifest()`.

---

## UI — `dungeon_daddy/ui/panels/character_sheet_panel.py` (extend)

The panel already renders stress pip tracks and action ratings from an injected `ActorState`
and draws via Arcade. Extend it with three read-only sections, reusing the existing pip
drawing for kits:

- **Class kits** — pip tracks for `charges_current / charges_max` (reuse `_PIP_*` constants).
- **Dungeon items** — a compact card list (name + status); level-bound items visually tagged.
- **Equipped gear** — feature badges (rating modifiers shown as `FIGHT +1`; `new_action`
  features shown as a labelled badge, inert until Phase 50).

Inject item data via a `set_inventory(...)` method (same pattern as `set_actor` / `set_fallout`),
so the panel stays GUI-test-friendly (state set in, draw assertions out — see `UI_TESTING.md`).
No new rules live in the widget; it renders what it is given.

---

## Reuse (do NOT re-implement)

- **Proposal triad** (`rpg/proposal.py`, `proposal_validator.py`, `proposal_applier.py`) — copy
  the *shape* for the command triad; extend the *union* for world-reaction item changes.
- **`MemoryRepository`** faction methods — template for item CRUD + migration style.
- **`seed_from_manifest()` / `_seed_faction`** — idempotent seeding pattern.
- **`ContextBundleBuilder._fetch_faction_reputations`** — template for `_fetch_inventory`.
- **`CharacterSheetPanel`** pip-drawing + `set_*` injection — template for kit/item/gear rendering.
- **`DomainEvent`** — every applied command/proposal emits one (Authority Boundary §Debugging).

---

## Phase slices (TDD)

Each slice = one failing test → minimal code → refactor. Read `spec/TESTING.md` and invoke
the TDD skill before writing the test files. Test homes follow existing layout
(`tests/unit/rpg/`, `tests/unit/memory/`, `tests/unit/campaign/`, `tests/unit/ui/`).

1. **`Item` + `ItemFeature` models + DB schema.** Pydantic invariants; migration `008_items.sql`
   creates both tables; `list_tables()` sees them.
2. **Repository item CRUD.** `save_item` (+ feature child rows), `get_items`,
   `get_items_by_actor`, status/charge/equip/owner updaters. Round-trip + upsert.
3. **Kit charges:** `ConsumeKitCharge` command + validator rules + applier; `refresh_kits`
   engine effect. (Resolves the issue's "ConsumeKitCharge + RefreshKit" — command + effect,
   not proposals.)
4. **Dungeon items:** `ConsumeItem`, `GiveItem`, `TakeItem` commands; cap (≤ 10 `dungeon_item`)
   enforced in the validator.
5. **Equipped gear:** `EquipItem`/`UnequipItem` commands; effective-rating resolution
   (base + equipped `rating_modifier`s) as a read-time computation.
6. **Level-bound inert:** `mark_level_items_inert(...)` marks matching items inert; direct
   unit test (trigger deferred to Phase 48).
7. **Context bundle inventory:** `_fetch_inventory` adds kits, dungeon items, equipped features,
   and `effective_actions` per focus actor.
8. **World-reaction item proposals:** `GrantItemChange` / `StripItemChange` /
   `TransformItemChange` added to the proposal union, validator, and applier (approval-gated).
9. **Character Sheet Panel UI:** kit pips, dungeon-item cards, gear badges via `set_inventory`.
10. **Manifest + seed:** `ItemManifest` + `CampaignManifest.items`; `_seed_item` wires items
    into the save DB at publish (idempotent; `dry_run`/`force` honoured).

> Slices 3–5 deliberately replace the issue's "proposal types" wording with the
> Command-channel design from the 2026-06-17 review (decision #1). Slice 8 keeps the genuinely
> world-driven item changes on the proposal channel.

---

## Exit criteria

- `008_items.sql` applied; `items` + `item_features` tables present in seeded saves.
- A campaign manifest with `items` seeds party kits + starting dungeon items into the save DB.
- Player can consume kit charges, equip/unequip gear, consume/give/drop dungeon items via the
  Command channel; each applies immediately and emits a domain event.
- Effective action ratings reflect equipped `rating_modifier` gear without altering base ratings.
- Level-bound items can be marked inert via the engine function.
- Context bundles include per-actor inventory; the character sheet renders kits, items, and gear.
- World-driven grant/strip/transform flow through the approval-gated proposal channel.
- Full suite green; new tests cover every slice. Update `spec/PROJECT_INDEX.md`.

## Out of scope (later phases)

- Items in rooms + pickup/drop-to-room + `room_id` column — **Phase 47**.
- Level-transition *trigger* for `mark_level_items_inert`; exit conditions using items — **Phase 48**.
- Class verbs / playbook kits as the source of abilities — **Phase 49**.
- `new_action` gear features becoming selectable verbs in the action picker — **Phase 50**.
