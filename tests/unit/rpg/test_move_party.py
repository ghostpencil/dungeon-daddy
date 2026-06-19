from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.command import MoveParty
from dungeon_daddy.rpg.models import Item, RoomExit
from dungeon_daddy.rpg.move_party import HOW_MODIFIER_FLAGS, apply_move_party

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)

CAMPAIGN_ID = "campaign:test"
ROOM_A = "room:a"
ROOM_B = "room:b"
EXIT_ID = "exit:1"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


@pytest.fixture
def session() -> SessionState:
    return SessionState(dungeon_id="dungeon:test", current_room_id=ROOM_A)


def _make_exit(
    exit_id: str = EXIT_ID,
    from_room_id: str = ROOM_A,
    to_room_id: str = ROOM_B,
    status: str = "open",
) -> RoomExit:
    return RoomExit(
        exit_id=exit_id,
        campaign_id=CAMPAIGN_ID,
        from_room_id=from_room_id,
        to_room_id=to_room_id,
        level_id="level:1",
        label="North Door",
        status=status,
    )


# ---------------------------------------------------------------------------
# Tracer bullet — happy path
# ---------------------------------------------------------------------------

def test_move_party_open_exit_accepted(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit(status="open"))
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    new_session, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is True
    assert new_session.current_room_id == ROOM_B


def test_move_party_exit_not_found(repo: MemoryRepository, session: SessionState) -> None:
    cmd = MoveParty(exit_id="exit:nonexistent", how="cautiously")

    _, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is False


def test_move_party_exit_not_from_current_room(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit(from_room_id="room:other"))
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    _, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is False


def test_move_party_locked_exit_rejected(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit(status="locked"))
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    _, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is False


def test_move_party_hidden_exit_rejected(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit(status="hidden"))
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    _, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is False


def test_move_party_discovered_exit_accepted(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit(status="discovered"))
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    new_session, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is True
    assert new_session.current_room_id == ROOM_B


# ---------------------------------------------------------------------------
# visited_rooms
# ---------------------------------------------------------------------------

def test_move_party_appends_to_visited_rooms(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit())
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    new_session, _ = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert ROOM_B in new_session.visited_rooms


def test_move_party_does_not_duplicate_visited_room(repo: MemoryRepository) -> None:
    session = SessionState(dungeon_id="dungeon:test", current_room_id=ROOM_A, visited_rooms=[ROOM_B])
    repo.save_room_exit(_make_exit())
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    new_session, _ = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert new_session.visited_rooms.count(ROOM_B) == 1


# ---------------------------------------------------------------------------
# one_way sealing
# ---------------------------------------------------------------------------

def test_move_party_seals_one_way_exit(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit(status="one_way"))
    cmd = MoveParty(exit_id=EXIT_ID, how="deliberately")

    apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    exit_row = repo.get_exit_by_id(EXIT_ID)
    assert exit_row is not None
    assert exit_row["status"] == "sealed"


# ---------------------------------------------------------------------------
# party.moved event
# ---------------------------------------------------------------------------

def test_move_party_emits_party_moved_event(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit())
    cmd = MoveParty(exit_id=EXIT_ID, how="boldly")

    _, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert len(result.events) == 1
    event = result.events[0]
    assert event.event_type == "party.moved"
    assert event.payload["exit_id"] == EXIT_ID
    assert event.payload["from_room_id"] == ROOM_A
    assert event.payload["to_room_id"] == ROOM_B
    assert event.payload["how"] == "boldly"


# ---------------------------------------------------------------------------
# Slice 5 — how? modifier flags
# ---------------------------------------------------------------------------

def test_how_modifier_flags_cautiously() -> None:
    assert HOW_MODIFIER_FLAGS["cautiously"] == {"suppress_entry_ticks", "trap_chance:-1"}


def test_how_modifier_flags_recklessly() -> None:
    assert HOW_MODIFIER_FLAGS["recklessly"] == {"skip_condition_checks", "force_trap_trigger"}


def test_move_party_populates_modifier_flags_on_success(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit())
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    _, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is True
    assert result.modifier_flags == {"suppress_entry_ticks", "trap_chance:-1"}


def test_move_party_unknown_how_yields_empty_flags(repo: MemoryRepository, session: SessionState) -> None:
    repo.save_room_exit(_make_exit())
    cmd = MoveParty(exit_id=EXIT_ID, how="sneakily")

    _, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is True
    assert result.modifier_flags == set()


# ---------------------------------------------------------------------------
# Slice 6 — Level connector transition
# ---------------------------------------------------------------------------

def _make_connector_exit(
    exit_id: str = EXIT_ID,
    from_room_id: str = ROOM_A,
    to_room_id: str = ROOM_B,
    from_level_id: str = "level:0",
    to_level_id: str = "level:1",
    connector_type: str = "stair_down",
) -> RoomExit:
    return RoomExit(
        exit_id=exit_id,
        campaign_id=CAMPAIGN_ID,
        from_room_id=from_room_id,
        to_room_id=to_room_id,
        level_id=from_level_id,
        label="Spiral Stair",
        status="open",
        connector_type=connector_type,
        to_level_id=to_level_id,
    )


def test_move_party_level_connector_updates_current_level_idx(repo: MemoryRepository) -> None:
    session = SessionState(dungeon_id="dungeon:test", current_room_id=ROOM_A, current_level_idx=0)
    repo.save_room_exit(_make_connector_exit())
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    new_session, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is True
    assert new_session.current_level_idx == 1


def _make_level_item(item_id: str, level_id: str) -> Item:
    return Item(
        item_id=item_id,
        campaign_id=CAMPAIGN_ID,
        slug=item_id.split(":")[-1],
        display_name="Relic",
        item_type="dungeon_item",
        description="A level-bound relic.",
        level_id=level_id,
    )


def test_move_party_level_connector_marks_old_level_items_inert(repo: MemoryRepository) -> None:
    session = SessionState(dungeon_id="dungeon:test", current_room_id=ROOM_A, current_level_idx=0)
    repo.save_room_exit(_make_connector_exit(from_level_id="level:0", to_level_id="level:1"))
    repo.save_item(_make_level_item("item:relic1", "level:0"))
    repo.save_item(_make_level_item("item:relic2", "level:0"))
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    items = {i["item_id"]: i for i in repo.get_items(CAMPAIGN_ID)}
    assert items["item:relic1"]["status"] == "inert"
    assert items["item:relic2"]["status"] == "inert"


def test_move_party_non_connector_does_not_change_level_idx(repo: MemoryRepository) -> None:
    session = SessionState(dungeon_id="dungeon:test", current_room_id=ROOM_A, current_level_idx=2)
    repo.save_room_exit(_make_exit(status="open"))
    cmd = MoveParty(exit_id=EXIT_ID, how="cautiously")

    new_session, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is True
    assert new_session.current_level_idx == 2


def test_move_party_recklessly_bypasses_condition_failure(repo: MemoryRepository, session: SessionState) -> None:
    exit_obj = RoomExit(
        exit_id=EXIT_ID,
        campaign_id=CAMPAIGN_ID,
        from_room_id=ROOM_A,
        to_room_id=ROOM_B,
        level_id="level:1",
        label="North Door",
        status="open",
        requires_item_slug="iron-key",
    )
    repo.save_room_exit(exit_obj)
    cmd = MoveParty(exit_id=EXIT_ID, how="recklessly")

    new_session, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is True
    assert new_session.current_room_id == ROOM_B
