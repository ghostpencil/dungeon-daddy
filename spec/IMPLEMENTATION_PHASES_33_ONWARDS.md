# Implementation Phases — 33 Onwards (Active Play Loop + Future Roadmap)

## Phase 33 â€” Player-Controlled Action Loop âœ“ Complete (2026-06-04, 1761 passing)

Make the RPG loop visible and playable in Play Mode.

Major work:

- Seed both existing campaigns with minimal RPG-ready data.
- Add player-controlled actor filtering.
- Add Player Action panel.
- Resolve actions through `RpgService`.
- Show results, stress, clocks, fallout, and memory indicators.
- Pass `ContextBundle` into live DM narration.
- Add Debug bundle provenance display.

## Phase 34 â€” Campaign RPG Data Deepening

**Status: Complete (2026-06-05) â€” 1802 passing**

Make the existing campaigns meaningful RPG testbeds. Phase 33 proved a player action can be resolved; Phase 34 makes the campaigns interesting enough that those actions matter.

Spec: `spec/PHASE_34_CAMPAIGN_RPG_DATA_DEEPENING.md`

### Modules

| Module / File | Notes |
|---|---|
| `seed_data/campaigns/<slug>/rpg_seed.json` (new) | Readable seed-pack format per campaign |
| `dungeon_daddy/rpg/seed_pack.py` (new) | Seed-pack schema (Pydantic), parser, stable ID derivation |
| `tools/seed_rpg_state.py` (update) | Apply seed packs; `--dry-run`, `--seed-pack`, `--all-existing-campaigns`, `--force` |
| `tests/unit/rpg/test_seed_pack.py` (new) | Schema parse, stable ID, idempotency, actor filtering |
| `tests/integration/test_seed_pack_integration.py` (new) | Apply + re-apply to temp campaign DB; context bundle retrieval |

### Implementation Steps

| Step | Task | Status |
|---|---|---|
| 34-1 | Seed-pack schema (`rpg_seed.py`): Pydantic models for `PlayerActor`, `DungeonActor`, `SeedClock`, `RoomThreat`, `StarterMemory`; parse + validate from JSON | Complete |
| 34-2 | Stable ID derivation: deterministic `actor_id` / `clock_id` from campaign slug + name slug | Complete |
| 34-3 | Apply seed pack to campaign DB: insert/update actors, clocks, memories; idempotent by stable ID | Complete |
| 34-4 | Seeder CLI upgrade: `--dry-run`, `--campaign`, `--all-existing-campaigns`, `--seed-pack`, `--force`; create/update/skip summary | Complete |
| 34-5 | Write seed packs for both existing campaigns (player actors, dungeon actors, clocks, room threats, starter memories) | Complete |
| 34-6 | Verify player-controlled actor filter and dungeon-actor exclusion from Player Action UI | Complete |
| 34-7 | Verify seeded clocks and memories appear in context bundle | Complete |

### TDD Slices

1. Seed pack schema parse test.
2. Stable ID generation test.
3. Apply seed pack to temp campaign DB.
4. Re-apply seed pack; verify no duplicates.
5. Player-controlled actor filter test.
6. Dungeon-controlled actors excluded from player UI.
7. Seeded clocks appear in context bundle.
8. Seeded memories appear by retrieval rules.

### Exit Criteria

- [x] Both existing campaigns have RPG seed packs in `seed_data/campaigns/<slug>/rpg_seed.json`
- [x] Both campaigns have at least one player-controlled actor
- [x] Both campaigns have dungeon-controlled actors (NPCs/monsters)
- [x] Both campaigns have 3â€“6 clocks connected to threats
- [x] Both campaigns have 5â€“10 starter memories retrievable by context bundle
- [x] Seeder applies seed packs idempotently (`--dry-run` + `--force` both work)
- [x] Player Action UI shows meaningful actor choices after seeding
- [x] Context bundle includes actor state, memories, clocks, and fallout after seeding
- [x] Tests cover schema parse, stable ID, idempotency, and context bundle retrieval
- [x] `pytest tests/unit/` + `tests/integration/` green

## Phase 35 â€” Deterministic World Reaction Service

**Status: Complete** (2026-06-05) â€” 1818 unit tests passing.

Make the dungeon push back through deterministic state changes.

Major work:

- Add `WorldReactionService`.
- Map action outcomes to consequences.
- Use threat hooks and clocks.
- Apply clock/stress/memory changes through repositories/services.
- Write domain events.
- Update context bundle after reactions.
- Show reaction summary in Debug tab.

Full spec: `spec/PHASE_35_WORLD_REACTION_SERVICE.md`

## Phase 35.5 â€” Clock Scoping

**Status: Complete** (2026-06-06) â€” 1698 unit tests passing. All 10 manual UI behavior tests passing.

Make clock advancement contextually meaningful so clocks only tick when
the triggering action is relevant to them.

Major work:

- Add `scope_room_id` and `action_tags` fields to `ClockState` and `SeedClock`.
- DB migration: add `scope_room_id` and `action_tags` columns to the `clocks` table.
- Update `save_clock` / `get_clocks` in `MemoryRepository` to persist and load new fields.
- Add `update_clock_scope` to `MemoryRepository` for targeted scope backfill.
- Update `apply_seed_pack` to read `room_threats` and set scope/action_tags on saved clocks.
- Add `current_room_id` parameter to `compute_world_reaction`; apply room + action filters before ticking.
- Pass `current_room_id` through `RpgService.react_to_resolution` from `PlayView`.
- Show `scope_room_id` and `action_tags` in Debug tab clock section when non-default.
- 8 TDD slices (see `spec/FEATURE_CLOCK_SCOPING.md`).

Spec: `spec/FEATURE_CLOCK_SCOPING.md`

## Phase 35.6 â€” Stress Routing by Action Intent

**Status: Complete (2026-06-06) â€” 1738 unit tests passing**

Replace hard-coded `body` stress in `compute_world_reaction()` with deterministic
stress-track selection driven by clock category, clock level, action key, and
intent keywords.

Major work:

