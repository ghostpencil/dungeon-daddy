# Phase 33–37 Test Plan

## Testing principles

Follow existing Dungeon Daddy testing discipline:

- tracer-bullet TDD
- real internal objects by default
- mocks only for UI rendering, external LLM provider calls, OS dialogs, and similar boundaries
- temp campaign folders/databases for persistence tests
- screenshots after visible UI-affecting smoke actions

## Phase 33 tests

Unit:

- actor control adapter filters player-controlled actors
- actor control adapter excludes dungeon-controlled actors
- player action request construction
- context bundle handoff helper handles missing RPG state
- debug provenance line builder handles no bundle and populated bundle

Integration:

- seed existing-style temp campaign with player actor, clocks, memories
- action resolution from UI/controller boundary calls `RpgService`
- `PlayView._spawn_dm_thread` passes `context_bundle` when available
- `PlayView._spawn_dm_thread` preserves no-bundle fallback

Smoke:

- load campaign A, open RPG panel, resolve action, view debug provenance
- load campaign B, open RPG panel, resolve action, view debug provenance

## Phase 34 tests

Unit:

- seed pack parse
- stable ID generation
- controlled tag validation
- room threat hook parse

Integration:

- apply seed pack to temp campaign DB
- reapply seed pack without duplicates
- seeded memories appear in context bundle
- seeded clocks appear in context bundle
- dungeon-controlled actors excluded from player action UI

## Phase 35 tests

Unit:

- reaction input/proposal models
- partial success -> moderate deterministic consequence
- miss -> stronger deterministic consequence
- validation rejects unknown clock
- validation rejects unknown actor
- validation rejects player actor intent control

Integration:

- action partial -> threat clock advances -> domain event written -> bundle updated
- action miss -> stress applied -> memory created -> bundle updated
- no relevant threat hook -> safe fallback consequence

## Phase 36 tests

Unit:

- parse valid LLM proposal
- reject malformed proposal
- reject proposal with unknown actor/clock
- reject proposal exceeding allowed bounds
- classify risk level

Integration:

- low-risk validated proposal applies through service
- medium-risk proposal remains draft
- rejected proposal does not mutate state

## Phase 37 tests

Unit:

- memory status transitions
- retrieval excludes rejected memories
- retrieval includes approved memories
- draft labels remain visible

Integration:

- approve draft memory writes DB and Markdown consistently
- edit draft memory updates checksum/sync state
- curation report counts statuses and drift

Smoke:

- run alpha scenario in both seeded campaigns
- approve/edit/reject draft memory from UI
- verify future bundle behavior
