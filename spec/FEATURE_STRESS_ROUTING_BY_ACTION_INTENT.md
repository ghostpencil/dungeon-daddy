# Feature Enhancement — Stress Routing by Action, Intent, Threat, and Clock Context

> **Status: Complete — Phase 35.6 (2026-06-06)**
> 1738 unit tests passing. All acceptance criteria met.

## Purpose

Dungeon Daddy currently applies world-reaction stress to the acting character, but it defaults that stress to `body` for every miss or partial consequence. That is mechanically safe but dramatically too narrow.

This feature teaches the deterministic world reaction layer to route stress to the appropriate track:

- `body` for physical danger, harm, exhaustion, poison, traps, combat, and environmental punishment.
- `composure` for fear, panic, shame, grief, horror, psychic pressure, intimidation, and emotional destabilization.
- `bonds` for betrayal, isolation, rejection, dependency, social fracture, and relationship pressure.
- `weird` for magic, visions, dungeon intimacy, memory bleed, alien influence, occult contact, and the dungeon's seductive/alluring pressure.

The LLM may narrate the result, but it must not decide the mechanical stress track. The deterministic rules must choose the track first.

---

## Current Repo State

The current `ClockState` already has rich clock metadata:

```python
scope_room_id: str | None
_action_tags: list[str]
clock_level: Literal["room", "level", "dungeon", "quest", "character", "faction"]
category: str | None
level_id: str | None
owner_actor_id: str | None
stakes: str | None
completion_effect: str | None
visible_to_player: bool
```

The seed pack format also supports clock metadata including `clock_level`, `category`, `level_id`, `owner_actor_slug`, `stakes`, and `completion_effect`.

The world reaction service already filters clocks by:

- current room
- current level
- action tags
- active status

However, stress routing is still hard-coded to `body` inside `compute_world_reaction()`:

```python
track = tracks.get("body", StressTrack(track_key="body"))
...
track_key="body"
```

This feature replaces that hard-coded default with deterministic stress-track selection.

---

## Design Principle

Stress track selection should follow this priority order:

1. Explicit stress track declared by a matched room threat or matched clock.
2. Clock category / clock level mapping.
3. Action key mapping.
4. Intent keyword mapping.
5. Fallback to `body`.

This keeps the system deterministic while allowing campaign-specific authoring to override generic defaults.

---

## Recommended First Implementation

### 1. Add `intent` to `ActionResolution`

Current `ActionRequest` captures action intent indirectly through the player action panel, but `ActionResolution` does not retain it.

Add:

```python
class ActionResolution(BaseModel):
    ...
    intent: str | None = None
```

Update `resolve_action()` so the resulting `ActionResolution` receives the request intent if available.

If `ActionRequest` does not currently expose `intent`, add it there too:

```python
class ActionRequest(BaseModel):
    ...
    intent: str | None = None
```

Then update the request builder in the player action UI to populate it from the submitted intent text.

### Acceptance

- Action intent survives from UI request construction into `ActionResolution`.
- Existing tests without intent still pass because the field defaults to `None`.

---

### 2. Add stress routing helper module

Create:

```text
dungeon_daddy/rpg/stress_routing.py
```

Suggested API:

```python
from typing import Literal

StressTrackKey = Literal["body", "composure", "bonds", "weird"]


def choose_stress_track(
    *,
    action_key: str,
    intent: str | None = None,
    matched_clocks: list[ClockState] | None = None,
    explicit_track: StressTrackKey | None = None,
) -> StressTrackKey:
    ...
```

Keep this module pure and easy to unit test.

Do not put this logic in `PlayView`, `DungeonMasterAgent`, or UI classes.

---

## Routing Rules

### Explicit override

If an explicit valid stress track is supplied, use it.

```text
explicit_track="weird" -> weird
```

This is for future room threat hooks or explicit campaign data.

---

### Clock category mapping

When a consequence advances one or more clocks, use the most relevant matched clock category to infer stress.

Suggested category mapping:

```python
_CLOCK_CATEGORY_TO_STRESS = {
    # Body
    "danger": "body",
    "hazard": "body",
    "pursuit": "body",
    "boss": "body",
    "escape": "body",

    # Composure
    "horror": "composure",
    "fear": "composure",
    "dread": "composure",
    "despair": "composure",
    "panic": "composure",

    # Bonds
    "relationship": "bonds",
    "betrayal": "bonds",
    "dependency": "bonds",
    "isolation": "bonds",
    "faction_pressure": "bonds",

    # Weird
    "ritual": "weird",
    "occult": "weird",
    "magic": "weird",
    "dungeon_intimacy": "weird",
    "allure": "weird",
    "memory_bleed": "weird",
    "transformation": "weird",
}
```

