# Phase 37 — Memory Approval and Campaign Curation

## Goal

Turn LLM-drafted memories and proposed reactions into a manageable campaign curation workflow.

By this phase, Dungeon Daddy can resolve player actions, apply deterministic world reactions, and optionally receive validated LLM reaction proposals. Phase 37 gives the user control over memory quality and prepares the game for sustained playtesting.

## Product problem

Memory is powerful but dangerous.

Bad memory entries can poison future retrieval and make the campaign feel incoherent. LLM-drafted memories need review, editing, and rejection paths.

## Scope

### 37.1 Draft memory states

Support clear memory statuses:

```text
draft
approved
rejected
archived
```

Existing `[DRAFT]` display should become actionable.

### 37.2 Memory approval UI

Add basic controls in MEM tab or a dedicated curation panel:

```text
Approve
Edit
Reject
Archive
```

Minimum display fields:

```text
Title
Summary
Importance
Tags
Source action/reaction
Draft source: deterministic / llm_draft / human
Created time
```

### 37.3 Editing rules

The user may edit:

- title
- summary
- importance
- tags
- body text

The user should not directly edit:

- memory_id
- campaign_id
- source action id
- checksum fields
- domain event history

### 37.4 Retrieval behavior

Default retrieval should include:

```text
approved memories
high-confidence deterministic memories
```

Draft behavior options:

```text
- include drafts only in debug/dev mode
- include drafts with [DRAFT] label
- exclude rejected memories always
```

Choose the safest repo-aligned behavior.

### 37.5 Campaign curation report

Add a tool or panel output showing:

```text
- memory counts by status
- top tags
- orphaned memories
- memories with missing markdown
- memories with invalid tags
- draft memories awaiting review
- high-importance memories
```

### 37.6 Alpha playtest scenario

Create a repeatable alpha scenario using the two existing seeded campaigns.

For each campaign, test:

```text
1. Load campaign.
2. Select a player-controlled actor.
3. Make three actions:
   - investigation/study/sense
   - physical/fight/move/tinker
   - social/weird/sway/channel/focus
4. Trigger at least one partial or miss.
5. Verify world reaction.
6. Verify memory created.
7. Approve/edit/reject a draft memory.
8. Verify future context bundle reflects approved memory behavior.
9. Capture smoke screenshots.
```

## Out of scope

- Full campaign editor.
- Memory graph visualization.
- Multi-user collaboration.
- Cloud sync.

## Acceptance criteria

- Draft memories can be approved.
- Draft memories can be edited before approval.
- Draft memories can be rejected.
- Rejected memories do not appear in normal context bundles.
- Approved memories appear in future retrieval when relevant.
- Curation report identifies pending drafts and obvious drift issues.
- Alpha playtest scenario can run in both seeded campaigns.
- Screenshots are captured after visible UI actions.
- Tests cover status transitions and retrieval behavior.

## Suggested TDD slices

1. Memory status transition tests.
2. Retrieval excludes rejected memories.
3. Retrieval includes approved memories.
4. Draft labeling remains visible.
5. Edit draft memory test.
6. Approve draft writes/checks Markdown sync.
7. Curation report counts statuses.
8. Alpha smoke scenario.
