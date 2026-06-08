# Dungeon Daddy — Project Index

## Phase

Phase: 36 — LLM-Proposed Reaction Drafts
Status: **Complete (2026-06-07) — All 9 slices done + post-merge bug fixes**

Branch: `phase-36-llm-reaction-proposals`

_Slice 9 done (2026-06-07). 1772 unit tests passing. Proposal pipeline wired into live action loop: `DmAgent.request_proposal()` added, `PlayView._run_proposal_pipeline()` fires after each action, debug tab always shows proposal provenance._

**Post-merge fixes (2026-06-07):**
- `_draw_debug_tab()` now calls `proposal_section_lines()` — proposal provenance was stored but never rendered.
- `DebugControls` now filters level-scoped clocks to current level only (`set_current_level_id` + `_sync_debug_level_id()`).
- `DebugControls` now filters room-scoped clocks to rooms on the current level only (`set_current_level_room_ids`).
- `_sync_debug_level_id()` is called at campaign load and level change (not just after actions) so the filter is correct from first open.
- `request_proposal` signature changed: `known_clock_ids`/`known_actor_ids` replaced with `known_clocks`/`known_actors` (dicts with labels and display names); `room_name`/`room_note` added. Prompt restructured to system + user message so the LLM gets named, concrete context instead of opaque UUIDs — fixes the "Accepted: 0 Rejected: 0" empty proposal problem.
- 1802 unit tests passing.

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is advisory. The LLM may narrate, frame choices, interpret tone, and eventually propose structured world reactions. It must not directly mutate authoritative state.

---

## Phase 33–37 Roadmap

| Phase | Name | Goal |
|---|---|---|
| **33** | Player-Controlled Action Loop | Make Play Mode resolve player-controlled actor actions through the RPG service and narrate with live context bundles. |
| 34 | Campaign RPG Data Deepening | Patch the two existing campaigns with RPG-ready player actors, NPCs, monsters, clocks, memories, and room threat hooks. |
| 35 | Deterministic World Reaction Service | Add a deterministic service that turns player outcomes into dungeon/NPC/monster reactions, clocks, stress, fallout, and memory events. |
| 35.5 | Clock Scoping | Make clocks room-scoped and action-tagged so they only advance when contextually relevant. |
| **35.6** | Stress Routing by Action Intent | Replace hard-coded body stress with deterministic track selection driven by clock category, action key, and intent keywords. |
| 36 | LLM-Proposed Reaction Drafts | Allow the LLM to propose structured reactions, but validate and apply them through deterministic services only. |
| 37 | Memory Approval and Playtest Curation | Add curated approval/edit/reject workflows for LLM-drafted memories and run an alpha playtest scenario across seeded campaigns. |

Full phase specs in `spec/IMPLEMENTATION_PHASES.md`.

---

## Next Steps — Phase 36

Spec: `spec/PHASE_36_LLM_REACTION_PROPOSALS.md`

Allow the LLM to propose structured reactions, but validate and apply them through deterministic services only. Full spec including pre-build notes is in the spec file above.

### 8 TDD slices

1. Proposal model parse tests — `LLMReactionProposal`, `ProposedChange` subtypes ✓
2. Validation rejects unknown clock reference ✓
3. Validation rejects unknown actor reference ✓
4. Validation rejects player actor intent control ✓
5. Low-risk `create_memory` proposal auto-applies ✓
6. Medium-risk `apply_consequence` (stress) stays draft unless explicitly permitted ✓
7. Malformed JSON from LLM does not crash Play Mode ✓
8. Debug tab shows proposal provenance (accepted / rejected / source label) ✓
9. Wire proposal pipeline into live action loop — proposal fires after each action, debug tab shows real results ✓

### Slice 9 wiring notes

The entire proposal pipeline exists as tested standalone modules but is not called from the live app. Slice 9 connects them.

