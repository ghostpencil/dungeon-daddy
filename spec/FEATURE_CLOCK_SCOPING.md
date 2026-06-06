# Feature — Clock Scoping, Clock Levels, and Campaign Seed Upgrades

## Problem

All active clocks advance on every failed roll, regardless of where the
action took place or what kind of action it was. A SENSE roll in one room
should not advance a clock representing a trap mechanism in a completely
different room. A clock representing a patrol detecting noise should not
advance because a character failed a CHANNEL roll.

Beyond room scoping, Dungeon Daddy needs clocks at multiple narrative scales:

```text
Room clocks
Level clocks
Dungeon clocks
Quest / Plot clocks
Character clocks
Faction clocks
```

Without upgrading the campaign seed files and the data model, the feature
exists mostly as infrastructure. Playtests need real seeded clocks that
demonstrate how different clock levels behave.

---

## Goals

1. Make clock advancement contextually meaningful by room and action.
2. Preserve and complete Phase 35.5 scoping behavior.
3. Finish the missing branch wiring so scoped clocks work in the actual PlayView action loop.
4. Add explicit clock-level metadata to seeded clocks.
5. Upgrade existing campaign seed files with representative clocks at multiple levels.
6. Ensure context bundles, debug UI, and world reactions expose enough clock metadata for the DM prompt and developer debugging.
7. Keep this deterministic. The LLM narrates clock consequences; it does not decide which clock advances.

---

## Branch Context

Current branch: `phase-35.5-clock-scoping`

### Already implemented

`ClockState` now has:

```python
scope_room_id: str | None = None
action_tags: list[str] = Field(default_factory=list)
```

`MemoryRepository.save_clock()` persists both fields, `update_clock_scope()` can
update them without overwriting progress/status, and `get_clocks()` returns them.

`compute_world_reaction()` accepts `current_room_id` and filters clocks:

```python
if clock.scope_room_id is not None and clock.scope_room_id != current_room_id:
    continue
if clock.action_tags and resolution.action_key not in clock.action_tags:
    continue
```

`apply_seed_pack()` already walks `room_threats` and calls `update_clock_scope()`
for related clocks. Migration `004_clock_scoping.sql` exists.

### Important gaps

1. `RpgService.react_to_resolution()` does not accept/pass `current_room_id` yet.
2. `PlayView._apply_world_reaction()` reconstructs `ClockState` without `scope_room_id` and `action_tags`.
3. `PlayView._apply_world_reaction()` saves advanced clocks without preserving scope metadata, which can erase scope fields because `save_clock()` updates them on conflict.
4. Debug clock display still does not show scope/action metadata.
5. Seed clocks still only have `category`; they do not yet have explicit clock level/scope.
6. Existing campaign files need to be enhanced to include examples of each useful clock level.

---

## Terminology

Use **clock level** for narrative scope.

Recommended values:

```text
room
level
dungeon
quest
character
faction
```

Use **clock category** for mechanical/dramatic type.

Recommended values:

```text
danger
discovery
ritual
pursuit
relationship
dungeon_intimacy
faction_pressure
objective
boss
escape
transformation
```

Examples:

```text
Room danger clock: Boiler Trap Primed
Level alert clock: The Factory Reawakens
Dungeon intimacy clock: The Dungeon Learns What Comforts You
Quest objective clock: Restore the Industrial Elevator
Character transformation clock: Mara Begins to Trust the Dungeon
Faction pressure clock: The Cult Opens the Inner Gate
```

---

## Design

### Filtering rules (compose with AND)

| Clock field | Empty / None | Non-empty |
|---|---|---|
| `scope_room_id` | advances in any room (global) | advances only when `current_room_id` matches |
| `action_tags` | advances for any action | advances only when `resolution.action_key` is in `action_tags` |

A clock must pass **both** filters to advance. Examples:

- `scope_room_id=None, action_tags=[]` → global; ticks on any miss/partial (current behaviour, preserved as default)
- `scope_room_id="room_boiler", action_tags=[]` → ticks on any miss/partial in the boiler room only
- `scope_room_id=None, action_tags=["sense","study"]` → ticks on a sense/study miss anywhere in the dungeon
- `scope_room_id="room_boiler", action_tags=["fight","move"]` → ticks only on a fight/move miss inside the boiler room

