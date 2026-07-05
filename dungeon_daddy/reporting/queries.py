from __future__ import annotations

from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.reporting.models import (
    ActionUsageRow,
    ClockActivityRow,
    FalloutRow,
    MemoryStats,
    OutcomeBreakdown,
    ProposalStats,
    StressDistributionRow,
)

if TYPE_CHECKING:
    from dungeon_daddy.memory.repository import MemoryRepository


def action_usage(events: list[DomainEvent]) -> list[ActionUsageRow]:
    counts: Counter[str] = Counter()
    for e in events:
        if e.event_type == "action.resolved":
            counts[e.payload["action_key"]] += 1
    return [ActionUsageRow(action_key=k, count=v) for k, v in counts.most_common()]


def outcome_breakdown(events: list[DomainEvent]) -> OutcomeBreakdown:
    counts: Counter[str] = Counter()
    for e in events:
        if e.event_type == "action.resolved":
            counts[e.payload.get("outcome", "")] += 1
    return OutcomeBreakdown(
        critical=counts["critical"],
        full=counts["full"],
        partial=counts["partial"],
        miss=counts["miss"],
    )


def stress_distribution(events: list[DomainEvent]) -> list[StressDistributionRow]:
    totals: defaultdict[tuple[str, str], int] = defaultdict(int)
    for e in events:
        if e.event_type == "stress.marked":
            key = (e.payload["actor_id"], e.payload["track_key"])
            totals[key] += e.payload.get("count", 1)
    return [
        StressDistributionRow(actor_id=actor_id, track_key=track_key, total_marks=marks)
        for (actor_id, track_key), marks in totals.items()
    ]


def clock_activity(events: list[DomainEvent]) -> list[ClockActivityRow]:
    advance_counts: Counter[str] = Counter()
    last_event: dict[str, DomainEvent] = {}
    for e in events:
        if e.event_type == "clock.advanced":
            clock_id = e.payload["clock_id"]
            advance_counts[clock_id] += 1
            last_event[clock_id] = e
    rows = [
        ClockActivityRow(
            label=last_event[clock_id].payload.get("label", ""),
            clock_id=clock_id,
            times_advanced=count,
            final_status=last_event[clock_id].payload.get("status", ""),
        )
        for clock_id, count in advance_counts.most_common()
    ]
    return rows


def fallout_frequency(repo: MemoryRepository, campaign_id: str) -> list[FalloutRow]:
    actors = repo.get_actors_by_campaign(campaign_id)
    rows: list[FalloutRow] = []
    for actor in actors:
        records = repo.get_fallout_records(campaign_id, actor["actor_id"])
        for r in records:
            rows.append(FalloutRow(
                actor_id=r["actor_id"],
                track_key=r["track_key"],
                severity=r["severity"],
            ))
    return rows


def proposal_stats(events: list[DomainEvent]) -> ProposalStats:
    applied = 0
    rejected = 0
    by_kind: Counter[str] = Counter()
    for e in events:
        if e.event_type == "proposal.applied":
            applied += 1
            kind = e.payload.get("kind", "")
            if kind:
                by_kind[kind] += 1
        elif e.event_type == "proposal.rejected":
            rejected += 1
    return ProposalStats(applied=applied, rejected=rejected, by_kind=dict(by_kind))


def memory_stats(events: list[DomainEvent], repo: MemoryRepository, campaign_id: str) -> MemoryStats:
    created = sum(1 for e in events if e.event_type == "memory_created")
    counts = repo.count_by_status(campaign_id)
    return MemoryStats(
        created=created,
        approved=counts.get("approved", 0),
        rejected=counts.get("rejected", 0),
        draft=counts.get("draft", 0),
        archived=counts.get("archived", 0),
    )
