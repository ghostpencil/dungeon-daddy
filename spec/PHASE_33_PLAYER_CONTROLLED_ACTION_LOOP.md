# Phase 33 — Player-Controlled Action Loop

## Status

Ready to implement after Phase 32 closeout.

## Goal

Make the RPG system playable from Play Mode for the first time.

The player controls one or more player-controlled actors. Dungeon Daddy controls the world, monsters, NPCs, dungeon state, secrets, clocks, and consequences.

Phase 33 must let a human tester:

1. Load either existing campaign.
2. Enter Play Mode.
3. Open the RPG panel.
4. Select a player-controlled actor.
5. Enter an action intent.
6. Choose an action key.
7. Resolve the action through `RpgService`.
8. See the mechanical result in the UI.
9. See stress/fallout/clock/memory effects when present.
10. Confirm the live DM response receives a `ContextBundle`.

## Product framing

Avoid naming this permanently as a party-only system.

The correct abstraction is:

```text
player side
  -> one or more player-controlled actors
```

A party campaign is many player-controlled actors. A single-protagonist campaign is one player-controlled actor.

## Required boundaries

- Player-facing UI may select player-controlled actors only.
- Player-facing UI must not directly control NPCs, monsters, dungeon clocks, or world consequences.
- UI panels must not write DuckDB directly.
- `PlayView` orchestrates user intent and service calls.
- `RpgService` resolves mechanical uncertainty.
- `ContextBundleBuilder` builds LLM-ready context.
- `DungeonMasterAgent` consumes context and narrates.
- The LLM does not mutate authoritative state.

## Scope

### 33.1 Actor control model adapter

Add the minimal support needed to distinguish player-controlled actors from dungeon-controlled actors.

Preferred direction:

```text
actor_control:
- player
- dungeon
- system

actor_role:
- protagonist
- party_member
- companion
- npc
- monster
- faction
- dungeon_presence
```

If adding schema fields is too risky for Phase 33, use a compatibility adapter around existing `actor_type`:

```text
pc -> actor_control=player, actor_role=party_member/protagonist
npc -> actor_control=dungeon, actor_role=npc
monster -> actor_control=dungeon, actor_role=monster
dungeon -> actor_control=dungeon, actor_role=dungeon_presence
```

Do not block Phase 33 on a perfect model. The important requirement is that the UI can list controllable actors and exclude dungeon-controlled actors.

### 33.2 Existing campaign RPG seed patch

Add enough seed data to both existing campaigns to test the player action loop.

This may be implemented as a tool or fixture-backed seeder.

Required behavior:

- Supports `--dry-run`.
- Idempotent: running twice must not duplicate actors, stress tracks, clocks, or memories.
- Preserves existing campaign content.
- Works against the current campaign folder layout.
- Prints a clear summary of created/skipped/updated records.

Minimum seed content per campaign:

```text
- campaign row if missing
- session row if missing
- at least one active scene bound to the current level/room when possible
- 1–3 player-controlled actors
- action ratings for all player-controlled actors
- stress tracks for all player-controlled actors
- 1–3 dungeon-controlled actors: NPC, monster, or dungeon presence
- 2–4 open clocks
- 3–6 starter memories
- actor/location/theme tags for retrieval
```

The seeder may choose campaign-appropriate defaults from `setting.md`, `party.md`, `dungeon.json`, and level design docs when available. When uncertain, use generic but thematic defaults and clearly mark them as seed data.

### 33.3 Player Action Panel

Add a new tab or panel in Play Mode. Prefer the label:

```text
ACTION
```

or:

```text
PLAYER
```

Do not label the core system as permanently party-only.

Minimum UI fields:

```text
Controlled Actor: [dropdown/list]
Intent: [text input]
Action: [fight/move/tinker/study/focus/sway/sense/channel/endure]
Optional: Push yourself [toggle]
Optional: Momentum spend [small numeric control]
Resolve Action [button]
```

Minimum result display:

```text
Outcome: miss / partial / full / critical
Dice: [x, y, z]
Stress cost if any
Stress track changes if any
Fallout triggered if any
Clock changes if any
Memory created/updated if any
```

Phase 33 may use a simple layout. Polish is not required.

### 33.4 Live ContextBundle handoff

Wire `ContextBundleBuilder` into `PlayView._spawn_dm_thread`.

Requirements:

- Build a bundle before spawning the DM thread when RPG/memory state is available.
- Pass the bundle into `DungeonMasterAgent.respond(context_bundle=...)`.
- Preserve existing Play Mode behavior when no RPG service/repository/bundle exists.
- Avoid DuckDB writes in the LLM thread.
- Snapshot the bundle on the main thread before starting the LLM thread.
- Store the last bundle in debug controls when available.

### 33.5 Debug provenance display

The Debug tab should show:

```text
- bundle_id
- whether bundle was passed to DM
- retrieved memory count
- omitted/trimmed count
- focus actor IDs
- memory card titles
- active fallout count
- open clock count
```

This must be developer-facing, not player polish.

### 33.6 Smoke test both campaigns

Add or update smoke tooling so Claude captures screenshots after each visible UI-affecting action.

Required smoke flow for each existing campaign:

```text
1. Load campaign.
2. Enter Play Mode.
3. Open RPG panel.
4. Open ACTION/PLAYER tab.
5. Select player-controlled actor.
6. Enter intent.
7. Resolve action.
8. Verify visible result.
9. Open CHAR/SCENE/FALLOUT/MEM/DBG tabs.
10. Verify bundle provenance shown.
11. Send or trigger DM narration.
12. Verify no crash and context bundle handoff indicator is present.
```

## Out of scope

- LLM mutation tools.
- LLM-proposed world reaction drafts.
- Complex monster AI.
- Full memory approval workflow.
- Final UI styling.
- Tactical initiative.
- D&D-style attack/damage system.

## Acceptance criteria

- Both existing campaigns can be patched with RPG seed data.
- Seed operation is dry-run capable and idempotent.
- Player Action UI lists only player-controlled actors.
- Player can resolve at least one action through the UI.
- Result is visible without reading logs.
- Live DM response receives a `ContextBundle` when available.
- Debug tab displays bundle provenance.
- Play Mode still works without RPG state.
- Existing tests pass.
- New tests cover bundle-present and bundle-absent flows.
- UI smoke screenshots are produced after visible UI actions.

## Suggested TDD slices

1. Actor control adapter tests: player-controlled filtering and dungeon-controlled exclusion.
2. Seeder dry-run tests using temp campaign folder.
3. Seeder idempotency tests.
4. Player action request construction tests.
5. PlayView/context bundle snapshot tests.
6. DM agent call receives bundle when available.
7. Debug provenance rendering data tests.
8. UI smoke test after visible integration is stable.

## Claude kickoff prompt

```text
We are implementing Phase 33 only: Player-Controlled Action Loop.

Read the Phase 33 spec and docs/LLM_AUTHORITY_BOUNDARY.md.

Do not implement Phase 34, 35, 36, or 37.
Do not give the LLM mutation tools.
Do not directly control monsters/NPCs from the player UI.
Do not let UI panels write DuckDB directly.

First produce a small TDD slice checklist.
Stop before coding.
```