### Stress tracks unchanged

Stress on miss/partial still applies to the acting actor only. Stress track
selection (body vs composure vs weird) is **out of scope** for this feature.

---

## Data Model

### `ClockState` (models.py)

```python
class ClockState(BaseModel):
    clock_id: str
    campaign_id: str
    label: str
    segments: int
    filled: int = 0
    status: Literal["active", "completed", "abandoned"] = "active"

    # Phase 35.5 fields
    scope_room_id: str | None = None
    action_tags: list[str] = Field(default_factory=list)

    # Clock level fields
    clock_level: Literal["room", "level", "dungeon", "quest", "character", "faction"] = "dungeon"
    category: str | None = None
    level_id: str | None = None
    owner_actor_id: str | None = None
    stakes: str | None = None
    completion_effect: str | None = None
    visible_to_player: bool = True
```

`scope_room_id` remains the precise room filter. `clock_level` answers the broader
question: is this pressure local, level-wide, dungeon-wide, quest-focused, personal,
or faction-driven?

### `SeedClock` (seed_pack.py)

```python
class SeedClock(BaseModel):
    slug: str
    label: str
    segments: int
    category: str
    notes: str | None = None

    # Phase 35.5 / branch-compatible fields
    scope_room_id: str | None = None
    action_tags: list[str] = Field(default_factory=list)

    # Clock level fields
    clock_level: Literal["room", "level", "dungeon", "quest", "character", "faction"] = "dungeon"
    level_id: str | None = None
    owner_actor_slug: str | None = None
    stakes: str | None = None
    completion_effect: str | None = None
    visible_to_player: bool = True
```

---

## Migrations

### `004_clock_scoping.sql` (already exists)

```sql
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS scope_room_id TEXT DEFAULT NULL;
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS action_tags TEXT DEFAULT '[]';
```

### `005_clock_levels.sql` (new)

Location: `dungeon_daddy/data/migrations/005_clock_levels.sql`

```sql
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS clock_level TEXT DEFAULT 'dungeon';
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS category TEXT DEFAULT NULL;
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS level_id TEXT DEFAULT NULL;
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS owner_actor_id TEXT DEFAULT NULL;
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS stakes TEXT DEFAULT NULL;
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS completion_effect TEXT DEFAULT NULL;
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS visible_to_player BOOLEAN DEFAULT TRUE;
```

Existing clocks remain valid and become dungeon-level clocks by default.

---

## Repository (`memory/repository.py`)

### `save_clock`

Accept and persist all metadata fields:

```python
def save_clock(
    self,
    clock_id: str,
    campaign_id: str,
    label: str,
    segments: int,
    filled: int = 0,
    status: str = "active",
    scope_room_id: str | None = None,
    action_tags: list[str] | None = None,
    clock_level: str = "dungeon",
    category: str | None = None,
    level_id: str | None = None,
    owner_actor_id: str | None = None,
    stakes: str | None = None,
    completion_effect: str | None = None,
    visible_to_player: bool = True,
) -> None:
```

Store `action_tags` as `json.dumps(action_tags or [])`.

### `get_clocks`

Add all new fields to the SELECT and returned dicts. Deserialise `action_tags`
with `json.loads`.

### `update_clock_progress` (new method)

Add a targeted method that changes only `filled` and `status`, preserving all
metadata. PlayView and world reaction persistence should call this instead of
`save_clock()` when only advancing a clock:

```python
def update_clock_progress(
    self,
    clock_id: str,
    filled: int,
    status: str,
) -> None:
    ...
```

### `update_clock_scope`

Must not erase `clock_level`, `category`, `stakes`, or `completion_effect`.

---

## Seed Pack (`rpg/seed_pack.py`)

### `apply_seed_pack`

Save all new clock metadata including `clock_level`, `level_id`, `stakes`,
`completion_effect`, and `visible_to_player`.

If `owner_actor_slug` is supplied, derive the stable actor id:

```python
owner_actor_id = derive_actor_id(pack.campaign_slug, clock.owner_actor_slug)
```

Room threat backfill continues to work. If a `room_threat` references a clock,
it may overwrite or fill in `scope_room_id` and `action_tags`, but must not erase
the clock's broader `clock_level`, `category`, `stakes`, or `completion_effect`.

