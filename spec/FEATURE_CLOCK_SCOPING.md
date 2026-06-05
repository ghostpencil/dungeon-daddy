# Feature — Clock Scoping: Room-Scoped and Action-Tagged Clocks

## Problem

All active clocks advance on every failed roll, regardless of where the
action took place or what kind of action it was. A SENSE roll in one room
should not advance a clock representing a trap mechanism in a completely
different room. A clock representing a patrol detecting noise should not
advance because a character failed a CHANNEL roll.

## Goal

Make clock advancement contextually meaningful:

1. **Room-scoped clocks** — a clock only advances when the action took place
   in the room (or area) the clock belongs to.
2. **Action-tagged clocks** — a clock only advances when the action key
   matches one of the clock's declared trigger actions.

Global clocks (no scope, no tags) continue to advance on any failure, as
before.

---

## Design

### Filtering rules (compose with AND)

| Clock field | Empty / None | Non-empty |
|---|---|---|
| `scope_room_id` | advances in any room (global) | advances only when `current_room_id` matches |
| `action_tags` | advances for any action | advances only when `resolution.action_key` is in `action_tags` |

A clock must pass **both** filters to advance. Examples:

- `scope_room_id=None, action_tags=[]` → global; ticks on any miss/partial
  (current behaviour, preserved as default)
- `scope_room_id="room_boiler", action_tags=[]` → ticks on any miss/partial
  in the boiler room only
- `scope_room_id=None, action_tags=["sense","study"]` → ticks on a
  sense/study miss anywhere in the dungeon
- `scope_room_id="room_boiler", action_tags=["fight","move"]` → ticks only
  on a fight/move miss inside the boiler room

### Stress tracks unchanged

Stress on miss/partial still applies to the acting actor only (fixed in
Phase 35 bugfix). Stress track selection (body vs composure vs weird) is
**out of scope** for this feature — it belongs in a separate balance pass.

---

## Data model changes

### `ClockState` (models.py)

Add two optional fields:

```python
class ClockState(BaseModel):
    clock_id: str
    campaign_id: str
    label: str
    segments: int
    filled: int = 0
    status: Literal["active", "completed", "abandoned"] = "active"
    scope_room_id: str | None = None       # NEW — None = global
    action_tags: list[str] = Field(default_factory=list)  # NEW — empty = any action
```

### `SeedClock` (seed_pack.py)

```python
class SeedClock(BaseModel):
    slug: str
    label: str
    segments: int
    category: str
    notes: str | None = None
    scope_room_id: str | None = None       # NEW
    action_tags: list[str] = Field(default_factory=list)  # NEW
```

### DB migration — `clocks` table

New migration file in `dungeon_daddy/memory/migrations/`:

```sql
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS scope_room_id TEXT DEFAULT NULL;
ALTER TABLE clocks ADD COLUMN IF NOT EXISTS action_tags TEXT DEFAULT '[]';
```

`action_tags` is stored as a JSON-encoded list string. Existing rows default
to `NULL` / `'[]'`, preserving global-clock behaviour with no data migration
needed.

---

## Repository changes (`memory/repository.py`)

### `save_clock`

Add `scope_room_id` and `action_tags` parameters (both optional, defaulting
to current behaviour):

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
) -> None:
```

Store `action_tags` as `json.dumps(action_tags or [])`.

### `get_clocks`

Add `scope_room_id` and `action_tags` to the SELECT and returned dicts.
Deserialise `action_tags` with `json.loads`.

---

## Seed pack changes (`rpg/seed_pack.py`)

### `apply_seed_pack`

Currently discards `pack.room_threats` entirely. Add a pass that reads
`SeedRoomThreat.related_clock_slugs` and `SeedRoomThreat.trigger_tags` to
backfill `scope_room_id` and `action_tags` on already-saved clocks:

```python
for threat in pack.room_threats:
    for clock_slug in threat.related_clock_slugs:
        clock_id = derive_clock_id(pack.campaign_slug, clock_slug)
        repo.update_clock_scope(
            clock_id,
            scope_room_id=threat.location_slug,
            action_tags=threat.trigger_tags,
        )
```

`location_slug` in `SeedRoomThreat` must match the room `id` in the dungeon
design JSON (the value used in `SessionState.current_room_id`). Verify this
against the seeded campaigns before writing tests.

Add `repo.update_clock_scope(clock_id, scope_room_id, action_tags)` to
`MemoryRepository` as a targeted UPDATE (avoids overwriting filled/status).

---

## `compute_world_reaction` signature change (`rpg/world_reaction.py`)

Add `current_room_id: str | None = None` parameter:

```python
def compute_world_reaction(
    resolution: ActionResolution,
    threat_clocks: list[ClockState],
    pc_actors: list[tuple[ActorState, dict[str, StressTrack]]],
    current_room_id: str | None = None,
) -> WorldReaction:
```

Clock filtering (replace the current `if clock.status != "active": continue`
block with):

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

## Call site changes (`views/play_view.py`)

`_apply_world_reaction` already has access to `self._state.current_room_id`.
Pass it through to `react_to_resolution`:

```python
reaction, _evt = self._rpg_service.react_to_resolution(
    resolution, threat_clocks, pc_pairs,
    current_room_id=self._state.current_room_id,
)
```

`RpgService.react_to_resolution` passes it down to `compute_world_reaction`.

---

## Debug tab update

Add `scope_room_id` and `action_tags` to the clock section lines in
`DebugControls.clock_section_lines()` when they are non-default, e.g.:

```
  [2/6] Heat Rising  (global)
  [0/4] Trap Primed  (room: trap_corridor | actions: sense, study)
```

---

## TDD slices

Write tests in `tests/unit/rpg/test_world_reaction.py`:

1. **Room match** — clock with `scope_room_id="room_a"` advances when
   `current_room_id="room_a"`.
2. **Room mismatch** — same clock does not advance when
   `current_room_id="room_b"`.
3. **Global clock** — clock with `scope_room_id=None` advances regardless of
   `current_room_id`.
4. **Action tag match** — clock with `action_tags=["sense"]` advances on a
   SENSE miss.
5. **Action tag mismatch** — same clock does not advance on a FIGHT miss.
6. **No action tags** — clock with `action_tags=[]` advances on any action.
7. **Composed filters** — clock with both scope and action_tags only advances
   when both conditions are satisfied.
8. **`apply_seed_pack` sets scope** — after applying a seed pack with a room
   threat that links a clock slug to a location, `get_clocks` returns that
   clock with the correct `scope_room_id` and `action_tags`.

---

## Out of scope

- Stress track selection by action category (separate balance pass).
- Multi-clock priority logic (advance only the most relevant clock).
- UI for editing clock scope or action tags in-app.
- LLM-proposed scope changes.

---

## Acceptance criteria

- A clock with a `scope_room_id` set never advances when the player acts in a
  different room.
- A clock with `action_tags` set never advances from an action not in its list.
- Global clocks (no scope, no tags) advance exactly as before.
- `apply_seed_pack` populates scope and action_tags from `room_threats` data.
- All 8 TDD slices pass.
- Existing test suite stays green.
- Existing no-RPG Play Mode still works.
