from datetime import UTC, datetime

import pytest

from dungeon_daddy.reporting.models import (
    ActionUsageRow,
    ClockActivityRow,
    FalloutRow,
    MemoryStats,
    OutcomeBreakdown,
    PlaytestReport,
    ProposalStats,
    StressDistributionRow,
)


def test_outcome_breakdown_defaults_to_zero():
    ob = OutcomeBreakdown()
    assert ob.critical == 0
    assert ob.full == 0
    assert ob.partial == 0
    assert ob.miss == 0


def test_proposal_stats_by_kind_default_empty():
    ps = ProposalStats()
    assert ps.by_kind == {}
    assert ps.applied == 0
    assert ps.rejected == 0


def test_action_usage_row_rejects_missing_action_key():
    with pytest.raises(Exception):
        ActionUsageRow(count=3)


def test_playtest_report_validates_with_all_sub_models():
    report = PlaytestReport(
        campaign_id="camp:test",
        generated_at=datetime(2026, 6, 13, 0, 0, tzinfo=UTC),
        action_usage=[ActionUsageRow(action_key="fight", count=3)],
        outcome_breakdown=OutcomeBreakdown(full=2, partial=1),
        stress_distribution=[StressDistributionRow(actor_id="a1", track_key="body", total_marks=2)],
        clock_activity=[ClockActivityRow(label="Bone Warden", clock_id="clk1", times_advanced=4, final_status="completed")],
        fallout_frequency=[FalloutRow(actor_id="a1", track_key="body", severity="minor")],
        proposal_stats=ProposalStats(applied=5, rejected=1),
        memory_stats=MemoryStats(created=3, approved=2),
    )
    assert report.campaign_id == "camp:test"
    assert len(report.action_usage) == 1
    assert report.outcome_breakdown.full == 2
    assert report.proposal_stats.applied == 5
    assert report.memory_stats.created == 3