**Hook point:** `play_view.PlayView._on_resolve_action()` (`dungeon_daddy/views/play_view.py` ~line 671), right after `self._apply_world_reaction(resolution)`.

**New method needed:** `DmAgent.request_proposal(resolution, context_bundle, known_clock_ids, known_actor_ids, player_actor_ids)` in `dungeon_daddy/llm/agents/dm_agent.py`.
- Builds a proposal-request prompt (player intent, action result, deterministic consequences, known clocks/actors, schema instructions, authority boundary reminder).
- Calls `self._provider.complete(...)` with `max_tokens=512`.
- Returns the raw string (caller parses it).
- Must not raise — return empty string on any provider error.

**Wiring in `_on_resolve_action()`:**
1. Call `dm_agent.request_proposal(...)` with resolution + context.
2. `parse_proposal(raw)` → `LLMReactionProposal | None`.
3. If not None: `validate_proposal(proposal, known_clock_ids, known_actor_ids, player_actor_ids)`.
4. `apply_low_risk_proposals(validation_result, repo, campaign_id, action_key, intent, matched_clocks)`.
5. `self._debug.set_proposal_result(validation_result, apply_result)`.
6. If proposal is None (parse failed or DM agent absent): call `self._debug.set_proposal_result` with a no-op result so the tab always shows something.

**`_debug` accessor:** `PlayView` already owns `DebugControls` — find the attribute name and use it directly.

**Tests:** Add unit tests for `DmAgent.request_proposal()` (mock the provider); add an integration-style test for the wiring in `play_view` (use `__new__` + manual setup, mock provider, assert `_debug._last_validation` is set after `_on_resolve_action()`).

### Key implementation notes (from 35.5/35.6 review)

- **Clock validation**: fetch full `ClockState` from repo; reject proposals for clocks
  out of scope (`scope_room_id`, `level_id`, `action_tags` filters from Phase 35.5)
- **LLM prompt**: include `resolution.intent` in the proposal request context
- **Stress validation**: call `choose_stress_track()` deterministically and compare;
  matching proposal → low-risk auto-apply; divergent → medium-risk draft
- **Service hook**: `choose_stress_track(explicit_track=...)` is already the correct
  entry point when applying an approved stress proposal

### New modules (expected)

| Module | Purpose |
|---|---|
| `dungeon_daddy/rpg/proposal.py` | `LLMReactionProposal`, `ProposedChange` models |
| `dungeon_daddy/rpg/proposal_validator.py` | Validation + risk classification |
| `dungeon_daddy/rpg/proposal_applier.py` | Apply accepted low-risk changes |
| `tests/unit/rpg/test_proposal*.py` | TDD test files |

## Known Failures

_None._

---

## Previous Phases

