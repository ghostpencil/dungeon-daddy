# Connection Metadata Migration Report — Phase 3

## Summary

Explicit connection metadata (`layout_connection_role`, `graph_notes`) was backfilled into
all target fixture files and local dungeon files for The Crucible and Tomb of the Forgotten King
as part of Phase 3 Step 2.

---

## Fixture Files Changed

| File | Dungeon | Levels Patched | Connections Patched |
|---|---|---|---|
| `tests/fixtures/crucible.json` | The Crucible | L1, L2, L3 | 18 |
| `tests/fixtures/tomb.json` | Tomb of the Forgotten King | L1, L2, L3 | 18 |

## Local Dungeon Files Changed

| File | Dungeon | Levels Patched | Connections Patched |
|---|---|---|---|
| `C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons\The Crucible\dungeon.json` | The Crucible | L1, L2, L3 | 18 |
| `C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons\Tomb of the Forgotten King\dungeon.json` | Tomb of the Forgotten King | L1, L2, L3 | 18 |

## Skipped Files (no patch definition)

- Irongate Depths
- Tomb of the Lich King
- `__test_drive__`

---

## Backups Created

| Original File | Backup |
|---|---|
| `tests/fixtures/crucible.json` | `tests/fixtures/crucible.20260530_210203.bak` |
| `tests/fixtures/tomb.json` | `tests/fixtures/tomb.20260530_210203.bak` |
| `.../The Crucible/dungeon.json` | `.../The Crucible/dungeon.<timestamp>.bak` |
| `.../Tomb of the Forgotten King/dungeon.json` | `.../Tomb of the Forgotten King/dungeon.<timestamp>.bak` |

---

## Connections Patched — The Crucible

### Level 1

| Connection | Role | Notes |
|---|---|---|
| R1→R2 | `critical_path` | Main path from Receiving Hall to Marketplace |
| R1→R3 | `optional_branch` | Hidden door bypass into Cargo Bay |
| R2→R4 | `locked` | Locked door — key obtained in Marketplace |
| R3→R2 | `optional_branch` | Cargo Bay fallback into Marketplace |
| R5→R2 | `optional_branch` | Pursuit route back to Marketplace |
| R5→R4 | `optional_branch` | Direct hazardous path to Elevator Shaft |

**Total: 6 connections**

### Level 2

| Connection | Role | Notes |
|---|---|---|
| r01→r02 | `critical_path` | Entry Chamber to Central Hub |
| r02→r03 | `optional_branch` | Branch to Conveyor Control objective |
| r02→r04 | `optional_branch` | Branch to Arcane Power Room |
| r02→r05 | `critical_path` | Hub to Molten Metal Pit — hazard on critical path |
| r05→r06 | `critical_path` | Molten Pit to Maintenance Tunnel — floor exit |

**Total: 5 connections**

### Level 3

| Connection | Role | Notes |
|---|---|---|
| r1→r2 | `critical_path` | Control Nexus to Conduit Corridor |
| r2→r3 | `critical_path` | Conduit Corridor to Crystal Array objective |
| r3→r4 | `critical_path` | Crystal Array to Electrified Floor hazard |
| r4→r5 | `secret` | Secret passage to Vault of Opportunities |
| r5→r6 | `optional_branch` | Vault bypass route into Gravity Anomaly |
| r6→r7 | `critical_path` | Gravity Anomaly to Prime Golem Lair boss |
| r7→r8 | `critical_path` | Prime Golem Lair to Power Core Chamber — final door |

**Total: 7 connections**

---

## Connections Patched — Tomb of the Forgotten King

### Level 1