- Add `intent: str | None` to `ActionRequest` and `ActionResolution`.
- Update UI request builder to populate intent from the submitted intent text.
- Create `dungeon_daddy/rpg/stress_routing.py` with `choose_stress_track()`.
- Clock category mapping: `danger`/`hazard` â†’ body; `horror`/`fear` â†’ composure; `relationship`/`betrayal` â†’ bonds; `ritual`/`occult`/`dungeon_intimacy` â†’ weird.
- Clock level mapping (weaker signal): `room`/`level` â†’ body; `dungeon` â†’ weird; `quest` â†’ composure; `character`/`faction` â†’ bonds.
- Action key mapping: `fight`/`move`/`endure`/`tinker` â†’ body; `study`/`focus`/`sense` â†’ composure; `sway` â†’ bonds; `channel` â†’ weird.
- Intent keyword mapping (lowest priority): weird > bonds > composure > body when multiple groups match.
- Wire `choose_stress_track()` into `compute_world_reaction()`, passing matched clocks.
- Fix `PlayView._apply_world_reaction()` to read capacity from the actual stress track, not hard-coded `body`.
- 8 TDD slices (see `spec/FEATURE_STRESS_ROUTING_BY_ACTION_INTENT.md`).

Spec: `spec/FEATURE_STRESS_ROUTING_BY_ACTION_INTENT.md`

## Phase 36 â€” LLM-Proposed Reaction Drafts âœ“ Complete (2026-06-07)

Allow LLM creativity without giving it authority.

Major work:

- Add structured proposal format (`LLMReactionProposal`, `ProposedChange` discriminated union).
- Validate proposed changes â€” reject unknown clocks/actors, player-actor intent control.
- Auto-apply low-risk proposals (`create_memory`); keep `advance_clock` / `npc_reaction` as draft.
- `apply_consequence` auto-applies only when LLM track matches deterministic `choose_stress_track()`.
- `request_proposal` uses `response_format: json_object` and explicit flat-object schema prompt.
- Validator logs accepted/rejected changes at INFO level; debug panel shows kind + reason.
- Proposal pipeline fires after every resolve action in Play Mode.
- 9 TDD slices + post-merge live-app fixes. ~1810 unit tests passing.

Spec: `spec/PHASE_36_LLM_REACTION_PROPOSALS.md`

## Phase 37 â€” Memory Approval and Campaign Curation âœ“ Complete (2026-06-08)

Improve long-term play quality by controlling memory drift. 1814 unit tests passing; all manual UI tests passing.

Major work:

- `MemoryEntry.status` â†’ `Literal["draft", "approved", "rejected", "archived"]`, default `"draft"`.
- `MemoryRetriever.query()` returns only `approved` by default.
- `MemoryRepository.update_memory_status()` + `count_by_status()` added.
- Migration `006_memory_approval_status.sql` converts `active`â†’`approved`, `resolved`â†’`archived`.
- Seed pack saves seeded memories as `approved`.
- `build_curation_report()` in `dungeon_daddy/memory/curation.py`.
- `MemoryInspectorPanel.approve_selected()`, `reject_selected()`, `edit_selected_summary()`, `pop_pending_commit()`.
- `PlayView._handle_mem_click()` + `_persist_pending_memory_commit()` wired in live UI.
- MEM tab APPROVE/REJECT buttons live; detail pane with title truncation, word-wrap, dynamic height.
- Alpha playtest smoke test `tools/smoke_test_phase37.py` â€” 16 behaviors across both seeded campaigns.

Spec: `spec/PHASE_37_MEMORY_APPROVAL_AND_CAMPAIGN_CURATION.md`


---

# Dungeon Daddy â€” RPG System Stabilization and Chat-Centered Play Roadmap

**Audience:** Claude Code working in the `ghostpencil/dungeon-daddy` repository  
**Purpose:** Stabilize the post-Phase-37 RPG system, then guide the next development phases toward a more natural Dungeon Daddy play experience.  
**Core product goal:** The RPG system should make player choices mechanically meaningful, visibly consequential, and narratively responsive without allowing the LLM to mutate authoritative game state directly.

---

## Current State Summary

Dungeon Daddy has completed Phase 37. The RPG foundation is no longer theoretical. It now includes:

- Player-controlled actors.
- Action ratings.
- Stress tracks: `body`, `composure`, `bonds`, `weird`.
- Clocks with scope, level, category, room binding, action tags, and visibility.
- Deterministic world reactions.
- Stress routing by action, clock category, clock level, and intent keywords.
- Context bundle handoff into live Dungeon Master narration.
- LLM-proposed reaction drafts with structured parsing and validation.
- Memory approval/curation workflow.
- Seeded campaigns with enough RPG state to perform playtest scenarios.

However, the system has reached a new design inflection point:

> The RPG backend has become substantial enough that the current UI now feels like a development/testing interface rather than the final player-facing experience.

The immediate priority is **not** to add more mechanics. The immediate priority is to ensure the mechanics are reliable, observable, and then move the player action loop into the Dungeon Chat experience where Dungeon Daddy actually feels alive.

---

## Non-Negotiable Authority Boundary

This boundary must remain true in all future phases.

```text
The player controls the player side:
- one or more player-controlled actors
- intent declarations
- selected or confirmed actions
- strategic decisions

Dungeon Daddy controls the world:
- dungeon
- monsters
- NPCs
- factions
- hazards
- secrets
- clocks
- consequences
- narration

The RPG service and memory layer are authoritative.
The LLM is advisory.
The LLM may narrate, summarize, interpret tone, or propose structured changes.
The LLM must not directly mutate authoritative RPG or memory state.
```

The guiding phrase remains:

```text
The LLM may propose.
The engine disposes.
```

---

## Architectural Guardrails

Preserve the existing dependency direction:

```text
views/play_view.py
  -> rpg/service.py
  -> memory/context_bundle.py
  -> llm/agents/dm_agent.py

rpg/service.py
  -> rpg/actions.py
  -> rpg/world_reaction.py
  -> rpg/stress_routing.py
  -> memory/repository.py only through explicit persistence/event boundaries

llm/agents/dm_agent.py
  -> receives ContextBundle and known IDs
  -> does not query DuckDB
  -> does not import RPGService
```

Do not let UI panels become repositories, rule engines, or LLM agents.

Do not let the LLM choose and apply state changes without deterministic validation.

Do not let the next UI work destroy the existing right-side RPG panel. It should be demoted into an inspector/debug/status surface, not deleted.

---

## Current Concern: Intent May Not Be Reaching the Mechanics

Before new feature work, verify and fix the player intent path.

Known likely issue:

