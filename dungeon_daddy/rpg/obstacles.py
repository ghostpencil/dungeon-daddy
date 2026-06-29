"""Obstacle approaches & convergence (Phase 51.5 Part A).

An *obstacle* is a :class:`RoomObject` in a blocked state whose **contested**
transitions out of that state are multiple class-flavored "approaches" (e.g.
Artificer *tinker*, Fighter *fight*, Thief *finesse*). All approaches converge
on one canonical resolved state, so however the obstacle is overcome it ends in
the same state and the gated objective completes uniformly (#1).

These are pure helpers over the model — no repo, no LLM.
"""

from __future__ import annotations

from dungeon_daddy.rpg.models import ObjectTransition, RoomObject


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
