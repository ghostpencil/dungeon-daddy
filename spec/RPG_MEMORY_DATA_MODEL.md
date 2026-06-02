# RPG + Memory Data Model

## Model split

Dungeon Daddy should keep three related but separate model families:

1. Existing dungeon design models.
2. RPG runtime models.
3. Memory models.

Do not overload existing `Room`, `Level`, or `Dungeon` models with runtime RPG state. Existing dungeon JSON should remain human-readable design data.

Runtime state should live in DuckDB and dedicated RPG/memory models.

## Actor model

Actors include:

- player characters
- NPCs
- monsters
- the dungeon as an emotional actor

Suggested fields:

```python
class ActorState(BaseModel):
    actor_id: str
    campaign_id: str
    actor_type: Literal["pc", "npc", "monster", "dungeon"]
    slug: str
    display_name: str
    concept: str | None = None
    status: Literal["active", "inactive", "dead", "absorbed", "lost"] = "active"
    markdown_path: str | None = None
    actions: dict[str, int] = Field(default_factory=dict)
    stress: dict[str, StressTrack] = Field(default_factory=dict)
    abilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
```

## Action keys

Initial action list:

- `fight`
- `move`
- `tinker`
- `study`
- `focus`
- `sway`
- `sense`
- `channel`
- `endure`

Ratings are normally 0–3 for first pass.

## Stress tracks

Player-facing tracks:

- `body`
- `composure`
- `bonds`
- `weird`

NPCs and monsters may use simplified tracks:

- `threat`
- `resistance`
- optional named clocks

## Fallout model

```python
class FalloutRecord(BaseModel):
    fallout_id: str
    campaign_id: str
    actor_id: str
    source_action_id: str | None = None
    track_key: Literal["body", "composure", "bonds", "weird"]
    severity: Literal["minor", "moderate", "severe"]
    title: str
    summary: str
    status: Literal["active", "resolved", "escalated"] = "active"
    mechanical_hooks: dict[str, Any] = Field(default_factory=dict)
    markdown_path: str | None = None
```

## Memory model

A memory record is a database index entry plus a Markdown body.

DuckDB stores:

- ID
- type
- title
- summary
- flattened search text
- status
- importance
- tags
- links
- markdown path and checksum

Markdown stores:

- narrative meaning
- DM-facing notes
- resolution conditions
- emotional interpretation
- event log

## Context bundle model

```python
class ContextBundle(BaseModel):
    bundle_id: str
    campaign_id: str
    scene_id: str | None = None
    mode: Literal["run_scene", "recap", "room_revisit", "fallout_resolution"]
    scene_brief: dict[str, Any]
    mechanical_state: dict[str, Any]
    active_fallout: list[dict[str, Any]]
    open_clocks: list[dict[str, Any]]
    must_remember: list[str]
    memory_cards: list[dict[str, Any]]
    provenance: dict[str, Any]
```

## SQL overview

The SQL files in this archive define:

- campaigns
- sessions
- scenes
- actors
- action ratings
- stress tracks
- abilities
- clocks
- action resolutions
- fallout
- memory entries
- tags
- memory links
- domain events

The schema intentionally treats health as stress tracks and clocks, not hit points.

## Markdown front matter standard

Every memory file must begin with YAML-style front matter.

```md
---
id: fallout_mara_0004
type: fallout
campaign_id: camp_dungeondaddy
subject_ids: [pc_mara]
status: active
severity: moderate
track: weird
tags:
  - actor:pc:mara
  - theme:guilt
  - fallout:moderate
  - track:weird
source_action_id: act_0182
source_scene_id: scn_cathedral_02
updated_at: 2026-06-02T20:15:00Z
---

# Mara dreams in the cathedral's voice

## Summary

Mara accepted comfort from the dungeon and now dreams inside its memories.

## Narrative meaning

The dungeon has learned that solace is a viable route into Mara's defenses.

## Mechanical hooks

- The dungeon gains leverage when offering warmth, refuge, or absolution.

## Resolution

Clear after Mara rejects, redefines, or domesticates that comfort in play.
```

## Tag taxonomy

Use namespaced tags.

Examples:

- `actor:pc:mara`
- `actor:npc:elowen`
- `location:moonlit-cathedral`
- `level:factory-2`
- `theme:guilt`
- `theme:redemption`
- `fallout:active`
- `track:weird`
- `emotion:dungeon-curiosity`
- `thread:find-the-vessel`

Avoid arbitrary ad hoc tags in first pass. Use a small controlled vocabulary and expand only when retrieval requires it.