- `ActionRequest` supports `intent`.
- `ActionResolution` supports `intent`.
- `resolve_action()` copies `request.intent` into the resolution.
- `choose_stress_track()` uses intent keywords.
- `PlayerActionPanel._build_request()` appears to accept `intent` but may not currently pass it into `ActionRequest`.

Expected correction:

```python
return ActionRequest(
    campaign_id=campaign_id,
    actor_id=actor_id,
    action_key=action_key,
    dice_pool=dice_pool,
    push_yourself=push_yourself,
    momentum_spend=momentum_spend,
    intent=intent,
)
```

This is small but important. Without it, the system cannot fully honor player-declared intent when routing stress or building reactions.

---

# Phase 37.1 â€” RPG Intent and Consequence Stabilization

## Goal

Ensure that the post-Phase-37 RPG system faithfully carries player intent through action resolution, world reaction, proposal validation, memory creation, debug display, and DM narration.

This phase should be completed before any major UI refactor.

## Desired System Behavior

When the player resolves an action with an intent string:

```text
Actor: Mara Flint
Action: Study
Intent: I study the mural to resist the dungeon's seductive memory and understand what it wants from us.
```

The system should preserve that intent through:

```text
PlayerActionPanel -> ActionRequest -> RpgService.resolve_action -> ActionResolution -> WorldReactionService -> stress routing -> proposal pipeline -> context bundle -> DM narration/debug display
```

The intent should be visible or inspectable in debug/test artifacts.

Stress should route using the best available deterministic information in this order:

1. Explicit track override, if future systems provide one.
2. Matched clock category.
3. Matched clock level.
4. Intent keywords.
5. Action key fallback.
6. Safe default.

LLM proposals must not obscure deterministic consequences. The debug tab should clearly distinguish:

```text
Deterministic world reaction:
- Clock advanced
- Stress applied
- Fallout triggered

LLM proposal result:
- Accepted proposal changes
- Rejected proposal changes
- Auto-applied low-risk changes
- Skipped changes and reasons
```

## Development Tasks

### 37.1.1 â€” Intent Plumbing Audit

Inspect:

- `dungeon_daddy/ui/panels/player_action_panel.py`
- `dungeon_daddy/rpg/models.py`
- `dungeon_daddy/rpg/actions.py`
- `dungeon_daddy/views/play_view.py`
- `dungeon_daddy/rpg/world_reaction.py`
- `dungeon_daddy/rpg/stress_routing.py`

Confirm that:

- `PlayerActionPanel._build_request()` passes `intent` to `ActionRequest`.
- `ActionResolution.intent` is populated.
- `_apply_world_reaction()` receives a resolution with populated intent.
- `_run_proposal_pipeline()` receives the same intent.
- DM narration history includes the player intent.

### 37.1.2 â€” Regression Tests for Intent Preservation

Add or update unit tests covering:

- `PlayerActionPanel._build_request()` preserves intent.
- `resolve_action()` preserves intent from request to resolution.
- `compute_world_reaction()` passes `resolution.intent` to stress routing.
- A live-style PlayView action uses the typed intent in the resolution.

### 37.1.3 â€” Intent-Sensitive Stress Routing Tests

Add tests proving that intent affects stress when no stronger clock category/level applies.

Suggested examples:

```text
Action: study
Intent contains: "ritual", "dungeon", "voice"
Expected stress: weird

Action: move
Intent contains: "protect", "ally", "promise"
Expected stress: bonds

Action: tinker
Intent contains: "fear", "nightmare", "truth"
Expected stress: composure
```

Also test precedence:

```text
Clock category: danger
Intent contains: ritual
Expected stress: body, because matched clock category wins.
```

### 37.1.4 â€” Proposal Application Audit

Inspect:

- `dungeon_daddy/rpg/proposal.py`
- `dungeon_daddy/rpg/proposal_validator.py`
- `dungeon_daddy/rpg/proposal_applier.py`
- Debug display for proposals.

Confirm that:

- LLM-created memories are saved as draft unless explicitly approved.
- LLM-proposed consequence application does not duplicate deterministic stress accidentally.
- Skipped proposal changes are surfaced in debug output.
- Rejected proposal changes are surfaced in debug output.

Do not broaden proposal auto-application in this phase.

### 37.1.5 â€” Debug Visibility

Improve debug output if needed so a developer can understand one action end-to-end:

```text
Last action:
- actor
- action
- intent
- dice
- outcome

Deterministic reaction:
- clocks changed
- stress changed
- fallout triggered

LLM proposal:
- raw parse status if available
- accepted count
- rejected count
- applied count
- skipped count
- reasons
```

Avoid making the debug UI beautiful. Make it reliable and clear.

## Test Guidance

Run targeted tests after each slice:

```bash
pytest tests/unit/rpg -q
pytest tests/unit/ui/test_player_action_panel.py -q
pytest tests/unit/views -q
```

Then run the broader suite used in the current project workflow:

```bash
pytest tests/unit -q
```

Run existing smoke test(s):

```bash
python tools/smoke_test_phase37.py
```

Add a new smoke artifact if needed:

```text
artifacts/play_mode/phase37_1/intent_consequence_summary.json
```

The smoke artifact should show:

- actor ID/name
- action key
- intent
- outcome
- deterministic stress track chosen
- clock changes
- proposal accepted/rejected/applied/skipped counts

## Exit Criteria

Phase 37.1 is complete when:

- [x] Player intent is preserved from UI to `ActionRequest`.
- [x] Player intent is preserved from `ActionRequest` to `ActionResolution`.
- [x] World reaction uses populated intent for stress routing.
- [x] Proposal pipeline receives populated intent.
- [x] Debug display distinguishes deterministic consequences from LLM proposals.
- [x] LLM-created memory remains draft by default.
- [x] No direct LLM mutation of authoritative state is introduced.
- [x] Unit tests cover intent preservation and stress routing precedence.
- [x] Existing Phase 37 smoke test still passes.
- [x] No known failures are introduced.

**Status: Complete — 2026-06-09. 1839 unit tests passing.**

---

# Phase 38 â€” Chat-Centered RPG Interaction Refactor

**Status: Complete (2026-06-09) â€” 1920 unit tests passing. Smoke test 18/18 behaviors passing.**

## Goal

Move the primary player action loop from the right-side RPG panel into the Dungeon Chat experience while preserving the right panel as an RPG/memory/debug inspector.

