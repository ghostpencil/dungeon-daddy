# Phase 2.5 Metadata Migration Report

Generated: 2026-05-30

---

## Fixture Files Updated

### tests/fixtures/crucible.json

All three floors received `layout_metadata` at the floor level and `layout_role`, `visual_priority`, `critical_path`, and `graph_notes` fields on every room.

| Floor | Rooms Patched | layout_metadata Set |
|---|---|---|
| Level 1 | R1, R2, R3, R4, R5 | Yes |
| Level 2 | r01, r02, r03, r04, r05, r06 | Yes |
| Level 3 | r1, r2, r3, r4, r5, r6, r7, r8 | Yes |

### tests/fixtures/tomb.json

All three floors received `layout_metadata` at the floor level and room-level metadata fields.

| Floor | Rooms Patched | layout_metadata Set |
|---|---|---|
| Level 1 | 1-A, 1-B, 1-C, 1-D, 1-E | Yes |
| Level 2 | 2-A, 2-B, 2-C, 2-D, 2-E, 2-F | Yes |
| Level 3 | 3-A, 3-B, 3-C, 3-D, 3-E | Yes |

---

## Local Dungeon Files

Directory: `C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons`

**Status: Found and accessible.**

| Dungeon | File | Found | Updated | Backup Created |
|---|---|---|---|---|
| The Crucible | `The Crucible\dungeon.json` | Yes | Yes | Yes |
| Tomb of the Forgotten King | `Tomb of the Forgotten King\dungeon.json` | Yes | Yes | Yes |
| `__test_drive__` | — | Yes | No | No |
| Other dungeons | — | Not searched | No | No |

Backup filenames (timestamped):
- `The Crucible\dungeon.20260530_144656.bak`
- `Tomb of the Forgotten King\dungeon.20260530_144656.bak`

The `__test_drive__` dungeon was found in the directory but skipped — no patch definitions exist for it and it is not in scope for Phase 2.5.

---

## Rooms Changed from `unknown` to Explicit Role

### The Crucible — Level 1

| Room ID | Room Name | Before | After |
|---|---|---|---|
| R3 | Cargo Bay | `unknown` | `side_room` |

### The Crucible — Level 2

| Room ID | Room Name | Before | After |
|---|---|---|---|
| r04 | Arcane Power Room | `unknown` | `utility` |
| r06 | Maintenance Tunnel | `unknown` | `transition` |

### The Crucible — Level 3

| Room ID | Room Name | Before | After |
|---|---|---|---|
| r1 | Control Nexus | `key_room` (name-inferred) | `entrance` (explicit) |
| r2 | Conduit Corridor | `unknown` | `corridor` |
| r3 | Crystal Array | `unknown` | `objective` |
| r8 | Power Core Chamber | `boss` (name-inferred, incorrect) | `objective` (explicit) |

### Tomb of the Forgotten King — Level 1

| Room ID | Room Name | Before | After |
|---|---|---|---|
| 1-B | Drowned Shrine | `unknown` | `objective` |
| 1-C | Rat Warren | `unknown` | `hazard` |
| 1-D | Collapsed Gallery | `unknown` | `hall` |

---

## Endpoints Explicitly Set

| Fixture | Floor | Explicit endpoint_room_id | Before (inferred) | After (explicit) |
|---|---|---|---|---|
| crucible | Level 1 | R4 | R4 descent (already correct) | R4 descent |
| crucible | Level 2 | r06 | r06 **unknown**, not emphasized | r06 **transition**, emphasized |
| crucible | Level 3 | r8 | r7 boss (wrong — boss priority won) | r8 objective (correct) |
| tomb | Level 1 | 1-E | 1-E descent (already correct) | 1-E descent |

The Level 2 and Level 3 Crucible cases were the primary motivation for Phase 2.5 endpoint override support.

---

## Critical Paths Explicitly Set

| Fixture | Floor | Critical Path |
|---|---|---|
| crucible | Level 1 | R1 → R2 → R4 |
| crucible | Level 2 | r01 → r02 → r05 → r06 |
| crucible | Level 3 | r1 → r2 → r3 → r4 → r5 → r6 → r7 → r8 |
| tomb | Level 1 | 1-A → 1-B → 1-D → 1-E |
| tomb | Level 2 | 2-A → 2-C → 2-E → 2-F |
| tomb | Level 3 | 3-A → 3-D → 3-E |

---

## Local Directory Errors

None. The directory was present, readable, and writable. Backups were created before any writes.

---

## Skipped Files

| File | Reason |
|---|---|
| `__test_drive__\dungeon.json` | No patch definitions for this dungeon; not in Phase 2.5 scope. |
| Other files in dungeon directory | Not targeted by Phase 2.5. Not modified. |

---

## Commands Run

```
python scripts/backfill_graph_metadata.py --target-fixtures --dry-run
python scripts/backfill_graph_metadata.py --target-fixtures --write
python scripts/backfill_graph_metadata.py --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" --dungeons "The Crucible" "Tomb of the Forgotten King" --dry-run
python scripts/backfill_graph_metadata.py --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" --dungeons "The Crucible" "Tomb of the Forgotten King" --write
```
