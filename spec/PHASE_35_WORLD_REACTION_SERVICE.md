# Phase 35 — Deterministic World Reaction Service

**Status: Complete** (2026-06-05) — 1818 unit tests passing. All acceptance criteria met. Post-release bugs tracked in `spec/PROJECT_INDEX.md`.

## Goal

Make Dungeon Daddy respond mechanically to player choices.

Phase 35 introduces a deterministic service that turns player action outcomes into world pressure: monsters react, NPCs respond, clocks advance, hazards trigger, fallout appears, and memories are created.

This is the phase where the RPG service becomes visibly impactful.

## Core rule

The LLM does not apply world reactions.

The deterministic service applies world reactions.

The LLM narrates the applied truth afterward.

## New module

Suggested module:

```text
dungeon_daddy/world/reaction_service.py
```

Alternative acceptable location:

```text
dungeon_daddy/rpg/world_reactions.py
```

Use whichever best fits the repo, but do not put this logic inside `PlayView`, UI panels, or `DungeonMasterAgent`.

## Proposed model types

```python
class WorldReactionInput(BaseModel):
    campaign_id: str
    scene_id: str | None
    location_slug: str | None
    player_actor_id: str
    intent: str
    action_key: str
    resolution_id: str
    outcome: Literal["critical", "full", "partial", "miss"]
    dice_rolled: list[int]
    active_actor_ids: list[str] = []
    tags: list[str] = []

class WorldReactionProposal(BaseModel):
    proposal_id: str
    campaign_id: str
    source: Literal["deterministic", "llm_draft", "debug"]
    source_resolution_id: str
    proposed_changes: list[dict]
    narration_facts: list[str]
    risk_level: Literal["low", "medium", "high"] = "low"

class AppliedWorldReaction(BaseModel):
    reaction_id: str
    campaign_id: str
    source_resolution_id: str
    applied_changes: list[dict]
    domain_event_ids: list[str]
    memory_ids: list[str]
    narration_facts: list[str]
```

Keep first implementation small. Pydantic models are fine, but do not overbuild.

## Reaction change types

Initial supported deterministic changes:

```text
advance_clock
create_memory
apply_stress
trigger_fallout
set_actor_status
add_scene_note
reveal_threat
```

Phase 35 does not need all of these on day one. Start with:

```text
advance_clock
create_memory
apply_stress
```

Then add fallout if existing services make it safe.

## Deterministic reaction rules

Minimum default rules:

```text
critical:
- no negative world reaction by default
- may reduce/complete player-progress clock if present
- may create positive memory if intent was significant

full:
- no negative world reaction by default
- may create memory for significant progress

partial:
- apply one moderate consequence
- typical: advance danger clock by 1 OR apply 1 stress OR reveal threat

miss:
- apply stronger consequence
- typical: advance danger clock by 2 OR apply stress + advance clock OR trigger hazard
```

The service must use campaign data from Phase 34 when available:

- room threat hooks
- related clocks
- related dungeon-controlled actors
- active fallout hooks
- current scene/location
- memory tags

## Consequence selection

For first implementation, consequence selection may be deterministic and simple.

Example priority for partial/miss:

1. If current location has a threat hook with active related clock, advance that clock.
2. Else if actor has a relevant stress track, apply stress based on action category.
3. Else create a memory note describing the complication.
4. Else emit a no-op reaction with a debug warning.

Do not use random monster behavior until deterministic test coverage exists.

## Monster/NPC handling

Monsters and NPCs are dungeon-controlled actors.

They do not need player-style turns.

They react when:

- player rolls a miss
- player rolls a partial success
- a clock fills
- the player ignores an obvious threat
- a location threat hook triggers
- fallout gives the dungeon leverage

NPC/monster reaction should initially be represented through:

```text
- clock movement
- threat revealed
- actor status change
- memory entry
- narration fact
```

Avoid building tactical initiative.

## Integration flow

Correct Phase 35 flow:

```text
Player Action Panel submits intent
  -> RpgService resolves action
  -> WorldReactionService builds deterministic proposal
  -> WorldReactionService validates proposal
  -> WorldReactionService applies proposal through repositories/services
  -> ContextBundleBuilder builds updated context
  -> DungeonMasterAgent narrates applied facts
```

## Debug UI

Add a compact World Reaction section to Debug tab:

```text
Last reaction id
Source: deterministic
Applied changes count
Clock changes
Stress changes
Memory ids created
Rejected changes, if any
```

## Out of scope

- LLM-proposed reactions.
- Direct LLM tools.
- Complex NPC planning.
- Tactical rounds.
- Monster stat blocks.
- Full approval workflow.

## Acceptance criteria

- Partial success causes an appropriate deterministic world reaction.
- Miss causes a stronger deterministic world reaction.
- Reaction changes are persisted through service/repository boundaries.
- Domain events are written for applied changes.
- Context bundle after the reaction includes updated clocks/memories/fallout as appropriate.
- DM narration receives applied facts, not unvalidated guesses.
- Debug tab displays last world reaction summary.
- Tests prove player choices change state.
- Tests prove dungeon-controlled actors are not directly controlled by player UI.
- Existing no-RPG Play Mode still works.

## Suggested TDD slices

1. WorldReactionInput/Proposal model tests.
2. Outcome-to-default-consequence tests.
3. Threat-hook clock advancement test.
4. Apply-stress consequence test.
5. Create-memory consequence test.
6. Validation rejects unknown clock/actor.
7. Integration: action partial -> clock advances -> bundle shows new clock state.
8. Integration: miss -> stress/memory -> DM prompt facts include applied reaction.
