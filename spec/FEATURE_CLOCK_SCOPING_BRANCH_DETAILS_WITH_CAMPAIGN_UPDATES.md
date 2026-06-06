# Feature Enhancement — Clock Scoping, Clock Levels, and Campaign Seed Upgrades

## Branch Context

Use branch:

```text
phase-35.5-clock-scoping
```

This feature builds on the current branch implementation, not `main`.

The branch already includes:

- `ClockState.scope_room_id`
- `ClockState.action_tags`
- migration `004_clock_scoping.sql`
- repository persistence for scoped clocks
- seed-pack room threat backfill into clock scope
- deterministic world reaction filtering by room and action tags
- unit tests for room/action clock filtering

The next enhancement should **finish the existing branch wiring** and then **upgrade campaign seed files so the richer clock model is actually exercised in play**.

---

## Problem

The current branch adds useful first-pass scoping, but it only models one level of scope:

```text
scope_room_id: Optional[str]
action_tags: list[str]
```

That is enough to prevent a trap clock in one room from advancing because of an unrelated action elsewhere. However, Dungeon Daddy needs clocks at multiple narrative scales:

```text
Room clocks
Level clocks
Dungeon clocks
Quest / Plot clocks
Character clocks
Faction clocks
```

Without upgrading the campaign seed files, the feature will exist mostly as infrastructure. Playtests need real seeded clocks that demonstrate how different clock levels behave.

---

## Goals

1. Preserve the existing Phase 35.5 behavior.
2. Finish the missing branch wiring so scoped clocks work in the actual PlayView action loop.
3. Add explicit clock-level metadata to seeded clocks.
4. Upgrade existing campaign seed files with representative clocks at multiple levels.
5. Ensure context bundles, debug UI, and world reactions expose enough clock metadata for the DM prompt and developer debugging.
6. Keep this deterministic. The LLM narrates clock consequences; it does not decide which clock advances.

---

## Current Branch Findings

### Already implemented

`ClockState` now has:

```python
scope_room_id: str | None = None
action_tags: list[str] = Field(default_factory=list)
```

`MemoryRepository.save_clock()` persists both fields, `update_clock_scope()` can update them without overwriting progress/status, and `get_clocks()` returns them.

`compute_world_reaction()` accepts `current_room_id` and filters clocks:

```python
if clock.scope_room_id is not None and clock.scope_room_id != current_room_id:
    continue
if clock.action_tags and resolution.action_key not in clock.action_tags:
    continue
```

`apply_seed_pack()` already walks `room_threats` and calls `update_clock_scope()` for related clocks.

### Important gaps

1. `RpgService.react_to_resolution()` does not accept/pass `current_room_id` yet.
2. `PlayView._apply_world_reaction()` reconstructs `ClockState` without `scope_room_id` and `action_tags`.
3. `PlayView._apply_world_reaction()` saves advanced clocks without preserving scope metadata, which can erase scope fields because `save_clock()` updates them on conflict.
4. Debug clock display still does not show scope/action metadata.
5. Seed clocks still only have `category`; they do not yet have explicit clock level/scope such as `room`, `level`, `dungeon`, `quest`, `character`, or `faction`.
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

## Proposed Data Model Enhancement

### `ClockState`

Keep existing fields and add a minimal explicit level field:

```python
class ClockState(BaseModel):
    clock_id: str
    campaign_id: str
    label: str
    segments: int
    filled: int = 0
    status: Literal["active", "completed", "abandoned"] = "active"

    # Existing Phase 35.5 fields
    scope_room_id: str | None = None
    action_tags: list[str] = Field(default_factory=list)

    # New fields
    clock_level: Literal["room", "level", "dungeon", "quest", "character", "faction"] = "dungeon"
    category: str | None = None
    level_id: str | None = None
    owner_actor_id: str | None = None
    stakes: str | None = None
    completion_effect: str | None = None
    visible_to_player: bool = True
```

### Why this shape?

