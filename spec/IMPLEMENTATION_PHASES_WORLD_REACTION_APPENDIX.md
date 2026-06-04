# Implementation Phases Appendix — Player Control and World Reactions

## Phase 33 — Player-Controlled Action Loop

Make the RPG loop visible and playable in Play Mode.

Major work:

- Seed both existing campaigns with minimal RPG-ready data.
- Add player-controlled actor filtering.
- Add Player Action panel.
- Resolve actions through `RpgService`.
- Show results, stress, clocks, fallout, and memory indicators.
- Pass `ContextBundle` into live DM narration.
- Add Debug bundle provenance display.

## Phase 34 — Campaign RPG Data Deepening

Make the existing campaigns meaningful RPG testbeds.

Major work:

- Add seed-pack format.
- Add richer player-controlled actors.
- Add dungeon-controlled NPCs, monsters, factions, and dungeon presence.
- Add campaign clocks.
- Add room threat hooks.
- Add starter memories and controlled tags.
- Improve seeder idempotency and reporting.

## Phase 35 — Deterministic World Reaction Service

Make the dungeon push back through deterministic state changes.

Major work:

- Add `WorldReactionService`.
- Map action outcomes to consequences.
- Use threat hooks and clocks.
- Apply clock/stress/memory changes through repositories/services.
- Write domain events.
- Update context bundle after reactions.
- Show reaction summary in Debug tab.

## Phase 36 — LLM-Proposed Reaction Drafts

Allow LLM creativity without giving it authority.

Major work:

- Add structured proposal format.
- Validate proposed changes.
- Reject invalid or unsafe proposals.
- Auto-apply only low-risk validated proposals if appropriate.
- Keep medium/high-risk proposals as draft.
- Show proposal provenance in Debug tab.

## Phase 37 — Memory Approval and Campaign Curation

Improve long-term play quality by controlling memory drift.

Major work:

- Add memory statuses: draft/approved/rejected/archived.
- Add approve/edit/reject UI.
- Define retrieval behavior by memory status.
- Add curation report.
- Run alpha playtest scenario across both seeded campaigns.
