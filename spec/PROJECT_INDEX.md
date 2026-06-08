# Dungeon Daddy — Project Index

## Phase

Phase: 37 — Memory Approval and Playtest Curation
Status: **Not started**

Branch: `main`

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

## Next Steps — Phase 37

Spec: `spec/IMPLEMENTATION_PHASES.md` (Phase 37 section)

Improve long-term play quality by controlling memory drift. Add approve/edit/reject workflows for LLM-drafted memories and run an alpha playtest scenario across seeded campaigns.

### Planned work

- Add memory statuses: `draft` / `approved` / `rejected` / `archived`.
- Add approve/edit/reject UI in the MEM tab.
- Define retrieval behavior per memory status (approved only in context bundles by default).
- Add curation report surfacing stale or conflicting memories.
- Run alpha playtest scenario across both seeded campaigns (The Crucible, one other).

## Known Failures

_None._

---

## Previous Phases

| Phase | Status | Tests |
|---|---|---|
| Phase 36 — LLM-Proposed Reaction Drafts | **Complete** (2026-06-07) | ~1810 unit passing; live-app verified; merged to main PR #40 |
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