### Clock level mapping

Clock level should be a weaker signal than category. Use it only when category does not resolve a track.

Suggested mapping:

```python
_CLOCK_LEVEL_TO_STRESS = {
    "room": "body",
    "level": "body",
    "dungeon": "weird",
    "quest": "composure",
    "character": "bonds",
    "faction": "bonds",
}
```

Dungeon-level clocks should often route to `weird` because they represent the dungeon as an entity learning, changing, or exerting influence.

---

### Action key mapping

Use the existing action system:

```python
_ACTION_TO_STRESS = {
    "fight": "body",
    "move": "body",
    "endure": "body",
    "tinker": "body",

    "study": "composure",
    "focus": "composure",
    "sense": "composure",

    "sway": "bonds",

    "channel": "weird",
}
```

Notes:

- `tinker` defaults to `body` because failed machine work tends to produce physical danger first.
- `study`, `sense`, and `focus` default to `composure` unless a clock/category indicates `weird`.
- `channel` defaults to `weird`.
- `sway` defaults to `bonds` because failed social/emotional action should damage trust, connection, or dependency.

---

### Intent keyword mapping

Intent text should be used only after clock/category/action rules fail or when the action is ambiguous.

Suggested keyword groups:

```python
_BODY_KEYWORDS = {
    "attack", "fight", "strike", "hit", "block", "run", "jump", "climb",
    "dodge", "force", "break", "lift", "push", "carry", "poison", "wound",
    "pain", "blood", "trap", "fire", "steam", "acid", "fall"
}

_COMPOSURE_KEYWORDS = {
    "fear", "panic", "terror", "horror", "shame", "guilt", "grief",
    "despair", "nightmare", "memory", "regret", "truth", "confess",
    "focus", "calm", "resist"
}

_BONDS_KEYWORDS = {
    "trust", "betray", "comfort", "reject", "abandon", "protect", "promise",
    "friend", "ally", "love", "dependency", "help", "isolate", "relationship",
    "forgive", "convince", "deceive"
}

_WEIRD_KEYWORDS = {
    "dungeon", "vision", "ritual", "magic", "spell", "spirit", "ghost",
    "dream", "voice", "whisper", "allure", "comfort", "intimacy", "claim",
    "absorb", "transform", "memory bleed", "channel", "entity", "alien"
}
```

If multiple groups match, prefer this order:

```text
weird > bonds > composure > body
```

Reason: physical danger is the generic fallback. Weird/Bonds/Composure should win when the player’s intent clearly points there.

---

## Integration with `compute_world_reaction()`

Current `compute_world_reaction()` builds `clock_lines` first, then applies stress to the acting actor.

Modify it to keep track of the clocks that actually matched and produced clock consequences.

Pseudo-code:

```python
matched_clocks: list[ClockState] = []

for clock in threat_clocks:
    if clock.status != "active":
        continue
    if clock.scope_room_id is not None and clock.scope_room_id != current_room_id:
        continue
    if clock.level_id is not None and current_level_id is not None and clock.level_id != current_level_id:
        continue
    if clock.action_tags and resolution.action_key not in clock.action_tags:
        continue

    if clock_ticks != 0:
        matched_clocks.append(clock)
        clock_lines.append(...)
```

Then choose stress track:

```python
track_key = choose_stress_track(
    action_key=resolution.action_key,
    intent=resolution.intent,
    matched_clocks=matched_clocks,
)
track = tracks.get(track_key, StressTrack(track_key=track_key))
```

Then emit:

```python
ReactionStressLine(
    actor_id=actor.actor_id,
    display_name=actor.display_name,
    track_key=track_key,
    amount=stress_amount,
    new_filled=new_filled,
    triggered_fallout=triggered_fallout,
    reason=f"{outcome} consequence — {track_key}",
)
```

### Important

Only the acting actor takes stress by default. Preserve the existing behavior that prevents the whole party from taking stress on every miss/partial.

---

## Persistence / PlayView Fix

`PlayView._apply_world_reaction()` currently persists stress using `sl.track_key`, but it looks up capacity through `tracks["body"].capacity`.

Replace this logic with a lookup for the actual stress line track:

```python
capacity=next(
    (
        tracks[sl.track_key].capacity
        for actor, tracks in pc_pairs
        if actor.actor_id == sl.actor_id and sl.track_key in tracks
    ),
    4,
)
```

