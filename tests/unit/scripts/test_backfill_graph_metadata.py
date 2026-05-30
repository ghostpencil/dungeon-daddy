"""Tests for scripts/backfill_graph_metadata.py."""
import json
import sys
from pathlib import Path

# Make the script importable as a module
sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))
import backfill_graph_metadata as bgm

# ---------------------------------------------------------------------------
# Behavior 1: apply_level_patch adds layout_metadata to a level dict
# ---------------------------------------------------------------------------

def test_apply_level_patch_adds_layout_metadata():
    level = {"id": 1, "name": "Test Floor", "rooms": [], "connections": []}
    patch = {
        "graph_template": "freeform",
        "entrance_room_id": "R1",
        "endpoint_room_id": "R4",
        "critical_path": ["R1", "R2", "R4"],
    }
    changed = bgm.apply_level_patch(level, patch)
    assert changed is True
    assert level["layout_metadata"] == patch


# ---------------------------------------------------------------------------
# Behavior 2: apply_room_patch adds metadata fields to rooms matched by ID
# ---------------------------------------------------------------------------

def test_apply_room_patch_adds_fields_to_matching_room():
    level = {
        "id": 1,
        "rooms": [
            {"id": "R1", "name": "Receiving Hall", "type": "hall"},
            {"id": "R2", "name": "Marketplace", "type": "lair"},
        ],
    }
    room_patches = {
        "R1": {"layout_role": "entrance", "visual_priority": "medium"},
        "R2": {"layout_role": "hub", "visual_priority": "high"},
    }
    changed = bgm.apply_room_patch(level, room_patches)
    assert changed is True
    r1 = next(r for r in level["rooms"] if r["id"] == "R1")
    r2 = next(r for r in level["rooms"] if r["id"] == "R2")
    assert r1["layout_role"] == "entrance"
    assert r1["visual_priority"] == "medium"
    assert r2["layout_role"] == "hub"
    assert r2["visual_priority"] == "high"


def test_apply_room_patch_ignores_unknown_ids():
    level = {"id": 1, "rooms": [{"id": "R1", "name": "Hall", "type": "hall"}]}
    changed = bgm.apply_room_patch(level, {"UNKNOWN": {"layout_role": "hub"}})
    assert changed is False
    assert "layout_role" not in level["rooms"][0]


# ---------------------------------------------------------------------------
# Behavior 4: run_backfill dry-run returns report without writing files
# ---------------------------------------------------------------------------

def _minimal_dungeon() -> dict:
    return {
        "meta": {"title": "Test Dungeon"},
        "levels": [
            {
                "id": 1,
                "name": "Level 1",
                "rooms": [{"id": "R1", "name": "Hall", "type": "hall"}],
                "connections": [],
            }
        ],
    }


def test_run_backfill_dry_run_returns_report_and_no_file_written(tmp_path):
    dungeon_file = tmp_path / "test_dungeon.json"
    dungeon_file.write_text(json.dumps(_minimal_dungeon(), indent=2))
    original_mtime = dungeon_file.stat().st_mtime

    patches = bgm.DungeonPatches(
        levels={1: bgm.LevelPatch(
            floor_metadata={"graph_template": "freeform", "entrance_room_id": "R1"},
            room_patches={"R1": {"layout_role": "entrance"}},
        )},
    )
    report = bgm.run_backfill(dungeon_file, patches, dry_run=True)

    assert "Test Dungeon" in report
    assert dungeon_file.stat().st_mtime == original_mtime  # file untouched


# ---------------------------------------------------------------------------
# Behavior 5: backup_file creates a timestamped .bak copy
# ---------------------------------------------------------------------------

def test_backup_file_creates_bak_with_original_content(tmp_path):
    original = tmp_path / "dungeon.json"
    original.write_text('{"meta": {"title": "Test"}}')

    bak = bgm.backup_file(original)

    assert bak.exists()
    assert bak.suffix == ".bak" or ".bak." in bak.name
    assert bak.read_text() == original.read_text()
    assert bak != original


# ---------------------------------------------------------------------------
# Behavior 6: write mode creates backup and updates the file on disk
# ---------------------------------------------------------------------------

def test_run_backfill_write_mode_creates_backup_and_updates_file(tmp_path):
    dungeon_file = tmp_path / "test_dungeon.json"
    dungeon_file.write_text(json.dumps(_minimal_dungeon(), indent=2))

    patches = bgm.DungeonPatches(
        levels={1: bgm.LevelPatch(
            floor_metadata={"graph_template": "freeform", "entrance_room_id": "R1"},
            room_patches={"R1": {"layout_role": "entrance"}},
        )},
    )
    bgm.run_backfill(dungeon_file, patches, dry_run=False)

    # A .bak file should exist alongside the original
    bak_files = list(tmp_path.glob("*.bak"))
    assert len(bak_files) == 1

    # The file on disk should now contain layout_metadata
    updated = json.loads(dungeon_file.read_text())
    level1 = updated["levels"][0]
    assert "layout_metadata" in level1
    assert level1["layout_metadata"]["entrance_room_id"] == "R1"
    assert level1["rooms"][0]["layout_role"] == "entrance"
