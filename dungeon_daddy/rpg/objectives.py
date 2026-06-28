"""Objective completion & advancement (Phase 51.5 §4.3.2).

The completion *predicate* is a pure helper — it decides whether an
``ObjectiveCompletion`` condition is satisfied given a snapshot of world state,
with no repo or LLM involvement (D4). The objective *service* (a later slice)
wraps it with persistence.
"""

from __future__ import annotations

from typing import Any, Mapping

from dungeon_daddy.rpg.models import ObjectiveCompletion


def completion_satisfied(
    completion: ObjectiveCompletion, world_state: Mapping[str, Any]
) -> bool:
    """Return whether ``completion`` is satisfied by ``world_state``.

    ``world_state`` is a deterministic snapshot the engine queries after each
    command (no event bus). For the primary ``object_state`` kind it carries an
    ``"objects"`` list of object dicts (the ``repo.get_objects_by_room`` shape,
    each with ``slug``/``current_state``); the condition holds when the target
    object is at ``required_state``.
    """
    if completion.kind == "object_state":
        for obj in world_state.get("objects", []):
            if obj.get("slug") == completion.target_slug:
                return obj.get("current_state") == completion.required_state
        return False
    raise NotImplementedError(
        f"completion kind {completion.kind!r} is not yet evaluated"
    )