Do not assume Body capacity when persisting Composure, Bonds, or Weird.

---

## Seed / Campaign Data Enhancement

Do not require campaign files to explicitly declare stress routing in the first pass. The current clock `category`, `clock_level`, and `action_tags` are enough to infer good defaults.

However, update the campaign seed guidelines to prefer categories that clearly imply stress consequences.

Examples:

```json
{
  "slug": "the-dungeon-learns-what-comforts-you",
  "label": "The Dungeon Learns What Comforts You",
  "segments": 6,
  "category": "dungeon_intimacy",
  "clock_level": "dungeon",
  "action_tags": ["sense", "sway", "channel", "focus"],
  "stakes": "The dungeon develops an eerie emotional awareness of the party.",
  "completion_effect": "The dungeon begins offering personalized refuge that comforts and compromises the characters."
}
```

This should route stress toward `weird` because `dungeon_intimacy` is mapped to Weird.

```json
{
  "slug": "dax-remembers-the-truth",
  "label": "Dax Remembers the Truth",
  "segments": 6,
  "category": "relationship",
  "clock_level": "character",
  "owner_actor_slug": "dax",
  "action_tags": ["sense", "move", "study"],
  "stakes": "Fragments of Dax's previous expedition surface unbidden.",
  "completion_effect": "Dax remembers abandoning his companions."
}
```

This should route stress toward `bonds` if category wins, or `composure` if the implementation chooses action-first. The recommended implementation is category-first, so it routes to `bonds`.

---

## Testing Plan

### New unit test file

Create or extend:

```text
tests/unit/rpg/test_stress_routing.py
```

Tests:

1. `fight` miss defaults to `body`.
2. `move` miss defaults to `body`.
3. `sense` miss defaults to `composure` when no clock context exists.
4. `sway` miss defaults to `bonds`.
5. `channel` miss defaults to `weird`.
6. `dungeon_intimacy` clock routes stress to `weird`.
7. `relationship` clock routes stress to `bonds`.
8. `ritual` clock routes stress to `weird`.
9. `danger` clock routes stress to `body`.
10. Intent containing "comfort" and "dungeon" routes to `weird` when no stronger clock category exists.
11. Intent containing "trust" or "betray" routes to `bonds`.
12. Unknown action and no intent fallback routes to `body`.

### Extend world reaction tests

In `tests/unit/rpg/test_world_reaction.py`, add tests:

1. Miss on `channel` applies Weird stress.
2. Partial on `sway` applies Bonds stress.
3. Miss on `sense` with a `dungeon_intimacy` matched clock applies Weird stress.
4. Miss on `fight` with a `relationship` matched clock applies Bonds stress if category has priority.
5. Stress overflow clamps and flags fallout on non-Body tracks.
6. Only the acting actor takes non-Body stress.

### Extend PlayView/unit integration tests

Add/adjust a test proving:

- A `ReactionStressLine(track_key="weird")` persists to the Weird track, not Body.
- Capacity is read from the same track being updated.

---

## Acceptance Criteria

- World reactions no longer hard-code Body stress for all miss/partial consequences.
- Stress track selection is deterministic and unit-tested.
- Existing Body stress behavior remains the fallback.
- `fight`, `move`, and `endure` still usually create Body stress.
- `sway` can create Bonds stress.
- `channel` can create Weird stress.
- `sense`, `study`, and `focus` can create Composure stress unless clock/category context points elsewhere.
- Dungeon intimacy/allure clocks create Weird stress.
- Relationship/dependency clocks create Bonds stress.
- Horror/fear/despair clocks create Composure stress.
- PlayView persists the correct track and capacity.
- Existing clock scoping, clock levels, and world reaction tests remain green.
- Existing no-RPG Play Mode still works.

---

## Out of Scope

- LLM-proposed stress routing.
- Applying stress to multiple party members from one action.
- Advanced stress amount balancing by track.
- Automatic fallout creation/resolution changes.
- UI for manually selecting stress tracks.
- Full room-threat schema changes for explicit stress routing.

These can come later.

---

## Suggested TDD Slices

1. Add `intent` to `ActionRequest` and `ActionResolution`; update tests.
2. Add `stress_routing.py` with action-key mapping only.
3. Update `compute_world_reaction()` to use `choose_stress_track()`.
4. Add clock category/level routing.
5. Add intent keyword routing.
6. Fix PlayView persistence to use `sl.track_key` capacity lookup.
7. Add world reaction tests for non-Body stress.
8. Run full test suite.

