# Dungeon Daddy — Project Index

## Phase

Phase: —
Status: **No active phase** — Phase 21 complete. Next phase TBD.

---

## Next Steps

| Step | Task |
|---|---|
| ~~1~~ | ~~Update semantic role resolution pipeline~~ — **Done** (`LayoutMetadata` model added; `classify_all_roles` uses floor-level entrance/objective overrides; 4 new tests; 1116 passing) |
| ~~2~~ | ~~Endpoint detection override~~ — **Done** (`detect()` accepts `endpoint_room_id`; `_find_endpoint()` checks it before role-priority list; 1 new test; 1117 passing) |
| ~~3~~ | ~~Critical path override~~ — **Done** (`compute_critical_path` checks `layout_metadata.critical_path` first; 1 new test; 1118 passing) |
| ~~4~~ | ~~Connection style override~~ — **Done** (`Connection` model gets `connection_style`/`layout_connection_role` fields; `resolve()` checks them before label aliases; 5 new tests; 1117 passing) |
| ~~5~~ | ~~`metadata_validator.py` — warns on invalid roles, missing referenced room IDs, path ordering violations~~ — **Done** (`validate_metadata` implemented; 24 new tests; 1147 passing) |
| ~~6~~ | ~~`metadata_quality_feedback` JSON section + updated Markdown summary columns~~ — **Done** (`MetadataQualityFeedback` model + `generate_metadata_quality_feedback()` + `format_summary_row()` in `metadata_quality_feedback.py`; 23 new tests; 1170 passing) |
| ~~7~~ | ~~`scripts/backfill_graph_metadata.py` — dry-run / write / timestamped-backup support~~ — **Done** (`apply_level_patch`, `apply_room_patch`, `backup_file`, `run_backfill`; patch definitions for all Crucible + Tomb floors; CLI with `--target-fixtures`/`--local-dungeon-dir`/`--dry-run`/`--write`; 6 new tests; 1176 passing) |
| ~~8~~ | ~~Backfill `tests/fixtures/crucible.json` (L1, L2, L3)~~ — **Done** (`layout_metadata` + room fields applied to all 3 levels; 1176 passing) |
| ~~9~~ | ~~Backfill `tests/fixtures/tomb.json` (L1 + additional floors)~~ — **Done** (`layout_metadata` + room fields applied to all 3 levels; 1176 passing) |
| ~~10~~ | ~~Backfill local dungeon files at `C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons`~~ — **Done** (Crucible + Tomb patched; directory also contains Irongate Depths, Tomb of the Lich King, __test_drive__ — no patches defined for those) |
| ~~11~~ | ~~Unit + integration tests for all new behaviour~~ — **Done** (`metadata_quality_feedback` wired into `LayoutFeedbackReport`; `_run_pipeline` populates it + uses explicit `endpoint_room_id`; 8 new integration tests (endpoint overrides, geometry non-regression, metadata fields, JSON output); 1184 passing) |
| ~~12~~ | ~~Artifact generation: screenshots, feedback JSON, migration report, summary~~ — **Done** (`crucible_l{1,2,3}_graph.png`, `tomb_l1_graph.png`, `metadata_migration_report.md`, `implementation_summary.md`, `before_after_summary.md` written; `layout_feedback_summary.md` updated with metadata columns; 1184 passing) |

---

## Known Failures

_None._

---

## Previous Phases

| Phase | Status | Tests |
|---|---|---|
| Phase 21 — Graph Mode Phase 2.5: Semantic Metadata Backfill | **Complete** (2026-05-30) | 1184 passing |
| Phase 20 — Map Layout Visual Hierarchy (Phase 2) | **Complete** (2026-05-30) | 1097 passing |
| Phase 19 — Map Layout Phase 1 | **Complete** (2026-05-30) | 337 map tests |
| Post-Phase 18 — IP-1 through IP-9, MC-1 | **Complete** (2026-05-27) | 849 passing |
| Phase 18 — Python Code Quality Stabilisation | **Complete** | 664 passing |
| Phases 1–17 | **Complete** | — |

_Full session history in `spec/HISTORY.md`._

---

## Notes

- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