The player should feel like they are speaking to the dungeon, not operating a rules console.

## Design Principle

```text
The dungeon filters player intent into meaningful risk.
```

The chat panel should become the primary place where the player:

- selects or sees the active player-controlled actor,
- declares intent,
- receives action framing,
- confirms or adjusts the action,
- sees the mechanical result,
- receives Dungeon Daddy narration.

The right RPG panel should remain for:

- character sheet,
- stress/fallout,
- clocks,
- memory approval,
- proposal/debug/provenance,
- development inspection.

## Desired System Behavior

Minimum Phase 38 behavior:

```text
1. Player selects or cycles active player-controlled actor near the chat input.
2. Player types an intent in chat.
3. Player can either:
   a. choose an action chip before sending, or
   b. send intent as narration and receive a lightweight framing prompt.
4. System resolves through RPGService, not through the LLM.
5. WorldReactionService applies deterministic consequences.
6. DM narration receives the updated context bundle.
7. The right panel updates as an inspector.
```

Phase 38 should not require full natural language action detection yet. It should support explicit or semi-explicit action selection in the chat area.

## Proposed UX

Add a compact player-action strip to the left Dungeon Chat panel.

Example:

```text
[Mara Flint]  Body 1/4  Composure 2/4  Bonds 0/4  Weird 1/4
Actions: [FIGHT] [MOVE] [TINKER] [STUDY] [FOCUS] [SWAY] [SENSE] [CHANNEL] [ENDURE]
Intent: existing chat input
```

Flow A â€” Explicit Action:

```text
Player selects: Mara
Player clicks: STUDY
Player types: I study the mural to understand what the dungeon wants.
Player sends.
System resolves STUDY using Mara's rating.
Dungeon Daddy narrates outcome.
```

Flow B â€” Chat Intent with Action Confirmation Stub:

```text
Player types: Mara studies the mural to understand what the dungeon wants.
System detects that no action chip was selected.
System responds: Choose an action to resolve this intent.
Buttons/chips: [STUDY] [SENSE] [FOCUS] [No roll]
Player clicks STUDY.
System resolves.
```

Flow B can be minimal and deterministic in Phase 38. Do not require LLM-based intent classification yet.

## Development Tasks

### 38.1 â€” Separate Player Action State from Right Panel

Create a small view/controller model for pending player action state. Suggested name:

```text
dungeon_daddy/ui/player_action_state.py
```

It should track:

- selected actor ID,
- selected action key or `None`,
- pending intent text,
- whether action is awaiting confirmation,
- last resolution summary.

Do not store authoritative RPG state here.

### 38.2 â€” Add Chat-Side Actor Mini-Card

Add a compact selected-actor display in or near `ChatPanel`.

It should show:

- actor name,
- compact stress track summary,
- optional tiny status/fallout indicator,
- previous/next actor controls if multiple player actors exist.

Single-actor campaigns should not feel awkward. If there is only one player actor, actor selection controls may be hidden or disabled.

### 38.3 â€” Add Chat-Side Action Chips

Add action chips near the chat input:

```text
FIGHT MOVE TINKER STUDY FOCUS SWAY SENSE CHANNEL ENDURE
```

Each chip should display rating if available:

```text
STUDY 2
TINKER 1
```

Selecting a chip should set the pending action but should not resolve immediately.

### 38.4 â€” Send Intent Through Existing Chat Input

When a player sends chat text while an action chip is selected:

- treat the text as action intent,
- build `ActionRequest`,
- call `RpgService.resolve_action`,
- call deterministic world reaction handling,
- run proposal pipeline if enabled,
- add mechanical summary to chat,
- send DM narration request with updated context bundle.

The same code path should be shared with the old right-panel action system where practical.

Avoid duplicating world reaction logic in two places.

### 38.5 â€” Preserve Right Panel as Inspector

The right action tab can remain for now, but it should not be the only way to take actions.

Right panel should update after chat-side actions.

### 38.6 â€” Add Mechanical Result Chat Bubble

Add a compact system/mechanical chat bubble before the DM narration:

```text
Mara rolls STUDY â€” Partial Success [4]
World Reaction:
- Bone Warden Stirs +1
- Weird +1
```

This bubble should be clearly distinguishable from Dungeon Daddy narration.

## Test Guidance

Add tests for:

- Chat-side selected actor state.
- Action chip selection.
- Sending chat with selected action creates `ActionRequest` with intent.
- Chat-side action uses same resolution path as right-panel action.
- Right panel reflects updated actor stress after chat-side action.
- No room selected -> action cannot resolve and user gets a system message.
- No RPG service -> fallback chat behavior remains stable.
- Single actor campaign -> actor selector behaves cleanly.
- Multiple actor campaign -> actor cycling changes selected actor.

Suggested test files:

```text
tests/unit/ui/test_chat_action_controls.py
tests/unit/views/test_play_view_chat_actions.py
tests/integration/test_chat_centered_action_loop.py
```

Use existing testing rules. Prefer real service/model objects over mocks unless Arcade widgets or external LLM calls must be isolated.

## Exit Criteria

Phase 38 is complete when:

- [ ] Player can resolve an RPG action from the chat area.
- [ ] Player intent from chat becomes `ActionRequest.intent`.
- [ ] Actor selection works for one or more player-controlled actors.
- [ ] Action chips show available actions and ratings.
- [ ] World reactions and stress routing still run deterministically.
- [ ] DM narration receives updated context bundle after chat-side action.
- [ ] Right RPG panel updates as inspector/debug/status.
- [ ] Existing right-panel action flow still works or is intentionally deprecated with tests adjusted.
- [ ] Legacy plain chat still works.
- [ ] Unit/integration tests cover the new flow.
- [ ] Manual smoke test demonstrates action -> consequence -> narration from chat.

---

# Phase 39 — Intent Framing and Player Confirmation

**Status: Complete (2026-06-12) — 2023 unit + 149 integration = 2172 total passing.**

## Goal

Let Dungeon Daddy help frame player intent into an RPG action while preserving player agency and deterministic authority.

This is the middle ground between pure buttons and pure natural language.

## Design Principle

```text
The player declares intent.
Dungeon Daddy frames the risk.
The player confirms or changes the action.
The engine resolves.
```

## Desired System Behavior

