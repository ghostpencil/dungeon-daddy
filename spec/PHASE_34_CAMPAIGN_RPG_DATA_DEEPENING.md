# Phase 34 — Campaign RPG Data Deepening

## Goal

Make the two existing campaigns rich enough to meaningfully test Dungeon Daddy's RPG loop.

Phase 33 proves that a player-controlled action can be resolved. Phase 34 makes the campaigns interesting enough that those actions matter.

## Design principle

Campaign seed data should give the RPG engine something to react to.

A good seeded campaign has:

- player-controlled actors with different strengths and weaknesses
- dungeon-controlled NPCs/monsters with motives or instincts
- active clocks that represent pressure
- room-level threat hooks
- memories that shape narration and retrieval
- fallout hooks that let the dungeon exploit prior consequences

## Scope

### 34.1 Campaign seed pack format

Create a readable seed-pack format, preferably JSON or Markdown-with-frontmatter, stored outside core code.

Suggested folder:

```text
seed_data/campaigns/<campaign_slug>/rpg_seed.json
```

Minimum structure:

```json
{
  "campaign_slug": "example",
  "player_side": {
    "label": "The Expedition",
    "actors": []
  },
  "dungeon_side": {
    "actors": []
  },
  "clocks": [],
  "memories": [],
  "room_threats": []
}
```

If a different repo convention is better, use it, but keep seed data readable and reviewable.

### 34.2 Player-controlled actors

Each campaign should have 1–3 player-controlled actors.

Each actor should include:

```text
- stable actor_id or stable slug-derived ID
- display_name
- actor_control=player or compatible pc marker
- actor_role=protagonist/party_member/companion
- concept
- action ratings
- stress tracks
- 1–3 tags
- optional starting relationships/bonds
```

Use distinct action profiles so choices matter.

Example profiles:

```text
- scout/infiltrator: move, sense, tinker
- scholar/occultist: study, focus, channel
- guardian/fighter: fight, endure, sway
```

### 34.3 Dungeon-controlled actors

Each campaign should have 2–5 dungeon-controlled actors.

Types:

```text
- npc
- monster
- faction
- dungeon_presence
```

Each actor should include:

```text
- display_name
- concept
- instinct
- threat tags
- relevant room/location tags
- optional reaction hooks
```

Dungeon-controlled actors are not selectable in the Player Action UI.

### 34.4 Clocks

Each campaign should have 3–6 active clocks.

Clock categories:

```text
- danger clock
- discovery clock
- ritual clock
- pursuit clock
- relationship/dungeon intimacy clock
- faction pressure clock
```

Clocks should be connected to campaign locations or threats when possible.

Examples:

```text
- The Bone Warden Stirs — 6 segments
- The Factory Reawakens — 8 segments
- The Dungeon Learns What Comforts You — 6 segments
- The Cult Opens the Inner Gate — 8 segments
```

### 34.5 Room threat hooks

Add room or location threat hooks so Phase 35 has deterministic reaction inputs.

Suggested fields:

```text
location_slug
trigger_tags
related_actor_ids
related_clock_ids
possible_reactions
notes
```

Example:

```json
{
  "location_slug": "ossuary_gate",
  "trigger_tags": ["noise", "forced_entry", "failed_move"],
  "related_actor_ids": ["monster_bone_warden"],
  "related_clock_ids": ["clock_bone_warden_stirs"],
  "possible_reactions": ["advance_clock", "reveal_threat", "separate_party"]
}
```

### 34.6 Starter memories

Each campaign should have 5–10 starter memories.

Memory types:

```text
- campaign premise
- actor relationship
- location lore
- dungeon emotional tell
- unresolved threat
- prior consequence
```

All starter memories should use controlled tags.

Required tags where relevant:

```text
actor:<role>:<slug>
location:<slug>
theme:<theme>
thread:<thread>
emotion:<emotion>
clock:<clock_slug>
```

### 34.7 Seeder improvements

Upgrade the Phase 33 seeder so it can apply seed packs.

Requirements:

- `--dry-run`
- `--campaign <slug>`
- `--all-existing-campaigns`
- `--seed-pack <path>`
- idempotency by stable IDs/slugs
- create/update/skip summary
- no destructive overwrite unless explicit `--force` is passed

## Out of scope

- WorldReactionService implementation.
- LLM-proposed reactions.
- Full memory approval workflow.
- Deep balancing.

## Acceptance criteria

- Both existing campaigns have RPG seed packs or equivalent data source.
- Both campaigns have at least one player-controlled actor.
- Both campaigns have dungeon-controlled actors.
- Both campaigns have clocks connected to threats.
- Both campaigns have starter memories retrievable by context bundle.
- Seeder can apply seed packs idempotently.
- Player Action UI has meaningful actor choices in seeded campaigns.
- Context bundle includes relevant actor state, memories, clocks, and fallout after seeding.
- Tests cover seed pack parsing, idempotency, and context bundle retrieval.

## Suggested TDD slices

1. Seed pack schema parse test.
2. Stable ID generation test.
3. Apply seed pack to temp campaign DB.
4. Reapply seed pack and verify no duplicates.
5. Verify player-controlled actor filter.
6. Verify dungeon-controlled actors are excluded from player UI.
7. Verify seeded clocks appear in context bundle.
8. Verify seeded memories appear by retrieval rules.
