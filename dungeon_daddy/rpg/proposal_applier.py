"""Proposal applier — Phase 36: auto-apply low-risk proposals."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.proposal import AdjustReputationChange, ApplyConsequenceChange, CreateMemoryChange, ProposedChange
from dungeon_daddy.rpg.proposal_validator import ValidationResult


@dataclass
class ApplyResult:
    applied: list[ProposedChange] = field(default_factory=list)
    skipped: list[ProposedChange] = field(default_factory=list)
    events: list[DomainEvent] = field(default_factory=list)


def apply_low_risk_proposals(
    validation_result: ValidationResult,
    repo: MemoryRepository,
    campaign_id: str,
    action_key: str | None = None,
    intent: str | None = None,
    matched_clocks: list | None = None,
) -> ApplyResult:
    result = ApplyResult()

    for change in validation_result.accepted:
        if isinstance(change, CreateMemoryChange):
            memory_id = str(uuid.uuid4())
            repo.save_memory_entry(
                memory_id=memory_id,
                campaign_id=campaign_id,
                entry_type="event",
                title=change.title,
                summary=change.summary,
                importance=change.importance,
            )
            for tag in change.tags:
                repo.add_memory_tag(memory_id, tag)
            event = DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="memory_created",
                payload={
                    "memory_id": memory_id,
                    "title": change.title,
                    "source": validation_result.source,
                },
            )
            repo.insert_domain_event(event)
            applied_event = DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="proposal.applied",
                payload={"kind": change.kind, "reason": None},
            )
            repo.insert_domain_event(applied_event)
            result.applied.append(change)
            result.events.append(event)
        elif isinstance(change, AdjustReputationChange):
            factions = repo.get_factions(campaign_id)
            match = next((f for f in factions if f["slug"] == change.faction_slug), None)
            if match is None:
                result.skipped.append(change)
            else:
                repo.update_faction_reputation(match["faction_id"], change.delta_steps)
                event = DomainEvent(
                    event_id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    event_type="reputation_changed",
                    payload={
                        "faction_slug": change.faction_slug,
                        "delta_steps": change.delta_steps,
                        "reason": change.reason,
                    },
                )
                repo.insert_domain_event(event)
                applied_event = DomainEvent(
                    event_id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    event_type="proposal.applied",
                    payload={"kind": change.kind, "reason": change.reason},
                )
                repo.insert_domain_event(applied_event)
                result.applied.append(change)
                result.events.append(event)
        elif isinstance(change, ApplyConsequenceChange):
            # Deterministic reaction is authoritative for stress; skip to prevent duplication.
            result.skipped.append(change)
        else:
            result.skipped.append(change)

    return result
