"""Obstacle approaches & convergence (Phase 51.5 Part A).

An *obstacle* is a :class:`RoomObject` in a blocked state whose **contested**
transitions out of that state are multiple class-flavored "approaches" (e.g.
Artificer *tinker*, Fighter *fight*, Thief *finesse*). All approaches converge
on one canonical resolved state, so however the obstacle is overcome it ends in
the same state and the gated objective completes uniformly (#1).

These are pure helpers over the model — no repo, no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass

from dungeon_daddy.rpg.dice import Outcome
from dungeon_daddy.rpg.models import ObjectTransition, RoomObject

# Locked outcome→success mapping (owner, 2026-06-29): a critical or full success
# resolves the obstacle cleanly; a partial resolves it but with a complication;
# a miss fails (no state change).
_RESOLVING_OUTCOMES: frozenset[Outcome] = frozenset({"critical", "full", "partial"})


def is_resolving_outcome(outcome: Outcome) -> bool:
    """Return whether a roll ``outcome`` resolves an obstacle (locked mapping).

    Crit/full/partial resolve (partial with a complication); a miss fails. Shared
    gate for both the contested-approach path (:func:`resolve_obstacle_with_roll`)
    and the DM-ruled proposal path (Part B).
    """
    return outcome in _RESOLVING_OUTCOMES


def resolving_trigger(obj: RoomObject, to_state: str) -> str | None:
    """Return the trigger of a transition from ``obj``'s current state to ``to_state``.

    Used by the DM-ruled path to route an accepted ``ResolveObstacleChange`` through
    the deterministic ``ActivateObject`` pipeline: the LLM names the resolved state,
    this finds a converging transition's trigger to actually apply it. Returns
    ``None`` when no such transition exists.
    """
    for t in obj.transitions:
        if t.from_state == obj.current_state and t.to_state == to_state:
            return t.trigger
    return None


def obstacle_approaches(obj: RoomObject) -> list[ObjectTransition]:
    """Return the contested transitions out of the object's current state.

    These are the multiple ways to solve the obstacle; each carries an
    ``action_verb``. Non-contested transitions (the deterministic ``activate``
    path) and transitions out of other states are excluded.
    """
    return [
        t
        for t in obj.transitions
        if t.contested and t.from_state == obj.current_state
    ]


def obstacle_approach_verbs(obj: RoomObject) -> list[str]:
    """Return the ``action_verb``s of the obstacle's current approaches, in order.

    These are the class-flavored verbs (tinker / fight / finesse / …) offered as
    *suggested actions* for the obstacle in the builder. Empty when the object is
    not an obstacle (no contested approaches out of ``current_state``).
    """
    return [t.action_verb for t in obstacle_approaches(obj) if t.action_verb]


def obstacle_resolved_state(obj: RoomObject) -> str | None:
    """Return the single canonical resolved state all approaches converge on.

    Returns ``None`` when the object has no contested approaches (it is not an
    obstacle). Raises :class:`ValueError` when the approaches diverge — an
    obstacle must converge so that every path completes the objective the same
    way (#1).
    """
    target_states = {t.to_state for t in obstacle_approaches(obj)}
    if not target_states:
        return None
    if len(target_states) > 1:
        raise ValueError(
            f"obstacle {obj.slug!r} approaches diverge to {sorted(target_states)}; "
            "all approaches must converge on one resolved state"
        )
    return target_states.pop()


@dataclass(frozen=True)
class ObstacleRollResolution:
    """A roll that overcomes an obstacle: which approach applied, at what cost."""

    transition: ObjectTransition
    complication: bool


def resolve_obstacle_with_roll(
    obj: RoomObject, verb: str, outcome: Outcome
) -> ObstacleRollResolution | None:
    """Decide whether an action roll overcomes the obstacle.

    Returns the matched approach (and whether it carries a complication) when
    ``verb`` matches one of the obstacle's contested approaches **and** the roll
    ``outcome`` resolves it per the locked mapping (crit/full clean, partial with
    a complication). Returns ``None`` on a miss or when ``verb`` is not an
    approach — the engine then leaves object state unchanged.
    """
    if outcome not in _RESOLVING_OUTCOMES:
        return None
    for t in obstacle_approaches(obj):
        if t.action_verb == verb:
            return ObstacleRollResolution(transition=t, complication=outcome == "partial")
    return None
