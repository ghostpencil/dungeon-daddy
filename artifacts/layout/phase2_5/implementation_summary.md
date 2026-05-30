# Phase 2.5 Implementation Summary

Generated: 2026-05-30

---

## Purpose

Phase 2.5 improves the semantic accuracy of Graph Mode by replacing name-based inference with explicit dungeon-authored metadata for The Crucible and Tomb of the Forgotten King. It does not replace the inference fallback; it adds an override layer above it.

---

## Files Changed

### New modules

| File | Purpose |
|---|---|
| `dungeon_daddy/map/dungeon_layout/metadata_validator.py` | Validates `layout_metadata` fields — invalid roles, missing room IDs, path ordering violations |
| `dungeon_daddy/map/dungeon_layout/metadata_quality_feedback.py` | `MetadataQualityFeedback` model + `generate_metadata_quality_feedback()` + `format_summary_row()` |
| `scripts/backfill_graph_metadata.py` | CLI script for dry-run/write fixture and local dungeon backfill with timestamped backups |

### Modified modules

| File | Change |
|---|---|
| `dungeon_daddy/data/models.py` | Added `LayoutMetadata` dataclass (`graph_template`, `entrance_room_id`, `endpoint_room_id`, `objective_room_ids`, `critical_path`, `optional_branches`, `notes`) |
| `dungeon_daddy/map/dungeon_layout/semantics.py` | `classify_all_roles` checks explicit `layout_role` first, then floor-level `entrance_room_id`/`objective_room_ids`, then name inference |
| `dungeon_daddy/map/dungeon_layout/endpoint_emphasis.py` | `detect()` accepts `endpoint_room_id`; `_find_endpoint()` checks it before role-priority list |
| `dungeon_daddy/map/dungeon_layout/seed_layout.py` | `compute_critical_path` checks `layout_metadata.critical_path` before inferred path |
| `dungeon_daddy/map/dungeon_layout/connection_style.py` | `resolve()` checks explicit `connection_style`, then `layout_connection_role`, then label aliases |
| `dungeon_daddy/map/dungeon_layout/validation.py` | Integrated `validate_metadata` into the layout pipeline |

### Updated fixtures

| File | Change |
|---|---|
| `tests/fixtures/crucible.json` | `layout_metadata` added to all 3 floors; room-level `layout_role`, `visual_priority`, `critical_path`, `graph_notes` added to all rooms |
| `tests/fixtures/tomb.json` | Same as above for all 3 floors |

### New test files

| File | Tests |
|---|---|
| `tests/unit/map/layout/test_metadata_validator.py` | 24 tests covering invalid roles, missing IDs, path ordering, duplicate IDs, endpoint/critical path consistency |
| `tests/unit/map/layout/test_metadata_quality_feedback.py` | 23 tests for feedback model, score calculation, warning accumulation, summary row format |
| `tests/unit/scripts/` | 6 tests for backfill script (dry-run mode, write mode, backup creation, patch application, missing directory handling) |

### Modified test files

| File | Tests Added |
|---|---|
| `tests/unit/map/layout/test_semantics.py` | 4 tests for explicit role override, entrance override via floor metadata |
| `tests/unit/map/layout/test_endpoint_emphasis.py` | 1 test for `endpoint_room_id` override |
| `tests/unit/map/layout/test_seed_layout.py` | 1 test for explicit critical path override |
| `tests/unit/map/layout/test_connection_style.py` | 5 tests for explicit `connection_style` and `layout_connection_role` override |
| `tests/integration/test_layout_pipeline.py` | 8 integration tests (endpoint overrides, geometry non-regression, metadata fields in JSON output, score improvements) |

---

## Schema Decisions

### Room-level fields

`layout_role`, `visual_priority`, `critical_path` (bool), `optional_branch` (bool), `graph_notes` are optional additive fields on each room. Existing rooms without these fields are unaffected.

### Floor-level `layout_metadata`

Stored as a `layout_metadata` key on each floor object. Fields: `graph_template`, `entrance_room_id`, `endpoint_room_id`, `objective_room_ids`, `critical_path`, `optional_branches`, `notes`. All optional; inference fills anything not explicitly provided.

### Resolution order

Implemented strictly:

1. Explicit room `layout_role`
2. Existing room role/type fields
3. Floor-level `entrance_room_id` / `endpoint_room_id` / `objective_room_ids`
4. Name-based inference
5. `unknown`

Connection style resolves: explicit `connection_style` → explicit `layout_connection_role` → label alias → `normal`.

---

## Migration Behavior

The backfill script (`scripts/backfill_graph_metadata.py`) applies pre-defined patch definitions for The Crucible and Tomb of the Forgotten King:

- Dry-run by default unless `--write` is supplied.
- Applies patches additively — existing fields not in the patch are preserved.
- Writes are atomic per file: backup first, then overwrite.
- Reports every applied patch to stdout.
- Skips files with no matching patch definition.

---

## Backup Behavior

Before writing any local dungeon file, the script creates a timestamped backup:

```
<dungeon-dir>\<dungeon-name>\dungeon.<YYYYMMDD_HHMMSS>.bak
```

Backups created on 2026-05-30:
- `The Crucible\dungeon.20260530_144656.bak`
- `Tomb of the Forgotten King\dungeon.20260530_144656.bak`

Test fixtures (`tests/fixtures/*.json`) are not backed up by the script — they are managed by git.

---

## Commands Run

```
python scripts/backfill_graph_metadata.py --target-fixtures --dry-run
python scripts/backfill_graph_metadata.py --target-fixtures --write
python scripts/backfill_graph_metadata.py --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" --dungeons "The Crucible" "Tomb of the Forgotten King" --dry-run
python scripts/backfill_graph_metadata.py --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" --dungeons "The Crucible" "Tomb of the Forgotten King" --write
python -m pytest
```

---

## Test Results

```
1184 passed in 68.23s
```

87 new tests added during Phase 2.5 (1097 passing at Phase 20 completion → 1184 passing at Phase 2.5 completion).

---

## Known Limitations

- `crucible_l1` still triggers `MISSING_OBJECTIVE_ROLE` because `descent` is not counted as an objective-type role by the visual hierarchy feedback scorer. This is intentional — `descent` is a valid floor endpoint but not a combat/quest objective. The warning is classified as medium severity and does not affect layout rendering.
- Connection styles remain inferred from label aliases for all target fixtures. No explicit `connection_style` or `layout_connection_role` fields were added to connections in this phase; the connection override machinery is implemented and tested but not exercised by the backfill.
- Phase 2.5 covers only Crucible and Tomb of the Forgotten King. The `__test_drive__`, Irongate Depths, and Tomb of the Lich King dungeons in the local directory were not patched.

---

## Grid Mode

Grid Mode was not touched. No Grid Mode rendering code, Grid Mode layout data, or Grid Mode tests were modified.