This avoids separate classes while giving the engine enough information to reason about where a clock lives.

`scope_room_id` remains the precise room filter.

`clock_level` answers the broader question:

```text
Is this pressure local, level-wide, dungeon-wide, quest-focused, personal, or faction-driven?
```

---

## Seed Pack Enhancement

### `SeedClock`

Extend `SeedClock`:

```python
class SeedClock(BaseModel):
    slug: str
    label: str
    segments: int
    category: str
    notes: str | None = None

    # Existing / branch-compatible fields
    scope_room_id: str | None = None
    action_tags: list[str] = Field(default_factory=list)

    # New fields
    clock_level: Literal["room", "level", "dungeon", "quest", "character", "faction"] = "dungeon"
    level_id: str | None = None
    owner_actor_slug: str | None = None
    stakes: str | None = None
    completion_effect: str | None = None
    visible_to_player: bool = True
```

### Apply seed pack rules

`apply_seed_pack()` should save all new clock metadata.

If `owner_actor_slug` is supplied, derive the stable actor id:

```python
owner_actor_id = derive_actor_id(pack.campaign_slug, clock.owner_actor_slug)
```

Then pass it to `repo.save_clock()`.

Room threat backfill should continue to work. If a `room_threat` references a clock, it may overwrite or fill in `scope_room_id` and `action_tags`, but it should not erase the clock's broader `clock_level`, `category`, `stakes`, or `completion_effect`.

---

## Migration Enhancement

Add a new migration after `004_clock_scoping.sql`, for example:

```text
dungeon_daddy/data/migrations/005_clock_levels.sql
```

Suggested SQL:

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

## Repository Enhancement

Update `MemoryRepository.save_clock()` to accept and persist:

```python
clock_level: str = "dungeon"
category: str | None = None
level_id: str | None = None
owner_actor_id: str | None = None
stakes: str | None = None
completion_effect: str | None = None
visible_to_player: bool = True
```

Important: when `save_clock()` is used only to update progress, it must **not accidentally erase metadata**.

Two acceptable approaches:

### Preferred approach

Add a separate method:

```python
def update_clock_progress(
    self,
    clock_id: str,
    filled: int,
    status: str,
) -> None:
    ...
```

Then PlayView/world reaction persistence should call `update_clock_progress()` instead of `save_clock()`.

### Acceptable fallback

Ensure all callers reconstruct and pass full metadata when calling `save_clock()`.

Preferred is safer because it prevents future metadata loss.

---

## World Reaction Wiring Fixes

### `RpgService.react_to_resolution()`

Current branch has `compute_world_reaction(..., current_room_id=None)` but `RpgService.react_to_resolution()` does not expose it.

Change signature:

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

### `PlayView._apply_world_reaction()`

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

Pass current room:

```python
reaction, _evt = self._rpg_service.react_to_resolution(
    resolution,
    threat_clocks,
    pc_pairs,
    current_room_id=self._state.current_room_id if self._state else None,
)
```

When persisting reaction clock changes, use `update_clock_progress()` so metadata survives.

---

## Campaign File Enhancement Instructions

This is a required part of the feature.

Upgrade every existing campaign seed file, likely under:

```text
seed_data/campaigns/<campaign_slug>/rpg_seed.json
```

If the repo uses a different campaign seed folder, locate all seed packs consumed by `tools/seed_rpg_state.py` and update those files instead.

### Minimum campaign upgrade requirement

Each existing campaign should include at least:

```text
2 room clocks
1 level clock
1 dungeon clock
1 quest/plot clock
1 character clock, if the campaign has a named PC
1 faction clock, if the campaign has a faction or cult actor
```

If a campaign does not currently have a faction actor, either:

1. skip the faction clock for that campaign, or
2. add a lightweight dungeon-side faction actor if it fits the seed.

Do not add meaningless clocks just to satisfy a count. Each clock must have a clear fictional consequence.

---

## Clock Design Rules for Campaign Files

### Room clocks

