"""Phase 51.5 Slice 3 — pure completion predicate (spec §4.3.2)."""

from __future__ import annotations

import pytest

from dungeon_daddy.rpg.models import ObjectiveCompletion
from dungeon_daddy.rpg.objectives import completion_satisfied


class TestCompletionSatisfiedObjectState:
    def test_target_object_at_required_state_is_satisfied(self) -> None:
        completion = ObjectiveCompletion(
            kind="object_state", target_slug="coolant-loop", required_state="restored"
        )
        world_state = {"objects": [{"slug": "coolant-loop", "current_state": "restored"}]}

        assert completion_satisfied(completion, world_state) is True

    def test_target_object_in_wrong_state_is_not_satisfied(self) -> None:
        completion = ObjectiveCompletion(
            kind="object_state", target_slug="coolant-loop", required_state="restored"
        )
        world_state = {"objects": [{"slug": "coolant-loop", "current_state": "damaged"}]}

        assert completion_satisfied(completion, world_state) is False

    def test_target_object_absent_is_not_satisfied(self) -> None:
        completion = ObjectiveCompletion(
            kind="object_state", target_slug="coolant-loop", required_state="restored"
        )
        world_state = {"objects": [{"slug": "reactor", "current_state": "restored"}]}

        assert completion_satisfied(completion, world_state) is False

    def test_empty_world_state_is_not_satisfied(self) -> None:
        completion = ObjectiveCompletion(
            kind="object_state", target_slug="coolant-loop", required_state="restored"
        )

        assert completion_satisfied(completion, {}) is False


class TestCompletionSatisfiedUnsupportedKind:
    def test_unsupported_kind_raises(self) -> None:
        completion = ObjectiveCompletion(kind="item_obtained", target_slug="cipher-key")

        with pytest.raises(NotImplementedError):
            completion_satisfied(completion, {"objects": []})
