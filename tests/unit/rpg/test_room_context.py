from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import RoomExit
from dungeon_daddy.rpg.room_context import build_room_context

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)

CAMPAIGN_ID = "campaign:test"
ROOM_A = "room:a"
ROOM_B = "room:b"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def _make_exit(
    exit_id: str,
    status: str = "open",
    label: str = "North Door",
    requires_item_slug: str | None = None,
    requires_memory_slug: str | None = None,
) -> RoomExit:
    return RoomExit(
        exit_id=exit_id,
        campaign_id=CAMPAIGN_ID,
        from_room_id=ROOM_A,
        to_room_id=ROOM_B,
        level_id="level:1",
        label=label,
        status=status,
        requires_item_slug=requires_item_slug,
        requires_memory_slug=requires_memory_slug,
    )


def _session(visited: list[str] | None = None) -> SessionState:
    return SessionState(dungeon_id="dungeon:1", visited_rooms=visited or [ROOM_A])


# ---------------------------------------------------------------------------
# Slice 9-1: visible_exits contains only open exits
# ---------------------------------------------------------------------------

def test_visible_exits_contains_open_exit(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit("exit:open", status="open", label="North Door"))
    repo.save_room_exit(_make_exit("exit:locked", status="locked", label="Iron Gate"))

    result = build_room_context(ROOM_A, CAMPAIGN_ID, _session(), repo)

    labels = [e["label"] for e in result["visible_exits"]]
    assert "North Door" in labels
    assert "Iron Gate" not in labels


# ---------------------------------------------------------------------------
# Slice 9-2: visible_exits includes discovered exits
# ---------------------------------------------------------------------------

def test_visible_exits_includes_discovered_exit(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit("exit:disc", status="discovered", label="Hidden Arch"))

    result = build_room_context(ROOM_A, CAMPAIGN_ID, _session(), repo)

    labels = [e["label"] for e in result["visible_exits"]]
    assert "Hidden Arch" in labels


# ---------------------------------------------------------------------------
# Slice 9-3: locked_exits includes locked exit with reason and missing_condition
# ---------------------------------------------------------------------------

def test_locked_exits_has_reason_and_missing_condition(repo: MemoryRepository) -> None:
    repo.save_room_exit(
        _make_exit("exit:locked", status="locked", label="Iron Gate", requires_item_slug="iron-key")
    )

    result = build_room_context(ROOM_A, CAMPAIGN_ID, _session(), repo)

    assert len(result["locked_exits"]) == 1
    entry = result["locked_exits"][0]
    assert entry["reason"] == "locked"
    assert entry["missing_condition"] == "iron-key"
    assert entry["label"] == "Iron Gate"


# ---------------------------------------------------------------------------
# Slice 9-4: locked_exits includes blocked exits
# ---------------------------------------------------------------------------

def test_locked_exits_includes_blocked_exit(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit("exit:blocked", status="blocked", label="Collapsed Tunnel"))

    result = build_room_context(ROOM_A, CAMPAIGN_ID, _session(), repo)

    reasons = [e["reason"] for e in result["locked_exits"]]
    assert "blocked" in reasons


# ---------------------------------------------------------------------------
# Slice 9-5: locked_exits includes one_way exits
# ---------------------------------------------------------------------------

def test_locked_exits_includes_one_way_exit(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit("exit:one_way", status="one_way", label="Drop Shaft"))

    result = build_room_context(ROOM_A, CAMPAIGN_ID, _session(), repo)

    reasons = [e["reason"] for e in result["locked_exits"]]
    assert "one_way" in reasons


# ---------------------------------------------------------------------------
# Slice 9-6: hidden_exit_hint is 0 when no PC has sense >= 2
# ---------------------------------------------------------------------------

def test_hidden_exit_hint_zero_when_no_pc_has_high_sense(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit("exit:hidden", status="hidden"))
    repo.save_actor("actor:fighter", CAMPAIGN_ID, "pc", "fighter", "Fighter")
    repo.save_actor_action_rating("actor:fighter", "sense", 1)

    result = build_room_context(ROOM_A, CAMPAIGN_ID, _session(), repo)

    assert result["hidden_exit_hint"] == 0


# ---------------------------------------------------------------------------
# Slice 9-7: hidden_exit_hint returns count when a PC has sense >= 2
# ---------------------------------------------------------------------------

def test_hidden_exit_hint_returns_count_when_pc_has_sense_2(repo: MemoryRepository) -> None:
    repo.save_room_exit(_make_exit("exit:h1", status="hidden"))
    repo.save_room_exit(_make_exit("exit:h2", status="hidden"))
    repo.save_actor("actor:scout", CAMPAIGN_ID, "pc", "scout", "Scout")
    repo.save_actor_action_rating("actor:scout", "sense", 2)

    result = build_room_context(ROOM_A, CAMPAIGN_ID, _session(), repo)

    assert result["hidden_exit_hint"] == 2


# ---------------------------------------------------------------------------
# Slice 9-8: visited_rooms comes from session
# ---------------------------------------------------------------------------

def test_visited_rooms_comes_from_session(repo: MemoryRepository) -> None:
    session = SessionState(dungeon_id="d:1", visited_rooms=[ROOM_A, ROOM_B])

    result = build_room_context(ROOM_A, CAMPAIGN_ID, session, repo)

    assert result["visited_rooms"] == [ROOM_A, ROOM_B]


# ---------------------------------------------------------------------------
# Slice 9-9: resonance_point defaults to False; True is passed through
# ---------------------------------------------------------------------------

def test_resonance_point_defaults_to_false(repo: MemoryRepository) -> None:
    result = build_room_context(ROOM_A, CAMPAIGN_ID, _session(), repo)
    assert result["resonance_point"] is False


def test_resonance_point_true_is_passed_through(repo: MemoryRepository) -> None:
    result = build_room_context(ROOM_A, CAMPAIGN_ID, _session(), repo, resonance_point=True)
    assert result["resonance_point"] is True
