# Phase 36 — LLM-Proposed Reaction Drafts

## Goal

Allow the LLM to help draft creative world reactions while preserving deterministic authority.

The LLM may propose structured reaction drafts. The application validates and applies approved/valid changes through `WorldReactionService`.

## Core rule

The LLM never mutates authoritative state directly.

It returns proposals only.

## Why this phase exists

A fully deterministic world reaction service gives safety and testability. But Dungeon Daddy's strongest vision requires reactions that feel emotionally intelligent, context-aware, and specific to the dungeon's tragic personality.

Phase 36 introduces LLM creativity safely:

```text
LLM proposes possible reaction
  -> validator rejects/accepts/sanitizes
  -> deterministic service applies accepted changes
  -> memory/context update
  -> LLM narrates applied truth
```

## Proposal format

Use structured output or a constrained parser. Keep the first version small.

Example:

```json
{
  "narration_hint": "The gate opens, but the sound travels through the bones like a remembered scream.",
  "proposed_changes": [
    {
      "kind": "advance_clock",
      "clock_id": "clock_bone_warden_stirs",
      "amount": 1,
      "reason": "Partial success consequence from noisy gate work"
    },
    {
      "kind": "create_memory",
      "title": "Mara woke the ossuary hinges",
      "summary": "Mara opened the ossuary gate, but the sound alerted something behind the walls.",
      "importance": 5,
      "tags": ["actor:pc:mara", "location:ossuary_gate", "thread:bone_warden"]
    }
  ]
}
```

## Validation requirements

Reject or sanitize proposals that:

- reference unknown actors
- reference unknown clocks
- try to control player actor intent
- apply stress to dungeon-controlled actors using player stress tracks
- exceed allowed tick/stress bounds
- create severe/permanent consequences without permission
- contradict the mechanical outcome
- invent campaign facts not present in context
- write unapproved memory types
- introduce tags outside the controlled taxonomy unless marked as draft

## Source labeling

Every proposal and applied change must record source:

```text
deterministic
llm_draft
human_approved
```

Do not hide LLM influence.

## Human approval policy

Phase 36 may auto-apply low-risk validated proposals, but medium/high-risk proposals should be draft-only unless the UI already supports review.

Suggested default:

```text
low risk: auto-apply after validation
medium risk: record as draft proposal, do not apply yet
high risk: reject or require future approval workflow
```

Examples:

```text
low: create memory, advance existing danger clock by 1
medium: apply stress, reveal hidden NPC, advance clock by 2
high: kill actor, absorb actor, complete major ritual, permanently alter campaign premise
```

## Integration points

The LLM proposal request should include:

- player intent
- action result
- applied deterministic consequences if any
- context bundle
- room/dungeon context
- known clocks
- known NPCs/monsters
- strict schema instructions
- authority boundary reminder

The proposal should be processed on return before any state change.

## Debug UI

Debug tab should show:

```text
Last LLM proposal id
Validation status
Accepted changes
Rejected changes
Reason for rejection
Whether anything was auto-applied
```

## Out of scope

- Direct LLM tools that mutate state.
- Full memory approval UI.
- Complex autonomous NPC planning.
- Multi-step agent loops.

## Acceptance criteria

- LLM proposal parser handles valid structured draft.
- Validator rejects invalid actor/clock references.
- Validator rejects direct player intent control.
- Low-risk accepted proposal can be applied through `WorldReactionService`.
- Medium/high-risk proposal can be stored or displayed as draft without applying.
- Applied changes produce domain events.
- Debug tab exposes proposal provenance.
- Tests cover valid proposal, invalid proposal, partial acceptance, and no-proposal fallback.

## Suggested TDD slices

1. Proposal model parse tests.
2. Validation rejects unknown clock.
3. Validation rejects unknown actor.
4. Validation rejects player actor control.
5. Low-risk create-memory proposal applies.
6. Medium-risk stress proposal remains draft unless explicitly permitted.
7. LLM malformed JSON fallback does not crash Play Mode.
8. Debug provenance includes accepted/rejected proposal summary.

---

## Pre-build notes (reviewed 2026-06-06)

Impact of Phase 35.5 (Clock Scoping) and Phase 35.6 (Stress Routing) on implementation.

### Clock validation must enforce 35.5 scope constraints

`ClockState` now carries `scope_room_id`, `level_id`, `action_tags`, and `clock_level`.
A proposal to advance a clock must be rejected (or auto-rejected as out-of-scope) if:

- `scope_room_id` is set and does not match the current room
- `level_id` is set and does not match the current level
- `action_tags` is non-empty and the resolution's `action_key` is not in the list

The validator should fetch the full `ClockState` from repo and run the same filter
logic used in `compute_world_reaction` before accepting an `advance_clock` proposal.

### `resolution.intent` must be included in the LLM prompt

`ActionResolution.intent` was added in Phase 35.6. The LLM proposal prompt (under
Integration points) should include this field — it is the player's stated purpose and
grounds the LLM's proposed narration and consequence framing.

### Stress proposal validation: use `choose_stress_track()` as the reference

When the LLM proposes `apply_consequence` with an explicit `track_key`:

1. Call `choose_stress_track(action_key, intent, matched_clocks)` to get the
   deterministic result.
2. If the proposed track matches the deterministic result → low-risk, auto-apply.
3. If the proposed track diverges → medium-risk, keep as draft.

`choose_stress_track` already accepts `explicit_track: StressTrackKey | None` — this
is the correct entry point when an approved proposal is applied by the service.

### No structural blockers

35.5 and 35.6 do not break the proposal interface described in `LLM_AUTHORITY_BOUNDARY.md`.
They enrich what the validator must check (clock scope) and what context the LLM receives
(intent). The four proposal kinds (`advance_clock`, `apply_consequence`, `create_memory`,
`npc_reaction`) are unchanged.
