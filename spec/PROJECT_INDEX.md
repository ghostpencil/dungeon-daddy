# Dungeon Daddy — Project Index

## Phase

Phase: 22 — Graph Mode Phase 3: Interaction Polish + Phase 2.5 Cleanup
Status: **Complete** (2026-05-31) — All 14 steps done. Spec: `spec/MAP_LAYOUT_PHASE_3.md`

---

## Next Steps

| Step | Task |
|---|---|
| ~~1~~ | ~~Phase 2.5 cleanup: refine objective warning naming in `validation.py` (`MISSING_ENDPOINT_ROLE`, `NO_QUEST_OBJECTIVE_ROLE`, `ENDPOINT_IS_TRANSITION_ONLY`)~~ — **Done** (`MISSING_OBJECTIVE_ROLE` replaced; 3 new warning categories with severity tiering; 4 new tests; 1188 passing) |
| ~~2~~ | ~~Connection metadata backfill for `crucible.json`, `tomb.json`, and local dungeon files~~ — **Done** (`apply_connection_patch` added to backfill script; `connection_patches` field in `LevelPatch`; all 6 levels patched with `layout_connection_role`/`graph_notes`; impactful: locked doors (Crucible L1 R2→R4, Tomb L2 2-C→2-E), secret passage (Crucible L3 r4→r5), vertical stairs (Tomb L1 1-E→2-A, Tomb L2 2-F→3-A); 3 new tests; 1199 passing) |
| ~~2a~~ | ~~Renderer visual parity with Phase 2.5 artifact — three gaps: (1) role-based border color, (2) role-based fill color, (3) marker text at top of room box~~ — **Done** (`border_color` + `fill_color` fields added to `GraphRoomStyle`; renderer uses style fields instead of `_ROOM_BORDER`/`_ROOM_FILL` constants; marker y moved from `wh*0.15` to `wh*0.82`; 6 new tests; 1194 passing) |
| ~~3~~ | ~~`GraphViewState` model: camera, selected room, hovered room, hovered connection~~ — **Done** (`CameraState` + `GraphViewState` in `graph_view_state.py`; `hover_room`, `select_room`, `hover_connection`, `clear_selection`, `recenter` methods; 12 new tests; 1211 passing) |
| ~~4~~ | ~~Room hit testing (point-in-rect) + connection hit testing (tolerance; room wins)~~ — **Done** (`hit_test.py` added; `hit_test_room`, `hit_test_connection`, `hit_test` functions; `_point_to_segment_dist` helper; 9 new tests; 1220 passing) |
| ~~5~~ | ~~Style resolution pipeline: base → semantic role → critical path → focus/fade → hover → selected~~ — **Done** (`style_resolver.py` added; `resolve_room_render_style` composites focus/fade + neighbor highlight + critical path subtle fade + hover + selected; 8 new tests; 1228 passing) |
| ~~6~~ | ~~Room hover visual state: border brightens/thickens; restores on mouse-out unless selected~~ — **Done** (`view_state: GraphViewState | None` added to `LayoutRenderer.draw()`; `resolve_room_render_style` composited per room when provided; hover branch adds `border_width+0.5`, `border_alpha+40`; old `selected_room_id` path preserved; 4 new tests; 1232 passing) |
| ~~7~~ | ~~Room selection + focus mode: connected rooms highlight, unrelated rooms/connections fade~~ — **Done** (`_connected_room_ids` helper added to `layout_renderer.py`; `_draw_rooms` passes real connected set to `resolve_room_render_style`; `_draw_edges` fades unrelated connections to 40% alpha when a room is selected; 3 new tests; 1235 passing) |
| ~~8~~ | ~~Connection hover: brightens near segment; tolerance-based hit testing~~ — **Done** (`_draw_edges` checks `view_state.hovered_connection_id`; applies `alpha+60` (capped 255) and `line_width+0.5`; 3 new tests; 1238 passing) |
| ~~9~~ | ~~Room detail panel: fixed panel showing name, ID, role, connections, notes~~ — **Done** (`room_detail_panel.py` added; `build_room_detail` assembles name/ID/role/visual_priority/on_critical_path/on_optional_branch/graph_notes/note/connections; `Room` + `Connection` models got `graph_notes`/`visual_priority` fields; 24 new tests; 1262 passing) |
| ~~10~~ | ~~Critical path emphasis: stronger when selected room is on the critical path~~ — **Done** (`selected_on_critical_path` flag added to `resolve_room_render_style`; other crit-path rooms get `+40 border_alpha` + `+0.5 border_width` when selected room is on the path; 3 new tests; 1265 passing) |
| ~~11~~ | ~~Keyboard controls: R = recenter, Escape = clear selection~~ — **Done** (`handle_key_press` in `map_panel.py` handles `R` → `_fit_layout_camera()` and `Escape` → `_selected_room_id = None`, both scoped to Graph mode; 6 new tests; 1271 passing) |
| ~~12~~ | ~~Artifact generation script + screenshot artifacts under `artifacts/layout/phase3/`~~ — **Done** (`scripts/generate_phase3_graph_artifacts.py`; 31 artifacts in `artifacts/layout/phase3/`: 4 default PNGs, 20 selection PNGs, 4 hover-connection PNGs, 3 connection hover PNGs, 4 interaction feedback JSONs, `phase3_feedback_summary.md`, `before_after_summary.md`; `map_panel.py` wired up with `GraphViewState` property + `handle_mouse_motion`; `play_view.py` routes `on_mouse_motion`; 5 new tests; 1276 passing) |
| ~~13~~ | ~~Integration tests: geometry/semantic/metadata scores do not regress; interaction states render~~ — **Done** (`test_phase3_semantic_scores_do_not_regress`, `test_phase3_metadata_scores_do_not_regress`, `test_phase3_interactive_states_render_without_exception`, `test_phase3_detail_panel_produces_data_for_entrance_room` added to `test_layout_pipeline.py`; 4 new tests; 1279 passing) |
| ~~14~~ | ~~Output artifacts: interaction feedback JSON per fixture, `phase3_feedback_summary.md`, `before_after_summary.md`, `connection_metadata_migration_report.md`~~ — **Done** (`connection_metadata_migration_report.md` + `implementation_summary.md` written; 36 total connections patched across 6 levels for Crucible + Tomb; all 4 interaction feedback JSONs, summary MD, before/after MD confirmed present; 1280 passing) |

### Phase 21 Completed Steps (archived)

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

- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