---

## World Reaction (`rpg/world_reaction.py`)

### `compute_world_reaction` signature

```python
def compute_world_reaction(
    resolution: ActionResolution,
    threat_clocks: list[ClockState],
    pc_actors: list[tuple[ActorState, dict[str, StressTrack]]],
    current_room_id: str | None = None,
) -> WorldReaction:
```

Clock filtering (replace the existing status-only check with):

```python
for clock in threat_clocks:
    if clock.status != "active":
        continue
    if clock.scope_room_id is not None and clock.scope_room_id != current_room_id:
        continue
    if clock.action_tags and resolution.action_key not in clock.action_tags:
        continue
    # ... existing tick logic unchanged
```

---

## Call Site Fixes

### `RpgService.react_to_resolution`

Change signature to expose `current_room_id`:

```python
def react_to_resolution(
    self,
    resolution: ActionResolution,
    threat_clocks: list[ClockState],
    pc_actors: list[tuple[ActorState, dict[str, StressTrack]]],
    current_room_id: str | None = None,
) -> tuple[WorldReaction, DomainEvent]:
    reaction = compute_world_reaction(
        resolution,
        threat_clocks,
        pc_actors,
        current_room_id=current_room_id,
    )
    ...
```

### `PlayView._apply_world_reaction`

When building `ClockState` from repository rows, include all clock metadata:

```python
ClockState(
    clock_id=r["clock_id"],
    campaign_id=r["campaign_id"],
    label=r["label"],
    segments=r["segments"],
    filled=r["filled"],
    status=r["status"],
    scope_room_id=r.get("scope_room_id"),
    action_tags=r.get("action_tags", []),
    clock_level=r.get("clock_level", "dungeon"),
    category=r.get("category"),
    level_id=r.get("level_id"),
    owner_actor_id=r.get("owner_actor_id"),
    stakes=r.get("stakes"),
    completion_effect=r.get("completion_effect"),
    visible_to_player=r.get("visible_to_player", True),
)
```

Pass current room and use `update_clock_progress()` when persisting reaction clock
changes so metadata survives:

```python
reaction, _evt = self._rpg_service.react_to_resolution(
    resolution,
    threat_clocks,
    pc_pairs,
    current_room_id=self._state.current_room_id if self._state else None,
)
```

---

## Debug UI

Update `DebugControls.clock_section_lines()` to display scope and level metadata:

```text
Clocks: 6 active
  [1/4] Boiler Trap Primes {room:boiler_room | danger | actions: move,tinker}
  [3/8] The Factory Reawakens {level:level_2 | danger}
  [2/8] The Dungeon Learns What Comforts You {dungeon | dungeon_intimacy | actions: sense,sway,channel}
  [0/6] Restore the Industrial Elevator {quest | objective}
  [1/6] Mara Begins to Trust the Dungeon {character:mara | relationship}
```

---

## Context Bundle

`ContextBundleBuilder` should preserve all clock metadata from
`MemoryRepository.get_clocks()` in `open_clocks`.

The DM prompt should receive:

```text
- label
- filled / segments
- clock_level
- category
- scope_room_id / level_id / owner_actor_id when present
- stakes
- completion_effect
```

---

## Campaign File Enhancement

Upgrade every existing campaign seed file under:

```text
seed_data/campaigns/<campaign_slug>/rpg_seed.json
```

### Minimum per-campaign requirement

```text
2 room clocks
1 level clock
1 dungeon clock
1 quest/plot clock
1 character clock  (if campaign has a named PC)
1 faction clock    (if campaign has a faction or cult actor)
```

Do not add meaningless clocks just to satisfy a count. Each clock must have a
clear fictional consequence. If a campaign has no faction actor, either skip the
faction clock or add a lightweight dungeon-side faction actor if it fits the seed.

### Room clocks

Use for local hazards, traps, monsters waking up, room-specific investigations,
or immediate scene pressure.

Required fields:

```json
{
  "slug": "boiler-trap-primes",
  "label": "The Boiler Trap Primes",
  "segments": 4,
  "category": "danger",
  "clock_level": "room",
  "scope_room_id": "boiler_room",
  "action_tags": ["move", "tinker", "fight"],
  "stakes": "The room becomes actively dangerous as pressure valves fail.",
  "completion_effect": "Steam erupts through the chamber; future movement actions here start in a worse position."
}
```

