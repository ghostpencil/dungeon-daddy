from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.discover_exit import discover_exit
from dungeon_daddy.rpg.models import RoomExit

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)

CAMPAIGN_ID = "campaign:test"
ROOM_A = "room:a"
EXIT_ID = "exit:hidden-1"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def _make_exit(exit_id: str = EXIT_ID, status: str = "hidden") -> RoomExit:
    return RoomExit(
        exit_id=exit_id,
        campaign_id=CAMPAIGN_ID,
        from_room_id=ROOM_A,
        to_room_id="room:b",
        level_id="level:1",
        label="Concealed Passage",
        status=status,
    )


# ---------------------------------------------------------------------------
# Slice 7-1: discover_exit flips hidden → discovered
# ---------------------------------------------------------------------------

def test_discover_exit_flips_status_to_discovered(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit(status="hidden"))

    result = discover_exit(EXIT_ID, CAMPAIGN_ID, "Found a concealed passage.", repo)

    assert result.accepted is True
    row = repo.get_exit_by_id(EXIT_ID)
    assert row["status"] == "discovered"


# ---------------------------------------------------------------------------
# Slice 7-2: discover_exit creates an approved memory entry
# ---------------------------------------------------------------------------

def test_discover_exit_creates_approved_memory_entry(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit(status="hidden"))

    discover_exit(EXIT_ID, CAMPAIGN_ID, "Found a concealed passage.", repo)

    entries = repo.get_memory_entries_by_campaign(CAMPAIGN_ID)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["title"] == "Found a concealed passage."
    assert entry["status"] == "approved"


# ---------------------------------------------------------------------------
# A5b: discover_exit stamps scene-anchor tags on its memory
# ---------------------------------------------------------------------------

def test_discover_exit_stamps_scene_anchor_tags(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit(status="hidden"))
    repo.save_actor("pc-1", CAMPAIGN_ID, "pc", "scout", "Scout", room_id=ROOM_A)

    discover_exit(
        EXIT_ID,
        CAMPAIGN_ID,
        "Found a concealed passage.",
        repo,
        room_id=ROOM_A,
        party_ids=["pc-1"],
    )

    entry = repo.get_memory_entries_by_campaign(CAMPAIGN_ID)[0]
    tags = set(repo.get_memory_tags(entry["memory_id"]))
    assert tags == {"location:room:a", "actor:pc:scout"}


def test_discover_exit_untagged_without_scene(repo: MemoryRepository) -> None:
    # Back-compat: the pre-A5b call shape (no room/party) writes no tags.
    repo.save_room_exit(_make_exit(status="hidden"))

    discover_exit(EXIT_ID, CAMPAIGN_ID, "Found a concealed passage.", repo)

    entry = repo.get_memory_entries_by_campaign(CAMPAIGN_ID)[0]
    assert repo.get_memory_tags(entry["memory_id"]) == []


# ---------------------------------------------------------------------------
# Slice 7-3: discover_exit emits an exit.discovered domain event
# ---------------------------------------------------------------------------

def test_discover_exit_emits_domain_event(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit(status="hidden"))

    result = discover_exit(EXIT_ID, CAMPAIGN_ID, "Found a concealed passage.", repo)

    assert len(result.events) == 1
    event = result.events[0]
    assert event.event_type == "exit.discovered"
    assert event.payload["exit_id"] == EXIT_ID


# ---------------------------------------------------------------------------
# Slice 7-4: discover_exit rejects a non-hidden exit
# ---------------------------------------------------------------------------

def test_discover_exit_rejects_open_exit(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit(status="open"))

    result = discover_exit(EXIT_ID, CAMPAIGN_ID, "Found something.", repo)

    assert result.accepted is False
    assert result.rejection_reason is not None
    row = repo.get_exit_by_id(EXIT_ID)
    assert row["status"] == "open"


# ---------------------------------------------------------------------------
# Slice 7-5: repo.get_hidden_exit_count counts hidden exits in a room
# ---------------------------------------------------------------------------

def test_get_hidden_exit_count(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit(exit_id="exit:h1", status="hidden"))
    repo.save_room_exit(_make_exit(exit_id="exit:h2", status="hidden"))
    repo.save_room_exit(_make_exit(exit_id="exit:open", status="open"))

    count = repo.get_hidden_exit_count(CAMPAIGN_ID, ROOM_A)

    assert count == 2


# ---------------------------------------------------------------------------
# Slice 7-6: passive_hidden_exit_hint returns count when a PC has sense >= 2
# ---------------------------------------------------------------------------

def test_passive_hint_returns_count_when_pc_has_high_sense(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.discover_exit import passive_hidden_exit_hint

    repo.save_room_exit(_make_exit(exit_id="exit:h1", status="hidden"))
    repo.save_room_exit(_make_exit(exit_id="exit:h2", status="hidden"))

    actor_id = "actor:scout"
    repo.save_actor(actor_id, CAMPAIGN_ID, "pc", "scout", "Scout")
    repo.save_actor_action_rating(actor_id, "sense", 2)

    hint = passive_hidden_exit_hint(CAMPAIGN_ID, ROOM_A, repo)

    assert hint == 2


# ---------------------------------------------------------------------------
# Slice 7-7: passive_hidden_exit_hint returns 0 when no PC has sense >= 2
# ---------------------------------------------------------------------------

def test_passive_hint_returns_zero_when_no_pc_has_high_sense(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.discover_exit import passive_hidden_exit_hint

    repo.save_room_exit(_make_exit(exit_id="exit:h1", status="hidden"))

    actor_id = "actor:fighter"
    repo.save_actor(actor_id, CAMPAIGN_ID, "pc", "fighter", "Fighter")
    repo.save_actor_action_rating(actor_id, "sense", 1)

    hint = passive_hidden_exit_hint(CAMPAIGN_ID, ROOM_A, repo)

    assert hint == 0
