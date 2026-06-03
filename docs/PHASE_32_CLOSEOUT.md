# Phase 32 — Stabilization + Balancing — Closeout Note

**Date:** 2026-06-03  
**Status:** Complete  
**Tests at close:** 1704 (excluding LLM eval tests)

---

## Acceptance Criteria — Verified

| Criterion | Status | Evidence |
|---|---|---|
| End-to-end action → stress → fallout → memory → context → DM narration | ✅ | `test_rpg_memory_full_pipeline.py` — 10 tests, all passing |
| Restart does not lose campaign state | ✅ | `MemoryRepository` uses DuckDB (persistent); session saved on `on_hide_view` |
| Sync validator catches drift | ✅ | `test_memory_repair_tools.py` — validates clean fixture reports zero drift; missing `.md` reports exactly that entry |
| Golden context bundle snapshots stable | ✅ | `test_context_bundle_snapshots.py` — deterministic retrieval order asserted across two runs |
| Documentation sufficient for future phases | ✅ | `docs/GM_RULES.md`, `docs/ARCHITECTURE.md`, `docs/TROUBLESHOOTING.md`, `docs/MIGRATION.md` |
| Full test suite green | ✅ | 1704 passing (evals excluded — LLM quality tests, non-deterministic by design) |
| LLM advisory only; no RPG/memory mutations | ✅ | `DungeonMasterAgent` has no repo or RPG service dependency; mutation is architecturally impossible |
| Play Mode works without initialized RPG state | ✅ | `PlayView.__init__` accepts `rpg_service=None`; all view unit tests run without it |

---

## Test Coverage Map

| Scenario | File | Tests |
|---|---|---|
| Golden fixture — seed helper | `tests/fixtures/phase32_campaign.py` | `seed_campaign()` importable; seeds PCs, NPCs, monsters, scenes, clocks, fallout, memories |
| Golden context bundle snapshots | `tests/integration/test_context_bundle_snapshots.py` | Retrieval order stable, `must_remember` always included, provenance counts accurate |
| Repair tools | `tests/integration/test_memory_repair_tools.py` | validate, export, import round-trip |
| Full pipeline | `tests/integration/test_rpg_memory_full_pipeline.py` | action roll → stress → fallout → memory entry → bundle → DM prompt |
| Bundle — empty / no actor / no memories / no fallout | `tests/unit/memory/test_context_bundle.py` | `test_build_with_no_data_returns_empty_collections`, `test_build_with_unknown_actor_returns_empty_actor_state` (added at closeout) |
| Prompt generation with bundle | `tests/unit/llm/test_dm_agent_context_bundle.py` | scene, memories, fallout, clocks, [DRAFT] label, no-bundle fallback |

---

## Changed Files (Phase 32)

| File | Change |
|---|---|
| `tests/fixtures/phase32_campaign.py` | New — golden fixture with full campaign seed |
| `tests/integration/test_context_bundle_snapshots.py` | New — deterministic retrieval snapshot tests |
| `tests/integration/test_memory_repair_tools.py` | New — validate/export/import repair tool tests |
| `tests/integration/test_rpg_memory_full_pipeline.py` | New — end-to-end pipeline test |
| `tools/validate_campaign.py` | New — DuckDB/Markdown drift reporter |
| `tools/rebuild_memory_projection.py` | New — drops and rebuilds memory search projection |
| `tools/export_campaign.py` | New — exports full campaign state to JSON bundle |
| `tools/import_campaign_fixture.py` | New — imports JSON bundle into a new campaign DB |
| `spec/BALANCE_NOTES.md` | New — RPG constant review findings |
| `docs/GM_RULES.md` | New — GM-facing RPG summary |
| `docs/ARCHITECTURE.md` | New — developer-facing system map |
| `docs/TROUBLESHOOTING.md` | New — common problems and fixes |
| `docs/MIGRATION.md` | New — backup, migration, and restore guide |
| `tests/unit/memory/test_context_bundle.py` | +2 empty-case tests added at closeout |

---

## Smoke Artifacts

| File | Description |
|---|---|
| `artifacts/play_mode/phase31/bundle_sample.json` | Context bundle from Phase 31 smoke run — all fields populated |
| `artifacts/play_mode/phase32/pipeline_summary.json` | Phase 32 pipeline smoke: action miss → stress 3→4→6 → Battered fallout → memory in bundle → 1599-char DM prompt |
| `artifacts/play_mode/phase30/*.png` | Play Mode UI smoke screenshots (Phase 30) |

`pipeline_summary.json` confirms the full arc works end-to-end: `outcome: "miss"`, `stress_cost: 1`, body reset to 0 after fallout, new memory card `in_bundle: true`, bundle containing 6 memory cards + 3 active fallout entries + 1 open clock.

---

## Known Limitations

**`PlayView._spawn_dm_thread` does not pass `context_bundle` to `agent.respond()`.**  
The bundle infrastructure is fully built and tested in isolation, but the live DM dispatch in PlayView still uses the old path (room memory text only, no RPG context bundle). During actual play, the DM agent does not receive actor state, clocks, or fallout as structured context. The wire-up is the primary outstanding item for the next phase.

---

## Deferrals to Next Phase

| Item | Notes |
|---|---|
| Wire `ContextBundleBuilder` into `PlayView._spawn_dm_thread` | Bundle must be built from the campaign's `MemoryRepository` and passed to `agent.respond()` at call time |
| Memory provenance display in Debug tab | Data available via `bundle.provenance`; UI panel not wired |
| LLM-drafted memory entry approval flow | `[DRAFT]` label renders in prompt; approval/auto-accept logic not implemented |
