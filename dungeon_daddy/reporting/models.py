from datetime import datetime
from pydantic import BaseModel, Field


class ActionUsageRow(BaseModel):
    action_key: str
    count: int


class OutcomeBreakdown(BaseModel):
    critical: int = 0
    full: int = 0
    partial: int = 0
    miss: int = 0


class StressDistributionRow(BaseModel):
    actor_id: str
    track_key: str
    total_marks: int


class ClockActivityRow(BaseModel):
    label: str
    clock_id: str
    times_advanced: int
    final_status: str


class FalloutRow(BaseModel):
    actor_id: str
    track_key: str
    severity: str


class ProposalStats(BaseModel):
    applied: int = 0
    rejected: int = 0
    by_kind: dict[str, int] = Field(default_factory=dict)


class MemoryStats(BaseModel):
    created: int = 0
    approved: int = 0
    rejected: int = 0
    draft: int = 0
    archived: int = 0


class PlaytestReport(BaseModel):
    campaign_id: str
    generated_at: datetime
    action_usage: list[ActionUsageRow]
    outcome_breakdown: OutcomeBreakdown
    stress_distribution: list[StressDistributionRow]
    clock_activity: list[ClockActivityRow]
    fallout_frequency: list[FalloutRow]
    proposal_stats: ProposalStats
    memory_stats: MemoryStats
