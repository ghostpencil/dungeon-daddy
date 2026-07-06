from __future__ import annotations

from dungeon_daddy.rpg.exit_validator import validate_exit_conditions
from dungeon_daddy.rpg.models import RoomExit

CAMPAIGN = "campaign:test"
EXIT_ID = "exit:test:001"


def _exit(**kwargs) -> RoomExit:
    defaults = dict(
        exit_id=EXIT_ID,
        campaign_id=CAMPAIGN,
        from_room_id="room:foyer",
        to_room_id="room:hall",
        level_id="level:1",
        label="North Door",
    )
    defaults.update(kwargs)
    return RoomExit(**defaults)


# ---------------------------------------------------------------------------
# Behavior 1: exit with no conditions always passes
# ---------------------------------------------------------------------------

class TestNoConditions:
    def test_unconditional_exit_passes(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(),
            inventory_slugs=[],
            room_objects=[],
            clocks=[],
            approved_memory_slugs=[],
        )
        assert result is None


# ---------------------------------------------------------------------------
# Behavior 2: item condition
# ---------------------------------------------------------------------------

class TestItemCondition:
    def test_item_present_passes(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_item_slug="iron-key"),
            inventory_slugs=["iron-key", "torch"],
            room_objects=[],
            clocks=[],
            approved_memory_slugs=[],
        )
        assert result is None

    def test_item_missing_returns_failure(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_item_slug="iron-key", label="Spiral Stair"),
            inventory_slugs=["torch"],
            room_objects=[],
            clocks=[],
            approved_memory_slugs=[],
        )
        assert result == {"reason": "locked", "missing": "iron-key", "label": "Spiral Stair"}

    def test_empty_inventory_returns_failure(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_item_slug="iron-key"),
            inventory_slugs=[],
            room_objects=[],
            clocks=[],
            approved_memory_slugs=[],
        )
        assert result is not None
        assert result["reason"] == "locked"


# ---------------------------------------------------------------------------
# Behavior 3: object-state condition
# ---------------------------------------------------------------------------

class TestObjectStateCondition:
    _DOOR_OBJ_ID = "obj:test:iron-door"

    def test_object_in_required_state_passes(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_object_id=self._DOOR_OBJ_ID, requires_object_state="unlocked"),
            inventory_slugs=[],
            room_objects=[{"object_id": self._DOOR_OBJ_ID, "current_state": "unlocked"}],
            clocks=[],
            approved_memory_slugs=[],
        )
        assert result is None

    def test_object_in_wrong_state_returns_failure(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_object_id=self._DOOR_OBJ_ID, requires_object_state="unlocked", label="Iron Gate"),
            inventory_slugs=[],
            room_objects=[{"object_id": self._DOOR_OBJ_ID, "current_state": "locked"}],
            clocks=[],
            approved_memory_slugs=[],
        )
        assert result == {"reason": "locked", "missing": self._DOOR_OBJ_ID, "label": "Iron Gate"}

    def test_object_not_in_room_returns_failure(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_object_id=self._DOOR_OBJ_ID, requires_object_state="unlocked"),
            inventory_slugs=[],
            room_objects=[],
            clocks=[],
            approved_memory_slugs=[],
        )
        assert result is not None
        assert result["reason"] == "locked"


# ---------------------------------------------------------------------------
# Behavior 4: clock condition
# ---------------------------------------------------------------------------

def _clock(slug: str, filled: int, segments: int = 4, status: str = "active") -> dict:
    return {
        "clock_id": f"clock:test:{slug}",
        "filled": filled,
        "segments": segments,
        "status": status,
    }


class TestClockCondition:
    def test_clock_at_min_filled_passes(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_clock_slug="ritual", requires_clock_min_filled=3),
            inventory_slugs=[],
            room_objects=[],
            clocks=[_clock("ritual", filled=3)],
            approved_memory_slugs=[],
        )
        assert result is None

    def test_clock_above_min_filled_passes(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_clock_slug="ritual", requires_clock_min_filled=2),
            inventory_slugs=[],
            room_objects=[],
            clocks=[_clock("ritual", filled=4)],
            approved_memory_slugs=[],
        )
        assert result is None

    def test_clock_under_min_filled_returns_failure(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_clock_slug="ritual", requires_clock_min_filled=3, label="Dream Bridge"),
            inventory_slugs=[],
            room_objects=[],
            clocks=[_clock("ritual", filled=2)],
            approved_memory_slugs=[],
        )
        assert result == {"reason": "locked", "missing": "ritual", "label": "Dream Bridge"}

    def test_completed_clock_always_passes_regardless_of_min(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_clock_slug="ritual", requires_clock_min_filled=4),
            inventory_slugs=[],
            room_objects=[],
            clocks=[_clock("ritual", filled=0, status="completed")],
            approved_memory_slugs=[],
        )
        assert result is None

    def test_clock_not_found_returns_failure(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_clock_slug="ritual", requires_clock_min_filled=1),
            inventory_slugs=[],
            room_objects=[],
            clocks=[],
            approved_memory_slugs=[],
        )
        assert result is not None
        assert result["reason"] == "locked"


# ---------------------------------------------------------------------------
# Behavior 5: memory condition
# ---------------------------------------------------------------------------

class TestMemoryCondition:
    _MEM_SLUG = "mem:test:spoke-the-vow"

    def test_approved_memory_present_passes(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_memory_slug=self._MEM_SLUG),
            inventory_slugs=[],
            room_objects=[],
            clocks=[],
            approved_memory_slugs=[self._MEM_SLUG, "mem:test:other"],
        )
        assert result is None

    def test_memory_not_approved_returns_failure(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(requires_memory_slug=self._MEM_SLUG, label="Ritual Gate"),
            inventory_slugs=[],
            room_objects=[],
            clocks=[],
            approved_memory_slugs=[],
        )
        assert result == {"reason": "locked", "missing": self._MEM_SLUG, "label": "Ritual Gate"}


# ---------------------------------------------------------------------------
# Behavior 6: multiple conditions — all pass, then one fails
# ---------------------------------------------------------------------------

class TestMultipleConditions:
    def test_all_conditions_met_passes(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(
                requires_item_slug="iron-key",
                requires_object_id="obj:gate",
                requires_object_state="unlocked",
                requires_clock_slug="ritual",
                requires_clock_min_filled=2,
                requires_memory_slug="mem:vow",
            ),
            inventory_slugs=["iron-key"],
            room_objects=[{"object_id": "obj:gate", "current_state": "unlocked"}],
            clocks=[_clock("ritual", filled=3)],
            approved_memory_slugs=["mem:vow"],
        )
        assert result is None

    def test_one_condition_fails_returns_failure(self) -> None:
        result = validate_exit_conditions(
            exit_obj=_exit(
                requires_item_slug="iron-key",
                requires_clock_slug="ritual",
                requires_clock_min_filled=4,
            ),
            inventory_slugs=["iron-key"],
            room_objects=[],
            clocks=[_clock("ritual", filled=2)],
            approved_memory_slugs=[],
        )
        assert result is not None
        assert result["reason"] == "locked"
