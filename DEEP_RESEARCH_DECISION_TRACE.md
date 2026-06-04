# Deep Research Decision Trace — Phase 33–37 Revision

This packet reflects the post-Phase-32 design decision that Dungeon Daddy must become a responsive RPG system without allowing the LLM to directly mutate authoritative state.

## Core decisions captured

### 1. Player authority vs Dungeon Daddy authority

The human player controls the player side: one or more player-controlled actors and the actions they attempt.

Dungeon Daddy controls:
- the dungeon
- monsters
- NPCs
- factions
- external pressure clocks
- hazards
- secrets
- consequences
- narration framing

The design deliberately supports both:
- a single-protagonist campaign
- a multi-character party campaign

A party is treated as one possible configuration of the player side, not as a permanent hardcoded assumption.

### 2. LLM authority boundary

The LLM is advisory. It may narrate, interpret tone, and eventually propose structured world reactions.

The LLM must not directly:
- advance clocks
- apply stress
- create fallout
- change actor state
- create authoritative memory records
- control player intent
- mutate DuckDB or Markdown
- call RPG service mutation methods directly

The principle is:

> The LLM may propose. The engine disposes.

### 3. Deterministic WorldReactionService

The packet introduces Phase 35 around a deterministic `WorldReactionService`.

This service is responsible for turning player choices and RPG action results into concrete world consequences:
- clock advancement
- NPC/monster reactions
- hazards triggering
- fallout hooks
- memory creation requests
- domain events

This is the mechanism that makes the RPG service impactful and responsive while preserving testability.

### 4. LLM proposal model comes later

Phase 36 introduces LLM-proposed reaction drafts only after deterministic world reactions exist.

The LLM proposal path must be:

```text
LLM proposes structured reaction
  -> parser normalizes it
  -> validator checks authority, bounds, existence, and risk
  -> WorldReactionService applies only validated/approved changes
  -> domain events and memory records persist applied truth
  -> LLM narrates the applied truth
```

There are no direct LLM mutation tools in Phase 33, Phase 34, or Phase 35.

### 5. Campaign data must support real playtesting

The archive includes `tools/SEED_RPG_STATE_REQUIREMENTS.md` to ensure the two existing campaigns can be patched with:
- player-controlled actors
- dungeon-controlled actors
- action ratings
- stress tracks
- scene records
- room clocks
- threat clocks
- starter memories
- relationship/bond memories
- seed summaries

The seeding tool must be idempotent and support dry-run mode.

### 6. Player choices must produce visible consequences

The phase plan intentionally moves from visible player action to meaningful world response:

```text
Phase 33: player action UI + live context bundles
Phase 34: richer RPG campaign data
Phase 35: deterministic world reactions
Phase 36: LLM reaction proposals under validation
Phase 37: memory approval + campaign curation
```

This progression is intended to make Dungeon Daddy feel like a real interactive RPG instead of a passive AI narrator.

## Files that implement these decisions

- `README_PHASE_33_37.md`
- `docs/LLM_AUTHORITY_BOUNDARY.md`
- `spec/PHASE_33_PLAYER_CONTROLLED_ACTION_LOOP.md`
- `spec/PHASE_34_CAMPAIGN_RPG_DATA_DEEPENING.md`
- `spec/PHASE_35_WORLD_REACTION_SERVICE.md`
- `spec/PHASE_36_LLM_REACTION_PROPOSALS.md`
- `spec/PHASE_37_MEMORY_APPROVAL_AND_CAMPAIGN_CURATION.md`
- `tests/PHASE_33_37_TEST_PLAN.md`
- `tools/SEED_RPG_STATE_REQUIREMENTS.md`

## Integration stance

Start with Phase 33 only.

Do not ask Claude Code to implement all phases at once.

For each phase:
1. Ask Claude Code to read only the phase file plus directly referenced support files.
2. Ask for a small TDD checklist.
3. Approve one slice at a time.
4. Require screenshots after visible UI effects.
5. Require closeout notes before moving to the next phase.
