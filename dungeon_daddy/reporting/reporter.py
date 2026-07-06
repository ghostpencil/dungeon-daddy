from datetime import UTC, datetime

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.reporting.models import PlaytestReport
from dungeon_daddy.reporting.queries import (
    action_usage,
    clock_activity,
    fallout_frequency,
    memory_stats,
    outcome_breakdown,
    proposal_stats,
    stress_distribution,
)


def build_report(repo: MemoryRepository, campaign_id: str) -> PlaytestReport:
    events = repo.get_domain_events(campaign_id)
    return PlaytestReport(
        campaign_id=campaign_id,
        generated_at=datetime.now(UTC),
        action_usage=action_usage(events),
        outcome_breakdown=outcome_breakdown(events),
        stress_distribution=stress_distribution(events),
        clock_activity=clock_activity(events),
        fallout_frequency=fallout_frequency(repo, campaign_id),
        proposal_stats=proposal_stats(events),
        memory_stats=memory_stats(events, repo, campaign_id),
    )