When a player types a natural language intent without selecting an action, the system should not immediately let the LLM roll anything.

Instead, it should propose a small deterministic or semi-deterministic framing:

```text
Mara studies the mural to understand what the dungeon wants.

Suggested frame:
- Actor: Mara
- Action: Study
- Alternative: Sense, Focus
- Stakes: the mural may reveal truth, but the dungeon may notice Mara noticing it

[Roll Study] [Use Sense] [Use Focus] [No Roll]
```

In Phase 39, this can start with deterministic heuristics. LLM assistance may be allowed only as advisory suggestion text, not direct resolution.

## Development Tasks

### 39.1 â€” Pending Intent Model

Create a model for unresolved player intent:

```text
PendingIntent
- actor_id
- raw_text
- suggested_action_keys
- suggested_primary_action
- stakes_text
- status: awaiting_confirmation / resolved / cancelled
```

This is UI/session state, not authoritative campaign history until resolved.

### 39.2 â€” Deterministic Intent Classifier

Create a simple deterministic classifier first.

Suggested mapping examples:

```text
fight keywords: attack, strike, block, duel, kill, smash
move keywords: sneak, run, climb, dodge, leap, escape
tinker keywords: open, repair, disable, mechanism, lock, device
study keywords: read, inspect, analyze, research, mural, book, symbol
focus keywords: resist, concentrate, calm, endure mentally
sway keywords: persuade, lie, comfort, command, bargain
sense keywords: listen, notice, feel, search, detect
channel keywords: ritual, magic, ghost, spirit, voice, dream
endure keywords: withstand, survive, hold, bear, take the hit
```

This classifier should return ranked suggestions, not a final command.

### 39.3 â€” Framing UI in Chat

When plain chat appears actionable:

- create pending intent,
- show suggested action chips,
- do not call `RpgService.resolve_action` yet,
- let player confirm.

### 39.4 â€” Confirmation Path

When player clicks a suggested action:

- build `ActionRequest`,
- resolve through RPG service,
- apply deterministic world reaction,
- update memory/proposal/debug as appropriate,
- narrate outcome.

### 39.5 â€” No-Roll Path

Allow player or system to mark the intent as `No Roll`.

No-roll intent should:

- go to ordinary DM narration,
- not create action resolution,
- not trigger world reaction,
- possibly allow room memory if `[REMEMBER]` is returned.

## Test Guidance

Add tests for:

- Intent classifier keyword mapping.
- Multi-suggestion ranking.
- Unknown intent falls back to no automatic roll.
- Pending intent is created but not resolved until confirmation.
- Confirming suggested action resolves via same path as explicit action.
- No-roll confirmation uses plain chat path.
- Player actor cannot be changed by LLM suggestion without player confirmation.

Suggested files:

```text
tests/unit/rpg/test_intent_classifier.py
tests/unit/views/test_play_view_pending_intent.py
tests/integration/test_intent_confirmation_loop.py
```

## Exit Criteria

- [x] Natural language chat can create a pending intent.
- [x] System proposes action choices without resolving automatically.
- [x] Player confirmation is required before any RPG action roll.
- [x] Confirmed action uses the authoritative RPG/world reaction path.
- [x] No-roll path remains available.
- [x] LLM does not directly resolve player intent.
- [x] Tests cover classifier, confirmation, cancellation, and no-roll paths.
- [x] Smoke test shows a full natural-language intent → suggested action → confirmed roll → consequence → narration flow.

### Post-completion UI polish (2026-06-12)

- Replaced mini card + static play chips with a full **character card** in `ChatPanel`:
  - Portrait placeholder (dark box, `◆` icon) on the left column
  - Character name with fixed-position `<` / `>` carousel arrows (wraps last → first)
  - 3×3 action ratings grid (teal when rating > 0, dim when 0)
  - 4 stress tracks in 2×2 layout (body/composure, bonds/weird)
  - Play mode `INPUT_AREA_H` expanded 122 → 176 px
- Removed `_CHIPS_PLAY` static suggestions; play mode shows chips only when `_pending_chips` explicitly set
- Added `actions: dict[str, int]` to `ActorMiniCardData`
- Fixed stress label/box overlap (`_LBL_W` 22→30, `_SQ_GAP` 1→2)
- Fixed `rpg_seed.json` (The Crucible): added `protagonist` actor so `--force` resets its stress tracks; removed stale string-ID protagonist row from DB

---

# Phase 40 — Campaign Authoring Foundation

**Status: Complete (2026-06-13) — 2216 total passing.**

## Goal

Begin building the tools needed to author playable campaigns that feed the RPG/world-reaction/memory system intentionally.

This phase should not attempt a full visual campaign editor yet. Start with schemas, CLI tooling, validation, and seed/export support.

## Why This Comes After the RPG UX Work

The runtime model is now clearer:

```text
Playable campaign data must include:
- player-controlled actors
- dungeon-controlled actors
- NPCs
- monsters
- factions
- room threats
- clocks
- action tags
- stress/fallout hooks
- approved starter memories
- draft memories when generated
- setting/party/level design docs
```

Authoring tools should produce data that the current runtime can actually use.

## Desired System Behavior

A campaign author or developer should be able to run:

```bash
python tools/create_campaign.py --slug bone-cathedral --title "The Bone Cathedral"
python tools/validate_campaign.py --campaign bone-cathedral
python tools/seed_campaign_rpg.py --campaign bone-cathedral --from manifest.yaml
```

The system should create or patch a campaign folder containing:

```text
campaigns/<slug>/
  dungeon.json
  session.json
  campaign.duckdb
  memory/
  rpg-memory/
  setting.md
  party.md or player_roster.md
  level_N_design.md
  campaign_manifest.yaml/json
```

Do not require the LLM for basic campaign authoring.

## Development Tasks

### 40.1 â€” Campaign Manifest Schema

Define a manifest format. Start small.

Suggested model:

```text
CampaignManifest
- slug
- title
- premise
- dungeon_slug
- starting_level
- player_side
- world_actors
- factions
- clocks
- memory_seeds
- room_threats
```

Suggested actor fields:

```text
ActorManifest
- slug
- display_name
- actor_type: pc / npc / monster / dungeon / faction / dungeon_presence
- concept
- status
- action_ratings
- stress_tracks
- tags
```

Suggested clock fields:

