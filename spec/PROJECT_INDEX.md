# Dungeon Daddy — Project Index

## Phase

Phase: 41 — AI-Assisted Campaign Drafting
Status: **NOT STARTED**

Branch: `phase-41-ai-campaign-drafting`

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is advisory. It may narrate, frame choices, interpret tone, and propose structured world reactions. It must not directly mutate authoritative state.

---

## Phase 41 — AI-Assisted Campaign Drafting

### Goal

Let the LLM draft campaign manifest changes, but require validation and human approval before writing.

Expected flow:
```
User: Add an undead jailer to the ossuary.
LLM drafts manifest patch.
Validator checks it.
User approves.
Authoring service applies it.
```

Full spec: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` — search for "Phase 41".

### Tasks

- [ ] **41.1** — `ManifestPatch` model — structured diff of changes the LLM proposes (add/remove actors, clocks, room threats, memory seeds)
- [ ] **41.2** — LLM drafter: given a manifest and a natural-language request, produce a `ManifestPatch`
- [ ] **41.3** — Patch validator: run `validate_manifest` on the proposed result before presenting it to the user
- [ ] **41.4** — Approval flow: CLI `tools/draft_campaign_patch.py` — shows diff, asks yes/no, applies if approved
- [ ] **41.5** — Integration test: end-to-end natural-language → patch → validate → apply → re-validate

### Exit Criteria

- [ ] LLM can propose manifest additions/removals in structured form
- [ ] Validator always runs before any patch is applied
- [ ] Human must explicitly approve before the manifest is mutated
- [ ] Patch application is idempotent (re-applying an approved patch is safe)
- [ ] LLM provider is injected — no live API calls in unit tests
- [ ] Tests cover: drafter output structure, patch validation, approval gating, idempotency

---

## Known Failures

None (test suite passes — 2216 total as of 2026-06-13).

---

## Previous Phases

Phase 40 and earlier are complete. Full history in `spec/HISTORY.md`.

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
- `protagonist` actor is in `seed_data/campaigns/the-crucible/rpg_seed.json`; `--force` resets its stress tracks.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates and seeds cleanly).
