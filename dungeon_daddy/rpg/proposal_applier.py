"""Proposal applier — Phase 36: auto-apply low-risk proposals."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.proposal import ApplyConsequenceChange, CreateMemoryChange, ProposedChange
from dungeon_daddy.rpg.proposal_validator import ValidationResult
from dungeon_daddy.rpg.stress import mark_stress
from dungeon_daddy.rpg.stress_routing import choose_stress_track
from dungeon_daddy.rpg.models import StressTrack

if TYPE_CHECKING:
    from dungeon_daddy.rpg.models import ClockState


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
    matched_clocks: "list[ClockState] | None" = None,
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
            result.applied.append(change)
            result.events.append(event)
        elif isinstance(change, ApplyConsequenceChange):
            deterministic_track = choose_stress_track(
                action_key=action_key or "",
                intent=intent,
                matched_clocks=matched_clocks,
            )
            if change.track_key != deterministic_track:
                result.skipped.append(change)
                continue
            tracks = {
                t["track_key"]: StressTrack(
                    track_key=t["track_key"], capacity=t["capacity"], filled=t["filled"]
                )
                for t in repo.get_actor_stress_tracks(change.actor_id)
            }
            track = tracks.get(change.track_key, StressTrack(track_key=change.track_key))
            updated = mark_stress(track, amount=change.amount)
            repo.save_actor_stress_track(
                change.actor_id, updated.track_key, updated.capacity, updated.filled
            )
            event = DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="stress.marked",
                payload={
                    "actor_id": change.actor_id,
                    "track_key": updated.track_key,
                    "filled": updated.filled,
                    "source": validation_result.source,
                },
            )
            repo.insert_domain_event(event)
            result.applied.append(change)
            result.events.append(event)
        else:
            result.skipped.append(change)

    return result
