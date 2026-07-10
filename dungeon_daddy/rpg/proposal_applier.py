"""Proposal applier — Phase 36: auto-apply low-risk proposals."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.tags import normalize_tag
from dungeon_daddy.rpg.proposal import (
    AdjustReputationChange,
    ApplyConsequenceChange,
    BlockExitChange,
    CreateMemoryChange,
    GrantItemChange,
    ProposedChange,
    StripItemChange,
    TransformItemChange,
)
from dungeon_daddy.rpg.proposal_validator import ValidationResult

_log = logging.getLogger(__name__)


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
    matched_clocks: list[Any] | None = None,
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
                # Auto-applied: no player review queue. The AI impacts the world
                # directly (owner decision 2026-06-29); approved memories feed
                # back through MemoryRetriever, which reads only `approved`.
                status="approved",
            )
            # A5b: normalize LLM-proposed tags to canonical form; drop (and log)
            # anything un-normalizable so a model tag typo never loses the memory
            # nor poisons the tag space (owner ruling 2026-07-10).
            for tag in change.tags:
                canonical = normalize_tag(tag)
                if canonical is None:
                    _log.warning("dropping un-normalizable proposed memory tag %r", tag)
                    continue
                repo.add_memory_tag(memory_id, canonical)
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
        elif isinstance(change, GrantItemChange):
            items = repo.get_items(campaign_id)
            match = next((i for i in items if i["slug"] == change.item_slug), None)
            if match is None:
                result.skipped.append(change)
            else:
                repo.update_item_owner(match["item_id"], change.to_actor_id)
                event = DomainEvent(
                    event_id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    event_type="item.granted",
                    payload={
                        "item_slug": change.item_slug,
                        "to_actor_id": change.to_actor_id,
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
        elif isinstance(change, StripItemChange):
            repo.update_item_status(change.item_id, "lost")
            event = DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="item.stripped",
                payload={"item_id": change.item_id, "reason": change.reason},
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
        elif isinstance(change, TransformItemChange):
            repo.update_item_slug(change.item_id, change.new_slug)
            event = DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="item.transformed",
                payload={
                    "item_id": change.item_id,
                    "new_slug": change.new_slug,
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
        elif isinstance(change, BlockExitChange):
            repo.update_exit_status(change.exit_id, "blocked")
            event = DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="exit.blocked",
                payload={"exit_id": change.exit_id, "reason": change.reason},
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
        else:
            result.skipped.append(change)

    return result
