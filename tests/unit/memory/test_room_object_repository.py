from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ObjectTransition, RoomObject

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def _room_object(
    object_id: str = "obj:test:chest",
    campaign_id: str = "campaign:test",
    room_id: str = "room:test:vault",
    slug: str = "iron-chest",
) -> RoomObject:
    return RoomObject(
        object_id=object_id,
        campaign_id=campaign_id,
        room_id=room_id,
        level_id="level:test:1",
        slug=slug,
        display_name="Iron Chest",
        archetype="container",
        description="A heavy iron chest.",
        current_state="locked",
    )


def _transition(
    transition_id: str = "tr:test:1",
    object_id: str = "obj:test:chest",
) -> ObjectTransition:
    return ObjectTransition(
        transition_id=transition_id,
        object_id=object_id,
        from_state="locked",
        to_state="open",
        trigger="use_key",
        requires_item_slug="iron-key",
        spawns_item_slug="gold-coin",
        advances_clock_slug=None,
    )


class TestTransitions:
    def test_transitions_nested_in_get_room_object(self, repo: MemoryRepository) -> None:
        obj = _room_object().model_copy(update={"transitions": [_transition()]})
        repo.save_room_object(obj)
        result = repo.get_room_object("obj:test:chest")
        assert result is not None
        assert len(result["transitions"]) == 1
        t = result["transitions"][0]
        assert t["transition_id"] == "tr:test:1"
        assert t["from_state"] == "locked"
        assert t["to_state"] == "open"
        assert t["trigger"] == "use_key"
        assert t["requires_item_slug"] == "iron-key"
        assert t["spawns_item_slug"] == "gold-coin"
        assert t["advances_clock_slug"] is None

    def test_upsert_replaces_transitions(self, repo: MemoryRepository) -> None:
        obj = _room_object().model_copy(update={"transitions": [_transition()]})
        repo.save_room_object(obj)
        new_tr = _transition(transition_id="tr:test:2")
        updated = _room_object().model_copy(update={"transitions": [new_tr]})
        repo.save_room_object(updated)
        result = repo.get_room_object("obj:test:chest")
        assert result is not None
        assert len(result["transitions"]) == 1
        assert result["transitions"][0]["transition_id"] == "tr:test:2"


class TestUpdateObjectState:
    def test_update_state(self, repo: MemoryRepository) -> None:
        repo.save_room_object(_room_object())
        repo.update_object_state("obj:test:chest", "open")
        result = repo.get_room_object("obj:test:chest")
        assert result is not None
        assert result["current_state"] == "open"


class TestGetObjectsByRoom:
    def test_returns_only_that_room(self, repo: MemoryRepository) -> None:
        vault_obj = _room_object(object_id="obj:test:chest", room_id="room:test:vault", slug="iron-chest")
        hall_obj = _room_object(object_id="obj:test:door", room_id="room:test:hall", slug="iron-door")
        repo.save_room_object(vault_obj)
        repo.save_room_object(hall_obj)
        results = repo.get_objects_by_room("campaign:test", "room:test:vault")
        assert len(results) == 1
        assert results[0]["object_id"] == "obj:test:chest"

    def test_returns_empty_for_unknown_room(self, repo: MemoryRepository) -> None:
        repo.save_room_object(_room_object())
        results = repo.get_objects_by_room("campaign:test", "room:test:nowhere")
        assert results == []


class TestRoundTrip:
    def test_upsert_updates_no_duplicate(self, repo: MemoryRepository) -> None:
        repo.save_room_object(_room_object())
        updated = _room_object().model_copy(update={"display_name": "Gold Chest"})
        repo.save_room_object(updated)
        results = repo.get_objects_by_room("campaign:test", "room:test:vault")
        assert len(results) == 1
        assert results[0]["display_name"] == "Gold Chest"

    def test_save_and_get_by_id(self, repo: MemoryRepository) -> None:
        obj = _room_object()
        repo.save_room_object(obj)
        result = repo.get_room_object("obj:test:chest")
        assert result is not None
        assert result["object_id"] == "obj:test:chest"
        assert result["slug"] == "iron-chest"
        assert result["archetype"] == "container"
        assert result["description"] == "A heavy iron chest."
        assert result["current_state"] == "locked"
        assert result["transitions"] == []
