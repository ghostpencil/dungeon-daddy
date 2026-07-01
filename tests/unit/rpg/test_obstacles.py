"""Phase 51.5 Part A Slice 1 — obstacle approaches & convergence validation.

An *obstacle* is a ``RoomObject`` in a blocked state whose contested transitions
out of that state are multiple class-flavored "approaches" (tinker / fight /
finesse / …) that all converge on one canonical resolved state. These pure
helpers extract those approaches and validate the convergence.
"""

from __future__ import annotations

import pytest

from dungeon_daddy.rpg.models import ObjectTransition, RoomObject
from dungeon_daddy.rpg.obstacles import (
    obstacle_approach_verbs,
    obstacle_approaches,
    obstacle_resolved_state,
    resolve_obstacle_with_roll,
)


def _obstacle(*transitions: ObjectTransition, current_state: str = "jammed") -> RoomObject:
    return RoomObject(
        object_id="obj:c:gearworks",
        campaign_id="c",
        room_id="room:forge",
        level_id="level:1",
        slug="gearworks",
        display_name="Seized Gearworks",
        archetype="mechanism",
        description="A jammed tangle of brass gears.",
        current_state=current_state,
        transitions=list(transitions),
    )


def _approach(verb: str, *, from_state: str = "jammed", to_state: str = "cleared") -> ObjectTransition:
    return ObjectTransition(
        transition_id=f"tr:{verb}",
        object_id="obj:c:gearworks",
        from_state=from_state,
        to_state=to_state,
        trigger=verb,
        contested=True,
        action_verb=verb,
    )


class TestObstacleApproaches:
    def test_returns_only_contested_transitions_from_current_state(self) -> None:
        tinker = _approach("tinker")
        fight = _approach("fight")
        # A non-contested transition (deterministic activate path) is not an approach.
        deterministic = ObjectTransition(
            transition_id="tr:reset",
            object_id="obj:c:gearworks",
            from_state="jammed",
            to_state="reset",
            trigger="reset",
        )
        # A contested transition from a *different* state is not a current approach.
        from_other = _approach("scrap", from_state="cleared", to_state="dismantled")

        obj = _obstacle(tinker, fight, deterministic, from_other)

        approaches = obstacle_approaches(obj)

        assert [t.action_verb for t in approaches] == ["tinker", "fight"]


class TestObstacleApproachVerbs:
    def test_returns_action_verbs_of_current_approaches_in_order(self) -> None:
        obj = _obstacle(_approach("tinker"), _approach("fight"))

        assert obstacle_approach_verbs(obj) == ["tinker", "fight"]

    def test_empty_when_not_an_obstacle(self) -> None:
        deterministic = ObjectTransition(
            transition_id="tr:open",
            object_id="obj:c:gearworks",
            from_state="jammed",
            to_state="open",
            trigger="open",
        )
        obj = _obstacle(deterministic)

        assert obstacle_approach_verbs(obj) == []


class TestObstacleResolvedState:
    def test_returns_shared_to_state_when_approaches_converge(self) -> None:
        obj = _obstacle(
            _approach("tinker", to_state="cleared"),
            _approach("fight", to_state="cleared"),
            _approach("finesse", to_state="cleared"),
        )

        assert obstacle_resolved_state(obj) == "cleared"

    def test_raises_when_approaches_diverge(self) -> None:
        obj = _obstacle(
            _approach("tinker", to_state="cleared"),
            _approach("fight", to_state="shattered"),
        )

        with pytest.raises(ValueError):
            obstacle_resolved_state(obj)

    def test_returns_none_when_no_approaches(self) -> None:
        # A plain object with only a deterministic transition is not an obstacle.
        deterministic = ObjectTransition(
            transition_id="tr:open",
            object_id="obj:c:gearworks",
            from_state="jammed",
            to_state="open",
            trigger="open",
        )
        obj = _obstacle(deterministic)

        assert obstacle_resolved_state(obj) is None


class TestResolveObstacleWithRoll:
    """Locked outcome mapping: crit/full resolve; partial resolves with a
    complication; miss fails."""

    def test_full_success_matching_verb_resolves_without_complication(self) -> None:
        obj = _obstacle(_approach("tinker"), _approach("fight"))

        res = resolve_obstacle_with_roll(obj, verb="tinker", outcome="full")

        assert res is not None
        assert res.transition.action_verb == "tinker"
        assert res.transition.to_state == "cleared"
        assert res.complication is False

    def test_critical_matching_verb_resolves_without_complication(self) -> None:
        obj = _obstacle(_approach("tinker"))

        res = resolve_obstacle_with_roll(obj, verb="tinker", outcome="critical")

        assert res is not None and res.complication is False

    def test_partial_matching_verb_resolves_with_complication(self) -> None:
        obj = _obstacle(_approach("fight"))

        res = resolve_obstacle_with_roll(obj, verb="fight", outcome="partial")

        assert res is not None
        assert res.transition.action_verb == "fight"
        assert res.complication is True

    def test_miss_does_not_resolve(self) -> None:
        obj = _obstacle(_approach("fight"))

        assert resolve_obstacle_with_roll(obj, verb="fight", outcome="miss") is None

    def test_verb_not_an_approach_does_not_resolve(self) -> None:
        obj = _obstacle(_approach("tinker"), _approach("fight"))

        assert resolve_obstacle_with_roll(obj, verb="finesse", outcome="full") is None