Also add or verify a matching `room_threats` entry:

```json
{
  "location_slug": "boiler_room",
  "trigger_tags": ["move", "tinker", "fight"],
  "related_clock_slugs": ["boiler-trap-primes"],
  "possible_reactions": ["advance_clock", "apply_stress", "reveal_threat"]
}
```

`location_slug` must match the room `id` used in `SessionState.current_room_id`.

### Level clocks

Use for floor-wide escalation: security alert, factory awakening, level flooding,
library rearranging, patrol mobilization. Generally should not have `scope_room_id`
unless triggered from one specific control room.

```json
{
  "slug": "factory-reawakens",
  "label": "The Factory Reawakens",
  "segments": 8,
  "category": "danger",
  "clock_level": "level",
  "level_id": "level_2",
  "action_tags": ["fight", "move", "tinker"],
  "stakes": "The abandoned factory begins routing power back into dormant systems.",
  "completion_effect": "Repair golems begin patrolling multiple rooms on this level."
}
```

### Dungeon clocks

Use for the entity's long-term understanding, intimacy, possessiveness, architecture
changes, or dungeon-wide awakening. Ideal companions to Weird stress and dungeon
intimacy mechanics.

```json
{
  "slug": "dungeon-learns-your-comforts",
  "label": "The Dungeon Learns What Comforts You",
  "segments": 8,
  "category": "dungeon_intimacy",
  "clock_level": "dungeon",
  "action_tags": ["sense", "sway", "channel", "focus"],
  "stakes": "The dungeon learns which forms of safety and tenderness make the party hesitate.",
  "completion_effect": "The dungeon begins creating personalized refuge rooms that are comforting but dangerous to trust."
}
```

### Quest / Plot clocks

Use for player-facing objectives. May advance positively on full/critical successes
in a future pass; for now they are tracked and displayed.

```json
{
  "slug": "restore-industrial-elevator",
  "label": "Restore the Industrial Elevator",
  "segments": 6,
  "category": "objective",
  "clock_level": "quest",
  "action_tags": ["tinker", "study", "channel"],
  "stakes": "The party needs the elevator to reach the lower power core level.",
  "completion_effect": "The industrial elevator can carry the party to Level 3."
}
```

### Character clocks

Use for personal arcs, trust, corruption, fear, obsession, injury recovery, or
dependency on the dungeon. Use `owner_actor_slug` in seed files (becomes
`owner_actor_id` in persisted state).

```json
{
  "slug": "mara-trusts-the-dungeon",
  "label": "Mara Begins to Trust the Dungeon",
  "segments": 6,
  "category": "relationship",
  "clock_level": "character",
  "owner_actor_slug": "mara",
  "action_tags": ["sense", "sway", "channel", "focus"],
  "stakes": "Mara starts to believe the dungeon's comfort may be sincere.",
  "completion_effect": "Mara gains a vulnerability tag tied to the dungeon's offers of refuge."
}
```

### Faction clocks

Use for cultists, rival delvers, goblin scavengers, dungeon servants, or
institutional forces.

```json
{
  "slug": "cult-opens-inner-gate",
  "label": "The Cult Opens the Inner Gate",
  "segments": 8,
  "category": "faction_pressure",
  "clock_level": "faction",
  "owner_actor_slug": "cult-remnant",
  "action_tags": ["fight", "move", "study", "channel"],
  "stakes": "The cult remnant advances its own ritual while the party is distracted.",
  "completion_effect": "A sealed path opens for the cult, releasing a new threat into the dungeon."
}
```

---

## TDD

### Phase 35.5 slices (existing)

Tests in `tests/unit/rpg/test_world_reaction.py`:

1. **Room match** — clock with `scope_room_id="room_a"` advances when `current_room_id="room_a"`.
2. **Room mismatch** — same clock does not advance when `current_room_id="room_b"`.
3. **Global clock** — clock with `scope_room_id=None` advances regardless of `current_room_id`.
4. **Action tag match** — clock with `action_tags=["sense"]` advances on a SENSE miss.
5. **Action tag mismatch** — same clock does not advance on a FIGHT miss.
6. **No action tags** — clock with `action_tags=[]` advances on any action.
7. **Composed filters** — clock with both scope and action_tags only advances when both conditions are satisfied.
8. **`apply_seed_pack` sets scope** — after applying a seed pack with a room threat that links a clock slug to a location, `get_clocks` returns that clock with the correct `scope_room_id` and `action_tags`.

