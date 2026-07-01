"""Tests for the Crucible new-game reset tool (`reset_crucible_new_game`).

Seeds a realistic campaign with the real seed builders, drives it forward
(clears an obstacle, completes a tier, advances a clock, records memories/events,
takes stress, moves the party), then resets and asserts every dimension reverts
to the authored new-game state. Real `MemoryRepository` on `tmp_path`, no mocks.
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from tools.populate_crucible_dungeon_channel import CAMPAIGN_ID, seed_dungeon_channel
from tools.populate_crucible_level1 import _objects as level1_objects
from tools.populate_crucible_level1 import save_objects_preserving_state
from tools.reset_crucible_new_game import reset_to_new_game

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")
_GEARWORKS = "object:the-crucible:R4:gearworks"
_GREAT_LIFT = "object:the-crucible:R4:great-lift"


@pytest.fixture
def seeded(tmp_path: Path):
    repo = MemoryRepository(tmp_path / "campaign.duckdb")
    repo.initialize_schema(_MIGRATIONS_DIR)
    repo.save_campaign(
        campaign_id=CAMPAIGN_ID,
        slug="the-crucible",
        title="The Crucible",
        dungeon_slug="the-crucible",
    )
    save_objects_preserving_state(repo, level1_objects())
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    yield repo, tmp_path
    repo.close()


def _advance_the_game(repo: MemoryRepository, save_dir: Path) -> None:
    con = repo._conn
    # Party has descended and explored.
    (save_dir / "session.json").write_text(
        json.dumps(
            {
                "dungeon_id": "The Crucible",
                "current_level_idx": 1,
                "current_room_id": "r04",
                "visited_rooms": ["R1", "R2", "R4", "r04"],
                "map_variant": "grid",
                "play_transcript": ["a line"],
            }
        ),
        encoding="utf-8",
    )
    (save_dir / "memory" / "level_1.md").write_text("# play memory\n- did a thing", "utf-8")

    # Obstacle cleared + lift powered.
    repo.update_object_state(_GEARWORKS, "cleared")
    repo.update_object_state(_GREAT_LIFT, "powered")
    # Tier 0 completed.
    tier0 = next(o for o in repo.get_objectives(CAMPAIGN_ID) if o["tier_index"] == 0)
    repo.update_objective_status(tier0["objective_id"], "completed")
    # A clock advanced.
    con.execute("UPDATE clocks SET filled = 3 WHERE campaign_id = ?", [CAMPAIGN_ID])
    # A memory + a domain event recorded.
    repo.save_memory_entry("mem:1", CAMPAIGN_ID, "play", "Cleared the gears", status="approved")
    con.execute(
        "INSERT INTO domain_events (event_id, campaign_id, event_type, payload, occurred_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ["evt:1", CAMPAIGN_ID, "object.transitioned", "{}", datetime(2026, 7, 1, 8, 0, 0)],
    )
    # A PC took stress and is holding an item.
    repo.save_actor(
        "actor:the-crucible:pc:kira", CAMPAIGN_ID, "pc", "kira", "Kira",
        status="active", room_id="R1",
    )
    con.execute(
        "INSERT INTO stress_tracks (actor_id, track_key, capacity, filled) VALUES (?, ?, ?, ?)",
        ["actor:the-crucible:pc:kira", "body", 4, 3],
    )
    con.execute(
        "UPDATE items SET owner_actor_id = ? WHERE campaign_id = ? AND slug = 'lift-warden-key'",
        ["actor:the-crucible:pc:kira", CAMPAIGN_ID],
    )


def test_reset_reverts_all_progress_to_new_game(seeded):
    repo, save_dir = seeded
    _advance_the_game(repo, save_dir)

    counts = reset_to_new_game(repo, save_dir, CAMPAIGN_ID)
    con = repo._conn

    # Party back at the first room of the first floor.
    session = json.loads((save_dir / "session.json").read_text(encoding="utf-8"))
    assert session["current_level_idx"] == 0
    assert session["current_room_id"] == "R1"
    assert session["visited_rooms"] == ["R1"]
    assert session["play_transcript"] == []

    # Objects back to authored seed state.
    assert repo.get_room_object(_GEARWORKS)["current_state"] == "jammed"
    assert repo.get_room_object(_GREAT_LIFT)["current_state"] == "unpowered"
    assert counts["objects_reset"] >= 2

    # Ladder reset; clocks and stress zeroed.
    statuses = {o["tier_index"]: o["status"] for o in repo.get_objectives(CAMPAIGN_ID)}
    assert statuses == {0: "active", 1: "locked", 2: "locked", 3: "locked"}
    assert con.execute("SELECT COUNT(*) FROM clocks WHERE filled > 0").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM stress_tracks WHERE filled > 0").fetchone()[0] == 0

    # Items unowned again.
    assert con.execute(
        "SELECT COUNT(*) FROM items WHERE owner_actor_id IS NOT NULL"
    ).fetchone()[0] == 0

    # Play memory + events wiped; persona docs kept; play-memory md deleted.
    assert con.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0] == 0
    assert counts["memories_wiped"] == 1 and counts["events_wiped"] == 1
    assert not (save_dir / "memory" / "level_1.md").exists()
    assert (save_dir / "memory" / "dungeon" / "voice.md").exists()


def test_reset_is_idempotent(seeded):
    repo, save_dir = seeded
    _advance_the_game(repo, save_dir)

    reset_to_new_game(repo, save_dir, CAMPAIGN_ID)
    second = reset_to_new_game(repo, save_dir, CAMPAIGN_ID)

    # Nothing left to change on a second run.
    assert second == {
        "objects_reset": 0,
        "memories_wiped": 0,
        "events_wiped": 0,
        "play_memory_md_deleted": 0,
    }
    assert repo.get_room_object(_GEARWORKS)["current_state"] == "jammed"