```text
ClockManifest
- slug/id
- label
- segments
- filled
- status
- clock_level
- category
- scope_room_id
- level_id
- action_tags
- visible_to_player
- stakes
- completion_effect
```

### 40.2 â€” Manifest Validator

Create validation that catches:

- duplicate IDs/slugs,
- unknown room references,
- invalid action keys,
- invalid stress tracks,
- invalid clock segments,
- invalid actor types,
- invalid memory status,
- room threat references to missing actors/clocks,
- empty player side.

### 40.3 â€” Campaign Creation CLI

Create or extend tools for:

```text
tools/create_campaign.py
tools/seed_campaign_rpg.py
tools/validate_campaign.py
```

The first implementation may be CLI-only.

### 40.4 â€” Export Existing Campaign as Manifest

Add export support that can generate a manifest-like view from an existing seeded campaign.

This helps convert The Crucible and Tomb of the Forgotten King into reusable examples.

### 40.5 â€” Example Campaign Manifest

Add one example manifest under:

```text
examples/campaign_manifests/
```

The example should be small but complete enough to validate and seed.

## Test Guidance

Add tests for:

- manifest parsing,
- required fields,
- invalid actor types,
- invalid clock references,
- duplicate IDs,
- seed idempotency,
- dry-run behavior,
- create -> validate -> seed -> export round trip.

Suggested files:

```text
tests/unit/campaign/test_campaign_manifest.py
tests/unit/campaign/test_campaign_manifest_validator.py
tests/integration/test_campaign_authoring_cli.py
```

Use temporary directories and temporary DuckDB files. Do not mutate real campaign data during tests.

## Exit Criteria

Phase 40 is complete when:

- [ ] A campaign manifest schema exists.
- [ ] A validator catches common authoring mistakes.
- [ ] CLI can create or patch a campaign from a manifest.
- [ ] CLI supports dry-run mode.
- [ ] CLI is idempotent.
- [ ] Existing seeded campaign data can be exported or summarized into manifest form.
- [ ] At least one example manifest exists.
- [ ] Tests cover manifest parsing, validation, seeding, and round trip.
- [ ] No visual campaign editor is required yet.

---

# Future Phase Candidates

These are not part of the immediate implementation request unless explicitly approved.

## Phase 41 â€” AI-Assisted Campaign Drafting

**Status: Complete (2026-06-13) â€” 2266 tests passing. Manually verified.**

Let the LLM draft campaign manifest changes, but require validation and human approval before writing.

Modules: `dungeon_daddy/campaign/patch.py`, `drafter.py`, `patch_validator.py`, `approval.py`, `draft_flow.py`
CLI: `tools/draft_campaign_patch.py`
Tests: `tests/unit/campaign/test_manifest_patch.py`, `test_campaign_drafter.py`, `test_patch_validator.py`, `test_approval_flow.py`, `tests/integration/test_ai_campaign_drafting.py`

Exit criteria all met:
- LLM proposes manifest additions/removals in structured form
- Validator always runs before any patch is applied
- Human must explicitly approve before the manifest is mutated
- Patch application is idempotent
- LLM provider is injected â€” no live API calls in unit tests
- Integration test: end-to-end natural-language â†' patch â†' validate â†' apply â†' re-validate

## Phase 42 â€” Campaign Authoring UI

**Status: Complete (2026-06-13) â€” 2402 tests passing.**

Add a Design Mode interface for:

- player side,
- NPCs,
- monsters,
- factions,
- clocks,
- room threats,
- memory seeds,
- validation report.

Spec: `spec/PHASE_42_CAMPAIGN_AUTHORING_UI.md`

## Phase 43 â€” Faction System

**Status: Complete (2026-06-13) â€” 2402 tests passing.**

Add named factions as first-class campaign entities with persistent reputation state.

Spec: `spec/PHASE_42_ADDITION_FACTION_SYSTEM.md`

Major work:

- `FactionManifest` model (replaces `ActorManifest` for factions); named reputation tiers (hostile/cold/neutral/warm/allied).
- `FactionState` persisted in DuckDB (`007_factions.sql`).
- `AdjustReputationChange` in LLM proposal system.
- Faction reputations included in `ContextBundle`.
- Campaign UI: faction-specific edit form and list card (reputation chip, tier label, no action ratings/stress tracks).
- 7 TDD slices.

## Phase 44 â€” Playtest Telemetry and Balance Reports

**Status: Complete (2026-06-13) â€” 2435 tests passing**

Generate reports from domain events:

- most-used actions,
- stress distribution,
- clocks advanced too often/not enough,
- fallout frequency,
- proposal acceptance/rejection rates,
- memories created/approved/rejected.

## Phase 45 â€” Campaign Pipeline: Dungeon Library â†' Campaign Seeds â†' Save Games

**Status: Complete (2026-06-14) â€” 2436 tests passing**
Spec: `spec/PHASE_45_CAMPAIGN_PIPELINE.md`
Branch: `phase-45-campaign-pipeline`

Wire Design â†' Campaign â†' Play into a real authoring â†' publishing â†' playing pipeline
backed by three on-disk libraries: `dungeons/` (reusable templates), `campaign_seeds/`
(manifests attached to a dungeon), and `saves/` (self-contained `dungeon + seed + live
state`). Publishing a seed snapshots its dungeon + manifest into a new save and seeds its
DuckDB. Existing `campaigns/*` auto-migrate once. A new Library home screen is the
landing/hub view. Post-phase: entire top-level menu bar removed; 4-pill navigation
(Library / Design / Campaign / Play).

9 TDD slices (0â€”8): config dirs, dungeon library wiring, seed library, seed persistence,
publish service, play loads saves, Library view, one-time migration, startup integration.

## Phase 46 — Inventory System (COMPLETE)

**Status: Complete (2026-06-17) — 2555 tests passing**
Spec: `spec/PHASE_46_INVENTORY_SYSTEM.md`
Branch: `phase-46-inventory-system`

Narrative-first inventory with three item categories: **Class Kits** (repeatable class
capabilities with charge tracks), **Dungeon Items** (significant stateful objects with a
≤ 10 cap), and **Equipped Gear** (modifies ratings at read time; `new_action` features
stored for Phase 50). Introduces the **Player Command** channel (`rpg/command.py`) — the
engine-authoritative input-dual of `LLMReactionProposal`. World-driven item changes
(`GrantItemChange`, `StripItemChange`, `TransformItemChange`) stay on the LLM-advisory
proposal channel. Migration `008_items.sql` creates `items` + `item_features` tables.
`CharacterSheetPanel.set_inventory()` renders KITS/ITEMS/GEAR sections. Manifest +
seeder support via `ItemManifest` / `CampaignManifest.items`.