### Model tests

- `ClockState` defaults `clock_level` to `dungeon`.
- `ClockState` accepts all valid clock levels.
- Invalid clock level is rejected.
- `ClockState` stores `stakes` and `completion_effect`.

### Repository tests

- `save_clock()` persists all new metadata.
- `get_clocks()` returns all new metadata.
- `update_clock_progress()` changes only `filled/status` and preserves scope/category/stakes.
- `update_clock_scope()` does not erase clock level/category/stakes.

### Seed pack tests

- `SeedClock` parses `clock_level`, `scope_room_id`, `level_id`, `owner_actor_slug`, `stakes`, and `completion_effect`.
- Applying seed pack derives `owner_actor_id` from `owner_actor_slug`.
- Applying seed pack preserves room threat scoping.
- Applying seed pack is idempotent with upgraded clocks.
- Existing campaign seed files validate against the upgraded schema.

### World reaction tests

- Room clock advances only in matching room.
- Level clock with no `scope_room_id` can advance from any room on the same campaign.
- Action tags still filter level/dungeon/quest clocks.
- Scoped room clock metadata survives after reaction persistence.

### Integration tests

- Seed upgraded campaign → run action in scoped room → only matching room clock advances.
- Seed upgraded campaign → run action outside scoped room → room clock does not advance but eligible dungeon/level clock may.
- After reaction, context bundle includes upgraded clock metadata.
- Debug controls display level/scope/action information.

---

## Implementation Order

1. Finish Phase 35.5 wiring gaps:
   - `RpgService.react_to_resolution(current_room_id=...)`
   - preserve scope/action tags in `PlayView._apply_world_reaction()`
   - use `update_clock_progress()` or equivalent metadata-safe persistence
2. Add clock-level fields to model, migration, repository, and seed pack.
3. Extend context bundle and debug display.
4. Upgrade existing campaign seed files with real multi-level clocks.
5. Add/extend tests.
6. Run full suite.

---

## Out of Scope

- LLM-created clocks.
- In-game editor for clock metadata.
- Complex clock priority scoring.
- Positive quest-clock advancement on full/critical rolls.
- Separate clock classes.
- Full faction AI.
- Stress track selection by action category (separate balance pass).
- Multi-clock priority logic (advance only the most relevant clock).
- UI for editing clock scope or action tags in-app.
- LLM-proposed scope changes.

---

## Acceptance Criteria

- A clock with a `scope_room_id` set never advances when the player acts in a different room.
- A clock with `action_tags` set never advances from an action not in its list.
- Global clocks (no scope, no tags) advance exactly as before.
- `apply_seed_pack` populates scope and action_tags from `room_threats` data.
- All TDD slices pass.
- Existing test suite stays green.
- Existing no-RPG Play Mode still works.
- At least one clock has `clock_level="room"` and a valid `scope_room_id` per campaign.
- At least one clock has `clock_level="level"` and a valid `level_id` per campaign.
- At least one clock has `clock_level="dungeon"` per campaign.
- At least one clock has `clock_level="quest"` per campaign.
- Character clocks use `owner_actor_slug` that exists in the seed file.
- Faction clocks use `owner_actor_slug` that exists as a faction or dungeon-side actor, or are omitted with a note if no faction exists.
- Every room clock with `scope_room_id` has a matching `room_threats.location_slug`.
- Every clock has `stakes` and `completion_effect`.
- Seed application remains idempotent.
- Context bundle includes upgraded clock metadata.
- Debug tab shows enough metadata to distinguish all clock levels.

---

## Success Definition

A playtest action should now feel context-aware.

Example:

```text
A failed TINKER roll in the Boiler Room advances:
- Boiler Trap Primes                room clock
- The Factory Reawakens             level clock
- Restore the Industrial Elevator   quest clock, if relevant

It does NOT advance:
- A trap in another room
- A SENSE-only mystery clock
- An unrelated faction clock
```

This makes clocks feel like living pressure systems rather than generic failure counters.
