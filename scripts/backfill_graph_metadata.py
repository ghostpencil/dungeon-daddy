"""Backfill semantic metadata into dungeon JSON files.

Usage:
    python scripts/backfill_graph_metadata.py --target-fixtures [--dry-run | --write]
    python scripts/backfill_graph_metadata.py --local-dungeon-dir DIR --dungeons NAME... [--dry-run | --write]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Pure transformation helpers
# ---------------------------------------------------------------------------

def apply_level_patch(level_dict: dict, patch: dict) -> bool:
    """Merge patch into level_dict["layout_metadata"]. Returns True if changed."""
    level_dict["layout_metadata"] = patch
    return True


def apply_room_patch(level_dict: dict, room_patches: dict[str, dict]) -> bool:
    """Add metadata fields to rooms matched by ID. Returns True if any room changed."""
    changed = False
    for room in level_dict.get("rooms", []):
        patch = room_patches.get(room["id"])
        if patch:
            room.update(patch)
            changed = True
    return changed


def apply_connection_patch(level_dict: dict, connection_patches: dict[str, dict]) -> bool:
    """Add metadata fields to connections matched by 'from→to' key. Returns True if any changed."""
    changed = False
    for conn in level_dict.get("connections", []):
        key = f"{conn['from']}→{conn['to']}"
        patch = connection_patches.get(key)
        if patch:
            conn.update(patch)
            changed = True
    return changed


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LevelPatch:
    floor_metadata: dict = field(default_factory=dict)
    room_patches: dict[str, dict] = field(default_factory=dict)
    connection_patches: dict[str, dict] = field(default_factory=dict)


@dataclass
class DungeonPatches:
    levels: dict[int, LevelPatch] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def backup_file(path: Path) -> Path:
    """Copy path to a timestamped .bak file in the same directory. Returns backup path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(f".{timestamp}.bak")
    shutil.copy2(path, bak)
    return bak


