"""Proposal validation — Phase 36."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Literal

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.rpg.proposal import (
    AdjustReputationChange,
    AdvanceClockChange,
    ApplyConsequenceChange,
    BlockExitChange,
    GrantItemChange,
    LLMReactionProposal,
    NpcReactionChange,
    ProposedChange,
    ResolveObstacleChange,
    StripItemChange,
    TransformItemChange,
)

_log = logging.getLogger(__name__)


@dataclass
class RejectedChange:
    change: ProposedChange
    reason: str


@dataclass
class ValidationResult:
    accepted: list[ProposedChange] = field(default_factory=list)
    rejected: list[RejectedChange] = field(default_factory=list)
    source: Literal["deterministic", "llm_draft", "human_approved"] = "llm_draft"
    parse_status: str | None = None
    rejection_events: list[DomainEvent] = field(default_factory=list)


def validate_proposal(
    proposal: LLMReactionProposal,
    known_clock_ids: set[str],
    known_actor_ids: set[str] | None = None,
    player_actor_ids: set[str] | None = None,
    known_faction_slugs: set[str] | None = None,
    known_item_ids: set[str] | None = None,
    known_item_slugs: set[str] | None = None,
    dungeon_item_counts: dict[str, int] | None = None,
    known_exit_ids: set[str] | None = None,
    obstacle_resolved_states: dict[str, str] | None = None,
) -> ValidationResult:
    result = ValidationResult(source=proposal.source)
    actor_ids = known_actor_ids or set()
    player_ids = player_actor_ids or set()
    faction_slugs = known_faction_slugs or set()
    item_ids = known_item_ids or set()
    item_slugs = known_item_slugs or set()
    di_counts = dungeon_item_counts or {}
    exit_ids = known_exit_ids or set()
    resolved_states = obstacle_resolved_states or {}

    for change in proposal.proposed_changes:
        rejection_reason: str | None = None

        if isinstance(change, AdvanceClockChange):
            if change.clock_id not in known_clock_ids:
                rejection_reason = f"Unknown clock reference: {change.clock_id}"
        elif isinstance(change, ApplyConsequenceChange):
            if change.actor_id not in actor_ids:
                rejection_reason = f"Unknown actor reference: {change.actor_id}"
        elif isinstance(change, NpcReactionChange):
            if change.npc_id in player_ids:
                rejection_reason = f"Player actor intent control: {change.npc_id}"
            elif change.npc_id not in actor_ids:
                rejection_reason = f"Unknown actor reference: {change.npc_id}"
        elif isinstance(change, AdjustReputationChange):
            if change.faction_slug not in faction_slugs:
                rejection_reason = f"Unknown faction slug: {change.faction_slug}"
        elif isinstance(change, GrantItemChange):
            if change.to_actor_id not in actor_ids:
                rejection_reason = f"Unknown actor reference: {change.to_actor_id}"
            elif change.item_slug not in item_slugs:
                rejection_reason = f"Unknown item slug: {change.item_slug}"
            elif di_counts.get(change.to_actor_id, 0) >= 10:
                rejection_reason = f"Actor at dungeon-item cap: {change.to_actor_id}"
        elif isinstance(change, StripItemChange):
            if change.item_id not in item_ids:
                rejection_reason = f"Unknown item reference: {change.item_id}"
        elif isinstance(change, TransformItemChange):
            if change.item_id not in item_ids:
                rejection_reason = f"Unknown item reference: {change.item_id}"
        elif isinstance(change, BlockExitChange):
            if change.exit_id not in exit_ids:
                rejection_reason = f"Unknown exit reference: {change.exit_id}"
        elif isinstance(change, ResolveObstacleChange):
            authored = resolved_states.get(change.object_slug)
            if authored is None:
                rejection_reason = f"Unknown obstacle reference: {change.object_slug}"
            elif change.to_state != authored:
                rejection_reason = (
                    f"Obstacle {change.object_slug!r} cannot be pushed to "
                    f"{change.to_state!r}; authored resolved state is {authored!r}"
                )

        if rejection_reason is not None:
            _log.info("Proposal rejected [%s]: %s", change.kind, rejection_reason)
            result.rejected.append(RejectedChange(change=change, reason=rejection_reason))
            result.rejection_events.append(DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id="",
                event_type="proposal.rejected",
                payload={"kind": change.kind, "reason": rejection_reason},
            ))
        else:
            _log.info("Proposal accepted [%s]", change.kind)
            result.accepted.append(change)

    return result
