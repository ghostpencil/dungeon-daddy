"""Proposal validation — Phase 36."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from dungeon_daddy.rpg.proposal import (
    AdvanceClockChange,
    AdjustReputationChange,
    ApplyConsequenceChange,
    LLMReactionProposal,
    NpcReactionChange,
    ProposedChange,
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


def validate_proposal(
    proposal: LLMReactionProposal,
    known_clock_ids: set[str],
    known_actor_ids: set[str] | None = None,
    player_actor_ids: set[str] | None = None,
    known_faction_slugs: set[str] | None = None,
) -> ValidationResult:
    result = ValidationResult(source=proposal.source)
    actor_ids = known_actor_ids or set()
    player_ids = player_actor_ids or set()
    faction_slugs = known_faction_slugs or set()

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

        if rejection_reason is not None:
            _log.info("Proposal rejected [%s]: %s", change.kind, rejection_reason)
            result.rejected.append(RejectedChange(change=change, reason=rejection_reason))
        else:
            _log.info("Proposal accepted [%s]", change.kind)
            result.accepted.append(change)

    return result