def run_backfill(path: Path, patches: DungeonPatches, *, dry_run: bool = True) -> str:
    """Apply patches to a dungeon JSON file. Dry-run by default (no writes).

    Returns a migration report string.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    title = data.get("meta", {}).get("title", path.stem)
    lines: list[str] = [f"## {title}"]

    for level in data.get("levels", []):
        level_id = level.get("id")
        level_patch = patches.levels.get(level_id)
        if not level_patch:
            continue
        if level_patch.floor_metadata:
            apply_level_patch(level, level_patch.floor_metadata)
            lines.append(f"  Level {level_id}: layout_metadata set")
        if level_patch.room_patches:
            apply_room_patch(level, level_patch.room_patches)
            for rid in level_patch.room_patches:
                lines.append(f"  Level {level_id}, room {rid}: metadata applied")
        if level_patch.connection_patches:
            apply_connection_patch(level, level_patch.connection_patches)
            for cid in level_patch.connection_patches:
                lines.append(f"  Level {level_id}, connection {cid}: metadata applied")

    if not dry_run:
        bak = backup_file(path)
        lines.append(f"  Backup: {bak.name}")
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        lines.append("  [WRITTEN]")
    else:
        lines.append("  [DRY RUN — no files written]")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Patch definitions
# ---------------------------------------------------------------------------

def _crucible_patches() -> DungeonPatches:
    return DungeonPatches(levels={
        1: LevelPatch(
            floor_metadata={
                "graph_template": "freeform",
                "entrance_room_id": "R1",
                "endpoint_room_id": "R4",
                "critical_path": ["R1", "R2", "R4"],
                "notes": "Sand-covered citadel. Elevator Shaft is the floor descent.",
            },
            room_patches={
                "R1": {"layout_role": "entrance", "visual_priority": "medium",
                       "graph_notes": "Floor entry point via front or hidden entrance."},
                "R2": {"layout_role": "hub", "visual_priority": "high",
                       "critical_path": True,
                       "graph_notes": "Central organizing room — Marketplace."},
                "R3": {"layout_role": "side_room", "visual_priority": "low",
                       "optional_branch": True,
                       "graph_notes": "Cargo Bay — safe bypass route."},
                "R4": {"layout_role": "descent", "visual_priority": "medium",
                       "critical_path": True,
                       "graph_notes": "Elevator Shaft — floor transition to Level 2."},
                "R5": {"layout_role": "hazard", "visual_priority": "medium",
                       "optional_branch": True,
                       "graph_notes": "Trap Room — mechanical hazard area."},
            },
            connection_patches={
                "R1→R2": {"layout_connection_role": "critical_path",
                           "graph_notes": "Main path from Receiving Hall to Marketplace."},
                "R1→R3": {"layout_connection_role": "optional_branch",
                           "graph_notes": "Hidden door bypass into Cargo Bay."},
                "R2→R4": {"layout_connection_role": "locked",
                           "graph_notes": "Locked door — key obtained in Marketplace."},
                "R3→R2": {"layout_connection_role": "optional_branch",
                           "graph_notes": "Cargo Bay fallback into Marketplace."},
                "R5→R2": {"layout_connection_role": "optional_branch",
                           "graph_notes": "Pursuit route back to Marketplace."},
                "R5→R4": {"layout_connection_role": "optional_branch",
                           "graph_notes": "Direct hazardous path to Elevator Shaft."},
            },
        ),
        2: LevelPatch(
            floor_metadata={
                "graph_template": "hub_spoke",
                "entrance_room_id": "r01",
                "endpoint_room_id": "r06",
                "objective_room_ids": ["r03"],
                "critical_path": ["r01", "r02", "r05", "r06"],
                "optional_branches": [["r02", "r03"], ["r02", "r04"]],
                "notes": "Factory floor organized around Central Hub. Maintenance Tunnel is the forward transition.",
            },
            room_patches={
                "r01": {"layout_role": "entrance", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Entry Chamber — floor start point."},
                "r02": {"layout_role": "hub", "visual_priority": "high",
                        "critical_path": True,
                        "graph_notes": "Central Hub — hub-spoke anchor."},
                "r03": {"layout_role": "key_room", "visual_priority": "medium",
                        "optional_branch": True,
                        "graph_notes": "Conveyor Control — key/control objective."},
                "r04": {"layout_role": "utility", "visual_priority": "medium",
                        "optional_branch": True,
                        "graph_notes": "Arcane Power Room — dormant golem lab."},
                "r05": {"layout_role": "hazard", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Molten Metal Pit — hazard on critical path."},
                "r06": {"layout_role": "transition", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Maintenance Tunnel — forward transition / floor endpoint."},
            },
            connection_patches={
                "r01→r02": {"layout_connection_role": "critical_path",
                             "graph_notes": "Entry Chamber to Central Hub."},
                "r02→r03": {"layout_connection_role": "optional_branch",
                             "graph_notes": "Branch to Conveyor Control objective."},
                "r02→r04": {"layout_connection_role": "optional_branch",
                             "graph_notes": "Branch to Arcane Power Room."},
                "r02→r05": {"layout_connection_role": "critical_path",
                             "graph_notes": "Hub to Molten Metal Pit — hazard on critical path."},
                "r05→r06": {"layout_connection_role": "critical_path",
                             "graph_notes": "Molten Pit to Maintenance Tunnel — floor exit."},
            },
        ),
        3: LevelPatch(
            floor_metadata={
                "graph_template": "linear",
                "entrance_room_id": "r1",
                "endpoint_room_id": "r8",
                "objective_room_ids": ["r3", "r8"],
                "critical_path": ["r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8"],
                "notes": "Power complex. Power Core Chamber is the true destination even though Prime Golem Lair is the boss.",
            },
            room_patches={
                "r1": {"layout_role": "entrance", "visual_priority": "medium",
                       "critical_path": True,
                       "graph_notes": "Control Nexus — floor entry / control point."},
                "r2": {"layout_role": "corridor", "visual_priority": "low",
                       "critical_path": True,
                       "graph_notes": "Conduit Corridor — energy conduit passage."},
                "r3": {"layout_role": "objective", "visual_priority": "medium",
                       "critical_path": True,
                       "graph_notes": "Crystal Array — arcane power objective."},
                "r4": {"layout_role": "hazard", "visual_priority": "medium",
                       "critical_path": True,
                       "graph_notes": "Electrified Floor — electrical hazard."},
                "r5": {"layout_role": "treasure", "visual_priority": "medium",
                       "optional_branch": True,
                       "graph_notes": "Vault of Opportunities — loot/ally room."},
                "r6": {"layout_role": "hazard", "visual_priority": "medium",
                       "critical_path": True,
                       "graph_notes": "Gravity Anomaly — environmental hazard."},
                "r7": {"layout_role": "boss", "visual_priority": "high",
                       "critical_path": True,
                       "graph_notes": "Prime Golem Lair — boss encounter before Power Core."},
                "r8": {"layout_role": "objective", "visual_priority": "major",
                       "critical_path": True,
                       "graph_notes": "Power Core Chamber — true final destination / quest objective."},
            },
            connection_patches={
                "r1→r2": {"layout_connection_role": "critical_path",
                           "graph_notes": "Control Nexus to Conduit Corridor."},
                "r2→r3": {"layout_connection_role": "critical_path",
                           "graph_notes": "Conduit Corridor to Crystal Array objective."},
                "r3→r4": {"layout_connection_role": "critical_path",
                           "graph_notes": "Crystal Array to Electrified Floor hazard."},
                "r4→r5": {"layout_connection_role": "secret",
                           "graph_notes": "Secret passage to Vault of Opportunities."},
                "r5→r6": {"layout_connection_role": "optional_branch",
                           "graph_notes": "Vault bypass route into Gravity Anomaly."},
                "r6→r7": {"layout_connection_role": "critical_path",
                           "graph_notes": "Gravity Anomaly to Prime Golem Lair boss."},
                "r7→r8": {"layout_connection_role": "critical_path",
                           "graph_notes": "Prime Golem Lair to Power Core Chamber — final door."},
            },
        ),
    })


def _tomb_patches() -> DungeonPatches:
    return DungeonPatches(levels={
        1: LevelPatch(
            floor_metadata={
                "graph_template": "freeform",
                "entrance_room_id": "1-A",
                "endpoint_room_id": "1-E",
                "critical_path": ["1-A", "1-B", "1-D", "1-E"],
                "optional_branches": [["1-A", "1-C", "1-E"]],
                "notes": "Waterlogged antechambers. Descent Chamber is explicit endpoint.",
            },
            room_patches={
                "1-A": {"layout_role": "entrance", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Flooded Entry — floor entry point."},
                "1-B": {"layout_role": "objective", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Drowned Shrine — altar of Mythrax, critical ritual room."},
                "1-C": {"layout_role": "hazard", "visual_priority": "low",
                        "optional_branch": True,
                        "graph_notes": "Rat Warren — hazard/optional side area."},
                "1-D": {"layout_role": "hall", "visual_priority": "low",
                        "critical_path": True,
                        "graph_notes": "Collapsed Gallery — passage through eroded murals."},
                "1-E": {"layout_role": "descent", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Descent Chamber — explicit floor endpoint / stair down."},
            },
            connection_patches={
                "1-A→1-B": {"layout_connection_role": "critical_path",
                              "graph_notes": "Flooded Entry to Drowned Shrine."},
                "1-A→1-C": {"layout_connection_role": "optional_branch",
                              "graph_notes": "Branch into Rat Warren hazard area."},
                "1-B→1-D": {"layout_connection_role": "critical_path",
                              "graph_notes": "Drowned Shrine to Collapsed Gallery."},
                "1-C→1-E": {"layout_connection_role": "shortcut",
                              "graph_notes": "Rat tunnel shortcut to Descent Chamber (squeeze DC 12)."},
                "1-D→1-E": {"layout_connection_role": "critical_path",
                              "graph_notes": "Collapsed Gallery to Descent Chamber."},
                "1-E→2-A": {"layout_connection_role": "vertical",
                              "graph_notes": "Stair down from Level 1 to Level 2."},
            },
        ),
        2: LevelPatch(
            floor_metadata={
                "graph_template": "freeform",
                "entrance_room_id": "2-A",
                "endpoint_room_id": "2-F",
                "critical_path": ["2-A", "2-C", "2-E", "2-F"],
                "notes": "Hall of Bound Servants. Sealed Descent is the floor exit.",
            },
            room_patches={
                "2-A": {"layout_role": "entrance", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Stair Landing — arrives from Level 1."},
                "2-B": {"layout_role": "hall", "visual_priority": "low",
                        "optional_branch": True,
                        "graph_notes": "Servants' Hall — ceremonial skeleton guards."},
                "2-C": {"layout_role": "treasure", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Reliquary — mimic trap; dangerous shortcut."},
                "2-D": {"layout_role": "library", "visual_priority": "medium",
                        "optional_branch": True,
                        "graph_notes": "Scriptorium — self-writing books; alternate path."},
                "2-E": {"layout_role": "boss", "visual_priority": "high",
                        "critical_path": True,
                        "graph_notes": "Wraith's Study — wraith-steward encounter."},
                "2-F": {"layout_role": "descent", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Sealed Descent — keyed exit to Level 3."},
            },
            connection_patches={
                "2-A→2-B": {"layout_connection_role": "optional_branch",
                              "graph_notes": "Branch into Servants' Hall."},
                "2-A→2-C": {"layout_connection_role": "critical_path",
                              "graph_notes": "Entry to Reliquary — dangerous shortcut."},
                "2-B→2-D": {"layout_connection_role": "optional_branch",
                              "graph_notes": "Servants' Hall to Scriptorium alternate path."},
                "2-C→2-E": {"layout_connection_role": "locked",
                              "graph_notes": "Sigil-locked door to Wraith's Study."},
                "2-D→2-E": {"layout_connection_role": "optional_branch",
                              "graph_notes": "Scriptorium alternate path to Wraith's Study."},
                "2-E→2-F": {"layout_connection_role": "critical_path",
                              "graph_notes": "Wraith's Study to Sealed Descent exit."},
                "2-F→3-A": {"layout_connection_role": "vertical",
                              "graph_notes": "Stair down from Level 2 to Level 3."},
            },
        ),
        3: LevelPatch(
            floor_metadata={
                "graph_template": "branch_and_merge",
                "entrance_room_id": "3-A",
                "endpoint_room_id": "3-E",
                "critical_path": ["3-A", "3-D", "3-E"],
                "optional_branches": [["3-A", "3-C", "3-D"], ["3-A", "3-B", "3-D"]],
                "notes": "King's Tomb. Throne of Bone is climax / boss endpoint.",
            },
            room_patches={
                "3-A": {"layout_role": "entrance", "visual_priority": "medium",
                        "critical_path": True,
                        "graph_notes": "Ossuary Approach — whispering skull walls."},
                "3-B": {"layout_role": "study", "visual_priority": "medium",
                        "optional_branch": True,
                        "graph_notes": "Advisor's Nook — spectral advisor with binding knowledge."},
                "3-C": {"layout_role": "hazard", "visual_priority": "medium",
                        "optional_branch": True,
                        "graph_notes": "Golem Forge — bone golems, still-hot forge."},
                "3-D": {"layout_role": "hall", "visual_priority": "low",
                        "critical_path": True,
                        "graph_notes": "Processional — audience hall leading to throne."},
                "3-E": {"layout_role": "boss", "visual_priority": "major",
                        "critical_path": True,
                        "graph_notes": "Throne of Bone — lich-king climax / Sundered Crown."},
            },
            connection_patches={
                "3-A→3-B": {"layout_connection_role": "optional_branch",
                              "graph_notes": "Branch to Advisor's Nook — binding knowledge path."},
                "3-A→3-C": {"layout_connection_role": "optional_branch",
                              "graph_notes": "Branch to Golem Forge — bone golem hazard path."},
                "3-B→3-D": {"layout_connection_role": "optional_branch",
                              "graph_notes": "Advisor's Nook to Processional."},
                "3-C→3-D": {"layout_connection_role": "optional_branch",
                              "graph_notes": "Golem Forge to Processional."},
                "3-D→3-E": {"layout_connection_role": "critical_path",
                              "graph_notes": "Processional to Throne of Bone — threshold of binding."},
            },
        ),
    })


# ---------------------------------------------------------------------------
# Patch registry  (title → patches)
# ---------------------------------------------------------------------------

_PATCH_REGISTRY: dict[str, DungeonPatches] = {
    "The Crucible": _crucible_patches(),
    "Tomb of the Forgotten King": _tomb_patches(),
}


# ---------------------------------------------------------------------------
# High-level runners
# ---------------------------------------------------------------------------

def _find_dungeon_files_by_title(
    directory: Path, dungeon_names: list[str]
) -> dict[str, Path | None]:
    """Search directory for JSON files whose meta.title matches one of dungeon_names.

    Checks both flat JSON files and subdirectory/dungeon.json layout.
    """
    result: dict[str, Path | None] = {name: None for name in dungeon_names}
    candidates: list[Path] = list(directory.glob("*.json"))
    # Also check <dir>/<name>/dungeon.json layout
    for name in dungeon_names:
        sub = directory / name / "dungeon.json"
        if sub.exists():
            candidates.append(sub)
    for json_file in candidates:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            title = data.get("meta", {}).get("title", "")
            if title in result:
                result[title] = json_file
        except (json.JSONDecodeError, OSError):
            pass
    return result


def run_fixtures(fixtures_dir: Path, *, dry_run: bool = True) -> str:
    """Backfill all known fixture files. Returns combined report."""
    report_sections: list[str] = ["# Fixture Backfill Report\n"]
    for name, patches in _PATCH_REGISTRY.items():
        candidates = list(fixtures_dir.glob("*.json"))
        target: Path | None = None
        for c in candidates:
            try:
                data = json.loads(c.read_text(encoding="utf-8"))
                if data.get("meta", {}).get("title", "") == name:
                    target = c
                    break
            except (json.JSONDecodeError, OSError):
                pass
        if target is None:
            report_sections.append(f"## {name}\n  FIXTURE_NOT_FOUND\n")
            continue
        report_sections.append(run_backfill(target, patches, dry_run=dry_run))
    return "\n".join(report_sections)


def run_local_dungeons(
    local_dir: Path,
    dungeon_names: list[str],
    *,
    dry_run: bool = True,
) -> str:
    """Backfill local dungeon files. Returns combined report."""
    if not local_dir.exists():
        return "LOCAL_DUNGEON_DIRECTORY_NOT_FOUND"

    report_sections: list[str] = [f"# Local Dungeon Backfill Report\n# Directory: {local_dir}\n"]
    found = _find_dungeon_files_by_title(local_dir, dungeon_names)

    for name in dungeon_names:
        path = found.get(name)
        patches = _PATCH_REGISTRY.get(name)
        if patches is None:
            report_sections.append(f"## {name}\n  SKIPPED — no patch definition\n")
            continue
        if path is None:
            report_sections.append(f"## {name}\n  FILE_NOT_FOUND in {local_dir}\n")
            continue
        report_sections.append(run_backfill(path, patches, dry_run=dry_run))

    return "\n".join(report_sections)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Backfill semantic metadata into dungeon JSON files."
    )
    p.add_argument(
        "--target-fixtures",
        action="store_true",
        help="Patch the repository fixture files (tests/fixtures/).",
    )
    p.add_argument(
        "--local-dungeon-dir",
        metavar="DIR",
        help="Path to the local dungeon directory.",
    )
    p.add_argument(
        "--dungeons",
        nargs="+",
        metavar="NAME",
        help="Dungeon titles to patch (used with --local-dungeon-dir).",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=True,
        help="Show what would change without writing (default).",
    )
    mode.add_argument(
        "--write",
        dest="dry_run",
        action="store_false",
        help="Write changes to disk (creates .bak backups first).",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.target_fixtures and not args.local_dungeon_dir:
        parser.print_help()
        sys.exit(1)

    repo_root = Path(__file__).parents[1]
    all_reports: list[str] = []

    if args.target_fixtures:
        fixtures_dir = repo_root / "tests" / "fixtures"
        report = run_fixtures(fixtures_dir, dry_run=args.dry_run)
        all_reports.append(report)

    if args.local_dungeon_dir:
        local_dir = Path(args.local_dungeon_dir)
        names = args.dungeons or list(_PATCH_REGISTRY.keys())
        report = run_local_dungeons(local_dir, names, dry_run=args.dry_run)
        all_reports.append(report)

    print("\n\n".join(all_reports))


if __name__ == "__main__":
    main()