| Phase | Status | Tests |
|---|---|---|
| Phase 36 — LLM-Proposed Reaction Drafts | **Complete** (2026-06-07) | 1802 unit passing (post-fix) |
| Phase 35.6 — Stress Routing by Action Intent | **Complete** (2026-06-06) | 1738 unit passing |
| Phase 35.5 — Clock Scoping, Clock Levels, Campaign Seed Upgrades | **Complete** (2026-06-06) | 1698 unit passing (post-bugfix) |
| Phase 35 — Deterministic World Reaction Service | **Complete** (2026-06-05) | 1818 passing |
| Phase 34 — Campaign RPG Data Deepening | **Complete** (2026-06-05) | 1802 passing |
| Phase 33 — Player-Controlled Action Loop | **Complete** (2026-06-04) | 1761 passing; live-app verified end-to-end |
| Phase 32 — Closeout pass | **Complete** (2026-06-03) | 1704 passing (excl. evals); see `docs/PHASE_32_CLOSEOUT.md` |
| Phase 32 step 32-6 — Smoke test + full pipeline test | **Complete** (2026-06-03) | 1708 passing |
| Phase 32 step 32-5 — Documentation | **Complete** (2026-06-03) | 1698 passing |
| Phase 32 step 32-4 — Balance pass | **Complete** (2026-06-03) | 1698 passing |
| Phase 32 step 32-3 — Repair tools | **Complete** (2026-06-03) | 1698 passing |
| Phase 32 step 32-2 — Golden context bundle snapshots | **Complete** (2026-06-03) | 1694 passing |
| Phase 31 — Context Bundles + AI Integration | **Complete** (2026-06-03) | 1686 passing |
| Phase 30 — Play Mode UI + Debug Tools | **Complete** (2026-06-03) | 1639 passing |
| Phase 29.5 — Campaign Save Folder Rename | **Complete** (2026-06-02) | 1575 passing |
| Phase 29 — Fallout + Dungeon Influence | **Complete** (2026-06-02) | 1568 passing |
| Phase 28 — Memory Persistence | **Complete** (2026-06-02) | 1549 passing |
| Phase 27 — RPG Core Loop | **Complete** (2026-06-02) | 1511 passing |
| Phase 26 — RPG + Memory Foundation | **Complete** (2026-06-02) | 1480 passing |
| Phase 25 — Map Visual Polish Phase 1 | **Complete** (2026-06-02) | 1410 passing |
| Phase 24 — Graph Mode Phase 4.1: Cleanup | **Complete** (2026-06-02) | 1395 passing (post-fix) |
| Phase 23 — Graph Mode Phase 4: Presentation, Detail Panel, Dungeon Personality | **Complete** (2026-06-01) | 1368 passing |
| Phase 22 — Graph Mode Phase 3: Interaction Polish | **Complete** (2026-05-31) | 1280 passing |
| Phase 21 — Graph Mode Phase 2.5: Semantic Metadata Backfill | **Complete** (2026-05-30) | 1184 passing |
| Phase 20 — Map Layout Visual Hierarchy (Phase 2) | **Complete** (2026-05-30) | 1097 passing |
| Phase 19 — Map Layout Phase 1 | **Complete** (2026-05-30) | 337 map tests |
| Post-Phase 18 — IP-1 through IP-9, MC-1 | **Complete** (2026-05-27) | 849 passing |
| Phase 18 — Python Code Quality Stabilisation | **Complete** | 664 passing |
| Phases 1–17 | **Complete** | — |

_Full session history in `spec/HISTORY.md`._

---

## Notes

- Player controls the player side: one or more player-controlled actors.
- Dungeon Daddy controls the dungeon, monsters, NPCs, factions, clocks, secrets, and consequences.
- The LLM is advisory. It may narrate or propose, but deterministic services apply authoritative state.
- World reactions implemented in Phase 35 via `WorldReactionService`.
- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
- RPG + Memory roadmap begins at Phase 26. See `spec/RPG_MEMORY_ROADMAP.md`.
- The RPG engine and memory layer are authoritative; the LLM is advisory.
- Use `spec/RPG_MEMORY_ARCHITECTURE.md`, `spec/RPG_MEMORY_DATA_MODEL.md`, `spec/RPG_SYSTEM_SPEC.md`, and `spec/MEMORY_SYSTEM_SPEC.md` only when relevant to the active task.

### Save Folder Structure (current)

Each campaign lives at `<campaigns_dir>/<campaign_slug>/`. The campaign's DuckDB and Markdown memory files live in the same folder. The `campaigns` table has a `dungeon_slug` column that records which dungeon design the campaign is running.

```
<campaigns_dir>/
  <campaign_slug>/
    dungeon.json        ← dungeon design (copied from source on clone)
    session.json        ← play session state
    campaign.duckdb     ← MemoryRepository (RPG state + memory)
    memory/             ← room play notes (level_N.md)
    rpg-memory/         ← Phase 28 Markdown narrative memory
      actors/
      events/
      fallout/
    setting.md          ← AI context docs (copied on clone)
    party.md
    level_N_design.md
```
