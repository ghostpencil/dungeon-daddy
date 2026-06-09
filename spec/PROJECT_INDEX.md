# Dungeon Daddy — Project Index

## Phase

Phase: 39 — Intent Framing and Player Confirmation
Status: **Planned**

Branch: `phase-38-chat-centered-rpg` (Phase 38 complete; new branch for Phase 39 pending)

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is advisory. It may narrate, frame choices, interpret tone, and propose structured world reactions. It must not directly mutate authoritative state.

---

## Phase 39 — Planned Work

### Goal

Let Dungeon Daddy help frame player intent into an RPG action while preserving player agency and deterministic authority.

Full spec: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` — search for "Phase 39".

### Tasks

- [ ] 39.1 — `PendingIntent` model (actor_id, raw_text, suggested_action_keys, suggested_primary_action, stakes_text, status)
- [ ] 39.2 — Deterministic intent classifier (keyword → ranked action suggestions)
- [ ] 39.3 — Framing UI in chat (pending intent → suggested chips, no resolve yet)
- [ ] 39.4 — Confirmation path (chip click → `ActionRequest` → RPG resolution → world reaction → narration)
- [ ] 39.5 — No-roll path (intent → plain DM narration, no action resolution)

### Exit Criteria

- [ ] Natural language chat can create a pending intent
- [ ] System proposes action choices without resolving automatically
- [ ] Player confirmation is required before any RPG action roll
- [ ] Confirmed action uses the authoritative RPG/world reaction path
- [ ] No-roll path remains available
- [ ] LLM does not directly resolve player intent
- [ ] Tests cover classifier, confirmation, cancellation, and no-roll paths
- [ ] Smoke test shows a full natural-language intent → suggested action → confirmed roll → consequence → narration flow

---

## Known Failures

None.

---

## Previous Phases

Phase 38 and earlier are complete. Full history in `spec/HISTORY.md`.

Last recorded test count: **1920 unit passing** (Phase 38 complete, 2026-06-09).

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