10 TDD slices; 2555 tests passing.

## Phase 47 — Room Contents (COMPLETE)

**Status: Complete (2026-06-18) — 2673 tests passing**
Spec: `spec/PHASE_47_ROOM_CONTENTS.md` (GitHub issue [#72](https://github.com/ghostpencil/dungeon-daddy/issues/72))
Branch: `phase-47-items-in-rooms`

Place **items** and **interactive objects** into rooms per campaign seed (the dungeon
template stays generic). Loose items (`dungeon_item` with `owner_actor_id = None` + `room_id`)
can be picked up / dropped; **objects** are room fixtures with a per-archetype **state
machine** — activating one can change state, **spawn a pre-seeded item** into the room, and
**advance a clock**, all as engine-internal deterministic side-effects. Room interactions are
**Player Commands** (`PickUpItem` / `DropItem` / `ActivateObject`), not LLM proposals;
side-effects fire inside the command applier. No party-location gate this phase (Phase 48).
New `current_room` context block (objects + loose items) provided via optional
`current_room_id`. Migration `009_room_objects.sql`; `RoomObjectManifest` +
`CampaignManifest.room_objects`; Campaign Seed editor gains a room → objects drill-down.

9 TDD slices + 3 rounds of post-slice Campaign-UI bug/UX fixes (rooms drill-down navigation,
auto-generated slug, archetype cycle picker). 2673 tests passing.


# Planned Roadmap — Phases 48–53

These phases are **defined on the GitHub Projects roadmap** (`ghostpencil/dungeon-daddy`,
project #1) and are **not yet implemented**. Numbering and scope below mirror that board.
A detailed `spec/PHASE_NN_*.md` is written when each phase actually starts.

| Phase | Title | One-line scope |
|---|---|---|
| 47 | Room Contents | Items in rooms + interactive objects with a state machine — **COMPLETE** |
| 48 | Dungeon Navigation | Room exits, party location, level connectors |
| 49 | Starting Playbooks | Class foundations: ratings, tracks, kit, **tags**, **signature adverbs**, starting abilities |
| 50 | Hybrid Action Model | Structured **Verb · Noun · Adverb** action input; LLM narrates only |
| 51 | Talk to the Dungeon | Intimacy-gated freeform channel at resonance points |
| 52 | Milestone Advancement | Playbook beats, ranks to 5, ability unlocks |
| 53 | Threat Behavior & Monster Reactions | Instinct-driven, engine-bounded monster reactions (no enemy turn); boss phases via clock thresholds |

## Phase Dependencies & Sequencing (47–53)

Reviewed 2026-06-17 (after adding Phase 53; Phase 46 now complete). **The ordering is
topologically valid — every hard dependency points backward to a lower phase number, so no
phase is sequenced ahead of a prerequisite. No renumbering is required.** The matrix below
is sourced from each card's stated "Depends on:" line on GitHub Project #1.

| Phase | Hard deps | Points back? |
|---|---|---|
| 47 Room Contents | 46 (complete) | ✓ (complete) |
| 48 Dungeon Navigation | 47 (complete) | ✓ |
| 49 Starting Playbooks | 46 (complete) | ✓ |
| 50 Hybrid Action Model | 47, 48, 49 | ✓ |
| 51 Talk to the Dungeon | none (adds its own recedable-clock support) | ✓ |
| 52 Milestone Advancement | 49 | ✓ |
| 53 Monster Reactions | none hard (P34/35/36, all complete); *soft* "after 50" | ✓ |

**The roadmap is two parts:**

- **Tight spine (must stay ordered):** `47 → 48 → 50`, plus `49 → 50`, plus `49 → 52`.
  Every edge points forward; these phases cannot be reordered among themselves.
- **Flexible depth phases (no spine dependency):** **51** and **53**. Neither depends on the
  47→50 spine, so both are effectively "pull-on-demand" — they sit at the end by default but
  could slot in earlier whenever a playtest needs that depth.

**Notes:**
- **`rpg/command.py` forward reference (accepted, not a bug).** The Player-Command module is
  *first built* in Phase 46 but its *canonical framing* is documented in Phase 50 (the
  "a Card is the input-dual of a Proposal" boundary). Phases 46–48 reference it; this was a
  deliberate decision in the 2026-06-17 review.
- **Why Phase 53 stays last.** Its hard dependencies (monster actors P34, world-reaction P35,
  the `npc_reaction` channel P36) are already complete, so "after Phase 50" is only a *soft*
  preference: monster reactions ride the **LLM-advisory** channel that Phase 50 canonicalizes
  when it splits Player Commands from LLM proposals. Building 53 *before* 50 would force Phase
  50's proposal refactor to carry monster reactions through it (rework), so 53 is kept last.

## Key sequencing decisions (2026-06-17)

- **The former single "Playbooks" phase was split** into:
  - **Phase 49 — Starting Playbooks** (character creation: ratings, tracks, kit, tags,
    signature adverbs, starting abilities, `PlaybookLibrary`, `actor_abilities` live set), and
  - **Phase 52 — Milestone Advancement** (beats, ranks-to-5, `FulfillMilestone`, LLM
    milestone detection, `actor_beats`, campaign-specific beats).
- **Starting Playbooks (49) was moved ahead of the Action Model (50)** because the action
  model's **Verb** and **Adverb** slots read directly from playbook data:
  - **Verbs** = universal verbs (filtered by room + playbook gates) ∪ class verbs (actor abilities).
  - **Adverbs** = universal adverb pool (filtered by target + world state) ∪ playbook signature adverbs.

  The action picker reads the actor's **live** `actor_abilities` set, so Phase 52
  advancement grows the verb/adverb lists with no rewiring.
- **"How" → "Adverb".** The Phase 50 modifier slot is formalized as an **adverb** (it
  modifies the verb — "pick the lock *carefully*"), giving the grammar **Verb · Noun · Adverb**.
- Previous numbering: old 49 Hybrid Action Model → 50; old 50 Talk to the Dungeon → 51.

## Key design resolutions (2026-06-17 review)

A design review of the seven phases (logical coherence, Arcade feasibility, gaps) settled the
following — folded into the GitHub issue bodies for 46–52:

- **Pipeline split (Gap 1).** Player-initiated, engine-authoritative actions (move, pick up,
  equip, activate object, fulfil milestone) are **Player Commands** in a new `rpg/command.py`
  module — the input-dual of an `LLMReactionProposal`. The existing proposal union stays the
  *LLM-advisory* channel and carries only genuine **world reactions** (BlockExit, NPC reactions,
  clock/stress). This is why no proposal may set `current_room_id`. Phase 50 holds the canonical
  framing; 46–48 reference it.
- **Adverbs map to dice + flags, not position/effect (Gap 2).** The roll system is
  highest-of-d6-pool → outcome tier; it has **no position/effect axis**. Adverb (and movement
  `how?`) modifier flags are **dice-pool deltas** (`dice:±1`, `push`) plus **world-side-effect
  flags** (`suppress_entry_ticks`, `force_trap_trigger`, …), with optional momentum interaction.
- **Recedable intimacy clock (Gap 3).** Phase 51 adds a signed `tick_clock(clock, delta)` and a
  `monotonic: bool = True` field on `ClockState`. Existing clocks default `monotonic=True`
  (unchanged); intimacy/relationship clocks set `monotonic=False` so they may recede and do not
  latch to `completed`. Thresholds read `filled/segments` live.
- **9 universal verbs incl. `endure`.** Per `RPG_SYSTEM_SPEC.md` the action list has nine verbs;
  playbooks do not own verbs exclusively (their unique contribution is signature **adverbs** +
  kit/abilities). Phase 50's "8 verbs" was a miscount.
- **Combat has no enemy turn.** `RPG_SYSTEM_SPEC.md` makes initiative an explicit non-goal:
  `fight` resolves a roll against a monster **resistance/threat clock**; monsters surface as nouns.

Also recorded in the issue bodies (should-fix, resolved during the relevant phase):

- **Approval policy (46).** Player Commands apply immediately; world-reaction proposals keep the
  low-risk-auto / else-draft policy; batch a turn's drafts into one review prompt to avoid fatigue.
- **ContextBundle room block (47 → 48 → 50).** Today's bundle is actor/memory-keyed; the net-new
  `current_room` block (objects + loose items, then exits + fog-of-war + resonance) grows additively.
- **Provisional movement UI (48).** Keep it minimal — Phase 50's Card replaces it; the engine +
  `how?`→flag mapping is the first-class deliverable.
- **Milestone-detection gate (52).** Don't spend an LLM call every world reaction — pre-filter on
  beat-trigger relevance or batch at scene end.

## Phase 53 — Threat Behavior & Monster Reactions (design 2026-06-17)

Full design: **`spec/MONSTER_REACTION_DESIGN.md`**.

Makes monsters feel alive in fights **without** an enemy turn. A monster never rolls and never
takes a turn; it **reacts** to the player's roll when that roll gives it an opening (one player
action → one resolution → at most one monster reaction). This honors the same non-goal as the
combat note above (`RPG_SYSTEM_SPEC.md:17-31`): no initiative, no grid, no damage dice — a
reaction spends only the existing currencies (stress, clocks, tags).

- **Hybrid authority.** The engine computes the *eligible* reaction set **and every magnitude**;
  the LLM selects one reaction **by id** and writes the fiction. ("Engine bounds, LLM selects.")
- **Depth by rank.** `standard` monsters use **Model A** (instinct + a small reaction menu keyed
  to outcome tier + action tags). `elite`/`boss` use **Model B** = A + boss phases, where
  resistance-clock thresholds unlock higher reaction tiers. A boss is a Model-A monster with
  extra tiers — same schema. Full special-abilities (Model C) is out of scope until playtests
  demand it (`RPG_SYSTEM_SPEC.md:31`).
- **Catalog-bounded magnitudes.** Reactions carry `severity ∈ {minor,moderate,severe}` (mirrors
  the fallout catalog); the map to amounts/ticks lives in `BALANCE_NOTES.md`. Authors and the LLM
  cannot invent numbers.
- **Activates the inert channel.** Realizes `NpcReactionChange` (exists since Phase 36, never
  applied): the LLM returns a chosen `reaction_id`, the validator rejects out-of-set ids, and the
  engine applies the precomputed effect. Deterministic highest-priority fallback when the LLM
  omits/returns an invalid choice.
- **No double-application.** A fired reaction *is* the consequence and suppresses the generic
  stress-routing path in `world_reaction.py` for that resolution; the generic path still runs
  when no monster reaction is eligible. Additive, not a rewrite.
- **Dependencies.** Foundations exist today (monster actors P34, world-reaction P35,
  `npc_reaction` channel P36). Cleanest after Phase 50 canonicalizes the Player-Command vs
  LLM-advisory split, since reactions ride the LLM-advisory channel.

---

# Development Sequence Recommendation

Use this order:

```text
1. Phase 37.1 â€” stabilize intent/consequence/proposal visibility.
2. Manual smoke test both seeded campaigns.
3. Phase 38 â€” move primary action loop into chat.
4. Manual playtest and UX review.
5. Phase 39 â€” add intent framing and confirmation.
6. Manual playtest and UX review.
7. Phase 40 â€” authoring foundation.
```

Do not compress these phases. Each one changes a different risk surface:

```text
37.1: correctness
38: UI interaction model
39: player intent interpretation
40: content pipeline
```

Keeping them separate gives the project the best chance of reaching the Dungeon Daddy vision without destabilizing the working RPG foundation.

---

# Final Product Vision Check

A successful implementation should feel like this:

```text
Player:
Mara studies the mural to understand what the dungeon wants from her.

Dungeon Daddy:
That sounds like STUDY. The risk is not physical harm â€” it is that the mural studies her back.
[Roll Study] [Use Sense] [No Roll]

Player confirms.

System:
Mara rolls STUDY â€” Partial Success.
World Reaction:
- The Dungeon Notices Mara +1
- Weird +1

Dungeon Daddy:
The mural answers by remembering her before she was born. The painted woman turns her face toward Mara, and for one perfect second, Mara feels recognized.
```

That is the target: conversational, mechanically grounded, emotionally responsive, and still deterministic where it matters.