Use for local hazards, traps, monsters waking up, room-specific investigations, or immediate scene pressure.

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

### Level clocks

Use for floor-wide escalation: security alert, factory awakening, level flooding, library rearranging, patrol mobilization.

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

Level clocks generally should not have `scope_room_id` unless they are only triggered from one specific control room.

### Dungeon clocks

Use for the entity's long-term understanding, intimacy, possessiveness, architecture changes, or dungeon-wide awakening.

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

Dungeon clocks are ideal companions to Weird stress and dungeon intimacy mechanics.

### Quest / Plot clocks

Use for player-facing objectives.

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

Quest clocks may advance positively on full/critical successes later, but for this pass they can still be displayed and tracked even if deterministic positive advancement is deferred.

### Character clocks

Use for personal arcs, trust, corruption, fear, obsession, injury recovery, or dependency on the dungeon.

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

Character clocks should have `owner_actor_slug` in seed files and become `owner_actor_id` in persisted state.

### Faction clocks

Use for cultists, rival delvers, goblin scavengers, dungeon servants, or institutional forces.

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

## Campaign Upgrade Acceptance Criteria

For each existing campaign seed file:

- At least one clock has `clock_level="room"` and a valid `scope_room_id`.
- At least one clock has `clock_level="level"` and a valid `level_id` where level ids/slugs exist.
- At least one clock has `clock_level="dungeon"`.
- At least one clock has `clock_level="quest"`.
- Character clocks use `owner_actor_slug` that exists in the seed file.
- Faction clocks use `owner_actor_slug` that exists as a faction or dungeon-side actor, or are omitted with a comment/note in the spec if no faction exists.
- Every room clock with `scope_room_id` has a matching `room_threats.location_slug` or an explicit reason why it does not.
- Every clock has `stakes` and `completion_effect`.
- Seed application remains idempotent.
- Context bundle includes the upgraded clock metadata.
- Debug tab shows enough metadata to distinguish room, level, dungeon, quest, character, and faction clocks.

---

## Debug UI Enhancement

Update `DebugControls.clock_section_lines()` so clocks display scope and level metadata.

Suggested output:

```text
Clocks: 6 active
  [1/4] Boiler Trap Primes {room:boiler_room | danger | actions: move,tinker}
  [3/8] The Factory Reawakens {level:level_2 | danger}
  [2/8] The Dungeon Learns What Comforts You {dungeon | intimacy | actions: sense,sway,channel}
  [0/6] Restore the Industrial Elevator {quest | objective}
  [1/6] Mara Begins to Trust the Dungeon {character:mara | relationship}
```

Do not over-invest in UI polish. This is a debug visibility feature.

---

## Context Bundle Enhancement

`ContextBundleBuilder` should preserve clock metadata from `MemoryRepository.get_clocks()` in `open_clocks`.

The DM prompt should receive enough clock information to narrate consequences:

```text
- label
- filled / segments
- clock_level
- category
- scope_room_id / level_id / owner_actor_id when present
- stakes
- completion_effect
```

This matters because the LLM should narrate what the clock means, not just that it is `3/8` full.

---

## TDD Additions

Add tests beyond the existing Phase 35.5 slices.

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

## Out of Scope

Do not implement these yet:

- LLM-created clocks.
- In-game editor for clock metadata.
- Complex clock priority scoring.
- Positive quest-clock advancement on full/critical rolls, unless already trivial.
- Separate clock classes.
- Full faction AI.

---

## Final Implementation Order

1. Finish Phase 35.5 wiring gaps:
   - `RpgService.react_to_resolution(current_room_id=...)`
   - preserve scope/action tags in `PlayView._apply_world_reaction()`
   - use `update_clock_progress()` or equivalent metadata-safe persistence
2. Add clock-level fields to model, migration, repository, and seed pack.
3. Extend context bundle/debug display.
4. Upgrade existing campaign seed files with real multi-level clocks.
5. Add/extend tests.
6. Run full suite.

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