| Connection | Role | Notes |
|---|---|---|
| 1-A→1-B | `critical_path` | Flooded Entry to Drowned Shrine |
| 1-A→1-C | `optional_branch` | Branch into Rat Warren hazard area |
| 1-B→1-D | `critical_path` | Drowned Shrine to Collapsed Gallery |
| 1-C→1-E | `shortcut` | Rat tunnel shortcut to Descent Chamber (squeeze DC 12) |
| 1-D→1-E | `critical_path` | Collapsed Gallery to Descent Chamber |
| 1-E→2-A | `vertical` | Stair down from Level 1 to Level 2 |

**Total: 6 connections**

### Level 2

| Connection | Role | Notes |
|---|---|---|
| 2-A→2-B | `optional_branch` | Branch into Servants' Hall |
| 2-A→2-C | `critical_path` | Entry to Reliquary — dangerous shortcut |
| 2-B→2-D | `optional_branch` | Servants' Hall to Scriptorium alternate path |
| 2-C→2-E | `locked` | Sigil-locked door to Wraith's Study |
| 2-D→2-E | `optional_branch` | Scriptorium alternate path to Wraith's Study |
| 2-E→2-F | `critical_path` | Wraith's Study to Sealed Descent exit |
| 2-F→3-A | `vertical` | Stair down from Level 2 to Level 3 |

**Total: 7 connections**

### Level 3

| Connection | Role | Notes |
|---|---|---|
| 3-A→3-B | `optional_branch` | Branch to Advisor's Nook — binding knowledge path |
| 3-A→3-C | `optional_branch` | Branch to Golem Forge — bone golem hazard path |
| 3-B→3-D | `optional_branch` | Advisor's Nook to Processional |
| 3-C→3-D | `optional_branch` | Golem Forge to Processional |
| 3-D→3-E | `critical_path` | Processional to Throne of Bone — threshold of binding |

**Total: 5 connections**

---

## Dry-Run Output Summary

```
python scripts/backfill_graph_metadata.py --target-fixtures --dry-run

# Fixture Backfill Report

## The Crucible
  Level 1: layout_metadata set
  Level 1, room R1: metadata applied
  Level 1, room R2: metadata applied
  Level 1, room R3: metadata applied
  Level 1, room R4: metadata applied
  Level 1, room R5: metadata applied
  Level 1, connection R1→R2: metadata applied
  Level 1, connection R1→R3: metadata applied
  Level 1, connection R2→R4: metadata applied
  Level 1, connection R3→R2: metadata applied
  Level 1, connection R5→R2: metadata applied
  Level 1, connection R5→R4: metadata applied
  Level 2: layout_metadata set
  [... rooms and connections for L2 ...]
  Level 3: layout_metadata set
  [... rooms and connections for L3 ...]
  [DRY RUN — no files written]

## Tomb of the Forgotten King
  [... levels 1–3 ...]
  [DRY RUN — no files written]
```

## Write Output Summary

```
python scripts/backfill_graph_metadata.py --target-fixtures --write

[same per-level / per-room / per-connection lines as dry-run, plus:]
  Backup: crucible.20260530_210203.bak
  [WRITTEN]
  Backup: tomb.20260530_210203.bak
  [WRITTEN]

python scripts/backfill_graph_metadata.py \
  --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" \
  --dungeons "The Crucible" "Tomb of the Forgotten King" \
  --write

  [same structure; backups created at local dungeon paths]
  [WRITTEN]
```

---

## Notable Impactful Connections

| Dungeon | Connection | Role | Why Notable |
|---|---|---|---|
| Crucible L1 | R2→R4 | `locked` | Only locked door on the floor — key mechanic |
| Crucible L3 | r4→r5 | `secret` | Secret passage, not inferrable from label alone |
| Tomb L1 | 1-C→1-E | `shortcut` | Squeeze shortcut bypasses ~2 rooms |
| Tomb L1 | 1-E→2-A | `vertical` | Cross-level stair; only inter-floor connection in scope |
| Tomb L2 | 2-C→2-E | `locked` | Sigil-locked — key mechanic on Level 2 |
| Tomb L2 | 2-F→3-A | `vertical` | Cross-level stair |
