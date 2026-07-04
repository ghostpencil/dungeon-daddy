"""Objective completion & advancement (Phase 51.5 §4.3.2).

The completion *predicate* is a pure helper — it decides whether an
``ObjectiveCompletion`` condition is satisfied given a snapshot of world state,
with no repo or LLM involvement (D4). The objective *service* (a later slice)
wraps it with persistence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

from dungeon_daddy.rpg.clocks import tick_clock
from dungeon_daddy.rpg.models import ClockState, ObjectiveCompletion

if TYPE_CHECKING:  # avoid a hard import cycle; the service only needs the repo at runtime
    from dungeon_daddy.memory.repository import MemoryRepository

# One objective completion advances the latching intimacy clock by exactly one
# tier (D6: segments = #tiers, filled = #completed objectives). The objective
# service is the *single* source of the intimacy tick (D5).
OBJECTIVE_INTIMACY_DELTA = 1

# Completing an objective restores a dungeon subsystem; the engine records a
# ``dungeon_state`` memory. Owner override (2026-06-28): written **approved**
# (not draft) so the milestone is not queued for curation and feeds back through
# MemoryRetriever — the engine composes it; the LLM never authors memory.
OBJECTIVE_MEMORY_TYPE = "dungeon_state"


@dataclass(frozen=True)
class ObjectiveResult:
    """Outcome of completing one objective during :func:`advance_objectives`."""

    objective_id: str
    slug: str
    tier_index: int
    clock: ClockState | None
    memory_id: str
    activated_objective_ids: list[str]


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


def advance_objectives(
    repo: "MemoryRepository", campaign_id: str
) -> list[ObjectiveResult]:
    """Complete satisfied active objectives, advancing the intimacy ladder.

    Deterministic and engine-applied (D4) — never the LLM. For each **active**
    objective whose completion condition is satisfied by current world state:

    1. mark it ``completed``;
    2. tick + persist its intimacy clock (the single intimacy-tick source, D5);
    3. flip the next tier's locked objective(s) to ``active``;
    4. draft a ``dungeon_state`` memory (reuses the Phase 51 D4 engine-draft).

    Returns one :class:`ObjectiveResult` per objective completed this pass.
    """
    objectives = repo.get_objectives(campaign_id)
    world_state = {"objects": repo.get_objects_for_campaign(campaign_id)}
    clocks = repo.get_clocks(campaign_id)

    results: list[ObjectiveResult] = []
    for obj in objectives:
        if obj["status"] != "active":
            continue
        if not completion_satisfied(ObjectiveCompletion(**obj["completion"]), world_state):
            continue

        repo.update_objective_status(obj["objective_id"], "completed")
        obj["status"] = "completed"

        ticked = _tick_intimacy(repo, clocks, obj.get("advances_clock_slug"))
        activated = _activate_next_tier(repo, objectives, obj["tier_index"])

        memory_id = str(uuid.uuid4())
        repo.save_memory_entry(
            memory_id=memory_id,
            campaign_id=campaign_id,
            entry_type=OBJECTIVE_MEMORY_TYPE,
            title=f"Objective complete: {obj['title']}",
            summary=(
                f"The dungeon registered the completion of {obj['title']!r} "
                f"(tier {obj['tier_index']})."
            ),
            status="approved",
        )

        results.append(
            ObjectiveResult(
                objective_id=obj["objective_id"],
                slug=obj["slug"],
                tier_index=obj["tier_index"],
                clock=ticked,
                memory_id=memory_id,
                activated_objective_ids=activated,
            )
        )
    return results


def _tick_intimacy(
    repo: "MemoryRepository", clocks: list[dict], clock_slug: str | None
) -> ClockState | None:
    """Tick + persist the clock whose ``category`` matches ``clock_slug``."""
    if not clock_slug:
        return None
    for row in clocks:
        if row.get("category") == clock_slug:
            ticked = tick_clock(ClockState(**row), OBJECTIVE_INTIMACY_DELTA)
            repo.update_clock_progress(ticked.clock_id, ticked.filled, ticked.status)
            # Keep the in-memory snapshot current so a second completion this
            # pass ticks from the updated fill, not the stale one.
            row["filled"] = ticked.filled
            row["status"] = ticked.status
            return ticked
    return None


def _activate_next_tier(
    repo: "MemoryRepository", objectives: list[dict], completed_tier: int
) -> list[str]:
    """Flip the next tier's locked objective(s) to ``active``."""
    activated: list[str] = []
    for other in objectives:
        if other["tier_index"] == completed_tier + 1 and other["status"] == "locked":
            repo.update_objective_status(other["objective_id"], "active")
            other["status"] = "active"
            activated.append(other["objective_id"])
    return activated
